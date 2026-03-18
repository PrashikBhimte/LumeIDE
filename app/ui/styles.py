DARK_PLUS_QSS = """
/*
 * Dark+ High Contrast Theme for PyQt6
 * Based on Visual Studio Code's "Dark+ (default)" and "High Contrast" themes.
 */

QWidget {
    background-color: #000000;
    color: #FFFFFF;
    border: 1px solid #FFFFFF;
    font-family: "Segoe UI", "Cantarell", "sans-serif";
    font-size: 10pt;
}

QMainWindow {
    background-color: #000000;
}

QDockWidget {
    titlebar-close-icon: url(close.png);
    titlebar-normal-icon: url(undock.png);
    border: 1px solid #FFFFFF;
    color: #FFFFFF;
}

QDockWidget::title {
    text-align: left;
    background: #1E1E1E;
    padding: 5px;
    border: 1px solid #FFFFFF;
}

QTabWidget::pane {
    border-top: 2px solid #1E1E1E;
}

QTabBar::tab {
    background: #1E1E1E;
    color: #FFFFFF;
    border: 1px solid #FFFFFF;
    border-bottom-color: #1E1E1E; /* same as pane border color */
    padding: 8px 12px;
}

QTabBar::tab:selected, QTabBar::tab:hover {
    background: #000000;
    color: #FFFFFF;
}

QTabBar::tab:selected {
    border-color: #FFFFFF;
    border-bottom-color: #000000; /* same as pane background */
}

QTabBar::tab:!selected {
    margin-top: 2px; /* make non-selected tabs look smaller */
}

QToolBar {
    background: #000000;
    border: 1px solid #FFFFFF;
    spacing: 5px;
}

QToolButton {
    background-color: transparent;
    border: 1px solid transparent;
    color: #FFFFFF;
    padding: 5px;
}

QToolButton:hover {
    background-color: #333333;
    border: 1px solid #FFFFFF;
}

QToolButton:pressed {
    background-color: #555555;
}

QTreeView {
    background-color: #000000;
    color: #FFFFFF;
    border: 1px solid #FFFFFF;
    outline: 0;
}

QTreeView::item {
    padding: 4px;
}

QTreeView::item:hover {
    background-color: #333333;
}

QTreeView::item:selected {
    background-color: #007ACC;
    color: #FFFFFF;
}

QTreeView::branch {
    background-color: transparent;
}

QTextEdit {
    background-color: #1E1E1E;
    color: #D4D4D4;
    border: 1px solid #FFFFFF;
    font-family: "Consolas", "Courier New", "monospace";
    font-size: 10pt;
    selection-background-color: #007ACC;
    selection-color: #FFFFFF;
}

QStatusBar {
    background-color: #007ACC;
    color: #FFFFFF;
    border-top: 1px solid #FFFFFF;
}

QStatusBar::item {
    border: none;
}

QLabel {
    color: #FFFFFF;
    border: none;
    padding: 0 5px;
}

QScrollBar:vertical {
    border: 1px solid #FFFFFF;
    background: #1E1E1E;
    width: 15px;
    margin: 15px 0 15px 0;
}

QScrollBar::handle:vertical {
    background: #555555;
    min-height: 20px;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: 1px solid #FFFFFF;
    background: #333333;
    height: 14px;
    subcontrol-origin: margin;
}

QScrollBar::add-line:vertical:hover, QScrollBar::sub-line:vertical:hover {
    background: #444444;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}

QScrollBar:horizontal {
    border: 1px solid #FFFFFF;
    background: #1E1E1E;
    height: 15px;
    margin: 0px 15px 0 15px;
}

QScrollBar::handle:horizontal {
    background: #555555;
    min-width: 20px;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    border: 1px solid #FFFFFF;
    background: #333333;
    width: 14px;
    subcontrol-origin: margin;
}

QScrollBar::add-line:horizontal:hover, QScrollBar::sub-line:horizontal:hover {
    background: #444444;
}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: none;
}
"""
