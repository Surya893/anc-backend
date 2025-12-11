"""
User Management API Endpoints
"""

from flask import Blueprint, request, jsonify, g
from backend.middleware.auth import require_auth
import logging
from src.db.models import db

logger = logging.getLogger(__name__)

users_bp = Blueprint('users', __name__)


@users_bp.route('/me', methods=['GET'])
@require_auth
def get_current_user():
    """Get current authenticated user"""
    try:
        from flask import g
        return jsonify({
            'success': True,
            'user': g.current_user.to_dict()
        }), 200

    except Exception as e:
        logger.error(f"Error fetching user: {e}")
        return jsonify({'error': str(e)}), 500


@users_bp.route('/api-key', methods=['POST'])
@require_auth
def regenerate_api_key():
    """Regenerate API key for current user"""
    try:
        from flask import g
        from config.database import db

        new_key = g.current_user.generate_api_key()
        db.session.commit()

        return jsonify({
            'success': True,
            'api_key': new_key
        }), 200

    except Exception as e:
        logger.error(f"Error regenerating API key: {e}")
        return jsonify({'error': str(e)}), 500
