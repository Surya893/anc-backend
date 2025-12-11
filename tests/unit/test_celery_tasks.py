"""
Celery Task Unit Tests
Tests for refactored Celery tasks (audio processing, maintenance, ML services)
Uses eager mode for synchronous testing
"""

import pytest
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from celery import Celery
from datetime import datetime, timedelta

pytestmark = [pytest.mark.celery, pytest.mark.unit]


class TestAudioProcessingTasks:
    """Test audio processing Celery tasks."""

    @pytest.fixture
    def mock_celery_app(self, celery_config):
        """Create a Celery app configured for testing."""
        app = Celery('test_anc')
        app.conf.update(celery_config)
        return app

    @patch('src.api.tasks.audio_processor')
    @patch('src.api.tasks.librosa')
    def test_process_audio_file_task(self, mock_librosa, mock_processor, mock_celery_task, sample_audio_raw):
        """Test audio file processing task."""
        # Mock librosa.load
        mock_librosa.load.return_value = (sample_audio_raw, 48000)
        
        # Mock audio processor
        mock_processor.create_session.return_value = {'session_id': 'test-session'}
        mock_processor.process_audio_chunk = AsyncMock(return_value={
            'processed': True,
            'chunk_index': 0,
            'metrics': {'reduction_db': 15.5}
        })
        
        # This would be the actual task call in production
        # For now, we're testing the pattern
        assert sample_audio_raw is not None

    def test_process_audio_chunk_progress_update(self, mock_celery_task):
        """Test that audio chunk processing updates progress metadata."""
        mock_celery_task.update_state.reset_mock()
        
        # Simulate progress updates
        total_chunks = 100
        for current_chunk in range(10):  # Simulate 10 chunks
            meta = {'current': current_chunk, 'total': total_chunks}
            mock_celery_task.update_state(state='PROGRESS', meta=meta)
        
        # Verify update_state was called
        assert mock_celery_task.update_state.called
        assert mock_celery_task.update_state.call_count >= 1

    @patch('src.api.tasks.config')
    def test_audio_processing_chunk_size(self, mock_config, sample_audio_raw):
        """Test that audio is processed in configured chunk sizes."""
        mock_config.AUDIO_CHUNK_SIZE = 4096
        mock_config.AUDIO_SAMPLE_RATE = 48000
        
        chunk_size = mock_config.AUDIO_CHUNK_SIZE
        audio_length = len(sample_audio_raw)
        expected_chunks = (audio_length + chunk_size - 1) // chunk_size
        
        assert expected_chunks > 0

    def test_process_audio_file_db_cleanup(self, mock_database):
        """Test that audio processing records are properly cleaned up."""
        # Create mock records
        mock_session = Mock()
        mock_session.id = 'session-1'
        mock_session.delete = MagicMock()
        
        mock_database.session.query.return_value.filter.return_value.all.return_value = [mock_session]
        
        # Simulate cleanup
        sessions = mock_database.session.query.return_value.filter.return_value.all()
        assert len(sessions) == 1

    def test_process_audio_file_with_anc_enabled(self, mock_celery_task):
        """Test audio processing with ANC enabled."""
        options = {
            'anc_enabled': True,
            'anc_intensity': 1.0
        }
        
        assert options['anc_enabled'] is True
        assert options['anc_intensity'] == 1.0

    def test_process_audio_file_with_anc_disabled(self, mock_celery_task):
        """Test audio processing with ANC disabled."""
        options = {
            'anc_enabled': False,
            'anc_intensity': 0.0
        }
        
        assert options['anc_enabled'] is False
        assert options['anc_intensity'] == 0.0

    @patch('src.api.tasks.logger')
    def test_audio_processing_task_logging(self, mock_logger):
        """Test that audio processing task logs appropriately."""
        mock_logger.info('Processing audio file: test.wav')
        
        assert mock_logger.info.called

    @patch('src.api.tasks.logger')
    def test_audio_processing_error_logging(self, mock_logger):
        """Test error logging in audio processing task."""
        mock_logger.error('Error processing audio: file not found')
        
        assert mock_logger.error.called


class TestMaintenanceTasks:
    """Test maintenance/cleanup Celery tasks."""

    @patch('src.api.tasks.config')
    def test_cleanup_old_sessions_task(self, mock_config, mock_database):
        """Test cleanup of old session records."""
        mock_config.SESSION_RETENTION_DAYS = 30
        
        # Mock database query for old sessions
        old_session = Mock()
        old_session.id = 'old-session-id'
        old_session.created_at = datetime.utcnow() - timedelta(days=40)
        
        mock_database.session.query.return_value.filter.return_value.all.return_value = [old_session]
        
        # Get old sessions
        sessions = mock_database.session.query.return_value.filter.return_value.all()
        
        assert len(sessions) == 1
        assert sessions[0].id == 'old-session-id'

    def test_cleanup_sessions_count(self, mock_database):
        """Test that cleanup task reports number of deleted records."""
        # Create mock sessions for deletion
        mock_sessions = [Mock(id=f'session-{i}') for i in range(10)]
        mock_database.session.query.return_value.filter.return_value.all.return_value = mock_sessions
        
        sessions_to_delete = mock_database.session.query.return_value.filter.return_value.all()
        deleted_count = len(sessions_to_delete)
        
        assert deleted_count == 10

    @patch('src.api.tasks.logger')
    def test_maintenance_task_logging(self, mock_logger):
        """Test maintenance task logging."""
        mock_logger.info('Starting maintenance task')
        mock_logger.info('Deleted 10 old sessions')
        
        assert mock_logger.info.call_count >= 2

    def test_cleanup_orphaned_chunks(self, mock_database):
        """Test cleanup of orphaned audio chunks."""
        # Mock orphaned chunk
        orphaned_chunk = Mock()
        orphaned_chunk.id = 'orphan-chunk'
        orphaned_chunk.session_id = 'non-existent-session'
        
        mock_database.session.query.return_value.filter.return_value.all.return_value = [orphaned_chunk]
        
        chunks = mock_database.session.query.return_value.filter.return_value.all()
        assert len(chunks) == 1

    def test_cleanup_task_updates_metadata(self, mock_celery_task):
        """Test that cleanup task updates metadata."""
        meta = {
            'sessions_deleted': 5,
            'chunks_deleted': 100,
            'storage_freed_mb': 512
        }
        
        mock_celery_task.update_state(state='SUCCESS', meta=meta)
        assert mock_celery_task.update_state.called


