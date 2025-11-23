"""
Unit Tests for IoT Connection Module
=====================================

Tests the AWS IoT MQTT connection management functionality.
"""

import pytest
import unittest
from unittest.mock import Mock, MagicMock, patch, call
import json
import time
from pathlib import Path
import tempfile
import os


# Mock paho.mqtt if not installed
try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None

# Skip all tests if paho-mqtt not installed
pytestmark = pytest.mark.skipif(
    mqtt is None,
    reason="paho-mqtt not installed"
)


class TestIoTConnection(unittest.TestCase):
    """Test IoTConnection class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary certificate files
        self.temp_dir = tempfile.mkdtemp()
        self.cert_path = os.path.join(self.temp_dir, 'cert.pem')
        self.key_path = os.path.join(self.temp_dir, 'private.key')
        self.root_ca_path = os.path.join(self.temp_dir, 'root-ca.pem')

        # Create dummy cert files
        for path in [self.cert_path, self.key_path, self.root_ca_path]:
            Path(path).touch()

        # Mock MQTT client
        self.mock_mqtt_client = MagicMock()

        # Patch MQTT Client
        self.mqtt_patcher = patch('cloud.iot.iot_connection.mqtt.Client')
        self.mock_mqtt_class = self.mqtt_patcher.start()
        self.mock_mqtt_class.return_value = self.mock_mqtt_client

    def tearDown(self):
        """Clean up test fixtures."""
        self.mqtt_patcher.stop()

        # Clean up temp files
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_initialization(self):
        """Test IoTConnection initialization."""
        from cloud.iot.iot_connection import IoTConnection

        iot = IoTConnection(
            thing_name='test-thing',
            endpoint='test.iot.us-east-1.amazonaws.com',
            cert_path=self.cert_path,
            key_path=self.key_path,
            root_ca_path=self.root_ca_path
        )

        self.assertEqual(iot.thing_name, 'test-thing')
        self.assertEqual(iot.endpoint, 'test.iot.us-east-1.amazonaws.com')
        self.assertFalse(iot.connected)
        self.assertEqual(len(iot.message_queue), 0)

    def test_missing_certificates(self):
        """Test initialization with missing certificates."""
        from cloud.iot.iot_connection import IoTConnection

        with self.assertRaises(FileNotFoundError):
            IoTConnection(
                thing_name='test-thing',
                endpoint='test.iot.us-east-1.amazonaws.com',
                cert_path='/nonexistent/cert.pem',
                key_path=self.key_path,
                root_ca_path=self.root_ca_path
            )

    def test_connect_success(self):
        """Test successful connection."""
        from cloud.iot.iot_connection import IoTConnection

        iot = IoTConnection(
            thing_name='test-thing',
            endpoint='test.iot.us-east-1.amazonaws.com',
            cert_path=self.cert_path,
            key_path=self.key_path,
            root_ca_path=self.root_ca_path
        )

        # Simulate successful connection
        def simulate_connect(*args, **kwargs):
            iot._on_connect(None, None, None, 0)
            return 0

        self.mock_mqtt_client.connect.side_effect = simulate_connect

        result = iot.connect()

        self.assertTrue(result)
        self.assertTrue(iot.connected)
        self.mock_mqtt_client.connect.assert_called_once()
        self.mock_mqtt_client.loop_start.assert_called_once()

    def test_publish_when_connected(self):
        """Test publishing message when connected."""
        from cloud.iot.iot_connection import IoTConnection

        iot = IoTConnection(
            thing_name='test-thing',
            endpoint='test.iot.us-east-1.amazonaws.com',
            cert_path=self.cert_path,
            key_path=self.key_path,
            root_ca_path=self.root_ca_path
        )

        # Set as connected
        iot.connected = True

        # Mock successful publish
        mock_result = Mock()
        mock_result.rc = 0  # MQTT_ERR_SUCCESS
        self.mock_mqtt_client.publish.return_value = mock_result

        # Publish message
        payload = {'status': 'online', 'value': 42}
        result = iot.publish('test/topic', payload, qos=1)

        self.assertTrue(result)
        self.mock_mqtt_client.publish.assert_called_once()

        # Verify payload was JSON encoded
        call_args = self.mock_mqtt_client.publish.call_args
        self.assertEqual(call_args[0][0], 'test/topic')
        self.assertEqual(json.loads(call_args[0][1]), payload)

    def test_publish_when_disconnected_queues_message(self):
        """Test publishing when disconnected queues the message."""
        from cloud.iot.iot_connection import IoTConnection

        iot = IoTConnection(
            thing_name='test-thing',
            endpoint='test.iot.us-east-1.amazonaws.com',
            cert_path=self.cert_path,
            key_path=self.key_path,
            root_ca_path=self.root_ca_path
        )

        # Ensure disconnected
        iot.connected = False

        # Publish message
        payload = {'status': 'offline'}
        result = iot.publish('test/topic', payload)

        self.assertFalse(result)  # Publish returns False when queued
        self.assertEqual(len(iot.message_queue), 1)
        self.assertEqual(iot.message_queue[0][0], 'test/topic')

    def test_subscribe(self):
        """Test topic subscription."""
        from cloud.iot.iot_connection import IoTConnection

        iot = IoTConnection(
            thing_name='test-thing',
            endpoint='test.iot.us-east-1.amazonaws.com',
            cert_path=self.cert_path,
            key_path=self.key_path,
            root_ca_path=self.root_ca_path
        )

        # Set as connected
        iot.connected = True

        # Subscribe to topic
        handler = Mock()
        iot.subscribe('test/topic/#', handler, qos=1)

        self.assertIn('test/topic/#', iot.message_handlers)
        self.mock_mqtt_client.subscribe.assert_called_once_with('test/topic/#', qos=1)

    def test_message_handler_called(self):
        """Test message handler is called on message receipt."""
        from cloud.iot.iot_connection import IoTConnection

        iot = IoTConnection(
            thing_name='test-thing',
            endpoint='test.iot.us-east-1.amazonaws.com',
            cert_path=self.cert_path,
            key_path=self.key_path,
            root_ca_path=self.root_ca_path
        )

        # Set up handler
        handler = Mock()
        iot.subscribe('test/topic', handler)

        # Simulate message receipt
        mock_message = Mock()
        mock_message.topic = 'test/topic'
        mock_message.payload = json.dumps({'value': 123}).encode('utf-8')

        iot._on_message(None, None, mock_message)

        # Verify handler was called
        handler.assert_called_once()
        call_args = handler.call_args[0]
        self.assertEqual(call_args[0], 'test/topic')
        self.assertEqual(call_args[1], {'value': 123})

    def test_topic_matching_with_wildcards(self):
        """Test topic matching with wildcards."""
        from cloud.iot.iot_connection import IoTConnection

        iot = IoTConnection(
            thing_name='test-thing',
            endpoint='test.iot.us-east-1.amazonaws.com',
            cert_path=self.cert_path,
            key_path=self.key_path,
            root_ca_path=self.root_ca_path
        )

        # Test single-level wildcard (+)
        self.assertTrue(iot._topic_matches('devices/device1/status', 'devices/+/status'))
        self.assertFalse(iot._topic_matches('devices/device1/other', 'devices/+/status'))

        # Test multi-level wildcard (#)
        self.assertTrue(iot._topic_matches('devices/device1/status', 'devices/#'))
        self.assertTrue(iot._topic_matches('devices/device1/status/battery', 'devices/#'))
        self.assertFalse(iot._topic_matches('other/device1', 'devices/#'))

    def test_disconnect(self):
        """Test disconnect functionality."""
        from cloud.iot.iot_connection import IoTConnection

        iot = IoTConnection(
            thing_name='test-thing',
            endpoint='test.iot.us-east-1.amazonaws.com',
            cert_path=self.cert_path,
            key_path=self.key_path,
            root_ca_path=self.root_ca_path
        )

        iot.connected = True
        iot.disconnect()

        self.assertFalse(iot.connected)
        self.assertFalse(iot.auto_reconnect)
        self.mock_mqtt_client.loop_stop.assert_called_once()
        self.mock_mqtt_client.disconnect.assert_called_once()

    def test_get_status(self):
        """Test status reporting."""
        from cloud.iot.iot_connection import IoTConnection

        iot = IoTConnection(
            thing_name='test-thing',
            endpoint='test.iot.us-east-1.amazonaws.com',
            cert_path=self.cert_path,
            key_path=self.key_path,
            root_ca_path=self.root_ca_path
        )

        iot.connected = True
        iot.subscribe('test/topic', Mock())
        iot.message_queue.append(('topic', {}, 1, False))

        status = iot.get_status()

        self.assertEqual(status['thing_name'], 'test-thing')
        self.assertTrue(status['connected'])
        self.assertEqual(status['queued_messages'], 1)
        self.assertEqual(len(status['subscriptions']), 1)
        self.assertIn('timestamp', status)


class TestIoTConnectionEdgeCases(unittest.TestCase):
    """Test edge cases and error scenarios."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.cert_path = os.path.join(self.temp_dir, 'cert.pem')
        self.key_path = os.path.join(self.temp_dir, 'private.key')
        self.root_ca_path = os.path.join(self.temp_dir, 'root-ca.pem')

        for path in [self.cert_path, self.key_path, self.root_ca_path]:
            Path(path).touch()

        self.mqtt_patcher = patch('cloud.iot.iot_connection.mqtt.Client')
        self.mock_mqtt_class = self.mqtt_patcher.start()
        self.mock_mqtt_client = MagicMock()
        self.mock_mqtt_class.return_value = self.mock_mqtt_client

    def tearDown(self):
        """Clean up."""
        self.mqtt_patcher.stop()
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_message_queue_limit(self):
        """Test message queue has maximum size."""
        from cloud.iot.iot_connection import IoTConnection

        iot = IoTConnection(
            thing_name='test-thing',
            endpoint='test.iot.us-east-1.amazonaws.com',
            cert_path=self.cert_path,
            key_path=self.key_path,
            root_ca_path=self.root_ca_path
        )

        iot.connected = False
        iot.max_queue_size = 5

        # Try to queue more than max
        for i in range(10):
            iot.publish(f'topic/{i}', {'value': i})

        # Should only keep max_queue_size messages
        self.assertEqual(len(iot.message_queue), 5)

    def test_invalid_json_in_message(self):
        """Test handling of invalid JSON in received message."""
        from cloud.iot.iot_connection import IoTConnection

        iot = IoTConnection(
            thing_name='test-thing',
            endpoint='test.iot.us-east-1.amazonaws.com',
            cert_path=self.cert_path,
            key_path=self.key_path,
            root_ca_path=self.root_ca_path
        )

        handler = Mock()
        iot.subscribe('test/topic', handler)

        # Simulate message with invalid JSON
        mock_message = Mock()
        mock_message.topic = 'test/topic'
        mock_message.payload = b'invalid{json'

        # Should not raise exception, just log error
        iot._on_message(None, None, mock_message)

        # Handler should not be called
        handler.assert_not_called()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
