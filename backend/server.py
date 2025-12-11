"""
Backend API Server - Main Entry Point
Provides REST and WebSocket APIs for the ANC Platform
"""

from flask import Flask, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO
import logging
import os
from pathlib import Path

# Import configuration
from config import get_config
from src.db.models import db, init_db as init_db_models

# Import API blueprints
from backend.api.health import health_bp
from backend.api.audio import audio_bp
from backend.api.users import users_bp
from backend.api.sessions import sessions_bp

# Import WebSocket handlers
try:
    from backend.websocket import init_socketio
except ImportError:
    init_socketio = None

# Import middleware
from backend.middleware.auth import setup_jwt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app(config_name='development'):
    """Application factory pattern"""

    app = Flask(__name__)

    # Load configuration
    config = get_config(config_name)
    app.config.from_object(config)

    # Setup CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": app.config['CORS_ORIGINS'],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })

    # Initialize database
    db.init_app(app)

    # Setup JWT authentication
    setup_jwt(app)

    # Create database tables
    with app.app_context():
        init_db_models(app)
        logger.info("Database initialized")

    # Register API blueprints
    app.register_blueprint(health_bp)
    app.register_blueprint(audio_bp, url_prefix='/api/audio')
    app.register_blueprint(users_bp, url_prefix='/api/users')
    app.register_blueprint(sessions_bp, url_prefix='/api/sessions')

    # Root endpoint
    @app.route('/')
    def index():
        return jsonify({
            'name': 'ANC Platform Backend API',
            'version': '2.0.0',
            'status': 'running',
            'documentation': '/api/docs'
        })

    # API docs endpoint
    @app.route('/api/docs')
    def api_docs():
        return jsonify({
            'endpoints': {
                'health': '/health',
                'audio': '/api/audio/*',
                'users': '/api/users/*',
                'sessions': '/api/sessions/*'
            },
            'websocket': 'ws://localhost:5001'
        })

    logger.info("Backend server initialized")
    return app


def create_socketio(app):
    """Create and configure SocketIO server"""
    socketio = SocketIO(
        app,
        cors_allowed_origins=app.config['CORS_ORIGINS'],
        async_mode='threading',
        logger=True,
        engineio_logger=True
    )

    # Initialize WebSocket handlers
    init_socketio(socketio)

    logger.info("WebSocket server initialized")
    return socketio


# Create Flask app
app = create_app()

# Create SocketIO instance
socketio = create_socketio(app)


if __name__ == '__main__':
    # Get configuration
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'

    logger.info(f"Starting backend server on {host}:{port}")
    logger.info(f"Debug mode: {debug}")

    # Run with SocketIO
    socketio.run(
        app,
        host=host,
        port=port,
        debug=debug,
        use_reloader=debug
    )
