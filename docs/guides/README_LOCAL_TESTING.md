# Local Testing Quick Reference

Quick commands for testing the ANC system locally with microphone and speakers.

---

## Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt

# Verify audio hardware
python check_audio_devices.py
```

---

## Quick Start

### Option 1: Automated Test Runner (Recommended)

```bash
./run_local_test.sh
```

This interactive script will:
1. ✓ Check all dependencies
2. ✓ Verify audio devices
3. ✓ Check trained models
4. ✓ Run integration tests
5. ✓ Execute ANC system
6. ✓ Analyze results
7. ✓ Save logs

### Option 2: Manual Execution

```bash
# Quick 30-second test
python main.py --mode core --duration 30

# Full system with web UI
python main.py --mode web

# Extended test with logging
python main.py --mode core --duration 300 2>&1 | tee logs/test.log
```

---

## What to Expect

### Successful Execution

**Console output:**
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
```

**Audio effect:**
- ✓ Background noise 30-50% quieter
- ✓ Ambient sounds muffled
- ✓ Continuous noise dampened
- ✓ No added distortion

**Status updates (every 2 seconds):**
```
[STATUS] 14:23:15
  ANC: ENABLED
  Noise: office (confidence: 87.3%)
  Intensity: 68.5 dB
  Emergency: No
  Stats: 15 detections, 0 emergencies
```

### Emergency Detection Test

When alarm/siren detected:
```
🚨 EMERGENCY DETECTED: alarm (confidence: 95.8%)
   ANC bypassed for safety!

[STATUS] Emergency: YES - BYPASS ACTIVE
```

---

## Monitoring

### Real-time Resource Monitor

In a separate terminal while system is running:

```bash
./monitor_anc.sh
```

Output:
```
Time       CPU%   MEM%   MEM(MB)  Threads  Runtime
--------   ----   ----   -------  -------  -------
14:23:15   22.5   1.2    145.3    5        00:00:15
14:23:16   23.1   1.2    146.1    5        00:00:16
14:23:17   21.8   1.2    145.7    5        00:00:17
```

### Manual Monitoring

```bash
# CPU usage
top -p $(pgrep -f "python main.py")

# Memory usage
ps aux | grep "python main.py"

# Thread count
ps -T -p $(pgrep -f "python main.py") | wc -l
```

---

## Testing Scenarios

### Scenario 1: Office Noise

**Setup:**
- Sit at desk with keyboard, fan, AC
- Enable ANC

**Expected:**
- Keyboard clicks quieter
- Fan noise reduced
- Background conversations muffled

**Command:**
```bash
python main.py --mode core --duration 60
```

### Scenario 2: Traffic Noise

**Setup:**
- Near window with road sounds
- Adjust intensity to 70-90%

**Expected:**
- Engine sounds dampened
- Road noise reduced
- Classification: "traffic"

**Command:**
```bash
python main.py --mode web
# Adjust intensity slider in browser
```

### Scenario 3: Emergency Alert

**Setup:**
- Enable ANC
- Play alarm sound or use web UI simulator

**Expected:**
- ANC automatically disables
- Full sound passes through
- Console shows emergency alert

**Command:**
```bash
python main.py --mode web
# Click "Simulate Alarm" button
```

---

## Performance Benchmarks

**Expected metrics:**

| Metric | Target | Typical |
|--------|--------|---------|
| Latency | <50ms | 25-30ms |
| CPU Usage | <30% | 20-25% |
| Memory | <300MB | 100-200MB |
| Classification Accuracy | >70% | 85-95% |
| Noise Reduction | 30-50% | 40% avg |

---

## Troubleshooting

### No audio output

```bash
# Check speakers
python -c "import pyaudio, numpy as np; p=pyaudio.PyAudio(); s=p.open(format=pyaudio.paFloat32, channels=1, rate=44100, output=True); s.write((0.3*np.sin(2*np.pi*440*np.linspace(0,1,44100))).astype(np.float32).tobytes()); s.close(); p.terminate()"
```

### Poor cancellation

```bash
# Adjust intensity in main.py
python -c "from main import ANCSystemCore; anc = ANCSystemCore(); anc.set_noise_intensity(0.8); anc.start_realtime_anc(duration=60)"
```

### High CPU usage

```bash
# Reduce sample rate
python -c "from main import ANCSystemCore; anc = ANCSystemCore(sample_rate=22050); anc.start_realtime_anc(duration=60)"
```

### Classification errors

```bash
# Retrain models
python train_sklearn_demo.py
```

---

## Web UI Testing

```bash
# Start with web UI
python main.py --mode web
```

**Access:**
- Desktop: http://localhost:5000
- Mobile: http://192.168.x.x:5000 (find IP with `hostname -I`)

**Test features:**
1. ✓ Toggle ANC on/off → Sound change
2. ✓ Intensity slider → Cancellation strength
3. ✓ Simulate alarm → ANC bypass
4. ✓ Notifications → Emergency alert
5. ✓ Statistics → Counters update

---

## Logs

All test runs are logged to:

```
logs/anc_test_YYYYMMDD_HHMMSS.log
```

**View latest log:**
```bash
cat $(ls -t logs/anc_test_*.log | head -1)
```

**Search for errors:**
```bash
grep -i error logs/anc_test_*.log
```

**Extract statistics:**
```bash
grep -A 5 "Session Statistics:" logs/anc_test_*.log
```

---

## Quick Commands

```bash
# Check audio devices
python check_audio_devices.py

# Quick 30s test
python main.py --mode core --duration 30

# Full automated test
./run_local_test.sh

# Monitor running system
./monitor_anc.sh

# Web UI mode
python main.py --mode web

# Stop system
Ctrl+C

# View logs
ls -lh logs/
```

---

## Success Criteria

After local testing, verify:

✅ **Initialization:**
- [ ] All 7 initialization steps complete
- [ ] No error messages
- [ ] PyAudio initialized

✅ **Audio:**
- [ ] Microphone capturing
- [ ] Speakers outputting
- [ ] Noise noticeably reduced

✅ **Classification:**
- [ ] Confidence >70%
- [ ] Correct noise type detected
- [ ] Status updates every 2s

✅ **Emergency:**
- [ ] Alarm detection works
- [ ] ANC bypasses on emergency
- [ ] Alert shown in console/UI

✅ **Performance:**
- [ ] CPU <30%
- [ ] Memory <300MB
- [ ] No audio glitches
- [ ] Graceful shutdown

---

## Next Steps

After successful local testing:

1. **Fine-tune:**
   - Collect audio samples from your environment
   - Retrain models with local data
   - Adjust intensity for preferences

2. **Extended testing:**
   - Run for longer periods (hours)
   - Test different noise types
   - Verify stability

3. **Production:**
   - Set up as system service
   - Configure auto-start
   - Deploy to target hardware

---

## Documentation

- **LOCAL_EXECUTION_GUIDE.md** - Complete testing guide
- **FULL_INTEGRATION_GUIDE.md** - System architecture
- **INTEGRATION_SUMMARY.md** - Component overview
- **WEB_APP_GUIDE.md** - Web interface guide

---

**Ready for local testing!** 🎧

Run: `./run_local_test.sh` to begin.
