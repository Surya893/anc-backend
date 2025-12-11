"""
Statistics and Analytics Routes Blueprint
Handles system metrics, user analytics, and health monitoring
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime, timedelta
import logging

# Import shared models
from src.db.models import db, User, AudioSession, NoiseDetection, ProcessingMetric, APIRequest

logger = logging.getLogger(__name__)

stats_bp = Blueprint('stats', __name__)


def require_api_key(f):
    """API key authentication decorator"""
    @stats_bp.before_request
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


@stats_bp.route('/dashboard', methods=['GET'])
@require_api_key
def get_dashboard_stats():
    """Get dashboard statistics for current user"""
    now = datetime.utcnow()
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)
    
    # User session stats
    total_sessions = AudioSession.query.filter_by(user_id=g.current_user.id).count()
    active_sessions = AudioSession.query.filter_by(
        user_id=g.current_user.id, status='active'
    ).count()
    sessions_24h = AudioSession.query.filter(
        AudioSession.user_id == g.current_user.id,
        AudioSession.created_at >= last_24h
    ).count()
    
    # Processing stats
    total_chunks = db.session.query(
        db.func.sum(AudioSession.total_chunks_processed)
    ).filter_by(user_id=g.current_user.id).scalar() or 0
    
    avg_latency = db.session.query(
        db.func.avg(AudioSession.average_latency_ms)
    ).filter_by(user_id=g.current_user.id).scalar() or 0.0
    
    avg_cancellation = db.session.query(
        db.func.avg(AudioSession.average_cancellation_db)
    ).filter_by(user_id=g.current_user.id).scalar() or 0.0
    
    # API usage stats
    api_stats_24h = APIRequest.get_user_stats(g.current_user.id, hours=24)
    api_stats_7d = APIRequest.get_user_stats(g.current_user.id, hours=168)  # 7 days
    
    return jsonify({
        'dashboard': {
            'sessions': {
                'total': total_sessions,
                'active': active_sessions,
                'last_24h': sessions_24h
            },
            'processing': {
                'total_chunks': total_chunks,
                'avg_latency_ms': float(avg_latency),
                'avg_cancellation_db': float(avg_cancellation)
            },
            'api_usage': {
                'requests_24h': api_stats_24h['total_requests'],
                'avg_response_time_24h': api_stats_24h['avg_response_time'],
                'errors_24h': api_stats_24h['error_count'],
                'requests_7d': api_stats_7d['total_requests'],
                'avg_response_time_7d': api_stats_7d['avg_response_time']
            }
        }
    }), 200


@stats_bp.route('/sessions/trends', methods=['GET'])
@require_api_key
def get_session_trends():
    """Get session usage trends"""
    days = request.args.get('days', 30, type=int)
    since = datetime.utcnow() - timedelta(days=days)
    
    # Daily session counts
    daily_stats = db.session.query(
        db.func.date(AudioSession.created_at).label('date'),
        db.func.count(AudioSession.id).label('sessions'),
        db.func.sum(AudioSession.total_chunks_processed).label('chunks'),
        db.func.avg(AudioSession.average_latency_ms).label('avg_latency')
    ).filter(
        AudioSession.user_id == g.current_user.id,
        AudioSession.created_at >= since
    ).group_by(
        db.func.date(AudioSession.created_at)
    ).order_by('date').all()
    
    return jsonify({
        'trends': {
            'days': days,
            'data': [{
                'date': stat.date.isoformat(),
                'sessions': stat.sessions,
                'chunks': stat.chunks or 0,
                'avg_latency_ms': float(stat.avg_latency or 0.0)
            } for stat in daily_stats]
        }
    }), 200


@stats_bp.route('/noise/types', methods=['GET'])
@require_api_key
def get_noise_type_stats():
    """Get noise type classification statistics"""
    days = request.args.get('days', 30, type=int)
    since = datetime.utcnow() - timedelta(days=days)
    
    # Noise type counts
    noise_stats = db.session.query(
        NoiseDetection.noise_type,
        db.func.count(NoiseDetection.id).label('count'),
        db.func.avg(NoiseDetection.confidence).label('avg_confidence'),
        db.func.sum(db.case([(NoiseDetection.is_emergency == True, 1)], else_=0)).label('emergency_count')
    ).join(
        AudioSession, AudioSession.id == NoiseDetection.session_id
    ).filter(
        AudioSession.user_id == g.current_user.id,
        NoiseDetection.created_at >= since,
        NoiseDetection.noise_type.isnot(None)
    ).group_by(
        NoiseDetection.noise_type
    ).order_by('count desc').limit(20).all()
    
    return jsonify({
        'noise_types': {
            'period_days': days,
            'data': [{
                'noise_type': stat.noise_type,
                'count': stat.count,
                'avg_confidence': float(stat.avg_confidence or 0.0),
                'emergency_count': stat.emergency_count
            } for stat in noise_stats]
        }
    }), 200


@stats_bp.route('/performance/metrics', methods=['GET'])
@require_api_key
def get_performance_metrics():
    """Get system performance metrics"""
    days = request.args.get('days', 7, type=int)
    since = datetime.utcnow() - timedelta(days=days)
    
    # Processing metrics
    metrics = db.session.query(
        db.func.avg(ProcessingMetric.latency_ms).label('avg_latency'),
        db.func.max(ProcessingMetric.latency_ms).label('max_latency'),
        db.func.avg(ProcessingMetric.cancellation_db).label('avg_cancellation'),
        db.func.max(ProcessingMetric.cancellation_db).label('max_cancellation'),
        db.func.count(ProcessingMetric.id).label('total_processed')
    ).join(
        AudioSession, AudioSession.id == ProcessingMetric.session_id
    ).filter(
        AudioSession.user_id == g.current_user.id,
        ProcessingMetric.created_at >= since
    ).first()
    
    return jsonify({
        'performance': {
            'period_days': days,
            'avg_latency_ms': float(metrics.avg_latency or 0.0),
            'max_latency_ms': float(metrics.max_latency or 0.0),
            'avg_cancellation_db': float(metrics.avg_cancellation or 0.0),
            'max_cancellation_db': float(metrics.max_cancellation or 0.0),
            'total_chunks_processed': metrics.total_processed or 0
        }
    }), 200


@stats_bp.route('/system/health', methods=['GET'])
def get_system_health():
    """Get system health status"""
    try:
        # Database connectivity
        db.session.execute('SELECT 1')
        db_status = 'healthy'
    except Exception as e:
        db_status = f'unhealthy: {str(e)}'
    
    # Basic system metrics
    user_count = User.query.filter_by(is_active=True).count()
    active_sessions = AudioSession.query.filter_by(status='active').count()
    total_requests_24h = APIRequest.query.filter(
        APIRequest.created_at >= datetime.utcnow() - timedelta(hours=24)
    ).count()
    
    # Service status
    services = {
        'database': db_status,
        'users': f'healthy ({user_count} active users)',
        'sessions': f'healthy ({active_sessions} active sessions)',
        'api_requests_24h': f'healthy ({total_requests_24h} requests)'
    }
    
    return jsonify({
        'health': {
            'status': 'healthy' if db_status == 'healthy' else 'degraded',
            'timestamp': datetime.utcnow().isoformat(),
            'services': services
        }
    }), 200 if db_status == 'healthy' else 503


@stats_bp.route('/users/activity', methods=['GET'])
@require_api_key
def get_user_activity():
    """Get user activity summary (admin only)"""
    if not g.current_user.is_admin:
        return jsonify({'error': 'Admin access required'}), 403
    
    days = request.args.get('days', 7, type=int)
    since = datetime.utcnow() - timedelta(days=days)
    
    # Active users
    active_users = db.session.query(
        db.func.count(db.distinct(User.id)).label('active_users')
    ).join(
        AudioSession, User.id == AudioSession.user_id
    ).filter(
        AudioSession.created_at >= since
    ).scalar()
    
    # User registration trend
    new_users = db.session.query(
        db.func.count(User.id)
    ).filter(
        User.created_at >= since
    ).scalar()
    
    # Top users by activity
    top_users = db.session.query(
        User.username,
        db.func.count(AudioSession.id).label('session_count'),
        db.func.sum(AudioSession.total_chunks_processed).label('total_chunks')
    ).join(
        AudioSession, User.id == AudioSession.user_id
    ).filter(
        AudioSession.created_at >= since
    ).group_by(
        User.id, User.username
    ).order_by('session_count desc').limit(10).all()
    
    return jsonify({
        'activity': {
            'period_days': days,
            'active_users': active_users or 0,
            'new_users': new_users or 0,
            'top_users': [{
                'username': user.username,
                'session_count': user.session_count or 0,
                'total_chunks': user.total_chunks or 0
            } for user in top_users]
        }
    }), 200