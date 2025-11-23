"""
Lambda function: Audio Sender
Sends processed audio back to client via WebSocket

CRITICAL FIXES:
- Moved boto3 client initialization outside handler (cold start optimization)
- Added boto3 timeout configuration (prevents hanging)
- Added environment variable validation (fail-fast on misconfiguration)
"""

import json
import boto3
import os
from datetime import datetime
from botocore.config import Config

# Boto3 timeout configuration (prevents hanging)
boto_config = Config(
    connect_timeout=2,
    read_timeout=10,
    retries={'max_attempts': 3, 'mode': 'standard'}
)

# Environment variable validation
def get_required_env(key):
    """Get required environment variable or raise error"""
    value = os.environ.get(key)
    if not value:
        raise ValueError(f"Required environment variable {key} not set")
    return value

try:
    WEBSOCKET_ENDPOINT = get_required_env('WEBSOCKET_ENDPOINT')
    CONNECTIONS_TABLE = get_required_env('CONNECTIONS_TABLE')
except ValueError as e:
    print(f"FATAL: {str(e)}")
    raise

# AWS clients with timeout configuration (initialized ONCE at cold start)
cloudwatch = boto3.client('cloudwatch', config=boto_config)
dynamodb = boto3.resource('dynamodb', config=boto_config)

# API Gateway Management API client (initialized ONCE, not per request)
apigatewaymanagementapi = boto3.client(
    'apigatewaymanagementapi',
    endpoint_url=WEBSOCKET_ENDPOINT,
    config=boto_config
)


def lambda_handler(event, context):
    """
    Send processed audio to WebSocket client

    Event structure (SQS message):
    {
        "Records": [{
            "body": {
                "chunkId": "abc123",
                "sessionId": "session-uuid",
                "connectionId": "conn-xyz",
                "audioData": "base64-encoded-float32-array",
                "numSamples": 512,
                "metrics": {
                    "cancellationDb": 35.2,
                    "processingLatencyMs": 5.3
                },
                "timestamp": 1234567890
            }
        }]
    }
    """

    try:
        # Process each SQS record
        for record in event['Records']:
            message = json.loads(record['body'])

            chunk_id = message['chunkId']
            session_id = message['sessionId']
            connection_id = message['connectionId']
            audio_data = message['audioData']
            metrics = message['metrics']

            print(f"Sending chunk {chunk_id} to connection {connection_id}")

            # Prepare response
            response_data = {
                'type': 'processedChunk',
                'chunkId': chunk_id,
                'audioData': audio_data,
                'metrics': metrics,
                'serverTimestamp': datetime.utcnow().isoformat()
            }

            # Send to WebSocket
            try:
                apigatewaymanagementapi.post_to_connection(
                    ConnectionId=connection_id,
                    Data=json.dumps(response_data).encode('utf-8')
                )

                print(f"Successfully sent chunk {chunk_id}")

                # Send metrics
                total_latency = (datetime.utcnow().timestamp() - message['timestamp']) * 1000
                send_metrics({
                    'AudioChunksSent': 1,
                    'TotalLatency': total_latency,
                    'CancellationDb': metrics.get('cancellationDb', 0)
                })

            except apigatewaymanagementapi.exceptions.GoneException:
                # Connection no longer exists
                print(f"Connection {connection_id} gone, cleaning up")
                cleanup_connection(connection_id)

            except Exception as e:
                print(f"Error sending to connection {connection_id}: {str(e)}")
                send_metrics({'ErrorCount': 1})

        return {'statusCode': 200, 'body': 'Sent successfully'}

    except Exception as e:
        print(f"Error in audio sender: {str(e)}")
        send_metrics({'ErrorCount': 1})
        raise


def cleanup_connection(connection_id):
    """Remove stale connection from DynamoDB"""
    table = dynamodb.Table(CONNECTIONS_TABLE)

    try:
        table.delete_item(Key={'connectionId': connection_id})
        print(f"Cleaned up connection {connection_id}")
    except Exception as e:
        print(f"Error cleaning up connection: {str(e)}")


def send_metrics(metrics):
    """Send custom metrics to CloudWatch"""
    try:
        metric_data = []
        for metric_name, value in metrics.items():
            unit = 'Milliseconds' if 'Latency' in metric_name else 'None' if 'Db' in metric_name else 'Count'

            metric_data.append({
                'MetricName': metric_name,
                'Value': value,
                'Unit': unit,
                'Timestamp': datetime.utcnow()
            })

        cloudwatch.put_metric_data(
            Namespace='ANC-Platform/AudioSender',
            MetricData=metric_data
        )
    except Exception as e:
        print(f"Error sending metrics: {str(e)}")
