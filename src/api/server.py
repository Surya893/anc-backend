"""
Comprehensive ANC Platform API Server
Integrates all components: REST API, WebSocket, Database, Background Tasks
"""

from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
import jwt
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
import os
import sys
from pathlib import Path
import time

# Ensure src is in path for imports
import sys
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Import configurations and models
from config import get_config
from models import db, User, AudioSession, NoiseDetection, ProcessingMetric, APIRequest
from websocket_server import socketio, init_background_tasks
from websocket_streaming import register_streaming_handlers
from audio_processor import audio_processor
from celery_app import celery_app
from api.tasks import (  # Import all tasks to register them with Celery
    process_audio_file,
    batch_process_files,
    train_noise_classifier,
    analyze_session_data,
    generate_daily_report,
    cleanup_old_sessions
)

# Configure logging
def setup_logging(app):
    """Setup application logging"""
    if not app.debug:
        if not app.config['LOG_DIR'].exists():
            app.config['LOG_DIR'].mkdir(parents=True, exist_ok=True)

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


def create_app(config_name=None):
    """Application factory"""
    app = Flask(__name__)

    # Load configuration
    config = get_config(config_name)
    app.config.from_object(config)

    # Setup logging
    setup_logging(app)

    # Initialize extensions
    db.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": app.config['CORS_ORIGINS']}})
    socketio.init_app(app)

    # Register real-time streaming handlers
    register_streaming_handlers(socketio)

    # Initialize Celery
    celery_app.conf.update(app.config)

    # Create database tables
    with app.app_context():
        db.create_all()
        app.logger.info("Database initialized")

    # Initialize WebSocket background tasks
    with app.app_context():
        init_background_tasks()

    return app


app = create_app()
logger = app.logger


# ============================================================================
# AUTHENTICATION & MIDDLEWARE
# ============================================================================

def require_api_key(f):
    """API key authentication decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get(app.config['API_KEY_HEADER'])

        if not api_key:
            return jsonify({'error': 'API key required'}), 401

        user = User.query.filter_by(api_key=api_key, is_active=True).first()
        if not user:
            return jsonify({'error': 'Invalid API key'}), 401

        request.current_user = user
        return f(*args, **kwargs)

    return decorated_function


def require_jwt(f):
    """JWT token authentication decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')

        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'JWT token required'}), 401

        token = auth_header.split(' ')[1]

        try:
            payload = jwt.decode(
                token,
                app.config['JWT_SECRET_KEY'],
                algorithms=['HS256']
            )
            user_id = payload.get('user_id')
            user = User.query.get(user_id)

            if not user or not user.is_active:
                return jsonify({'error': 'Invalid token'}), 401

            request.current_user = user
            return f(*args, **kwargs)

        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401

    return decorated_function


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
        logger.info(
            f"{request.method} {request.path} - {response.status_code} - {response_time:.2f}ms"
        )

        # Save to database (async)
        if hasattr(request, 'current_user'):
            try:
                api_request = APIRequest(
                    user_id=request.current_user.id,
                    method=request.method,
                    endpoint=request.path,
                    status_code=response.status_code,
                    response_time_ms=response_time,
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent', '')[:255]
                )
                db.session.add(api_request)
                db.session.commit()
            except Exception as e:
                logger.error(f"Error saving API request: {e}")
                db.session.rollback()

    return response


# ============================================================================
# ROUTES - AUTHENTICATION
# ============================================================================

@app.route('/api/v1/auth/register', methods=['POST'])
def register():
    """Register new user"""
    data = request.get_json()

    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Username and password required'}), 400

    # Check if user exists
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 409

    if User.query.filter_by(email=data.get('email', '')).first():
        return jsonify({'error': 'Email already exists'}), 409

    # Create user
    user = User(
        username=data['username'],
        email=data.get('email', '')
    )
    user.set_password(data['password'])
    user.generate_api_key()

    db.session.add(user)
    db.session.commit()

    logger.info(f"New user registered: {user.username}")

    return jsonify({
        'message': 'User created successfully',
        'user': user.to_dict(),
        'api_key': user.api_key
    }), 201


