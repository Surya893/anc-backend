"""
Audio processing tasks for Celery
Handles audio file processing and batch operations
"""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

import librosa
import numpy as np

import sys
from pathlib import Path

# Ensure src is in path for imports
src_path = Path(__file__).parent.parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from celery import Task
from celery_app import celery_app
from config import get_config
from audio_processor import audio_processor
from models import db, AudioSession

from .utils import (
    task_logger,
    get_db_session,
    validate_audio_chunk,
    calculate_chunk_progress,
    handle_task_error,
    get_chunk_size
)

logger = logging.getLogger(__name__)
config = get_config()


class DatabaseTask(Task):
    """Base task with database session handling"""
    _db = None

    @property
    def db(self):
        if self._db is None:
            self._db = db
        return self._db


@celery_app.task(bind=True, base=DatabaseTask, name='tasks.process_audio_file')
@task_logger
def process_audio_file(
    self,
    file_path: str,
    session_id: str,
    apply_anc: bool = True
) -> Dict[str, Any]:
    """
    Process an audio file asynchronously
    Handles chunk-based processing with progress tracking

    Args:
        self: Celery task instance
        file_path: Path to audio file
        session_id: Processing session ID
        apply_anc: Whether to apply noise cancellation

    Returns:
        dict: Processing results with metrics

    Raises:
        FileNotFoundError: If audio file doesn't exist
        ValueError: If processing fails
    """
    try:
        logger.info(f"Processing audio file: {file_path}", extra={'session_id': session_id})

        # Validate file exists
        audio_path = Path(file_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        # Load audio file
        audio_data, sample_rate = librosa.load(
            str(audio_path),
            sr=config.AUDIO_SAMPLE_RATE
        )

        # Create processing session
        session = audio_processor.create_session(session_id, {
            'anc_enabled': apply_anc,
            'anc_intensity': 1.0,
            'file_path': file_path
        })

        # Calculate optimal chunk size
        total_samples = len(audio_data)
        chunk_size = get_chunk_size(total_samples, config.AUDIO_CHUNK_SIZE)
        num_chunks = max(1, (total_samples + chunk_size - 1) // chunk_size)

        logger.info(
            f"Starting chunk processing",
            extra={
                'session_id': session_id,
                'total_samples': total_samples,
                'chunk_size': chunk_size,
                'num_chunks': num_chunks
            }
        )

        # Process in chunks using sync adapter
        results = []
        for i in range(num_chunks):
            start_idx = i * chunk_size
            end_idx = min(start_idx + chunk_size, total_samples)
            chunk = audio_data[start_idx:end_idx]

            # Validate chunk
            try:
                validate_audio_chunk(chunk)
            except ValueError as e:
                logger.warning(f"Chunk validation failed: {e}", extra={'chunk_index': i})
                continue

            # Update progress
            progress = calculate_chunk_progress(i + 1, num_chunks)
            self.update_state(state='PROGRESS', meta=progress)

            # Process chunk synchronously (no asyncio.run per chunk)
            try:
                result = audio_processor.process_chunk_sync(
                    session_id=session_id,
                    audio_data=chunk,
                    apply_anc=apply_anc
                )
                results.append(result)
            except Exception as e:
                logger.error(
                    f"Error processing chunk",
                    extra={'session_id': session_id, 'chunk_index': i},
                    exc_info=True
                )
                raise

        # Get final stats
        stats = audio_processor.get_session_stats(session_id)

        # Cleanup
        audio_processor.end_session(session_id)

        logger.info(
            f"Completed processing {file_path}",
            extra={
                'session_id': session_id,
                'num_chunks': num_chunks,
                'avg_cancellation_db': stats['average_cancellation_db'],
                'avg_latency_ms': stats['average_latency_ms']
            }
        )

        return {
            'status': 'completed',
            'file_path': str(file_path),
            'num_chunks': num_chunks,
            'session_stats': stats,
            'results_summary': {
                'average_cancellation_db': float(stats['average_cancellation_db']),
                'average_latency_ms': float(stats['average_latency_ms']),
                'duration_seconds': float(stats['duration_seconds'])
            }
        }

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}", exc_info=True)
        raise
    except Exception as e:
        handle_task_error('process_audio_file', e)
        raise


@celery_app.task(bind=True, name='tasks.batch_process_files')
@task_logger
def batch_process_files(
    self,
    file_paths: List[str],
    apply_anc: bool = True
) -> Dict[str, Any]:
    """
    Batch process multiple audio files
    Processes files sequentially with progress tracking

    Args:
        self: Celery task instance
        file_paths: List of audio file paths
        apply_anc: Whether to apply noise cancellation

    Returns:
        dict: Batch processing results

    Raises:
        ValueError: If batch processing fails
    """
    try:
        logger.info(f"Batch processing {len(file_paths)} files")

        if not file_paths:
            raise ValueError("No files provided for batch processing")

        results = []
        failed_files = []

        for i, file_path in enumerate(file_paths):
            # Update progress
            progress = calculate_chunk_progress(i + 1, len(file_paths))
            self.update_state(state='PROGRESS', meta=progress)

            try:
                # Process file
                session_id = f"batch_{self.request.id}_{i}"
                result = process_audio_file(
                    file_path=file_path,
                    session_id=session_id,
                    apply_anc=apply_anc
                )
                results.append(result)
                logger.info(f"Successfully processed: {file_path}")
            except Exception as e:
                logger.error(f"Failed to process: {file_path}", exc_info=True)
                failed_files.append({'file': file_path, 'error': str(e)})

        logger.info(
            f"Batch processing completed",
            extra={
                'total_files': len(file_paths),
                'successful': len(results),
                'failed': len(failed_files)
            }
        )

        return {
            'status': 'completed' if not failed_files else 'partial',
            'files_processed': len(results),
            'files_failed': len(failed_files),
            'results': results,
            'failed': failed_files
        }

    except Exception as e:
        handle_task_error('batch_process_files', e)
        raise
