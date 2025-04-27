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
        uploaded_filepaths = []
        uploaded_filenames = [] # Keep track of original filenames for display
        try:
            for f in form.files.data:
                if f:
                    filename = secure_filename(f.filename)
                    unique_filename = f"{uuid.uuid4().hex}_{filename}"
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                    
                    app.logger.info(f"Attempting to save file: {filename} to: {filepath}")
                    
                    # Ensure directory exists (moved check here)
                    upload_dir = app.config['UPLOAD_FOLDER']
                    if not os.path.exists(upload_dir):
                        os.makedirs(upload_dir, exist_ok=True)
                        app.logger.info(f"Created upload directory: {upload_dir}")
                    elif not os.access(upload_dir, os.W_OK):
                         app.logger.error(f"Upload directory is not writable: {upload_dir}")
                         flash(f'Error: Upload directory is not writable.', 'danger')
                         # Return here to stop processing if directory is bad
                         return render_template('upload.html', title='Upload Files', form=form)

                    f.save(filepath)
                    app.logger.info(f"File saved successfully to {filepath}")
                    
                    if not os.path.exists(filepath):
                        app.logger.error(f"File was not saved! Path does not exist: {filepath}")
                        flash(f'Error: File upload failed for {filename}. The file could not be saved.', 'danger')
                        continue # Continue to the next file in the loop
                        
                    uploaded_filepaths.append(filepath)
                    uploaded_filenames.append(filename) # Store original filename
            # This block should be outside the for loop but inside the try block
            if not uploaded_filepaths:
                flash('No valid files were uploaded.', 'warning')
                return render_template('upload.html', title='Upload Files', form=form)

            # Store the list of filepaths and filenames in session
            session['uploaded_files_info'] = list(zip(uploaded_filenames, uploaded_filepaths))
            app.logger.info(f"Setting session uploaded_files_info to {session['uploaded_files_info']}")
            
            # Redirect to the file selection page instead of map view
            return redirect(url_for('select_files')) 
            
        # Except block aligned with the try block
        except Exception as e:
            app.logger.error(f"Error during file upload: {str(e)}", exc_info=True)
            flash(f'An unexpected error occurred during upload: {str(e)}', 'danger')
            return render_template('upload.html', title='Upload Files', form=form)
    
    return render_template('upload.html', title='Upload Files', form=form)

@app.route('/select_files', methods=['GET'])
def select_files():
    """Displays the list of uploaded files for selection."""
    uploaded_files_info = session.get('uploaded_files_info', [])
    if not uploaded_files_info:
        flash('No files uploaded yet. Please upload files first.', 'warning')
        return redirect(url_for('upload_file'))
        
    # Pass the list of (filename, filepath) tuples to the template
    return render_template('select_files.html', title='Select Files', files_info=uploaded_files_info)

