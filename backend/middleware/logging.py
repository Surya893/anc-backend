"""
Request Logging Middleware
"""

from flask import request, g
import time
import logging

logger = logging.getLogger(__name__)


def setup_logging(app):
    """Setup request logging middleware"""

    @app.before_request
    def before_request():
        """Log request start"""
        g.start_time = time.time()
        logger.info(f"{request.method} {request.path} - Started")

    @app.after_request
    def after_request(response):
        """Log request completion"""
        if hasattr(g, 'start_time'):
            elapsed = time.time() - g.start_time
            logger.info(
                f"{request.method} {request.path} - "
                f"Status: {response.status_code} - "
                f"Duration: {elapsed:.3f}s"
            )
        return response

    logger.info("Request logging middleware configured")