@app.route('/api/v1/auth/login', methods=['POST'])
def login():
    """User login - returns JWT token"""
    data = request.get_json()

    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Username and password required'}), 400

    user = User.query.filter_by(username=data['username']).first()

    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401

    if not user.is_active:
        return jsonify({'error': 'Account disabled'}), 403

    # Generate JWT token
    token = jwt.encode(
        {
            'user_id': user.id,
            'exp': datetime.utcnow() + app.config['JWT_ACCESS_TOKEN_EXPIRES'],
            'iat': datetime.utcnow()
        },
        app.config['JWT_SECRET_KEY'],
        algorithm='HS256'
    )

    logger.info(f"User logged in: {user.username}")

    return jsonify({
        'token': token,
        'user': user.to_dict(),
        'expires_in': int(app.config['JWT_ACCESS_TOKEN_EXPIRES'].total_seconds())
    }), 200


@app.route('/api/v1/auth/refresh-api-key', methods=['POST'])
@require_jwt
def refresh_api_key():
    """Refresh user's API key"""
    user = request.current_user
    old_key = user.api_key

    user.generate_api_key()
    db.session.commit()

    logger.info(f"API key refreshed for user: {user.username}")

    return jsonify({
        'message': 'API key refreshed',
        'api_key': user.api_key
    }), 200


# ============================================================================
# ROUTES - ANC CONTROL
# ============================================================================

@app.route('/api/v1/sessions', methods=['POST'])
@require_api_key
def create_session():
    """Create new audio processing session"""
    data = request.get_json() or {}

    session = AudioSession(
        user_id=request.current_user.id,
        session_type=data.get('session_type', 'live'),
        sample_rate=data.get('sample_rate', app.config['AUDIO_SAMPLE_RATE']),
        channels=data.get('channels', app.config['AUDIO_CHANNELS']),
        chunk_size=data.get('chunk_size', app.config['AUDIO_CHUNK_SIZE']),
        anc_enabled=data.get('anc_enabled', True),
        anc_algorithm=data.get('anc_algorithm', 'lms'),
        anc_intensity=data.get('anc_intensity', 1.0),
        filter_length=data.get('filter_length', app.config['ANC_FILTER_LENGTH'])
    )

    db.session.add(session)
    db.session.commit()

    # Create audio processor session
    audio_processor.create_session(session.id, {
        'anc_enabled': session.anc_enabled,
        'anc_intensity': session.anc_intensity,
        'anc_algorithm': session.anc_algorithm
    })

    logger.info(f"Session created: {session.id} for user {request.current_user.username}")

    return jsonify({
        'message': 'Session created',
        'session': session.to_dict()
    }), 201


@app.route('/api/v1/sessions/<session_id>', methods=['GET'])
@require_api_key
def get_session(session_id):
    """Get session details"""
    session = AudioSession.query.get_or_404(session_id)

    # Check ownership
    if session.user_id != request.current_user.id and not request.current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    return jsonify({'session': session.to_dict()}), 200


@app.route('/api/v1/sessions/<session_id>', methods=['PATCH'])
@require_api_key
def update_session(session_id):
    """Update session settings"""
    session = AudioSession.query.get_or_404(session_id)

    # Check ownership
    if session.user_id != request.current_user.id and not request.current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json() or {}

    # Update fields
    if 'anc_enabled' in data:
        session.anc_enabled = data['anc_enabled']

    if 'anc_intensity' in data:
        session.anc_intensity = max(0.0, min(1.0, data['anc_intensity']))

    if 'anc_algorithm' in data:
        session.anc_algorithm = data['anc_algorithm']

    if 'status' in data:
        session.status = data['status']

    db.session.commit()

    # Update processor session
    processor_session = audio_processor.get_session(session_id)
    if processor_session:
        if 'anc_enabled' in data:
            processor_session.enable_anc(data['anc_enabled'])
        if 'anc_intensity' in data:
            processor_session.set_intensity(data['anc_intensity'])
        if 'anc_algorithm' in data:
            processor_session.set_algorithm(data['anc_algorithm'])

    logger.info(f"Session updated: {session_id}")

    return jsonify({
        'message': 'Session updated',
        'session': session.to_dict()
    }), 200


