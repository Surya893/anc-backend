"""
ANC Platform API Server - Thin CLI Entry Point
Uses shared application factory to create and configure Flask app
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import shared application factory
from src.api.app_factory import create_app, register_core_blueprints


app, socketio = create_app(register_blueprints=register_core_blueprints)
logger = app.logger


if __name__ == '__main__':
    """Run the server"""
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5001))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

    logger.info(f"Starting ANC Platform server on {host}:{port}")
    logger.info(f"Debug mode: {debug}")

    # Run with SocketIO
    socketio.run(
        app,
        host=host,
        port=port,
        debug=debug,
        use_reloader=debug
    )