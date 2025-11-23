# Local Execution Guide - Full ANC System Testing

Complete guide for running and testing the integrated ANC system locally with microphone and speakers.

---

## Prerequisites Check

Before running, ensure you have:

### 1. Hardware
- ✓ Working microphone (built-in or external)
- ✓ Working speakers/headphones
- ✓ Quiet environment for testing

### 2. Software Dependencies

```bash
# Install all dependencies
pip install -r requirements.txt

# Verify PyAudio installation
python -c "import pyaudio; print('PyAudio OK')"

# Verify other dependencies
python -c "import librosa, sklearn, flask; print('All dependencies OK')"
```

### 3. Trained Models

```bash
# Check if models exist
ls -lh models/*.joblib

# If not found, train models:
python train_sklearn_demo.py
```

---

## Step-by-Step Local Execution

### Step 1: Pre-Flight Check

Run the verification script to ensure everything is ready:

```bash
python verify_integration.py
```

Expected output:
```
Tests passed: 6/7 (or 7/7 with proper numpy version)
✓ Module Imports
✓ ANC Core Initialization
✓ State Management
✓ Web UI Integration
```

### Step 2: Audio Device Check

Verify your microphone and speakers are detected:

```bash
python check_audio_devices.py
```

This will list all available input/output devices.

### Step 3: Quick Test (30 seconds)

Test the system for 30 seconds in core mode:

```bash
python main.py --mode core --duration 30
```

**What to expect:**
1. Initialization messages (7 steps)
2. System starts capturing audio
3. Status updates every 2 seconds
4. Real-time noise classification
5. Anti-noise output to speakers
6. Statistics at the end

**What to listen for:**
- Ambient noise should become quieter
- Speaking should be more muffled
- Background hum should reduce

### Step 4: Full Test with Web UI

Start the system with web interface:

```bash
python main.py --mode web
```

Access the UI:
- Desktop: http://localhost:5000
- Mobile (same WiFi): http://192.168.x.x:5000

**Test these features:**
1. Toggle ANC on/off → Notice sound change
2. Adjust intensity slider → Notice cancellation strength
3. Simulate alarm → ANC should bypass
4. Check notifications → Emergency alert appears
5. Monitor statistics → Counters update

---

## Expected Behavior

### Console Output

```
================================================================================
INITIALIZING ACTIVE NOISE CANCELLATION SYSTEM
================================================================================

[1/7] Connecting to database...
✓ Database connected: anc_system.db

[2/7] Initializing feature extractor...
✓ Feature extractor ready

[3/7] Loading noise classifier...
✓ Classifier loaded: models/noise_classifier_sklearn.joblib

[4/7] Loading emergency detector...
✓ Emergency detector loaded: models/emergency_classifier.joblib

[5/7] Initializing anti-noise generator...
✓ Anti-noise generator ready

[6/7] Initializing audio interface...
✓ PyAudio initialized

[7/7] Setting up system state...
✓ System state initialized

================================================================================
ANC SYSTEM READY
================================================================================

================================================================================
STARTING REAL-TIME ANC SYSTEM
================================================================================

✓ All threads started

Press Ctrl+C to stop...

[CAPTURE] Starting audio capture thread...
[CAPTURE] Input stream opened
[PROCESS] Starting audio processing thread...
[PROCESS] Output stream opened
[STATUS] Starting status display thread...

[STATUS] 14:23:15
  ANC: ENABLED
  Noise: office (confidence: 87.3%)
  Intensity: 68.5 dB
  Emergency: No
  Stats: 15 detections, 0 emergencies
```

### Audio Behavior

**Expected:**
- ✓ Ambient noise reduced (fans, AC, traffic)
- ✓ Background hum quieter
- ✓ Echo/reverb dampened
- ✓ Continuous sounds muffled

**Emergency Override:**
- When alarm/siren detected:
  - ANC automatically disables
  - Full sound passes through
  - Emergency alert in console/web UI

---

## Testing Scenarios

### Scenario 1: Basic Noise Reduction

**Setup:**
1. Play background music or white noise
2. Start ANC: `python main.py --mode core --duration 60`
3. Listen for volume reduction

**Expected Result:**
- Background noise 30-50% quieter
- Still audible but noticeably reduced

**Verify in Console:**
```
[STATUS] Noise: music (confidence: 85%)
[STATUS] Intensity: 72.3 dB
```

### Scenario 2: Office Environment

**Setup:**
1. Sit in office with keyboard typing, phone calls
2. Enable ANC via web UI
3. Adjust intensity slider

**Expected Result:**
- Keyboard clicks softer
- Background conversations muffled
- HVAC noise reduced

**Verify in Web UI:**
- Current Detection shows: "office"
- Confidence > 70%
- Stats increment

