# ANC Platform Tests

Comprehensive test suite for the ANC Platform including unit tests, integration tests, and demos.

## Test Structure

```
tests/
├── conftest.py                # Shared pytest fixtures and configuration
│
├── unit/                      # Unit tests (fast, isolated)
│   ├── test_audio_system.py
│   ├── test_emergency_detection.py
│   ├── test_noise_classifier.py
│   ├── test_iot_connection.py
│   ├── test_device_shadow_sync.py
│   ├── test_telemetry_publisher.py
│   ├── test_train_sklearn_demo.py
│   ├── test_flask_blueprints.py     # NEW: Flask API blueprint tests
│   └── test_celery_tasks.py         # NEW: Celery background task tests
│
├── integration/               # Integration tests (slower)
│   ├── verify_integration.py
│   ├── verify_playback_ready.py
│   └── verify_flask_app.py
│
├── validation/                # Validation tests
│   └── (validation scripts)
│
└── demos/                     # Demo scripts and examples
    ├── simple_anti_noise_demo.py
    ├── realtime_anti_noise_output.py
    └── anc_with_database.py
```

## Running Tests

### Prerequisites

```bash
# Install test dependencies
pip install -r requirements.txt

# Optional: Install test-specific packages
pip install pytest pytest-cov pytest-mock pytest-timeout
```

### Run All Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=src --cov=cloud --cov-report=html
```

### Run Specific Test Categories

```bash
# Unit tests only (fast)
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# Specific test file
pytest tests/unit/test_emergency_detection.py

# Specific test function
pytest tests/unit/test_iot_connection.py::TestIoTConnection::test_connect_success
```

### Run Tests by Marker

```bash
# Run only unit tests
pytest -m unit

# Run only Flask API tests
pytest -m flask

# Run only Celery task tests
pytest -m celery

# Run authentication tests
pytest -m auth

# Run audio processing tests
pytest -m audio

# Run ML tests (requires numpy, sklearn, etc.)
pytest -m ml

# Run backend integration tests
pytest -m integration_backend

# Skip slow tests
pytest -m "not slow"

# Combine markers (Flask and audio tests)
pytest -m "flask and audio"
```

### Continuous Integration

```bash
# Run tests suitable for CI (skip slow and external dependencies)
pytest -m "unit and not slow" --tb=short

# Generate JUnit XML report
pytest --junitxml=test-results.xml

# Generate coverage report
pytest --cov=src --cov-report=xml
```

## Test Categories

### Unit Tests (`tests/unit/`)

Fast, isolated tests that don't require external dependencies.

**Coverage:**
- Audio processing core functionality
- Emergency detection logic
- Noise classification
- IoT connection management
- Device shadow synchronization
- Telemetry publishing
- Training script utilities
- **Flask API blueprints** (auth, audio, sessions, users) - NEW
- **Celery background tasks** (audio processing, maintenance, ML services) - NEW

**Flask Blueprints Tests** (`test_flask_blueprints.py`):
- Authentication middleware (JWT tokens, API keys)
- Audio processing endpoints (process, classify, detect emergency)
- Session management endpoints
- User management endpoints
- App factory pattern validation
- Service mocking and dependency injection

**Celery Tasks Tests** (`test_celery_tasks.py`):
- Audio file processing with progress tracking
- Chunk-based processing with metadata updates
- Maintenance and cleanup tasks
- Database interactions and transaction handling
- ML service wrapper and inference tasks
- Task state management (pending, progress, success, failure)

**Run:**
```bash
# All unit tests
pytest tests/unit/ -v

# Flask tests only
pytest tests/unit/test_flask_blueprints.py -v

# Celery tests only
pytest tests/unit/test_celery_tasks.py -v

# Using markers
pytest -m flask
pytest -m celery
pytest -m audio
pytest -m auth
```

### Integration Tests (`tests/integration/`)

Tests that verify component interactions and may require external services.

**Coverage:**
- End-to-end ANC pipeline
- Flask API integration
- Database operations
- WebSocket streaming

**Run:**
```bash
pytest tests/integration/ -v
```

### Demo Scripts (`tests/demos/`)

Executable demonstrations of specific features (not automated tests).

**Run manually:**
```bash
python tests/demos/simple_anti_noise_demo.py
python tests/demos/realtime_anti_noise_output.py
```

## Fixtures and conftest.py

The `conftest.py` file provides shared fixtures for all tests:

### Flask Fixtures

```python
@pytest.fixture(scope='function')
def flask_app():
    """Create a Flask app instance for testing with app factory pattern."""
    # Returns a configured test Flask app

@pytest.fixture(scope='function')
def client(flask_app):
    """Create a Flask test client for making HTTP requests."""
    # Returns test client for the app

