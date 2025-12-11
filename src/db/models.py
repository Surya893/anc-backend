"""
SQLAlchemy models for ANC Platform
Defines database schema for users, sessions, processing metrics, etc.
"""

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from sqlalchemy import func

db = SQLAlchemy()


class User(db.Model):
    """User model for authentication and authorization"""
    
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    api_key = db.Column(db.String(128), unique=True, nullable=True, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    audio_sessions = db.relationship('AudioSession', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    api_requests = db.relationship('APIRequest', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def generate_api_key(self):
        """Generate unique API key"""
        import secrets
        self.api_key = secrets.token_urlsafe(32)
    
    def to_dict(self):
        """Convert user to dictionary (exclude sensitive data)"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_active': self.is_active,
            'is_admin': self.is_admin,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def get_by_api_key(cls, api_key):
        """Get user by API key"""
        return cls.query.filter_by(api_key=api_key, is_active=True).first()
    
    @classmethod
    def get_by_username(cls, username):
        """Get user by username"""
        return cls.query.filter_by(username=username, is_active=True).first()


class AudioSession(db.Model):
    """Audio processing session model"""
    
    __tablename__ = 'audio_sessions'
    
    id = db.Column(db.String(36), primary_key=True)  # UUID as string
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    session_type = db.Column(db.String(50), default='live', nullable=False)  # live, batch, test
    sample_rate = db.Column(db.Integer, default=48000, nullable=False)
    channels = db.Column(db.Integer, default=1, nullable=False)
    chunk_size = db.Column(db.Integer, default=1024, nullable=False)
    anc_enabled = db.Column(db.Boolean, default=True, nullable=False)
    anc_algorithm = db.Column(db.String(50), default='lms', nullable=False)  # lms, nlms, rls
    anc_intensity = db.Column(db.Float, default=1.0, nullable=False)
    filter_length = db.Column(db.Integer, default=256, nullable=False)
    status = db.Column(db.String(20), default='active', nullable=False)  # active, paused, completed, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ended_at = db.Column(db.DateTime)
    total_chunks_processed = db.Column(db.Integer, default=0, nullable=False)
    average_latency_ms = db.Column(db.Float, default=0.0, nullable=False)
    average_cancellation_db = db.Column(db.Float, default=0.0, nullable=False)
    
    # Relationships
    noise_detections = db.relationship('NoiseDetection', backref='session', lazy='dynamic', cascade='all, delete-orphan')
    processing_metrics = db.relationship('ProcessingMetric', backref='session', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<AudioSession {self.id}>'
    
    def to_dict(self):
        """Convert session to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'session_type': self.session_type,
            'sample_rate': self.sample_rate,
            'channels': self.channels,
            'chunk_size': self.chunk_size,
            'anc_enabled': self.anc_enabled,
            'anc_algorithm': self.anc_algorithm,
            'anc_intensity': self.anc_intensity,
            'filter_length': self.filter_length,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'total_chunks_processed': self.total_chunks_processed,
            'average_latency_ms': self.average_latency_ms,
            'average_cancellation_db': self.average_cancellation_db
        }
    
    def update_averages(self, new_latency, new_cancellation, total_chunks):
        """Update running averages"""
        self.total_chunks_processed = total_chunks
        self.average_latency_ms = (
            (self.average_latency_ms * (total_chunks - 1) + new_latency) / total_chunks
        )
        self.average_cancellation_db = (
            (self.average_cancellation_db * (total_chunks - 1) + new_cancellation) / total_chunks
        )


class NoiseDetection(db.Model):
    """Noise detection results model"""
    
    __tablename__ = 'noise_detections'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(36), db.ForeignKey('audio_sessions.id'), nullable=False, index=True)
    noise_type = db.Column(db.String(100), nullable=True)  # null if no detection
    confidence = db.Column(db.Float, default=0.0, nullable=False)  # 0.0 to 1.0
    is_emergency = db.Column(db.Boolean, default=False, nullable=False)
    intensity_db = db.Column(db.Float, nullable=True)
    audio_features = db.Column(db.Text, nullable=True)  # JSON serialized features
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def __repr__(self):
        return f'<NoiseDetection {self.id} - {self.noise_type}>'
    
    def to_dict(self):
        """Convert detection to dictionary"""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'noise_type': self.noise_type,
            'confidence': self.confidence,
            'is_emergency': self.is_emergency,
            'intensity_db': self.intensity_db,
            'audio_features': self.audio_features,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ProcessingMetric(db.Model):
    """Audio processing performance metrics"""
    
    __tablename__ = 'processing_metrics'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(36), db.ForeignKey('audio_sessions.id'), nullable=False, index=True)
    latency_ms = db.Column(db.Float, nullable=False)
    cancellation_db = db.Column(db.Float, nullable=True)
    snr_improvement_db = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def __repr__(self):
        return f'<ProcessingMetric {self.id} - Session {self.session_id}>'
    
    def to_dict(self):
        """Convert metric to dictionary"""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'latency_ms': self.latency_ms,
            'cancellation_db': self.cancellation_db,
            'snr_improvement_db': self.snr_improvement_db,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class APIRequest(db.Model):
    """API request logging and metrics"""
    
    __tablename__ = 'api_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)  # null for anonymous
    method = db.Column(db.String(10), nullable=False)
    endpoint = db.Column(db.String(255), nullable=False)
    status_code = db.Column(db.Integer, nullable=False)
    response_time_ms = db.Column(db.Float, nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)  # IPv6 compatible
    user_agent = db.Column(db.String(512), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def __repr__(self):
        return f'<APIRequest {self.id} - {self.method} {self.endpoint}>'
    
    def to_dict(self):
        """Convert request to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'method': self.method,
            'endpoint': self.endpoint,
            'status_code': self.status_code,
            'response_time_ms': self.response_time_ms,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def get_user_stats(cls, user_id, hours=24):
        """Get API usage statistics for a user"""
        since = datetime.utcnow() - timedelta(hours=hours)
        
        stats = db.session.query(
            func.count(cls.id).label('total_requests'),
            func.avg(cls.response_time_ms).label('avg_response_time'),
            func.sum(func.case([(cls.status_code >= 400, 1)], else_=0)).label('error_count')
        ).filter(
            cls.user_id == user_id,
            cls.created_at >= since
        ).first()
        
        return {
            'total_requests': stats.total_requests or 0,
            'avg_response_time': float(stats.avg_response_time or 0),
            'error_count': stats.error_count or 0
        }


# Helper function to initialize database
def init_db(app):
    """Initialize database with Flask app"""
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        db.session.commit()