"""Telemetry collection for modal system events."""
import time
import logging
from flask import request, session, current_app
from app.core.extensions import db
from sqlalchemy import text

# Set up telemetry logger
telemetry_logger = logging.getLogger('crystalbudget.telemetry')
telemetry_logger.setLevel(logging.INFO)


class ModalTelemetry:
    """Collect and store modal system telemetry data."""
    
    @staticmethod
    def record_modal_event(event_type, modal_name, data=None, user_id=None):
        """Record a modal system event."""
        if not user_id:
            user_id = session.get('user_id', 'anonymous')
            
        event_data = {
            'timestamp': time.time(),
            'event_type': event_type,  # open, close, submit, error, load
            'modal_name': modal_name,  # expense_add, income_edit, etc.
            'user_id': user_id,
            'user_agent': request.headers.get('User-Agent', ''),
            'path': request.path,
            'data': data or {}
        }
        
        try:
            # Log to file for analysis
            telemetry_logger.info(
                f"modal_event={event_type} "
                f"modal_name={modal_name} "
                f"user_id={user_id} "
                f"duration_ms={data.get('duration_ms', 0) if data else 0} "
                f"success={data.get('success', True) if data else True}"
            )
            
            # Store in database if available
            if current_app.config.get('TELEMETRY_STORE_DB', False):
                ModalTelemetry._store_event_db(event_data)
                
        except Exception as e:
            # Don't break application for telemetry failures
            telemetry_logger.error(f"Failed to record telemetry: {e}")
    
    @staticmethod
    def _store_event_db(event_data):
        """Store event in database."""
        try:
            # Create telemetry table if it doesn't exist
            with db.engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS modal_telemetry (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL NOT NULL,
                        event_type TEXT NOT NULL,
                        modal_name TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        user_agent TEXT,
                        path TEXT,
                        data TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                # Insert event
                conn.execute(text("""
                    INSERT INTO modal_telemetry 
                    (timestamp, event_type, modal_name, user_id, user_agent, path, data)
                    VALUES (:timestamp, :event_type, :modal_name, :user_id, :user_agent, :path, :data)
                """), {
                    'timestamp': event_data['timestamp'],
                    'event_type': event_data['event_type'],
                    'modal_name': event_data['modal_name'],
                    'user_id': event_data['user_id'],
                    'user_agent': event_data['user_agent'],
                    'path': event_data['path'],
                    'data': str(event_data['data'])
                })
                conn.commit()
                
        except Exception as e:
            telemetry_logger.error(f"Failed to store event in database: {e}")
    
    @staticmethod
    def get_telemetry_summary(hours=24):
        """Get telemetry summary for the last N hours."""
        try:
            cutoff_time = time.time() - (hours * 3600)
            
            with db.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT 
                        event_type,
                        modal_name,
                        COUNT(*) as event_count,
                        COUNT(DISTINCT user_id) as unique_users
                    FROM modal_telemetry 
                    WHERE timestamp > :cutoff_time
                    GROUP BY event_type, modal_name
                    ORDER BY event_count DESC
                """), {'cutoff_time': cutoff_time})
                
                return [dict(row._mapping) for row in result]
                
        except Exception as e:
            telemetry_logger.error(f"Failed to get telemetry summary: {e}")
            return []


def record_modal_open(modal_name, user_id=None):
    """Record modal open event."""
    ModalTelemetry.record_modal_event('open', modal_name, user_id=user_id)


def record_modal_close(modal_name, duration_ms=0, user_id=None):
    """Record modal close event."""
    ModalTelemetry.record_modal_event('close', modal_name, {
        'duration_ms': duration_ms
    }, user_id=user_id)


def record_modal_submit(modal_name, success=True, duration_ms=0, user_id=None):
    """Record modal submit event."""
    ModalTelemetry.record_modal_event('submit', modal_name, {
        'success': success,
        'duration_ms': duration_ms
    }, user_id=user_id)


def record_modal_error(modal_name, error_type, error_message=None, user_id=None):
    """Record modal error event."""
    ModalTelemetry.record_modal_event('error', modal_name, {
        'error_type': error_type,
        'error_message': error_message
    }, user_id=user_id)


def record_modal_load(modal_name, load_time_ms, success=True, user_id=None):
    """Record modal load event."""
    ModalTelemetry.record_modal_event('load', modal_name, {
        'load_time_ms': load_time_ms,
        'success': success
    }, user_id=user_id)