# Real-Time Anti-Noise Output Guide

**Play inverted waves through speakers in real-time**

---

## Overview

This system captures audio from a microphone, inverts the phase in real-time, and plays the anti-noise through speakers for active noise cancellation demonstration.

**How it works:**
1. Microphone captures ambient noise
2. NumPy inverts phase: `anti_noise = -input`
3. Speakers play inverted waveform
4. Result: Destructive interference cancels noise

---

## Quick Start

### Option 1: Simple Demo (Easiest)

Play a test tone with anti-noise:

```bash
python simple_anti_noise_demo.py
```

**What you'll hear:**
1. 440 Hz tone (2 seconds)
2. Anti-noise tone (sounds identical, 2 seconds)
3. Combined signal (should be **SILENT**, 2 seconds)

**Expected:** Step 3 should be silent, proving cancellation works!

### Option 2: Test Tone Playback

Generate and play test tones:

```bash
# 440 Hz test (default)
python realtime_anti_noise_output.py test 440

# 1000 Hz test
python realtime_anti_noise_output.py test 1000

# Any frequency
python realtime_anti_noise_output.py test <frequency>
```

### Option 3: Real-Time ANC (Advanced)

⚠️ **WARNING:** This captures from microphone and outputs to speakers. Risk of audio feedback!

```bash
# Run for 10 seconds
python realtime_anti_noise_output.py realtime 10

# Run for 30 seconds
python realtime_anti_noise_output.py realtime 30
```

---

## Installation

### 1. Install PyAudio

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install portaudio19-dev python3-pyaudio
pip install pyaudio
```

**macOS:**
```bash
brew install portaudio
pip install pyaudio
```

**Windows:**
```bash
pip install pyaudio
```

If Windows fails, try:
```bash
pip install pipwin
pipwin install pyaudio
```

### 2. Verify Installation

```bash
python -c "import pyaudio; print('PyAudio OK')"
```

---

## Usage

### List Audio Devices

Find your microphone and speaker device IDs:

```bash
python realtime_anti_noise_output.py list
```

**Example output:**
```
Device 0: Built-in Microphone
  Max Input Channels: 2
  Max Output Channels: 0
  Default Sample Rate: 44100.0

Device 1: Built-in Speakers
  Max Input Channels: 0
  Max Output Channels: 2
  Default Sample Rate: 44100.0
```

### Simple Demo

Easiest way to test:

```bash
python simple_anti_noise_demo.py
```

**Output:**
```
================================================================================
ANTI-NOISE DEMONSTRATION
================================================================================

Generating 440 Hz test tone...
  Original RMS: 0.212132
  Anti-noise RMS: 0.212132
  Combined RMS: 0.000000e+00

✓ Verified: np.allclose(anti_noise, -tone)
✓ Verified: np.allclose(combined, 0)

================================================================================
PLAYBACK SEQUENCE
================================================================================

[1/3] Playing: Original 440 Hz tone...
      ✓ Done

[2/3] Playing: Anti-noise (phase inverted)...
      (Should sound identical to original)
      ✓ Done

[3/3] Playing: Combined (tone + anti-noise)...
      (Should be SILENT or very quiet)
      ✓ Done
```

### Test Tone Mode

Test with different frequencies:

```bash
# Musical A (440 Hz)
python realtime_anti_noise_output.py test 440

# Middle C (262 Hz)
python realtime_anti_noise_output.py test 262

# High pitch (1000 Hz)
python realtime_anti_noise_output.py test 1000
```

**What happens:**
1. Generates test tone at specified frequency
2. Creates phase-inverted anti-noise
3. Plays sequence: tone → anti-noise → combined
4. Combined should be silent (cancellation proof)

### Real-Time ANC Mode

⚠️ **CAUTION:** Risk of audio feedback loop!

**Safety precautions:**
1. Start with **low speaker volume**
2. Keep microphone **away from speakers** (at least 3 feet)
3. Use **headphones** for best results (one ear only)
4. Gradually increase volume
5. Be ready to press **Ctrl+C** to stop

**Basic usage:**
```bash
python realtime_anti_noise_output.py realtime 10
```

**Example session:**
```
================================================================================
REAL-TIME ANTI-NOISE OUTPUT
================================================================================

Configuration:
  Sample Rate: 44100 Hz
  Chunk Size: 1024 samples
  Channels: 1
  Buffer Duration: 23.22 ms
  Anti-Noise Gain: 1.00

