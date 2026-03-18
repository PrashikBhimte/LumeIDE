"""
Bottom Panel Module for LumeIDE

Provides the Terminal and Log Viewer panels.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QTabWidget, QPushButton, QLabel, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont


class TerminalOutput(QTextEdit):
    """
    Terminal output widget with command history.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """Initialize the terminal UI."""
        self.setFont(QFont("Consolas", 10))
        self.setReadOnly(True)
        self.setStyleSheet("""
            QTextEdit {
                background-color: #1E1E1E;
                color: #D4D4D4;
                border: none;
                padding: 8px;
            }
        """)
    
    def append_output(self, text: str, color: str = None):
        """Append text to terminal with optional color."""
        if color:
            self.append(f'<span style="color: {color};">{text}</span>')
        else:
            self.append(text)
    
    def append_command(self, command: str):
        """Append a command with prompt."""
        self.append(f'<span style="color: #4EC9B0;">$ {command}</span>')
    
    def append_error(self, error: str):
        """Append an error message."""
        self.append(f'<span style="color: #F14C4C;">Error: {error}</span>')
    
    def append_success(self, text: str):
        """Append a success message."""
        self.append(f'<span style="color: #4EC9B0;">{text}</span>')
    
    def clear_output(self):
        """Clear terminal output."""
        self.clear()


class LogViewer(QTextEdit):
    """
    Log viewer for streaming raw JSON requests/responses.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._log_entries = []
        self._max_entries = 1000
    
    def _setup_ui(self):
        """Initialize the log viewer UI."""
        self.setFont(QFont("Consolas", 9))
        self.setReadOnly(True)
        self.setStyleSheet("""
            QTextEdit {
                background-color: #0D0D0D;
                color: #AAAAAA;
                border: none;
                padding: 4px;
            }
        """)
    
    def log_request(self, data: dict):
        """Log a request."""
        import json
        self._add_entry("REQUEST", json.dumps(data, indent=2))
    
    def log_response(self, data: dict):
        """Log a response."""
        import json
        self._add_entry("RESPONSE", json.dumps(data, indent=2))
    
    def log_raw(self, text: str):
        """Log raw text."""
        self._add_entry("LOG", text)
    
    def _add_entry(self, prefix: str, content: str):
        """Add a log entry."""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        entry = {
            'timestamp': timestamp,
            'type': prefix,
            'content': content
        }
        
        self._log_entries.append(entry)
        
        # Trim if exceeds max
        if len(self._log_entries) > self._max_entries:
            self._log_entries.pop(0)
        
        # Update display
        self._refresh_display()
    
    def _refresh_display(self):
        """Refresh the log display."""
        self.clear()
        
        colors = {
            'REQUEST': '#0E639C',   # Blue
            'RESPONSE': '#4EC9B0',  # Green
            'LOG': '#AAAAAA',        # Gray
        }
        
        for entry in self._log_entries[-100:]:  # Show last 100 entries
            color = colors.get(entry['type'], '#AAAAAA')
            self.append(
                f'<span style="color: #666;">[{entry["timestamp"]}]</span> '
                f'<span style="color: {color}; font-weight: bold;">[{entry["type"]}]</span>'
            )
            
            # First line of content
            lines = entry['content'].split('\n')
            if lines:
                self.append(f'<span style="color: #888;">{lines[0]}</span>')
                if len(lines) > 1:
                    self.append(f'<span style="color: #555;">  ... {len(lines)-1} more lines</span>')
    
    def clear_logs(self):
        """Clear all log entries."""
        self._log_entries.clear()
        self.clear()
    
    def export_logs(self) -> str:
        """Export logs as formatted text."""
        import json
        lines = []
        for entry in self._log_entries:
            lines.append(f"[{entry['timestamp']}] [{entry['type']}]")
            lines.append(entry['content'])
            lines.append("")
        return "\n".join(lines)


class BottomPanel(QWidget):
    """
    Bottom panel containing Terminal and Log Viewer tabs.
    """
    
    # Signals
    command_executed = pyqtSignal(str)  # Emits command
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """Initialize the bottom panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Tab widget for different panels
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
            }
            QTabBar::tab {
                background-color: #252526;
                color: #888;
                padding: 6px 12px;
                border: none;
            }
            QTabBar::tab:selected {
                background-color: #1E1E1E;
                color: white;
            }
            QTabBar::tab:hover {
                background-color: #2D2D2D;
            }
        """)
        
        # Terminal tab
        self.terminal = TerminalOutput()
        terminal_container = QWidget()
        terminal_layout = QVBoxLayout(terminal_container)
        terminal_layout.setContentsMargins(0, 0, 0, 0)
        terminal_layout.addWidget(self.terminal)
        
        # Log Viewer tab
        self.log_viewer = LogViewer()
        log_container = QWidget()
        log_layout = QVBoxLayout(log_container)
        log_layout.setContentsMargins(0, 0, 0, 0)
        log_layout.addWidget(self.log_viewer)
        
        # Add tabs
        self.tabs.addTab(terminal_container, "Terminal")
        self.tabs.addTab(log_container, "Log Viewer")
        
        layout.addWidget(self.tabs)
    
    def append_terminal_output(self, text: str, color: str = None):
        """Append output to terminal."""
        self.terminal.append_output(text, color)
    
    def append_command(self, command: str):
        """Append a command to terminal."""
        self.terminal.append_command(command)
    
    def append_error(self, error: str):
        """Append an error to terminal."""
        self.terminal.append_error(error)
    
    def append_success(self, text: str):
        """Append success message to terminal."""
        self.terminal.append_success(text)
    
    def clear_terminal(self):
        """Clear terminal output."""
        self.terminal.clear_output()
    
    def log_request(self, data: dict):
        """Log a request to Log Viewer."""
        self.log_viewer.log_request(data)
        # Switch to log viewer tab
        self.tabs.setCurrentIndex(1)
    
    def log_response(self, data: dict):
        """Log a response to Log Viewer."""
        self.log_viewer.log_response(data)
    
    def log_raw(self, text: str):
        """Log raw text to Log Viewer."""
        self.log_viewer.log_raw(text)
    
    def clear_logs(self):
        """Clear log viewer."""
        self.log_viewer.clear_logs()
    
    def show_terminal(self):
        """Show the terminal tab."""
        self.tabs.setCurrentIndex(0)
    
    def show_log_viewer(self):
        """Show the log viewer tab."""
        self.tabs.setCurrentIndex(1)


# Export
__all__ = ['BottomPanel', 'TerminalOutput', 'LogViewer']
