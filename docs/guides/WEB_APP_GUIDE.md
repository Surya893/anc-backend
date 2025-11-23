## Flask Web App for ANC System - Complete Guide

**Mobile-responsive UI for Active Noise Cancellation control**

---

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements_web.txt
```

Or manually:
```bash
pip install Flask==3.0.0 Werkzeug==3.0.0 numpy==1.24.3
```

### 2. Run the App

```bash
python app.py
```

### 3. Access the Interface

**On local machine:**
```
http://localhost:5000
```

**On mobile device (same network):**
```
http://<your-computer-ip>:5000
```

To find your IP:
- **Linux/Mac:** `ifconfig` or `ip addr`
- **Windows:** `ipconfig`

---

## Features

### ✅ ANC Control
- **Toggle ANC on/off** with large button
- **Visual indicator** showing ANC status
- **Real-time updates** every second

### 📊 Noise Intensity Control
- **Slider control** (0-100%)
- **Smooth adjustment** for noise cancellation strength
- **Live feedback** showing current level

### 🔍 Current Detection
- **Real-time noise classification**
- **Confidence percentage** display
- **Visual indicators** for detection quality
- **Automatic updates** as noise changes

### ⏱️ Prolonged/Intermittent Detection
- **Enable/disable** prolonged detection
- **Configurable threshold** (1-60 seconds)
- **Duration tracking** for persistent noise
- **Automatic alerts** when threshold exceeded

### 🚨 Emergency Notifications
- **Instant alerts** for emergency sounds (alarms, sirens)
- **High-priority display** with visual emphasis
- **Acknowledge button** to dismiss
- **Safety bypass** confirmation

### 📱 Notifications System
- **Real-time notifications** queue
- **Categorized by severity**:
  - High: Emergency sounds
  - Medium: Prolonged detection
  - Low: General updates
- **Toast popups** for important events
- **History view** with timestamps

### 📈 Statistics Dashboard
- **Total detections** count
- **Emergency count** tracking
- **Active time** monitoring
- **Reset function** for fresh start

### 🧪 Test Controls
- **Simulate various noises** (office, traffic)
- **Test emergency sounds** (alarm, siren)
- **Debug interface** for development
- **Instant feedback** on simulations

---

## User Interface

### Mobile-Optimized Design

**Features:**
- Responsive layout (works on all screen sizes)
- Touch-friendly controls (large buttons)
- Smooth animations and transitions
- No horizontal scrolling
- Optimized for portrait and landscape

### Color Coding

| Color | Meaning |
|-------|---------|
| 🔵 Blue | Primary actions, normal state |
| 🟢 Green | ANC active, success |
| 🔴 Red | Emergency alerts, danger |
| 🟡 Yellow | Warnings, prolonged detection |
| ⚪ Gray | Disabled, inactive |

### Cards Layout

1. **ANC Control** - Main on/off toggle
2. **Noise Intensity** - Adjustable slider
3. **Current Detection** - Live classification
4. **Prolonged Detection** - Duration monitoring
5. **Emergency Alert** - Pop-up when needed
6. **Notifications** - Event history
7. **Statistics** - Usage metrics
8. **Test Controls** - Development tools

---

## API Endpoints

### GET /api/status
Get current system status.

**Response:**
```json
{
    "anc_enabled": true,
    "noise_intensity": 0.75,
    "current_noise_class": "office",
    "emergency_detected": false,
    "detection_confidence": 0.92,
    "prolonged_detection": {
        "enabled": true,
        "threshold_seconds": 5,
        "current_duration": 3,
        "detected_class": "office"
    },
    "stats": {
        "total_detections": 145,
        "emergency_count": 2,
        "anc_active_time": 3600
    }
}
```

### POST /api/toggle_anc
Toggle ANC on/off.

**Response:**
```json
{
    "success": true,
    "anc_enabled": true,
    "message": "ANC enabled"
}
```

### POST /api/set_intensity
Set noise intensity level (0.0-1.0).

**Request:**
```json
{
    "intensity": 0.75
}
```

**Response:**
```json
{
    "success": true,
    "intensity": 0.75,
    "message": "Intensity set to 75%"
}
```

### POST /api/prolonged_detection
Configure prolonged detection settings.

**Request:**
```json
{
    "enabled": true,
    "threshold_seconds": 10
}
```

**Response:**
```json
{
    "success": true,
    "prolonged_detection": {
        "enabled": true,
        "threshold_seconds": 10,
        "current_duration": 0,
        "detected_class": null
    },
    "message": "Prolonged detection settings updated"
}
```

### GET /api/emergency_history
Get emergency detection history.

**Response:**
```json
{
    "history": [
        {
            "timestamp": "2025-11-08T10:30:45",
            "noise_class": "alarm",
            "confidence": 0.95,
            "action": "ANC bypassed for safety"
        }
    ],
    "count": 1
}
```

### GET /api/notifications
Get pending notifications.

**Response:**
```json
{
    "notifications": [
        {
            "type": "emergency",
            "title": "Emergency Sound Detected!",
            "message": "alarm detected (95% confidence)",
            "timestamp": "2025-11-08T10:30:45",
            "severity": "high"
        }
    ],
    "count": 1
}
```

### POST /api/simulate_noise
Simulate noise detection (for testing).

**Request:**
```json
{
    "noise_type": "alarm",
    "emergency": true,
    "confidence": 0.95
}
```

**Response:**
```json
{
    "success": true,
    "current_state": {
        "noise_class": "alarm",
        "emergency": true,
        "confidence": 0.95
    }
}
```

---

## Configuration

### Server Settings

Edit `app.py` to configure:

```python
app.run(
    host='0.0.0.0',  # Allow external connections
    port=5000,       # Port number
    debug=True,      # Enable debug mode
    threaded=True    # Handle multiple requests
)
```

### Production Deployment

For production, use a WSGI server:

```bash
# Install gunicorn
pip install gunicorn

