"""
REST API Server for ANC Platform
Comprehensive API with authentication, rate limiting, and monitoring
"""

from flask import Flask, request, jsonify, make_response, render_template
from flask_cors import CORS
from functools import wraps
import jwt
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any
import os

# Import ANC components
from main import ANCSystemCore
from advanced_anc_algorithms import AdvancedANCSystem
from database_schema import ANCDatabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['JSON_SORT_KEYS'] = False

# Enable CORS
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Global ANC system instance
anc_system = None
advanced_anc = None
db = ANCDatabase()

# Rate limiting
rate_limit_storage = {}


def rate_limit(max_per_minute=60):
    """Rate limiting decorator."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = request.remote_addr
            now = time.time()

            # Clean old entries
            rate_limit_storage[client_ip] = [
                t for t in rate_limit_storage.get(client_ip, [])
                if now - t < 60
            ]

            # Check rate limit
            if len(rate_limit_storage.get(client_ip, [])) >= max_per_minute:
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Maximum {max_per_minute} requests per minute'
                }), 429

            # Add current request
            if client_ip not in rate_limit_storage:
                rate_limit_storage[client_ip] = []
            rate_limit_storage[client_ip].append(now)

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_api_key(f):
    """API key authentication decorator."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')

        # In production, validate against database
        valid_api_keys = os.environ.get('API_KEYS', 'dev-api-key').split(',')

        if not api_key or api_key not in valid_api_keys:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Valid API key required'
            }), 401

        return f(*args, **kwargs)
    return decorated_function


def create_token(user_id: str, expiry_hours: int = 24) -> str:
    """Create JWT token."""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=expiry_hours),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')


def verify_token(token: str) -> Dict[str, Any]:
    """Verify JWT token."""
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        return {'valid': True, 'payload': payload}
    except jwt.ExpiredSignatureError:
        return {'valid': False, 'error': 'Token expired'}
    except jwt.InvalidTokenError:
        return {'valid': False, 'error': 'Invalid token'}


# ==================================================================================
# HEALTH & STATUS ENDPOINTS
# ==================================================================================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for load balancers."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    }), 200


@app.route('/ready', methods=['GET'])
def readiness_check():
    """Readiness check endpoint."""
    # Check if system is ready
    ready = anc_system is not None

    return jsonify({
        'ready': ready,
        'timestamp': datetime.utcnow().isoformat()
    }), 200 if ready else 503


@app.route('/metrics', methods=['GET'])
def metrics():
    """Prometheus-compatible metrics endpoint."""
    metrics_text = f"""
# HELP anc_requests_total Total number of API requests
# TYPE anc_requests_total counter
anc_requests_total {sum(len(v) for v in rate_limit_storage.values())}

# HELP anc_system_status ANC system status (1=enabled, 0=disabled)
# TYPE anc_system_status gauge
anc_system_status {1 if anc_system and anc_system.anc_enabled else 0}

# HELP anc_detections_total Total number of noise detections
# TYPE anc_detections_total counter
anc_detections_total {anc_system.stats['total_detections'] if anc_system else 0}

# HELP anc_emergencies_total Total number of emergency detections
# TYPE anc_emergencies_total counter
anc_emergencies_total {anc_system.stats['emergency_count'] if anc_system else 0}
"""
    return make_response(metrics_text, 200, {'Content-Type': 'text/plain'})


# ==================================================================================
# AUTHENTICATION ENDPOINTS
# ==================================================================================

@app.route('/api/v1/auth/token', methods=['POST'])
@rate_limit(max_per_minute=10)
def get_token():
    """Get JWT token for API access."""
    data = request.get_json()

    # In production, validate credentials against database
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400

    # Mock authentication (replace with real auth)
    if username == 'demo' and password == 'demo':
        token = create_token(username)
        return jsonify({
            'token': token,
            'expires_in': 86400,  # 24 hours
            'token_type': 'Bearer'
        }), 200

    return jsonify({'error': 'Invalid credentials'}), 401


# ==================================================================================
# ANC CONTROL ENDPOINTS
# ==================================================================================

