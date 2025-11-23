"""
Audio Processing API Endpoints
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import logging

from services.anc_service import ANCService
from services.ml_service import MLService
from middleware.auth import require_auth

logger = logging.getLogger(__name__)

audio_bp = Blueprint('audio', __name__)
anc_service = ANCService()
ml_service = MLService()


@audio_bp.route('/process', methods=['POST'])
@require_auth
def process_audio():
    """
    Process audio with ANC algorithm

    Request Body:
    {
        "audio_data": "base64-encoded audio",
        "sample_rate": 48000,
        "algorithm": "nlms",
        "intensity": 1.0
    }
    """
    try:
        data = request.get_json()

        if not data or 'audio_data' not in data:
            return jsonify({'error': 'Missing audio_data'}), 400

        # Process audio
        result = anc_service.process_audio(
            audio_data=data['audio_data'],
            sample_rate=data.get('sample_rate', 48000),
            algorithm=data.get('algorithm', 'nlms'),
            intensity=data.get('intensity', 1.0)
        )

        return jsonify({
            'success': True,
            'processed_audio': result['processed_audio'],
            'metrics': result['metrics'],
            'timestamp': datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        logger.error(f"Audio processing error: {e}")
        return jsonify({'error': str(e)}), 500


@audio_bp.route('/classify', methods=['POST'])
@require_auth
def classify_noise():
    """
    Classify noise type using ML model

    Request Body:
    {
        "audio_data": "base64-encoded audio",
        "sample_rate": 48000
    }
    """
    try:
        data = request.get_json()

        if not data or 'audio_data' not in data:
            return jsonify({'error': 'Missing audio_data'}), 400

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
@require_auth
def detect_emergency():
    """
    Detect emergency sounds (fire alarm, siren, etc.)

    Request Body:
    {
        "audio_data": "base64-encoded audio",
        "sample_rate": 48000
    }
    """
    try:
        data = request.get_json()

        if not data or 'audio_data' not in data:
            return jsonify({'error': 'Missing audio_data'}), 400

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
@require_auth
def list_sessions():
    """Get all audio sessions for current user"""
    try:
        # Get sessions from database
        from database.models import AudioSession
        from flask import g

        sessions = AudioSession.query.filter_by(
            user_id=g.current_user.id
        ).order_by(AudioSession.created_at.desc()).limit(50).all()

        return jsonify({
            'success': True,
            'sessions': [s.to_dict() for s in sessions],
            'count': len(sessions)
        }), 200

    except Exception as e:
        logger.error(f"Error fetching sessions: {e}")
        return jsonify({'error': str(e)}), 500


@audio_bp.route('/sessions/<session_id>', methods=['GET'])
@require_auth
def get_session(session_id):
    """Get specific audio session details"""
    try:
        from database.models import AudioSession
        from flask import g

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

    except Exception as e:
        logger.error(f"Error fetching session: {e}")
        return jsonify({'error': str(e)}), 500
