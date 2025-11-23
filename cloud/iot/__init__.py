"""
AWS IoT Integration for ANC Platform
=====================================

This package provides complete AWS IoT Core integration for ANC devices,
including connection management, device shadow synchronization, and
telemetry publishing.

Main Components:
- IoTConnection: MQTT connection to AWS IoT Core
- DeviceShadowSync: Device shadow state synchronization
- TelemetryPublisher: Metrics and telemetry publishing
- DataSyncOrchestrator: Main orchestrator coordinating all components

Quick Start:
    from cloud.iot import DataSyncOrchestrator

    orchestrator = DataSyncOrchestrator(
        thing_name='anc-device-001',
        endpoint='your-endpoint.iot.us-east-1.amazonaws.com',
        cert_path='/path/to/cert.pem',
        key_path='/path/to/private.key',
        root_ca_path='/path/to/AmazonRootCA1.pem'
    )

    orchestrator.start()
    orchestrator.update_anc_state(enabled=True, intensity=0.85)
    orchestrator.publish_metrics({'latency_ms': 35})
"""

__version__ = '1.0.0'
__author__ = 'ANC Platform Team'

from .iot_connection import IoTConnection
from .device_shadow_sync import DeviceShadowSync
from .telemetry_publisher import TelemetryPublisher
from .data_sync_orchestrator import DataSyncOrchestrator

__all__ = [
    'IoTConnection',
    'DeviceShadowSync',
    'TelemetryPublisher',
    'DataSyncOrchestrator'
]