@app.route('/map', methods=['GET', 'POST']) # Allow POST for file selection
def view_map():
    if request.method == 'POST':
        # Files selected from the select_files page
        selected_filepaths = request.form.getlist('selected_files')
        app.logger.info(f"Received selected files via POST: {selected_filepaths}")
        if not selected_filepaths:
             flash('No files were selected to display on the map.', 'warning')
             # Redirect back to selection or upload page
             uploaded_files_info = session.get('uploaded_files_info', [])
             if uploaded_files_info:
                 return redirect(url_for('select_files'))
             else:
                 # Correct indentation for this return
                 return redirect(url_for('upload_file'))
        
        filepaths_to_process = selected_filepaths
        source = "POST selection"
        
    else: # Handle GET request (e.g., direct navigation or refresh)
        flash('Please select files to view on the map first.', 'info')
        return redirect(url_for('select_files')) # Or upload_file if session is empty

    app.logger.info(f"Processing map using files ({source}): {filepaths_to_process}")
    
    all_emptyings = []
    valid_files_processed = 0
    total_files_attempted = len(filepaths_to_process)
    
    for filepath in filepaths_to_process:
        # Security check: Ensure the filepath is within the allowed upload directory
        # This prevents potential directory traversal if paths were manipulated
        if not filepath.startswith(app.config['UPLOAD_FOLDER']):
            app.logger.warning(f"Skipping potentially unsafe file path: {filepath}")
            continue
            
        if not os.path.exists(filepath):
            app.logger.error(f"Selected file does not exist: {filepath}")
            # Extract original filename if possible for a better message
            original_filename = os.path.basename(filepath).split('_', 1)[-1] if '_' in os.path.basename(filepath) else os.path.basename(filepath)
            flash(f'Error: Selected file \'{original_filename}\' not found. It might have been removed.', 'warning')
            continue
        
        try:
            app.logger.info(f"Reading CSV data from {filepath}")
            emptyings_from_file = read_emptyings_from_csv(filepath)
            all_emptyings.extend(emptyings_from_file)
            valid_files_processed += 1
            app.logger.info(f"Successfully read {len(emptyings_from_file)} records from {os.path.basename(filepath)}")
            
        except Exception as e:
            original_filename = os.path.basename(filepath).split('_', 1)[-1] if '_' in os.path.basename(filepath) else os.path.basename(filepath)
            app.logger.error(f"Error processing file {filepath}: {str(e)}")
            flash(f'Error reading or processing file \'{original_filename}\': {str(e)}', 'danger')

    if valid_files_processed == 0 and total_files_attempted > 0:
        flash('No valid data could be loaded from the selected files.', 'danger')
        # Redirect back to selection page as no map can be shown
        return redirect(url_for('select_files'))
    elif valid_files_processed < total_files_attempted:
        flash(f'Processed data from {valid_files_processed} out of {total_files_attempted} selected files. Some files may have had errors.', 'warning')
    elif not all_emptyings and total_files_attempted == 0: # Should not happen due to checks above, but safeguard
         flash('No files were selected or processed.', 'warning')
         return redirect(url_for('select_files'))
         
    # --- Rest of the map data preparation and rendering logic (as before) ---
    map_data = {
        'points': [],
        'center': [41.9028, 12.4964]  # Default center
    }
    total_records = len(all_emptyings)
    valid_coords = 0
    waste_types = {}
    
    for emptying in all_emptyings:
        if (emptying.latitude == 0.0 and emptying.longitude == 0.0) or \
           not (-90 <= emptying.latitude <= 90) or not (-180 <= emptying.longitude <= 180):
            continue
        valid_coords += 1
        waste_type = emptying.waste_type.lower()
        waste_types[waste_type] = waste_types.get(waste_type, 0) + 1
        marker_color = 'grey'
        if 'organic' in waste_type or 'food' in waste_type or 'compost' in waste_type:
            marker_color = 'brown'
        elif 'plastic' in waste_type:
            marker_color = 'yellow'
        elif 'paper' in waste_type or 'cardboard' in waste_type:
            marker_color = 'dodgerblue'
        elif 'glass' in waste_type:
            marker_color = 'green'
        elif 'residual' in waste_type or 'non-recycl' in waste_type or 'general' in waste_type:
            marker_color = 'grey'
        elif 'metal' in waste_type or 'aluminum' in waste_type:
            marker_color = 'cadetblue'
        elif 'electronic' in waste_type or 'ewaste' in waste_type:
            marker_color = 'darkred'
        map_data['points'].append({
            'lat': emptying.latitude,
            'lng': emptying.longitude,
            'tag_code': emptying.tag_code,
            'waste_type': emptying.waste_type,
            'weight': emptying.weight,
            'timestamp': emptying.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            'color': marker_color
        })
    
    if valid_coords > 0:
        sum_lat = sum(point['lat'] for point in map_data['points'])
        sum_lng = sum(point['lng'] for point in map_data['points'])
        map_data['center'] = [sum_lat / valid_coords, sum_lng / valid_coords]
    
    stats = {
        'total_records': total_records,
        'valid_coords': valid_coords,
        'waste_types': waste_types
    }
    legend_items = [
        {'name': 'Organic', 'color': 'brown'},
        {'name': 'Residual', 'color': 'grey'},
        {'name': 'Plastic', 'color': 'yellow'},
        {'name': 'Paper', 'color': 'dodgerblue'},
        {'name': 'Glass', 'color': 'green'},
        {'name': 'Metal', 'color': 'cadetblue'},
        {'name': 'Electronic', 'color': 'darkred'}
    ]
    
    return render_template('map.html', title='Map View', map_data=map_data, stats=stats, legend_items=legend_items)