### Scenario 3: Emergency Detection

**Setup:**
1. Enable ANC
2. Click "Simulate Alarm" in web UI
3. Observe bypass behavior

**Expected Result:**
- Console shows: "🚨 EMERGENCY DETECTED"
- ANC status: "BYPASS ACTIVE"
- Full audio passes through
- Red alert banner in web UI

**Verify:**
```bash
# Check console output
[STATUS] Emergency: YES - BYPASS ACTIVE
```

### Scenario 4: Traffic Noise

**Setup:**
1. Near window with traffic sounds
2. Start ANC
3. Monitor classification

**Expected Result:**
- Road noise reduced
- Engine sounds dampened
- Classification: "traffic" (confidence > 70%)

---

## Monitoring & Logs

### Real-Time Monitoring

The system provides continuous status updates:

**Console Status (every 2s):**
```
[STATUS] HH:MM:SS
  ANC: ENABLED/DISABLED
  Noise: <class> (confidence: XX%)
  Intensity: XX.X dB
  Emergency: YES/No
  Stats: X detections, Y emergencies
```

**Web UI (live updates):**
- Current noise class badge
- Confidence percentage
- Intensity bar graph
- Emergency banner (when active)
- Notification feed
- Statistics dashboard

### Log Files

If you want to save logs:

```bash
# Save all output to log file
python main.py --mode core 2>&1 | tee anc_session.log

# Save with timestamp
python main.py --mode core 2>&1 | tee "anc_$(date +%Y%m%d_%H%M%S).log"
```

### Error Monitoring

Watch for these error patterns:

**Audio Device Errors:**
```
Error: No Default Input Device Available
→ Fix: Check microphone connection, enable in system settings
```

**Buffer Overrun:**
```
[CAPTURE] Read error: Input overflowed
→ Fix: Reduce chunk_size or increase sample_rate
```

**Model Not Found:**
```
⚠ Classifier not found
→ Fix: Run python train_sklearn_demo.py
```

---

## Performance Testing

### Measure Latency

```bash
# Create test script
cat > test_latency.py << 'EOF'
import time
import numpy as np
from main import ANCSystemCore

anc = ANCSystemCore()

# Generate test audio
audio = np.random.randn(1024).astype(np.float32)

# Measure processing time
start = time.perf_counter()
for _ in range(100):
    anc.process_audio_chunk(audio)
end = time.perf_counter()

avg_latency = (end - start) / 100 * 1000
print(f"Average latency: {avg_latency:.2f} ms")

anc.cleanup()
EOF

python test_latency.py
```

**Expected latency:** <30ms

### Monitor CPU Usage

```bash
# Terminal 1: Run ANC
python main.py --mode core

# Terminal 2: Monitor CPU
top -p $(pgrep -f "python main.py")

# Or use htop for better visualization
htop -p $(pgrep -f "python main.py")
```

**Expected CPU:** 20-25%

### Monitor Memory

```bash
# Check memory usage
ps aux | grep "python main.py" | awk '{print $4 " " $6}'

# Continuous monitoring
watch -n 1 'ps aux | grep "python main.py"'
```

**Expected memory:** ~100-200 MB

---

## Troubleshooting

### Problem: No Audio Output

**Check:**
```bash
# Verify speakers in system
python -c "import pyaudio; p=pyaudio.PyAudio(); print(f'Output devices: {p.get_default_output_device_info()}')"

# Test speaker output
python -c "import numpy as np, pyaudio; p=pyaudio.PyAudio(); s=p.open(format=pyaudio.paFloat32, channels=1, rate=44100, output=True); s.write((0.3*np.sin(2*np.pi*440*np.linspace(0,1,44100))).astype(np.float32).tobytes()); s.close(); p.terminate()"
```

**Solution:**
- Check volume levels
- Verify speaker connection
- Check system audio settings

### Problem: Poor Cancellation Quality

**Symptoms:**
- Noise not reduced
- Added distortion
- Echo/feedback

**Solutions:**

1. **Adjust intensity:**
   ```python
   # In web UI: Move intensity slider
   # Or modify main.py:
   anc_core.set_noise_intensity(0.7)  # Try 0.5-0.9
   ```

2. **Reduce latency:**
   ```python
   # In main.py, reduce chunk size:
   ANCSystemCore(chunk_size=512)  # From 1024
   ```

3. **Calibrate microphone distance:**
   - Move mic closer to noise source
   - Adjust mic gain in system settings

### Problem: High CPU Usage

**Check thread status:**
```bash
# List threads
ps -T -p $(pgrep -f "python main.py")

# Monitor per-thread CPU
top -H -p $(pgrep -f "python main.py")
```

**Solutions:**

