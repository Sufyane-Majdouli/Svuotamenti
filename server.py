import os
import sys
from pathlib import Path

# Add the project root to the Python path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

# Import the Flask app
from app import app

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
uploads_dir = Path(PROJECT_ROOT) / 'app' / 'static' / 'uploads'
os.makedirs(uploads_dir, exist_ok=True)

# Vercel will use this as the main entrypoint
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080))) 