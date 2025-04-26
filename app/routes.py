import os
import csv
import uuid
import ftplib
from datetime import datetime
from pathlib import Path
from werkzeug.utils import secure_filename
import sys

from flask import render_template, request, redirect, url_for, flash, jsonify, session
# Fix imports to work with Vercel deployment
try:
    # Try relative import first (how it works locally)
    from app import app
    from app.forms import FTPSettingsForm, UploadForm
    from app.models import read_emptyings_from_csv, Emptying
except ImportError:
    # For Vercel deployment
    from Svuotamenti.app import app
    from Svuotamenti.app.forms import FTPSettingsForm, UploadForm
    from Svuotamenti.app.models import read_emptyings_from_csv, Emptying

# Ensure upload folder exists
os.makedirs(os.path.join(os.getcwd(), app.config['UPLOAD_FOLDER']), exist_ok=True)

# Simple test route to check if the app is loading
@app.route('/test')
def test_route():
    return "Flask app is running! Python path: " + str(sys.path)

@app.route('/')
def index():
    return render_template('index.html', title='Home')

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    form = UploadForm()
    if form.validate_on_submit():
        try:
            f = form.file.data
            filename = secure_filename(f.filename)
            # Generate unique filename to prevent conflicts
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            
            # Log file path for debugging
            app.logger.info(f"Attempting to save file to: {filepath}")
            app.logger.info(f"Upload folder is: {app.config['UPLOAD_FOLDER']}")
            app.logger.info(f"Is directory writable: {os.access(app.config['UPLOAD_FOLDER'], os.W_OK)}")
            
            # Create the directory if it doesn't exist (again, for safety)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Save the file
            f.save(filepath)
            app.logger.info(f"File saved successfully to {filepath}")
            
            # Verify the file exists
            if not os.path.exists(filepath):
                app.logger.error(f"File was not saved! Path does not exist: {filepath}")
                flash('Error: File upload failed. The file could not be saved.', 'danger')
                return render_template('upload.html', title='Upload File', form=form)
            
            # Store the filepath in session for the map route
            session['current_file'] = filepath
            app.logger.info(f"Setting session current_file to {filepath}")
            
            # Redirect to the map view
            return redirect(url_for('view_map'))
            
        except Exception as e:
            app.logger.error(f"Error during file upload: {str(e)}")
            flash(f'Error uploading file: {str(e)}', 'danger')
            return render_template('upload.html', title='Upload File', form=form)
    
    return render_template('upload.html', title='Upload File', form=form)

@app.route('/map')
def view_map():
    filepath = session.get('current_file')
    app.logger.info(f"Attempting to read file from: {filepath}")
    
    if not filepath:
        app.logger.warning("No file path in session")
        flash('No file selected. Please upload a file first.', 'warning')
        return redirect(url_for('upload_file'))
    
    if not os.path.exists(filepath):
        app.logger.error(f"File does not exist at path: {filepath}")
        flash('The uploaded file could not be found. Please upload a file again.', 'warning')
        return redirect(url_for('upload_file'))
    
    try:
        # Read emptyings data
        app.logger.info(f"Reading CSV data from {filepath}")
        emptyings = read_emptyings_from_csv(filepath)
        app.logger.info(f"Successfully read {len(emptyings)} records from CSV")
        
        # Prepare data for the map
        map_data = {
            'points': [],
            'center': [41.9028, 12.4964]  # Default center: Rome, Italy
        }
        
        # Statistics
        total_records = len(emptyings)
        valid_coords = 0
        waste_types = {}
        
        # Process valid emptyings
        for emptying in emptyings:
            # Skip invalid coordinates
            if (emptying.latitude == 0.0 and emptying.longitude == 0.0) or \
               not (-90 <= emptying.latitude <= 90) or not (-180 <= emptying.longitude <= 180):
                continue
            
            valid_coords += 1
            
            # Track waste types
            waste_type = emptying.waste_type.lower()
            waste_types[waste_type] = waste_types.get(waste_type, 0) + 1
            
            # Determine marker color based on waste type
            marker_color = 'red'  # Default color
            if 'plastic' in waste_type:
                marker_color = 'orange'
            elif 'paper' in waste_type:
                marker_color = 'blue'
            elif 'glass' in waste_type:
                marker_color = 'green'
            elif 'organic' in waste_type:
                marker_color = 'darkgreen'
            elif 'metal' in waste_type:
                marker_color = 'cadetblue'
            
            # Add point data
            map_data['points'].append({
                'lat': emptying.latitude,
                'lng': emptying.longitude,
                'tag_code': emptying.tag_code,
                'waste_type': emptying.waste_type,
                'weight': emptying.weight,
                'timestamp': emptying.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                'color': marker_color
            })
        
        # Calculate map center if there are valid points
        if valid_coords > 0:
            sum_lat = sum(point['lat'] for point in map_data['points'])
            sum_lng = sum(point['lng'] for point in map_data['points'])
            map_data['center'] = [sum_lat / valid_coords, sum_lng / valid_coords]
        
        # Prepare statistics for display
        stats = {
            'total_records': total_records,
            'valid_coords': valid_coords,
            'waste_types': waste_types
        }
        
        return render_template('map.html', title='Map View', map_data=map_data, stats=stats)
        
    except Exception as e:
        app.logger.error(f"Error processing file: {str(e)}")
        flash(f'Error reading or processing file: {str(e)}', 'danger')
        return redirect(url_for('upload_file'))

