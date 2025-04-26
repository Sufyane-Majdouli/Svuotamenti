import os
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Starting server initialization...")

# Add the project root to the Python path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)
logger.info(f"Added {PROJECT_ROOT} to Python path")

# Log Vercel environment information
if os.environ.get('VERCEL', False):
    logger.info("Running on Vercel environment")
    logger.info(f"Python path: {sys.path}")
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info(f"Directory contents: {os.listdir('.')}")
    logger.info(f"Environment variables: {[(k, v) for k, v in os.environ.items() if not k.startswith(('AWS', 'LAMBDA')) and 'SECRET' not in k.upper()]}")

# Import the Flask app
try:
    from app import app
    logger.info("Successfully imported Flask app")
except Exception as e:
    logger.error(f"Error importing Flask app: {str(e)}")
    raise

# Add a specific Vercel health check route
@app.route('/api/healthcheck')
def healthcheck():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "python_path": str(sys.path),
        "project_root": PROJECT_ROOT,
        "working_dir": os.getcwd(),
        "env_vars": {k: v for k, v in os.environ.items() if "SECRET" not in k.upper()}
    }

# Ensure upload folder exists
try:
    upload_folder = '/tmp' if os.environ.get('VERCEL', False) else os.path.join(PROJECT_ROOT, 'app', 'static', 'uploads')
    os.makedirs(upload_folder, exist_ok=True)
    logger.info(f"Created upload folder at: {upload_folder}")
except Exception as e:
    logger.error(f"Error creating upload folder: {str(e)}")

# For debugging on Vercel
@app.route('/debug')
def debug_info():
    return {
        "python_path": str(sys.path),
        "project_root": PROJECT_ROOT,
        "working_dir": os.getcwd(),
        "directory_contents": os.listdir('.'),
        "app_config": {
            "upload_folder": app.config.get('UPLOAD_FOLDER', 'Not set'),
            "upload_folder_exists": os.path.exists(app.config.get('UPLOAD_FOLDER', '')),
            "upload_folder_writable": os.access(app.config.get('UPLOAD_FOLDER', ''), os.W_OK),
        },
        "tmp_dir_writable": os.access('/tmp', os.W_OK),
        "vercel_env": os.environ.get('VERCEL', 'Not set')
    }

# Vercel will use this as the main entrypoint
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080))) 