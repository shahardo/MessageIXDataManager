"""
Configuration module for MessageIX Data Manager

Handles application configuration, environment variables, and GAMS/MessageIX settings.
"""

from .settings import config, GAMS_PATH, MESSAGEIX_DB_PATH

__all__ = ['config', 'GAMS_PATH', 'MESSAGEIX_DB_PATH']
