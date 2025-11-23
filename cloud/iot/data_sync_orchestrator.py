#!/usr/bin/env python3
"""
AWS IoT Data Sync Orchestrator
===============================

Main orchestrator that coordinates all AWS IoT data synchronization
components including connection management, shadow sync, and telemetry.

This is the primary entry point for device-to-cloud integration.

Usage:
    from data_sync_orchestrator import DataSyncOrchestrator

    # Initialize
    orchestrator = DataSyncOrchestrator(
        thing_name='anc-device-001',
        endpoint='xxxxx.iot.us-east-1.amazonaws.com',
        cert_path='/path/to/cert.pem',
        key_path='/path/to/private.key',
        root_ca_path='/path/to/AmazonRootCA1.pem'
    )

    # Start sync
    orchestrator.start()

    # Update device state
    orchestrator.update_anc_state(enabled=True, intensity=0.85)

    # Publish metrics
    orchestrator.publish_metrics({
        'latency_ms': 35,
        'cancellation_db': 42.5
    })
"""

import json
import logging
import time
import signal
import sys
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

# Import IoT components
try:
    from iot_connection import IoTConnection
    from device_shadow_sync import DeviceShadowSync
    from telemetry_publisher import TelemetryPublisher
except ImportError:
    # Try relative imports
    from .iot_connection import IoTConnection
    from .device_shadow_sync import DeviceShadowSync
    from .telemetry_publisher import TelemetryPublisher


logger = logging.getLogger(__name__)