@app.route('/ftp_browser', methods=['GET', 'POST'])
def ftp_browser():
    # Initialize session values if not present
    if 'ftp_host' not in session:
        session['ftp_host'] = '192.168.1.100'
        session['ftp_port'] = 21
        session['ftp_user'] = 'user'
        session['ftp_password'] = ''
    
    form = FTPSettingsForm()
    
    # Pre-populate form with session values
    if request.method == 'GET':
        form.host.data = session.get('ftp_host')
        form.port.data = session.get('ftp_port')
        form.username.data = session.get('ftp_user')
        form.password.data = session.get('ftp_password')
    
    # Process form submission (connect button)
    if form.validate_on_submit():
        # Save settings to session
        session['ftp_host'] = form.host.data
        session['ftp_port'] = form.port.data
        session['ftp_user'] = form.username.data
        session['ftp_password'] = form.password.data
        
        # Store the form data in session for FTP connection
        session['connected'] = True
        session['current_dir'] = '/'
        
        # Redirect to prevent form resubmission
        return redirect(url_for('ftp_browser'))
    
    # If we're connected, list directory contents
    file_list = []
    error_message = None
    
    if session.get('connected'):
        try:
            with ftplib.FTP() as ftp:
                # Connect to server
                ftp.connect(session['ftp_host'], session['ftp_port'], timeout=10)
                ftp.login(session['ftp_user'], session['ftp_password'])
                ftp.set_pasv(True)
                
                # Navigate to current directory if not at root
                if session['current_dir'] != '/':
                    ftp.cwd(session['current_dir'])
                
                # Get directory listing
                files = []
                ftp.dir(files.append)
                
                # Parse listing
                for item in files:
                    if item.startswith('d'):
                        # Directory
                        name = item.split()[-1]
                        file_list.append({
                            'name': name,
                            'is_dir': True,
                            'size': '-',
                            'date': ' '.join(item.split()[5:8])
                        })
                    else:
                        # File
                        parts = item.split()
                        name = parts[-1]
                        size = parts[4]
                        date = ' '.join(parts[5:8])
                        file_list.append({
                            'name': name,
                            'is_dir': False,
                            'size': size,
                            'date': date
                        })
        except Exception as e:
            error_message = f"FTP Error: {str(e)}"
            session['connected'] = False
    
    return render_template('ftp_browser.html', title='FTP Browser', 
                          form=form, files=file_list, 
                          connected=session.get('connected', False),
                          current_dir=session.get('current_dir', '/'),
                          error=error_message)

@app.route('/ftp_navigate', methods=['POST'])
def ftp_navigate():
    if not session.get('connected'):
        return jsonify({'success': False, 'error': 'Not connected to FTP server'})
    
    target_dir = request.form.get('dir')
    current_dir = session.get('current_dir', '/')
    
    try:
        with ftplib.FTP() as ftp:
            # Connect to server
            ftp.connect(session['ftp_host'], session['ftp_port'], timeout=10)
            ftp.login(session['ftp_user'], session['ftp_password'])
            ftp.set_pasv(True)
            
            # Navigate to current directory first
            if current_dir != '/':
                ftp.cwd(current_dir)
            
            # Navigate to target directory
            if target_dir == '..':
                # Go up one level
                ftp.cwd('..')
            else:
                # Go into subdirectory
                ftp.cwd(target_dir)
            
            # Update current directory
            new_dir = ftp.pwd()
            session['current_dir'] = new_dir
            
            return jsonify({'success': True, 'new_dir': new_dir})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/ftp_download', methods=['POST'])
def ftp_download():
    if not session.get('connected'):
        return jsonify({'success': False, 'error': 'Not connected to FTP server'})
    
    filename = request.form.get('file')
    current_dir = session.get('current_dir', '/')
    
    try:
        # Create a unique filename for the download
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        local_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        with ftplib.FTP() as ftp:
            # Connect to server
            ftp.connect(session['ftp_host'], session['ftp_port'], timeout=10)
            ftp.login(session['ftp_user'], session['ftp_password'])
            ftp.set_pasv(True)
            
            # Navigate to current directory
            if current_dir != '/':
                ftp.cwd(current_dir)
            
            # Download the file
            with open(local_path, 'wb') as local_file:
                ftp.retrbinary(f'RETR {filename}', local_file.write)
        
        # Store the filepath in session for the map route
        session['current_file'] = local_path
        
        return jsonify({
            'success': True, 
            'message': f'File {filename} downloaded successfully',
            'redirect': url_for('view_map')
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/disconnect', methods=['POST'])
def disconnect():
    session['connected'] = False
    return jsonify({'success': True})

@app.route('/ftp_settings', methods=['GET', 'POST'])
def ftp_settings():
    form = FTPSettingsForm()
    
    # Pre-populate form with session values
    if request.method == 'GET':
        form.host.data = session.get('ftp_host', '192.168.1.100')
        form.port.data = session.get('ftp_port', 21)
        form.username.data = session.get('ftp_user', 'user')
        form.password.data = session.get('ftp_password', '')
    
    if form.validate_on_submit():
        # Save settings to session
        session['ftp_host'] = form.host.data
        session['ftp_port'] = form.port.data
        session['ftp_user'] = form.username.data
        session['ftp_password'] = form.password.data
        
        flash('FTP settings saved successfully', 'success')
        return redirect(url_for('index'))
    
    return render_template('ftp_settings.html', title='FTP Settings', form=form) 