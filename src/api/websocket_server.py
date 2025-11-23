"""
WebSocket Server for Real-time Audio Streaming
Handles bidirectional audio streaming with clients
"""

from flask_socketio import SocketIO, emit, join_room, leave_room, rooms
from flask import request
import logging
import numpy as np
from datetime import datetime
import asyncio

from audio_processor import audio_processor, audio_base64_to_numpy, numpy_to_audio_base64


logger = logging.getLogger(__name__)

socketio = SocketIO(
    cors_allowed_origins="*",
    async_mode='threading',
    ping_timeout=10,
    ping_interval=5,
    logger=False,
    engineio_logger=False
)


# Track connected clients
connected_clients = {}


@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    client_id = request.sid
    client_ip = request.remote_addr

    connected_clients[client_id] = {
        'connected_at': datetime.utcnow(),
        'ip_address': client_ip,
        'session_id': None
    }

    logger.info(f"Client connected: {client_id} from {client_ip}")

    emit('connection_established', {
        'client_id': client_id,
        'server_time': datetime.utcnow().isoformat(),
        'message': 'Connected to ANC Platform WebSocket'
    })


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    client_id = request.sid

    if client_id in connected_clients:
        client_info = connected_clients[client_id]
        session_id = client_info.get('session_id')

        # End audio session if active
        if session_id:
            audio_processor.end_session(session_id)
            logger.info(f"Ended session {session_id} for disconnected client {client_id}")

        del connected_clients[client_id]
        logger.info(f"Client disconnected: {client_id}")


@socketio.on('start_session')
def handle_start_session(data):
    """Start a new audio processing session"""
    client_id = request.sid

    if client_id not in connected_clients:
        emit('error', {'message': 'Client not registered'})
        return

    # Extract configuration
    config = data.get('config', {})
    session_id = data.get('session_id', client_id)

    # Create processing session
    try:
        session = audio_processor.create_session(session_id, config)
        connected_clients[client_id]['session_id'] = session_id

        # Join room for this session
        join_room(session_id)

        emit('session_started', {
            'session_id': session_id,
            'config': config,
            'message': 'Audio processing session started'
        })

        logger.info(f"Started session {session_id} for client {client_id}")

    except Exception as e:
        logger.error(f"Error starting session: {e}")
        emit('error', {'message': f'Failed to start session: {str(e)}'})


@socketio.on('end_session')
def handle_end_session(data):
    """End audio processing session"""
    client_id = request.sid
    session_id = data.get('session_id')

    if not session_id and client_id in connected_clients:
        session_id = connected_clients[client_id].get('session_id')

    if not session_id:
        emit('error', {'message': 'No active session'})
        return

    try:
        # Get session stats before ending
        stats = audio_processor.get_session_stats(session_id)

        # End session
        audio_processor.end_session(session_id)

        # Leave room
        leave_room(session_id)

        # Clear session from client info
        if client_id in connected_clients:
            connected_clients[client_id]['session_id'] = None

        emit('session_ended', {
            'session_id': session_id,
            'stats': stats,
            'message': 'Session ended successfully'
        })

        logger.info(f"Ended session {session_id}")

    except Exception as e:
        logger.error(f"Error ending session: {e}")
        emit('error', {'message': f'Failed to end session: {str(e)}'})


@socketio.on('process_audio')
def handle_process_audio(data):
    """Process audio chunk"""
    client_id = request.sid
    session_id = data.get('session_id')

    if not session_id and client_id in connected_clients:
        session_id = connected_clients[client_id].get('session_id')

    if not session_id:
        emit('error', {'message': 'No active session'})
        return

    try:
        # Extract audio data
        audio_b64 = data.get('audio_data')
        if not audio_b64:
            emit('error', {'message': 'No audio data provided'})
            return

        # Convert to numpy array
        audio_array = audio_base64_to_numpy(audio_b64)

        # Process audio
        result = asyncio.run(audio_processor.process_audio_chunk(
            session_id=session_id,
            audio_data=audio_array,
            apply_anc=data.get('apply_anc', True)
        ))

        # Emit result back to client
        emit('audio_processed', result)

        # Broadcast to room if needed (for monitoring)
        if data.get('broadcast', False):
            emit('audio_processed', result, room=session_id, skip_sid=client_id)

    except Exception as e:
        logger.error(f"Error processing audio: {e}", exc_info=True)
        emit('error', {'message': f'Audio processing error: {str(e)}'})


