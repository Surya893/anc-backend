"""
Celery application bootstrap
Initializes Celery with configuration and exposes the app instance
"""

from celery import Celery
from config import get_config

# Get configuration
config = get_config()

# Initialize Celery app
celery_app = Celery('anc_platform')

# Configure Celery from config
celery_app.conf.update(
    broker_url=config.CELERY_BROKER_URL,
    result_backend=config.CELERY_RESULT_BACKEND,
    task_serializer=config.CELERY_TASK_SERIALIZER,
    result_serializer=config.CELERY_RESULT_SERIALIZER,
    accept_content=config.CELERY_ACCEPT_CONTENT,
    timezone=config.CELERY_TIMEZONE,
    enable_utc=config.CELERY_ENABLE_UTC,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50
)
