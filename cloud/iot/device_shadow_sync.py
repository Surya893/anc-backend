#!/usr/bin/env python3
"""
AWS IoT Device Shadow Synchronization
======================================

Manages device shadow state synchronization between device and cloud.
Handles reported state, desired state, and delta updates.

Device Shadow Structure:
{
    "state": {
        "reported": {
            "anc_enabled": true,
            "anc_intensity": 0.8,
            "firmware_version": "1.2.3",
            "battery_level": 85,
            "noise_type": "office",
            "emergency_detected": false
        },
        "desired": {
            "anc_enabled": true,
            "anc_intensity": 0.9
        }
    }
}

Usage:
    from device_shadow_sync import DeviceShadowSync

    shadow = DeviceShadowSync(iot_connection, thing_name)
    shadow.update_reported_state({'battery_level': 75})
    shadow.start_sync()
"""

import json
import logging
import threading
import time
from typing import Dict, Any, Callable, Optional
from datetime import datetime


logger = logging.getLogger(__name__)


class DeviceShadowSync:
    """
    Synchronizes device state with AWS IoT Device Shadow.

    Features:
    - Automatic state reporting
    - Desired state change notifications
    - Delta detection and handling
    - Conflict resolution
    - Periodic sync
    """

    def __init__(
        self,
        iot_connection,
        thing_name: str,
        sync_interval: int = 60
    ):
        """
        Initialize device shadow sync.

        Args:
            iot_connection: IoTConnection instance
            thing_name: AWS IoT thing name
            sync_interval: State sync interval in seconds
        """
        self.iot = iot_connection
        self.thing_name = thing_name
        self.sync_interval = sync_interval

        # Shadow topics
        self.topic_update = f"$aws/things/{thing_name}/shadow/update"
        self.topic_update_accepted = f"$aws/things/{thing_name}/shadow/update/accepted"
        self.topic_update_rejected = f"$aws/things/{thing_name}/shadow/update/rejected"
        self.topic_update_delta = f"$aws/things/{thing_name}/shadow/update/delta"
        self.topic_get = f"$aws/things/{thing_name}/shadow/get"
        self.topic_get_accepted = f"$aws/things/{thing_name}/shadow/get/accepted"

        # Current state
        self.reported_state: Dict[str, Any] = {}
        self.desired_state: Dict[str, Any] = {}
        self.metadata: Dict[str, Any] = {}

        # Callbacks
        self.on_delta_callback: Optional[Callable] = None
        self.on_desired_change_callback: Optional[Callable] = None

        # Sync thread
        self.sync_thread: Optional[threading.Thread] = None
        self.running = False

        # Subscribe to shadow topics
        self._subscribe_to_shadow_topics()

        logger.info(f"Device shadow sync initialized for: {thing_name}")

    def _subscribe_to_shadow_topics(self):
        """Subscribe to all shadow-related topics."""
        self.iot.subscribe(self.topic_update_accepted, self._on_update_accepted)
        self.iot.subscribe(self.topic_update_rejected, self._on_update_rejected)
        self.iot.subscribe(self.topic_update_delta, self._on_delta_received)
        self.iot.subscribe(self.topic_get_accepted, self._on_get_accepted)

        logger.info("Subscribed to device shadow topics")

    def update_reported_state(self, state: Dict[str, Any], merge: bool = True) -> bool:
        """
        Update reported state in device shadow.

        Args:
            state: State dictionary to report
            merge: If True, merge with existing state; if False, replace

        Returns:
            True if update successful
        """
        try:
            if merge:
                self.reported_state.update(state)
            else:
                self.reported_state = state.copy()

            # Add timestamp
            self.reported_state['timestamp'] = datetime.utcnow().isoformat()

            payload = {
                'state': {
                    'reported': self.reported_state
                }
            }

            success = self.iot.publish(self.topic_update, payload, qos=1)

            if success:
                logger.info(f"Reported state updated: {list(state.keys())}")
            else:
                logger.error("Failed to update reported state")

            return success

        except Exception as e:
            logger.error(f"Error updating reported state: {e}")
            return False

    def request_desired_state(self) -> bool:
        """
        Request current desired state from shadow.

        Returns:
            True if request sent successfully
        """
        try:
            payload = {}
            success = self.iot.publish(self.topic_get, payload, qos=1)

            if success:
                logger.info("Requested desired state from shadow")
            else:
                logger.error("Failed to request desired state")

            return success

        except Exception as e:
            logger.error(f"Error requesting desired state: {e}")
            return False

    def clear_desired_state(self, keys: list = None) -> bool:
        """
        Clear desired state properties from shadow.

        Args:
            keys: List of keys to clear (or None for all)

        Returns:
            True if cleared successfully
        """
        try:
            if keys is None:
                # Clear all by setting to null
                desired = {k: None for k in self.desired_state.keys()}
            else:
                desired = {k: None for k in keys}

            payload = {
                'state': {
                    'desired': desired
                }
            }

            success = self.iot.publish(self.topic_update, payload, qos=1)

            if success:
                logger.info(f"Cleared desired state: {list(desired.keys())}")
            else:
                logger.error("Failed to clear desired state")

            return success

        except Exception as e:
            logger.error(f"Error clearing desired state: {e}")
            return False

    def delete_shadow(self) -> bool:
        """
        Delete the device shadow.

        Returns:
            True if deleted successfully
        """
        try:
            topic = f"$aws/things/{self.thing_name}/shadow/delete"
            success = self.iot.publish(topic, {}, qos=1)

            if success:
                logger.info("Shadow deleted")
                self.reported_state = {}
                self.desired_state = {}
            else:
                logger.error("Failed to delete shadow")

            return success

        except Exception as e:
            logger.error(f"Error deleting shadow: {e}")
            return False

    def _on_update_accepted(self, topic: str, payload: Dict[str, Any]):
        """Handle shadow update accepted."""
        logger.debug(f"Shadow update accepted: {payload.get('version', 'unknown')}")

        # Update metadata if present
        if 'metadata' in payload:
            self.metadata = payload['metadata']

    def _on_update_rejected(self, topic: str, payload: Dict[str, Any]):
        """Handle shadow update rejected."""
        code = payload.get('code', 'unknown')
        message = payload.get('message', 'No message')

        logger.error(f"Shadow update rejected: {code} - {message}")

    def _on_delta_received(self, topic: str, payload: Dict[str, Any]):
        """Handle shadow delta (difference between reported and desired)."""
        try:
            delta_state = payload.get('state', {})

            logger.info(f"Shadow delta received: {list(delta_state.keys())}")
            logger.debug(f"Delta details: {delta_state}")

            # Update desired state
            self.desired_state.update(delta_state)

            # Call delta callback
            if self.on_delta_callback:
                try:
                    self.on_delta_callback(delta_state)
                except Exception as e:
                    logger.error(f"Delta callback error: {e}")

            # After processing, report the new state
            self.update_reported_state(delta_state)

        except Exception as e:
            logger.error(f"Error processing delta: {e}")

    def _on_get_accepted(self, topic: str, payload: Dict[str, Any]):
        """Handle shadow get response."""
        try:
            state = payload.get('state', {})

            if 'reported' in state:
                self.reported_state = state['reported']
                logger.info("Reported state retrieved from shadow")

            if 'desired' in state:
                self.desired_state = state['desired']
                logger.info("Desired state retrieved from shadow")

                # Notify about desired changes
                if self.on_desired_change_callback and self.desired_state:
                    try:
                        self.on_desired_change_callback(self.desired_state)
                    except Exception as e:
                        logger.error(f"Desired change callback error: {e}")

        except Exception as e:
            logger.error(f"Error processing get response: {e}")

    def start_sync(self):
        """Start periodic shadow synchronization."""
        if self.running:
            logger.warning("Sync already running")
            return

        self.running = True
        self.sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self.sync_thread.start()

        logger.info(f"Shadow sync started (interval: {self.sync_interval}s)")

    def stop_sync(self):
        """Stop periodic shadow synchronization."""
        self.running = False

        if self.sync_thread:
            self.sync_thread.join(timeout=5)

        logger.info("Shadow sync stopped")

    def _sync_loop(self):
        """Periodic sync loop."""
        while self.running:
            try:
                # Request latest desired state
                self.request_desired_state()

                # Wait for next sync
                time.sleep(self.sync_interval)

            except Exception as e:
                logger.error(f"Sync loop error: {e}")
                time.sleep(5)  # Brief pause on error

    def get_state(self) -> Dict[str, Any]:
        """
        Get current shadow state.

        Returns:
            Dictionary with reported and desired states
        """
        return {
            'reported': self.reported_state.copy(),
            'desired': self.desired_state.copy(),
            'metadata': self.metadata.copy()
        }

    def get_reported_value(self, key: str, default=None):
        """Get value from reported state."""
        return self.reported_state.get(key, default)

    def get_desired_value(self, key: str, default=None):
        """Get value from desired state."""
        return self.desired_state.get(key, default)


def demo_shadow_sync():
    """Demonstrate shadow synchronization."""
    print("=" * 80)
    print("AWS IoT Device Shadow Sync Demo")
    print("=" * 80)

    # Example usage
    print("\nShadow Topics:")
    print("  Update: $aws/things/THING_NAME/shadow/update")
    print("  Get: $aws/things/THING_NAME/shadow/get")
    print("  Delta: $aws/things/THING_NAME/shadow/update/delta")

    print("\nExample Reported State:")
    reported = {
        'anc_enabled': True,
        'anc_intensity': 0.8,
        'firmware_version': '1.2.3',
        'battery_level': 85,
        'noise_type': 'office',
        'emergency_detected': False
    }
    print(json.dumps(reported, indent=2))

    print("\nExample Desired State:")
    desired = {
        'anc_enabled': True,
        'anc_intensity': 0.9
    }
    print(json.dumps(desired, indent=2))

    print("\n" + "=" * 80)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    demo_shadow_sync()
