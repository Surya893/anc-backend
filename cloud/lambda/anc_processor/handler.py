"""
Lambda function: ANC Processor
Applies NLMS adaptive filtering and phase inversion to audio chunks
This is the core ANC algorithm running in the cloud

CRITICAL FIXES:
- Added boto3 timeout configuration (prevents hanging)
- Added environment variable validation (fail-fast on misconfiguration)
- Added Redis connection error handling
"""

import json
import base64
import boto3
import os
import numpy as np
from datetime import datetime
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

# Environment variable validation
def get_required_env(key):
    """Get required environment variable or raise error"""
    value = os.environ.get(key)
    if not value:
        raise ValueError(f"Required environment variable {key} not set")
    return value

try:
    OUTPUT_QUEUE_URL = get_required_env('OUTPUT_QUEUE_URL')
    REDIS_ENDPOINT = get_required_env('REDIS_ENDPOINT')
    SESSIONS_TABLE = get_required_env('SESSIONS_TABLE')
except ValueError as e:
    print(f"FATAL: {str(e)}")
    raise

# Redis client for caching filter coefficients
try:
    import redis
    redis_client = redis.Redis.from_url(
        f"redis://{REDIS_ENDPOINT}",
        socket_connect_timeout=2,
        socket_timeout=5,
        decode_responses=False
    )
    REDIS_AVAILABLE = True
except Exception as e:
    print(f"WARNING: Redis not available: {str(e)}")
    redis_client = None
    REDIS_AVAILABLE = False

# Constants
SAMPLE_RATE = 48000
FILTER_LENGTH = 512  # NLMS filter taps


class NLMSFilter:
    """Normalized Least Mean Squares adaptive filter"""

    def __init__(self, filter_length=FILTER_LENGTH, mu=0.001):
        self.length = filter_length
        self.mu = mu
        self.epsilon = 1e-6
        self.weights = np.zeros(filter_length, dtype=np.float32)
        self.x_buffer = np.zeros(filter_length, dtype=np.float32)
        self.index = 0

    def process(self, reference, desired):
        """
        Process audio samples with NLMS algorithm

        Args:
            reference: Reference signal (input noise)
            desired: Desired signal (what we want to cancel)

        Returns:
            output: Anti-noise signal
            error: Residual error signal
        """
        num_samples = len(reference)
        output = np.zeros(num_samples, dtype=np.float32)
        error = np.zeros(num_samples, dtype=np.float32)

        for n in range(num_samples):
            # Update input buffer (circular)
            self.x_buffer[self.index] = reference[n]

            # Compute filter output (FIR)
            y = 0.0
            for i in range(self.length):
                idx = (self.index + i) % self.length
                y += self.weights[i] * self.x_buffer[idx]

            output[n] = y

            # Calculate error
            error[n] = desired[n] - y

            # Calculate input power (for normalization)
            power = self.epsilon
            for i in range(self.length):
                power += self.x_buffer[i] ** 2

            # Normalized step size
            mu_norm = self.mu / power

            # Update filter weights (LMS adaptation)
            for i in range(self.length):
                idx = (self.index + i) % self.length
                self.weights[i] += mu_norm * error[n] * self.x_buffer[idx]

            # Update circular buffer index
            self.index = (self.index + 1) % self.length

        return output, error

    def to_dict(self):
        """Serialize filter state"""
        return {
            'weights': self.weights.tobytes(),
            'x_buffer': self.x_buffer.tobytes(),
            'index': self.index
        }

    @classmethod
    def from_dict(cls, data, mu=0.001):
        """Deserialize filter state"""
        filter_obj = cls(mu=mu)
        filter_obj.weights = np.frombuffer(data['weights'], dtype=np.float32)
        filter_obj.x_buffer = np.frombuffer(data['x_buffer'], dtype=np.float32)
        filter_obj.index = data['index']
        return filter_obj


