"""
Database schema module for ANC Platform
Provides database abstraction and schema definitions
"""

import sqlite3
from typing import Dict, Any, List, Optional
from pathlib import Path


class ANCDatabase:
    """Database interface for ANC system"""
    
    def __init__(self, db_path: str = 'anc_system.db'):
        """Initialize database"""
        self.db_path = db_path
        self.connection = None
        self._init_db()
    
    def _init_db(self):
        """Initialize database connection and schema"""
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        
        # Create tables if they don't exist
        cursor = self.connection.cursor()
        
        # Audio sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audio_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                status TEXT DEFAULT 'active',
                average_cancellation_db REAL DEFAULT 0.0,
                average_latency_ms REAL DEFAULT 0.0
            )
        ''')
        
        # Noise detections table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS noise_detections (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                noise_type TEXT NOT NULL,
                confidence REAL DEFAULT 0.0,
                intensity_db REAL DEFAULT 0.0,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(session_id) REFERENCES audio_sessions(id)
            )
        ''')
        
        # Processing metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processing_metrics (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                latency_ms REAL DEFAULT 0.0,
                cancellation_db REAL DEFAULT 0.0,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(session_id) REFERENCES audio_sessions(id)
            )
        ''')
        
        self.connection.commit()
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
    
    def execute(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute a query and return results"""
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def execute_write(self, query: str, params: tuple = ()) -> int:
        """Execute a write query and return affected rows"""
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        self.connection.commit()
        return cursor.rowcount
