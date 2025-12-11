"""
Celery tasks package for ANC Platform
Provides all background job definitions for audio processing, training, and maintenance
"""

from celery.schedules import crontab
# Import celery_app - it's in src/ due to PYTHONPATH configuration
try:
    from celery_app import celery_app
except ImportError:
    # Fallback for when PYTHONPATH isn't set correctly
    import sys
    from pathlib import Path
    src_path = Path(__file__).parent.parent.parent
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    from celery_app import celery_app

# Import all task modules to register them with Celery
from .audio_processing import process_audio_file, batch_process_files  # noqa: F401
from .model_training import train_noise_classifier, validate_model  # noqa: F401
from .analytics import analyze_session_data, generate_daily_report, export_session_data  # noqa: F401
from .maintenance import (  # noqa: F401
    cleanup_old_sessions,
    cleanup_failed_sessions,
    vacuum_database,
    health_check
)

import logging

logger = logging.getLogger(__name__)


# Setup periodic tasks
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Configure periodic tasks"""

    # Daily report at 1 AM UTC
    sender.add_periodic_task(
        crontab(hour=1, minute=0),
        generate_daily_report.s(),
        name='generate_daily_report'
    )

    # Cleanup old sessions weekly on Sunday at 2 AM UTC
    sender.add_periodic_task(
        crontab(hour=2, minute=0, day_of_week=0),
        cleanup_old_sessions.s(days_old=30),
        name='cleanup_old_sessions'
    )

    # Cleanup failed sessions daily at 3 AM UTC
    sender.add_periodic_task(
        crontab(hour=3, minute=0),
        cleanup_failed_sessions.s(hours_old=24),
        name='cleanup_failed_sessions'
    )

    # Vacuum database weekly on Saturday at 4 AM UTC
    sender.add_periodic_task(
        crontab(hour=4, minute=0, day_of_week=6),
        vacuum_database.s(),
        name='vacuum_database'
    )

    # Health check every hour
    sender.add_periodic_task(
        60 * 60,  # 3600 seconds = 1 hour
        health_check.s(),
        name='health_check'
    )

    logger.info("Periodic tasks configured")


__all__ = [
    'celery_app',
    'process_audio_file',
    'batch_process_files',
    'train_noise_classifier',
    'validate_model',
    'analyze_session_data',
    'generate_daily_report',
    'export_session_data',
    'cleanup_old_sessions',
    'cleanup_failed_sessions',
    'vacuum_database',
    'health_check',
]
