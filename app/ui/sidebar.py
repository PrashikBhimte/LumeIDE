"""
Sidebar Module for LumeIDE

Provides the File Explorer with VS Code styling.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeView, QLabel, QPushButton, QHBoxLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QDir
from PyQt6.QtGui import QFileSystemModel, QFont


class FileExplorer(QWidget):
    """
    File Explorer widget showing project directory structure.
    VS Code-style file explorer.
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
        
        # Header with title
        header_widget = QWidget()
        header_widget.setStyleSheet("background-color: #252526;")
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(12, 8, 12, 8)
        
        header_title = QLabel("EXPLORER")
        header_title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        header_title.setStyleSheet("""
            QLabel {
                color: #BBBBBB;
                letter-spacing: 1px;
                background-color: transparent;
            }
        """)
        header_layout.addWidget(header_title)
        layout.addWidget(header_widget)
        
        # Tree view
        self.tree_view = QTreeView()
        self.tree_view.setHeaderHidden(True)
        self.tree_view.setAnimated(True)
        self.tree_view.setAlternatingRowColors(False)
        self.tree_view.setUniformRowHeights(True)
        self.tree_view.doubleClicked.connect(self._on_double_click)
        self.tree_view.clicked.connect(self._on_click)
        
        # File system model
        self.model = QFileSystemModel()
        self.model.setRootPath('')
        self.tree_view.setModel(self.model)
        
        # Style the tree view
        self.tree_view.setStyleSheet("""
            QTreeView {
                background-color: #1E1E1E;
                color: #CCCCCC;
                border: none;
                outline: 0;
                padding: 4px 0;
            }
            QTreeView::item {
                padding: 3px 8px 3px 4px;
                border: none;
            }
            QTreeView::item:hover {
                background-color: #2A2D2E;
            }
            QTreeView::item:selected {
                background-color: #094771;
                color: #FFFFFF;
            }
            QTreeView::item:selected:active {
                background-color: #094771;
            }
            QTreeView::branch {
                background-color: transparent;
            }
            QTreeView::branch:has-children:!has-siblings:closed,
            QTreeView::branch:closed:has-children:has-siblings {
                border-image: none;
                image: url(none);
            }
            QTreeView::branch:open:has-children:!has-siblings,
            QTreeView::branch:open:has-children:has-siblings {
                border-image: none;
                image: url(none);
            }
            QHeaderView {
                background-color: #1E1E1E;
            }
        """)

        # Hide columns for Size, Type, Date Modified
        self.tree_view.setColumnHidden(1, True)
        self.tree_view.setColumnHidden(2, True)
        self.tree_view.setColumnHidden(3, True)
        
        layout.addWidget(self.tree_view)
        
        # Open folder button
        footer_widget = QWidget()
        footer_widget.setStyleSheet("""
            background-color: #252526;
            border-top: 1px solid #3C3C3C;
        """)
        footer_layout = QVBoxLayout(footer_widget)
        footer_layout.setContentsMargins(8, 4, 8, 4)
        
        self.open_folder_btn = QPushButton("📂 Open Folder")
        self.open_folder_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #CCCCCC;
                border: none;
                padding: 6px 12px;
                text-align: left;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #2A2D2E;
            }
        """)
        self.open_folder_btn.clicked.connect(self._on_open_folder_clicked)
        footer_layout.addWidget(self.open_folder_btn)
        
        layout.addWidget(footer_widget)
    
    def _on_open_folder_clicked(self):
        """Handle open folder button click."""
        from PyQt6.QtWidgets import QFileDialog
        path = QFileDialog.getExistingDirectory(None, "Open Folder")
        if path:
            self.set_root_path(path)
            self.file_selected.emit(path)
    
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
    
    def refresh(self):
        """Refresh the file tree."""
        self.model.setRootPath(self.model.rootPath())
    
    def collapse_all(self):
        """Collapse all items in the tree."""
        self.tree_view.collapseAll()
    
    def expand_all(self):
        """Expand all items in the tree."""
        self.tree_view.expandAll()


class Sidebar(QWidget):
    """
    Main sidebar container for the File Explorer.
    VS Code-style sidebar.
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
