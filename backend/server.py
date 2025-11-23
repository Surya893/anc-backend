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
from config.settings import Config
from config.database import db, init_db

# Import API blueprints
from api.health import health_bp
from api.audio import audio_bp
from api.users import users_bp
from api.sessions import sessions_bp

# Import WebSocket handlers
from websocket import init_socketio

# Import middleware
from middleware.auth import setup_jwt
from middleware.logging import setup_logging

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
    app.config.from_object(Config)

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

    # Setup request logging
    setup_logging(app)

    # Create database tables
    with app.app_context():
        init_db()
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
