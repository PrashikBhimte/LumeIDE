"""
Bottom Panel Module for LumeIDE

Provides the Unified Shell and Log Viewer panels.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QTabWidget, QPushButton, QLabel, QComboBox, QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

from app.engine.dispatcher import CommandDispatcher


class UnifiedShell(QWidget):
    """
    A unified shell for both commands and natural language queries.
    """

    def __init__(self, command_dispatcher: CommandDispatcher, parent=None):
        super().__init__(parent)
        self.command_dispatcher = command_dispatcher
        self._setup_ui()

    def _setup_ui(self):
        """Initialize the unified shell UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.output_view = QTextEdit()
        self.output_view.setFont(QFont("Consolas", 10))
        self.output_view.setReadOnly(True)
        self.output_view.setStyleSheet("""
            QTextEdit {
                background-color: #1E1E1E;
                color: #D4D4D4;
                border: none;
                padding: 8px;
            }
        """)

        self.input_line = QLineEdit()
        self.input_line.setFont(QFont("Consolas", 10))
        self.input_line.setStyleSheet("""
            QLineEdit {
                background-color: #252526;
                color: #D4D4D4;
                border: 1px solid #333;
                padding: 4px 8px;
            }
        """)
        self.input_line.setPlaceholderText("Enter a command or ask Aura...")
        self.input_line.returnPressed.connect(self._on_command_entered)
        
        layout.addWidget(self.output_view)
        layout.addWidget(self.input_line)

    def _on_command_entered(self):
        """Handle command entry."""
        command = self.input_line.text()
        if not command:
            return

        self.input_line.clear()
        self.append_output(f"> {command}", "gray")

        output, color = self.command_dispatcher.dispatch(command)
        self.append_output(output, color)

    def append_output(self, text: str, color: str = None):
        """Append text to the output view with optional color."""
        color_map = {
            "green": "#4EC9B0",  # Terminal output
            "blue": "#569CD6",   # Aura response
            "red": "#F14C4C",    # Errors
            "gray": "#888888"    # Command echo
        }
        
        if color and color.startswith("#"):
            hex_color = color
        else:
            hex_color = color_map.get(color, "#D4D4D4") # Default to standard text color
        
        # Pre-wrap to avoid long lines
        formatted_text = f'<pre style="white-space: pre-wrap; margin: 0; font-family: Consolas, monospace;">{text}</pre>'

        self.output_view.append(f'<div style="color: {hex_color};">{formatted_text}</div>')
        self.output_view.verticalScrollBar().setValue(self.output_view.verticalScrollBar().maximum())

    def clear_output(self):
        """Clear the output view."""
        self.output_view.clear()


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
    Bottom panel containing Unified Shell and Log Viewer tabs.
    """
    
    # Signals
    command_executed = pyqtSignal(str)  # Emits command
    
    def __init__(self, command_dispatcher: CommandDispatcher, parent=None):
        super().__init__(parent)
        self.command_dispatcher = command_dispatcher
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
        
        # Unified Shell tab
        self.shell = UnifiedShell(self.command_dispatcher)
        
        # Log Viewer tab
        self.log_viewer = LogViewer()
        
        # Add tabs
        self.tabs.addTab(self.shell, "Unified Shell")
        self.tabs.addTab(self.log_viewer, "Log Viewer")
        
        layout.addWidget(self.tabs)
    
    def append_output(self, text: str, color: str = None):
        """Append output to the shell."""
        self.shell.append_output(text, color)
    
    def clear_shell(self):
        """Clear shell output."""
        self.shell.clear_output()
    
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
    
    def show_shell(self):
        """Show the shell tab."""
        self.tabs.setCurrentIndex(0)
    
    def show_log_viewer(self):
        """Show the log viewer tab."""
        self.tabs.setCurrentIndex(1)


# Export
__all__ = ['BottomPanel', 'UnifiedShell', 'LogViewer']
