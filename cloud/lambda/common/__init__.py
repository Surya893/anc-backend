"""
ANC Platform Lambda Common Package
Shared utilities for all Lambda functions including:
- Redis client factory
- Base64 encoding/decoding
- CloudWatch metrics publishing
- Boto3 configuration
"""

from .redis_client import get_redis_client, redis_cache_get, redis_cache_set
from .encoding import encode_audio, decode_audio
from .metrics import publish_metrics, send_metrics
from .boto_config import get_boto_config, get_aws_clients

__all__ = [
    'get_redis_client',
    'redis_cache_get',
    'redis_cache_set',
    'encode_audio',
    'decode_audio',
    'publish_metrics',
    'send_metrics',
    'get_boto_config',
    'get_aws_clients',
]
