"""
Pytest configuration and shared fixtures for ANC Platform tests
"""

import pytest
import sys
import os
from pathlib import Path
import numpy as np
from unittest.mock import Mock, MagicMock, patch

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'backend'))
sys.path.insert(0, str(project_root / 'src'))
sys.path.insert(0, str(project_root / 'src' / 'api'))
sys.path.insert(0, str(project_root / 'src' / 'ml'))


# ============================================================================
# FLASK FIXTURES
# ============================================================================

@pytest.fixture(scope='function')
def flask_app():
    """
    Create a Flask app instance for testing with app factory pattern.
    Configures test settings and initializes database.
    """
    # Mock the config module to avoid import errors
    with patch('backend.server.Config') as mock_config:
        mock_config.CORS_ORIGINS = ['http://localhost:3000']
        mock_config.JWT_SECRET_KEY = 'test-secret-key'
        mock_config.JWT_ACCESS_TOKEN_EXPIRES = 3600
        mock_config.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
        mock_config.SQLALCHEMY_TRACK_MODIFICATIONS = False
        mock_config.ANC_FILTER_TAPS = 256

        # Mock db module
        with patch('backend.server.db') as mock_db, \
             patch('backend.server.init_db'), \
             patch('backend.server.setup_jwt'), \
             patch('backend.server.setup_logging'), \
             patch('backend.server.init_socketio'):

            mock_db.init_app = MagicMock()

            from backend.server import create_app
            app = create_app()
            app.config['TESTING'] = True

            # Create a mock database context
            with app.app_context():
                yield app


@pytest.fixture(scope='function')
def client(flask_app):
    """
    Create a Flask test client for making HTTP requests.
    """
    return flask_app.test_client()


@pytest.fixture(scope='function')
def app_context(flask_app):
    """
    Provide Flask application context for tests that need it.
    """
    with flask_app.app_context():
        yield flask_app


@pytest.fixture
def mock_user():
    """
    Create a mock user object for authentication tests.
    """
    user = Mock()
    user.id = 'test-user-id'
    user.username = 'testuser'
    user.email = 'test@example.com'
    user.is_active = True
    user.api_key = 'test-api-key'
    return user


@pytest.fixture
def mock_anc_service():
    """
    Create a mock ANCService for testing.
    """
    service = Mock()
    service.process_audio = MagicMock(return_value={
        'processed_audio': 'base64encodedaudio',
        'metrics': {
            'reduction_db': 15.5,
            'original_rms': 0.2,
            'processed_rms': 0.1,
            'samples_processed': 48000
        }
    })
    return service


@pytest.fixture
def mock_ml_service():
    """
    Create a mock MLService for testing.
    """
    service = Mock()
    service.classify_noise = MagicMock(return_value={
        'noise_type': 'office',
        'confidence': 0.95,
        'all_predictions': {
            'office': 0.95,
            'traffic': 0.03,
            'music': 0.02
        }
    })
    service.detect_emergency = MagicMock(return_value={
        'is_emergency': False,
        'emergency_type': None,
        'confidence': 0.01
    })
    return service


# ============================================================================
# AUDIO DATA FIXTURES
# ============================================================================

@pytest.fixture
def sample_audio_data():
    """
    Generate synthetic audio data for testing.
    Returns base64-encoded audio.
    """
    import base64
    
    # Generate 1 second of 440 Hz tone
    sample_rate = 48000
    duration = 1.0
    frequency = 440
    
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio = 0.5 * np.sin(2 * np.pi * frequency * t)
    
    # Convert to bytes and encode as base64
    audio_bytes = audio.astype(np.float32).tobytes()
    audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
    
    return audio_b64


@pytest.fixture
def sample_audio_raw():
    """
    Generate raw audio numpy array for testing.
    """
    sample_rate = 48000
    duration = 1.0
    frequency = 440
    
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio = 0.5 * np.sin(2 * np.pi * frequency * t)
    
    return audio


