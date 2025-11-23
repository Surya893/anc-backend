"""
Celery Background Tasks for ANC Platform
Handles asynchronous processing, model training, and batch operations
"""

from celery import Celery, Task
from celery.schedules import crontab
import logging
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import joblib

from config import get_config
from audio_processor import audio_processor
from feature_extraction import AudioFeatureExtractor
import librosa


logger = logging.getLogger(__name__)

# Initialize Celery
config = get_config()
celery_app = Celery('anc_platform')
celery_app.conf.update(
    broker_url=config.CELERY_BROKER_URL,
    result_backend=config.CELERY_RESULT_BACKEND,
    task_serializer=config.CELERY_TASK_SERIALIZER,
    result_serializer=config.CELERY_RESULT_SERIALIZER,
    accept_content=config.CELERY_ACCEPT_CONTENT,
    timezone=config.CELERY_TIMEZONE,
    enable_utc=config.CELERY_ENABLE_UTC,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50
)


class DatabaseTask(Task):
    """Base task with database session handling"""
    _db = None

    @property
    def db(self):
        if self._db is None:
            from models import db
            self._db = db
        return self._db


@celery_app.task(bind=True, base=DatabaseTask, name='tasks.process_audio_file')
def process_audio_file(self, file_path: str, session_id: str, apply_anc: bool = True):
    """
    Process an audio file asynchronously

    Args:
        file_path: Path to audio file
        session_id: Processing session ID
        apply_anc: Whether to apply noise cancellation

    Returns:
        dict: Processing results with metrics
    """
    try:
        logger.info(f"Processing audio file: {file_path}")

        # Load audio file
        audio_data, sample_rate = librosa.load(file_path, sr=config.AUDIO_SAMPLE_RATE)

        # Create processing session
        session = audio_processor.create_session(session_id, {
            'anc_enabled': apply_anc,
            'anc_intensity': 1.0
        })

        # Process in chunks
        chunk_size = config.AUDIO_CHUNK_SIZE
        num_chunks = len(audio_data) // chunk_size

        results = []
        for i in range(num_chunks):
            start_idx = i * chunk_size
            end_idx = start_idx + chunk_size
            chunk = audio_data[start_idx:end_idx]

            # Update progress
            self.update_state(
                state='PROGRESS',
                meta={'current': i + 1, 'total': num_chunks}
            )

            # Process chunk (synchronous call)
            import asyncio
            result = asyncio.run(audio_processor.process_audio_chunk(
                session_id=session_id,
                audio_data=chunk,
                apply_anc=apply_anc
            ))

            results.append(result)

        # Get final stats
        stats = audio_processor.get_session_stats(session_id)

        # Cleanup
        audio_processor.end_session(session_id)

        logger.info(f"Completed processing {file_path}: {num_chunks} chunks processed")

        return {
            'status': 'completed',
            'file_path': file_path,
            'num_chunks': num_chunks,
            'session_stats': stats,
            'results_summary': {
                'average_cancellation_db': stats['average_cancellation_db'],
                'average_latency_ms': stats['average_latency_ms'],
                'duration_seconds': stats['duration_seconds']
            }
        }

    except Exception as e:
        logger.error(f"Error processing audio file: {e}", exc_info=True)
        raise


@celery_app.task(bind=True, name='tasks.batch_process_files')
def batch_process_files(self, file_paths: list, apply_anc: bool = True):
    """
    Batch process multiple audio files

    Args:
        file_paths: List of audio file paths
        apply_anc: Whether to apply noise cancellation

    Returns:
        dict: Batch processing results
    """
    try:
        logger.info(f"Batch processing {len(file_paths)} files")

        results = []
        for i, file_path in enumerate(file_paths):
            # Update progress
            self.update_state(
                state='PROGRESS',
                meta={'current': i + 1, 'total': len(file_paths)}
            )

            # Process file
            session_id = f"batch_{self.request.id}_{i}"
            result = process_audio_file(file_path, session_id, apply_anc)
            results.append(result)

        return {
            'status': 'completed',
            'files_processed': len(file_paths),
            'results': results
        }

    except Exception as e:
        logger.error(f"Error in batch processing: {e}", exc_info=True)
        raise


