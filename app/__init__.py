from flask import Flask
from flask_bootstrap import Bootstrap
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['UPLOAD_FOLDER'] = 'app/static/uploads'
bootstrap = Bootstrap(app)

# Add datetime to all templates
@app.context_processor
def inject_now():
    return {'now': datetime.now()}

from app import routes 