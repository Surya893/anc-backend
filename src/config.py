"""
Configuration module for ANC Platform
Provides unified configuration management
"""

import os
from pathlib import Path


class Config:
    """Base configuration"""
    # Celery configuration
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')
    CELERY_TASK_SERIALIZER = os.environ.get('CELERY_TASK_SERIALIZER', 'json')
    CELERY_RESULT_SERIALIZER = os.environ.get('CELERY_RESULT_SERIALIZER', 'json')
    CELERY_ACCEPT_CONTENT = ['json', 'msgpack', 'yaml']
    CELERY_TIMEZONE = 'UTC'
    CELERY_ENABLE_UTC = True

    # Audio processing
    AUDIO_SAMPLE_RATE = int(os.environ.get('AUDIO_SAMPLE_RATE', '16000'))
    AUDIO_CHUNK_SIZE = int(os.environ.get('AUDIO_CHUNK_SIZE', '16000'))  # 1 second at 16kHz
    
    # ML model paths
    ML_MODEL_PATH = Path(os.environ.get('ML_MODEL_PATH', 'models/noise_classifier.joblib'))
    ML_SCALER_PATH = Path(os.environ.get('ML_SCALER_PATH', 'models/feature_scaler.joblib'))
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_DIR = Path(os.environ.get('LOG_DIR', 'logs'))
    LOG_FILE = LOG_DIR / 'anc_platform.log'
    LOG_MAX_BYTES = int(os.environ.get('LOG_MAX_BYTES', '10485760'))  # 10MB
    LOG_BACKUP_COUNT = int(os.environ.get('LOG_BACKUP_COUNT', '5'))
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # CORS
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')


def get_config(config_name=None):
    """Get configuration object"""
    return Config()
