"""
Session Management API Endpoints
"""

from flask import Blueprint, request, jsonify
from middleware.auth import require_auth
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

sessions_bp = Blueprint('sessions', __name__)


@sessions_bp.route('/', methods=['POST'])
@require_auth
def create_session():
    """Create new audio processing session"""
    try:
        from flask import g
        from config.database import db
        from database.models import AudioSession

        data = request.get_json() or {}

        # Create new session
        session = AudioSession(
            user_id=g.current_user.id,
            session_type=data.get('session_type', 'live'),
            sample_rate=data.get('sample_rate', 48000),
            channels=data.get('channels', 1),
            anc_enabled=data.get('anc_enabled', True),
            anc_algorithm=data.get('anc_algorithm', 'nlms'),
            anc_intensity=data.get('anc_intensity', 1.0)
        )

        db.session.add(session)
        db.session.commit()

        return jsonify({
            'success': True,
            'session': session.to_dict()
        }), 201

    except Exception as e:
        logger.error(f"Error creating session: {e}")
        return jsonify({'error': str(e)}), 500


@sessions_bp.route('/<session_id>', methods=['PUT'])
@require_auth
def update_session(session_id):
    """Update existing session"""
    try:
        from flask import g
        from config.database import db
        from database.models import AudioSession

        session = AudioSession.query.filter_by(
            id=session_id,
            user_id=g.current_user.id
        ).first()

        if not session:
            return jsonify({'error': 'Session not found'}), 404

        data = request.get_json() or {}

        # Update fields
        if 'status' in data:
            session.status = data['status']
        if 'anc_enabled' in data:
            session.anc_enabled = data['anc_enabled']
        if 'anc_intensity' in data:
            session.anc_intensity = data['anc_intensity']

        db.session.commit()

        return jsonify({
            'success': True,
            'session': session.to_dict()
        }), 200

    except Exception as e:
        logger.error(f"Error updating session: {e}")
        return jsonify({'error': str(e)}), 500


@sessions_bp.route('/<session_id>/metrics', methods=['GET'])
@require_auth
def get_session_metrics(session_id):
    """Get metrics for a specific session"""
    try:
        from flask import g
        from database.models import AudioSession, ProcessingMetric

        session = AudioSession.query.filter_by(
            id=session_id,
            user_id=g.current_user.id
        ).first()

        if not session:
            return jsonify({'error': 'Session not found'}), 404

        metrics = ProcessingMetric.query.filter_by(
            session_id=session_id
        ).all()

        return jsonify({
            'success': True,
            'session_id': session_id,
            'metrics': [m.to_dict() for m in metrics],
            'count': len(metrics)
        }), 200

    except Exception as e:
        logger.error(f"Error fetching metrics: {e}")
        return jsonify({'error': str(e)}), 500
