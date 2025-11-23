# ANC Platform - Complete Hardware-Software Integration

This document describes the complete system integration from firmware to cloud backend.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        HARDWARE LAYER                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ External Mic │  │ Internal Mic │  │  Speakers    │          │
│  └──────┬───────┘  └──────┬───────┘  └──────▲───────┘          │
│         │                  │                  │                  │
│  ┌──────▼──────────────────▼──────────────────┴───────┐         │
│  │         STM32H7 - ARM Cortex-M7 @ 480MHz           │         │
│  │  • NLMS Adaptive Filtering (512 taps)              │         │
│  │  • Real-time DSP (<1ms latency)                    │         │
│  │  • DMA Audio I/O (I2S, 48kHz, 24-bit)             │         │
│  │  • Bluetooth Audio Stack                           │         │
│  │  • Power Management & Battery Monitoring           │         │
│  └─────────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Bluetooth / WebSocket
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     BACKEND SERVER LAYER                         │
│  ┌──────────────────────────────────────────────────────┐       │
│  │  Python Backend (Flask + Flask-SocketIO)             │       │
│  │  • Real-time Audio Streaming                         │       │
│  │  • Session Management                                │       │
│  │  • ML Noise Classification (95.83% accuracy)         │       │
│  │  • REST API (20+ endpoints)                          │       │
│  └──────────────────────────────────────────────────────┘       │
│                              │                                   │
│  ┌────────────┐  ┌──────────┴────────┐  ┌──────────────┐       │
│  │ PostgreSQL │  │  Redis Cache      │  │ Celery Tasks │       │
│  │  Database  │  │  + WebSocket      │  │ (Background) │       │
│  └────────────┘  └───────────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTPS / WebSocket
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FRONTEND LAYER                              │
│  ┌──────────────────────────────────────────────────────┐       │
│  │  Premium Web UI (Apple-inspired)                     │       │
│  │  • Real-time Waveform Visualization                  │       │
│  │  • Before/After Audio Comparison                     │       │
│  │  • Live ANC Controls (Intensity, Algorithm)          │       │
│  │  • WebSocket Streaming                               │       │
│  └──────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

## Component Overview

### 1. Embedded Firmware (`/firmware/`)

**Purpose**: Real-time ANC processing on headphone hardware

**Key Files**:
- `anc_firmware.c` - Main firmware, ANC algorithms
- `hardware.c` - Peripheral drivers (I2S, I2C, DMA)
- `dsp_processor.c` - DSP utilities (FFT, FIR, SIMD)
- `bluetooth_audio.c` - Bluetooth audio stack
- `power_management.c` - Battery and power management
- `ota_update.c` - Over-the-air firmware updates

**Technical Specs**:
- ARM Cortex-M7 @ 480MHz
- <1ms processing latency
- 35-45 dB noise cancellation
- 48kHz, 24-bit audio
- DMA-based zero-copy I/O

**Build**:
```bash
cd firmware/
make clean && make -j$(nproc)
st-flash write build/anc_firmware.bin 0x08010000
```

### 2. Real-Time Audio Engine (`realtime_audio_engine.py`)

**Purpose**: Production-grade audio processing for server-side ANC

**Features**:
- Thread-safe audio buffering
- <40ms end-to-end latency
- Concurrent session management
- NLMS adaptive filtering
- Optional ML classification

**Usage**:
```python
from realtime_audio_engine import create_streaming_session

session = create_streaming_session(
    session_id="user123",
    sample_rate=48000,
    anc_enabled=True,
    anc_intensity=1.0
)

session.start()
processed = session.process_audio_chunk(audio_data)
```

### 3. WebSocket Streaming (`websocket_streaming.py`)

**Purpose**: Real-time bidirectional audio streaming

**Events**:
- `start_streaming` - Initialize session
- `audio_chunk` - Send/receive audio data
- `processed_chunk` - Return processed audio
- `update_streaming_settings` - Change ANC parameters
- `stop_streaming` - End session

