"""
Redis client factory and caching utilities for Lambda functions
Handles connection management, authentication, and error handling
"""

import redis
import json
import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Global Redis client (reused across Lambda invocations)
_redis_client = None


def get_redis_client(
    endpoint=None,
    port=6379,
    auth_token=None,
    socket_connect_timeout=2,
    socket_timeout=5,
    decode_responses=False
):
    """
    Get or create Redis client with connection pooling
    
    Args:
        endpoint: Redis endpoint hostname
        port: Redis port
        auth_token: Authentication token/password
        socket_connect_timeout: Connection timeout in seconds
        socket_timeout: Read/write timeout in seconds
        decode_responses: Whether to decode responses as strings
        
    Returns:
        redis.Redis: Configured Redis client or None if unavailable
    """
    global _redis_client
    
    if _redis_client is not None:
        return _redis_client
    
    try:
        if endpoint is None:
            endpoint = os.environ.get('REDIS_ENDPOINT')
        
        if not endpoint:
            logger.warning("REDIS_ENDPOINT not configured, Redis disabled")
            return None
        
        port = int(port or os.environ.get('REDIS_PORT', '6379'))
        
        if auth_token is None:
            auth_token = os.environ.get('REDIS_PASSWORD')
        
        _redis_client = redis.Redis(
            host=endpoint,
            port=port,
            password=auth_token,
            decode_responses=decode_responses,
            socket_connect_timeout=socket_connect_timeout,
            socket_timeout=socket_timeout,
            retry_on_timeout=True,
            health_check_interval=30
        )
        
        # Test connection
        _redis_client.ping()
        logger.info(f"Redis client connected to {endpoint}:{port}")
        return _redis_client
        
    except Exception as e:
        logger.warning(f"Failed to create Redis client: {str(e)}")
        return None


def redis_cache_get(key, redis_client=None):
    """
    Get value from Redis cache
    
    Args:
        key: Cache key
        redis_client: Redis client instance (creates new if None)
        
    Returns:
        Deserialized value or None if not found
    """
    if redis_client is None:
        redis_client = get_redis_client()
    
    if redis_client is None:
        return None
    
    try:
        data = redis_client.get(key)
        if data:
            return json.loads(data) if isinstance(data, bytes) else json.loads(data)
        return None
    except Exception as e:
        logger.warning(f"Redis GET failed for {key}: {str(e)}")
        return None


def redis_cache_set(key, value, ttl=3600, redis_client=None):
    """
    Set value in Redis cache with TTL
    
    Args:
        key: Cache key
        value: Value to cache (will be JSON serialized)
        ttl: Time to live in seconds
        redis_client: Redis client instance (creates new if None)
        
    Returns:
        bool: Success/failure
    """
    if redis_client is None:
        redis_client = get_redis_client()
    
    if redis_client is None:
        return False
    
    try:
        data = json.dumps(value) if not isinstance(value, (str, bytes)) else value
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        redis_client.setex(key, ttl, data)
        logger.debug(f"Redis SET {key} with TTL {ttl}s")
        return True
    except Exception as e:
        logger.warning(f"Redis SET failed for {key}: {str(e)}")
        return False


def redis_cache_delete(key, redis_client=None):
    """
    Delete value from Redis cache
    
    Args:
        key: Cache key
        redis_client: Redis client instance
        
    Returns:
        bool: Success/failure
    """
    if redis_client is None:
        redis_client = get_redis_client()
    
    if redis_client is None:
        return False
    
    try:
        redis_client.delete(key)
        logger.debug(f"Redis DELETE {key}")
        return True
    except Exception as e:
        logger.warning(f"Redis DELETE failed for {key}: {str(e)}")
        return False


def redis_cache_hgetall(key, redis_client=None):
    """
    Get all fields from Redis hash
    
    Args:
        key: Cache key
        redis_client: Redis client instance
        
    Returns:
        dict: Hash fields or empty dict
    """
    if redis_client is None:
        redis_client = get_redis_client()
    
    if redis_client is None:
        return {}
    
    try:
        return redis_client.hgetall(key) or {}
    except Exception as e:
        logger.warning(f"Redis HGETALL failed for {key}: {str(e)}")
        return {}


def redis_cache_hset(key, mapping, ttl=3600, redis_client=None):
    """
    Set multiple hash fields in Redis
    
    Args:
        key: Cache key
        mapping: Dictionary of field:value pairs
        ttl: Time to live in seconds
        redis_client: Redis client instance
        
    Returns:
        bool: Success/failure
    """
    if redis_client is None:
        redis_client = get_redis_client()
    
    if redis_client is None:
        return False
    
    try:
        redis_client.hset(key, mapping=mapping)
        if ttl:
            redis_client.expire(key, ttl)
        logger.debug(f"Redis HSET {key} with {len(mapping)} fields")
        return True
    except Exception as e:
        logger.warning(f"Redis HSET failed for {key}: {str(e)}")
        return False
