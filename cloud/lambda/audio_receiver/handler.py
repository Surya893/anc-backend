"""
Lambda function: Audio Receiver
Receives incoming audio chunks via WebSocket, validates, and queues for processing

SECURITY & RELIABILITY FIXES:
- Environment variable validation
- Boto3 timeout configuration
- Input validation and schema checking
- Error handling for all external calls
"""

import json
import base64
import boto3
import os
import numpy as np
from datetime import datetime
import hashlib
import traceback
from botocore.config import Config

# Boto3 timeout configuration (prevents hanging)
boto_config = Config(
    connect_timeout=2,
    read_timeout=10,
    retries={'max_attempts': 3, 'mode': 'standard'}
)

# AWS clients with timeout configuration
sqs = boto3.client('sqs', config=boto_config)
dynamodb = boto3.resource('dynamodb', config=boto_config)
cloudwatch = boto3.client('cloudwatch', config=boto_config)

# Environment variables with validation
def get_required_env(key):
    """Get required environment variable or raise error"""
    value = os.environ.get(key)
    if not value:
        raise ValueError(f"Required environment variable {key} not set")
    return value

try:
    AUDIO_QUEUE_URL = get_required_env('AUDIO_QUEUE_URL')
    SESSIONS_TABLE = get_required_env('SESSIONS_TABLE')
    CONNECTIONS_TABLE = get_required_env('CONNECTIONS_TABLE')
except ValueError as e:
    print(f"FATAL: {str(e)}")
    # Will fail on first invocation if env vars not set
    raise

# Constants
SAMPLE_RATE = 48000
MAX_CHUNK_SIZE = 4096  # samples
MAX_AUDIO_SIZE_BYTES = MAX_CHUNK_SIZE * 4  # 4 bytes per float32