@app.route('/api/v1/anc/initialize', methods=['POST'])
@require_api_key
@rate_limit(max_per_minute=10)
def initialize_anc():
    """Initialize ANC system."""
    global anc_system, advanced_anc

    data = request.get_json() or {}

    try:
        # Initialize core system
        anc_system = ANCSystemCore(
            sample_rate=data.get('sample_rate', 44100),
            chunk_size=data.get('chunk_size', 1024)
        )

        # Initialize advanced algorithms
        advanced_anc = AdvancedANCSystem(
            sample_rate=data.get('sample_rate', 44100),
            algorithm=data.get('algorithm', 'nlms'),
            filter_length=data.get('filter_length', 512),
            use_adaptive_gain=data.get('use_adaptive_gain', True)
        )

        logger.info("ANC system initialized")

        return jsonify({
            'status': 'initialized',
            'config': {
                'sample_rate': anc_system.sample_rate,
                'chunk_size': anc_system.chunk_size,
                'algorithm': data.get('algorithm', 'nlms')
            }
        }), 200

    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/anc/status', methods=['GET'])
@rate_limit(max_per_minute=120)
def get_anc_status():
    """Get ANC system status."""
    if not anc_system:
        return jsonify({'error': 'System not initialized'}), 503

    state = anc_system.get_state()

    # Add advanced algorithm performance
    if advanced_anc:
        performance = advanced_anc.get_performance_summary()
        state['performance'] = performance

    return jsonify(state), 200


@app.route('/api/v1/anc/enable', methods=['POST'])
@require_api_key
@rate_limit(max_per_minute=60)
def enable_anc():
    """Enable ANC."""
    if not anc_system:
        return jsonify({'error': 'System not initialized'}), 503

    anc_system.set_anc_enabled(True)
    logger.info("ANC enabled")

    return jsonify({
        'status': 'enabled',
        'timestamp': datetime.utcnow().isoformat()
    }), 200


@app.route('/api/v1/anc/disable', methods=['POST'])
@require_api_key
@rate_limit(max_per_minute=60)
def disable_anc():
    """Disable ANC."""
    if not anc_system:
        return jsonify({'error': 'System not initialized'}), 503

    anc_system.set_anc_enabled(False)
    logger.info("ANC disabled")

    return jsonify({
        'status': 'disabled',
        'timestamp': datetime.utcnow().isoformat()
    }), 200


@app.route('/api/v1/anc/intensity', methods=['POST'])
@require_api_key
@rate_limit(max_per_minute=60)
def set_intensity():
    """Set ANC intensity."""
    if not anc_system:
        return jsonify({'error': 'System not initialized'}), 503

    data = request.get_json()
    intensity = data.get('intensity')

    if intensity is None or not (0 <= intensity <= 1):
        return jsonify({'error': 'Intensity must be between 0 and 1'}), 400

    anc_system.set_noise_intensity(intensity)
    logger.info(f"Intensity set to {intensity}")

    return jsonify({
        'intensity': intensity,
        'timestamp': datetime.utcnow().isoformat()
    }), 200


# ==================================================================================
# AUDIO PROCESSING ENDPOINTS
# ==================================================================================

@app.route('/api/v1/audio/process', methods=['POST'])
@require_api_key
@rate_limit(max_per_minute=30)
def process_audio():
    """Process audio through ANC system."""
    if not advanced_anc:
        return jsonify({'error': 'Advanced ANC not initialized'}), 503

    # Expecting base64-encoded audio data
    data = request.get_json()

    # In production, decode and process actual audio
    # For now, return mock response

    return jsonify({
        'status': 'processed',
        'metrics': {
            'cancellation_db': 35.5,
            'snr_improvement_db': 28.3,
            'processing_time_ms': 12.5
        }
    }), 200


@app.route('/api/v1/audio/analyze', methods=['POST'])
@require_api_key
@rate_limit(max_per_minute=30)
def analyze_audio():
    """Analyze audio and return features."""
    if not anc_system:
        return jsonify({'error': 'System not initialized'}), 503

    # Mock analysis
    return jsonify({
        'noise_class': 'office',
        'confidence': 0.87,
        'intensity_db': 68.5,
        'frequency_spectrum': [],
        'features': {
            'mfcc_mean': [0.1, 0.2, 0.3],
            'spectral_centroid': 2500.5,
            'zcr': 0.15
        }
    }), 200


# ==================================================================================
# MODEL MANAGEMENT ENDPOINTS
# ==================================================================================

