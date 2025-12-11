"""
Maintenance and cleanup tasks for Celery
Handles database cleanup and system maintenance
"""

import logging
import sys
from pathlib import Path
from typing import Dict, Any
from datetime import datetime, timedelta

# Ensure src is in path for imports
src_path = Path(__file__).parent.parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from celery_app import celery_app
from models import db, AudioSession

from .utils import task_logger, handle_task_error

logger = logging.getLogger(__name__)


@celery_app.task(name='tasks.cleanup_old_sessions')
@task_logger
def cleanup_old_sessions(days_old: int = 30) -> Dict[str, Any]:
    """
    Clean up old session data and related records
    Safely deletes completed sessions older than specified days

    Args:
        days_old: Delete sessions older than this many days (default: 30)

    Returns:
        dict: Cleanup results with count of deleted sessions

    Raises:
        Exception: If cleanup fails
    """
    try:
        logger.info(f"Cleaning up sessions older than {days_old} days")

        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        # Find old sessions
        old_sessions = AudioSession.query.filter(
            AudioSession.created_at < cutoff_date,
            AudioSession.status == 'completed'
        ).all()

        count = len(old_sessions)

        if count > 0:
            # Delete sessions (cascades to related records via foreign keys)
            for session in old_sessions:
                try:
                    db.session.delete(session)
                except Exception as e:
                    logger.warning(
                        f"Failed to delete session {session.id}: {e}",
                        exc_info=True
                    )
                    db.session.rollback()
                    continue

            # Commit the transaction
            try:
                db.session.commit()
            except Exception as e:
                logger.error(f"Failed to commit cleanup transaction: {e}", exc_info=True)
                db.session.rollback()
                raise

        logger.info(
            f"Cleanup completed",
            extra={
                'sessions_deleted': count,
                'cutoff_date': cutoff_date.isoformat()
            }
        )

        return {
            'status': 'completed',
            'sessions_deleted': count,
            'cutoff_date': cutoff_date.isoformat()
        }

    except Exception as e:
        handle_task_error('cleanup_old_sessions', e)
        raise


@celery_app.task(name='tasks.cleanup_failed_sessions')
@task_logger
def cleanup_failed_sessions(hours_old: int = 24) -> Dict[str, Any]:
    """
    Clean up failed session records
    Removes incomplete/failed sessions after specified hours

    Args:
        hours_old: Delete failed sessions older than this many hours

    Returns:
        dict: Cleanup results

    Raises:
        Exception: If cleanup fails
    """
    try:
        logger.info(f"Cleaning up failed sessions older than {hours_old} hours")

        cutoff_time = datetime.utcnow() - timedelta(hours=hours_old)

        # Find failed sessions
        failed_sessions = AudioSession.query.filter(
            AudioSession.created_at < cutoff_time,
            AudioSession.status.in_(['failed', 'error'])
        ).all()

        count = len(failed_sessions)

        if count > 0:
            for session in failed_sessions:
                try:
                    db.session.delete(session)
                except Exception as e:
                    logger.warning(f"Failed to delete session {session.id}: {e}")
                    db.session.rollback()
                    continue

            try:
                db.session.commit()
            except Exception as e:
                logger.error(f"Failed to commit failed session cleanup: {e}")
                db.session.rollback()
                raise

        logger.info(f"Cleaned up {count} failed sessions")

        return {
            'status': 'completed',
            'failed_sessions_deleted': count,
            'cutoff_time': cutoff_time.isoformat()
        }

    except Exception as e:
        handle_task_error('cleanup_failed_sessions', e)
        raise


@celery_app.task(name='tasks.vacuum_database')
@task_logger
def vacuum_database() -> Dict[str, Any]:
    """
    Optimize database by running VACUUM command
    Reclaims unused space and optimizes table layout

    Returns:
        dict: Vacuum results

    Raises:
        Exception: If vacuum fails
    """
    try:
        logger.info("Starting database vacuum")

        # Execute VACUUM to optimize database
        db.session.execute('VACUUM')
        db.session.commit()

        logger.info("Database vacuum completed")

        return {
            'status': 'completed',
            'operation': 'vacuum',
            'timestamp': datetime.utcnow().isoformat()
        }

    except Exception as e:
        handle_task_error('vacuum_database', e)
        raise


@celery_app.task(name='tasks.health_check')
@task_logger
def health_check() -> Dict[str, Any]:
    """
    Perform system health check
    Validates database connectivity and basic system status

    Returns:
        dict: Health check results

    Raises:
        Exception: If health check fails
    """
    try:
        logger.info("Starting system health check")

        health_status = {
            'timestamp': datetime.utcnow().isoformat(),
            'components': {}
        }

        # Check database
        try:
            session_count = AudioSession.query.count()
            health_status['components']['database'] = {
                'status': 'healthy',
                'session_count': session_count
            }
        except Exception as e:
            logger.warning(f"Database health check failed: {e}")
            health_status['components']['database'] = {
                'status': 'unhealthy',
                'error': str(e)
            }

        logger.info("Health check completed")

        return health_status

    except Exception as e:
        handle_task_error('health_check', e)
        raise