@app.route('/ftp_browser', methods=['GET', 'POST'])
def ftp_browser():
    # Initialize session values if not present
    if 'ftp_host' not in session:
        session['ftp_host'] = '192.168.1.100'
        session['ftp_port'] = 21
        session['ftp_user'] = 'user'
        session['ftp_password'] = ''
        session['connected'] = False # Ensure disconnected state initially
        session['current_dir'] = '/' 
        
    form = FTPSettingsForm()
    error_message = None
    vercel_warning = None
    file_list = []
    
    # Check if running on Vercel for warning
    if os.environ.get('VERCEL'):
        vercel_warning = "Note: FTP functionality may be limited or unreliable on Vercel's serverless platform due to network restrictions and timeouts."
        
    # Handle form submission to connect/update settings
    if form.validate_on_submit():
        app.logger.info("FTP settings form submitted")
        # Save settings to session
        session['ftp_host'] = form.host.data
        session['ftp_port'] = form.port.data
        session['ftp_user'] = form.username.data
        session['ftp_password'] = form.password.data
        session['connected'] = True # Assume connection attempt on submit
        session['current_dir'] = '/' # Reset directory on new connection attempt
        # Redirect to the same page using GET to attempt connection
        return redirect(url_for('ftp_browser'))

    # Handle GET request: Attempt connection and list files if connected flag is true
    if request.method == 'GET':
        # Pre-populate form with session values
        form.host.data = session.get('ftp_host')
        form.port.data = session.get('ftp_port')
        form.username.data = session.get('ftp_user')
        # Do not pre-fill password for security
        # form.password.data = session.get('ftp_password') 
        
        # Attempt to list files only if 'connected' flag is set
        if session.get('connected'):
            app.logger.info(f"Attempting FTP connection to {session.get('ftp_host')}:{session.get('ftp_port')} in directory {session.get('current_dir')}")
            ftp = None # Initialize ftp variable
            try:
                ftp = ftplib.FTP() # Create FTP object outside with block for finally
                timeout = 5 
                app.logger.info(f"Connecting to FTP with timeout {timeout}s")
                ftp.connect(session['ftp_host'], session['ftp_port'], timeout=timeout)
                ftp.login(session['ftp_user'], session['ftp_password'])
                ftp.set_pasv(True) 
                
                current_dir_session = session.get('current_dir', '/')
                if current_dir_session != '/':
                    app.logger.info(f"Changing directory to {current_dir_session}")
                    ftp.cwd(current_dir_session)
                
                app.logger.info(f"Retrieving directory listing for {ftp.pwd()}")
                files_raw = []
                ftp.dir(files_raw.append)
                app.logger.info(f"Successfully retrieved {len(files_raw)} raw listing items")

                # Parse listing (add basic parsing)
                for item in files_raw:
                    parts = item.split()
                    if len(parts) < 9: continue # Basic check for valid line
                    
                    name = ' '.join(parts[8:])
                    is_dir = item.startswith('d')
                    size = parts[4] if not is_dir else '-'
                    date_str = ' '.join(parts[5:8])
                    
                    file_list.append({
                        'name': name,
                        'is_dir': is_dir,
                        'size': size,
                        'date': date_str
                    })
                app.logger.info(f"Parsed {len(file_list)} items from directory listing")

            except ftplib.error_timeout as e:
                app.logger.error(f"FTP connection timed out: {str(e)}", exc_info=True)
                error_message = "FTP connection timed out. Server might be slow or unreachable from Vercel."
                session['connected'] = False 
            except ConnectionRefusedError as e:
                app.logger.error(f"FTP connection refused: {str(e)}", exc_info=True)
                error_message = "FTP connection refused. Ensure server details are correct and firewall allows connection."
                session['connected'] = False
            except ftplib.error_perm as e:
                app.logger.error(f"FTP permission error: {str(e)}", exc_info=True)
                error_message = f"FTP permission error: {str(e)}. Check credentials/permissions."
                session['connected'] = False
            except Exception as e:
                app.logger.error(f"An unexpected FTP error occurred: {str(e)}", exc_info=True)
                error_message = f"An unexpected FTP error occurred: {str(e)}"
                session['connected'] = False
            finally:
                # Ensure connection is closed
                if ftp and ftp.sock:
                    try:
                        app.logger.info("Closing FTP connection in finally block (ftp_browser)")
                        ftp.quit()
                    except Exception as e_quit:
                        app.logger.error(f"Error during FTP quit: {str(e_quit)}")
                
    return render_template('ftp_browser.html', title='FTP Browser', 
                          form=form, files=file_list, 
                          connected=session.get('connected', False),
                          current_dir=session.get('current_dir', '/'),
                          error=error_message,
                          vercel_warning=vercel_warning)

