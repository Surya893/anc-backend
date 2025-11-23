#!/usr/bin/env python3
"""
AWS IoT Connection Manager for ANC Devices
==========================================

Handles secure MQTT connection to AWS IoT Core with automatic reconnection,
certificate-based authentication, and message routing.

Usage:
    from iot_connection import IoTConnection

    iot = IoTConnection(
        thing_name='anc-device-001',
        endpoint='xxxxx.iot.us-east-1.amazonaws.com',
        cert_path='/path/to/cert.pem',
        key_path='/path/to/private.key',
        root_ca_path='/path/to/AmazonRootCA1.pem'
    )

    iot.connect()
    iot.publish('anc/devices/anc-device-001/status', {'status': 'online'})
"""

import json
import time
import logging
import ssl
import threading
from typing import Callable, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("Warning: paho-mqtt not installed. Install with: pip install paho-mqtt")
    mqtt = None


logger = logging.getLogger(__name__)


class IoTConnection:
    """
    Manages AWS IoT Core MQTT connection for ANC devices.

    Features:
    - Automatic reconnection with exponential backoff
    - Certificate-based authentication
    - Message queuing during disconnection
    - Topic-based subscription management
    - Connection status callbacks
    """

    def __init__(
        self,
        thing_name: str,
        endpoint: str,
        cert_path: str,
        key_path: str,
        root_ca_path: str,
        port: int = 8883,
        keep_alive: int = 60
    ):
        """
        Initialize IoT connection.

        Args:
            thing_name: AWS IoT thing name (device identifier)
            endpoint: AWS IoT endpoint (xxxxx.iot.region.amazonaws.com)
            cert_path: Path to device certificate (.pem)
            key_path: Path to private key (.key)
            root_ca_path: Path to Amazon Root CA certificate
            port: MQTT port (default: 8883 for TLS)
            keep_alive: MQTT keep alive interval in seconds
        """
        if mqtt is None:
            raise ImportError("paho-mqtt is required. Install with: pip install paho-mqtt")

        self.thing_name = thing_name
        self.endpoint = endpoint
        self.cert_path = cert_path
        self.key_path = key_path
        self.root_ca_path = root_ca_path
        self.port = port
        self.keep_alive = keep_alive

        # Validate certificate files
        self._validate_certificates()

        # MQTT client
        self.client = mqtt.Client(client_id=thing_name, protocol=mqtt.MQTTv311)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

        # Configure TLS
        self.client.tls_set(
            ca_certs=root_ca_path,
            certfile=cert_path,
            keyfile=key_path,
            cert_reqs=ssl.CERT_REQUIRED,
            tls_version=ssl.PROTOCOL_TLSv1_2,
            ciphers=None
        )

        # Connection state
        self.connected = False
        self.connection_lock = threading.Lock()

        # Callbacks
        self.on_connect_callback: Optional[Callable] = None
        self.on_disconnect_callback: Optional[Callable] = None
        self.message_handlers: Dict[str, Callable] = {}

        # Message queue for offline publishing
        self.message_queue = []
        self.max_queue_size = 100

        # Reconnection settings
        self.auto_reconnect = True
        self.reconnect_delay = 1  # seconds
        self.max_reconnect_delay = 60  # seconds

        logger.info(f"IoT connection initialized for thing: {thing_name}")

    def _validate_certificates(self):
        """Validate that all certificate files exist."""
        for path_name, path in [
            ('Certificate', self.cert_path),
            ('Private key', self.key_path),
            ('Root CA', self.root_ca_path)
        ]:
            if not Path(path).exists():
                raise FileNotFoundError(f"{path_name} not found: {path}")

    def connect(self) -> bool:
        """
        Connect to AWS IoT Core.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            logger.info(f"Connecting to AWS IoT endpoint: {self.endpoint}:{self.port}")
            self.client.connect(self.endpoint, self.port, self.keep_alive)
            self.client.loop_start()

            # Wait for connection (with timeout)
            timeout = 10
            start_time = time.time()
            while not self.connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)

            if self.connected:
                logger.info("Successfully connected to AWS IoT Core")
                self._flush_message_queue()
                return True
            else:
                logger.error("Connection timeout")
                return False

        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False

    def disconnect(self):
        """Disconnect from AWS IoT Core."""
        logger.info("Disconnecting from AWS IoT Core")
        self.auto_reconnect = False
        self.client.loop_stop()
        self.client.disconnect()
        self.connected = False

    def publish(
        self,
        topic: str,
        payload: Dict[str, Any],
        qos: int = 1,
        retain: bool = False
    ) -> bool:
        """
        Publish message to AWS IoT topic.

        Args:
            topic: MQTT topic
            payload: Message payload (will be JSON encoded)
            qos: Quality of Service (0, 1, or 2)
            retain: Whether to retain message

        Returns:
            True if published successfully, False otherwise
        """
        try:
            message = json.dumps(payload)

            if self.connected:
                result = self.client.publish(topic, message, qos=qos, retain=retain)

                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    logger.debug(f"Published to {topic}: {message[:100]}")
                    return True
                else:
                    logger.error(f"Publish failed: {result.rc}")
                    return False
            else:
                # Queue message for later
                if len(self.message_queue) < self.max_queue_size:
                    self.message_queue.append((topic, payload, qos, retain))
                    logger.warning(f"Not connected. Message queued ({len(self.message_queue)} in queue)")
                else:
                    logger.error("Message queue full. Dropping message.")
                return False

        except Exception as e:
            logger.error(f"Publish error: {e}")
            return False

    def subscribe(self, topic: str, handler: Callable, qos: int = 1):
        """
        Subscribe to AWS IoT topic.

        Args:
            topic: MQTT topic (can include wildcards: +, #)
            handler: Callback function(topic, payload)
            qos: Quality of Service (0, 1, or 2)
        """
        self.message_handlers[topic] = handler

        if self.connected:
            self.client.subscribe(topic, qos=qos)
            logger.info(f"Subscribed to topic: {topic}")
        else:
            logger.warning(f"Not connected. Subscription will be done on connect: {topic}")

    def unsubscribe(self, topic: str):
        """Unsubscribe from topic."""
        if topic in self.message_handlers:
            del self.message_handlers[topic]

        if self.connected:
            self.client.unsubscribe(topic)
            logger.info(f"Unsubscribed from topic: {topic}")

    def _on_connect(self, client, userdata, flags, rc):
        """MQTT on_connect callback."""
        if rc == 0:
            self.connected = True
            logger.info(f"Connected to AWS IoT Core (thing: {self.thing_name})")

            # Resubscribe to all topics
            for topic in self.message_handlers.keys():
                client.subscribe(topic, qos=1)
                logger.info(f"Resubscribed to: {topic}")

            # Call user callback
            if self.on_connect_callback:
                try:
                    self.on_connect_callback()
                except Exception as e:
                    logger.error(f"on_connect callback error: {e}")
        else:
            error_messages = {
                1: "Incorrect protocol version",
                2: "Invalid client identifier",
                3: "Server unavailable",
                4: "Bad username or password",
                5: "Not authorized"
            }
            logger.error(f"Connection failed: {error_messages.get(rc, f'Unknown error ({rc})')}")

    def _on_disconnect(self, client, userdata, rc):
        """MQTT on_disconnect callback."""
        self.connected = False

        if rc == 0:
            logger.info("Disconnected cleanly")
        else:
            logger.warning(f"Unexpected disconnection (rc={rc})")

            # Auto reconnect
            if self.auto_reconnect:
                self._reconnect()

        # Call user callback
        if self.on_disconnect_callback:
            try:
                self.on_disconnect_callback(rc)
            except Exception as e:
                logger.error(f"on_disconnect callback error: {e}")

    def _on_message(self, client, userdata, message):
        """MQTT on_message callback."""
        try:
            topic = message.topic
            payload = json.loads(message.payload.decode('utf-8'))

            logger.debug(f"Received message on {topic}: {str(payload)[:100]}")

            # Find matching handler
            for topic_pattern, handler in self.message_handlers.items():
                if self._topic_matches(topic, topic_pattern):
                    try:
                        handler(topic, payload)
                    except Exception as e:
                        logger.error(f"Message handler error: {e}")

        except Exception as e:
            logger.error(f"Message processing error: {e}")

    def _topic_matches(self, topic: str, pattern: str) -> bool:
        """Check if topic matches pattern (with wildcards)."""
        topic_parts = topic.split('/')
        pattern_parts = pattern.split('/')

        if len(pattern_parts) > len(topic_parts):
            return False

        for i, pattern_part in enumerate(pattern_parts):
            if pattern_part == '#':
                return True
            elif pattern_part == '+':
                continue
            elif i >= len(topic_parts) or pattern_part != topic_parts[i]:
                return False

        return len(topic_parts) == len(pattern_parts)

    def _reconnect(self):
        """
        Attempt to reconnect with exponential backoff.

        CRITICAL FIX: Added max_retries to prevent infinite loop.
        After max retries, gives up and disables auto_reconnect.
        """
        delay = self.reconnect_delay
        max_retries = 10  # CRITICAL: Prevent infinite loop
        retry_count = 0

        while self.auto_reconnect and not self.connected and retry_count < max_retries:
            logger.info(f"Reconnecting in {delay} seconds... (attempt {retry_count + 1}/{max_retries})")
            time.sleep(delay)

            try:
                self.connect()
                if self.connected:
                    logger.info("Reconnected successfully")
                    return
            except Exception as e:
                logger.error(f"Reconnection failed: {e}")

            # Exponential backoff
            delay = min(delay * 2, self.max_reconnect_delay)
            retry_count += 1

        if retry_count >= max_retries:
            logger.error(f"CRITICAL: Max reconnection attempts ({max_retries}) reached, giving up")
            self.auto_reconnect = False  # Stop trying to prevent resource exhaustion

    def _flush_message_queue(self):
        """Publish queued messages after reconnection."""
        if not self.message_queue:
            return

        logger.info(f"Flushing {len(self.message_queue)} queued messages")

        messages_to_send = self.message_queue[:]
        self.message_queue = []

        for topic, payload, qos, retain in messages_to_send:
            self.publish(topic, payload, qos=qos, retain=retain)

    def is_connected(self) -> bool:
        """Check if currently connected."""
        return self.connected

    def get_status(self) -> Dict[str, Any]:
        """Get connection status information."""
        return {
            'thing_name': self.thing_name,
            'endpoint': self.endpoint,
            'connected': self.connected,
            'queued_messages': len(self.message_queue),
            'subscriptions': list(self.message_handlers.keys()),
            'timestamp': datetime.utcnow().isoformat()
        }


def main():
    """Demo usage of IoT connection."""
    logging.basicConfig(level=logging.INFO)

    print("=" * 80)
    print("AWS IoT Connection Demo")
    print("=" * 80)

    # Example configuration (replace with actual values)
    config = {
        'thing_name': 'anc-device-demo',
        'endpoint': 'xxxxx.iot.us-east-1.amazonaws.com',
        'cert_path': '/path/to/cert.pem',
        'key_path': '/path/to/private.key',
        'root_ca_path': '/path/to/AmazonRootCA1.pem'
    }

    print("\nConfiguration:")
    print(f"  Thing Name: {config['thing_name']}")
    print(f"  Endpoint: {config['endpoint']}")
    print("\nNote: Update config with actual certificate paths")
    print("=" * 80)


if __name__ == "__main__":
    main()
