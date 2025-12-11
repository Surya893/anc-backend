"""
Boto3 configuration and client factory for Lambda functions
Provides timeout configuration and client initialization with error handling
"""

import boto3
from botocore.config import Config
import os


def get_boto_config(connect_timeout=2, read_timeout=10, max_retries=3):
    """
    Get Boto3 configuration with timeout and retry settings
    
    Args:
        connect_timeout: Connection timeout in seconds
        read_timeout: Read timeout in seconds
        max_retries: Maximum retry attempts
        
    Returns:
        botocore.config.Config: Configured Boto3 Config object
    """
    return Config(
        connect_timeout=connect_timeout,
        read_timeout=read_timeout,
        retries={'max_attempts': max_retries, 'mode': 'standard'}
    )


def get_aws_clients(client_names, region=None, config=None):
    """
    Factory function to create multiple AWS clients with standard configuration
    
    Args:
        client_names: List of client names (e.g., ['sqs', 'dynamodb', 'cloudwatch'])
        region: AWS region (defaults to environment or default)
        config: botocore.config.Config object (defaults to get_boto_config())
        
    Returns:
        dict: Dictionary mapping client names to boto3 client objects
    """
    if config is None:
        config = get_boto_config()
    
    clients = {}
    for client_name in client_names:
        if region:
            clients[client_name] = boto3.client(client_name, region_name=region, config=config)
        else:
            clients[client_name] = boto3.client(client_name, config=config)
    
    return clients


def get_required_env(key, default=None):
    """
    Get required environment variable or raise error
    
    Args:
        key: Environment variable name
        default: Default value if not required
        
    Returns:
        str: Environment variable value
        
    Raises:
        ValueError: If required env var not set
    """
    value = os.environ.get(key, default)
    if value is None:
        raise ValueError(f"Required environment variable {key} not set")
    return value
