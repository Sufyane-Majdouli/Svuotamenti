import os
import logging
from datetime import datetime
from flask import Flask, render_template
from flask_bootstrap import Bootstrap

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create and configure the app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fallback-dev-key-not-for-production')
bootstrap = Bootstrap(app)

# Check for Vercel environment and set upload folder
if os.environ.get('VERCEL'):
    # Use /tmp on Vercel (writable in serverless environment)
    app.config['UPLOAD_FOLDER'] = '/tmp'
    logger.info("Running on Vercel, using /tmp directory for uploads")
else:
    # Local development
    app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'app/static/uploads')
    logger.info(f"Running locally, using {app.config['UPLOAD_FOLDER']} for uploads")

# Create upload folder if it doesn't exist
try:
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    logger.info(f"Upload folder created at {app.config['UPLOAD_FOLDER']}")
except Exception as e:
    logger.error(f"Error creating upload directory: {str(e)}")

# Add error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html', title='Page Not Found'), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500 error: {str(error)}")
    return render_template('500.html', title='Server Error'), 500

# Make current datetime available to all templates
@app.context_processor
def inject_now():
    return {
        'now': datetime.utcnow(),
        'VERCEL': os.environ.get('VERCEL', False)  # Add Vercel environment status to all templates
    }

# Import routes at the end to avoid circular imports
from app import routes 