# Run with gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

Or with uWSGI:

```bash
# Install uwsgi
pip install uwsgi

# Run with uwsgi
uwsgi --http 0.0.0.0:5000 --wsgi-file app.py --callable app
```

### Firewall Configuration

Allow port 5000:

**Linux (UFW):**
```bash
sudo ufw allow 5000/tcp
```

**Linux (firewalld):**
```bash
sudo firewall-cmd --add-port=5000/tcp --permanent
sudo firewall-cmd --reload
```

---

## Usage Examples

### Example 1: Basic ANC Control

1. Open web app in browser
2. Tap "Enable ANC" button
3. Adjust intensity slider to desired level
4. Monitor current detection in real-time

### Example 2: Emergency Detection

1. Enable ANC
2. Tap "Simulate Alarm" button
3. Observe:
   - Emergency alert appears (red banner)
   - ANC status shows "bypassed"
   - Notification added to history
   - Toast notification appears

### Example 3: Prolonged Detection

1. Enable prolonged detection toggle
2. Set threshold to 10 seconds
3. Simulate office noise repeatedly
4. After 10 seconds:
   - Prolonged alert triggers
   - Notification appears
   - Duration counter updates

### Example 4: Mobile Access

1. Find computer's IP address
2. Open mobile browser
3. Navigate to `http://<ip>:5000`
4. Use touch controls:
   - Tap to toggle ANC
   - Swipe sliders for adjustments
   - Scroll through notifications

---

## Troubleshooting

### App Won't Start

**Error: `Address already in use`**

Solution:
```bash
# Find process using port 5000
lsof -i :5000

# Kill the process
kill -9 <PID>

# Or use different port
python app.py --port 5001
```

**Error: `Module not found`**

Solution:
```bash
pip install -r requirements_web.txt
```

### Mobile Can't Connect

**Check firewall:**
```bash
# Allow port 5000
sudo ufw allow 5000/tcp
```

**Check same network:**
- Computer and mobile must be on same WiFi/network
- Corporate networks may block connections

**Find correct IP:**
```bash
# Linux/Mac
ifconfig | grep inet

# Look for 192.168.x.x or 10.0.x.x
```

### Notifications Not Appearing

**Clear browser cache:**
- Hard refresh: Ctrl+F5 (Windows) or Cmd+Shift+R (Mac)

**Check console:**
- Open browser DevTools (F12)
- Look for JavaScript errors in Console