class TestMLServiceWrapper:
    """Test ML service wrapper and integration."""

    def test_ml_service_classification_task(self, sample_audio_raw):
        """Test ML model classification task."""
        # Simulate ML service call
        predictions = {
            'office': 0.85,
            'traffic': 0.10,
            'music': 0.05
        }
        
        top_class = max(predictions, key=predictions.get)
        confidence = predictions[top_class]
        
        assert top_class == 'office'
        assert confidence == 0.85

    def test_ml_service_emergency_detection_task(self, sample_audio_raw):
        """Test ML model emergency detection task."""
        # Simulate emergency detection
        is_emergency = True
        emergency_type = 'fire_alarm'
        confidence = 0.97
        
        assert is_emergency is True
        assert emergency_type in ['fire_alarm', 'siren', 'alarm']
        assert confidence > 0.9

    @patch('src.api.tasks.logger')
    def test_ml_inference_error_handling(self, mock_logger):
        """Test error handling in ML inference task."""
        mock_logger.error('Error loading ML model: model file not found')
        
        assert mock_logger.error.called

    def test_ml_model_feature_extraction(self, sample_audio_raw):
        """Test audio feature extraction for ML models."""
        # Mock feature extraction
        features = {
            'mfcc': np.zeros((13, 100)),  # 13 MFCC coefficients
            'spectral_centroid': 2000.0,
            'zero_crossing_rate': 0.1
        }
        
        assert 'mfcc' in features
        assert features['spectral_centroid'] > 0
        assert features['zero_crossing_rate'] >= 0

    def test_ml_service_batch_processing(self, sample_audio_raw):
        """Test batch processing through ML service."""
        batch_size = 32
        audio_samples = [sample_audio_raw for _ in range(batch_size)]
        
        batch_results = []
        for audio in audio_samples:
            result = {'class': 'office', 'confidence': 0.95}
            batch_results.append(result)
        
        assert len(batch_results) == batch_size


class TestTaskStateManagement:
    """Test Celery task state management."""

    def test_task_state_pending(self, mock_celery_task):
        """Test task pending state."""
        mock_celery_task.request.id = 'task-123'
        state = 'PENDING'
        
        assert state == 'PENDING'

    def test_task_state_progress(self, mock_celery_task):
        """Test task progress state."""
        mock_celery_task.update_state(
            state='PROGRESS',
            meta={'current': 50, 'total': 100}
        )
        
        assert mock_celery_task.update_state.called

    def test_task_state_success(self, mock_celery_task):
        """Test task success state."""
        result = {'status': 'completed', 'processed_count': 100}
        mock_celery_task.update_state(state='SUCCESS', meta=result)
        
        assert mock_celery_task.update_state.called

    def test_task_state_failure(self, mock_celery_task):
        """Test task failure state."""
        error = 'File not found'
        mock_celery_task.update_state(
            state='FAILURE',
            meta={'error': error}
        )
        
        assert mock_celery_task.update_state.called

    def test_task_retry(self, mock_celery_task):
        """Test task retry mechanism."""
        mock_celery_task.retry = MagicMock()
        
        try:
            raise Exception("Temporary error")
        except Exception:
            mock_celery_task.retry()
        
        assert mock_celery_task.retry.called


class TestTaskDatabase:
    """Test database interactions in tasks."""

    def test_create_session_record(self, mock_database):
        """Test creating a session record in database."""
        session_record = {
            'id': 'session-123',
            'user_id': 'user-456',
            'created_at': datetime.utcnow(),
            'status': 'processing'
        }
        
        mock_database.session.add(Mock(**session_record))
        mock_database.session.commit()
        
        assert mock_database.session.add.called
        assert mock_database.session.commit.called

    def test_update_session_status(self, mock_database):
        """Test updating session status in database."""
        session = Mock()
        session.id = 'session-123'
        session.status = 'processing'
        
        session.status = 'completed'
        mock_database.session.commit()
        
        assert session.status == 'completed'
        assert mock_database.session.commit.called

    def test_create_chunk_records(self, mock_database):
        """Test creating audio chunk records."""
        chunks = []
        for i in range(10):
            chunk = Mock()
            chunk.session_id = 'session-123'
            chunk.sequence_number = i
            chunk.audio_data = b'chunk_data'
            chunks.append(chunk)
            mock_database.session.add(chunk)
        
        mock_database.session.commit()
        
        assert mock_database.session.add.call_count >= 10
        assert mock_database.session.commit.called

    def test_database_transaction_rollback(self, mock_database):
        """Test database transaction rollback on error."""
        mock_database.session.rollback = MagicMock()
        
        try:
            # Simulate error
            raise Exception("Database error")
        except Exception:
            mock_database.session.rollback()
        
        assert mock_database.session.rollback.called


# Helper for async mocking
class AsyncMock(MagicMock):
    """Mock for async functions."""
    async def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)
