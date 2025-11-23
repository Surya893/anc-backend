# ANC Platform Tests

Comprehensive test suite for the ANC Platform including unit tests, integration tests, and demos.

## Test Structure

```
tests/
├── unit/                      # Unit tests (fast, isolated)
│   ├── test_audio_system.py
│   ├── test_emergency_detection.py
│   ├── test_noise_classifier.py
│   ├── test_iot_connection.py
│   ├── test_device_shadow_sync.py
│   ├── test_telemetry_publisher.py
│   └── test_train_sklearn_demo.py
│
├── integration/               # Integration tests (slower)
│   ├── verify_integration.py
│   ├── verify_playback_ready.py
│   └── verify_flask_app.py
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

# Run only IoT-related tests
pytest -m iot

# Skip slow tests
pytest -m "not slow"

# Run ML tests (requires numpy, sklearn, etc.)
pytest -m ml
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

**Run:**
```bash
pytest tests/unit/ -v
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

## Writing New Tests

### Unit Test Template

```python
"""
Unit Tests for [Module Name]
==============================

Description of what this test module covers.
"""

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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
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
          pip install pytest pytest-cov
      - name: Run tests
        run: pytest --cov=src --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
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
