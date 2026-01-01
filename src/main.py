#!/usr/bin/env python3
"""
Message Viewer - message_ix Data Manager
Main application entry point
"""

import sys
from PyQt5.QtWidgets import QApplication

from ui.main_window import MainWindow


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("Message Viewer")
    app.setApplicationVersion("1.0.0")

    # Create and show main window
    window = MainWindow()
    window.show()

    # Start event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
