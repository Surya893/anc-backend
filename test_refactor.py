"""
Simple test script to verify the modularized Flask APIs work correctly
"""

import sys
import traceback

def test_config():
    """Test configuration module"""
    try:
        from config import get_config, DevelopmentConfig, ProductionConfig
        dev_config = get_config('development')
        prod_config = get_config('production')
        print("✓ Config module works")
        return True
    except Exception as e:
        print(f"✗ Config module failed: {e}")
        return False

def test_models():
    """Test database models"""
    try:
        from src.db.models import db, User, AudioSession, NoiseDetection, ProcessingMetric, APIRequest
        print("✓ Database models work")
        return True
    except Exception as e:
        print(f"✗ Database models failed: {e}")
        return False

def test_app_factory():
    """Test application factory"""
    try:
        from src.api.app_factory import create_app, register_core_blueprints
        app, socketio = create_app(register_blueprints=None)
        print("✓ App factory works")
        return True
    except Exception as e:
        print(f"✗ App factory failed: {e}")
        return False

def test_blueprints():
    """Test blueprint modules"""
    try:
        from src.api.routes.auth import auth_bp
        from src.api.routes.sessions import sessions_bp
        from src.api.routes.audio import audio_bp
        from src.api.routes.stats import stats_bp
        print("✓ Blueprint routes work")
        return True
    except Exception as e:
        print(f"✗ Blueprint routes failed: {e}")
        return False

def test_backend_server():
    """Test backend server"""
    try:
        from backend.server import create_app
        app = create_app('development')
        print("✓ Backend server works")
        return True
    except Exception as e:
        print(f"✗ Backend server failed: {e}")
        return False

def test_backend_api():
    """Test backend API modules"""
    try:
        from backend.api import health_bp, audio_bp, users_bp, sessions_bp
        from backend.services.anc_service import ANCService
        from backend.services.ml_service import MLService
        print("✓ Backend API modules work")
        return True
    except Exception as e:
        print(f"✗ Backend API modules failed: {e}")
        return False

def test_wsgi():
    """Test WSGI entry point"""
    try:
        from wsgi import application
        print("✓ WSGI entry point works")
        return True
    except Exception as e:
        print(f"✗ WSGI entry point failed: {e}")
        return False

def test_middleware():
    """Test middleware modules"""
    try:
        from backend.middleware.auth import require_auth, verify_api_key, verify_jwt_token
        print("✓ Middleware modules work")
        return True
    except Exception as e:
        print(f"✗ Middleware modules failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing modularized Flask APIs...")
    print("=" * 50)
    
    tests = [
        test_config,
        test_models,
        test_app_factory,
        test_blueprints,
        test_backend_server,
        test_backend_api,
        test_middleware,
        test_wsgi
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} crashed: {e}")
            traceback.print_exc()
            failed += 1
        print()
    
    print("=" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! The modularized Flask APIs are working correctly.")
    else:
        print("❌ Some tests failed. Please check the errors above.")
        sys.exit(1)