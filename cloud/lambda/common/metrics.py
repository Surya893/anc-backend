"""
CloudWatch metrics publishing utilities for Lambda functions
Handles metric aggregation and publishing with consistent naming
"""

import boto3
import logging
from datetime import datetime
from typing import Dict, List, Optional, Union

logger = logging.getLogger(__name__)

# CloudWatch client (reused across Lambda invocations)
_cloudwatch = None


def get_cloudwatch_client(region=None):
    """
    Get or create CloudWatch client
    
    Args:
        region: AWS region
        
    Returns:
        boto3.client: CloudWatch client
    """
    global _cloudwatch
    
    if _cloudwatch is None:
        _cloudwatch = boto3.client('cloudwatch', region_name=region)
    
    return _cloudwatch


def publish_metrics(
    metrics,
    namespace='ANC/Lambda',
    dimensions=None,
    timestamp=None
):
    """
    Publish metrics to CloudWatch
    
    Args:
        metrics: Dictionary of metric_name -> value
        namespace: CloudWatch namespace
        dimensions: Dictionary of dimension_name -> value
        timestamp: Optional timestamp (defaults to now)
        
    Returns:
        bool: Success/failure
    """
    if not metrics:
        return True
    
    if timestamp is None:
        timestamp = datetime.utcnow()
    
    try:
        cloudwatch = get_cloudwatch_client()
        metric_data = []
        
        for metric_name, value in metrics.items():
            metric_entry = {
                'MetricName': metric_name,
                'Value': value,
                'Timestamp': timestamp,
                'Unit': _get_metric_unit(metric_name)
            }
            
            if dimensions:
                metric_entry['Dimensions'] = [
                    {'Name': k, 'Value': str(v)} for k, v in dimensions.items()
                ]
            
            metric_data.append(metric_entry)
        
        # CloudWatch API accepts max 20 metrics per request
        for i in range(0, len(metric_data), 20):
            batch = metric_data[i:i+20]
            cloudwatch.put_metric_data(
                Namespace=namespace,
                MetricData=batch
            )
        
        logger.debug(f"Published {len(metric_data)} metrics to {namespace}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to publish metrics: {str(e)}")
        return False


def publish_metric(
    metric_name,
    value,
    namespace='ANC/Lambda',
    unit='None',
    dimensions=None,
    timestamp=None
):
    """
    Publish single metric to CloudWatch
    
    Args:
        metric_name: Name of metric
        value: Metric value
        namespace: CloudWatch namespace
        unit: CloudWatch unit (Count, Milliseconds, Seconds, None, etc.)
        dimensions: Dictionary of dimension_name -> value
        timestamp: Optional timestamp
        
    Returns:
        bool: Success/failure
    """
    if timestamp is None:
        timestamp = datetime.utcnow()
    
    try:
        cloudwatch = get_cloudwatch_client()
        
        metric_data = {
            'MetricName': metric_name,
            'Value': value,
            'Unit': unit,
            'Timestamp': timestamp
        }
        
        if dimensions:
            metric_data['Dimensions'] = [
                {'Name': k, 'Value': str(v)} for k, v in dimensions.items()
            ]
        
        cloudwatch.put_metric_data(
            Namespace=namespace,
            MetricData=[metric_data]
        )
        
        logger.debug(f"Published {metric_name} = {value} {unit}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to publish metric {metric_name}: {str(e)}")
        return False


def send_metrics(metrics, namespace='ANC/Lambda'):
    """
    Alias for publish_metrics for backwards compatibility
    
    Args:
        metrics: Dictionary of metric_name -> value
        namespace: CloudWatch namespace
        
    Returns:
        bool: Success/failure
    """
    return publish_metrics(metrics, namespace=namespace)


def publish_processing_metrics(
    session_id,
    noise_reduction_db=None,
    processing_time_ms=None,
    error_power=None,
    num_samples=None,
    dimensions=None
):
    """
    Publish audio processing metrics
    
    Args:
        session_id: Session ID for dimensions
        noise_reduction_db: Noise reduction in dB
        processing_time_ms: Processing time in milliseconds
        error_power: Error power
        num_samples: Number of samples processed
        dimensions: Additional dimensions
        
    Returns:
        bool: Success/failure
    """
    if dimensions is None:
        dimensions = {}
    
    dimensions['SessionId'] = session_id
    
    metrics = {}
    if noise_reduction_db is not None:
        metrics['NoiseReductionDB'] = noise_reduction_db
    if processing_time_ms is not None:
        metrics['ProcessingTimeMs'] = processing_time_ms
    if error_power is not None:
        metrics['ErrorPower'] = error_power
    if num_samples is not None:
        metrics['NumSamples'] = num_samples
    
    return publish_metrics(metrics, namespace='ANC/Processing', dimensions=dimensions)


def publish_latency_metrics(
    latency_ms,
    component,
    operation='process',
    dimensions=None
):
    """
    Publish latency metric
    
    Args:
        latency_ms: Latency in milliseconds
        component: Component name (e.g., 'AudioReceiver', 'Processor')
        operation: Operation name
        dimensions: Additional dimensions
        
    Returns:
        bool: Success/failure
    """
    if dimensions is None:
        dimensions = {}
    
    dimensions['Component'] = component
    dimensions['Operation'] = operation
    
    return publish_metric(
        'Latency',
        latency_ms,
        namespace='ANC/Performance',
        unit='Milliseconds',
        dimensions=dimensions
    )


def publish_error_metric(error_type, component, dimensions=None):
    """
    Publish error counter metric
    
    Args:
        error_type: Type of error (e.g., 'ValidationError', 'TimeoutError')
        component: Component where error occurred
        dimensions: Additional dimensions
        
    Returns:
        bool: Success/failure
    """
    if dimensions is None:
        dimensions = {}
    
    dimensions['ErrorType'] = error_type
    dimensions['Component'] = component
    
    return publish_metric(
        'ErrorCount',
        1,
        namespace='ANC/Errors',
        unit='Count',
        dimensions=dimensions
    )


def _get_metric_unit(metric_name):
    """
    Infer CloudWatch unit from metric name
    
    Args:
        metric_name: Name of the metric
        
    Returns:
        str: CloudWatch unit
    """
    if 'Latency' in metric_name or 'Time' in metric_name:
        return 'Milliseconds'
    elif 'Count' in metric_name or 'Processed' in metric_name or 'Received' in metric_name:
        return 'Count'
    elif 'DB' in metric_name or 'Power' in metric_name:
        return 'None'
    else:
        return 'None'
