"""
Sidebar Module for LumeIDE

Provides the File Explorer and Aura Chat interface.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeView, QTextEdit,
    QPushButton, QLabel, QLineEdit, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QDir
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QFileSystemModel


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


class AuraChat(QWidget):
    """
    Aura Chat interface for AI interactions.
    """
    
    # Signals
    message_sent = pyqtSignal(str)  # Emits user message
    aura_stopped = pyqtSignal()  # Emitted when Aura is stopped
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_running = False
        self._setup_ui()
    
    def _setup_ui(self):
        """Initialize the chat UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        header = QLabel("Aura Chat")
        header.setStyleSheet("""
            QLabel {
                padding: 8px;
                font-weight: bold;
                color: #4EC9B0;
                background-color: #252526;
            }
        """)
        layout.addWidget(header)
        
        # Status indicator
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #888; padding: 4px 8px;")
        layout.addWidget(self.status_label)
        
        # Chat display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: #1E1E1E;
                color: #D4D4D4;
                border: none;
                padding: 8px;
                font-family: Consolas, monospace;
            }
        """)
        layout.addWidget(self.chat_display, stretch=1)
        
        # Input area
        input_container = QWidget()
        input_layout = QVBoxLayout(input_container)
        input_layout.setContentsMargins(8, 8, 8, 8)
        
        self.message_input = QTextEdit()
        self.message_input.setPlaceholderText("Describe what you want to build...")
        self.message_input.setMaximumHeight(80)
        self.message_input.setStyleSheet("""
            QTextEdit {
                background-color: #3C3C3C;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 8px;
                color: white;
            }
        """)
        input_layout.addWidget(self.message_input)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.send_btn = QPushButton("Send to Aura")
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #0E639C;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1177BB;
            }
            QPushButton:disabled {
                background-color: #3C3C3C;
                color: #666;
            }
        """)
        self.send_btn.clicked.connect(self._on_send)
        btn_layout.addWidget(self.send_btn)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #3D1E1E;
                color: #F14C4C;
                border: 1px solid #F14C4C;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #5D2E2E;
            }
            QPushButton:disabled {
                background-color: #3C3C3C;
                color: #666;
                border-color: #555;
            }
        """)
        self.stop_btn.clicked.connect(self._on_stop)
        btn_layout.addWidget(self.stop_btn)
        
        input_layout.addLayout(btn_layout)
        layout.addWidget(input_container)
    
    def _on_send(self):
        """Handle send button click."""
        message = self.message_input.toPlainText().strip()
        if message:
            self._add_message("You", message)
            self.message_input.clear()
            self.message_sent.emit(message)
            self._set_running(True)
    
    def _on_stop(self):
        """Handle stop button click."""
        self._set_running(False)
        self._add_message("System", "Aura execution stopped.")
        self.aura_stopped.emit()
    
    def _set_running(self, running: bool):
        """Update UI state for running/stopped."""
        self._is_running = running
        self.send_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)
        self.status_label.setText("Processing..." if running else "Ready")
    
    def _add_message(self, sender: str, message: str):
        """Add a message to the chat display."""
        import datetime
        time = datetime.datetime.now().strftime("%H:%M")
        self.chat_display.append(f"[{time}] {sender}: {message}")
    
    def add_response(self, response: str):
        """Add an AI response to the chat."""
        self._add_message("Aura", response)
        self._set_running(False)
    
    def add_error(self, error: str):
        """Add an error message to the chat."""
        self._add_message("Error", error)
        self._set_running(False)
    
    def is_running(self) -> bool:
        """Check if Aura is currently running."""
        return self._is_running


class Sidebar(QWidget):
    """
    Main sidebar container combining File Explorer and Aura Chat.
    """
    
    # Forward signals from children
    file_double_clicked = pyqtSignal(str)
    message_sent = pyqtSignal(str)
    aura_stopped = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Initialize the sidebar UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Tab selector
        self.tab_selector = QComboBox()
        self.tab_selector.addItems(["Explorer", "Aura Chat"])
        self.tab_selector.setStyleSheet("""
            QComboBox {
                background-color: #2D2D2D;
                border: none;
                padding: 8px;
                color: white;
            }
        """)
        self.tab_selector.currentIndexChanged.connect(self._on_tab_changed)
        layout.addWidget(self.tab_selector)
        
        # Stacked widget for different views
        from PyQt6.QtWidgets import QStackedWidget
        self.stack = QStackedWidget()
        
        self.explorer = FileExplorer()
        self.aura_chat = AuraChat()
        
        self.stack.addWidget(self.explorer)
        self.stack.addWidget(self.aura_chat)
        
        layout.addWidget(self.stack)
    
    def _connect_signals(self):
        """Connect child signals to parent."""
        self.explorer.file_double_clicked.connect(self.file_double_clicked)
        self.aura_chat.message_sent.connect(self.message_sent)
        self.aura_chat.aura_stopped.connect(self.aura_stopped)
    
    def _on_tab_changed(self, index: int):
        """Handle tab selector change."""
        self.stack.setCurrentIndex(index)
    
    def set_root_path(self, path: str):
        """Set the root path for the file explorer."""
        self.explorer.set_root_path(path)
    
    def add_response(self, response: str):
        """Add an Aura response to chat."""
        self.aura_chat.add_response(response)
    
    def add_error(self, error: str):
        """Add an error to chat."""
        self.aura_chat.add_error(error)
    
    def is_aura_running(self) -> bool:
        """Check if Aura is running."""
        return self.aura_chat.is_running()
    
    def stop_aura(self):
        """Stop Aura execution."""
        if self.aura_chat.is_running():
            self.aura_chat._on_stop()


# Export
__all__ = ['Sidebar', 'FileExplorer', 'AuraChat']
