# AWS IoT Integration for ANC Platform

Complete AWS IoT Core integration providing secure device connectivity, real-time data synchronization, and telemetry collection for ANC devices.

## Features

- **🔒 Secure Connection**: Certificate-based authentication with TLS 1.2
- **🔄 Device Shadow Sync**: Bidirectional state synchronization
- **📊 Telemetry Publishing**: Real-time metrics and events
- **🔁 Auto-Reconnection**: Automatic reconnection with exponential backoff
- **📦 Offline Buffering**: Message queuing during disconnection
- **⚡ High Performance**: Batch publishing and rate limiting
- **🛡️ Fail-Safe**: Graceful error handling and recovery

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ANC Device                                │
│  ┌────────────────────────────────────────────────────────┐ │
│  │         Data Sync Orchestrator                         │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐             │ │
│  │  │ IoT Conn │  │  Shadow  │  │Telemetry │             │ │
│  │  │ Manager  │  │   Sync   │  │Publisher │             │ │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘             │ │
│  └───────┼─────────────┼─────────────┼────────────────────┘ │
└──────────┼─────────────┼─────────────┼──────────────────────┘
           │             │             │
           │   MQTT over TLS (8883)    │
           ▼             ▼             ▼
┌─────────────────────────────────────────────────────────────┐
│                   AWS IoT Core                               │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │   Device   │  │   Device   │  │    Topic   │            │
│  │  Registry  │  │   Shadow   │  │  Routing   │            │
│  └──────┬─────┘  └──────┬─────┘  └──────┬─────┘            │
└─────────┼────────────────┼────────────────┼──────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────┐
│              AWS IoT Rules Engine                            │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐        │
│  │  Telemetry  │  │   Metrics    │  │  Emergency  │        │
│  │     →       │  │      →       │  │      →      │        │
│  │  DynamoDB   │  │     S3       │  │   Lambda    │        │
│  └─────────────┘  └──────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
cd cloud/iot/
pip install -r requirements.txt
```

### 2. Deploy AWS Infrastructure

```bash
# Deploy IoT Core resources with Terraform
cd ../terraform/

# Initialize Terraform
terraform init

# Deploy
terraform apply
```

### 3. Provision Device

```bash
# Create IoT thing and certificates
aws iot create-keys-and-certificate \
    --set-as-active \
    --certificate-pem-outfile cert.pem \
    --private-key-outfile private.key \
    --public-key-outfile public.key

# Create thing
aws iot create-thing --thing-name anc-device-001

# Attach certificate to thing
aws iot attach-thing-principal \
    --thing-name anc-device-001 \
    --principal <certificate-arn>

# Attach policy to certificate
aws iot attach-policy \
    --policy-name production-anc-device-policy \
    --target <certificate-arn>

# Download Amazon Root CA
wget https://www.amazontrust.com/repository/AmazonRootCA1.pem
```

### 4. Use in Your Application

```python
from cloud.iot import DataSyncOrchestrator

# Initialize orchestrator
orchestrator = DataSyncOrchestrator(
    thing_name='anc-device-001',
    endpoint='xxxxx.iot.us-east-1.amazonaws.com',
    cert_path='cert.pem',
    key_path='private.key',
    root_ca_path='AmazonRootCA1.pem'
)

# Start data synchronization
orchestrator.start()

# Update ANC state
orchestrator.update_anc_state(
    enabled=True,
    intensity=0.85,
    algorithm='nlms'
)

# Publish metrics
orchestrator.publish_metrics(
    anc_metrics={
        'latency_ms': 35.2,
        'cancellation_db': 42.5,
        'snr_improvement_db': 38.2
    },
    system_metrics={
        'battery_level': 85,
        'cpu_usage': 45.2,
        'memory_usage': 68.5
    }
)

# Report emergency event
orchestrator.report_emergency({
    'is_emergency': True,
    'predicted_class': 'fire_alarm',
    'confidence': 0.94,
    'action': 'anc_bypassed'
})

# Run forever (blocking)
orchestrator.run_forever()
```

## Components

### 1. IoTConnection

Manages MQTT connection to AWS IoT Core with automatic reconnection.

```python
from cloud.iot import IoTConnection

iot = IoTConnection(
    thing_name='anc-device-001',
    endpoint='xxxxx.iot.us-east-1.amazonaws.com',
    cert_path='cert.pem',
    key_path='private.key',
    root_ca_path='AmazonRootCA1.pem'
)

