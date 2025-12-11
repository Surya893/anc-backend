"""
Analytics and reporting tasks for Celery
Handles session analysis and report generation
"""

import logging
import sys
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, timedelta

# Ensure src is in path for imports
src_path = Path(__file__).parent.parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from celery_app import celery_app
from models import db, AudioSession, NoiseDetection, ProcessingMetric, APIRequest

from .utils import task_logger, handle_task_error

logger = logging.getLogger(__name__)


@celery_app.task(name='tasks.analyze_session_data')
@task_logger
def analyze_session_data(session_id: str) -> Dict[str, Any]:
    """
    Analyze collected session data for insights
    Provides comprehensive noise detection and performance analysis

    Args:
        session_id: Session to analyze

    Returns:
        dict: Analysis results with noise types and performance metrics

    Raises:
        ValueError: If session not found
    """
    try:
        logger.info(f"Analyzing session: {session_id}")

        # Query session data
        session = AudioSession.query.filter_by(id=session_id).first()
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Get noise detections
        detections = NoiseDetection.query.filter_by(session_id=session_id).all()

        # Get metrics
        metrics = ProcessingMetric.query.filter_by(session_id=session_id).all()

        # Analyze noise types
        noise_types = {}
        for detection in detections:
            noise_type = detection.noise_type
            if noise_type not in noise_types:
                noise_types[noise_type] = {
                    'count': 0,
                    'avg_confidence': 0.0,
                    'avg_intensity': 0.0
                }

            noise_types[noise_type]['count'] += 1
            noise_types[noise_type]['avg_confidence'] += detection.confidence
            noise_types[noise_type]['avg_intensity'] += detection.intensity_db

        # Calculate averages
        for noise_type in noise_types:
            count = noise_types[noise_type]['count']
            noise_types[noise_type]['avg_confidence'] = (
                noise_types[noise_type]['avg_confidence'] / count if count > 0 else 0.0
            )
            noise_types[noise_type]['avg_intensity'] = (
                noise_types[noise_type]['avg_intensity'] / count if count > 0 else 0.0
            )

        # Analyze performance metrics
        if metrics:
            avg_latency = sum(m.latency_ms for m in metrics) / len(metrics)
            avg_cancellation = sum(m.cancellation_db for m in metrics) / len(metrics)
            max_latency = max(m.latency_ms for m in metrics)
            min_latency = min(m.latency_ms for m in metrics)
        else:
            avg_latency = avg_cancellation = max_latency = min_latency = 0.0

        # Calculate session duration
        if session.ended_at:
            duration = (session.ended_at - session.started_at).total_seconds()
        else:
            duration = 0.0

        analysis = {
            'session_id': session_id,
            'duration_seconds': duration,
            'total_detections': len(detections),
            'noise_types': noise_types,
            'performance': {
                'avg_latency_ms': avg_latency,
                'max_latency_ms': max_latency,
                'min_latency_ms': min_latency,
                'avg_cancellation_db': avg_cancellation
            },
            'metrics_count': len(metrics),
            'analysis_timestamp': datetime.utcnow().isoformat()
        }

        logger.info(
            f"Session analysis completed",
            extra={
                'session_id': session_id,
                'total_detections': len(detections),
                'num_noise_types': len(noise_types)
            }
        )

        return analysis

    except ValueError as e:
        logger.error(f"Session analysis error: {e}")
        raise
    except Exception as e:
        handle_task_error('analyze_session_data', e)
        raise


@celery_app.task(name='tasks.generate_daily_report')
@task_logger
def generate_daily_report(days_back: int = 1) -> Dict[str, Any]:
    """
    Generate daily usage and performance report
    Provides comprehensive statistics for the reporting period

    Args:
        days_back: Number of days back to generate report for (default: yesterday)

    Returns:
        dict: Daily report data with sessions, detections, and API metrics

    Raises:
        Exception: If report generation fails
    """
    try:
        logger.info(f"Generating daily report for {days_back} day(s) back")

        # Date range
        today = datetime.utcnow().date()
        report_date = today - timedelta(days=days_back)
        start_time = datetime.combine(report_date, datetime.min.time())
        end_time = datetime.combine(today, datetime.min.time())

        # Query sessions
        sessions = AudioSession.query.filter(
            AudioSession.created_at >= start_time,
            AudioSession.created_at < end_time
        ).all()

        # Query detections
        detections = NoiseDetection.query.filter(
            NoiseDetection.detected_at >= start_time,
            NoiseDetection.detected_at < end_time
        ).all()

        # Query API requests
        api_requests = APIRequest.query.filter(
            APIRequest.created_at >= start_time,
            APIRequest.created_at < end_time
        ).all()

        # Calculate metrics
        total_sessions = len(sessions)
        total_detections = len(detections)
        total_api_requests = len(api_requests)

        avg_cancellation = (
            sum(s.average_cancellation_db for s in sessions) / total_sessions
            if total_sessions > 0 else 0.0
        )

        avg_latency = (
            sum(s.average_latency_ms for s in sessions) / total_sessions
            if total_sessions > 0 else 0.0
        )

        # Emergency detections
        emergency_count = sum(1 for d in detections if d.is_emergency)

        # API response times
        avg_api_response = (
            sum(r.response_time_ms for r in api_requests) / total_api_requests
            if total_api_requests > 0 else 0.0
        )

        # Noise type distribution
        noise_distribution = {}
        for detection in detections:
            noise_type = detection.noise_type
            noise_distribution[noise_type] = noise_distribution.get(noise_type, 0) + 1

        report = {
            'date': report_date.isoformat(),
            'report_period_start': start_time.isoformat(),
            'report_period_end': end_time.isoformat(),
            'sessions': {
                'total': total_sessions,
                'avg_cancellation_db': float(avg_cancellation),
                'avg_latency_ms': float(avg_latency)
            },
            'detections': {
                'total': total_detections,
                'emergency': emergency_count,
                'by_type': noise_distribution
            },
            'api': {
                'total_requests': total_api_requests,
                'avg_response_time_ms': float(avg_api_response)
            },
            'generated_at': datetime.utcnow().isoformat()
        }

        logger.info(
            f"Daily report generated",
            extra={
                'date': report_date.isoformat(),
                'total_sessions': total_sessions,
                'total_detections': total_detections
            }
        )

        return report

    except Exception as e:
        handle_task_error('generate_daily_report', e)
        raise


@celery_app.task(name='tasks.export_session_data')
@task_logger
def export_session_data(session_id: str, format: str = 'json') -> Dict[str, Any]:
    """
    Export session data in specified format
    
    Args:
        session_id: Session to export
        format: Export format (json, csv)
        
    Returns:
        dict: Export result with path or data
        
    Raises:
        ValueError: If session not found or format unsupported
    """
    try:
        logger.info(f"Exporting session {session_id} as {format}")

        if format not in ['json', 'csv']:
            raise ValueError(f"Unsupported export format: {format}")

        # Get session analysis
        analysis = analyze_session_data(session_id)

        return {
            'status': 'exported',
            'session_id': session_id,
            'format': format,
            'data': analysis,
            'export_timestamp': datetime.utcnow().isoformat()
        }

    except ValueError as e:
        logger.error(f"Export error: {e}")
        raise
    except Exception as e:
        handle_task_error('export_session_data', e)
        raise