@pytest.fixture
def mock_user():
    """Create a mock user object for authentication tests."""
    # Returns a mock User model with test data
```

### Audio Data Fixtures

```python
@pytest.fixture
def sample_audio_data():
    """Generate synthetic audio data (base64-encoded)."""
    # Returns 1 second of 440 Hz tone as base64

@pytest.fixture
def sample_audio_raw():
    """Generate raw audio numpy array."""
    # Returns numpy audio array

@pytest.fixture
def emergency_audio_data():
    """Generate synthetic emergency sound (fire alarm-like)."""
    # Returns emergency sound as base64
```

### Service Fixtures

```python
@pytest.fixture
def mock_anc_service():
    """Create a mock ANCService for testing."""
    # Returns mocked ANCService with process_audio

@pytest.fixture
def mock_ml_service():
    """Create a mock MLService for testing."""
    # Returns mocked MLService with classify_noise and detect_emergency
```

### Celery Fixtures

```python
@pytest.fixture(scope='session')
def celery_config():
    """Configure Celery for testing with eager mode."""
    # Returns Celery config with task_always_eager=True

@pytest.fixture
def mock_celery_task():
    """Create a mock Celery task for testing."""
    # Returns mock task with update_state method
```

## Writing New Tests

### Unit Test Template (Modern)

```python
"""
Unit Tests for [Module Name]
==============================

Description of what this test module covers.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch

pytestmark = [pytest.mark.unit]  # Mark all tests in this module


@pytest.mark.flask
class TestMyFeature:
    """Test [ClassName] class."""

    def test_[feature_name](self, client, mock_user):
        """Test [specific feature]."""
        # Arrange
        with patch('module.Service') as mock_service:
            # Setup mocks
            pass

        # Act
        response = client.get('/api/endpoint')

        # Assert
        assert response.status_code == 200
```

### Flask Test Template

```python
@pytest.mark.flask
class TestFlaskEndpoint:
    """Test Flask API endpoints."""

    def test_endpoint_success(self, client, mock_user, mock_anc_service):
        """Test successful endpoint request."""
        with patch('backend.api.audio.anc_service', mock_anc_service):
            response = client.post(
                '/api/audio/process',
                data=json.dumps({'audio_data': 'test'}),
                content_type='application/json',
                headers={'Authorization': 'Bearer test-token'}
            )
            assert response.status_code in [200, 401]

    def test_endpoint_auth_required(self, client):
        """Test endpoint requires authentication."""
        response = client.get('/api/protected')
        assert response.status_code == 401
```

### Celery Task Test Template

```python
@pytest.mark.celery
class TestCeleryTask:
    """Test Celery background task."""

    @patch('src.api.tasks.config')
    def test_task_with_config(self, mock_config, mock_celery_task):
        """Test task with mocked configuration."""
        mock_config.AUDIO_CHUNK_SIZE = 4096
        
        # Simulate task execution
        mock_celery_task.update_state(
            state='PROGRESS',
            meta={'current': 1, 'total': 10}
        )
        
        assert mock_celery_task.update_state.called
```

## Old Unit Test Template (unittest style)

```python
import pytest
import unittest
from unittest.mock import Mock, MagicMock, patch


class Test[ModuleName](unittest.TestCase):
    """Test [ClassName] class."""

    def setUp(self):
        """Set up test fixtures."""
        pass

    def tearDown(self):
        """Clean up after tests."""
        pass

    def test_[feature_name](self):
        """Test [specific feature]."""
        # Arrange
        pass

        # Act
        pass

        # Assert
        self.assertEqual(expected, actual)
```

### Integration Test Template

```python
"""
Integration Tests for [Feature Name]
====================================
"""

import pytest


@pytest.mark.integration
class TestIntegration[Feature]:
    """Integration tests for [feature]."""

    @pytest.fixture
    def setup_environment(self):
        """Set up test environment."""
        yield
        # Cleanup

    def test_[feature](self, setup_environment):
        """Test [feature] integration."""
        assert True
```

## Test Markers

Use markers to categorize tests:

```python
@pytest.mark.unit
def test_fast_unit():
    """Fast unit test."""
    pass

@pytest.mark.integration
def test_integration():
    """Integration test."""
    pass

@pytest.mark.slow
def test_slow_operation():
    """Test that takes >5 seconds."""
    pass

@pytest.mark.skipif(condition, reason="...")
def test_conditional():
    """Test that may be skipped."""
    pass
```

## Mocking External Dependencies

### Mock AWS IoT

```python
from unittest.mock import Mock, patch

@patch('cloud.iot.iot_connection.mqtt.Client')
def test_iot_connection(mock_mqtt):
    """Test with mocked MQTT client."""
    mock_mqtt.return_value = Mock()
    # Test code here
```

### Mock ML Models

```python
@patch('src.ml.emergency_noise_detector.pickle.load')
def test_emergency_detector(mock_load):
    """Test with mocked ML model."""
    mock_model = Mock()
    mock_model.predict.return_value = np.array([0])
    mock_load.return_value = {'model': mock_model}
    # Test code here
```

## Test Data

### Synthetic Test Data

Tests that require audio data use synthetic data generation:

```python
import numpy as np

def generate_test_audio(duration=1.0, sample_rate=44100):
    """Generate synthetic audio for testing."""
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio = 0.5 * np.sin(2 * np.pi * 440 * t)  # 440 Hz tone
    return audio
```

### Test Fixtures

```python
@pytest.fixture
def sample_audio():
    """Provide sample audio data."""
    return np.random.randn(44100)

@pytest.fixture
def mock_iot_connection():
    """Provide mock IoT connection."""
    return Mock()
```

## Coverage

### Generate Coverage Report

```bash
# Terminal report
pytest --cov=src --cov=cloud --cov-report=term-missing

# HTML report
pytest --cov=src --cov=cloud --cov-report=html
open htmlcov/index.html

# XML report (for CI)
pytest --cov=src --cov=cloud --cov-report=xml
```

### Coverage Goals

| Component | Current | Target |
|-----------|---------|--------|
| Core ANC | TBD | >80% |
| ML Models | TBD | >70% |
| IoT Integration | TBD | >75% |
| API Endpoints | TBD | >80% |
| Flask Blueprints | NEW | >85% |
| Celery Tasks | NEW | >80% |
| Authentication Middleware | NEW | >85% |

### Coverage Configuration

Coverage is configured in `pytest.ini` and `.coveragerc`. To generate a coverage report:

```bash
# Generate coverage report in terminal
pytest --cov=backend --cov=src --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=backend --cov=src --cov-report=html
open htmlcov/index.html

# Generate XML report for CI
pytest --cov=backend --cov=src --cov-report=xml

# Coverage badge (if using codecov)
# Add to README.md:
# [![codecov](https://codecov.io/gh/[org]/[repo]/branch/main/graph/badge.svg)](https://codecov.io/gh/[org]/[repo])
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-mock
      - name: Run unit tests
        run: pytest tests/unit/ -v --cov=backend --cov=src --cov-report=term-missing
      - name: Run Flask API tests
        run: pytest tests/unit/test_flask_blueprints.py -v -m flask
      - name: Run Celery task tests
        run: pytest tests/unit/test_celery_tasks.py -v -m celery
      - name: Run integration tests
        run: pytest tests/integration/ -v
      - name: Generate coverage report
        run: pytest --cov=backend --cov=src --cov-report=xml --cov-report=html
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

### Running Tests Locally

For development, use the `Makefile` target or run directly:

```bash
# Run all tests
pytest

# Run specific test suites
pytest tests/unit/test_flask_blueprints.py  # Flask tests
pytest tests/unit/test_celery_tasks.py      # Celery tests

# Run tests with coverage
pytest --cov=backend --cov=src --cov-report=html

# Run fast tests only (skip slow markers)
pytest -m "not slow"

# Run Flask + auth tests only
pytest -m "flask and auth"
```

## Troubleshooting

### ImportError: No module named 'X'

Install missing dependencies:
```bash
pip install -r requirements.txt
```

### Tests Hang or Timeout

Increase timeout or skip slow tests:
```bash
pytest -m "not slow"
```

### Mock Not Working

Ensure correct import path:
```python
# Wrong
@patch('module.Class')

# Correct (patch where it's used, not where it's defined)
@patch('tests.unit.test_module.Class')
```

### Fixtures Not Found

Ensure fixture is in same file or conftest.py:
```python
# tests/conftest.py
import pytest

@pytest.fixture
def shared_fixture():
    return "shared"
```

## Best Practices

1. **AAA Pattern**: Arrange, Act, Assert
2. **One assertion per test**: Test one thing at a time
3. **Use descriptive names**: `test_emergency_detector_bypasses_anc_for_fire_alarm`
4. **Mock external dependencies**: Don't test AWS IoT, test your code
5. **Clean up**: Use tearDown or fixtures to clean up
6. **Fast tests**: Unit tests should run in <1s each
7. **Deterministic**: Tests should always give same result
8. **Independent**: Tests shouldn't depend on each other

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [unittest documentation](https://docs.python.org/3/library/unittest.html)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
- [Best practices](https://docs.pytest.org/en/latest/goodpractices.html)

## Support

For test-related questions:
- Check existing tests for examples
- See pytest documentation
- Open GitHub issue with `[tests]` prefix