class DataSyncOrchestrator:
    """
    Coordinates all AWS IoT data synchronization components.

    Features:
    - Automatic connection management with reconnection
    - Device shadow synchronization
    - Telemetry publishing and batching
    - Desired state change handling
    - Graceful shutdown
    """

    def __init__(
        self,
        thing_name: str,
        endpoint: str,
        cert_path: str,
        key_path: str,
        root_ca_path: str,
        device_id: Optional[str] = None
    ):
        """
        Initialize data sync orchestrator.

        Args:
            thing_name: AWS IoT thing name
            endpoint: AWS IoT endpoint
            cert_path: Device certificate path
            key_path: Private key path
            root_ca_path: Root CA certificate path
            device_id: Device identifier (defaults to thing_name)
        """
        self.thing_name = thing_name
        self.device_id = device_id or thing_name

        # Initialize IoT connection
        self.iot = IoTConnection(
            thing_name=thing_name,
            endpoint=endpoint,
            cert_path=cert_path,
            key_path=key_path,
            root_ca_path=root_ca_path
        )

        # Set connection callbacks
        self.iot.on_connect_callback = self._on_connected
        self.iot.on_disconnect_callback = self._on_disconnected

        # Initialize device shadow sync
        self.shadow = DeviceShadowSync(
            iot_connection=self.iot,
            thing_name=thing_name
        )

        # Set shadow callbacks
        self.shadow.on_delta_callback = self._on_shadow_delta
        self.shadow.on_desired_change_callback = self._on_desired_change

        # Initialize telemetry publisher
        self.telemetry = TelemetryPublisher(
            iot_connection=self.iot,
            device_id=self.device_id
        )

        # Orchestrator state
        self.running = False
        self.start_time: Optional[datetime] = None

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info(f"Data sync orchestrator initialized for: {thing_name}")

    def start(self) -> bool:
        """
        Start data synchronization.

        Returns:
            True if started successfully
        """
        if self.running:
            logger.warning("Already running")
            return True

        logger.info("Starting data sync orchestrator...")

        # Connect to AWS IoT
        if not self.iot.connect():
            logger.error("Failed to connect to AWS IoT")
            return False

        # Start shadow sync
        self.shadow.start_sync()

        # Start telemetry publishing
        self.telemetry.start_publishing()

        # Mark as running
        self.running = True
        self.start_time = datetime.utcnow()

        # Report initial state
        self._report_initial_state()

        logger.info("✓ Data sync orchestrator started successfully")
        return True

    def stop(self):
        """Stop data synchronization gracefully."""
        if not self.running:
            return

        logger.info("Stopping data sync orchestrator...")

        # Mark as not running
        self.running = False

        # Stop telemetry publishing
        self.telemetry.stop_publishing()

        # Stop shadow sync
        self.shadow.stop_sync()

        # Report offline state
        self.shadow.update_reported_state({
            'status': 'offline',
            'last_seen': datetime.utcnow().isoformat()
        })

        # Wait for final messages to be sent
        time.sleep(2)

        # Disconnect from AWS IoT
        self.iot.disconnect()

        logger.info("✓ Data sync orchestrator stopped")

    def update_anc_state(
        self,
        enabled: Optional[bool] = None,
        intensity: Optional[float] = None,
        algorithm: Optional[str] = None
    ):
        """
        Update ANC state in device shadow.

        Args:
            enabled: ANC enabled status
            intensity: ANC intensity (0.0-1.0)
            algorithm: ANC algorithm name
        """
        state = {}

        if enabled is not None:
            state['anc_enabled'] = enabled

        if intensity is not None:
            state['anc_intensity'] = intensity

        if algorithm is not None:
            state['anc_algorithm'] = algorithm

        if state:
            self.shadow.update_reported_state(state)
            logger.info(f"ANC state updated: {state}")

    def update_audio_state(
        self,
        noise_type: Optional[str] = None,
        confidence: Optional[float] = None,
        emergency_detected: Optional[bool] = None
    ):
        """
        Update audio classification state.

        Args:
            noise_type: Detected noise type
            confidence: Classification confidence
            emergency_detected: Whether emergency sound detected
        """
        state = {}

        if noise_type is not None:
            state['noise_type'] = noise_type

        if confidence is not None:
            state['confidence'] = confidence

        if emergency_detected is not None:
            state['emergency_detected'] = emergency_detected

        if state:
            self.shadow.update_reported_state(state)

    def update_system_state(
        self,
        battery_level: Optional[int] = None,
        firmware_version: Optional[str] = None,
        uptime: Optional[int] = None
    ):
        """
        Update system state.

        Args:
            battery_level: Battery level (0-100)
            firmware_version: Firmware version string
            uptime: System uptime in seconds
        """
        state = {}

        if battery_level is not None:
            state['battery_level'] = battery_level

        if firmware_version is not None:
            state['firmware_version'] = firmware_version

        if uptime is not None:
            state['uptime'] = uptime

        if state:
            self.shadow.update_reported_state(state)

    def publish_metrics(
        self,
        anc_metrics: Optional[Dict[str, Any]] = None,
        audio_metrics: Optional[Dict[str, Any]] = None,
        system_metrics: Optional[Dict[str, Any]] = None
    ):
        """
        Publish telemetry metrics.

        Args:
            anc_metrics: ANC performance metrics
            audio_metrics: Audio classification metrics
            system_metrics: System health metrics
        """
        if anc_metrics:
            self.telemetry.publish_anc_metrics(anc_metrics)

        if audio_metrics:
            self.telemetry.publish_audio_metrics(audio_metrics)

        if system_metrics:
            self.telemetry.publish_system_metrics(system_metrics)

    def report_emergency(self, event: Dict[str, Any]):
        """
        Report emergency detection event (high priority).

        Args:
            event: Emergency event details
        """
        # Publish to telemetry
        self.telemetry.publish_emergency_event(event)

        # Update shadow
        self.shadow.update_reported_state({
            'emergency_detected': event.get('is_emergency', False),
            'last_emergency': datetime.utcnow().isoformat()
        })

        logger.warning(f"Emergency reported: {event}")

    def report_error(self, error: Dict[str, Any]):
        """
        Report error log.

        Args:
            error: Error details
        """
        self.telemetry.publish_error_log(error)
        logger.error(f"Error reported: {error.get('message', 'Unknown error')}")

    def _on_connected(self):
        """Callback when connected to AWS IoT."""
        logger.info("📡 Connected to AWS IoT Core")

        # Update shadow with online status
        self.shadow.update_reported_state({
            'status': 'online',
            'connected_at': datetime.utcnow().isoformat()
        })

    def _on_disconnected(self, rc: int):
        """Callback when disconnected from AWS IoT."""
        logger.warning(f"Disconnected from AWS IoT (rc={rc})")

    def _on_shadow_delta(self, delta: Dict[str, Any]):
        """
        Handle shadow delta (desired state changes).

        Args:
            delta: Dictionary of changed properties
        """
        logger.info(f"Shadow delta received: {list(delta.keys())}")

        # Handle ANC settings changes
        if 'anc_enabled' in delta:
            logger.info(f"ANC enabled changed to: {delta['anc_enabled']}")
            # TODO: Apply ANC setting to device

        if 'anc_intensity' in delta:
            logger.info(f"ANC intensity changed to: {delta['anc_intensity']}")
            # TODO: Apply intensity setting to device

        # Auto-report new state after applying changes
        # (DeviceShadowSync already does this)

    def _on_desired_change(self, desired: Dict[str, Any]):
        """
        Handle desired state retrieval.

        Args:
            desired: Complete desired state
        """
        logger.info(f"Desired state retrieved: {list(desired.keys())}")

    def _report_initial_state(self):
        """Report initial device state to shadow."""
        initial_state = {
            'status': 'online',
            'device_id': self.device_id,
            'thing_name': self.thing_name,
            'connected_at': datetime.utcnow().isoformat(),
            'firmware_version': '1.0.0',  # TODO: Get from device
            'sdk_version': '1.0.0'
        }

        self.shadow.update_reported_state(initial_state)
        logger.info("Initial state reported to shadow")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)

    def get_status(self) -> Dict[str, Any]:
        """
        Get orchestrator status.

        Returns:
            Status dictionary
        """
        uptime = None
        if self.start_time:
            uptime = (datetime.utcnow() - self.start_time).total_seconds()

        return {
            'running': self.running,
            'thing_name': self.thing_name,
            'device_id': self.device_id,
            'connected': self.iot.is_connected(),
            'uptime_seconds': uptime,
            'shadow_state': self.shadow.get_state(),
            'telemetry_stats': self.telemetry.get_statistics()
        }

    def run_forever(self):
        """
        Run orchestrator indefinitely (blocking).

        Useful for standalone device daemons.
        """
        logger.info("Running orchestrator in forever mode...")

        try:
            while self.running:
                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")

        finally:
            self.stop()


def main():
    """Demo usage of data sync orchestrator."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("=" * 80)
    print("AWS IoT Data Sync Orchestrator Demo")
    print("=" * 80)

    # Example configuration
    config = {
        'thing_name': 'anc-device-demo',
        'endpoint': 'xxxxx.iot.us-east-1.amazonaws.com',
        'cert_path': '/path/to/cert.pem',
        'key_path': '/path/to/private.key',
        'root_ca_path': '/path/to/AmazonRootCA1.pem'
    }

    print("\nConfiguration:")
    for key, value in config.items():
        print(f"  {key}: {value}")

    print("\nNote: Update config with actual certificate paths and endpoint")
    print("\nUsage:")
    print("  1. Initialize orchestrator with valid credentials")
    print("  2. Call orchestrator.start() to begin sync")
    print("  3. Update state: orchestrator.update_anc_state(enabled=True)")
    print("  4. Publish metrics: orchestrator.publish_metrics(...)")
    print("  5. Call orchestrator.stop() for graceful shutdown")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
