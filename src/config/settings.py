"""
Configuration settings for MessageIX Data Manager

Uses python-decouple for environment variable management and provides
centralized configuration for GAMS, MessageIX, and application settings.
"""

import os
import platform
import threading
from pathlib import Path
from typing import Optional
from decouple import config as decouple_config, undefined

# Base directory
BASE_DIR = Path(__file__).parent.parent.parent

# Thread lock for MessageIX import checking (JPype is not thread-safe)
_messageix_check_lock = threading.Lock()
_messageix_check_cache = None

# Configuration using python-decouple
class Config:
    """Application configuration class"""

    # GAMS Configuration
    GAMS_PATH = decouple_config('GAMS_PATH', default=None)

    # MessageIX Configuration
    MESSAGEIX_DB_PATH = decouple_config('MESSAGEIX_DB_PATH', default=None)
    MESSAGEIX_PLATFORM_NAME = decouple_config('MESSAGEIX_PLATFORM_NAME', default='messageix_data_manager')

    # Application Configuration
    DEBUG = decouple_config('DEBUG', default=False, cast=bool)
    LOG_LEVEL = decouple_config('LOG_LEVEL', default='INFO')

    # Database Configuration (for future use)
    DATABASE_URL = decouple_config('DATABASE_URL', default=None)

    @classmethod
    def detect_gams_path(cls) -> Optional[str]:
        """
        Auto-detect GAMS installation path based on platform and common locations.

        Returns:
            Path to GAMS executable if found, None otherwise
        """
        system = platform.system()

        if cls.GAMS_PATH and os.path.exists(cls.GAMS_PATH):
            return cls.GAMS_PATH

        # Common GAMS installation paths by platform
        if system == 'Windows':
            search_paths = [
                'C:\\GAMS\\win64',
                'C:\\Program Files\\GAMS',
                'C:\\Program Files (x86)\\GAMS',
            ]
            # Look for latest version directory
            for base_path in search_paths:
                if os.path.exists(base_path):
                    try:
                        subdirs = [d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]
                        # Sort by version number (assuming format like "38", "39", etc.)
                        version_dirs = sorted(subdirs, key=lambda x: [int(i) for i in x.split('.') if i.isdigit()], reverse=True)
                        for version_dir in version_dirs:
                            full_path = os.path.join(base_path, version_dir)
                            exe_path = os.path.join(full_path, 'gams.exe')
                            if os.path.exists(exe_path):
                                return exe_path
                    except (OSError, ValueError):
                        continue

        elif system == 'Linux':
            search_paths = [
                '/opt/gams',
                '/usr/local/gams',
                '/usr/gams',
                str(Path.home() / 'gams'),
            ]
            for base_path in search_paths:
                if os.path.exists(base_path):
                    exe_path = os.path.join(base_path, 'gams')
                    if os.path.exists(exe_path):
                        return exe_path

        elif system == 'Darwin':  # macOS
            search_paths = [
                '/Applications/GAMS',
                str(Path.home() / 'Applications' / 'GAMS'),
                '/usr/local/gams',
            ]
            for base_path in search_paths:
                if os.path.exists(base_path):
                    exe_path = os.path.join(base_path, 'gams')
                    if os.path.exists(exe_path):
                        return exe_path

        # Check PATH environment variable
        import shutil
        gams_exe = shutil.which('gams')
        if gams_exe:
            return gams_exe

        return None

    @classmethod
    def detect_messageix_db_path(cls) -> Optional[str]:
        """
        Auto-detect MessageIX database path.

        Returns:
            Path to MessageIX database if found, None otherwise
        """
        if cls.MESSAGEIX_DB_PATH and os.path.exists(cls.MESSAGEIX_DB_PATH):
            return cls.MESSAGEIX_DB_PATH

        # Default MessageIX database locations
        default_paths = [
            str(BASE_DIR / 'db' / 'messageix.db'),
            str(Path.home() / '.messageix' / 'default.db'),
            '/tmp/messageix.db',  # Linux/Mac
            str(Path.home() / 'AppData' / 'Local' / 'Temp' / 'messageix.db'),  # Windows
        ]

        for path in default_paths:
            if os.path.exists(path):
                return path

        # Return default path
        return str(BASE_DIR / 'db' / 'messageix.db')

    @classmethod
    def _check_messageix_availability(cls) -> dict:
        """
        Check MessageIX availability with proper error handling.
        This method is thread-safe when called through validate_environment().

        Returns:
            Dictionary with availability status, warnings, and errors
        """
        result = {
            'available': False,
            'warnings': [],
            'errors': []
        }

        try:
            # First check if modules are importable without actually importing
            import importlib.util
            ixmp_spec = importlib.util.find_spec('ixmp')
            messageix_spec = importlib.util.find_spec('message_ix')

            if ixmp_spec and messageix_spec:
                # Try importing but catch any initialization errors
                try:
                    import ixmp
                    import message_ix
                    result['available'] = True
                except Exception as e:
                    # MessageIX might be installed but not properly configured
                    result['warnings'].append(f"MessageIX modules found but initialization failed: {e}")
            else:
                result['errors'].append("MessageIX not available: modules not found")

        except Exception as e:
            result['errors'].append(f"MessageIX check failed: {e}")

        return result

    @classmethod
    def validate_environment(cls) -> dict:
        """
        Validate the environment and return status information.

        Returns:
            Dictionary with validation results
        """
        results = {
            'gams_available': False,
            'gams_path': None,
            'messageix_available': False,
            'messageix_db_path': None,
            'warnings': [],
            'errors': []
        }

        # Check GAMS
        gams_path = cls.detect_gams_path()
        if gams_path:
            results['gams_available'] = True
            results['gams_path'] = gams_path
        else:
            results['warnings'].append("GAMS not found. Set GAMS_PATH environment variable or ensure GAMS is in PATH.")

        # Check MessageIX - with thread-safe import checking (JPype is not thread-safe)
        global _messageix_check_cache
        if _messageix_check_cache is not None:
            # Use cached result
            messageix_result = _messageix_check_cache
        else:
            # Perform the check with thread synchronization
            with _messageix_check_lock:
                # Double-check the cache in case another thread set it
                if _messageix_check_cache is not None:
                    messageix_result = _messageix_check_cache
                else:
                    messageix_result = cls._check_messageix_availability()
                    _messageix_check_cache = messageix_result

        # Apply the result to the current validation
        results['messageix_available'] = messageix_result['available']
        results['warnings'].extend(messageix_result['warnings'])
        results['errors'].extend(messageix_result['errors'])

        # Check database path
        db_path = cls.detect_messageix_db_path()
        if db_path:
            results['messageix_db_path'] = db_path
            # Ensure directory exists
            try:
                os.makedirs(os.path.dirname(db_path), exist_ok=True)
            except Exception as e:
                results['warnings'].append(f"Could not create database directory: {e}")

        return results


# Global config instance
config = Config()

# Convenience access to key paths
GAMS_PATH = config.detect_gams_path()
MESSAGEIX_DB_PATH = config.detect_messageix_db_path()
