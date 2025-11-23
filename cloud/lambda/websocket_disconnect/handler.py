"""
Lambda function: WebSocket Disconnect
Handles WebSocket connection termination and cleanup

CRITICAL FIXES:
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

# AWS clients with timeout configuration
dynamodb = boto3.resource('dynamodb', config=boto_config)
cloudwatch = boto3.client('cloudwatch', config=boto_config)
s3 = boto3.client('s3', config=boto_config)

# Environment variable validation
def get_required_env(key):
    """Get required environment variable or raise error"""
    value = os.environ.get(key)
    if not value:
        raise ValueError(f"Required environment variable {key} not set")
    return value

try:
    CONNECTIONS_TABLE = get_required_env('CONNECTIONS_TABLE')
    SESSIONS_TABLE = get_required_env('SESSIONS_TABLE')
    PROCESSED_AUDIO_BUCKET = os.environ.get('PROCESSED_AUDIO_BUCKET', '')
except ValueError as e:
    print(f"FATAL: {str(e)}")
    raise


def lambda_handler(event, context):
    """
    Handle WebSocket $disconnect route
    Clean up connection and session data
    """

    try:
        connection_id = event['requestContext']['connectionId']

        print(f"Disconnecting WebSocket: {connection_id}")

        # Get connection info
        connections_table = dynamodb.Table(CONNECTIONS_TABLE)
        connection_response = connections_table.get_item(
            Key={'connectionId': connection_id}
        )

        connection = connection_response.get('Item')
        if not connection:
            print(f"Connection {connection_id} not found in table")
            return {'statusCode': 200}

        user_id = connection.get('userId')

        # Find and cleanup active sessions
        sessions_table = dynamodb.Table(SESSIONS_TABLE)

        # Query sessions by connection ID
        session_response = sessions_table.query(
            IndexName='connectionId-index',
            KeyConditionExpression='connectionId = :conn_id',
            ExpressionAttributeValues={':conn_id': connection_id}
        )

        sessions = session_response.get('Items', [])

        for session in sessions:
            session_id = session['sessionId']
            print(f"Cleaning up session {session_id}")

            # Update session status
            sessions_table.update_item(
                Key={'sessionId': session_id},
                UpdateExpression='SET #status = :status, endTime = :end_time',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': 'disconnected',
                    ':end_time': datetime.utcnow().isoformat()
                }
            )

            # Optionally: Archive session data to S3
            if PROCESSED_AUDIO_BUCKET:
                archive_session_data(session_id, session)

        # Delete connection record
        connections_table.delete_item(
            Key={'connectionId': connection_id}
        )

        # Send metrics
        send_metrics({
            'ConnectionsTerminated': 1,
            'SessionsClosed': len(sessions)
        })

        print(f"Connection {connection_id} cleaned up successfully")

        return {'statusCode': 200}

    except Exception as e:
        print(f"Error in disconnect handler: {str(e)}")
        send_metrics({'ErrorCount': 1})
        return {'statusCode': 500, 'body': str(e)}


def archive_session_data(session_id, session):
    """Archive session data to S3"""
    try:
        # Prepare session summary
        summary = {
            'sessionId': session_id,
            'userId': session.get('userId'),
            'startTime': session.get('startTime'),
            'endTime': session.get('endTime'),
            'totalSamples': session.get('totalSamples', 0),
            'avgCancellationDb': session.get('avgCancellationDb', 0),
            'config': session.get('config', {})
        }

        # Upload to S3
        s3_key = f"sessions/{session_id}/summary.json"
        s3.put_object(
            Bucket=PROCESSED_AUDIO_BUCKET,
            Key=s3_key,
            Body=json.dumps(summary, indent=2),
            ContentType='application/json'
        )

        print(f"Archived session {session_id} to S3")

    except Exception as e:
        print(f"Error archiving session: {str(e)}")


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
            Namespace='ANC-Platform/WebSocket',
            MetricData=metric_data
        )
    except Exception as e:
        print(f"Error sending metrics: {str(e)}")
