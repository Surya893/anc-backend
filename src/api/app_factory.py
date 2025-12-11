"""
Shared Application Factory for ANC Platform
Encapsulates Flask app creation, configuration, and component initialization
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import time
import os

from flask import Flask, request, jsonify, g
from flask_cors import CORS
from flask_socketio import SocketIO
from functools import wraps

# Import shared components
from config import get_config
from src.db.models import db, User, APIRequest, init_db as init_db_models
from backend.services.anc_service import ANCService
from backend.services.ml_service import MLService
from backend.middleware.auth import require_auth, verify_api_key, verify_jwt_token


def setup_logging(app):
    """Setup application logging"""
    if not app.debug and app.config.get('LOG_DIR'):
        log_dir = Path(app.config['LOG_DIR'])
        if not log_dir.exists():
            log_dir.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            app.config['LOG_FILE'],
            maxBytes=app.config['LOG_MAX_BYTES'],
            backupCount=app.config['LOG_BACKUP_COUNT']
        )
        file_handler.setFormatter(logging.Formatter(app.config['LOG_FORMAT']))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

    app.logger.setLevel(logging.INFO)
    app.logger.info('ANC Platform startup')


def register_middleware(app):
    """Register middleware hooks"""
    
    @app.before_request
    def log_request():
        """Log incoming requests"""
        request.start_time = time.time()

    @app.after_request
    def log_response(response):
        """Log responses and save API request metrics"""
        if request.endpoint and not request.endpoint.startswith('static'):
            response_time = (time.time() - request.start_time) * 1000  # ms

            # Log to file
            app.logger.info(
                f"{request.method} {request.path} - {response.status_code} - {response_time:.2f}ms"
            )

            # Save to database (async in production)
            try:
                # Determine current user if authenticated
                current_user_id = None
                if hasattr(g, 'current_user'):
                    current_user_id = g.current_user.id
                elif request.headers.get('X-API-Key'):
                    user = verify_api_key(request.headers.get('X-API-Key'))
                    if user:
                        current_user_id = user.id

                if current_user_id or app.config.get('LOG_ANONYMOUS_REQUESTS', True):
                    api_request = APIRequest(
                        user_id=current_user_id,
                        method=request.method,
                        endpoint=request.path,
                        status_code=response.status_code,
                        response_time_ms=response_time,
                        ip_address=request.remote_addr,
                        user_agent=request.headers.get('User-Agent', '')[:512]
                    )
                    db.session.add(api_request)
                    db.session.commit()
            except Exception as e:
                app.logger.error(f"Error saving API request: {e}")
                db.session.rollback()

        return response


def init_celery(app):
    """Initialize Celery with Flask app"""
    try:
        from celery import Celery
        
        celery = Celery(
            app.import_name,
            broker=app.config['CELERY_BROKER_URL'],
            backend=app.config['CELERY_RESULT_BACKEND']
        )
        celery.conf.update(app.config)
        
        class ContextTask(celery.Task):
            """Make celery tasks work with Flask app context"""
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)
        
        celery.Task = ContextTask
        return celery
    except ImportError:
        # Celery not available, return None
        app.logger.warning("Celery not available, background tasks disabled")
        return None


# Global registry to track initialized apps
_initialized_apps = set()

def create_app(config_name=None, register_blueprints=None):
    """
    Create and configure Flask application
    
    Args:
        config_name: Configuration name (development, production, testing)
        register_blueprints: Function to register blueprints (optional)
    
    Returns:
        Configured Flask application
    """
    app = Flask(__name__)

    # Load configuration
    config = get_config(config_name)
    app.config.from_object(config)

    # Setup logging
    setup_logging(app)

    # Import shared database instance
    from src.db.models import db as shared_db
    
    # Initialize extensions (only once per app instance)
    # Check if this specific app instance already has SQLAlchemy initialized
    app_id = id(app)
    if app_id not in _initialized_apps:
        shared_db.init_app(app)
        _initialized_apps.add(app_id)
    CORS(app, resources={r"/api/*": {"origins": app.config['CORS_ORIGINS']}})
    
    # Initialize SocketIO
    socketio = SocketIO(
        app,
        cors_allowed_origins=app.config['CORS_ORIGINS'],
        async_mode='threading',
        logger=app.debug,
        engineio_logger=app.debug
    )

    # Register middleware
    register_middleware(app)

    # Initialize Celery
    celery_app = init_celery(app)

    # Initialize services
    anc_service = ANCService()
    ml_service = MLService()

    # Create database tables (only if not already created)
    with app.app_context():
        try:
            # Test if tables exist
            shared_db.session.execute('SELECT 1')
        except:
            # Tables don't exist, create them
            init_db_models(app)
            app.logger.info("Database initialized")
        else:
            app.logger.info("Database already initialized")

    # Register blueprints if function provided
    if register_blueprints:
        register_blueprints(app, socketio, anc_service, ml_service)

    # Add helper utilities to app context
    app.anc_service = anc_service
    app.ml_service = ml_service
    app.celery_app = celery_app

    # Add common utility functions
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Endpoint not found'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        shared_db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

    return app, socketio


def register_core_blueprints(app, socketio, anc_service, ml_service):
    """Register core API blueprints"""
    
    # Import blueprints
    from src.api.routes.auth import auth_bp
    from src.api.routes.sessions import sessions_bp
    from src.api.routes.audio import audio_bp
    from src.api.routes.stats import stats_bp
    from backend.api.health import health_bp
    
    # Register blueprints with URL prefixes
    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp, url_prefix='/api/v1/auth')
    app.register_blueprint(sessions_bp, url_prefix='/api/v1/sessions')
    app.register_blueprint(audio_bp, url_prefix='/api/v1/audio')
    app.register_blueprint(stats_bp, url_prefix='/api/v1/stats')
    
    # Register SocketIO handlers
    from backend.websocket import init_socketio as init_websocket_handlers
    init_websocket_handlers(socketio)


# Utility functions for backward compatibility
def create_lightweight_app():
    """Create lightweight app with only core functionality"""
    return create_app(register_blueprints=None)[0]


def create_full_app():
    """Create full app with all blueprints and services"""
    return create_app(register_blueprints=register_core_blueprints)[0]