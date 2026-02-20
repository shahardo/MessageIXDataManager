# tests/conftest.py
import sys
import os

# Add src directory to Python path for all tests
src_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# QtWebEngineWidgets requires AA_ShareOpenGLContexts set BEFORE QApplication
# is created.  Using QCoreApplication.setAttribute avoids importing
# QApplication at module level, which would conflict with tests that patch it.
from PyQt5.QtCore import Qt, QCoreApplication
QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
