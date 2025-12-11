"""
Audio Sessions Routes Blueprint
Handles session creation, management, and lifecycle
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime
import logging
import uuid

# Import shared models
from src.db.models import db, AudioSession

logger = logging.getLogger(__name__)

sessions_bp = Blueprint('sessions', __name__)


def require_api_key(f):
    """API key authentication decorator"""
    @sessions_bp.before_request
    def check_auth():
        from backend.middleware.auth import verify_api_key
        from flask import current_app
        
        api_key = request.headers.get(current_app.config['API_KEY_HEADER'])
        if api_key:
            user = verify_api_key(api_key)
            if user:
                g.current_user = user
            else:
                return jsonify({'error': 'Invalid API key'}), 401
        else:
            return jsonify({'error': 'API key required'}), 401
    
    return f


@sessions_bp.route('', methods=['POST'])
@require_api_key
def create_session():
    """Create new audio processing session"""
    data = request.get_json() or {}

    # Generate unique session ID
    session_id = str(uuid.uuid4())

    session = AudioSession(
        id=session_id,
        user_id=g.current_user.id,
        session_type=data.get('session_type', 'live'),
        sample_rate=data.get('sample_rate', 48000),
        channels=data.get('channels', 1),
        chunk_size=data.get('chunk_size', 1024),
        anc_enabled=data.get('anc_enabled', True),
        anc_algorithm=data.get('anc_algorithm', 'lms'),
        anc_intensity=data.get('anc_intensity', 1.0),
        filter_length=data.get('filter_length', 256)
    )

    db.session.add(session)
    db.session.commit()

    logger.info(f"Session created: {session_id} for user {g.current_user.username}")

    return jsonify({
        'message': 'Session created',
        'session': session.to_dict()
    }), 201


@sessions_bp.route('/<session_id>', methods=['GET'])
@require_api_key
def get_session(session_id):
    """Get session details"""
    session = AudioSession.query.get(session_id)

    if not session:
        return jsonify({'error': 'Session not found'}), 404

    # Check ownership
    if session.user_id != g.current_user.id and not g.current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    return jsonify({
        'session': session.to_dict()
    }), 200


@sessions_bp.route('/<session_id>', methods=['PATCH'])
@require_api_key
def update_session(session_id):
    """Update session settings"""
    session = AudioSession.query.get(session_id)

    if not session:
        return jsonify({'error': 'Session not found'}), 404

    # Check ownership
    if session.user_id != g.current_user.id and not g.current_user.is_admin:
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

    logger.info(f"Session updated: {session_id}")

    return jsonify({
        'message': 'Session updated',
        'session': session.to_dict()
    }), 200


@sessions_bp.route('/<session_id>', methods=['DELETE'])
@require_api_key
def delete_session(session_id):
    """Delete session"""
    session = AudioSession.query.get(session_id)

    if not session:
        return jsonify({'error': 'Session not found'}), 404

    # Check ownership
    if session.user_id != g.current_user.id and not g.current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    db.session.delete(session)
    db.session.commit()

    logger.info(f"Session deleted: {session_id}")

    return jsonify({
        'message': 'Session deleted'
    }), 200


@sessions_bp.route('/<session_id>/end', methods=['POST'])
@require_api_key
def end_session(session_id):
    """End processing session"""
    session = AudioSession.query.get(session_id)

    if not session:
        return jsonify({'error': 'Session not found'}), 404

    # Check ownership
    if session.user_id != g.current_user.id and not g.current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    session.status = 'completed'
    session.ended_at = datetime.utcnow()

    db.session.commit()

    logger.info(f"Session ended: {session_id}")

    return jsonify({
        'message': 'Session ended',
        'session': session.to_dict()
    }), 200


@sessions_bp.route('', methods=['GET'])
@require_api_key
def list_sessions():
    """List user sessions with pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status')
    
    # Build query
    query = AudioSession.query.filter_by(user_id=g.current_user.id)
    
    if status:
        query = query.filter_by(status=status)
    
    sessions = query.order_by(AudioSession.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'sessions': [s.to_dict() for s in sessions.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': sessions.total,
            'pages': sessions.pages,
            'has_next': sessions.has_next,
            'has_prev': sessions.has_prev
        }
    }), 200


@sessions_bp.route('/<session_id>/metrics', methods=['GET'])
@require_api_key
def get_session_metrics(session_id):
    """Get session performance metrics"""
    session = AudioSession.query.get(session_id)

    if not session:
        return jsonify({'error': 'Session not found'}), 404

    # Check ownership
    if session.user_id != g.current_user.id and not g.current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    # Get processing metrics
    from src.db.models import ProcessingMetric
    
    metrics = ProcessingMetric.query.filter_by(session_id=session_id).order_by(
        ProcessingMetric.created_at.desc()
    ).limit(100).all()

    # Get noise detections
    from src.db.models import NoiseDetection
    
    detections = NoiseDetection.query.filter_by(session_id=session_id).order_by(
        NoiseDetection.created_at.desc()
    ).limit(50).all()

    return jsonify({
        'session': session.to_dict(),
        'processing_metrics': [m.to_dict() for m in metrics],
        'noise_detections': [d.to_dict() for d in detections],
        'summary': {
            'total_chunks_processed': session.total_chunks_processed,
            'average_latency_ms': session.average_latency_ms,
            'average_cancellation_db': session.average_cancellation_db,
            'noise_detection_count': len(detections)
        }
    }), 200