**Verify API:**
```bash
# Test notifications endpoint
curl http://localhost:5000/api/notifications
```

### Statistics Not Updating

**Check status endpoint:**
```bash
curl http://localhost:5000/api/status
```

**Verify auto-update:**
- Should update every 1 second
- Check browser console for errors

---

## Advanced Features

### Integration with ANC System

To integrate with real hardware:

```python
# In app.py, add real-time audio processing

import threading
from realtime_anti_noise_output import RealtimeAntiNoise

# Create ANC instance
anc_system = RealtimeAntiNoise()

# Background thread for audio processing
def audio_processing_thread():
    while True:
        if state.anc_enabled:
            # Process audio
            audio_data = capture_audio()
            anti_noise = anc_system.generate_anti_noise(audio_data)
            play_audio(anti_noise)

            # Update state
            with state_lock:
                state.noise_intensity = calculate_intensity(audio_data)
                state.current_noise_class = classify_noise(audio_data)

# Start background thread
threading.Thread(target=audio_processing_thread, daemon=True).start()
```

### Custom Notifications

Add custom notification types:

```python
@app.route('/api/custom_notification', methods=['POST'])
def custom_notification():
    data = request.json

    notification = {
        'type': data.get('type', 'info'),
        'title': data['title'],
        'message': data['message'],
        'timestamp': datetime.now().isoformat(),
        'severity': data.get('severity', 'low')
    }

    state.notifications.put(notification)

    return jsonify({'success': True})
```

### WebSocket Support

For real-time bidirectional communication:

```python
from flask_socketio import SocketIO, emit

socketio = SocketIO(app)

@socketio.on('connect')
def handle_connect():
    emit('status_update', get_current_status())

@socketio.on('request_status')
def handle_status_request():
    emit('status_update', get_current_status())
```

---

## Security Considerations

### Production Security

**1. Disable Debug Mode:**
```python
app.run(debug=False)
```

**2. Use HTTPS:**
```python
# With SSL certificate
app.run(ssl_context=('cert.pem', 'key.pem'))
```

**3. Add Authentication:**
```python
from flask_httpauth import HTTPBasicAuth

auth = HTTPBasicAuth()

@auth.verify_password
def verify_password(username, password):
    # Verify credentials
    return check_credentials(username, password)

@app.route('/api/status')
@auth.login_required
def api_status():
    # Protected endpoint
    pass
```

**4. Rate Limiting:**
```python
from flask_limiter import Limiter

limiter = Limiter(app, default_limits=["200 per day", "50 per hour"])

@app.route('/api/toggle_anc')
@limiter.limit("10 per minute")
def api_toggle_anc():
    pass
```

---

## File Structure

```
anc-with-ai/
├── app.py                      # Flask application
├── requirements_web.txt        # Python dependencies
├── templates/
│   └── index.html             # Main HTML template
├── static/
│   ├── css/
│   │   └── style.css          # Styles
│   └── js/
│       └── app.js             # Frontend JavaScript
└── WEB_APP_GUIDE.md           # This file
```

---

## Performance Tips

### Optimize for Mobile

1. **Minimize API calls:**
   - Batch updates
   - Use WebSockets for real-time data

2. **Reduce payload size:**
   - Send only changed data
   - Compress responses

3. **Cache static assets:**
   - Enable browser caching
   - Use CDN for libraries

4. **Lazy load images:**
   - Load images on demand
   - Use placeholder images

### Server Optimization

1. **Use production WSGI server:**
   - gunicorn or uWSGI
   - Multiple workers

2. **Enable compression:**
   ```python
   from flask_compress import Compress
   Compress(app)
   ```

3. **Database connection pooling:**
   - Reuse connections
   - Close properly

---

## Support

**GitHub Issues:** Report bugs and feature requests

**Documentation:** See related guides:
- `REALTIME_ANTI_NOISE_GUIDE.md` - Real-time ANC
- `ANTI_NOISE_VERIFICATION.md` - Technical verification
- `LOCAL_PLAYBACK_INSTRUCTIONS.md` - Local testing

---

**Web app ready for mobile ANC control!** 📱🎧