@app.route('/api/v1/models', methods=['GET'])
@rate_limit(max_per_minute=60)
def list_models():
    """List available models."""
    return jsonify({
        'models': [
            {
                'id': 'noise_classifier_v1',
                'type': 'classification',
                'accuracy': 0.9583,
                'classes': ['traffic', 'office', 'construction', 'nature', 'music', 'conversation']
            },
            {
                'id': 'emergency_detector_v1',
                'type': 'emergency_detection',
                'accuracy': 1.0,
                'classes': ['alarm', 'siren']
            }
        ]
    }), 200


@app.route('/api/v1/models/<model_id>/predict', methods=['POST'])
@require_api_key
@rate_limit(max_per_minute=60)
def predict_with_model(model_id):
    """Make prediction with specific model."""
    # Mock prediction
    return jsonify({
        'model_id': model_id,
        'prediction': 'office',
        'confidence': 0.87,
        'probabilities': {
            'office': 0.87,
            'traffic': 0.08,
            'construction': 0.03,
            'nature': 0.01,
            'music': 0.01,
            'conversation': 0.00
        }
    }), 200


# ==================================================================================
# STATISTICS & ANALYTICS ENDPOINTS
# ==================================================================================

@app.route('/api/v1/stats/summary', methods=['GET'])
@rate_limit(max_per_minute=60)
def get_stats_summary():
    """Get statistics summary."""
    if not anc_system:
        return jsonify({'error': 'System not initialized'}), 503

    return jsonify({
        'total_detections': anc_system.stats['total_detections'],
        'emergency_count': anc_system.stats['emergency_count'],
        'uptime_seconds': anc_system.stats.get('anc_active_time', 0),
        'current_status': {
            'anc_enabled': anc_system.anc_enabled,
            'noise_class': anc_system.current_noise_class,
            'confidence': anc_system.current_confidence
        }
    }), 200


@app.route('/api/v1/stats/performance', methods=['GET'])
@rate_limit(max_per_minute=60)
def get_performance_stats():
    """Get performance statistics."""
    if not advanced_anc:
        return jsonify({'error': 'Advanced ANC not initialized'}), 503

    performance = advanced_anc.get_performance_summary()

    return jsonify(performance), 200


# ==================================================================================
# DOCUMENTATION ENDPOINTS
# ==================================================================================

@app.route('/api/v1/docs', methods=['GET'])
def api_docs():
    """Get API documentation."""
    return jsonify({
        'version': '1.0.0',
        'base_url': request.host_url + 'api/v1',
        'authentication': 'API Key (X-API-Key header)',
        'rate_limit': '60 requests per minute',
        'endpoints': {
            'authentication': [
                {'method': 'POST', 'path': '/auth/token', 'description': 'Get JWT token'}
            ],
            'anc_control': [
                {'method': 'POST', 'path': '/anc/initialize', 'description': 'Initialize system'},
                {'method': 'GET', 'path': '/anc/status', 'description': 'Get system status'},
                {'method': 'POST', 'path': '/anc/enable', 'description': 'Enable ANC'},
                {'method': 'POST', 'path': '/anc/disable', 'description': 'Disable ANC'},
                {'method': 'POST', 'path': '/anc/intensity', 'description': 'Set intensity'}
            ],
            'audio_processing': [
                {'method': 'POST', 'path': '/audio/process', 'description': 'Process audio'},
                {'method': 'POST', 'path': '/audio/analyze', 'description': 'Analyze audio'}
            ],
            'models': [
                {'method': 'GET', 'path': '/models', 'description': 'List models'},
                {'method': 'POST', 'path': '/models/{id}/predict', 'description': 'Predict'}
            ],
            'statistics': [
                {'method': 'GET', 'path': '/stats/summary', 'description': 'Get statistics'},
                {'method': 'GET', 'path': '/stats/performance', 'description': 'Get performance'}
            ]
        }
    }), 200


@app.route('/', methods=['GET'])
def index():
    """Web UI homepage."""
    # Check if client wants JSON (API access)
    if request.headers.get('Accept') == 'application/json':
        return jsonify({
            'name': 'ANC Platform API',
            'version': '1.0.0',
            'documentation': request.host_url + 'api/v1/docs',
            'health': request.host_url + 'health',
            'status': 'operational'
        }), 200
    # Otherwise serve the web UI
    return render_template('index.html')


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {error}")
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'

    logger.info(f"Starting API server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug, threaded=True)