def lambda_handler(event, context):
    """
    Handle incoming audio chunks from WebSocket clients

    Event structure:
    {
        "requestContext": {
            "connectionId": "abc123",
            "routeKey": "audioChunk"
        },
        "body": {
            "sessionId": "session-uuid",
            "audioData": "base64-encoded-float32-array",
            "sampleRate": 48000,
            "timestamp": 1234567890
        }
    }
    """

    try:
        # INPUT VALIDATION: Parse and validate event structure
        request_context = event.get('requestContext', {})
        connection_id = request_context.get('connectionId')

        if not connection_id:
            print("ERROR: Missing connectionId in requestContext")
            return error_response(400, 'Bad Request: Missing connectionId')

        # Parse body with error handling
        try:
            if isinstance(event.get('body'), str):
                body = json.loads(event['body'])
            else:
                body = event.get('body', {})
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON in body: {str(e)}")
            return error_response(400, 'Bad Request: Invalid JSON')

        # INPUT VALIDATION: Required fields
        if not isinstance(body, dict):
            print(f"ERROR: Body is not a dict: {type(body)}")
            return error_response(400, 'Bad Request: Body must be JSON object')

        # Validate required fields exist
        required_fields = ['session_id', 'audio_data']
        missing_fields = [f for f in required_fields if f not in body]
        if missing_fields:
            print(f"ERROR: Missing required fields: {missing_fields}")
            return error_response(400, f'Bad Request: Missing fields: {", ".join(missing_fields)}')

        # Extract and validate fields
        session_id = body['session_id']
        audio_data_b64 = body['audio_data']

        # Type validation
        if not isinstance(session_id, str) or not session_id.strip():
            print(f"ERROR: Invalid session_id type or empty")
            return error_response(400, 'Bad Request: session_id must be non-empty string')

        if not isinstance(audio_data_b64, str):
            print(f"ERROR: Invalid audio_data type: {type(audio_data_b64)}")
            return error_response(400, 'Bad Request: audio_data must be string')

        # Optional fields with validation
        sample_rate = body.get('sample_rate', SAMPLE_RATE)
        if not isinstance(sample_rate, (int, float)) or sample_rate <= 0:
            print(f"ERROR: Invalid sample_rate: {sample_rate}")
            return error_response(400, 'Bad Request: sample_rate must be positive number')

        timestamp = body.get('timestamp', datetime.utcnow().timestamp())
        if not isinstance(timestamp, (int, float)):
            print(f"ERROR: Invalid timestamp type: {type(timestamp)}")
            return error_response(400, 'Bad Request: timestamp must be number')

        # Validate session
        session = get_session(session_id)
        if not session:
            return error_response(404, 'Session not found')

        # Validate connection matches session
        if session['connectionId'] != connection_id:
            return error_response(403, 'Connection ID mismatch')

        # Decode audio data
        try:
            audio_bytes = base64.b64decode(audio_data_b64)
            audio_array = np.frombuffer(audio_bytes, dtype=np.float32)
        except Exception as e:
            return error_response(400, f'Invalid audio data: {str(e)}')

        # Validate audio chunk
        if len(audio_array) > MAX_CHUNK_SIZE:
            return error_response(400, f'Chunk too large: {len(audio_array)} samples (max: {MAX_CHUNK_SIZE})')

        if sample_rate != SAMPLE_RATE:
            return error_response(400, f'Invalid sample rate: {sample_rate} (expected: {SAMPLE_RATE})')

        # Generate chunk ID
        chunk_id = generate_chunk_id(session_id, timestamp)

        # Prepare message for SQS
        message = {
            'chunkId': chunk_id,
            'sessionId': session_id,
            'connectionId': connection_id,
            'audioData': audio_data_b64,  # Keep as base64 for SQS
            'sampleRate': sample_rate,
            'numSamples': len(audio_array),
            'timestamp': timestamp,
            'receivedAt': datetime.utcnow().isoformat(),
            'config': {
                'ancEnabled': session['config'].get('anc_enabled', True),
                'ancIntensity': session['config'].get('anc_intensity', 1.0),
                'algorithm': session['config'].get('algorithm', 'nlms'),
                'noiseType': session.get('noiseType', 'unknown')
            }
        }

        # Send to SQS for processing
        sqs_response = sqs.send_message(
            QueueUrl=AUDIO_QUEUE_URL,
            MessageBody=json.dumps(message),
            MessageAttributes={
                'sessionId': {
                    'StringValue': session_id,
                    'DataType': 'String'
                },
                'priority': {
                    'StringValue': 'high',  # Real-time processing
                    'DataType': 'String'
                }
            }
        )

        # Update session metrics
        update_session_metrics(session_id, len(audio_array))

        # Send CloudWatch metrics
        send_metrics({
            'AudioChunksReceived': 1,
            'AudioSamplesReceived': len(audio_array),
            'ReceiveLatency': (datetime.utcnow().timestamp() - timestamp) * 1000  # ms
        })

        # Return acknowledgment
        return {
            'statusCode': 200,
            'body': json.dumps({
                'status': 'received',
                'chunkId': chunk_id,
                'queuedAt': sqs_response['MessageId'],
                'numSamples': len(audio_array)
            })
        }

    except Exception as e:
        print(f"Error processing audio chunk: {str(e)}")
        send_metrics({'ErrorCount': 1})
        return error_response(500, f'Internal error: {str(e)}')


def get_session(session_id):
    """Retrieve session from DynamoDB"""
    table = dynamodb.Table(SESSIONS_TABLE)

    try:
        response = table.get_item(Key={'sessionId': session_id})
        return response.get('Item')
    except Exception as e:
        print(f"Error retrieving session: {str(e)}")
        return None


def update_session_metrics(session_id, num_samples):
    """Update session metrics in DynamoDB"""
    table = dynamodb.Table(SESSIONS_TABLE)

    try:
        table.update_item(
            Key={'sessionId': session_id},
            UpdateExpression='ADD totalSamples :samples SET lastActivityAt = :timestamp',
            ExpressionAttributeValues={
                ':samples': num_samples,
                ':timestamp': datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        print(f"Error updating session metrics: {str(e)}")


def generate_chunk_id(session_id, timestamp):
    """Generate unique chunk ID"""
    data = f"{session_id}:{timestamp}".encode('utf-8')
    return hashlib.sha256(data).hexdigest()[:16]


def send_metrics(metrics):
    """Send custom metrics to CloudWatch"""
    try:
        metric_data = []
        for metric_name, value in metrics.items():
            metric_data.append({
                'MetricName': metric_name,
                'Value': value,
                'Unit': 'Count',
                'Timestamp': datetime.utcnow()
            })

        cloudwatch.put_metric_data(
            Namespace='ANC-Platform/AudioReceiver',
            MetricData=metric_data
        )
    except Exception as e:
        print(f"Error sending metrics: {str(e)}")


def error_response(status_code, message):
    """Return error response"""
    return {
        'statusCode': status_code,
        'body': json.dumps({
            'error': message
        })
    }
