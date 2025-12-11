"""
WSGI Entry Point for Production Deployment
Uses shared application factory for consistent configuration
"""

import os
import sys
from pathlib import Path

# Add project directories to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set production environment
os.environ.setdefault('FLASK_ENV', 'production')

# Import shared application factory
from src.api.app_factory import create_app, register_core_blueprints

# Create and initialize application
app, socketio = create_app(
    config_name='production',
    register_blueprints=register_core_blueprints
)

# For WSGI compatibility
application = app

# For running with gunicorn + socketio
if __name__ == "__main__":
    socketio.run(application, host='0.0.0.0', port=5000)
