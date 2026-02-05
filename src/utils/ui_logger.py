"""
Unified logging adapter that outputs to both logging system and UI console.
Replaces scattered print() statements with consistent logging.

Part of the refactoring to consolidate logging across the codebase.
"""
import logging
from typing import Optional, Callable, Any
from functools import wraps

# Try to import the existing logging manager
try:
    from managers.logging_manager import logging_manager
except ImportError:
    logging_manager = None


class UILogger:
    """
    Logger adapter that writes to both file/console logs and UI console.

    Provides a unified interface for logging that:
    - Writes to the standard Python logging system
    - Writes to the logging_manager for persistence
    - Optionally writes to a UI console widget

    Usage:
        from utils.ui_logger import get_ui_logger

        logger = get_ui_logger(__name__)
        logger.set_console_callback(main_window._append_to_console)

        logger.info("Loading file...")  # Goes to log + console
        logger.error("Failed to parse", exc_info=True)  # With traceback
        logger.debug("Internal state", to_console=False)  # Only to log file
    """

    def __init__(
        self,
        name: str,
        console_callback: Optional[Callable[[str], None]] = None
    ):
        """
        Initialize the UI logger.

        Args:
            name: Logger name (usually __name__)
            console_callback: Optional callback to write to UI console
        """
        self.logger = logging.getLogger(name)
        self.console_callback = console_callback
        self._module_name = name.split('.')[-1] if '.' in name else name

    def set_console_callback(self, callback: Callable[[str], None]) -> None:
        """
        Set the UI console callback.

        Args:
            callback: Function that takes a message string
        """
        self.console_callback = callback

    def _log_to_manager(self, level: str, message: str) -> None:
        """Log to the logging manager if available."""
        if logging_manager:
            try:
                logging_manager.log(level, self._module_name, message)
            except Exception:
                pass  # Silently fail if logging manager has issues

    def _log_to_console(self, message: str, prefix: str = "") -> None:
        """Log to the UI console if callback is set."""
        if self.console_callback:
            try:
                full_message = f"{prefix}{message}" if prefix else message
                self.console_callback(full_message)
            except Exception:
                pass  # Silently fail if console has issues

    def debug(self, message: str, to_console: bool = False) -> None:
        """
        Log debug message.

        Args:
            message: Message to log
            to_console: Whether to also show in UI console
        """
        self.logger.debug(message)
        self._log_to_manager('DEBUG', message)
        if to_console:
            self._log_to_console(message, "[DEBUG] ")

    def info(self, message: str, to_console: bool = True) -> None:
        """
        Log info message.

        Args:
            message: Message to log
            to_console: Whether to also show in UI console (default: True)
        """
        self.logger.info(message)
        self._log_to_manager('INFO', message)
        if to_console:
            self._log_to_console(message)

    def warning(self, message: str, to_console: bool = True) -> None:
        """
        Log warning message.

        Args:
            message: Message to log
            to_console: Whether to also show in UI console (default: True)
        """
        self.logger.warning(message)
        self._log_to_manager('WARNING', message)
        if to_console:
            self._log_to_console(message, "[WARNING] ")

    def error(
        self,
        message: str,
        to_console: bool = True,
        exc_info: bool = False
    ) -> None:
        """
        Log error message.

        Args:
            message: Message to log
            to_console: Whether to also show in UI console (default: True)
            exc_info: Whether to include exception traceback
        """
        self.logger.error(message, exc_info=exc_info)
        self._log_to_manager('ERROR', message)
        if to_console:
            self._log_to_console(message, "[ERROR] ")

    def critical(
        self,
        message: str,
        to_console: bool = True,
        exc_info: bool = False
    ) -> None:
        """
        Log critical message.

        Args:
            message: Message to log
            to_console: Whether to also show in UI console (default: True)
            exc_info: Whether to include exception traceback
        """
        self.logger.critical(message, exc_info=exc_info)
        self._log_to_manager('CRITICAL', message)
        if to_console:
            self._log_to_console(message, "[CRITICAL] ")

    def exception(self, message: str, to_console: bool = True) -> None:
        """
        Log exception with traceback.

        Should be called from within an except block.

        Args:
            message: Message to log
            to_console: Whether to also show in UI console (default: True)
        """
        self.logger.exception(message)
        self._log_to_manager('ERROR', message)
        if to_console:
            self._log_to_console(message, "[EXCEPTION] ")


# Module-level logger cache
_loggers: dict = {}


def get_ui_logger(
    name: str,
    console_callback: Optional[Callable[[str], None]] = None
) -> UILogger:
    """
    Get or create a UILogger instance for a module.

    Uses a cache to return the same logger for the same name.

    Args:
        name: Logger name (usually __name__)
        console_callback: Optional callback to write to UI console

    Returns:
        UILogger instance
    """
    if name not in _loggers:
        _loggers[name] = UILogger(name, console_callback)
    elif console_callback and _loggers[name].console_callback is None:
        # Update console callback if provided
        _loggers[name].set_console_callback(console_callback)

    return _loggers[name]


def set_global_console_callback(callback: Callable[[str], None]) -> None:
    """
    Set the console callback for all existing loggers.

    Args:
        callback: Function that takes a message string
    """
    for logger in _loggers.values():
        logger.set_console_callback(callback)


def log_function_call(logger: UILogger, level: str = 'debug'):
    """
    Decorator to log function entry and exit.

    Args:
        logger: UILogger instance to use
        level: Log level ('debug', 'info', etc.)

    Usage:
        @log_function_call(logger)
        def my_function():
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            log_method = getattr(logger, level)
            log_method(f"Entering {func.__name__}", to_console=False)
            try:
                result = func(*args, **kwargs)
                log_method(f"Exiting {func.__name__}", to_console=False)
                return result
            except Exception as e:
                logger.error(f"Exception in {func.__name__}: {e}", exc_info=True)
                raise
        return wrapper
    return decorator


# Convenience function for quick debug output
def debug_print(message: str, module_name: str = "DEBUG") -> None:
    """
    Quick debug print that goes to both console and log.

    Use for temporary debugging that should be removed before commit.

    Args:
        message: Debug message
        module_name: Module name for context
    """
    print(f"DEBUG [{module_name}]: {message}")
    if logging_manager:
        try:
            logging_manager.log('DEBUG', module_name, message)
        except Exception:
            pass
