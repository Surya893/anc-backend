"""
Production WebSocket Handler for Real-Time Audio Streaming
Handles mic → processing → speakers with <30ms latency
"""

from flask_socketio import emit
from flask import request
import logging
import numpy as np
from datetime import datetime
import base64

from realtime_audio_engine import (
    create_streaming_session,
    get_streaming_session,
    end_streaming_session
)


logger = logging.getLogger(__name__)


def register_streaming_handlers(socketio):
    """Register real-time streaming WebSocket handlers"""

    @socketio.on('start_streaming')
    def handle_start_streaming(data):
        """
        Start real-time audio streaming session
        Client will send continuous audio chunks
        """
        client_id = request.sid
        session_id = data.get('session_id', client_id)

        # Configuration
        config = {
            'sample_rate': data.get('sample_rate', 48000),
            'chunk_size': data.get('chunk_size', 512),
            'channels': data.get('channels', 1),
            'anc_enabled': data.get('anc_enabled', True),
            'anc_intensity': data.get('anc_intensity', 1.0),
            'anc_algorithm': data.get('anc_algorithm', 'nlms'),
            'bypass_ml': data.get('bypass_ml', False),  # Set to True for minimum latency
            'buffer_size': data.get('buffer_size', 3)
        }

        try:
            # Create streaming session
            session = create_streaming_session(session_id, **config)
            session.start()

            emit('streaming_started', {
                'session_id': session_id,
                'config': config,
                'message': 'Real-time streaming started',
                'timestamp': datetime.utcnow().isoformat()
            })

            logger.info(f"Streaming started: {session_id} for client {client_id}")

        except Exception as e:
            logger.error(f"Error starting streaming: {e}", exc_info=True)
            emit('error', {
                'message': f'Failed to start streaming: {str(e)}',
                'timestamp': datetime.utcnow().isoformat()
            })

    @socketio.on('audio_chunk')
    def handle_audio_chunk(data):
        """
        Handle incoming audio chunk
        Process and immediately return processed audio
        """
        client_id = request.sid
        session_id = data.get('session_id')

        if not session_id:
            emit('error', {'message': 'No session_id provided'})
            return

        try:
            # Get session
            session = get_streaming_session(session_id)
            if not session:
                emit('error', {'message': 'Session not found'})
                return

            # Decode audio
            audio_b64 = data.get('audio_data')
            if not audio_b64:
                emit('error', {'message': 'No audio_data provided'})
                return

            # Convert from base64
            audio_bytes = base64.b64decode(audio_b64)
            audio_array = np.frombuffer(audio_bytes, dtype=np.float32)

            # Process audio through real-time engine
            processed_audio = session.process_audio_chunk(audio_array)

            if processed_audio is not None:
                # Convert back to base64
                processed_b64 = base64.b64encode(processed_audio.astype(np.float32).tobytes()).decode('utf-8')

                # Send processed audio back immediately
                emit('processed_chunk', {
                    'session_id': session_id,
                    'audio_data': processed_b64,
                    'timestamp': datetime.utcnow().isoformat()
                })

            else:
                # Buffer full or processing error
                logger.warning(f"Processing failed for session {session_id}")

        except Exception as e:
            logger.error(f"Error processing audio chunk: {e}", exc_info=True)
            emit('error', {
                'message': f'Audio processing error: {str(e)}',
                'timestamp': datetime.utcnow().isoformat()
            })

    @socketio.on('stop_streaming')
    def handle_stop_streaming(data):
        """Stop streaming session"""
        client_id = request.sid
        session_id = data.get('session_id')

        if not session_id:
            emit('error', {'message': 'No session_id provided'})
            return

        try:
            session = get_streaming_session(session_id)
            if session:
                stats = session.get_stats()
                end_streaming_session(session_id)

                emit('streaming_stopped', {
                    'session_id': session_id,
                    'stats': stats,
                    'message': 'Streaming stopped',
                    'timestamp': datetime.utcnow().isoformat()
                })

                logger.info(f"Streaming stopped: {session_id}")
            else:
                emit('error', {'message': 'Session not found'})

        except Exception as e:
            logger.error(f"Error stopping streaming: {e}", exc_info=True)
            emit('error', {
                'message': f'Failed to stop streaming: {str(e)}',
                'timestamp': datetime.utcnow().isoformat()
            })

    @socketio.on('update_streaming_settings')
    def handle_update_settings(data):
        """Update streaming settings in real-time"""
        session_id = data.get('session_id')

        if not session_id:
            emit('error', {'message': 'No session_id provided'})
            return

        try:
            session = get_streaming_session(session_id)
            if not session:
                emit('error', {'message': 'Session not found'})
                return

            # Update settings
            settings = {}
            if 'anc_enabled' in data:
                settings['anc_enabled'] = data['anc_enabled']
            if 'anc_intensity' in data:
                settings['anc_intensity'] = data['anc_intensity']
            if 'anc_algorithm' in data:
                settings['anc_algorithm'] = data['anc_algorithm']
            if 'bypass_ml' in data:
                settings['bypass_ml'] = data['bypass_ml']

            session.update_settings(**settings)

            emit('settings_updated', {
                'session_id': session_id,
                'settings': settings,
                'timestamp': datetime.utcnow().isoformat()
            })

            logger.info(f"Settings updated for session {session_id}: {settings}")

        except Exception as e:
            logger.error(f"Error updating settings: {e}", exc_info=True)
            emit('error', {
                'message': f'Failed to update settings: {str(e)}',
                'timestamp': datetime.utcnow().isoformat()
            })

    @socketio.on('get_streaming_stats')
    def handle_get_stats(data):
        """Get real-time streaming statistics"""
        session_id = data.get('session_id')

        if not session_id:
            emit('error', {'message': 'No session_id provided'})
            return

        try:
            session = get_streaming_session(session_id)
            if not session:
                emit('error', {'message': 'Session not found'})
                return

            stats = session.get_stats()

            emit('streaming_stats', {
                'session_id': session_id,
                'stats': stats,
                'timestamp': datetime.utcnow().isoformat()
            })

        except Exception as e:
            logger.error(f"Error getting stats: {e}", exc_info=True)
            emit('error', {
                'message': f'Failed to get stats: {str(e)}',
                'timestamp': datetime.utcnow().isoformat()
            })

    logger.info("Streaming WebSocket handlers registered")
