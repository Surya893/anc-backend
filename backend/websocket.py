"""
WebSocket Server for Real-Time Audio Streaming
"""

from flask_socketio import emit, join_room, leave_room
import logging

logger = logging.getLogger(__name__)


def init_socketio(socketio):
    """Initialize WebSocket event handlers"""

    @socketio.on('connect')
    def handle_connect():
        """Handle client connection"""
        logger.info(f"Client connected")
        emit('connected', {'message': 'Connected to ANC server'})

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        logger.info(f"Client disconnected")

    @socketio.on('join_session')
    def handle_join_session(data):
        """Join audio processing session"""
        session_id = data.get('session_id')
        if session_id:
            join_room(session_id)
            logger.info(f"Client joined session: {session_id}")
            emit('session_joined', {'session_id': session_id})

    @socketio.on('leave_session')
    def handle_leave_session(data):
        """Leave audio processing session"""
        session_id = data.get('session_id')
        if session_id:
            leave_room(session_id)
            logger.info(f"Client left session: {session_id}")
            emit('session_left', {'session_id': session_id})

    @socketio.on('audio_chunk')
    def handle_audio_chunk(data):
        """
        Handle incoming audio chunk for processing

        Data format:
        {
            'session_id': 'uuid',
            'audio_data': 'base64-encoded-audio',
            'sample_rate': 48000,
            'chunk_index': 0
        }
        """
        try:
            session_id = data.get('session_id')
            audio_data = data.get('audio_data')
            sample_rate = data.get('sample_rate', 48000)

            # Process audio with ANC
            from services.anc_service import ANCService
            anc_service = ANCService()

            result = anc_service.process_audio(
                audio_data=audio_data,
                sample_rate=sample_rate,
                algorithm=data.get('algorithm', 'nlms'),
                intensity=data.get('intensity', 1.0)
            )

            # Send processed audio back
            emit('processed_audio', {
                'session_id': session_id,
                'processed_audio': result['processed_audio'],
                'metrics': result['metrics'],
                'chunk_index': data.get('chunk_index')
            }, room=session_id)

            logger.debug(f"Processed audio chunk for session: {session_id}")

        except Exception as e:
            logger.error(f"Error processing audio chunk: {e}")
            emit('error', {'message': str(e)})

    @socketio.on('request_metrics')
    def handle_request_metrics(data):
        """Send real-time metrics update"""
        session_id = data.get('session_id')

        # Get session metrics from database
        try:
            from database.models import AudioSession

            session = AudioSession.query.get(session_id)
            if session:
                emit('metrics_update', {
                    'session_id': session_id,
                    'metrics': {
                        'chunks_processed': session.total_chunks_processed,
                        'avg_latency_ms': session.average_latency_ms,
                        'avg_cancellation_db': session.average_cancellation_db
                    }
                }, room=session_id)

        except Exception as e:
            logger.error(f"Error fetching metrics: {e}")

    logger.info("WebSocket event handlers initialized")
