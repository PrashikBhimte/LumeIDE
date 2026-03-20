"""
Sidebar Module for LumeIDE

Provides the File Explorer.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeView, QLabel
)
from PyQt6.QtCore import Qt, pyqtSignal, QDir
from PyQt6.QtGui import QFileSystemModel


class FileExplorer(QWidget):
    """
    File Explorer widget showing project directory structure.
    """
    
    # Signals
    file_double_clicked = pyqtSignal(str)  # Emits file path
    file_selected = pyqtSignal(str)  # Emits file path
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """Initialize the file explorer UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        header = QLabel("Explorer")
        header.setStyleSheet("""
            QLabel {
                padding: 8px;
                font-weight: bold;
                color: #CCCCCC;
                background-color: #252526;
            }
        """)
        layout.addWidget(header)
        
        # Tree view
        self.tree_view = QTreeView()
        self.tree_view.setHeaderHidden(True)
        self.tree_view.doubleClicked.connect(self._on_double_click)
        self.tree_view.clicked.connect(self._on_click)
        
        # File system model
        self.model = QFileSystemModel()
        self.model.setRootPath('')
        self.tree_view.setModel(self.model)
        
        layout.addWidget(self.tree_view)
    
    def set_root_path(self, path: str):
        """Set the root directory to display."""
        import os
        normalized = os.path.normpath(path)
        self.model.setRootPath(normalized)
        self.tree_view.setRootIndex(self.model.index(normalized))
    
    def _on_double_click(self, index):
        """Handle file double click."""
        file_path = self.model.filePath(index)
        if not self.model.isDir(index):
            self.file_double_clicked.emit(file_path)
    
    def _on_click(self, index):
        """Handle file click."""
        file_path = self.model.filePath(index)
        self.file_selected.emit(file_path)


class Sidebar(QWidget):
    """
    Main sidebar container for the File Explorer.
    """
    
    # Forward signals from children
    file_double_clicked = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Initialize the sidebar UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.explorer = FileExplorer()
        layout.addWidget(self.explorer)

    def _connect_signals(self):
        """Connect child signals to parent."""
        self.explorer.file_double_clicked.connect(self.file_double_clicked)
    
    def set_root_path(self, path: str):
        """Set the root path for the file explorer."""
        self.explorer.set_root_path(path)
        
    def show_explorer(self):
        """Ensure the explorer is visible."""
        self.setVisible(True)


# Export
__all__ = ['Sidebar', 'FileExplorer']