@pytest.fixture
def emergency_audio_data():
    """
    Generate synthetic emergency sound (fire alarm-like) for testing.
    """
    import base64
    
    sample_rate = 48000
    duration = 2.0
    
    t = np.linspace(0, duration, int(sample_rate * duration))
    # Fire alarm-like: alternating frequencies
    alarm1 = 0.3 * np.sin(2 * np.pi * 880 * t)  # High frequency
    alarm2 = 0.3 * np.sin(2 * np.pi * 1000 * t)  # Slightly higher frequency
    
    # Modulate between frequencies
    audio = np.where(t % 0.5 < 0.25, alarm1, alarm2)
    
    # Convert to bytes and encode as base64
    audio_bytes = audio.astype(np.float32).tobytes()
    audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
    
    return audio_b64


# ============================================================================
# CELERY FIXTURES
# ============================================================================

@pytest.fixture(scope='session')
def celery_config():
    """
    Configure Celery for testing with eager mode.
    """
    return {
        'broker_url': 'memory://',
        'result_backend': 'cache+memory://',
        'task_always_eager': True,
        'task_eager_propagates': True,
    }


@pytest.fixture
def celery_worker_pool():
    """
    Use solo pool for testing (synchronous execution).
    """
    return 'solo'


@pytest.fixture
def mock_celery_task():
    """
    Create a mock Celery task for testing.
    """
    task = Mock()
    task.request = Mock()
    task.request.id = 'test-task-id'
    task.update_state = MagicMock()
    return task


@pytest.fixture
def mock_database():
    """
    Create a mock database for task testing.
    """
    db = Mock()
    db.session = Mock()
    db.session.query = MagicMock()
    db.session.add = MagicMock()
    db.session.commit = MagicMock()
    db.session.rollback = MagicMock()
    return db


# ============================================================================
# DATABASE FIXTURES
# ============================================================================

@pytest.fixture
def mock_session_model():
    """
    Create a mock AudioSession model for testing.
    """
    session = Mock()
    session.id = 'test-session-id'
    session.user_id = 'test-user-id'
    session.created_at = '2024-01-01T00:00:00Z'
    session.updated_at = '2024-01-01T00:00:00Z'
    session.duration = 60.0
    session.noise_type = 'office'
    session.confidence = 0.95
    session.to_dict = MagicMock(return_value={
        'id': 'test-session-id',
        'user_id': 'test-user-id',
        'created_at': '2024-01-01T00:00:00Z',
        'duration': 60.0,
        'noise_type': 'office',
        'confidence': 0.95
    })
    return session


@pytest.fixture
def mock_audio_chunk_model():
    """
    Create a mock AudioChunk model for testing.
    """
    chunk = Mock()
    chunk.id = 'test-chunk-id'
    chunk.session_id = 'test-session-id'
    chunk.sequence_number = 1
    chunk.audio_data = b'audio_data'
    chunk.processed_audio_data = b'processed_audio'
    chunk.timestamp = '2024-01-01T00:00:00Z'
    chunk.to_dict = MagicMock(return_value={
        'id': 'test-chunk-id',
        'session_id': 'test-session-id',
        'sequence_number': 1,
        'timestamp': '2024-01-01T00:00:00Z'
    })
    return chunk


# ============================================================================
# PYTEST HOOKS
# ============================================================================

def pytest_configure(config):
    """
    Configure pytest with custom markers.
    """
    config.addinivalue_line(
        'markers', 'celery: marks tests as Celery task tests'
    )
    config.addinivalue_line(
        'markers', 'flask: marks tests as Flask API tests'
    )
    config.addinivalue_line(
        'markers', 'auth: marks tests as authentication tests'
    )
    config.addinivalue_line(
        'markers', 'audio: marks tests as audio processing tests'
    )
    config.addinivalue_line(
        'markers', 'ml: marks tests as ML model tests'
    )
    config.addinivalue_line(
        'markers', 'integration_backend: marks tests as backend integration tests'
    )
    config.addinivalue_line(
        'markers', 'requires_services: marks tests requiring external services'
    )
