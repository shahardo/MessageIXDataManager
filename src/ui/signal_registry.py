"""
Signal registry for centralized signal-slot management.
Provides a clear overview of all component connections.

Part of the refactoring to reduce complexity in main_window.py.
"""
from typing import Dict, List, Tuple, Any, Callable, Optional
from PyQt5.QtCore import QObject


class SignalConnection:
    """Represents a single signal-slot connection."""

    def __init__(
        self,
        source_name: str,
        signal_name: str,
        target: Callable,
        description: str = ""
    ):
        """
        Initialize a signal connection.

        Args:
            source_name: Name of the source component
            signal_name: Name of the signal on the source
            target: Slot function to connect
            description: Optional description of what this connection does
        """
        self.source_name = source_name
        self.signal_name = signal_name
        self.target = target
        self.description = description
        self._connected = False

    def connect(self, source: QObject) -> bool:
        """
        Connect the signal to the slot.

        Args:
            source: The QObject containing the signal

        Returns:
            True if connection succeeded
        """
        try:
            signal = getattr(source, self.signal_name)
            signal.connect(self.target)
            self._connected = True
            return True
        except AttributeError:
            print(f"Warning: Signal '{self.signal_name}' not found on '{self.source_name}'")
            return False
        except Exception as e:
            print(f"Failed to connect {self.source_name}.{self.signal_name}: {e}")
            return False

    def disconnect(self, source: QObject) -> bool:
        """
        Disconnect the signal from the slot.

        Args:
            source: The QObject containing the signal

        Returns:
            True if disconnection succeeded
        """
        if not self._connected:
            return False

        try:
            signal = getattr(source, self.signal_name)
            signal.disconnect(self.target)
            self._connected = False
            return True
        except Exception:
            return False

    @property
    def is_connected(self) -> bool:
        """Check if this connection is active."""
        return self._connected


class SignalRegistry:
    """
    Registry for managing all signal-slot connections in the application.

    Provides centralized management of Qt signal-slot connections with:
    - Registration of connections before sources are available
    - Batch connection/disconnection
    - Connection status reporting for debugging

    Usage:
        registry = SignalRegistry()

        # Register connections
        registry.register('file_navigator', 'file_selected', self._on_file_selected)
        registry.register('param_tree', 'parameter_selected', self._on_parameter_selected)

        # Set sources (components)
        registry.set_source('file_navigator', self.file_navigator)
        registry.set_source('param_tree', self.param_tree)

        # Connect all at once
        success, failed = registry.connect_all()
        print(f"Connected {success}, failed {failed}")

        # Debug
        print(registry.get_connection_report())
    """

    def __init__(self):
        """Initialize the signal registry."""
        self._connections: List[SignalConnection] = []
        self._sources: Dict[str, QObject] = {}

    def register(
        self,
        source_name: str,
        signal_name: str,
        target: Callable,
        description: str = ""
    ) -> None:
        """
        Register a signal-slot connection.

        Args:
            source_name: Name of the source component
            signal_name: Name of the signal
            target: Slot function to connect
            description: Optional description of what this connection does
        """
        self._connections.append(SignalConnection(
            source_name=source_name,
            signal_name=signal_name,
            target=target,
            description=description
        ))

    def set_source(self, name: str, source: QObject) -> None:
        """
        Register a source component by name.

        Args:
            name: Name for the source (matches source_name in register())
            source: The QObject to use as the signal source
        """
        self._sources[name] = source

    def set_sources(self, sources: Dict[str, QObject]) -> None:
        """
        Register multiple source components at once.

        Args:
            sources: Dictionary mapping names to QObjects
        """
        self._sources.update(sources)

    def connect_all(self) -> Tuple[int, int]:
        """
        Connect all registered signals.

        Returns:
            Tuple of (successful connections, failed connections)
        """
        success = 0
        failed = 0

        for conn in self._connections:
            source = self._sources.get(conn.source_name)
            if source and conn.connect(source):
                success += 1
            else:
                failed += 1
                if source is None:
                    print(f"Warning: Source '{conn.source_name}' not found for signal '{conn.signal_name}'")

        return success, failed

    def disconnect_all(self) -> int:
        """
        Disconnect all registered signals.

        Returns:
            Number of connections disconnected
        """
        disconnected = 0

        for conn in self._connections:
            source = self._sources.get(conn.source_name)
            if source and conn.disconnect(source):
                disconnected += 1

        return disconnected

    def connect_source(self, source_name: str) -> Tuple[int, int]:
        """
        Connect all signals for a specific source.

        Args:
            source_name: Name of the source to connect

        Returns:
            Tuple of (successful, failed)
        """
        source = self._sources.get(source_name)
        if not source:
            return 0, 0

        success = 0
        failed = 0

        for conn in self._connections:
            if conn.source_name == source_name:
                if conn.connect(source):
                    success += 1
                else:
                    failed += 1

        return success, failed

    def disconnect_source(self, source_name: str) -> int:
        """
        Disconnect all signals for a specific source.

        Args:
            source_name: Name of the source to disconnect

        Returns:
            Number of connections disconnected
        """
        source = self._sources.get(source_name)
        if not source:
            return 0

        disconnected = 0
        for conn in self._connections:
            if conn.source_name == source_name and conn.disconnect(source):
                disconnected += 1

        return disconnected

    def get_connection_report(self) -> str:
        """
        Generate a report of all connections for debugging.

        Returns:
            Multi-line string with connection status
        """
        lines = ["Signal Registry Connections:", "-" * 50]

        # Group by source
        sources = {}
        for conn in self._connections:
            if conn.source_name not in sources:
                sources[conn.source_name] = []
            sources[conn.source_name].append(conn)

        for source_name, conns in sorted(sources.items()):
            source_exists = source_name in self._sources
            lines.append(f"\n{source_name} {'(registered)' if source_exists else '(NOT REGISTERED)'}")

            for conn in conns:
                status = "CONNECTED" if conn.is_connected else "PENDING"
                lines.append(f"  [{status}] {conn.signal_name} -> {conn.target.__name__}")
                if conn.description:
                    lines.append(f"           {conn.description}")

        # Summary
        total = len(self._connections)
        connected = sum(1 for c in self._connections if c.is_connected)
        lines.append(f"\n{'-' * 50}")
        lines.append(f"Total: {total} connections, {connected} connected, {total - connected} pending")

        return "\n".join(lines)

    def get_connections_for_source(self, source_name: str) -> List[SignalConnection]:
        """
        Get all connections for a specific source.

        Args:
            source_name: Name of the source

        Returns:
            List of SignalConnection objects
        """
        return [c for c in self._connections if c.source_name == source_name]

    def clear(self) -> None:
        """Clear all registered connections and sources."""
        self.disconnect_all()
        self._connections.clear()
        self._sources.clear()

    @property
    def total_connections(self) -> int:
        """Get total number of registered connections."""
        return len(self._connections)

    @property
    def connected_count(self) -> int:
        """Get number of active connections."""
        return sum(1 for c in self._connections if c.is_connected)
