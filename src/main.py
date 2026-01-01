#!/usr/bin/env python3
"""
MessageIX Data Manager
Main application entry point
"""

import sys
import os
import platform
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize

from ui.main_window import MainWindow


def set_windows_taskbar_icon(window, icon_path):
    """Set the taskbar icon on Windows using Windows API"""
    if platform.system() != 'Windows':
        return

    try:
        import ctypes
        from ctypes import wintypes

        # Load user32.dll
        user32 = ctypes.WinDLL('user32', use_last_error=True)

        # Define Windows API functions
        LoadImageW = user32.LoadImageW
        LoadImageW.argtypes = [wintypes.HINSTANCE, wintypes.LPWSTR, wintypes.UINT, ctypes.c_int, ctypes.c_int, wintypes.UINT]
        LoadImageW.restype = wintypes.HANDLE

        SendMessageW = user32.SendMessageW
        SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        SendMessageW.restype = wintypes.LPARAM  # Use LPARAM instead of LRESULT

        # Constants
        IMAGE_ICON = 1
        LR_LOADFROMFILE = 0x0010
        WM_SETICON = 0x0080
        ICON_SMALL = 0
        ICON_BIG = 1

        # Get window handle
        hwnd = int(window.winId())

        # Load the icon
        hicon = LoadImageW(None, icon_path, IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
        if hicon:
            # Set both small and big icons
            SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon)
            SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon)
            print("Set Windows taskbar icon using API")
        else:
            print("Failed to load icon for Windows API")

    except Exception as e:
        print(f"Error setting Windows taskbar icon: {e}")


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("MessageIX Data Manager")
    app.setApplicationVersion("1.0.0")
    app.setApplicationDisplayName("MessageIX Data Manager")

    # Set application icon using PNG files with multiple sizes
    app_icon = QIcon()
    icons_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "icons")

    # Add multiple PNG sizes to the icon
    sizes = [256, 128, 64, 48, 32, 16]
    for size in sizes:
        png_path = os.path.join(icons_dir, f"icon_{size}x{size}.png")
        if os.path.exists(png_path):
            app_icon.addFile(png_path, size=QSize(size, size))

    if not app_icon.isNull():
        app.setWindowIcon(app_icon)

    # Create and show main window
    window = MainWindow()
    window.show()

    # Set window icon after showing (important for Windows taskbar)
    if not app_icon.isNull():
        window.setWindowIcon(app_icon)

        # On Windows, also set the taskbar icon using Windows API
        ico_path = os.path.join(icons_dir, "messageix_data_manager.ico")
        if os.path.exists(ico_path):
            set_windows_taskbar_icon(window, ico_path)

        # Also ensure icon is set after a short delay
        from PyQt5.QtCore import QTimer
        def set_icon_again():
            window.setWindowIcon(app_icon)
        QTimer.singleShot(100, set_icon_again)

    # Start event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
