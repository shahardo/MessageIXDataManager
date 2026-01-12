"""
Logging Manager - centralized logging with SQLite persistence
"""

import logging
import sqlite3
import json
from datetime import datetime
from typing import Optional, Dict, Any
import os


class SQLiteHandler(logging.Handler):
    """Custom logging handler that writes to SQLite database"""

    def __init__(self, db_path: str = "db/logs.db"):
        super().__init__()
        self.db_path = db_path
        self._conn = None
        self._db_available = True
        try:
            self._setup_database()
        except Exception as e:
            # Database setup failed, mark as unavailable
            self._db_available = False
            print(f"Database setup failed for {db_path}: {e}")

    def _setup_database(self):
        """Create logs table if it doesn't exist"""
        # For in-memory databases, keep a persistent connection
        if self.db_path == ':memory:':
            if self._conn is None:
                self._conn = sqlite3.connect(self.db_path)
            conn = self._conn
        else:
            conn = sqlite3.connect(self.db_path)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                category TEXT NOT NULL,
                message TEXT NOT NULL,
                details TEXT,
                config_id INTEGER
            )
        """)

        # Create index for faster queries
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_logs_timestamp
            ON logs(timestamp)
        """)

        conn.commit()

        # Don't close in-memory connection
        if self.db_path != ':memory:':
            conn.close()

    def emit(self, record):
        """Write log record to database"""
        if not self._db_available:
            return  # Silently ignore if database is not available

        try:
            # Format the record
            timestamp = datetime.fromtimestamp(record.created).isoformat()

            # Extract details from record
            details = None
            if hasattr(record, 'details') and record.details:
                details = json.dumps(record.details)

            # Get config_id if available
            config_id = getattr(record, 'config_id', None)

            # Use persistent connection for in-memory databases
            if self.db_path == ':memory:' and self._conn:
                conn = self._conn
            else:
                conn = sqlite3.connect(self.db_path)

            conn.execute("""
                INSERT INTO logs (timestamp, level, category, message, details, config_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                timestamp,
                record.levelname,
                getattr(record, 'category', 'GENERAL'),
                record.getMessage(),
                details,
                config_id
            ))
            conn.commit()

            # Don't close in-memory connection
            if self.db_path != ':memory:' or not self._conn:
                conn.close()

        except Exception as e:
            # Don't let logging errors break the application
            print(f"Logging error: {e}")

    def close(self):
        """Close the handler and release resources"""
        if self._conn:
            self._conn.close()
            self._conn = None
        super().close()


class LoggingManager:
    """Centralized logging manager for the application"""

    def __init__(self, log_file: str = "messageix_data_manager.log", db_file: str = "db/logs.db"):
        self.log_file = log_file
        self.db_file = db_file
        self.logger = None
        self._sqlite_handler = None
        self._setup_logging()

    def _setup_logging(self):
        """Set up Python logging with multiple handlers"""
        # Create logger
        self.logger = logging.getLogger('messageix_data_manager')
        self.logger.setLevel(logging.DEBUG)

        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()

        # File handler for traditional logging
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(category)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

        # SQLite handler for persistent storage
        sqlite_handler = SQLiteHandler(self.db_file)
        sqlite_handler.setLevel(logging.DEBUG)
        self.logger.addHandler(sqlite_handler)
        self._sqlite_handler = sqlite_handler

        # Console handler for development
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)  # Only show warnings/errors in console
        console_formatter = logging.Formatter(
            '%(levelname)s - %(category)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

    def log(self, level: str, category: str, message: str,
            details: Optional[Dict[str, Any]] = None, config_id: Optional[int] = None):
        """
        Log a message with the specified level and category

        Args:
            level: Log level ('DEBUG', 'INFO', 'WARNING', 'ERROR')
            category: Log category (e.g., 'INPUT_LOAD', 'PARAMETER_EDIT')
            message: Log message
            details: Optional structured data
            config_id: Optional configuration ID for association
        """
        if not self.logger:
            return

        # Create log record with extra attributes
        extra = {'category': category}
        if details:
            extra['details'] = details
        if config_id is not None:
            extra['config_id'] = config_id

        # Log at appropriate level
        log_method = getattr(self.logger, level.lower(), self.logger.info)
        log_method(message, extra=extra)

    def log_input_load(self, file_path: str, success: bool, error_msg: Optional[str] = None):
        """Log input file loading operations"""
        details = {'file_path': file_path, 'file_type': 'input'}
        if not success and error_msg:
            details['error'] = error_msg

        level = 'INFO' if success else 'ERROR'
        message = f"Input file load {'successful' if success else 'failed'}: {os.path.basename(file_path)}"
        self.log(level, 'INPUT_LOAD', message, details)

    def log_parameter_edit(self, param_name: str, action: str, details: Optional[Dict] = None):
        """Log parameter editing operations"""
        message = f"Parameter {action}: {param_name}"
        self.log('INFO', 'PARAMETER_EDIT', message, details or {})

    def log_solver_execution(self, command: str, status: str, duration: Optional[float] = None):
        """Log solver execution"""
        details = {'command': command, 'status': status}
        if duration:
            details['duration_seconds'] = duration

        level = 'INFO' if status == 'completed' else 'WARNING' if status == 'stopped' else 'ERROR'
        message = f"Solver execution {status}"
        self.log(level, 'SOLVER_EXECUTION', message, details)

    def log_results_load(self, file_path: str, success: bool, stats: Optional[Dict] = None):
        """Log results file loading operations"""
        details = {'file_path': file_path, 'file_type': 'results'}
        if stats:
            details.update(stats)

        level = 'INFO' if success else 'ERROR'
        message = f"Results file load {'successful' if success else 'failed'}: {os.path.basename(file_path)}"
        self.log(level, 'RESULTS_LOAD', message, details)

    # Convenience methods for different log levels
    def log_debug(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Log a debug message"""
        self.log('DEBUG', 'GENERAL', message, details)

    def log_info(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Log an info message"""
        self.log('INFO', 'GENERAL', message, details)

    def log_warning(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Log a warning message"""
        self.log('WARNING', 'GENERAL', message, details)

    def log_error(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Log an error message"""
        self.log('ERROR', 'GENERAL', message, details)

    def get_recent_logs(self, limit: int = 100, category: Optional[str] = None) -> list:
        """Get recent log entries from database"""
        try:
            # Use persistent connection for in-memory databases
            if self.db_file == ':memory:' and self._sqlite_handler and self._sqlite_handler._conn:
                conn = self._sqlite_handler._conn
                close_conn = False
            else:
                conn = sqlite3.connect(self.db_file)
                close_conn = True

            try:
                cursor = conn.cursor()

                if category:
                    cursor.execute("""
                        SELECT timestamp, level, category, message, details
                        FROM logs
                        WHERE category = ?
                        ORDER BY timestamp DESC
                        LIMIT ?
                    """, (category, limit))
                else:
                    cursor.execute("""
                        SELECT timestamp, level, category, message, details
                        FROM logs
                        ORDER BY timestamp DESC
                        LIMIT ?
                    """, (limit,))

                logs = []
                for row in cursor.fetchall():
                    timestamp, level, category, message, details_json = row
                    details = json.loads(details_json) if details_json else None

                    logs.append({
                        'timestamp': timestamp,
                        'level': level,
                        'category': category,
                        'message': message,
                        'details': details
                    })

                return logs

            finally:
                if close_conn:
                    conn.close()

        except Exception as e:
            print(f"Error retrieving logs: {e}")
            return []

    def cleanup_old_logs(self, days_to_keep: int = 30):
        """Remove logs older than specified days"""
        try:
            from datetime import datetime, timedelta
            cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()

            # Use persistent connection for in-memory databases
            if self.db_file == ':memory:' and self._sqlite_handler and self._sqlite_handler._conn:
                conn = self._sqlite_handler._conn
                close_conn = False
            else:
                conn = sqlite3.connect(self.db_file)
                close_conn = True

            try:
                conn.execute("DELETE FROM logs WHERE timestamp < ?", (cutoff_date,))
                deleted_count = conn.total_changes
                conn.commit()

                self.log('INFO', 'LOG_MAINTENANCE',
                        f"Cleaned up {deleted_count} old log entries")
            finally:
                if close_conn:
                    conn.close()

        except Exception as e:
            self.log('ERROR', 'LOG_MAINTENANCE', f"Log cleanup failed: {str(e)}")


# Global logging manager instance
logging_manager = LoggingManager()