@socketio.on('update_anc_settings')
def handle_update_anc_settings(data):
    """Update ANC settings for session"""
    client_id = request.sid
    session_id = data.get('session_id')

    if not session_id and client_id in connected_clients:
        session_id = connected_clients[client_id].get('session_id')

    if not session_id:
        emit('error', {'message': 'No active session'})
        return

    try:
        session = audio_processor.get_session(session_id)
        if not session:
            emit('error', {'message': 'Session not found'})
            return

        # Update settings
        if 'anc_enabled' in data:
            session.enable_anc(data['anc_enabled'])

        if 'anc_intensity' in data:
            session.set_intensity(data['anc_intensity'])

        if 'anc_algorithm' in data:
            session.set_algorithm(data['anc_algorithm'])

        emit('anc_settings_updated', {
            'session_id': session_id,
            'settings': {
                'anc_enabled': session.anc_enabled,
                'anc_intensity': session.anc_intensity,
                'anc_algorithm': session.anc_algorithm
            }
        })

        logger.info(f"Updated ANC settings for session {session_id}")

    except Exception as e:
        logger.error(f"Error updating ANC settings: {e}")
        emit('error', {'message': f'Failed to update settings: {str(e)}'})


@socketio.on('get_session_stats')
def handle_get_session_stats(data):
    """Get session statistics"""
    client_id = request.sid
    session_id = data.get('session_id')

    if not session_id and client_id in connected_clients:
        session_id = connected_clients[client_id].get('session_id')

    if not session_id:
        emit('error', {'message': 'No active session'})
        return

    try:
        stats = audio_processor.get_session_stats(session_id)
        if stats:
            emit('session_stats', stats)
        else:
            emit('error', {'message': 'Session not found'})

    except Exception as e:
        logger.error(f"Error getting session stats: {e}")
        emit('error', {'message': f'Failed to get stats: {str(e)}'})


@socketio.on('ping')
def handle_ping(data):
    """Handle ping for connection keep-alive"""
    emit('pong', {
        'timestamp': datetime.utcnow().isoformat(),
        'client_id': request.sid
    })


@socketio.on('broadcast_message')
def handle_broadcast(data):
    """Broadcast message to all clients in a room"""
    room = data.get('room', 'broadcast')
    message = data.get('message', '')

    emit('broadcast', {
        'from': request.sid,
        'message': message,
        'timestamp': datetime.utcnow().isoformat()
    }, room=room)


# Admin/monitoring events
@socketio.on('get_server_stats')
def handle_get_server_stats():
    """Get server statistics (admin only)"""
    stats = {
        'connected_clients': len(connected_clients),
        'active_sessions': len(audio_processor.sessions),
        'server_time': datetime.utcnow().isoformat(),
        'clients': [
            {
                'client_id': cid,
                'session_id': info.get('session_id'),
                'connected_at': info.get('connected_at').isoformat(),
                'ip_address': info.get('ip_address')
            }
            for cid, info in connected_clients.items()
        ]
    }

    emit('server_stats', stats)


# Error handler
@socketio.on_error_default
def default_error_handler(e):
    """Default error handler"""
    logger.error(f"WebSocket error: {e}", exc_info=True)
    emit('error', {
        'message': 'An error occurred',
        'details': str(e)
    })


# Background task for periodic stats broadcast
def broadcast_stats_task():
    """Periodically broadcast server stats to all clients"""
    while True:
        socketio.sleep(30)  # Every 30 seconds

        if len(connected_clients) > 0:
            stats = {
                'active_sessions': len(audio_processor.sessions),
                'total_clients': len(connected_clients),
                'timestamp': datetime.utcnow().isoformat()
            }

            socketio.emit('stats_update', stats, namespace='/', broadcast=True)


# Initialize background tasks
def init_background_tasks():
    """Initialize background tasks"""
    socketio.start_background_task(broadcast_stats_task)
    logger.info("WebSocket background tasks initialized")