def lambda_handler(event, context):
    """
    Process audio chunks with ANC algorithm

    Event structure (SQS message):
    {
        "Records": [{
            "body": {
                "chunkId": "abc123",
                "sessionId": "session-uuid",
                "connectionId": "conn-xyz",
                "audioData": "base64-encoded-float32-array",
                "sampleRate": 48000,
                "numSamples": 512,
                "timestamp": 1234567890,
                "config": {
                    "ancEnabled": true,
                    "ancIntensity": 1.0,
                    "algorithm": "nlms",
                    "noiseType": "traffic"
                }
            }
        }]
    }
    """

    start_time = datetime.utcnow()

    try:
        # Process each SQS record
        for record in event['Records']:
            message = json.loads(record['body'])

            chunk_id = message['chunkId']
            session_id = message['sessionId']
            connection_id = message['connectionId']
            audio_data_b64 = message['audioData']
            config = message['config']

            print(f"Processing chunk {chunk_id} for session {session_id}")

            # Decode audio data
            audio_bytes = base64.b64decode(audio_data_b64)
            audio_input = np.frombuffer(audio_bytes, dtype=np.float32)

            # Load or create NLMS filter for this session
            nlms_filter = load_filter(session_id, config)

            # Apply ANC processing
            if config['ancEnabled']:
                # Generate reference signal (for this demo, we use the input as reference)
                # In production, this would come from a feedforward microphone
                reference = audio_input.copy()

                # Desired signal (what we want at the output - silence in this case)
                desired = np.zeros_like(audio_input)

                # Apply NLMS filter to generate anti-noise
                anti_noise, residual_error = nlms_filter.process(reference, desired)

                # Apply intensity scaling
                anti_noise *= config['ancIntensity']

                # Phase inversion (anti-noise is already inverted by the algorithm)
                # Mix with original for partial cancellation
                processed_audio = audio_input + anti_noise

                # Calculate cancellation in dB
                input_power = np.mean(audio_input ** 2)
                output_power = np.mean(processed_audio ** 2)

                if output_power > 1e-10 and input_power > 1e-10:
                    cancellation_db = 10 * np.log10(input_power / output_power)
                else:
                    cancellation_db = 0.0

            else:
                # Passthrough mode - no ANC
                processed_audio = audio_input
                cancellation_db = 0.0

            # Save filter state
            save_filter(session_id, nlms_filter)

            # Update metrics
            update_processing_metrics(session_id, cancellation_db)

            # Encode processed audio
            processed_b64 = base64.b64encode(processed_audio.tobytes()).decode('utf-8')

            # Prepare output message
            output_message = {
                'chunkId': chunk_id,
                'sessionId': session_id,
                'connectionId': connection_id,
                'audioData': processed_b64,
                'numSamples': len(processed_audio),
                'metrics': {
                    'cancellationDb': float(cancellation_db),
                    'processingLatencyMs': (datetime.utcnow() - start_time).total_seconds() * 1000,
                    'inputRms': float(np.sqrt(np.mean(audio_input ** 2))),
                    'outputRms': float(np.sqrt(np.mean(processed_audio ** 2)))
                },
                'timestamp': message['timestamp']
            }

            # Send to output queue
            sqs.send_message(
                QueueUrl=OUTPUT_QUEUE_URL,
                MessageBody=json.dumps(output_message)
            )

            # Send CloudWatch metrics
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            send_metrics({
                'AudioChunksProcessed': 1,
                'ProcessingLatency': processing_time,
                'CancellationDb': cancellation_db
            })

            print(f"Processed chunk {chunk_id}: {cancellation_db:.1f} dB cancellation in {processing_time:.1f}ms")

        return {'statusCode': 200, 'body': 'Processing complete'}

    except Exception as e:
        print(f"Error processing audio: {str(e)}")
        send_metrics({'ErrorCount': 1})
        raise


def load_filter(session_id, config):
    """Load NLMS filter from Redis cache or create new"""
    if not REDIS_AVAILABLE:
        # Redis not available, always create new filter
        print(f"Redis unavailable, creating new filter for session {session_id}")
        return NLMSFilter(mu=0.001)

    try:
        # Try to load from cache
        cache_key = f"filter:{session_id}"
        cached_data = redis_client.hgetall(cache_key)

        if cached_data:
            # Deserialize filter
            filter_data = {
                'weights': cached_data[b'weights'],
                'x_buffer': cached_data[b'x_buffer'],
                'index': int(cached_data[b'index'])
            }
            nlms_filter = NLMSFilter.from_dict(filter_data, mu=0.001)
            print(f"Loaded filter from cache for session {session_id}")
        else:
            # Create new filter
            nlms_filter = NLMSFilter(mu=0.001)
            print(f"Created new filter for session {session_id}")

        return nlms_filter

    except Exception as e:
        print(f"Error loading filter: {str(e)}, creating new")
        return NLMSFilter(mu=0.001)


def save_filter(session_id, nlms_filter):
    """Save NLMS filter to Redis cache"""
    if not REDIS_AVAILABLE:
        # Redis not available, skip caching
        return

    try:
        cache_key = f"filter:{session_id}"
        filter_data = nlms_filter.to_dict()

        redis_client.hset(cache_key, mapping={
            'weights': filter_data['weights'],
            'x_buffer': filter_data['x_buffer'],
            'index': str(filter_data['index'])
        })

        # Set expiration (1 hour)
        redis_client.expire(cache_key, 3600)

    except Exception as e:
        print(f"Error saving filter: {str(e)}")


def update_processing_metrics(session_id, cancellation_db):
    """Update processing metrics in DynamoDB"""
    table = dynamodb.Table(SESSIONS_TABLE)

    try:
        table.update_item(
            Key={'sessionId': session_id},
            UpdateExpression='SET avgCancellationDb = :cancellation, lastProcessedAt = :timestamp',
            ExpressionAttributeValues={
                ':cancellation': float(cancellation_db),
                ':timestamp': datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        print(f"Error updating metrics: {str(e)}")


def send_metrics(metrics):
    """Send custom metrics to CloudWatch"""
    try:
        metric_data = []
        for metric_name, value in metrics.items():
            metric_data.append({
                'MetricName': metric_name,
                'Value': value,
                'Unit': 'None' if 'Db' in metric_name else 'Milliseconds' if 'Latency' in metric_name else 'Count',
                'Timestamp': datetime.utcnow()
            })

        cloudwatch.put_metric_data(
            Namespace='ANC-Platform/Processor',
            MetricData=metric_data
        )
    except Exception as e:
        print(f"Error sending metrics: {str(e)}")
