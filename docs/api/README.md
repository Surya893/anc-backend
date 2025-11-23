# API Documentation

Complete API specification for the ANC Platform.

## OpenAPI Specification

**File:** `openapi.yaml`

The OpenAPI 3.0 specification defines all REST API endpoints, request/response schemas, and authentication methods for the ANC Platform.

### Viewing the API Documentation

**Option 1: Swagger UI (Online)**
```bash
# Upload openapi.yaml to https://editor.swagger.io/
```

**Option 2: Local Swagger UI (Docker)**
```bash
docker run -p 8080:8080 \
  -e SWAGGER_JSON=/openapi.yaml \
  -v $(pwd)/docs/api/openapi.yaml:/openapi.yaml \
  swaggerapi/swagger-ui
```

Then visit: http://localhost:8080

**Option 3: Redoc (Docker)**
```bash
docker run -p 8080:80 \
  -e SPEC_URL=openapi.yaml \
  -v $(pwd)/docs/api/openapi.yaml:/usr/share/nginx/html/openapi.yaml \
  redocly/redoc
```

---

## API Endpoints Overview

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login and get JWT token
- `POST /api/auth/refresh` - Refresh JWT token
- `POST /api/auth/logout` - Logout

### Audio Processing
- `POST /api/audio/process` - Process audio with ANC
- `POST /api/audio/upload` - Upload audio file
- `GET /api/audio/sessions` - List processing sessions
- `GET /api/audio/sessions/{id}` - Get session details
- `DELETE /api/audio/sessions/{id}` - Delete session

### Noise Classification
- `POST /api/classify` - Classify noise type
- `GET /api/classify/types` - List noise types
- `GET /api/classify/history` - Classification history

### WebSocket
- `WS /ws/audio` - Real-time audio streaming
- `WS /ws/metrics` - Real-time metrics updates

### System
- `GET /api/health` - Health check
- `GET /api/metrics` - System metrics
- `GET /api/status` - Platform status

---

## Authentication

The API uses JWT (JSON Web Tokens) for authentication.

### Getting a Token

```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "password"}'
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "expires_in": 3600
}
```

### Using the Token

```bash
curl -X GET http://localhost:5000/api/audio/sessions \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."
```

---

## Request/Response Examples

### Process Audio

**Request:**
```bash
curl -X POST http://localhost:5000/api/audio/process \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@audio.wav" \
  -F "filter_type=nlms" \
  -F "filter_length=256"
```

**Response:**
```json
{
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "completed",
  "processing_time_ms": 6.85,
  "cancellation_db": 23.7,
  "output_url": "/api/audio/download/123e4567-e89b-12d3-a456-426614174000"
}
```

### Classify Noise

**Request:**
```bash
curl -X POST http://localhost:5000/api/classify \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@noise.wav"
```

**Response:**
```json
{
  "classification": {
    "type": "traffic",
    "confidence": 0.89,
    "is_emergency": false
  },
  "probabilities": {
    "traffic": 0.89,
    "construction": 0.07,
    "conversation": 0.03,
    "emergency": 0.01
  }
}
```

---

## WebSocket Protocol

### Audio Streaming

**Connect:**
```javascript
const ws = new WebSocket('ws://localhost:5000/ws/audio?token=YOUR_TOKEN');
```

**Send Audio Chunk:**
```javascript
ws.send(JSON.stringify({
  "type": "audio_chunk",
  "data": base64AudioData,
  "sample_rate": 48000,
  "channels": 1
}));
```

**Receive Processed Audio:**
```javascript
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'processed_audio') {
    // data.audio contains base64 anti-noise signal
    playAudio(data.audio);
  }
};
```

---

## Rate Limiting

- **Authenticated requests:** 1000 requests/hour
- **Unauthenticated requests:** 100 requests/hour
- **WebSocket connections:** 10 concurrent per user

Rate limit headers:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1699999999
```

---

## Error Responses

### Standard Error Format

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Audio file format not supported",
    "details": {
      "supported_formats": ["wav", "mp3", "flac"],
      "received_format": "ogg"
    }
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_REQUEST` | 400 | Invalid request parameters |
| `UNAUTHORIZED` | 401 | Missing or invalid token |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |

---

## API Versioning

Current API version: `v1`

All endpoints are prefixed with `/api/` (version 1).

Future versions will use `/api/v2/`, `/api/v3/`, etc.

**Version Headers:**
```
API-Version: 1.0.0
```

---

## Testing the API

### Using cURL

```bash
# Health check
curl http://localhost:5000/api/health

# Get status (requires auth)
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:5000/api/status
```

### Using Python

```python
import requests

# Login
response = requests.post('http://localhost:5000/api/auth/login', json={
    'username': 'user',
    'password': 'password'
})
token = response.json()['access_token']

# Process audio
with open('audio.wav', 'rb') as f:
    response = requests.post(
        'http://localhost:5000/api/audio/process',
        headers={'Authorization': f'Bearer {token}'},
        files={'file': f},
        data={'filter_type': 'nlms', 'filter_length': 256}
    )
print(response.json())
```

### Using Postman

1. Import `openapi.yaml` into Postman
2. Configure environment variables:
   - `base_url`: `http://localhost:5000`
   - `token`: Your JWT token
3. Run the collection

---

## API Client Libraries

### Python

```python
from anc_client import ANCClient

client = ANCClient(
    base_url='http://localhost:5000',
    username='user',
    password='password'
)

# Process audio
result = client.process_audio('audio.wav', filter_type='nlms')
print(f"Cancellation: {result.cancellation_db} dB")
```

### JavaScript/TypeScript

```typescript
import { ANCClient } from '@anc-platform/client';

const client = new ANCClient({
  baseUrl: 'http://localhost:5000',
  username: 'user',
  password: 'password'
});

// Process audio
const result = await client.processAudio('audio.wav', {
  filterType: 'nlms',
  filterLength: 256
});
console.log(`Cancellation: ${result.cancellationDb} dB`);
```

---

## See Also

- [Backend Documentation](../BACKEND_README.md) - Backend architecture
- [WebSocket Guide](../guides/WEB_APP_GUIDE.md) - WebSocket implementation
- [Deployment Guide](../guides/DEPLOYMENT_GUIDE.md) - Production deployment
- [API Server Code](../../src/api/server.py) - Implementation

---

**API Version:** 1.0.0
**Last Updated:** 2025-11-16
**OpenAPI Spec:** [openapi.yaml](openapi.yaml)
