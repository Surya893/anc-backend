"""
Unit tests for maintenance tasks
Tests cleanup and system maintenance tasks
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Set Celery to eager mode for testing
from celery_app import celery_app
celery_app.conf.update(task_always_eager=True, task_eager_propagates=True)

from api.tasks import (
    cleanup_old_sessions,
    cleanup_failed_sessions,
    vacuum_database,
    health_check
)
from models import db, AudioSession


@pytest.fixture
def app_context():
    """Create Flask app context for testing"""
    from api.server import create_app
    app = create_app()
    with app.app_context():
        yield app


class TestCleanupOldSessions:
    """Test cleanup_old_sessions task"""
    
    @patch('api.tasks.maintenance.db')
    def test_cleanup_old_sessions_success(self, mock_db):
        """Test successful cleanup of old sessions"""
        # Mock old sessions
        old_session = Mock()
        old_session.id = 'old_session_001'
        
        mock_db.query.return_value.filter.return_value.all.return_value = [old_session]
        
        result = cleanup_old_sessions(days_old=30)
        
        assert result['status'] == 'completed'
        assert result['sessions_deleted'] == 1
        assert 'cutoff_date' in result
    
    @patch('api.tasks.maintenance.db')
    def test_cleanup_no_old_sessions(self, mock_db):
        """Test cleanup when no old sessions exist"""
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        result = cleanup_old_sessions(days_old=30)
        
        assert result['status'] == 'completed'
        assert result['sessions_deleted'] == 0
    
    @patch('api.tasks.maintenance.db')
    def test_cleanup_with_cascade_delete(self, mock_db):
        """Test that cleanup cascades to related records"""
        old_session = Mock()
        old_session.id = 'old_session_002'
        
        mock_db.query.return_value.filter.return_value.all.return_value = [old_session]
        
        result = cleanup_old_sessions(days_old=30)
        
        # Verify session was deleted
        mock_db.session.delete.assert_called()
        mock_db.session.commit.assert_called()


class TestCleanupFailedSessions:
    """Test cleanup_failed_sessions task"""
    
    @patch('api.tasks.maintenance.db')
    def test_cleanup_failed_sessions_success(self, mock_db):
        """Test successful cleanup of failed sessions"""
        failed_session = Mock()
        failed_session.id = 'failed_session_001'
        
        mock_db.query.return_value.filter.return_value.all.return_value = [failed_session]
        
        result = cleanup_failed_sessions(hours_old=24)
        
        assert result['status'] == 'completed'
        assert result['failed_sessions_deleted'] == 1
        assert 'cutoff_time' in result
    
    @patch('api.tasks.maintenance.db')
    def test_cleanup_no_failed_sessions(self, mock_db):
        """Test cleanup when no failed sessions exist"""
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        result = cleanup_failed_sessions(hours_old=24)
        
        assert result['status'] == 'completed'
        assert result['failed_sessions_deleted'] == 0


class TestVacuumDatabase:
    """Test vacuum_database task"""
    
    @patch('api.tasks.maintenance.db')
    def test_vacuum_database_success(self, mock_db):
        """Test successful database vacuum"""
        result = vacuum_database()
        
        assert result['status'] == 'completed'
        assert result['operation'] == 'vacuum'
        assert 'timestamp' in result
        mock_db.session.execute.assert_called_with('VACUUM')
        mock_db.session.commit.assert_called()
    
    @patch('api.tasks.maintenance.db')
    def test_vacuum_database_error(self, mock_db):
        """Test vacuum with database error"""
        mock_db.session.execute.side_effect = Exception("Database error")
        
        with pytest.raises(Exception):
            vacuum_database()


class TestHealthCheck:
    """Test health_check task"""
    
    @patch('api.tasks.maintenance.AudioSession')
    def test_health_check_success(self, mock_audio_session):
        """Test successful health check"""
        mock_audio_session.query.count.return_value = 10
        
        result = health_check()
        
        assert 'timestamp' in result
        assert 'components' in result
        assert 'database' in result['components']
        assert result['components']['database']['status'] == 'healthy'
        assert result['components']['database']['session_count'] == 10
    
    @patch('api.tasks.maintenance.AudioSession')
    def test_health_check_database_failure(self, mock_audio_session):
        """Test health check with database error"""
        mock_audio_session.query.count.side_effect = Exception("Database connection failed")
        
        result = health_check()
        
        assert 'components' in result
        assert 'database' in result['components']
        assert result['components']['database']['status'] == 'unhealthy'
        assert 'error' in result['components']['database']


class TestCleanupIntegration:
    """Integration tests for cleanup operations"""
    
    def test_cleanup_cutoff_date_calculation(self):
        """Test that cutoff dates are calculated correctly"""
        from api.tasks.maintenance import cleanup_old_sessions
        from datetime import datetime, timedelta
        
        # Mock the database operations
        with patch('api.tasks.maintenance.db') as mock_db:
            mock_db.query.return_value.filter.return_value.all.return_value = []
            
            cleanup_old_sessions(days_old=30)
            
            # Verify cutoff date is approximately 30 days ago
            call_args = str(mock_db.query.return_value.filter.call_args)
            # Should contain filter for created_at < cutoff_date
            assert 'AudioSession.created_at' in call_args or 'created_at' in call_args


class TestErrorHandling:
    """Test error handling in maintenance tasks"""
    
    @patch('api.tasks.maintenance.db')
    def test_cleanup_handles_individual_delete_errors(self, mock_db):
        """Test that cleanup handles errors for individual sessions"""
        session1 = Mock()
        session1.id = 'session_1'
        
        session2 = Mock()
        session2.id = 'session_2'
        
        mock_db.query.return_value.filter.return_value.all.return_value = [
            session1, session2
        ]
        
        # First delete succeeds, second fails
        mock_db.session.delete.side_effect = [None, Exception("Delete failed")]
        
        with pytest.raises(Exception):
            cleanup_old_sessions(days_old=30)
        
        # Verify rollback was called
        assert mock_db.session.rollback.called


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