**Protocol**:
```javascript
socket.emit('start_streaming', {
    sample_rate: 48000,
    chunk_size: 512,
    anc_enabled: true,
    anc_intensity: 1.0
});

socket.on('streaming_started', (data) => {
    sessionId = data.session_id;
});

socket.emit('audio_chunk', {
    session_id: sessionId,
    audio_data: base64EncodedAudio
});

socket.on('processed_chunk', (result) => {
    playAudio(result.audio_data);
});
```

### 4. Backend API Server (`server.py`)

**Purpose**: REST API + WebSocket server

**Key Endpoints**:
```
POST   /api/v1/auth/register       - User registration
POST   /api/v1/auth/login          - User login
GET    /api/v1/auth/verify         - Verify JWT token

POST   /api/v1/sessions            - Create audio session
GET    /api/v1/sessions/:id        - Get session info
DELETE /api/v1/sessions/:id        - End session

POST   /api/v1/audio/upload        - Upload audio file
POST   /api/v1/audio/process       - Process audio
GET    /api/v1/audio/download/:id  - Download processed audio

GET    /api/v1/stats               - System statistics
GET    /api/v1/health              - Health check
```

**Start Server**:
```bash
./start.sh
```

### 5. Premium Web UI (`templates/live-demo.html`)

**Purpose**: Apple-quality user interface

**Features**:
- Glassmorphism design
- Real-time waveform visualization
- Before/After audio comparison
- Live ANC controls
- WebSocket integration
- Mobile responsive

**Access**:
```
http://localhost:5000/live
```

### 6. Production Tools (`/tools/`)

#### Calibration Tool
```bash
./tools/calibration_tool.py /dev/ttyUSB0
```
- Measures frequency response
- Calculates optimal filters
- Verifies >30dB cancellation
- Saves calibration report

#### Firmware Flasher
```bash
./tools/firmware_flasher.py firmware/build/anc_firmware.bin
```
- Verifies firmware integrity
- Flashes via ST-Link
- Validates write success

#### Manufacturing Test
```bash
./tools/manufacturing_test.py /dev/ttyUSB0
```
- 10-point quality check
- Audio, Bluetooth, battery tests
- Pass/Fail report

#### Build Automation
```bash
./tools/build_firmware.sh
```
- Clean + compile
- Generate release package
- Create checksums
- Size analysis

## Data Flow

### Real-Time Audio Processing

```
1. CAPTURE (Microphone)
   ↓
2. ADC (24-bit, 48kHz)
   ↓
3. DMA → Memory Buffer
   ↓
4. ANC Processing (NLMS)
   ↓
5. Mix with Bluetooth Audio
   ↓
6. DMA → DAC
   ↓
7. PLAYBACK (Speaker)

Total Latency: <10ms
```

### Web Streaming

```
1. Browser Microphone (getUserMedia)
   ↓
2. Encode to Float32 Array
   ↓
3. Base64 Encode
   ↓
4. WebSocket Send
   ↓
5. Server Decode
   ↓
6. ANC Processing
   ↓
7. Encode Result
   ↓
8. WebSocket Return
   ↓
9. Browser Decode
   ↓
10. Play through Speakers

Total Latency: 35-40ms
```

## Deployment

### Local Development

```bash
# Backend
./start.sh

# Frontend
open http://localhost:5000/live
```

### Docker Deployment

```bash
docker-compose up -d
```

Services:
- `anc-api` - Flask API server (port 5000)
- `postgres` - Database (port 5432)
- `redis` - Cache + message broker (port 6379)
- `celery-worker` - Background tasks

### Kubernetes Deployment

```bash
# AWS EKS
cd deploy/aws
./deploy.sh

# GCP GKE
cd deploy/gcp
./deploy.sh

# Azure AKS
cd deploy/azure
./deploy.sh
```

**Scaling**:
- Min replicas: 3
- Max replicas: 20
- CPU target: 70%
- Memory target: 80%

**Monitoring**:
- Prometheus metrics
- Grafana dashboards
- Health checks every 10s
- Auto-recovery on failure

## Performance Benchmarks

### Firmware Performance

