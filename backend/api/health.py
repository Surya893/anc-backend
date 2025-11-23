"""
Health Check API Endpoints
"""

from flask import Blueprint, jsonify
from datetime import datetime
import psutil
import os

health_bp = Blueprint('health', __name__)


@health_bp.route('/health', methods=['GET'])
def health_check():
    """Basic health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'anc-backend'
    }), 200


@health_bp.route('/health/detailed', methods=['GET'])
def detailed_health():
    """Detailed health check with system metrics"""
    try:
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'anc-backend',
            'version': '2.0.0',
            'system': {
                'cpu_percent': cpu_percent,
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'percent': memory.percent
                },
                'disk': {
                    'total': disk.total,
                    'used': disk.used,
                    'free': disk.free,
                    'percent': disk.percent
                }
            },
            'process': {
                'pid': os.getpid(),
                'threads': len(psutil.Process().threads())
            }
        }), 200

    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


@health_bp.route('/health/ready', methods=['GET'])
def readiness():
    """Kubernetes readiness probe"""
    # Check if database is accessible
    try:
        from config.database import db
        db.session.execute('SELECT 1')
        return jsonify({'status': 'ready'}), 200
    except Exception as e:
        return jsonify({
            'status': 'not ready',
            'error': str(e)
        }), 503


@health_bp.route('/health/live', methods=['GET'])
def liveness():
    """Kubernetes liveness probe"""
    return jsonify({'status': 'alive'}), 200