@app.route('/ftp_navigate', methods=['POST'])
def ftp_navigate():
    if not session.get('connected'):
        app.logger.warning("FTP navigate called but not connected.")
        return jsonify({'success': False, 'error': 'Not connected to FTP server. Please connect first.'}), 400
    
    target_dir = request.form.get('dir')
    if not target_dir:
        return jsonify({'success': False, 'error': 'No target directory specified.'}), 400
        
    current_dir_session = session.get('current_dir', '/')
    app.logger.info(f"FTP navigate request: from {current_dir_session} to {target_dir}")
    
    ftp = None
    try:
        ftp = ftplib.FTP()
        timeout = 5
        ftp.connect(session['ftp_host'], session['ftp_port'], timeout=timeout)
        ftp.login(session['ftp_user'], session['ftp_password'])
        ftp.set_pasv(True)
        
        # Navigate to current directory first (for safety)
        if current_dir_session != '/':
            ftp.cwd(current_dir_session)
        
        # Navigate to target directory
        ftp.cwd(target_dir) # ftplib handles '..' 
        
        new_dir = ftp.pwd()
        session['current_dir'] = new_dir
        app.logger.info(f"FTP navigate successful. New directory: {new_dir}")
        return jsonify({'success': True, 'new_dir': new_dir})
            
    except ftplib.error_timeout:
        app.logger.error("FTP navigate: Connection timed out.")
        return jsonify({'success': False, 'error': 'FTP connection timed out during navigation.'}), 500
    except ftplib.error_perm as e:
        app.logger.error(f"FTP navigate: Permission error: {str(e)}")
        return jsonify({'success': False, 'error': f'Permission error: {str(e)}'}), 500
    except Exception as e:
        app.logger.error(f"FTP navigate: Unexpected error: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': f'An unexpected error occurred: {str(e)}'}), 500
    finally:
        if ftp and ftp.sock:
            try:
                app.logger.info("Closing FTP connection in finally block (ftp_navigate)")
                ftp.quit()
            except Exception as e_quit:
                app.logger.error(f"Error during FTP quit: {str(e_quit)}")

@app.route('/ftp_download', methods=['POST'])
def ftp_download():
    if not session.get('connected'):
        app.logger.warning("FTP download called but not connected.")
        return jsonify({'success': False, 'error': 'Not connected to FTP server. Please connect first.'}), 400
    
    filename = request.form.get('file')
    if not filename:
         return jsonify({'success': False, 'error': 'No filename specified for download.'}), 400
         
    current_dir_session = session.get('current_dir', '/')
    app.logger.info(f"FTP download request: File '{filename}' from directory '{current_dir_session}'")
    
    local_path = None # Initialize for finally block
    ftp = None
    try:
        # Securely create local path in the upload folder
        local_filename = secure_filename(filename)
        unique_filename = f"{uuid.uuid4().hex}_{local_filename}"
        local_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        # Ensure upload folder exists and is writable
        upload_dir = app.config['UPLOAD_FOLDER']
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir, exist_ok=True)
        elif not os.access(upload_dir, os.W_OK):
            app.logger.error(f"FTP download: Upload directory not writable: {upload_dir}")
            return jsonify({'success': False, 'error': 'Server upload directory is not writable.'}), 500
            
        ftp = ftplib.FTP()
        timeout = 5
        ftp.connect(session['ftp_host'], session['ftp_port'], timeout=timeout)
        ftp.login(session['ftp_user'], session['ftp_password'])
        ftp.set_pasv(True)
        
        if current_dir_session != '/':
            ftp.cwd(current_dir_session)
        
        app.logger.info(f"Attempting to download FTP file '{filename}' to local path '{local_path}'")
        with open(local_path, 'wb') as local_file:
            ftp.retrbinary(f'RETR {filename}', local_file.write)
        
        app.logger.info(f"FTP download complete for {filename}")
        
        # Store the filepath of the *downloaded* file for map view
        session['uploaded_files_info'] = [(filename, local_path)]
        app.logger.info(f"Set session uploaded_files_info for downloaded file: {session['uploaded_files_info']}")
        
        # Redirect to file selection page, which will show the single downloaded file
        return jsonify({
            'success': True, 
            'message': f'File {filename} downloaded successfully.',
            'redirect': url_for('select_files')
        })
        
    except ftplib.error_timeout:
        app.logger.error("FTP download: Connection timed out.")
        if local_path and os.path.exists(local_path): os.remove(local_path) # Clean up partial download
        return jsonify({'success': False, 'error': 'FTP connection timed out during download.'}), 500
    except ftplib.error_perm as e:
        app.logger.error(f"FTP download: Permission error: {str(e)}")
        if local_path and os.path.exists(local_path): os.remove(local_path)
        return jsonify({'success': False, 'error': f'Permission error during download: {str(e)}'}), 500
    except Exception as e:
        app.logger.error(f"FTP download: Unexpected error: {str(e)}", exc_info=True)
        if local_path and os.path.exists(local_path): os.remove(local_path)
        return jsonify({'success': False, 'error': f'An unexpected error occurred during download: {str(e)}'}), 500
    finally:
         if ftp and ftp.sock:
            try:
                app.logger.info("Closing FTP connection in finally block (ftp_download)")
                ftp.quit()
            except Exception as e_quit:
                app.logger.error(f"Error during FTP quit: {str(e_quit)}")

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