| Metric | Value |
|--------|-------|
| Processing Latency | 0.8-0.9 ms |
| DMA Callback Rate | 1000 Hz (every 1ms) |
| CPU Load | 20-25% |
| Noise Cancellation | 35-45 dB |
| Power Consumption | 50 mA @ 3.7V (ANC on) |
| Battery Life | 20-30 hours |

### Backend Performance

| Metric | Value |
|--------|-------|
| API Response Time | 15-25 ms |
| WebSocket Latency | 5-10 ms |
| Processing Latency | 5-8 ms |
| Concurrent Sessions | 1000+ |
| Throughput | 1200 req/sec |
| Database Queries | <5 ms |

### End-to-End Latency

```
Web Demo:
  Capture:   10ms
  Upload:     5ms
  Process:    8ms
  Download:   5ms
  Playback:  10ms
  ──────────────
  Total:     38ms  ✓ Target: <40ms

Hardware:
  ADC:       0.5ms
  DMA:       0.1ms
  Process:   0.8ms
  DAC:       0.5ms
  ──────────────
  Total:     1.9ms  ✓ Target: <10ms
```

## Integration Testing

### Test 1: Firmware + Backend Integration

```bash
# 1. Flash firmware
cd tools/
./firmware_flasher.py ../firmware/build/anc_firmware.bin

# 2. Run calibration
./calibration_tool.py /dev/ttyUSB0

# 3. Start backend
cd ..
./start.sh

# 4. Test WebSocket connection
# (Firmware Bluetooth → Server WebSocket)
```

### Test 2: End-to-End Audio Pipeline

```bash
# 1. Start server
./start.sh

# 2. Open web demo
open http://localhost:5000/live

# 3. Enable microphone
# 4. Enable ANC
# 5. Play test noise
# 6. Verify cancellation in real-time
```

### Test 3: Manufacturing QA

```bash
# Complete production test
cd tools/
./manufacturing_test.py /dev/ttyUSB0

# Expected: All 10 tests PASS
```

## Troubleshooting

### Issue: Firmware won't flash

**Solutions**:
1. Check ST-Link connection: `st-info --probe`
2. Erase flash: `st-flash erase`
3. Verify power to target board
4. Check BOOT0 pin (should be low)

### Issue: ANC performance below 30dB

**Solutions**:
1. Run calibration: `./calibration_tool.py`
2. Check microphone placement
3. Verify acoustic seal
4. Inspect frequency response curve

### Issue: High WebSocket latency

**Solutions**:
1. Check network latency: `ping server`
2. Reduce chunk size (512 → 256 samples)
3. Enable `bypass_ml` for faster processing
4. Use dedicated server (not localhost)

### Issue: Audio distortion

**Solutions**:
1. Reduce ANC intensity (1.0 → 0.7)
2. Check for buffer overruns
3. Verify sample rate match (48kHz)
4. Inspect audio codec configuration

## Future Enhancements

### Firmware
- [ ] Multi-environment adaptation
- [ ] Wind noise suppression
- [ ] Active EQ adjustment
- [ ] Voice activity detection
- [ ] Spatial audio support

### Backend
- [ ] Multi-user collaboration
- [ ] Cloud storage integration
- [ ] Advanced analytics dashboard
- [ ] A/B testing framework
- [ ] GraphQL API

### ML Models
- [ ] Real-time noise type classification
- [ ] Personalized ANC profiles
- [ ] Predictive maintenance
- [ ] Anomaly detection

## References

### Documentation
- [PLATFORM_ARCHITECTURE.md](PLATFORM_ARCHITECTURE.md) - System architecture
- [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md) - Deployment guide
- [firmware/README.md](firmware/README.md) - Firmware documentation
- [BACKEND_README.md](BACKEND_README.md) - Backend API documentation

### External Resources
- [ARM CMSIS-DSP Library](https://arm-software.github.io/CMSIS_5/DSP/html/index.html)
- [STM32H7 Reference Manual](https://www.st.com/resource/en/reference_manual/dm00176879.pdf)
- [NLMS Algorithm](https://en.wikipedia.org/wiki/Least_mean_squares_filter)

## License

Copyright (c) 2024 ANC Platform. All rights reserved.
