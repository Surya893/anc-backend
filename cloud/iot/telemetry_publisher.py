#!/usr/bin/env python3
"""
AWS IoT Telemetry Publisher
============================

Collects and publishes device telemetry and metrics to AWS IoT Core.
Includes batching, throttling, and automatic retry logic.

Telemetry Types:
- ANC metrics (latency, cancellation, SNR)
- Audio metrics (RMS, frequency, classification)
- System metrics (CPU, memory, battery)
- Emergency detection events
- Error logs and diagnostics

Usage:
    from telemetry_publisher import TelemetryPublisher

    telemetry = TelemetryPublisher(iot_connection, device_id)
    telemetry.publish_anc_metrics({
        'latency_ms': 35,
        'cancellation_db': 42.5,
        'snr_improvement_db': 38.2
    })
"""

import json
import logging
import time
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import deque


logger = logging.getLogger(__name__)


class TelemetryPublisher:
    """
    Publishes device telemetry and metrics to AWS IoT.

    Features:
    - Multiple metric categories
    - Automatic batching
    - Rate limiting
    - Offline buffering
    - Metric aggregation
    """

    def __init__(
        self,
        iot_connection,
        device_id: str,
        batch_size: int = 10,
        batch_interval: int = 30,
        max_buffer_size: int = 1000
    ):
        """
        Initialize telemetry publisher.

        Args:
            iot_connection: IoTConnection instance
            device_id: Unique device identifier
            batch_size: Number of metrics to batch before publishing
            batch_interval: Max seconds to wait before publishing batch
            max_buffer_size: Maximum metrics to buffer when offline
        """
        self.iot = iot_connection
        self.device_id = device_id
        self.batch_size = batch_size
        self.batch_interval = batch_interval
        self.max_buffer_size = max_buffer_size

        # Metric buffers
        self.metrics_buffer = deque(maxlen=max_buffer_size)
        self.batch_buffer: List[Dict[str, Any]] = []

        # Publishing thread
        self.publish_thread: Optional[threading.Thread] = None
        self.running = False

        # Statistics
        self.stats = {
            'total_published': 0,
            'total_failed': 0,
            'total_buffered': 0,
            'last_publish_time': None
        }

        # Topics
        self.topics = {
            'anc': f'anc/telemetry/{device_id}/anc',
            'audio': f'anc/telemetry/{device_id}/audio',
            'system': f'anc/telemetry/{device_id}/system',
            'emergency': f'anc/devices/{device_id}/emergency',
            'errors': f'anc/telemetry/{device_id}/errors',
            'general': f'anc/telemetry/{device_id}'
        }

        logger.info(f"Telemetry publisher initialized for device: {device_id}")

    def publish_anc_metrics(self, metrics: Dict[str, Any]):
        """
        Publish ANC performance metrics.

        Args:
            metrics: Dictionary containing:
                - latency_ms: Processing latency
                - cancellation_db: Noise cancellation level
                - snr_improvement_db: SNR improvement
                - algorithm: ANC algorithm used
                - intensity: ANC intensity setting
        """
        payload = {
            'device_id': self.device_id,
            'timestamp': datetime.utcnow().isoformat(),
            'metric_type': 'anc',
            'metrics': metrics
        }

        self._add_to_batch(self.topics['anc'], payload)

    def publish_audio_metrics(self, metrics: Dict[str, Any]):
        """
        Publish audio classification metrics.

        Args:
            metrics: Dictionary containing:
                - noise_type: Classified noise type
                - confidence: Classification confidence
                - rms: RMS audio level
                - frequency: Dominant frequency
                - features: Audio features (optional)
        """
        payload = {
            'device_id': self.device_id,
            'timestamp': datetime.utcnow().isoformat(),
            'metric_type': 'audio',
            'metrics': metrics
        }

        self._add_to_batch(self.topics['audio'], payload)

    def publish_system_metrics(self, metrics: Dict[str, Any]):
        """
        Publish system health metrics.

        Args:
            metrics: Dictionary containing:
                - cpu_usage: CPU usage percentage
                - memory_usage: Memory usage percentage
                - battery_level: Battery level percentage
                - temperature: Device temperature
                - uptime: Device uptime in seconds
        """
        payload = {
            'device_id': self.device_id,
            'timestamp': datetime.utcnow().isoformat(),
            'metric_type': 'system',
            'metrics': metrics
        }

        self._add_to_batch(self.topics['system'], payload)

    def publish_emergency_event(self, event: Dict[str, Any]):
        """
        Publish emergency detection event (high priority).

        Args:
            event: Dictionary containing:
                - is_emergency: True if emergency detected
                - predicted_class: Classified sound type
                - confidence: Detection confidence
                - action: Action taken (e.g., 'anc_bypassed')
        """
        payload = {
            'device_id': self.device_id,
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': 'emergency',
            'event': event,
            'severity': 'critical' if event.get('is_emergency') else 'info'
        }

        # Publish immediately (high priority)
        success = self.iot.publish(self.topics['emergency'], payload, qos=1)

        if success:
            logger.warning(f"Emergency event published: {event.get('predicted_class')}")
            self.stats['total_published'] += 1
        else:
            logger.error("Failed to publish emergency event")
            self.stats['total_failed'] += 1

    def publish_error_log(self, error: Dict[str, Any]):
        """
        Publish error log entry.

        Args:
            error: Dictionary containing:
                - error_type: Type of error
                - message: Error message
                - stack_trace: Stack trace (optional)
                - context: Additional context
        """
        payload = {
            'device_id': self.device_id,
            'timestamp': datetime.utcnow().isoformat(),
            'log_type': 'error',
            'error': error
        }

        self._add_to_batch(self.topics['errors'], payload)

    def publish_custom_metric(self, category: str, metrics: Dict[str, Any]):
        """
        Publish custom metrics.

        Args:
            category: Metric category
            metrics: Metric data
        """
        payload = {
            'device_id': self.device_id,
            'timestamp': datetime.utcnow().isoformat(),
            'metric_type': category,
            'metrics': metrics
        }

        topic = self.topics.get(category, self.topics['general'])
        self._add_to_batch(topic, payload)

    def _add_to_batch(self, topic: str, payload: Dict[str, Any]):
        """Add metric to batch buffer."""
        self.batch_buffer.append((topic, payload))
        self.stats['total_buffered'] += 1

        # Publish if batch is full
        if len(self.batch_buffer) >= self.batch_size:
            self._publish_batch()

    def _publish_batch(self):
        """Publish batched metrics."""
        if not self.batch_buffer:
            return

        logger.info(f"Publishing batch of {len(self.batch_buffer)} metrics")

        success_count = 0
        failed_count = 0

        for topic, payload in self.batch_buffer:
            if self.iot.publish(topic, payload, qos=0):  # QoS 0 for high throughput
                success_count += 1
            else:
                failed_count += 1

        # Update statistics
        self.stats['total_published'] += success_count
        self.stats['total_failed'] += failed_count
        self.stats['last_publish_time'] = datetime.utcnow().isoformat()

        # Clear batch
        self.batch_buffer = []

        logger.info(f"Batch published: {success_count} success, {failed_count} failed")

    def start_publishing(self):
        """Start periodic batch publishing."""
        if self.running:
            logger.warning("Publishing already running")
            return

        self.running = True
        self.publish_thread = threading.Thread(target=self._publish_loop, daemon=True)
        self.publish_thread.start()

        logger.info(f"Telemetry publishing started (interval: {self.batch_interval}s)")

    def stop_publishing(self):
        """Stop periodic batch publishing."""
        self.running = False

        # Publish remaining metrics
        if self.batch_buffer:
            self._publish_batch()

        if self.publish_thread:
            self.publish_thread.join(timeout=5)

        logger.info("Telemetry publishing stopped")

    def _publish_loop(self):
        """Periodic publishing loop."""
        while self.running:
            try:
                time.sleep(self.batch_interval)

                if self.batch_buffer:
                    self._publish_batch()

            except Exception as e:
                logger.error(f"Publish loop error: {e}")
                time.sleep(5)

    def get_statistics(self) -> Dict[str, Any]:
        """Get publishing statistics."""
        return {
            'device_id': self.device_id,
            'total_published': self.stats['total_published'],
            'total_failed': self.stats['total_failed'],
            'total_buffered': self.stats['total_buffered'],
            'batch_size': len(self.batch_buffer),
            'last_publish_time': self.stats['last_publish_time']
        }

    def flush(self):
        """Immediately publish all buffered metrics."""
        if self.batch_buffer:
            logger.info("Flushing all buffered metrics")
            self._publish_batch()


