"""
Authentication Middleware
"""

from flask import request, jsonify, g
from functools import wraps
import jwt
import logging

logger = logging.getLogger(__name__)


def setup_jwt(app):
    """Setup JWT configuration"""
    app.config['JWT_SECRET_KEY'] = app.config.get('JWT_SECRET_KEY')
    logger.info("JWT authentication configured")


def require_auth(f):
    """
    Authentication decorator for API endpoints
    Checks for valid API key or JWT token
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for API key first
        api_key = request.headers.get('X-API-Key')
        if api_key:
            user = verify_api_key(api_key)
            if user:
                g.current_user = user
                return f(*args, **kwargs)

        # Check for JWT token
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header[7:]
            user = verify_jwt_token(token)
            if user:
                g.current_user = user
                return f(*args, **kwargs)

        return jsonify({'error': 'Authentication required'}), 401

    return decorated_function


def verify_api_key(api_key):
    """Verify API key and return user"""
    try:
        from database.models import User

        user = User.query.filter_by(
            api_key=api_key,
            is_active=True
        ).first()

        if user:
            logger.info(f"API key authenticated: {user.username}")
            return user

        logger.warning(f"Invalid API key attempted")
        return None

    except Exception as e:
        logger.error(f"Error verifying API key: {e}")
        return None


def verify_jwt_token(token):
    """Verify JWT token and return user"""
    try:
        from flask import current_app
        from database.models import User

        payload = jwt.decode(
            token,
            current_app.config['JWT_SECRET_KEY'],
            algorithms=['HS256']
        )

        user_id = payload.get('user_id')
        if not user_id:
            return None

        user = User.query.filter_by(
            id=user_id,
            is_active=True
        ).first()

        if user:
            logger.info(f"JWT authenticated: {user.username}")
            return user

        return None

    except jwt.ExpiredSignatureError:
        logger.warning("Expired JWT token")
        return None
    except jwt.InvalidTokenError:
        logger.warning("Invalid JWT token")
        return None
    except Exception as e:
        logger.error(f"Error verifying JWT: {e}")
        return None


def generate_jwt_token(user):
    """Generate JWT token for user"""
    from flask import current_app
    from datetime import datetime, timedelta

    payload = {
        'user_id': user.id,
        'username': user.username,
        'exp': datetime.utcnow() + timedelta(
            seconds=current_app.config['JWT_ACCESS_TOKEN_EXPIRES']
        ),
        'iat': datetime.utcnow()
    }

    token = jwt.encode(
        payload,
        current_app.config['JWT_SECRET_KEY'],
        algorithm='HS256'
    )

    return token
