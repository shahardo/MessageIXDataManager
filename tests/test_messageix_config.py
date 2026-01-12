"""
Tests for MessageIX Configuration System

Tests the configuration management, environment detection, and settings validation.
"""

import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock

from src.config.settings import Config


class TestConfig:
    """Test configuration management"""

    def test_config_initialization(self):
        """Test Config class can be instantiated"""
        config = Config()
        assert config is not None

    def test_detect_gams_path_not_found(self):
        """Test GAMS path detection when not found"""
        with patch('shutil.which', return_value=None), \
             patch('os.path.exists', return_value=False):
            path = Config.detect_gams_path()
            assert path is None

    def test_detect_gams_path_from_env(self):
        """Test GAMS path from environment variable"""
        with patch.dict(os.environ, {'GAMS_PATH': '/custom/gams/path'}), \
             patch('os.path.exists', return_value=True):
            # Create a new Config instance to pick up the env var
            config = Config()
            path = config.detect_gams_path()
            assert path == '/custom/gams/path'

    @patch('platform.system')
    def test_detect_gams_path_windows(self, mock_platform):
        """Test GAMS detection on Windows"""
        mock_platform.return_value = 'Windows'

        with patch('os.path.exists') as mock_exists, \
             patch('os.listdir') as mock_listdir, \
             patch('shutil.which', return_value=None):

            # Mock directory structure
            mock_exists.side_effect = lambda path: 'C:\\GAMS\\win64' in path
            mock_listdir.return_value = ['39', '40']

            path = Config.detect_gams_path()
            assert path is None  # No gams.exe found in mock

    @patch('platform.system')
    def test_detect_gams_path_linux(self, mock_platform):
        """Test GAMS detection on Linux"""
        mock_platform.return_value = 'Linux'

        with patch('os.path.exists') as mock_exists, \
             patch('shutil.which', return_value=None):

            mock_exists.side_effect = lambda path: '/opt/gams' in path

            path = Config.detect_gams_path()
            assert path is None  # No gams executable found in mock

    def test_detect_messageix_db_path_default(self):
        """Test MessageIX database path detection with defaults"""
        with patch('os.path.exists', return_value=False):
            path = Config.detect_messageix_db_path()
            assert 'messageix.db' in path

    def test_detect_messageix_db_path_from_env(self):
        """Test MessageIX database path from environment"""
        custom_path = '/custom/db/messageix.db'
        with patch.dict(os.environ, {'MESSAGEIX_DB_PATH': custom_path}), \
             patch('os.path.exists', return_value=True):
            config = Config()
            config.MESSAGEIX_DB_PATH = custom_path
            path = config.detect_messageix_db_path()
            assert path == custom_path

    def test_validate_environment_no_messageix(self):
        """Test environment validation when MessageIX not available"""
        with patch.dict('sys.modules', {'ixmp': None, 'message_ix': None}), \
             patch('src.config.settings.config.detect_gams_path', return_value=None):

            results = Config.validate_environment()

            assert not results['gams_available']
            assert not results['messageix_available']
            assert len(results['errors']) > 0
            assert 'MessageIX not available' in str(results['errors'])

    def test_validate_environment_with_messageix(self):
        """Test environment validation when MessageIX is available"""
        with patch('importlib.util.find_spec') as mock_find_spec, \
             patch('src.config.settings.config.detect_gams_path', return_value='/path/to/gams'), \
             patch('os.makedirs'):

            # Mock successful module finding and importing
            mock_spec = MagicMock()
            mock_find_spec.return_value = mock_spec

            with patch.dict('sys.modules', {'ixmp': MagicMock(), 'message_ix': MagicMock()}):
                results = Config.validate_environment()

                assert results['gams_available']
                assert results['messageix_available']
                assert len(results['errors']) == 0

    def test_validate_environment_partial_setup(self):
        """Test environment validation with partial setup"""
        with patch.dict('sys.modules', {'ixmp': MagicMock(), 'message_ix': MagicMock()}), \
             patch('src.config.settings.config.detect_gams_path', return_value=None):

            results = Config.validate_environment()

            assert not results['gams_available']
            assert results['messageix_available']
            assert len(results['warnings']) > 0
            assert 'GAMS not found' in results['warnings'][0]


class TestConfigIntegration:
    """Integration tests for configuration system"""

    def test_config_instance_creation(self):
        """Test that config instance can be created and used"""
        from src.config import config

        assert hasattr(config, 'detect_gams_path')
        assert hasattr(config, 'detect_messageix_db_path')
        assert hasattr(config, 'validate_environment')

    def test_environment_validation_results(self):
        """Test that validate_environment returns expected structure"""
        results = Config.validate_environment()

        required_keys = ['gams_available', 'gams_path', 'messageix_available',
                        'messageix_db_path', 'warnings', 'errors']

        for key in required_keys:
            assert key in results

        assert isinstance(results['warnings'], list)
        assert isinstance(results['errors'], list)

    @patch('tempfile.mkdtemp')
    def test_messageix_db_directory_creation(self, mock_mkdtemp):
        """Test that MessageIX database directory is created"""
        mock_mkdtemp.return_value = '/tmp/test_db'

        with patch('os.makedirs') as mock_makedirs, \
             patch('os.path.exists', return_value=False):

            results = Config.validate_environment()

            # Should attempt to create directory
            mock_makedirs.assert_called_once()

    def test_config_thread_safety(self):
        """Test that configuration is thread-safe"""
        import threading
        import time

        results = []

        def validate_env():
            result = Config.validate_environment()
            results.append(result)

        # Mock the MessageIX availability check to avoid JPype threading issues
        with patch.object(Config, '_check_messageix_availability', return_value={
            'available': False,
            'warnings': ['MessageIX not available for testing'],
            'errors': []
        }):
            threads = []
            for _ in range(3):
                t = threading.Thread(target=validate_env)
                threads.append(t)
                t.start()

            for t in threads:
                t.join()

            # All threads should complete successfully
            assert len(results) == 3
            for result in results:
                assert 'gams_available' in result
                assert not result['messageix_available']  # Should be False due to mock