# Connect
iot.connect()

# Publish message
iot.publish('anc/devices/anc-device-001/status', {'status': 'online'})

# Subscribe to topic
def on_message(topic, payload):
    print(f"Received: {payload}")

iot.subscribe('anc/devices/anc-device-001/commands', on_message)

# Check connection status
print(iot.get_status())
```

### 2. DeviceShadowSync

Synchronizes device state with AWS IoT Device Shadow.

```python
from cloud.iot import DeviceShadowSync

shadow = DeviceShadowSync(iot_connection, thing_name='anc-device-001')

# Update reported state
shadow.update_reported_state({
    'anc_enabled': True,
    'anc_intensity': 0.85,
    'battery_level': 85
})

# Handle desired state changes
def on_delta(delta):
    print(f"Desired state changed: {delta}")
    # Apply changes to device

shadow.on_delta_callback = on_delta

# Start automatic sync
shadow.start_sync()
```

### 3. TelemetryPublisher

Publishes device telemetry and metrics to AWS IoT.

```python
from cloud.iot import TelemetryPublisher

telemetry = TelemetryPublisher(iot_connection, device_id='anc-device-001')

# Publish ANC metrics
telemetry.publish_anc_metrics({
    'latency_ms': 35.2,
    'cancellation_db': 42.5,
    'snr_improvement_db': 38.2
})

# Publish audio metrics
telemetry.publish_audio_metrics({
    'noise_type': 'office',
    'confidence': 0.94,
    'rms': 0.45
})

# Publish system metrics
telemetry.publish_system_metrics({
    'battery_level': 85,
    'cpu_usage': 45.2,
    'temperature': 42.3
})

# Start automatic batching
telemetry.start_publishing()
```

## Device Shadow Schema

### Reported State

State reported by the device:

```json
{
  "state": {
    "reported": {
      "status": "online",
      "device_id": "anc-device-001",
      "firmware_version": "1.2.3",
      "anc_enabled": true,
      "anc_intensity": 0.85,
      "anc_algorithm": "nlms",
      "battery_level": 85,
      "noise_type": "office",
      "confidence": 0.94,
      "emergency_detected": false,
      "uptime": 3600,
      "timestamp": "2025-11-16T14:30:00Z"
    }
  }
}
```

### Desired State

State desired by the cloud application:

```json
{
  "state": {
    "desired": {
      "anc_enabled": true,
      "anc_intensity": 0.9,
      "anc_algorithm": "nlms"
    }
  }
}
```

### Delta (Difference)

AWS IoT automatically computes delta:

```json
{
  "state": {
    "anc_intensity": 0.9
  }
}
```

## MQTT Topics

### Device Topics

| Topic | Direction | Purpose |
|-------|-----------|---------|
| `anc/devices/{deviceId}/status` | Device → Cloud | Device status updates |
| `anc/devices/{deviceId}/commands` | Cloud → Device | Commands to device |
| `anc/devices/{deviceId}/emergency` | Device → Cloud | Emergency events |

### Telemetry Topics

| Topic | Purpose |
|-------|---------|
| `anc/telemetry/{deviceId}/anc` | ANC performance metrics |
| `anc/telemetry/{deviceId}/audio` | Audio classification metrics |
| `anc/telemetry/{deviceId}/system` | System health metrics |
| `anc/telemetry/{deviceId}/errors` | Error logs |

### Shadow Topics

| Topic | Purpose |
|-------|---------|
| `$aws/things/{thingName}/shadow/update` | Update shadow |
| `$aws/things/{thingName}/shadow/update/accepted` | Update confirmation |
| `$aws/things/{thingName}/shadow/update/delta` | State delta notification |
| `$aws/things/{thingName}/shadow/get` | Request current shadow |

## Configuration

### Environment Variables

```bash
# AWS IoT Configuration
export IOT_ENDPOINT="xxxxx.iot.us-east-1.amazonaws.com"
export IOT_THING_NAME="anc-device-001"
export IOT_CERT_PATH="/path/to/cert.pem"
export IOT_KEY_PATH="/path/to/private.key"
export IOT_ROOT_CA_PATH="/path/to/AmazonRootCA1.pem"

