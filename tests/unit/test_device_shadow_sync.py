"""
Unit Tests for Device Shadow Sync Module
=========================================

Tests the AWS IoT Device Shadow synchronization functionality.
"""

import pytest
import unittest
from unittest.mock import Mock, MagicMock, patch, call
import json
import time


class TestDeviceShadowSync(unittest.TestCase):
    """Test DeviceShadowSync class."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock IoT connection
        self.mock_iot = MagicMock()
        self.mock_iot.publish = Mock(return_value=True)
        self.mock_iot.subscribe = Mock()

    def test_initialization(self):
        """Test DeviceShadowSync initialization."""
        from cloud.iot.device_shadow_sync import DeviceShadowSync

        shadow = DeviceShadowSync(
            iot_connection=self.mock_iot,
            thing_name='test-thing',
            sync_interval=30
        )

        self.assertEqual(shadow.thing_name, 'test-thing')
        self.assertEqual(shadow.sync_interval, 30)
        self.assertEqual(len(shadow.reported_state), 0)
        self.assertEqual(len(shadow.desired_state), 0)

        # Verify subscriptions
        self.assertEqual(self.mock_iot.subscribe.call_count, 4)

    def test_update_reported_state(self):
        """Test updating reported state."""
        from cloud.iot.device_shadow_sync import DeviceShadowSync

        shadow = DeviceShadowSync(self.mock_iot, 'test-thing')

        state = {'temperature': 25.5, 'humidity': 60}
        result = shadow.update_reported_state(state)

        self.assertTrue(result)
        self.assertEqual(shadow.reported_state['temperature'], 25.5)
        self.assertEqual(shadow.reported_state['humidity'], 60)
        self.assertIn('timestamp', shadow.reported_state)

        # Verify publish was called
        self.mock_iot.publish.assert_called_once()
        call_args = self.mock_iot.publish.call_args
        self.assertIn('shadow/update', call_args[0][0])

    def test_update_reported_state_merge(self):
        """Test merging reported state."""
        from cloud.iot.device_shadow_sync import DeviceShadowSync

        shadow = DeviceShadowSync(self.mock_iot, 'test-thing')

        # First update
        shadow.update_reported_state({'temperature': 25.5})

        # Second update with merge=True (default)
        shadow.update_reported_state({'humidity': 60})

        # Both values should be present
        self.assertEqual(shadow.reported_state['temperature'], 25.5)
        self.assertEqual(shadow.reported_state['humidity'], 60)

    def test_update_reported_state_replace(self):
        """Test replacing reported state."""
        from cloud.iot.device_shadow_sync import DeviceShadowSync

        shadow = DeviceShadowSync(self.mock_iot, 'test-thing')

        # First update
        shadow.update_reported_state({'temperature': 25.5})

        # Second update with merge=False
        shadow.update_reported_state({'humidity': 60}, merge=False)

        # Only humidity should be present
        self.assertNotIn('temperature', shadow.reported_state)
        self.assertEqual(shadow.reported_state['humidity'], 60)

    def test_request_desired_state(self):
        """Test requesting desired state."""
        from cloud.iot.device_shadow_sync import DeviceShadowSync

        shadow = DeviceShadowSync(self.mock_iot, 'test-thing')

        result = shadow.request_desired_state()

        self.assertTrue(result)
        self.mock_iot.publish.assert_called()

        # Verify correct topic
        call_args = self.mock_iot.publish.call_args
        self.assertIn('shadow/get', call_args[0][0])

    def test_clear_desired_state(self):
        """Test clearing desired state."""
        from cloud.iot.device_shadow_sync import DeviceShadowSync

        shadow = DeviceShadowSync(self.mock_iot, 'test-thing')

        # Set some desired state
        shadow.desired_state = {'setting1': 'value1', 'setting2': 'value2'}

        # Clear specific keys
        result = shadow.clear_desired_state(['setting1'])

        self.assertTrue(result)
        self.mock_iot.publish.assert_called()

    def test_delta_handler_called(self):
        """Test delta handler is called on delta receipt."""
        from cloud.iot.device_shadow_sync import DeviceShadowSync

        shadow = DeviceShadowSync(self.mock_iot, 'test-thing')

        # Set delta callback
        delta_handler = Mock()
        shadow.on_delta_callback = delta_handler

        # Simulate delta message
        delta_payload = {
            'state': {
                'setting1': 'new_value'
            }
        }

        shadow._on_delta_received('delta/topic', delta_payload)

        # Verify callback was called
        delta_handler.assert_called_once_with({'setting1': 'new_value'})

        # Verify desired state was updated
        self.assertEqual(shadow.desired_state['setting1'], 'new_value')

    def test_get_accepted_handler(self):
        """Test handling of get accepted response."""
        from cloud.iot.device_shadow_sync import DeviceShadowSync

        shadow = DeviceShadowSync(self.mock_iot, 'test-thing')

        # Simulate get response
        get_payload = {
            'state': {
                'reported': {
                    'temperature': 25.5
                },
                'desired': {
                    'target_temp': 26.0
                }
            }
        }

        shadow._on_get_accepted('get/accepted', get_payload)

        # Verify states were updated
        self.assertEqual(shadow.reported_state['temperature'], 25.5)
        self.assertEqual(shadow.desired_state['target_temp'], 26.0)

    def test_update_rejected_handler(self):
        """Test handling of update rejected response."""
        from cloud.iot.device_shadow_sync import DeviceShadowSync

        shadow = DeviceShadowSync(self.mock_iot, 'test-thing')

        # Simulate rejected response (should just log, not crash)
        rejected_payload = {
            'code': 400,
            'message': 'Invalid request'
        }

        # Should not raise exception
        shadow._on_update_rejected('update/rejected', rejected_payload)

    def test_get_state(self):
        """Test getting current shadow state."""
        from cloud.iot.device_shadow_sync import DeviceShadowSync

        shadow = DeviceShadowSync(self.mock_iot, 'test-thing')

        shadow.reported_state = {'temp': 25}
        shadow.desired_state = {'target': 26}
        shadow.metadata = {'version': 1}

        state = shadow.get_state()

        self.assertEqual(state['reported']['temp'], 25)
        self.assertEqual(state['desired']['target'], 26)
        self.assertEqual(state['metadata']['version'], 1)

    def test_get_reported_value(self):
        """Test getting value from reported state."""
        from cloud.iot.device_shadow_sync import DeviceShadowSync

        shadow = DeviceShadowSync(self.mock_iot, 'test-thing')

        shadow.reported_state = {'temperature': 25.5}

        self.assertEqual(shadow.get_reported_value('temperature'), 25.5)
        self.assertIsNone(shadow.get_reported_value('nonexistent'))
        self.assertEqual(shadow.get_reported_value('nonexistent', 'default'), 'default')

    def test_sync_loop_start_stop(self):
        """Test starting and stopping sync loop."""
        from cloud.iot.device_shadow_sync import DeviceShadowSync

        shadow = DeviceShadowSync(self.mock_iot, 'test-thing', sync_interval=1)

        # Start sync
        shadow.start_sync()
        self.assertTrue(shadow.running)
        self.assertIsNotNone(shadow.sync_thread)

        # Stop sync
        shadow.stop_sync()
        self.assertFalse(shadow.running)


class TestDeviceShadowSyncEdgeCases(unittest.TestCase):
    """Test edge cases for device shadow sync."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_iot = MagicMock()
        self.mock_iot.publish = Mock(return_value=True)
        self.mock_iot.subscribe = Mock()

    def test_publish_failure_handling(self):
        """Test handling of publish failures."""
        from cloud.iot.device_shadow_sync import DeviceShadowSync

        # Make publish fail
        self.mock_iot.publish.return_value = False

        shadow = DeviceShadowSync(self.mock_iot, 'test-thing')

        result = shadow.update_reported_state({'value': 123})

        self.assertFalse(result)

    def test_delta_with_missing_state(self):
        """Test delta message with missing state field."""
        from cloud.iot.device_shadow_sync import DeviceShadowSync

        shadow = DeviceShadowSync(self.mock_iot, 'test-thing')

        # Simulate malformed delta
        delta_payload = {}  # Missing 'state' field

        # Should not crash
        shadow._on_delta_received('delta/topic', delta_payload)

    def test_exception_in_delta_callback(self):
        """Test exception in delta callback doesn't crash."""
        from cloud.iot.device_shadow_sync import DeviceShadowSync

        shadow = DeviceShadowSync(self.mock_iot, 'test-thing')

        # Set callback that raises exception
        def bad_callback(delta):
            raise ValueError("Test error")

        shadow.on_delta_callback = bad_callback

        delta_payload = {'state': {'value': 123}}

        # Should log error but not crash
        shadow._on_delta_received('delta/topic', delta_payload)

        # State should still be updated
        self.assertEqual(shadow.desired_state['value'], 123)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