1. **Reduce sample rate:**
   ```python
   ANCSystemCore(sample_rate=22050)  # Half of 44100
   ```

2. **Increase chunk size:**
   ```python
   ANCSystemCore(chunk_size=2048)  # Double
   ```

3. **Disable features:**
   ```python
   # Run without emergency detection
   emergency_model_path="none"
   ```

### Problem: Delayed Response

**Measure actual latency:**
```bash
# Use test_latency.py from above
python test_latency.py
```

**If latency > 50ms:**
1. Close other audio applications
2. Reduce buffer size
3. Use faster CPU

### Problem: Classification Inaccurate

**Check model performance:**
```bash
# Re-train with more samples
python collect_training_data.py  # Collect 50+ samples per class
python train_sklearn_demo.py     # Retrain
```

**Verify features:**
```bash
# Test feature extraction
python -c "
from main import ANCSystemCore
import numpy as np
anc = ANCSystemCore()
audio = np.random.randn(44100).astype(np.float32)
features = anc.feature_extractor.extract_feature_vector(audio)
print(f'Features: {len(features)} dimensions')
anc.cleanup()
"
```

---

## Optimization Tips

### For Best Cancellation:

1. **Microphone Placement:**
   - Close to noise source (10-30cm)
   - Same direction as noise arrival
   - Avoid obstructions

2. **Speaker Placement:**
   - Near listening position
   - Opposite polarity to noise
   - Sealed enclosure helps

3. **Environment:**
   - Closed room (no echo)
   - Minimal reflective surfaces
   - Consistent noise source

4. **Settings:**
   - Intensity: 0.7-0.9 for best results
   - Sample rate: 44100 Hz (standard)
   - Chunk size: 1024 samples (23ms)

### For Lowest Latency:

```python
ANCSystemCore(
    sample_rate=44100,  # Keep high for quality
    chunk_size=512,     # Reduce for lower latency
    channels=1          # Mono (fastest)
)
```

### For Best Classification:

1. **Collect diverse samples:**
   ```bash
   python audio_capture.py  # Record 20+ samples per noise type
   ```

2. **Train with augmentation:**
   ```bash
   python train_sklearn_demo.py  # Uses data augmentation
   ```

3. **Verify accuracy:**
   ```bash
   python predict_sklearn.py  # Test on all recordings
   ```

---

## Safety Checks

### Before Running:

- [ ] Volume at reasonable level (50-70%)
- [ ] Headphones removed (use speakers for testing)
- [ ] Emergency sounds testable (alarm simulation)
- [ ] Quick access to Ctrl+C (stop command)

### During Operation:

- [ ] Monitor for audio feedback/squealing
- [ ] Check for overheating (CPU usage)
- [ ] Verify emergency bypass works
- [ ] Test manual stop (Ctrl+C)

### After Session:

- [ ] Review error messages
- [ ] Check statistics (detections, emergencies)
- [ ] Inspect log files
- [ ] Verify graceful shutdown

---

## Quick Reference Commands

```bash
# Basic test (30 seconds)
python main.py --mode core --duration 30

# Full system with web UI
python main.py --mode web

# With logging
python main.py --mode core 2>&1 | tee session.log

# Custom intensity
python -c "from main import ANCSystemCore; anc = ANCSystemCore(); anc.set_noise_intensity(0.8); anc.start_realtime_anc(duration=60)"

# Check audio devices
python check_audio_devices.py

# Verify integration
python verify_integration.py

# Interactive quick start
./quick_start.sh

# Stop running system
Ctrl+C (or click Stop in web UI)
```

---

## Success Criteria

After local execution, you should observe:

✅ **Functional:**
- System initializes without errors
- Audio capture active (status updates)
- Noise classification working (>70% confidence)
- Anti-noise generation (no crashes)
- Speaker output audible

✅ **Performance:**
- Latency <50ms (real-time feel)
- CPU usage <30%
- Memory <300 MB
- No audio glitches/dropouts

✅ **Quality:**
- Ambient noise 30-50% quieter
- No added distortion
- Emergency bypass functional
- Graceful shutdown (Ctrl+C)

✅ **Verification:**
- Console shows status updates
- Web UI responsive (if using)
- Classifications accurate (>70%)
- Statistics increment correctly

---

## Next Steps After Testing

1. **Fine-tune for your environment:**
   - Collect audio samples specific to your space
   - Retrain models with your data
   - Adjust intensity for your preference

2. **Extended testing:**
   - Run for longer periods (hours)
   - Test different noise types
   - Verify stability over time

3. **Production deployment:**
   - Set up as system service
   - Configure auto-start
   - Set up remote monitoring

---

**Ready to test locally!** 🎧🔊

Run: `python main.py --mode core --duration 30` to start your first test.