# Optional Configuration
export IOT_PORT="8883"
export IOT_KEEP_ALIVE="60"
export TELEMETRY_BATCH_SIZE="10"
export TELEMETRY_BATCH_INTERVAL="30"
```

### Configuration File

```json
{
  "iot": {
    "thing_name": "anc-device-001",
    "endpoint": "xxxxx.iot.us-east-1.amazonaws.com",
    "cert_path": "/path/to/cert.pem",
    "key_path": "/path/to/private.key",
    "root_ca_path": "/path/to/AmazonRootCA1.pem",
    "port": 8883,
    "keep_alive": 60
  },
  "telemetry": {
    "batch_size": 10,
    "batch_interval": 30,
    "max_buffer_size": 1000
  },
  "shadow": {
    "sync_interval": 60
  }
}
```

## Troubleshooting

### Connection Issues

**Problem**: `Connection failed: Not authorized`

**Solution**: Check that:
- Certificate is active
- Policy is attached to certificate
- Thing principal is attached

```bash
# List certificates
aws iot list-certificates

# Check policy attachment
aws iot list-attached-policies --target <certificate-arn>

# Check thing principal
aws iot list-thing-principals --thing-name anc-device-001
```

**Problem**: `Connection timeout`

**Solution**:
- Verify endpoint URL
- Check firewall allows port 8883
- Verify certificate file paths

### Shadow Issues

**Problem**: Shadow updates rejected

**Solution**: Check shadow document size (max 8KB)

```python
# Check shadow size
import json
state = shadow.get_state()
size = len(json.dumps(state))
print(f"Shadow size: {size} bytes")
```

### Telemetry Issues

**Problem**: Messages not appearing in CloudWatch

**Solution**: Verify IoT Rule is enabled

```bash
# List rules
aws iot list-topic-rules

# Get rule details
aws iot get-topic-rule --rule-name production_anc_telemetry_to_dynamodb
```

## Performance

### Latency

| Operation | Typical Latency | Notes |
|-----------|----------------|-------|
| Publish message | 10-50ms | Depends on QoS |
| Shadow update | 50-100ms | Includes round-trip |
| Receive message | 10-30ms | From cloud to device |
| Delta notification | 50-150ms | Shadow delta processing |

### Throughput

| Metric | Limit | Recommended |
|--------|-------|-------------|
| Publish rate | 100 msg/sec | 10 msg/sec |
| Subscribe rate | 500 msg/sec | N/A |
| Connection rate | 500/sec | Maintain persistent connection |
| Message size | 128KB | <8KB |

## Security

### Certificate Management

```bash
# Generate new certificate
aws iot create-keys-and-certificate \
    --set-as-active \
    --certificate-pem-outfile cert.pem \
    --private-key-outfile private.key

# Rotate certificate
aws iot update-certificate --certificate-id <cert-id> --new-status INACTIVE

# Revoke certificate
aws iot update-certificate --certificate-id <cert-id> --new-status REVOKED
```

### Policy Best Practices

- Use least privilege principle
- Restrict resources with thing name variable
- Enable certificate revocation
- Monitor certificate expiration
- Rotate certificates regularly

## Monitoring

### CloudWatch Metrics

```bash
# View connection metrics
aws cloudwatch get-metric-statistics \
    --namespace AWS/IoT \
    --metric-name Connect.Success \
    --dimensions Name=Protocol,Value=MQTT \
    --start-time 2025-11-16T00:00:00Z \
    --end-time 2025-11-16T23:59:59Z \
    --period 3600 \
    --statistics Sum
```

### Logging

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Get status
status = orchestrator.get_status()
print(json.dumps(status, indent=2))
```

## Examples

See example scripts in `examples/`:
- `basic_connection.py` - Simple IoT connection
- `shadow_sync.py` - Device shadow synchronization
- `telemetry_demo.py` - Telemetry publishing
- `full_integration.py` - Complete integration example

## API Reference

See individual module documentation:
- [IoTConnection](./iot_connection.py)
- [DeviceShadowSync](./device_shadow_sync.py)
- [TelemetryPublisher](./telemetry_publisher.py)
- [DataSyncOrchestrator](./data_sync_orchestrator.py)

## License

MIT License - see [LICENSE](../../LICENSE) for details.

## Support

For issues or questions:
- GitHub Issues: https://github.com/Surya893/anc-with-ai/issues
- Documentation: `/cloud/iot/README.md`
- AWS IoT Docs: https://docs.aws.amazon.com/iot/