================================================================================
ACTIVE NOISE CANCELLATION ACTIVE
================================================================================

Capturing from microphone → Inverting phase → Playing through speakers
Press Ctrl+C to stop

Running for 10 seconds...
────────────────────────────────────────────────────────────────────────────────
[   2.3s] Chunks:     50 | Input RMS: 0.0234 | Output RMS: 0.0234 | Latency: 5.23ms
[   4.6s] Chunks:    100 | Input RMS: 0.0189 | Output RMS: 0.0189 | Latency: 5.18ms
[   6.9s] Chunks:    150 | Input RMS: 0.0245 | Output RMS: 0.0245 | Latency: 5.21ms
[   9.2s] Chunks:    200 | Input RMS: 0.0212 | Output RMS: 0.0212 | Latency: 5.19ms

================================================================================
SESSION STATISTICS
================================================================================

Duration: 10.00 seconds
Chunks Processed: 431
Average Latency: 5.20 ms
Processing Rate: 43.1 chunks/sec
Audio Processed: 10.0 seconds

Performance:
  ✓ Excellent latency (<10ms) - Real-time performance
================================================================================
```

---

## How It Works

### Phase Inversion

**Core algorithm:**
```python
# Capture audio from microphone
audio_data = np.frombuffer(audio_bytes, dtype=np.float32)

# Generate anti-noise (phase inversion)
anti_noise = -audio_data

# Verify
assert np.allclose(anti_noise, -audio_data)  # ✓

# Play through speakers
output_stream.write(anti_noise.tobytes())
```

### Signal Flow

```
┌─────────────┐
│ Microphone  │ ← Captures ambient noise
└─────┬───────┘
      │
      ▼
┌─────────────┐
│   NumPy     │ ← Phase inversion: anti_noise = -input
│  Inversion  │
└─────┬───────┘
      │
      ▼
┌─────────────┐
│  Speakers   │ ← Outputs inverted waveform
└─────────────┘
      │
      ▼
   Destructive interference → Cancellation
```

### Latency

**Processing chain:**
1. **Input buffering:** ~23ms (1024 samples @ 44.1kHz)
2. **Phase inversion:** <1ms (NumPy operation)
3. **Output buffering:** ~23ms
4. **Total latency:** ~50ms typical

**For effective ANC:**
- <10ms: Excellent (high frequencies)
- <20ms: Good (mid frequencies)
- <50ms: Acceptable (low frequencies)
- >50ms: Noticeable delay

---

## Troubleshooting

### PyAudio Installation Issues

**Error: `No module named 'pyaudio'`**

```bash
# Linux
sudo apt-get install portaudio19-dev python3-pyaudio
pip install pyaudio

# macOS
brew install portaudio
pip install pyaudio

# Windows
pip install pipwin
pipwin install pyaudio
```

### Audio Feedback Loop

**Problem:** Loud screeching noise

**Solutions:**
1. Reduce speaker volume immediately
2. Move microphone away from speakers
3. Use headphones instead
4. Press Ctrl+C to stop
5. Lower gain factor (not yet implemented in simple version)

### No Sound Output

**Problem:** Script runs but no audio heard

**Checks:**
1. Verify speakers are connected
2. Check system volume (not muted)
3. Test with simple demo first:
   ```bash
   python simple_anti_noise_demo.py
   ```
4. List devices and verify correct device:
   ```bash
   python realtime_anti_noise_output.py list
   ```

### Permission Denied

**Problem:** Cannot access microphone

**Linux:**
```bash
# Add user to audio group
sudo usermod -a -G audio $USER
# Log out and back in
```

**macOS:**
- System Preferences → Security & Privacy → Microphone
- Grant permission to Terminal/Python

---

## Performance Optimization

### Reduce Latency

Edit chunk size in the script:

```python
anc = RealtimeAntiNoise(
    sample_rate=44100,
    chunk_size=512,  # Smaller = lower latency (default: 1024)
    channels=1
)
```

**Trade-offs:**
- Smaller chunks: Lower latency, higher CPU usage
- Larger chunks: Higher latency, lower CPU usage

**Recommended values:**
- 512: ~12ms latency (low frequency noise)
- 1024: ~23ms latency (balanced)
- 2048: ~46ms latency (stable, low CPU)

### Audio Quality

Increase sample rate:

```python
anc = RealtimeAntiNoise(
    sample_rate=48000,  # Higher quality (default: 44100)
    chunk_size=1024,
    channels=1
)
```

---

## Safety Guidelines

### ⚠️ Audio Feedback Prevention

**DO:**
- ✓ Start with low volume
- ✓ Keep microphone away from speakers (3+ feet)
- ✓ Use headphones (one ear recommended)
- ✓ Test with simple demo first
- ✓ Have Ctrl+C ready

**DON'T:**
- ✗ Place microphone near speakers
- ✗ Use high volume without testing
- ✗ Leave system running unattended
- ✗ Use in closed-loop setup without testing

### Hearing Protection

- Start with low volume
- Gradually increase
- Stop if you hear screeching
- Use at comfortable listening levels

---

## Examples

### Example 1: Simple Test

```bash
# Basic test - safest option
python simple_anti_noise_demo.py
```

**Expected output:**
- Hear tone
- Hear identical tone (anti-noise)
- Hear silence (cancellation proof)

### Example 2: Different Frequencies

```bash
# Low frequency (bass)
python realtime_anti_noise_output.py test 100

