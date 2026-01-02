# UI Structure

This directory contains the user interface components for the MessageIX Data Manager application.

## Main Window Structure

```
MainWindow (QMainWindow)
├── MenuBar
│   ├── File Menu
│   │   ├── Open Input File
│   │   ├── Open Results File
│   │   └── Exit
│   ├── Run Menu
│   │   ├── Run Solver (F5)
│   │   └── Stop Solver (Ctrl+C)
│   └── View Menu
│       └── Dashboard
├── Central Widget (QHBoxLayout)
│   └── Main Splitter (Horizontal)
│       ├── Left Panel
│       │   └── Left Splitter (Vertical)
│       │       ├── Project Navigator
│       │       └── Parameter Tree
│       └── Content Widget
│           └── Content Splitter (Vertical)
│               ├── Data Container
│               │   └── Data Splitter (Horizontal)
│               │       ├── Table Container
│               │       │   ├── Title Layout
│               │       │   │   ├── Parameter Title Label
│               │       │   │   ├── View Toggle Button
│               │       │   │   └── Data Filters GroupBox
│               │       │   └── Parameter Table
│               │       └── Graph Container
│               │           └── Parameter Chart (QWebEngineView)
│               └── Console (QTextEdit)
└── Status Bar
    └── Progress Bar
```

## Components

- **main_window.ui**: Qt Designer file defining the main application window layout
- **dashboard.ui**: Qt Designer file defining the results dashboard widget
- **main_window.py**: Main window implementation loading from main_window.ui
- **dashboard.py**: Dashboard widget implementation loading from dashboard.ui
- **navigator.py**: Project navigator widget for file management
- **README.md**: This file documenting the UI structure