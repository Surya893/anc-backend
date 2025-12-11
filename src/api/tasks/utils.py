"""
Shared utilities for Celery tasks
Provides database session management, logging, and validation helpers
"""

import logging
import functools
from contextlib import contextmanager
from typing import Any, Dict, Callable, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def task_logger(func: Callable) -> Callable:
    """
    Decorator to add structured logging to tasks
    Logs task start, completion, and duration
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        task_name = func.__name__
        start_time = datetime.utcnow()
        
        logger.info(
            f"Task started",
            extra={
                'task_name': task_name,
                'args': str(args)[:100],
                'kwargs': str(kwargs)[:100]
            }
        )
        
        try:
            result = func(*args, **kwargs)
            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.info(
                f"Task completed successfully",
                extra={
                    'task_name': task_name,
                    'duration_seconds': duration
                }
            )
            return result
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.error(
                f"Task failed with exception",
                extra={
                    'task_name': task_name,
                    'duration_seconds': duration,
                    'error': str(e)
                },
                exc_info=True
            )
            raise
    
    return wrapper


@contextmanager
def get_db_session():
    """
    Context manager for database session handling
    Ensures proper cleanup of sessions
    """
    from models import db
    session = db.session
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database error: {e}", exc_info=True)
        raise
    finally:
        session.close()


def validate_audio_chunk(audio_data: Any, max_size: int = 100000) -> bool:
    """
    Validate audio chunk before processing
    
    Args:
        audio_data: Audio data to validate
        max_size: Maximum allowed size in samples
        
    Returns:
        True if valid, raises ValueError otherwise
    """
    if audio_data is None:
        raise ValueError("Audio data cannot be None")
    
    try:
        size = len(audio_data)
    except (TypeError, AttributeError):
        raise ValueError("Audio data must have a length")
    
    if size <= 0:
        raise ValueError("Audio chunk size must be greater than 0")
    
    if size > max_size:
        raise ValueError(f"Audio chunk size {size} exceeds maximum {max_size}")
    
    return True


def calculate_chunk_progress(current: int, total: int) -> Dict[str, Any]:
    """
    Calculate and return progress metadata
    
    Args:
        current: Current chunk number
        total: Total chunks
        
    Returns:
        Progress metadata dict
    """
    return {
        'current': current,
        'total': total,
        'percent': int((current / total) * 100) if total > 0 else 0
    }


def handle_task_error(
    task_name: str,
    error: Exception,
    max_retries: Optional[int] = None,
    current_retry: Optional[int] = None
) -> None:
    """
    Centralized error handling for tasks
    
    Args:
        task_name: Name of the task
        error: The exception that occurred
        max_retries: Maximum number of retries allowed
        current_retry: Current retry attempt
    """
    logger.error(
        f"Task error",
        extra={
            'task_name': task_name,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'current_retry': current_retry,
            'max_retries': max_retries
        },
        exc_info=True
    )
    
    if max_retries and current_retry and current_retry >= max_retries:
        logger.critical(
            f"Task failed after maximum retries",
            extra={
                'task_name': task_name,
                'max_retries': max_retries
            }
        )


def get_chunk_size(total_samples: int, desired_chunk_size: int) -> int:
    """
    Calculate optimal chunk size for processing
    Ensures chunks don't exceed reasonable limits
    
    Args:
        total_samples: Total number of samples
        desired_chunk_size: Desired chunk size
        
    Returns:
        Optimal chunk size in samples
    """
    # Minimum chunk size (0.5 second at 16kHz)
    MIN_CHUNK = 8000
    # Maximum chunk size (5 seconds at 16kHz)
    MAX_CHUNK = 80000
    
    if desired_chunk_size < MIN_CHUNK:
        chunk_size = MIN_CHUNK
    elif desired_chunk_size > MAX_CHUNK:
        chunk_size = MAX_CHUNK
    else:
        chunk_size = desired_chunk_size
    
    # Don't make chunks larger than total
    chunk_size = min(chunk_size, total_samples)
    
    return chunk_size