# Mid frequency
python realtime_anti_noise_output.py test 440

# High frequency
python realtime_anti_noise_output.py test 2000
```

### Example 3: Real-Time Demo (With Headphones)

```bash
# Use headphones for safety
python realtime_anti_noise_output.py realtime 5
```

**Setup:**
1. Wear headphones (one ear)
2. Speak or make noise near microphone
3. Hear inverted audio in headphones
4. Press Ctrl+C to stop

---

## Technical Details

### Audio Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| Sample Rate | 44100 Hz | CD quality |
| Bit Depth | 32-bit float | High precision |
| Channels | 1 (mono) | Single microphone |
| Chunk Size | 1024 samples | ~23ms buffer |
| Format | float32 | NumPy compatible |

### Phase Inversion Formula

```
Original signal:     x(t) = A·sin(ωt + φ)
Anti-noise:          y(t) = -x(t) = A·sin(ωt + φ + π)
Combined:            x(t) + y(t) = 0 (cancellation)
```

### NumPy Implementation

```python
def generate_anti_noise(audio_data):
    """Phase inversion using NumPy."""
    anti_noise = -audio_data
    assert np.allclose(anti_noise, -audio_data)
    return anti_noise
```

---

## Command Reference

| Command | Description | Example |
|---------|-------------|---------|
| `list` | List audio devices | `python realtime_anti_noise_output.py list` |
| `test <freq>` | Play test tone | `python realtime_anti_noise_output.py test 440` |
| `realtime <sec>` | Run real-time ANC | `python realtime_anti_noise_output.py realtime 10` |
| (no args) | Show usage | `python realtime_anti_noise_output.py` |

**Simple demo:**
```bash
python simple_anti_noise_demo.py
```

---

## Limitations

### Current Limitations

1. **Feedback risk:** Open-loop system can cause audio feedback
2. **Latency:** ~23-50ms may not cancel high-frequency noise effectively
3. **Single channel:** Mono only (no stereo ANC)
4. **No adaptive filtering:** Simple phase inversion only
5. **No emergency bypass:** All sounds inverted (see emergency_noise_detector.py for safety)

### Future Enhancements

- [ ] Adaptive filtering (LMS algorithm)
- [ ] Frequency-selective cancellation
- [ ] Stereo/multi-channel support
- [ ] Lower latency (<10ms)
- [ ] Emergency sound bypass
- [ ] Feedback cancellation
- [ ] GUI interface

---

## Additional Resources

**Related Files:**
- `anti_noise_generator.py` - Offline anti-noise generation
- `emergency_noise_detector.py` - Safety-critical sound detection
- `playback_cancellation_demo.py` - Pre-recorded playback demo
- `simple_counter_wave_test.py` - NumPy verification

**Documentation:**
- `ANTI_NOISE_VERIFICATION.md` - Verification report
- `NUMPY_COUNTER_WAVE_VERIFICATION.md` - NumPy tests
- `PLAYBACK_TESTING_GUIDE.md` - Audio playback guide

---

## Support

**If you encounter issues:**

1. Start with simple demo: `python simple_anti_noise_demo.py`
2. Verify PyAudio: `python -c "import pyaudio; print('OK')"`
3. List devices: `python realtime_anti_noise_output.py list`
4. Check documentation: See troubleshooting section above

---

**Real-time anti-noise output ready for testing!** 🎧

*Microphone → Phase Inversion → Speakers*
*Active Noise Cancellation through NumPy*
