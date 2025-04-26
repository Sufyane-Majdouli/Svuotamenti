import os
import logging
from flask import Flask
from flask_bootstrap import Bootstrap
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'

# Check if we're running on Vercel
if os.environ.get('VERCEL', False):
    # Use the /tmp directory for Vercel's serverless environment
    app.config['UPLOAD_FOLDER'] = '/tmp'
    logger.info("Running on Vercel, using /tmp directory for uploads")
else:
    # Use the static/uploads folder for local development
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/uploads')
    logger.info(f"Running locally, using {app.config['UPLOAD_FOLDER']} for uploads")

bootstrap = Bootstrap(app)

try:
    # Ensure the upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    logger.info(f"Upload folder created at {app.config['UPLOAD_FOLDER']}")
except Exception as e:
    logger.error(f"Error creating upload folder: {e}")

# Add datetime to all templates
@app.context_processor
def inject_now():
    return {'now': datetime.now()}

# Import routes after app is created to avoid circular imports
from app import routes

# Add an error handler
@app.errorhandler(404)
def page_not_found(e):
    logger.error(f"404 error: {e}")
    return "404 Not Found: The requested URL was not found on the server.", 404

@app.errorhandler(500)
def internal_server_error(e):
    logger.error(f"500 error: {e}")
    return "500 Internal Server Error: The server encountered an unexpected condition that prevented it from fulfilling the request.", 500 