"""
Audio processor module for ANC Platform
Handles audio processing, chunk management, and session handling
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AudioProcessorService:
    """Service for handling audio processing operations"""
    
    def __init__(self):
        """Initialize audio processor"""
        self.sessions = {}
        self.stats = {}
    
    def create_session(self, session_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new processing session"""
        session = {
            'id': session_id,
            'config': config,
            'created_at': datetime.utcnow(),
            'chunks_processed': 0,
            'total_duration': 0.0,
            'avg_cancellation_db': 0.0,
            'avg_latency_ms': 0.0
        }
        self.sessions[session_id] = session
        self.stats[session_id] = []
        logger.info(f"Created session: {session_id}")
        return session
    
    async def process_audio_chunk(
        self,
        session_id: str,
        audio_data,
        apply_anc: bool = True
    ) -> Dict[str, Any]:
        """
        Process a single audio chunk asynchronously
        
        Args:
            session_id: Session identifier
            audio_data: Audio data for the chunk
            apply_anc: Whether to apply noise cancellation
            
        Returns:
            Processing result with metrics
        """
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        
        # Simulate async processing
        await asyncio.sleep(0.001)
        
        result = {
            'session_id': session_id,
            'chunk_size': len(audio_data) if hasattr(audio_data, '__len__') else 0,
            'cancellation_db': 10.0 if apply_anc else 0.0,
            'latency_ms': 2.5,
            'processed_at': datetime.utcnow()
        }
        
        # Update session stats
        session = self.sessions[session_id]
        session['chunks_processed'] += 1
        self.stats[session_id].append(result)
        
        logger.debug(f"Processed chunk for session {session_id}")
        return result
    
    def process_chunk_sync(
        self,
        session_id: str,
        audio_data,
        apply_anc: bool = True
    ) -> Dict[str, Any]:
        """
        Process a single audio chunk synchronously
        This is the preferred way to use the processor in Celery tasks
        to avoid creating new event loops per chunk
        
        Args:
            session_id: Session identifier
            audio_data: Audio data for the chunk
            apply_anc: Whether to apply noise cancellation
            
        Returns:
            Processing result with metrics
        """
        # Create event loop if needed, otherwise reuse existing
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                raise RuntimeError("Event loop is closed")
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            self.process_audio_chunk(session_id, audio_data, apply_anc)
        )
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a session"""
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.sessions[session_id]
        stats = self.stats.get(session_id, [])
        
        if stats:
            cancellations = [s['cancellation_db'] for s in stats]
            latencies = [s['latency_ms'] for s in stats]
            avg_cancellation = sum(cancellations) / len(cancellations)
            avg_latency = sum(latencies) / len(latencies)
        else:
            avg_cancellation = 0.0
            avg_latency = 0.0
        
        return {
            'session_id': session_id,
            'chunks_processed': session['chunks_processed'],
            'average_cancellation_db': avg_cancellation,
            'average_latency_ms': avg_latency,
            'duration_seconds': session['total_duration'],
            'timestamp': datetime.utcnow()
        }
    
    def end_session(self, session_id: str) -> Dict[str, Any]:
        """End a processing session"""
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.sessions[session_id]
        stats = self.get_session_stats(session_id)
        
        # Cleanup
        del self.sessions[session_id]
        if session_id in self.stats:
            del self.stats[session_id]
        
        logger.info(f"Ended session: {session_id}")
        return stats


# Global instance
audio_processor = AudioProcessorService()