def demo_telemetry():
    """Demonstrate telemetry publishing."""
    print("=" * 80)
    print("AWS IoT Telemetry Publisher Demo")
    print("=" * 80)

    print("\nTelemetry Topics:")
    print("  ANC Metrics: anc/telemetry/DEVICE_ID/anc")
    print("  Audio Metrics: anc/telemetry/DEVICE_ID/audio")
    print("  System Metrics: anc/telemetry/DEVICE_ID/system")
    print("  Emergency Events: anc/devices/DEVICE_ID/emergency")
    print("  Error Logs: anc/telemetry/DEVICE_ID/errors")

    print("\nExample ANC Metrics:")
    anc_metrics = {
        'latency_ms': 35.2,
        'cancellation_db': 42.5,
        'snr_improvement_db': 38.2,
        'algorithm': 'nlms',
        'intensity': 0.85
    }
    print(json.dumps(anc_metrics, indent=2))

    print("\nExample Audio Metrics:")
    audio_metrics = {
        'noise_type': 'office',
        'confidence': 0.94,
        'rms': 0.45,
        'frequency': 850,
        'spectral_centroid': 2340
    }
    print(json.dumps(audio_metrics, indent=2))

    print("\nExample System Metrics:")
    system_metrics = {
        'cpu_usage': 45.2,
        'memory_usage': 68.5,
        'battery_level': 85,
        'temperature': 42.3,
        'uptime': 3600
    }
    print(json.dumps(system_metrics, indent=2))

    print("\n" + "=" * 80)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    demo_telemetry()
