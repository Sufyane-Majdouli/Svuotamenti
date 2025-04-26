import os
import sys
import logging
from pathlib import Path
from flask import Flask, redirect, url_for, render_template, flash, request, jsonify, session

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Starting Flask app initialization...")

# Create a simple Flask app that serves as a diagnostic
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'

# Debug routes
@app.route('/')
def index():
    return f"""
    <html>
    <head><title>Svuotamenti Diagnostic</title></head>
    <body>
        <h1>Svuotamenti Diagnostic Page</h1>
        <p>This is a simple diagnostic page for the Svuotamenti application.</p>
        <p>Python path: {sys.path}</p>
        <p>Working directory: {os.getcwd()}</p>
        <p>Files in directory: {os.listdir('.')}</p>
        <p>Svuotamenti directory exists: {os.path.isdir('Svuotamenti')}</p>
        <p>Environment: {[f"{k}={v}" for k, v in os.environ.items() if not k.startswith(('AWS', 'LAMBDA')) and 'SECRET' not in k.upper()]}</p>
    </body>
    </html>
    """

@app.route('/test')
def test():
    return jsonify({
        "status": "ok",
        "message": "Test endpoint is working"
    })

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return f"404 Not Found: {str(e)}", 404

@app.errorhandler(500)
def server_error(e):
    return f"500 Server Error: {str(e)}", 500

# For local testing
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080))) 