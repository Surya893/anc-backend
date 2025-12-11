"""
Unit tests for audio processing tasks
Tests process_audio_file and batch_process_files tasks in eager mode
"""

import pytest
import tempfile
from pathlib import Path
import numpy as np
import librosa

# Set Celery to eager mode for testing
from celery_app import celery_app
celery_app.conf.update(task_always_eager=True, task_eager_propagates=True)

from api.tasks import process_audio_file, batch_process_files
from audio_processor import audio_processor
from config import get_config


@pytest.fixture
def temp_audio_file():
    """Create a temporary audio file for testing"""
    config = get_config()
    sr = config.AUDIO_SAMPLE_RATE
    
    # Generate 2 seconds of silence
    duration = 2
    samples = sr * duration
    audio_data = np.zeros(samples, dtype=np.float32)
    
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        librosa.output.write_wav(f.name, audio_data, sr)
        yield f.name
    
    # Cleanup
    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def temp_audio_files():
    """Create multiple temporary audio files for testing"""
    config = get_config()
    sr = config.AUDIO_SAMPLE_RATE
    
    files = []
    for i in range(3):
        duration = 1
        samples = sr * duration
        audio_data = np.random.randn(samples).astype(np.float32) * 0.1
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            librosa.output.write_wav(f.name, audio_data, sr)
            files.append(f.name)
    
    yield files
    
    # Cleanup
    for f in files:
        Path(f).unlink(missing_ok=True)


class TestProcessAudioFile:
    """Test process_audio_file task"""
    
    def test_process_audio_file_success(self, temp_audio_file):
        """Test successful audio file processing"""
        session_id = "test_session_001"
        
        result = process_audio_file(
            file_path=temp_audio_file,
            session_id=session_id,
            apply_anc=True
        )
        
        assert result['status'] == 'completed'
        assert result['file_path'] == temp_audio_file
        assert result['num_chunks'] > 0
        assert 'session_stats' in result
        assert 'results_summary' in result
        assert result['results_summary']['average_cancellation_db'] >= 0
    
    def test_process_audio_file_missing_file(self):
        """Test processing non-existent file"""
        session_id = "test_session_002"
        non_existent_file = "/tmp/nonexistent_audio_12345.wav"
        
        with pytest.raises(FileNotFoundError):
            process_audio_file(
                file_path=non_existent_file,
                session_id=session_id,
                apply_anc=True
            )
    
    def test_process_audio_file_without_anc(self, temp_audio_file):
        """Test processing without ANC enabled"""
        session_id = "test_session_003"
        
        result = process_audio_file(
            file_path=temp_audio_file,
            session_id=session_id,
            apply_anc=False
        )
        
        assert result['status'] == 'completed'
        assert result['results_summary']['average_cancellation_db'] == 0.0
    
    def test_audio_processor_session_lifecycle(self, temp_audio_file):
        """Test audio processor session management"""
        session_id = "test_session_004"
        
        # Create session
        session = audio_processor.create_session(
            session_id,
            {'anc_enabled': True}
        )
        assert session['id'] == session_id
        
        # Process chunk
        audio_data = np.zeros(16000)
        result = audio_processor.process_chunk_sync(
            session_id=session_id,
            audio_data=audio_data,
            apply_anc=True
        )
        assert result['session_id'] == session_id
        
        # Get stats
        stats = audio_processor.get_session_stats(session_id)
        assert stats['chunks_processed'] == 1
        
        # End session
        final_stats = audio_processor.end_session(session_id)
        assert final_stats['session_id'] == session_id


class TestBatchProcessFiles:
    """Test batch_process_files task"""
    
    def test_batch_process_files_success(self, temp_audio_files):
        """Test successful batch file processing"""
        result = batch_process_files(
            file_paths=temp_audio_files,
            apply_anc=True
        )
        
        assert result['status'] == 'completed'
        assert result['files_processed'] == len(temp_audio_files)
        assert result['files_failed'] == 0
        assert len(result['results']) == len(temp_audio_files)
    
    def test_batch_process_empty_list(self):
        """Test batch processing with empty file list"""
        with pytest.raises(ValueError):
            batch_process_files(
                file_paths=[],
                apply_anc=True
            )
    
    def test_batch_process_mixed_valid_invalid(self, temp_audio_files):
        """Test batch with mix of valid and invalid files"""
        mixed_files = temp_audio_files + ['/tmp/nonexistent_file_12345.wav']
        
        result = batch_process_files(
            file_paths=mixed_files,
            apply_anc=True
        )
        
        # Should process valid files and record failures
        assert result['files_processed'] + result['files_failed'] == len(mixed_files)
        assert len(result['failed']) > 0


class TestAudioProcessorSync:
    """Test audio processor sync functionality"""
    
    def test_process_chunk_sync_creates_event_loop(self):
        """Test that sync processor can create event loops when needed"""
        session_id = "test_sync_001"
        audio_processor.create_session(session_id, {'anc_enabled': True})
        
        audio_data = np.random.randn(16000).astype(np.float32) * 0.1
        result = audio_processor.process_chunk_sync(
            session_id=session_id,
            audio_data=audio_data,
            apply_anc=True
        )
        
        assert result['session_id'] == session_id
        assert result['chunk_size'] == len(audio_data)
        audio_processor.end_session(session_id)
    
    def test_process_chunk_sync_reuses_event_loop(self):
        """Test that sync processor reuses existing event loops"""
        import asyncio
        
        session_id = "test_sync_002"
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        audio_processor.create_session(session_id, {'anc_enabled': True})
        audio_data = np.zeros(8000)
        
        result = audio_processor.process_chunk_sync(
            session_id=session_id,
            audio_data=audio_data,
            apply_anc=True
        )
        
        assert result['session_id'] == session_id
        audio_processor.end_session(session_id)
        loop.close()


class TestChunkProcessing:
    """Test chunk-based processing logic"""
    
    def test_chunk_size_calculation(self):
        """Test chunk size calculation"""
        from api.tasks.utils import get_chunk_size
        
        # Test with default chunk size
        chunk_size = get_chunk_size(100000, 16000)
        assert chunk_size == 16000
        
        # Test with chunk size too small
        chunk_size = get_chunk_size(100000, 4000)
        assert chunk_size == 8000  # MIN_CHUNK
        
        # Test with chunk size too large
        chunk_size = get_chunk_size(100000, 100000)
        assert chunk_size == 80000  # MAX_CHUNK
    
    def test_progress_calculation(self):
        """Test progress metadata calculation"""
        from api.tasks.utils import calculate_chunk_progress
        
        progress = calculate_chunk_progress(5, 10)
        assert progress['current'] == 5
        assert progress['total'] == 10
        assert progress['percent'] == 50
        
        progress = calculate_chunk_progress(1, 1)
        assert progress['percent'] == 100


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
