"""
WSGI Entry Point for Production Deployment
Uses Gunicorn with Gevent workers for async support
"""

import os
import sys

# Add project directories to Python path for reorganized structure
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'api'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'core'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'ml'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'database'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'utils'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'web'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'config'))

from server import app, socketio

# Set production environment
os.environ.setdefault('FLASK_ENV', 'production')

# Initialize application
application = app

# For running with gunicorn + socketio
if __name__ == "__main__":
    socketio.run(application)
