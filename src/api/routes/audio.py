"""
Audio Processing Routes Blueprint  
Handles audio processing, noise classification, and emergency detection
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime
import logging
import base64
import numpy as np
import uuid

# Import shared models
from src.db.models import db, AudioSession, NoiseDetection, ProcessingMetric

logger = logging.getLogger(__name__)

audio_bp = Blueprint('audio', __name__)


def require_api_key(f):
    """API key authentication decorator"""
    @audio_bp.before_request
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


@audio_bp.route('/process', methods=['POST'])
@require_api_key
def process_audio():
    """Process audio data (synchronous)"""
    from flask import current_app
    
    data = request.get_json()

    if not data or 'audio_data' not in data or 'session_id' not in data:
        return jsonify({'error': 'audio_data and session_id required'}), 400

    session_id = data['session_id']
    audio_b64 = data['audio_data']

    # Verify session ownership
    session = AudioSession.query.get(session_id)
    if not session or (session.user_id != g.current_user.id and not g.current_user.is_admin):
        return jsonify({'error': 'Invalid session'}), 403

    try:
        # Decode audio
        audio_bytes = base64.b64decode(audio_b64)
        audio_array = np.frombuffer(audio_bytes, dtype='float32')

        # Get ANC service from app context
        anc_service = current_app.anc_service
        
        # Process audio
        result = anc_service.process_audio(
            audio_data=audio_b64,
            sample_rate=session.sample_rate,
            algorithm=session.anc_algorithm,
            intensity=session.anc_intensity
        )

        # Store detection if classified
        if result.get('noise_detection'):
            detection = NoiseDetection(
                session_id=session_id,
                noise_type=result['noise_detection'].get('type'),
                confidence=result['noise_detection'].get('confidence', 0.0),
                is_emergency=result['noise_detection'].get('is_emergency', False),
                intensity_db=result['features'].get('rms'),
                audio_features=str(result['features'])
            )
            db.session.add(detection)

        # Store metric
        if result.get('performance'):
            metric = ProcessingMetric(
                session_id=session_id,
                latency_ms=result['performance'].get('latency_ms', 0.0),
                cancellation_db=result['anc_metrics'].get('cancellation_db'),
                snr_improvement_db=result['anc_metrics'].get('snr_improvement_db')
            )
            db.session.add(metric)

        # Update session
        session.total_chunks_processed += 1
        if result.get('performance', {}).get('latency_ms'):
            session.update_averages(
                result['performance']['latency_ms'],
                result.get('anc_metrics', {}).get('cancellation_db', 0.0),
                session.total_chunks_processed
            )

        db.session.commit()

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error processing audio: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@audio_bp.route('/process-file', methods=['POST'])
@require_api_key
def process_audio_file():
    """Process audio file (asynchronous)"""
    from flask import current_app
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Save file
    upload_dir = current_app.config['UPLOAD_DIR']
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / file.filename
    file.save(str(file_path))

    # Create session
    session_id = str(uuid.uuid4())
    session = AudioSession(
        id=session_id,
        user_id=g.current_user.id,
        session_type='batch',
        anc_enabled=request.form.get('anc_enabled', 'true').lower() == 'true'
    )
    db.session.add(session)
    db.session.commit()

    # Queue background task
    celery_app = current_app.celery_app
    task = celery_app.send_task(
        'process_audio_file',
        args=[str(file_path), session_id, g.current_user.id],
        kwargs={
            'anc_enabled': session.anc_enabled,
            'anc_algorithm': request.form.get('anc_algorithm', 'nlms')
        }
    )

    logger.info(f"File processing queued: {file.filename} -> {session_id}")

    return jsonify({
        'message': 'File processing started',
        'session_id': session_id,
        'task_id': task.id,
        'file_path': str(file_path)
    }), 202


@audio_bp.route('/classify', methods=['POST'])
@require_api_key
def classify_noise():
    """Classify noise type using ML model"""
    from flask import current_app
    
    data = request.get_json()

    if not data or 'audio_data' not in data:
        return jsonify({'error': 'audio_data required'}), 400

    try:
        # Get ML service from app context
        ml_service = current_app.ml_service
        
        # Classify noise
        result = ml_service.classify_noise(
            audio_data=data['audio_data'],
            sample_rate=data.get('sample_rate', 48000)
        )

        return jsonify({
            'success': True,
            'noise_type': result['noise_type'],
            'confidence': result['confidence'],
            'all_predictions': result['all_predictions'],
            'timestamp': datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        logger.error(f"Classification error: {e}")
        return jsonify({'error': str(e)}), 500


@audio_bp.route('/emergency-detect', methods=['POST'])
@require_api_key
def detect_emergency():
    """Detect emergency sounds (fire alarm, siren, etc.)"""
    from flask import current_app
    
    data = request.get_json()

    if not data or 'audio_data' not in data:
        return jsonify({'error': 'audio_data required'}), 400

    try:
        # Get ML service from app context
        ml_service = current_app.ml_service
        
        # Detect emergency
        result = ml_service.detect_emergency(
            audio_data=data['audio_data'],
            sample_rate=data.get('sample_rate', 48000)
        )

        return jsonify({
            'success': True,
            'is_emergency': result['is_emergency'],
            'emergency_type': result.get('emergency_type'),
            'confidence': result['confidence'],
            'timestamp': datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        logger.error(f"Emergency detection error: {e}")
        return jsonify({'error': str(e)}), 500


@audio_bp.route('/sessions', methods=['GET'])
@require_api_key
def list_sessions():
    """Get all audio sessions for current user"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    sessions = AudioSession.query.filter_by(
        user_id=g.current_user.id
    ).order_by(AudioSession.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'success': True,
        'sessions': [s.to_dict() for s in sessions.items],
        'count': len(sessions.items),
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': sessions.total,
            'pages': sessions.pages
        }
    }), 200


@audio_bp.route('/sessions/<session_id>', methods=['GET'])
@require_api_key
def get_session(session_id):
    """Get specific audio session details"""
    session = AudioSession.query.filter_by(
        id=session_id,
        user_id=g.current_user.id
    ).first()

    if not session:
        return jsonify({'error': 'Session not found'}), 404

    return jsonify({
        'success': True,
        'session': session.to_dict()
    }), 200