@celery_app.task(name='tasks.train_noise_classifier')
def train_noise_classifier(training_data_dir: str):
    """
    Train or retrain the noise classification model

    Args:
        training_data_dir: Directory containing training audio files

    Returns:
        dict: Training results and metrics
    """
    try:
        logger.info(f"Training noise classifier from: {training_data_dir}")

        from sklearn.ensemble import RandomForestClassifier
        from sklearn.preprocessing import StandardScaler
        from sklearn.model_selection import train_test_split

        # Load training data
        feature_extractor = AudioFeatureExtractor()
        X = []
        y = []

        training_path = Path(training_data_dir)
        for category_dir in training_path.iterdir():
            if not category_dir.is_dir():
                continue

            category = category_dir.name
            logger.info(f"Loading category: {category}")

            for audio_file in category_dir.glob('*.wav'):
                audio, sr = librosa.load(audio_file, sr=config.AUDIO_SAMPLE_RATE)
                features = feature_extractor.extract_features(audio)

                # Convert to feature vector
                feature_vector = [
                    features['rms'],
                    features['zero_crossing_rate'],
                    features['spectral_centroid'],
                    features['spectral_rolloff'],
                    features['spectral_bandwidth']
                ]

                X.append(feature_vector)
                y.append(category)

        X = np.array(X)
        y = np.array(y)

        logger.info(f"Training data: {X.shape[0]} samples, {X.shape[1]} features")

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        # Train model
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )

        model.fit(X_train_scaled, y_train)

        # Evaluate
        train_accuracy = model.score(X_train_scaled, y_train)
        test_accuracy = model.score(X_test_scaled, y_test)

        logger.info(f"Training accuracy: {train_accuracy:.4f}")
        logger.info(f"Test accuracy: {test_accuracy:.4f}")

        # Save model
        model_path = config.ML_MODEL_PATH
        scaler_path = config.ML_SCALER_PATH

        joblib.dump(model, model_path)
        joblib.dump(scaler, scaler_path)

        logger.info(f"Model saved to: {model_path}")

        return {
            'status': 'completed',
            'train_accuracy': float(train_accuracy),
            'test_accuracy': float(test_accuracy),
            'num_samples': len(X),
            'num_features': X.shape[1],
            'categories': list(np.unique(y)),
            'model_path': str(model_path),
            'scaler_path': str(scaler_path)
        }

    except Exception as e:
        logger.error(f"Error training classifier: {e}", exc_info=True)
        raise


@celery_app.task(name='tasks.analyze_session_data')
def analyze_session_data(session_id: str):
    """
    Analyze collected session data for insights

    Args:
        session_id: Session to analyze

    Returns:
        dict: Analysis results
    """
    try:
        from models import db, AudioSession, NoiseDetection, ProcessingMetric

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
            noise_types[noise_type]['avg_confidence'] /= count
            noise_types[noise_type]['avg_intensity'] /= count

        # Analyze performance metrics
        if metrics:
            avg_latency = sum(m.latency_ms for m in metrics) / len(metrics)
            avg_cancellation = sum(m.cancellation_db for m in metrics) / len(metrics)
            max_latency = max(m.latency_ms for m in metrics)
            min_latency = min(m.latency_ms for m in metrics)
        else:
            avg_latency = avg_cancellation = max_latency = min_latency = 0.0

        analysis = {
            'session_id': session_id,
            'duration_seconds': (session.ended_at - session.started_at).total_seconds() if session.ended_at else 0,
            'total_detections': len(detections),
            'noise_types': noise_types,
            'performance': {
                'avg_latency_ms': avg_latency,
                'max_latency_ms': max_latency,
                'min_latency_ms': min_latency,
                'avg_cancellation_db': avg_cancellation
            },
            'metrics_count': len(metrics)
        }

        logger.info(f"Session analysis completed: {session_id}")

        return analysis

    except Exception as e:
        logger.error(f"Error analyzing session: {e}", exc_info=True)
        raise


@celery_app.task(name='tasks.cleanup_old_sessions')
def cleanup_old_sessions(days_old: int = 30):
    """
    Clean up old session data

    Args:
        days_old: Delete sessions older than this many days

    Returns:
        dict: Cleanup results
    """
    try:
        from models import db, AudioSession

        logger.info(f"Cleaning up sessions older than {days_old} days")

        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        # Find old sessions
        old_sessions = AudioSession.query.filter(
            AudioSession.created_at < cutoff_date,
            AudioSession.status == 'completed'
        ).all()

        count = len(old_sessions)

        # Delete sessions (cascades to related records)
        for session in old_sessions:
            db.session.delete(session)

        db.session.commit()

        logger.info(f"Cleaned up {count} old sessions")

        return {
            'status': 'completed',
            'sessions_deleted': count,
            'cutoff_date': cutoff_date.isoformat()
        }

    except Exception as e:
        logger.error(f"Error cleaning up sessions: {e}", exc_info=True)
        raise


@celery_app.task(name='tasks.generate_daily_report')
def generate_daily_report():
    """
    Generate daily usage and performance report

    Returns:
        dict: Daily report data
    """
    try:
        from models import db, AudioSession, NoiseDetection, APIRequest

        logger.info("Generating daily report")

        # Date range: yesterday
        today = datetime.utcnow().date()
        yesterday = today - timedelta(days=1)
        start_time = datetime.combine(yesterday, datetime.min.time())
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

        report = {
            'date': yesterday.isoformat(),
            'sessions': {
                'total': total_sessions,
                'avg_cancellation_db': avg_cancellation,
                'avg_latency_ms': avg_latency
            },
            'detections': {
                'total': total_detections,
                'emergency': emergency_count
            },
            'api': {
                'total_requests': total_api_requests,
                'avg_response_time_ms': avg_api_response
            }
        }

        logger.info(f"Daily report generated for {yesterday}")

        return report

    except Exception as e:
        logger.error(f"Error generating daily report: {e}", exc_info=True)
        raise


# Periodic tasks configuration
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Setup periodic tasks"""

    # Daily report at 1 AM UTC
    sender.add_periodic_task(
        crontab(hour=1, minute=0),
        generate_daily_report.s(),
        name='generate_daily_report'
    )

    # Cleanup old sessions weekly on Sunday at 2 AM
    sender.add_periodic_task(
        crontab(hour=2, minute=0, day_of_week=0),
        cleanup_old_sessions.s(days_old=30),
        name='cleanup_old_sessions'
    )

    logger.info("Periodic tasks configured")