@app.route('/api/v1/sessions/<session_id>/end', methods=['POST'])
@require_api_key
def end_session(session_id):
    """End processing session"""
    session = AudioSession.query.get_or_404(session_id)

    # Check ownership
    if session.user_id != request.current_user.id and not request.current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    session.status = 'completed'
    session.ended_at = datetime.utcnow()

    db.session.commit()

    # End processor session
    audio_processor.end_session(session_id)

    logger.info(f"Session ended: {session_id}")

    return jsonify({
        'message': 'Session ended',
        'session': session.to_dict()
    }), 200


# ============================================================================
# ROUTES - AUDIO PROCESSING
# ============================================================================

@app.route('/api/v1/audio/process', methods=['POST'])
@require_api_key
def process_audio():
    """Process audio data (synchronous)"""
    import numpy as np
    import base64

    data = request.get_json()

    if not data or 'audio_data' not in data or 'session_id' not in data:
        return jsonify({'error': 'audio_data and session_id required'}), 400

    session_id = data['session_id']
    audio_b64 = data['audio_data']

    # Verify session ownership
    session = AudioSession.query.get(session_id)
    if not session or (session.user_id != request.current_user.id and not request.current_user.is_admin):
        return jsonify({'error': 'Invalid session'}), 403

    try:
        # Decode audio
        audio_bytes = base64.b64decode(audio_b64)
        audio_array = np.frombuffer(audio_bytes, dtype='float32')

        # Process
        import asyncio
        result = asyncio.run(audio_processor.process_audio_chunk(
            session_id=session_id,
            audio_data=audio_array,
            apply_anc=session.anc_enabled
        ))

        # Store detection if classified
        if result['noise_detection']['type']:
            detection = NoiseDetection(
                session_id=session_id,
                noise_type=result['noise_detection']['type'],
                confidence=result['noise_detection']['confidence'],
                is_emergency=result['noise_detection']['is_emergency'],
                intensity_db=result['features']['rms'],
                audio_features=result['features']
            )
            db.session.add(detection)

        # Store metric
        metric = ProcessingMetric(
            session_id=session_id,
            latency_ms=result['performance']['latency_ms'],
            cancellation_db=result['anc_metrics']['cancellation_db'],
            snr_improvement_db=result['anc_metrics']['snr_improvement_db']
        )
        db.session.add(metric)

        # Update session
        session.total_chunks_processed += 1
        session.average_latency_ms = (
            (session.average_latency_ms * (session.total_chunks_processed - 1) +
             result['performance']['latency_ms']) / session.total_chunks_processed
        )
        session.average_cancellation_db = (
            (session.average_cancellation_db * (session.total_chunks_processed - 1) +
             result['anc_metrics']['cancellation_db']) / session.total_chunks_processed
        )

        db.session.commit()

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error processing audio: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/audio/process-file', methods=['POST'])
@require_api_key
def process_audio_file():
    """Process audio file (asynchronous)"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Save file
    upload_dir = app.config['UPLOAD_DIR']
    file_path = upload_dir / file.filename
    file.save(file_path)

    # Create session
    session = AudioSession(
        user_id=request.current_user.id,
        session_type='batch',
        anc_enabled=request.form.get('anc_enabled', 'true').lower() == 'true'
    )
    db.session.add(session)
    db.session.commit()

    # Queue background task
    from tasks import process_audio_file as process_task
    task = process_task.delay(str(file_path), session.id, session.anc_enabled)

    logger.info(f"Queued file processing task: {task.id}")

    return jsonify({
        'message': 'File processing queued',
        'task_id': task.id,
        'session_id': session.id
    }), 202


# ============================================================================
# ROUTES - STATISTICS & MONITORING
# ============================================================================

@app.route('/api/v1/stats/sessions', methods=['GET'])
@require_api_key
def get_session_stats():
    """Get user's session statistics"""
    user_id = request.current_user.id

    sessions = AudioSession.query.filter_by(user_id=user_id).all()

    total_sessions = len(sessions)
    total_chunks = sum(s.total_chunks_processed for s in sessions)
    avg_cancellation = (
        sum(s.average_cancellation_db for s in sessions) / total_sessions
        if total_sessions > 0 else 0.0
    )

    return jsonify({
        'total_sessions': total_sessions,
        'total_chunks_processed': total_chunks,
        'average_cancellation_db': avg_cancellation,
        'recent_sessions': [s.to_dict() for s in sessions[-10:]]
    }), 200


