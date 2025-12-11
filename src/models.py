"""
SQLAlchemy models for ANC Platform
Defines database schema for sessions, detections, metrics, and requests
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class AudioSession(db.Model):
    """Audio processing session"""
    __tablename__ = 'audio_sessions'
    
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(36), nullable=False, index=True)
    started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ended_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    status = db.Column(db.String(20), default='active', nullable=False)  # active, completed, failed
    average_cancellation_db = db.Column(db.Float, default=0.0)
    average_latency_ms = db.Column(db.Float, default=0.0)
    duration_seconds = db.Column(db.Float, default=0.0)
    
    # Relationships
    noise_detections = db.relationship('NoiseDetection', cascade='all, delete-orphan')
    metrics = db.relationship('ProcessingMetric', cascade='all, delete-orphan')


class NoiseDetection(db.Model):
    """Noise detection record"""
    __tablename__ = 'noise_detections'
    
    id = db.Column(db.String(36), primary_key=True)
    session_id = db.Column(db.String(36), db.ForeignKey('audio_sessions.id'), nullable=False)
    noise_type = db.Column(db.String(50), nullable=False)
    confidence = db.Column(db.Float, default=0.0)
    intensity_db = db.Column(db.Float, default=0.0)
    detected_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    is_emergency = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class ProcessingMetric(db.Model):
    """Processing performance metrics"""
    __tablename__ = 'processing_metrics'
    
    id = db.Column(db.String(36), primary_key=True)
    session_id = db.Column(db.String(36), db.ForeignKey('audio_sessions.id'), nullable=False)
    latency_ms = db.Column(db.Float, default=0.0)
    cancellation_db = db.Column(db.Float, default=0.0)
    cpu_usage_percent = db.Column(db.Float, default=0.0)
    memory_usage_mb = db.Column(db.Float, default=0.0)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class APIRequest(db.Model):
    """API request tracking"""
    __tablename__ = 'api_requests'
    
    id = db.Column(db.String(36), primary_key=True)
    endpoint = db.Column(db.String(255), nullable=False)
    method = db.Column(db.String(10), nullable=False)
    status_code = db.Column(db.Integer, default=200)
    response_time_ms = db.Column(db.Float, default=0.0)
    user_id = db.Column(db.String(36), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)


class User(db.Model):
    """User model"""
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
