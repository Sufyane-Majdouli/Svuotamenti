from flask import Flask
from flask_bootstrap import Bootstrap
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/uploads')
bootstrap = Bootstrap(app)

# Ensure the upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Add datetime to all templates
@app.context_processor
def inject_now():
    return {'now': datetime.now()}

from app import routes 