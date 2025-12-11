"""
Authentication Routes Blueprint
Handles user registration, login, API key management, and JWT tokens
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime, timedelta
import jwt
import logging
import secrets

# Import shared models
from src.db.models import db, User

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)


def require_api_key(f):
    """API key authentication decorator"""
    @auth_bp.before_request
    def check_api_key():
        from backend.middleware.auth import verify_api_key
        from flask import current_app
        
        api_key = request.headers.get(current_app.config['API_KEY_HEADER'])
        if api_key:
            user = verify_api_key(api_key)
            if user:
                g.current_user = user
    
    return f


def require_jwt(f):
    """JWT token authentication decorator"""
    @auth_bp.before_request  
    def check_jwt():
        from backend.middleware.auth import verify_jwt_token
        from flask import current_app
        
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            user = verify_jwt_token(token)
            if user:
                g.current_user = user
    
    return f


@auth_bp.route('/register', methods=['POST'])
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


@auth_bp.route('/login', methods=['POST'])
def login():
    """User login - returns JWT token"""
    from flask import current_app
    
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
            'exp': datetime.utcnow() + current_app.config['JWT_ACCESS_TOKEN_EXPIRES'],
            'iat': datetime.utcnow()
        },
        current_app.config['JWT_SECRET_KEY'],
        algorithm='HS256'
    )

    logger.info(f"User logged in: {user.username}")

    return jsonify({
        'token': token,
        'user': user.to_dict(),
        'expires_in': int(current_app.config['JWT_ACCESS_TOKEN_EXPIRES'].total_seconds())
    }), 200


@auth_bp.route('/refresh-api-key', methods=['POST'])
@require_jwt
def refresh_api_key():
    """Refresh user's API key"""
    user = g.current_user
    old_key = user.api_key

    user.generate_api_key()
    db.session.commit()

    logger.info(f"API key refreshed for user: {user.username}")

    return jsonify({
        'message': 'API key refreshed',
        'api_key': user.api_key
    }), 200


@auth_bp.route('/me', methods=['GET'])
@require_jwt
def get_current_user():
    """Get current user profile"""
    return jsonify({
        'user': g.current_user.to_dict()
    }), 200


@auth_bp.route('/stats', methods=['GET'])
@require_jwt
def get_user_stats():
    """Get API usage statistics for current user"""
    from src.db.models import APIRequest
    
    stats = APIRequest.get_user_stats(g.current_user.id)
    
    return jsonify({
        'stats': stats
    }), 200