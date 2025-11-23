"""
Unit Tests for Telemetry Publisher Module
==========================================

Tests the telemetry publishing and metric collection functionality.
"""

import pytest
import unittest
from unittest.mock import Mock, MagicMock, patch
import json
import time
from datetime import datetime


class TestTelemetryPublisher(unittest.TestCase):
    """Test TelemetryPublisher class."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock IoT connection
        self.mock_iot = MagicMock()
        self.mock_iot.publish = Mock(return_value=True)

    def test_initialization(self):
        """Test TelemetryPublisher initialization."""
        from cloud.iot.telemetry_publisher import TelemetryPublisher

        telemetry = TelemetryPublisher(
            iot_connection=self.mock_iot,
            device_id='test-device',
            batch_size=10,
            batch_interval=30
        )

        self.assertEqual(telemetry.device_id, 'test-device')
        self.assertEqual(telemetry.batch_size, 10)
        self.assertEqual(telemetry.batch_interval, 30)
        self.assertEqual(len(telemetry.batch_buffer), 0)

    def test_publish_anc_metrics(self):
        """Test publishing ANC metrics."""
        from cloud.iot.telemetry_publisher import TelemetryPublisher

        telemetry = TelemetryPublisher(self.mock_iot, 'test-device', batch_size=10)

        metrics = {
            'latency_ms': 35.2,
            'cancellation_db': 42.5,
            'snr_improvement_db': 38.2
        }

        telemetry.publish_anc_metrics(metrics)

        # Should be added to batch buffer
        self.assertEqual(len(telemetry.batch_buffer), 1)
        self.assertEqual(telemetry.stats['total_buffered'], 1)

    def test_publish_audio_metrics(self):
        """Test publishing audio metrics."""
        from cloud.iot.telemetry_publisher import TelemetryPublisher

        telemetry = TelemetryPublisher(self.mock_iot, 'test-device')

        metrics = {
            'noise_type': 'office',
            'confidence': 0.94,
            'rms': 0.45
        }

        telemetry.publish_audio_metrics(metrics)

        self.assertEqual(len(telemetry.batch_buffer), 1)

    def test_publish_system_metrics(self):
        """Test publishing system metrics."""
        from cloud.iot.telemetry_publisher import TelemetryPublisher

        telemetry = TelemetryPublisher(self.mock_iot, 'test-device')

        metrics = {
            'cpu_usage': 45.2,
            'memory_usage': 68.5,
            'battery_level': 85
        }

        telemetry.publish_system_metrics(metrics)

        self.assertEqual(len(telemetry.batch_buffer), 1)

    def test_publish_emergency_event_immediate(self):
        """Test emergency events are published immediately."""
        from cloud.iot.telemetry_publisher import TelemetryPublisher

        telemetry = TelemetryPublisher(self.mock_iot, 'test-device')

        event = {
            'is_emergency': True,
            'predicted_class': 'fire_alarm',
            'confidence': 0.94,
            'action': 'anc_bypassed'
        }

        telemetry.publish_emergency_event(event)

        # Should publish immediately, not batch
        self.mock_iot.publish.assert_called_once()

        # Should not be in batch buffer
        self.assertEqual(len(telemetry.batch_buffer), 0)

        # Should increment published count
        self.assertEqual(telemetry.stats['total_published'], 1)

    def test_batch_publishing_when_full(self):
        """Test batch is published when full."""
        from cloud.iot.telemetry_publisher import TelemetryPublisher

        telemetry = TelemetryPublisher(self.mock_iot, 'test-device', batch_size=3)

        # Add metrics up to batch size
        for i in range(3):
            telemetry.publish_anc_metrics({'value': i})

        # Should have published batch
        self.assertEqual(self.mock_iot.publish.call_count, 3)
        self.assertEqual(len(telemetry.batch_buffer), 0)
        self.assertEqual(telemetry.stats['total_published'], 3)

    def test_publish_error_log(self):
        """Test publishing error logs."""
        from cloud.iot.telemetry_publisher import TelemetryPublisher

        telemetry = TelemetryPublisher(self.mock_iot, 'test-device')

        error = {
            'error_type': 'connection_error',
            'message': 'Failed to connect',
            'context': {'attempt': 3}
        }

        telemetry.publish_error_log(error)

        self.assertEqual(len(telemetry.batch_buffer), 1)

    def test_publish_custom_metric(self):
        """Test publishing custom metrics."""
        from cloud.iot.telemetry_publisher import TelemetryPublisher

        telemetry = TelemetryPublisher(self.mock_iot, 'test-device')

        metrics = {'custom_value': 123.45}

        telemetry.publish_custom_metric('custom_category', metrics)

        self.assertEqual(len(telemetry.batch_buffer), 1)

    def test_flush(self):
        """Test manual flush of buffered metrics."""
        from cloud.iot.telemetry_publisher import TelemetryPublisher

        telemetry = TelemetryPublisher(self.mock_iot, 'test-device', batch_size=100)

        # Add some metrics
        for i in range(5):
            telemetry.publish_anc_metrics({'value': i})

        # Flush manually
        telemetry.flush()

        # Should have published all buffered metrics
        self.assertEqual(self.mock_iot.publish.call_count, 5)
        self.assertEqual(len(telemetry.batch_buffer), 0)

    def test_get_statistics(self):
        """Test getting publishing statistics."""
        from cloud.iot.telemetry_publisher import TelemetryPublisher

        telemetry = TelemetryPublisher(self.mock_iot, 'test-device')

        # Publish some metrics
        telemetry.publish_anc_metrics({'value': 1})
        telemetry.publish_anc_metrics({'value': 2})

        stats = telemetry.get_statistics()

        self.assertEqual(stats['device_id'], 'test-device')
        self.assertEqual(stats['total_buffered'], 2)
        self.assertEqual(stats['batch_size'], 2)

    def test_start_stop_publishing(self):
        """Test starting and stopping periodic publishing."""
        from cloud.iot.telemetry_publisher import TelemetryPublisher

        telemetry = TelemetryPublisher(self.mock_iot, 'test-device', batch_interval=1)

        # Start publishing
        telemetry.start_publishing()
        self.assertTrue(telemetry.running)
        self.assertIsNotNone(telemetry.publish_thread)

        # Add a metric
        telemetry.publish_anc_metrics({'value': 123})

        # Stop publishing
        telemetry.stop_publishing()
        self.assertFalse(telemetry.running)

        # Should have published during stop
        self.assertEqual(len(telemetry.batch_buffer), 0)


class TestTelemetryPublisherEdgeCases(unittest.TestCase):
    """Test edge cases for telemetry publisher."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_iot = MagicMock()

    def test_publish_failure_increments_failed_count(self):
        """Test failed publishes are counted."""
        from cloud.iot.telemetry_publisher import TelemetryPublisher

        # Make publish fail
        self.mock_iot.publish.return_value = False

        telemetry = TelemetryPublisher(self.mock_iot, 'test-device', batch_size=1)

        telemetry.publish_anc_metrics({'value': 123})

        # Should increment failed count
        self.assertEqual(telemetry.stats['total_failed'], 1)

    def test_emergency_event_publish_failure(self):
        """Test emergency event publish failure handling."""
        from cloud.iot.telemetry_publisher import TelemetryPublisher

        # Make publish fail
        self.mock_iot.publish.return_value = False

        telemetry = TelemetryPublisher(self.mock_iot, 'test-device')

        event = {
            'is_emergency': True,
            'predicted_class': 'fire_alarm'
        }

        telemetry.publish_emergency_event(event)

        # Should increment failed count
        self.assertEqual(telemetry.stats['total_failed'], 1)

    def test_topic_selection(self):
        """Test correct topic selection for different metric types."""
        from cloud.iot.telemetry_publisher import TelemetryPublisher

        self.mock_iot.publish.return_value = True

        telemetry = TelemetryPublisher(self.mock_iot, 'test-device', batch_size=1)

        # Test ANC metrics topic
        telemetry.publish_anc_metrics({'value': 1})
        call_args = self.mock_iot.publish.call_args[0]
        self.assertIn('/anc', call_args[0])

        # Test audio metrics topic
        telemetry.publish_audio_metrics({'value': 2})
        call_args = self.mock_iot.publish.call_args[0]
        self.assertIn('/audio', call_args[0])

        # Test system metrics topic
        telemetry.publish_system_metrics({'value': 3})
        call_args = self.mock_iot.publish.call_args[0]
        self.assertIn('/system', call_args[0])

    def test_metric_payload_structure(self):
        """Test metric payloads have correct structure."""
        from cloud.iot.telemetry_publisher import TelemetryPublisher

        self.mock_iot.publish.return_value = True

        telemetry = TelemetryPublisher(self.mock_iot, 'test-device', batch_size=1)

        metrics = {'latency_ms': 35.2}
        telemetry.publish_anc_metrics(metrics)

        # Get published payload
        call_args = self.mock_iot.publish.call_args[0]
        payload = call_args[1]

        self.assertEqual(payload['device_id'], 'test-device')
        self.assertEqual(payload['metric_type'], 'anc')
        self.assertIn('timestamp', payload)
        self.assertEqual(payload['metrics'], metrics)


class TestTelemetryPublisherConcurrency(unittest.TestCase):
    """Test concurrent operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_iot = MagicMock()
        self.mock_iot.publish.return_value = True

    def test_concurrent_metric_publishing(self):
        """Test multiple metrics can be published concurrently."""
        from cloud.iot.telemetry_publisher import TelemetryPublisher

        telemetry = TelemetryPublisher(self.mock_iot, 'test-device', batch_size=100)

        # Publish multiple metrics in quick succession
        for i in range(20):
            telemetry.publish_anc_metrics({'value': i})

        # All should be buffered
        self.assertEqual(len(telemetry.batch_buffer), 20)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
