// ANC System Web App - Frontend JavaScript

// State management
let appState = {
    ancEnabled: false,
    noiseIntensity: 0.5,
    currentNoiseClass: 'unknown',
    emergencyDetected: false,
    detectionConfidence: 0,
    prolongedDetection: {
        enabled: true,
        threshold_seconds: 5,
        current_duration: 0,
        detected_class: null
    }
};

// Update interval
const UPDATE_INTERVAL = 1000; // 1 second
let updateTimer = null;

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    console.log('ANC System Web App initialized');

    // Start status updates
    startStatusUpdates();

    // Check for notifications
    checkNotifications();
    setInterval(checkNotifications, 2000);
});

// Toggle ANC
async function toggleANC() {
    try {
        const response = await fetch('/api/toggle_anc', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'}
        });

        const data = await response.json();

        if (data.success) {
            appState.ancEnabled = data.anc_enabled;
            updateANCUI();
            showToast(data.message, 'success');
        }
    } catch (error) {
        console.error('Toggle ANC error:', error);
        showToast('Failed to toggle ANC', 'error');
    }
}

// Update ANC UI
function updateANCUI() {
    const btn = document.getElementById('anc-toggle-btn');
    const statusText = document.getElementById('anc-status-text');
    const stateText = document.getElementById('anc-state-text');
    const indicator = document.querySelector('.indicator-light');

    if (appState.ancEnabled) {
        btn.classList.add('active');
        statusText.textContent = 'Disable ANC';
        stateText.textContent = 'ANC Active';
        indicator.classList.add('active');
    } else {
        btn.classList.remove('active');
        statusText.textContent = 'Enable ANC';
        stateText.textContent = 'ANC Disabled';
        indicator.classList.remove('active');
    }
}

// Update intensity
async function updateIntensity(value) {
    const intensity = parseInt(value) / 100;

    // Update UI immediately
    document.getElementById('intensity-value').textContent = value + '%';

    try {
        const response = await fetch('/api/set_intensity', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({intensity: intensity})
        });

        const data = await response.json();

        if (data.success) {
            appState.noiseIntensity = data.intensity;
        }
    } catch (error) {
        console.error('Update intensity error:', error);
    }
}

// Toggle prolonged detection
async function toggleProlonged() {
    const enabled = document.getElementById('prolonged-toggle').checked;

    try {
        const response = await fetch('/api/prolonged_detection', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({enabled: enabled})
        });

        const data = await response.json();

        if (data.success) {
            appState.prolongedDetection = data.prolonged_detection;
            showToast(data.message, 'success');
        }
    } catch (error) {
        console.error('Toggle prolonged error:', error);
    }
}

// Update threshold
async function updateThreshold(value) {
    document.getElementById('threshold-value').textContent = value + 's';

    try {
        const response = await fetch('/api/prolonged_detection', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({threshold_seconds: parseInt(value)})
        });

        const data = await response.json();

        if (data.success) {
            appState.prolongedDetection = data.prolonged_detection;
        }
    } catch (error) {
        console.error('Update threshold error:', error);
    }
}

// Start status updates
function startStatusUpdates() {
    updateStatus();
    updateTimer = setInterval(updateStatus, UPDATE_INTERVAL);
}

// Update status from server
async function updateStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();

        // Update state
        appState.ancEnabled = data.anc_enabled;
        appState.noiseIntensity = data.noise_intensity;
        appState.currentNoiseClass = data.current_noise_class;
        appState.emergencyDetected = data.emergency_detected;
        appState.detectionConfidence = data.detection_confidence;
        appState.prolongedDetection = data.prolonged_detection;

        // Update UI
        updateANCUI();
        updateDetectionUI();
        updateProlongedUI();
        updateStatsUI(data.stats);

        // Handle emergency
        if (data.emergency_detected) {
            showEmergencyAlert(data.current_noise_class, data.detection_confidence);
        }

    } catch (error) {
        console.error('Status update error:', error);
    }
}

// Update detection UI
function updateDetectionUI() {
    const classEl = document.getElementById('noise-class');
    const confidenceText = document.getElementById('confidence-text');
    const confidenceBadge = document.getElementById('confidence-badge');

    classEl.textContent = capitalize(appState.currentNoiseClass);
    const confidence = Math.round(appState.detectionConfidence * 100);
    confidenceText.textContent = `Confidence: ${confidence}%`;
    confidenceBadge.textContent = confidence + '%';

    // Update badge color
    if (confidence >= 80) {
        confidenceBadge.style.background = 'var(--success-color)';
    } else if (confidence >= 60) {
        confidenceBadge.style.background = 'var(--warning-color)';
    } else {
        confidenceBadge.style.background = 'var(--text-secondary)';
    }
}

