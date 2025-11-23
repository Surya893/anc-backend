"""
Lambda function: WebSocket Connect
Handles WebSocket connection establishment with SECURE JWT validation
"""

import json
import boto3
import os
from datetime import datetime
import uuid
from botocore.config import Config

# Boto3 timeout configuration (prevent hanging)
boto_config = Config(
    connect_timeout=2,
    read_timeout=10,
    retries={'max_attempts': 3, 'mode': 'standard'}
)

# AWS clients with timeout configuration
dynamodb = boto3.resource('dynamodb', config=boto_config)
cloudwatch = boto3.client('cloudwatch', config=boto_config)

# Environment variables with validation
def get_required_env(key):
    """Get required environment variable or raise error"""
    value = os.environ.get(key)
    if not value:
        raise ValueError(f"Required environment variable {key} not set")
    return value

CONNECTIONS_TABLE = get_required_env('CONNECTIONS_TABLE')
JWT_SECRET = get_required_env('JWT_SECRET')
JWT_ALGORITHM = os.environ.get('JWT_ALGORITHM', 'HS256')


def lambda_handler(event, context):
    """
    Handle WebSocket $connect route

    Event structure:
    {
        "requestContext": {
            "connectionId": "abc123",
            "routeKey": "$connect"
        },
        "queryStringParameters": {
            "token": "jwt-token"
        }
    }
    """

    try:
        # Extract connection ID with validation
        request_context = event.get('requestContext', {})
        connection_id = request_context.get('connectionId')

        if not connection_id:
            print("ERROR: Missing connectionId in request context")
            return {'statusCode': 400, 'body': 'Bad Request'}

        query_params = event.get('queryStringParameters', {}) or {}

        print(f"New WebSocket connection attempt: {connection_id}")

        # SECURITY: Validate JWT token with proper signature verification
        token = query_params.get('token')
        if not token:
            print("SECURITY: No authentication token provided")
            send_metrics({'UnauthorizedAttempts': 1})
            return {'statusCode': 401, 'body': 'Unauthorized: No token provided'}

        # Extract and verify user ID from token
        user_id = extract_and_verify_user_id(token)
        if not user_id:
            print("SECURITY: Invalid or expired token")
            send_metrics({'InvalidTokenAttempts': 1})
            return {'statusCode': 401, 'body': 'Unauthorized: Invalid token'}

        # Store connection in DynamoDB
        table = dynamodb.Table(CONNECTIONS_TABLE)

        try:
            table.put_item(
                Item={
                    'connectionId': connection_id,
                    'userId': user_id,
                    'connectedAt': datetime.utcnow().isoformat(),
                    'lastActivity': datetime.utcnow().isoformat(),
                    'status': 'connected',
                    'ttl': int(datetime.utcnow().timestamp()) + 86400  # 24 hour TTL
                }
            )
        except Exception as db_error:
            print(f"ERROR: Failed to store connection: {str(db_error)}")
            send_metrics({'DatabaseErrors': 1})
            return {'statusCode': 500, 'body': 'Internal server error'}

        # Send success metrics
        send_metrics({'ConnectionsEstablished': 1})

        print(f"SUCCESS: Connection {connection_id} established for user {user_id}")

        return {'statusCode': 200, 'body': 'Connected'}

    except ValueError as ve:
        # Configuration error (missing env vars)
        print(f"CONFIGURATION ERROR: {str(ve)}")
        send_metrics({'ConfigurationErrors': 1})
        return {'statusCode': 500, 'body': 'Internal server error'}

    except Exception as e:
        # Unexpected error
        print(f"UNEXPECTED ERROR in connect handler: {str(e)}")
        import traceback
        traceback.print_exc()
        send_metrics({'ErrorCount': 1})
        return {'statusCode': 500, 'body': 'Internal server error'}


def extract_and_verify_user_id(token):
    """
    Extract user ID from JWT token with SECURE signature verification

    SECURITY: This uses PyJWT library for proper HMAC signature verification.
    Tokens without valid signatures are rejected.
    """
    try:
        import jwt
        from jwt import InvalidTokenError

        # Verify JWT signature and decode payload
        try:
            payload = jwt.decode(
                token,
                JWT_SECRET,
                algorithms=[JWT_ALGORITHM],
                options={
                    'verify_signature': True,  # CRITICAL: Always verify signature
                    'verify_exp': True,        # Verify expiration
                    'verify_iat': True,        # Verify issued-at
                    'require_exp': True,       # Require expiration claim
                }
            )
        except jwt.ExpiredSignatureError:
            print("SECURITY: Token has expired")
            return None
        except jwt.InvalidSignatureError:
            print("SECURITY: Invalid token signature - possible forgery attempt")
            return None
        except jwt.DecodeError:
            print("SECURITY: Malformed token")
            return None
        except InvalidTokenError as e:
            print(f"SECURITY: Token validation failed: {str(e)}")
            return None

        # Extract user ID (support multiple claim formats)
        user_id = payload.get('user_id') or payload.get('sub') or payload.get('userId')

        if not user_id:
            print("SECURITY: Token missing user identifier")
            return None

        # Additional validation: Check token issuer if configured
        expected_issuer = os.environ.get('JWT_ISSUER')
        if expected_issuer and payload.get('iss') != expected_issuer:
            print(f"SECURITY: Invalid token issuer: {payload.get('iss')}")
            return None

        return str(user_id)

    except ImportError:
        # FALLBACK: If PyJWT not available, reject all tokens (fail-secure)
        print("CRITICAL: PyJWT library not available - rejecting all tokens")
        print("Install PyJWT: pip install PyJWT")
        return None

    except Exception as e:
        print(f"ERROR in token verification: {str(e)}")
        return None


def send_metrics(metrics):
    """Send custom metrics to CloudWatch with error handling"""
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
        # Don't fail the request if metrics fail
        print(f"WARNING: Error sending metrics: {str(e)}")
