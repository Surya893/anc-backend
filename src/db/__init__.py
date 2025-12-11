"""
Shared database models for ANC Platform
Centralized models that can be imported by both API stacks
"""

from .models import db, User, AudioSession, NoiseDetection, ProcessingMetric, APIRequest

__all__ = [
    'db',
    'User',
    'AudioSession', 
    'NoiseDetection',
    'ProcessingMetric',
    'APIRequest'
]

# Prevent double initialization
_db_initialized = False

def get_db():
    """Get the shared database instance, ensuring it's properly initialized"""
    global _db_initialized
    return db