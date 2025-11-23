"""
API Blueprints Module
"""

from .health import health_bp
from .audio import audio_bp

__all__ = ['health_bp', 'audio_bp']