@app.route('/api/v1/stats/detections', methods=['GET'])
@require_api_key
def get_detection_stats():
    """Get noise detection statistics"""
    user_sessions = AudioSession.query.filter_by(user_id=request.current_user.id).all()
    session_ids = [s.id for s in user_sessions]

    detections = NoiseDetection.query.filter(
        NoiseDetection.session_id.in_(session_ids)
    ).all()

    # Count by type
    type_counts = {}
    for detection in detections:
        noise_type = detection.noise_type
        if noise_type not in type_counts:
            type_counts[noise_type] = 0
        type_counts[noise_type] += 1

    emergency_count = sum(1 for d in detections if d.is_emergency)

    return jsonify({
        'total_detections': len(detections),
        'emergency_detections': emergency_count,
        'by_type': type_counts,
        'recent_detections': [d.to_dict() for d in detections[-20:]]
    }), 200


# ============================================================================
# ROUTES - GENERAL
# ============================================================================

@app.route('/')
def index():
    """Homepage - serve web UI"""
    return render_template('index.html')


@app.route('/demo')
def demo():
    """Standalone premium demo page"""
    return send_from_directory('.', 'demo-premium.html')


@app.route('/live')
def live_demo():
    """Live demo with real backend integration"""
    return render_template('live-demo.html')


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': app.config['APP_VERSION']
    }), 200


@app.route('/api/v1/info')
def api_info():
    """API information"""
    return jsonify({
        'name': app.config['APP_NAME'],
        'version': app.config['APP_VERSION'],
        'endpoints': {
            'auth': ['/api/v1/auth/register', '/api/v1/auth/login'],
            'sessions': ['/api/v1/sessions'],
            'audio': ['/api/v1/audio/process', '/api/v1/audio/process-file'],
            'stats': ['/api/v1/stats/sessions', '/api/v1/stats/detections']
        }
    }), 200


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {error}")
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500


# ============================================================================
# CLI COMMANDS
# ============================================================================

@app.cli.command()
def init_db():
    """Initialize database"""
    db.create_all()
    print("Database initialized")


@app.cli.command()
def create_admin():
    """Create admin user"""
    admin = User(
        username='admin',
        email='admin@ancplatform.com',
        is_admin=True
    )
    admin.set_password('admin123')  # Change in production!
    admin.generate_api_key()

    db.session.add(admin)
    db.session.commit()

    print(f"Admin user created")
    print(f"Username: admin")
    print(f"Password: admin123")
    print(f"API Key: {admin.api_key}")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'

    logger.info(f"Starting ANC Platform on port {port} (debug={debug})")

    socketio.run(
        app,
        host='0.0.0.0',
        port=port,
        debug=debug,
        use_reloader=debug
    )
