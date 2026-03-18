"""
Editor Area Module for LumeIDE

Provides the tabbed code editor area with file management.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QTextEdit, QPushButton, QLabel, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor


class CodeEditor(QTextEdit):
    """
    Simple code editor widget with file tracking.
    """
    
    # Signals
    content_changed = pyqtSignal()
    cursor_changed = pyqtSignal(int, int)  # line, column
    
    def __init__(self, file_path: str = None, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.original_content = ""
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Initialize the editor UI."""
        self.setFont(QFont("Consolas", 11))
        self.setStyleSheet("""
            QTextEdit {
                background-color: #1E1E1E;
                color: #D4D4D4;
                border: none;
                padding: 4px;
            }
        """)
    
    def _connect_signals(self):
        """Connect signals."""
        self.textChanged.connect(self.content_changed.emit)
        self.cursorPositionChanged.connect(self._on_cursor_changed)
    
    def _on_cursor_changed(self):
        """Handle cursor position change."""
        cursor = self.textCursor()
        line = cursor.blockNumber() + 1
        column = cursor.columnNumber() + 1
        self.cursor_changed.emit(line, column)
    
    def load_file(self, file_path: str):
        """Load content from a file."""
        import os
        normalized = os.path.normpath(file_path)
        
        try:
            with open(normalized, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.file_path = normalized
            self.original_content = content
            self.setPlainText(content)
            return True
        except Exception as e:
            return False, str(e)
    
    def save_file(self):
        """Save content to the current file."""
        import os
        
        if not self.file_path:
            return False, "No file path set"
        
        normalized = os.path.normpath(self.file_path)
        
        try:
            with open(normalized, 'w', encoding='utf-8') as f:
                f.write(self.toPlainText())
            
            self.original_content = self.toPlainText()
            return True, None
        except Exception as e:
            return False, str(e)
    
    def is_modified(self) -> bool:
        """Check if content has been modified."""
        return self.toPlainText() != self.original_content
    
    def get_file_name(self) -> str:
        """Get the file name without path."""
        import os
        if self.file_path:
            return os.path.basename(self.file_path)
        return "Untitled"
    
    def get_file_path(self) -> str:
        """Get the full file path."""
        return self.file_path


class EditorArea(QWidget):
    """
    Tabbed editor area managing multiple open files.
    """
    
    # Signals
    file_saved = pyqtSignal(str)  # Emits file path
    tab_changed = pyqtSignal(int)  # Emits tab index
    editor_status_changed = pyqtSignal(bool)  # Emits has_modified_files
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """Initialize the editor area UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Welcome tab (default)
        self.welcome_widget = self._create_welcome_tab()
        
        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self._on_tab_close)
        self.tabs.currentChanged.connect(self._on_current_changed)
        
        # Add welcome tab initially
        self.tabs.addTab(self.welcome_widget, "Welcome")
        
        layout.addWidget(self.tabs)
    
    def _create_welcome_tab(self) -> QWidget:
        """Create the welcome screen widget."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        title = QLabel("🚀 Welcome to LumeIDE")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #4EC9B0;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("Open a folder to get started")
        subtitle.setStyleSheet("color: #888; padding: 10px;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        return widget
    
    def _on_tab_close(self, index: int):
        """Handle tab close request."""
        # Don't close the welcome tab
        if index == 0 and self.tabs.widget(0) == self.welcome_widget:
            return
        
        widget = self.tabs.widget(index)
        if isinstance(widget, CodeEditor) and widget.is_modified():
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                f"'{widget.get_file_name()}' has unsaved changes. Close anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        self.tabs.removeTab(index)
        self._check_modified_state()
    
    def _on_current_changed(self, index: int):
        """Handle tab change."""
        if index >= 0:
            self.tab_changed.emit(index)
            self._check_modified_state()
    
    def _check_modified_state(self):
        """Check if any tabs have modified content."""
        has_modified = False
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if isinstance(widget, CodeEditor) and widget.is_modified():
                has_modified = True
                break
        
        self.editor_status_changed.emit(has_modified)
    
    def open_file(self, file_path: str) -> bool:
        """Open a file in a new tab or switch to existing."""
        import os
        normalized = os.path.normpath(file_path)
        
        # Check if already open
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if isinstance(widget, CodeEditor) and widget.file_path == normalized:
                self.tabs.setCurrentIndex(i)
                return True
        
        # Create new editor
        editor = CodeEditor(normalized)
        success = editor.load_file(normalized)
        
        if not success:
            return False
        
        # Add tab
        file_name = editor.get_file_name()
        index = self.tabs.addTab(editor, file_name)
        self.tabs.setCurrentIndex(index)
        
        return True
    
    def save_current(self) -> bool:
        """Save the current tab."""
        widget = self.tabs.currentWidget()
        if isinstance(widget, CodeEditor):
            success, error = widget.save_file()
            if success:
                self.file_saved.emit(widget.file_path)
                # Update tab title
                index = self.tabs.currentIndex()
                self.tabs.setTabText(index, widget.get_file_name())
            return success
        return False
    
    def save_all(self) -> int:
        """Save all modified tabs. Returns count of saved files."""
        saved_count = 0
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if isinstance(widget, CodeEditor) and widget.is_modified():
                success, _ = widget.save_file()
                if success:
                    saved_count += 1
                    self.tabs.setTabText(i, widget.get_file_name())
                    self.file_saved.emit(widget.file_path)
        return saved_count
    
    def get_current_editor(self) -> CodeEditor:
        """Get the current editor widget."""
        widget = self.tabs.currentWidget()
        if isinstance(widget, CodeEditor):
            return widget
        return None
    
    def get_current_file(self) -> str:
        """Get the current file path."""
        editor = self.get_current_editor()
        return editor.file_path if editor else None
    
    def close_all_tabs(self, force: bool = False) -> bool:
        """Close all tabs. Returns True if successful."""
        if not force:
            for i in range(self.tabs.count() - 1, -1, -1):
                if i == 0 and self.tabs.widget(0) == self.welcome_widget:
                    continue
                self._on_tab_close(i)
        else:
            # Remove all non-welcome tabs
            while self.tabs.count() > 1:
                self.tabs.removeTab(1)
        return True
    
    def has_modified_files(self) -> bool:
        """Check if any tabs have unsaved changes."""
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if isinstance(widget, CodeEditor) and widget.is_modified():
                return True
        return False
    
    def get_open_files(self) -> list:
        """Get list of open file paths."""
        files = []
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if isinstance(widget, CodeEditor) and widget.file_path:
                files.append(widget.file_path)
        return files


# Export
__all__ = ['EditorArea', 'CodeEditor']
