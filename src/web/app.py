"""
Flask Web Application for ANC System
Mobile-responsive UI with noise controls and emergency notifications.
"""

from flask import Flask, render_template, jsonify, request, send_from_directory
import numpy as np
import json
import time
from datetime import datetime
from pathlib import Path
import threading
import queue

# Import ANC system components
try:
    from emergency_noise_detector import EmergencyNoiseDetector
    from anti_noise_generator import AntiNoiseGenerator
    from database_schema import ANCDatabase
except ImportError:
    print("Warning: Some ANC modules not available")

app = Flask(__name__)

# Global state
class ANCSystemState:
    def __init__(self):
        self.anc_enabled = False
        self.noise_intensity = 0.0
        self.current_noise_class = "unknown"
        self.emergency_detected = False
        self.emergency_history = []
        self.detection_confidence = 0.0
        self.prolonged_detection = {
            'enabled': True,
            'threshold_seconds': 5,
            'current_duration': 0,
            'detected_class': None
        }
        self.notifications = queue.Queue()
        self.stats = {
            'total_detections': 0,
            'emergency_count': 0,
            'anc_active_time': 0,
            'last_update': datetime.now().isoformat()
        }

state = ANCSystemState()

# Lock for thread safety
state_lock = threading.Lock()


@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('index.html')


@app.route('/api/status')
def api_status():
    """Get current system status."""
    with state_lock:
        return jsonify({
            'anc_enabled': state.anc_enabled,
            'noise_intensity': state.noise_intensity,
            'current_noise_class': state.current_noise_class,
            'emergency_detected': state.emergency_detected,
            'detection_confidence': state.detection_confidence,
            'prolonged_detection': state.prolonged_detection,
            'stats': state.stats,
            'timestamp': datetime.now().isoformat()
        })


@app.route('/api/toggle_anc', methods=['POST'])
def api_toggle_anc():
    """Toggle ANC on/off."""
    with state_lock:
        state.anc_enabled = not state.anc_enabled

        return jsonify({
            'success': True,
            'anc_enabled': state.anc_enabled,
            'message': f"ANC {'enabled' if state.anc_enabled else 'disabled'}"
        })


@app.route('/api/set_intensity', methods=['POST'])
def api_set_intensity():
    """Set noise intensity level."""
    data = request.json
    intensity = float(data.get('intensity', 0.5))

    # Clamp to valid range
    intensity = max(0.0, min(1.0, intensity))

    with state_lock:
        state.noise_intensity = intensity

        return jsonify({
            'success': True,
            'intensity': intensity,
            'message': f"Intensity set to {intensity*100:.0f}%"
        })


@app.route('/api/prolonged_detection', methods=['POST'])
def api_prolonged_detection():
    """Configure prolonged/intermittent detection."""
    data = request.json

    with state_lock:
        if 'enabled' in data:
            state.prolonged_detection['enabled'] = bool(data['enabled'])

        if 'threshold_seconds' in data:
            threshold = int(data['threshold_seconds'])
            state.prolonged_detection['threshold_seconds'] = max(1, min(60, threshold))

        return jsonify({
            'success': True,
            'prolonged_detection': state.prolonged_detection,
            'message': 'Prolonged detection settings updated'
        })


@app.route('/api/emergency_history')
def api_emergency_history():
    """Get emergency detection history."""
    with state_lock:
        return jsonify({
            'history': state.emergency_history[-20:],  # Last 20
            'count': len(state.emergency_history)
        })


@app.route('/api/notifications')
def api_notifications():
    """Get pending notifications."""
    notifications = []

    try:
        while not state.notifications.empty():
            notifications.append(state.notifications.get_nowait())
    except queue.Empty:
        pass

    return jsonify({
        'notifications': notifications,
        'count': len(notifications)
    })


@app.route('/api/clear_notifications', methods=['POST'])
def api_clear_notifications():
    """Clear all notifications."""
    while not state.notifications.empty():
        try:
            state.notifications.get_nowait()
        except queue.Empty:
            break

    return jsonify({
        'success': True,
        'message': 'Notifications cleared'
    })


@app.route('/api/simulate_noise', methods=['POST'])
def api_simulate_noise():
    """Simulate noise detection (for testing)."""
    data = request.json
    noise_type = data.get('noise_type', 'office')
    is_emergency = data.get('emergency', False)
    confidence = data.get('confidence', 0.85)

    with state_lock:
        state.current_noise_class = noise_type
        state.detection_confidence = confidence
        state.emergency_detected = is_emergency
        state.stats['total_detections'] += 1

        if is_emergency:
            state.stats['emergency_count'] += 1

            # Add to history
            event = {
                'timestamp': datetime.now().isoformat(),
                'noise_class': noise_type,
                'confidence': confidence,
                'action': 'ANC bypassed for safety'
            }
            state.emergency_history.append(event)

            # Send notification
            notification = {
                'type': 'emergency',
                'title': 'Emergency Sound Detected!',
                'message': f'{noise_type} detected ({confidence*100:.0f}% confidence)',
                'timestamp': datetime.now().isoformat(),
                'severity': 'high'
            }
            state.notifications.put(notification)

        # Update prolonged detection
        if state.prolonged_detection['enabled']:
            if state.prolonged_detection['detected_class'] == noise_type:
                state.prolonged_detection['current_duration'] += 1
            else:
                state.prolonged_detection['detected_class'] = noise_type
                state.prolonged_detection['current_duration'] = 1

            # Check threshold
            if state.prolonged_detection['current_duration'] >= state.prolonged_detection['threshold_seconds']:
                notification = {
                    'type': 'prolonged',
                    'title': 'Prolonged Noise Detected',
                    'message': f'{noise_type} detected for {state.prolonged_detection["current_duration"]} seconds',
                    'timestamp': datetime.now().isoformat(),
                    'severity': 'medium'
                }
                state.notifications.put(notification)

        state.stats['last_update'] = datetime.now().isoformat()

        return jsonify({
            'success': True,
            'current_state': {
                'noise_class': noise_type,
                'emergency': is_emergency,
                'confidence': confidence
            }
        })


@app.route('/api/reset_stats', methods=['POST'])
def api_reset_stats():
    """Reset statistics."""
    with state_lock:
        state.stats = {
            'total_detections': 0,
            'emergency_count': 0,
            'anc_active_time': 0,
            'last_update': datetime.now().isoformat()
        }
        state.emergency_history = []

        return jsonify({
            'success': True,
            'message': 'Statistics reset'
        })


@app.route('/api/test_notification', methods=['POST'])
def api_test_notification():
    """Send test notification."""
    data = request.json

    notification = {
        'type': data.get('type', 'info'),
        'title': data.get('title', 'Test Notification'),
        'message': data.get('message', 'This is a test notification'),
        'timestamp': datetime.now().isoformat(),
        'severity': data.get('severity', 'low')
    }

    state.notifications.put(notification)

    return jsonify({
        'success': True,
        'notification': notification
    })


@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })


if __name__ == '__main__':
    print("="*80)
    print("ANC SYSTEM WEB APPLICATION")
    print("="*80)
    print("\nStarting Flask server...")
    print("Access the app at: http://localhost:5000")
    print("Mobile access: http://<your-ip>:5000")
    print("\nPress Ctrl+C to stop")
    print("="*80)

    # Run Flask app
    app.run(
        host='0.0.0.0',  # Allow external connections
        port=5000,
        debug=True,
        threaded=True
    )