// Update prolonged detection UI
function updateProlongedUI() {
    const pd = appState.prolongedDetection;

    document.getElementById('prolonged-duration').textContent = pd.current_duration + 's';
    document.getElementById('prolonged-class').textContent = pd.detected_class || 'None';
}

// Update statistics UI
function updateStatsUI(stats) {
    document.getElementById('stat-detections').textContent = stats.total_detections;
    document.getElementById('stat-emergency').textContent = stats.emergency_count;

    // Format uptime
    const uptimeMinutes = Math.floor(stats.anc_active_time / 60);
    const uptimeHours = Math.floor(uptimeMinutes / 60);
    const remainingMinutes = uptimeMinutes % 60;
    document.getElementById('stat-uptime').textContent = `${uptimeHours}h ${remainingMinutes}m`;
}

// Show emergency alert
function showEmergencyAlert(noiseClass, confidence) {
    const card = document.getElementById('emergency-card');
    const message = document.getElementById('emergency-message');

    message.textContent = `${capitalize(noiseClass)} detected! (${Math.round(confidence*100)}% confidence) - ANC bypassed for safety`;
    card.style.display = 'block';
}

// Dismiss emergency
function dismissEmergency() {
    document.getElementById('emergency-card').style.display = 'none';
}

// Acknowledge emergency
function acknowledgeEmergency() {
    showToast('Emergency acknowledged', 'warning');
    dismissEmergency();
}

// Check for notifications
async function checkNotifications() {
    try {
        const response = await fetch('/api/notifications');
        const data = await response.json();

        if (data.notifications && data.notifications.length > 0) {
            displayNotifications(data.notifications);
        }
    } catch (error) {
        console.error('Notification check error:', error);
    }
}

// Display notifications
function displayNotifications(notifications) {
    const container = document.getElementById('notifications');

    // Clear empty message
    const empty = container.querySelector('.notification-empty');
    if (empty) {
        empty.remove();
    }

    notifications.forEach(notification => {
        const notifEl = createNotificationElement(notification);
        container.insertBefore(notifEl, container.firstChild);

        // Show toast for high severity
        if (notification.severity === 'high') {
            showToast(notification.title + ': ' + notification.message, 'error');
        }
    });

    // Limit to 10 notifications
    while (container.children.length > 10) {
        container.removeChild(container.lastChild);
    }
}

// Create notification element
function createNotificationElement(notification) {
    const div = document.createElement('div');
    div.className = `notification-item ${notification.type}`;

    const time = new Date(notification.timestamp).toLocaleTimeString();

    div.innerHTML = `
        <div class="notification-header">
            <div class="notification-title">${notification.title}</div>
            <div class="notification-time">${time}</div>
        </div>
        <div class="notification-message">${notification.message}</div>
    `;

    return div;
}

// Clear notifications
async function clearNotifications() {
    try {
        const response = await fetch('/api/clear_notifications', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'}
        });

        const data = await response.json();

        if (data.success) {
            const container = document.getElementById('notifications');
            container.innerHTML = '<div class="notification-empty">No notifications</div>';
            showToast('Notifications cleared', 'success');
        }
    } catch (error) {
        console.error('Clear notifications error:', error);
    }
}

// Reset statistics
async function resetStats() {
    if (!confirm('Reset all statistics?')) {
        return;
    }

    try {
        const response = await fetch('/api/reset_stats', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'}
        });

        const data = await response.json();

        if (data.success) {
            showToast(data.message, 'success');
        }
    } catch (error) {
        console.error('Reset stats error:', error);
    }
}

// Simulate noise (for testing)
async function simulateNoise(noiseType, isEmergency) {
    try {
        const response = await fetch('/api/simulate_noise', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                noise_type: noiseType,
                emergency: isEmergency,
                confidence: 0.85 + Math.random() * 0.15
            })
        });

        const data = await response.json();

        if (data.success) {
            showToast(`Simulated ${noiseType} ${isEmergency ? '(Emergency)' : ''}`, 'info');
        }
    } catch (error) {
        console.error('Simulate noise error:', error);
    }
}

// Show toast notification
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;

    container.appendChild(toast);

    // Auto-remove after 3 seconds
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => {
            container.removeChild(toast);
        }, 300);
    }, 3000);
}

// Utility: Capitalize first letter
function capitalize(str) {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1);
}

// Add slideOut animation
const style = document.createElement('style');
style.textContent = `
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);
