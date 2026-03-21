"""
Bottom Panel Module for LumeIDE

Provides the Unified Shell and Log Viewer panels.
The unified shell uses a "lume>" prompt for both terminal commands and AI chat.
"""

import re
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QTabWidget, QPushButton, QLabel, QComboBox, QLineEdit, QScrollBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QProcess, QEvent
from PyQt6.QtGui import QFont, QTextCursor, QColor, QTextCharFormat, QKeyEvent

import mistune

from app.engine.dispatcher import CommandDispatcher

# Terminal colors (VS Code integrated terminal style)
TERMINAL_COLORS = {
    'background': '#1E1E1E',
    'prompt': '#CCCCCC',          # White prompt
    'command': '#D4D4D4',         # Command text
    'output': '#9CDCFE',          # Light blue output
    'error': '#F14C4C',           # Red errors
    'success': '#4EC9B0',         # Teal success
    'warning': '#CCA700',         # Yellow warnings
    'ai_prefix': '#C586C0',       # Purple for AI
    'ai_response': '#D4D4D4',      # AI response text
    'path': '#CE9178',            # Orange paths
}

# Commands that should be treated as shell commands
SHELL_COMMANDS = {
    # Navigation
    'cd', 'pwd', 'ls', 'dir', 'mkdir', 'rmdir', 'rm', 'del', 'copy', 'cp', 'move', 'mv',
    # File operations
    'cat', 'type', 'head', 'tail', 'grep', 'find', 'touch', 'chmod', 'chown',
    # Git
    'git', 'gh',
    # Python
    'python', 'python3', 'pip', 'pip3', 'conda', 'uv',
    # Package managers
    'npm', 'yarn', 'pnpm', 'bun', 'cargo', 'go', 'mvn', 'gradle', 'make', 'cmake',
    # Development
    'code', 'vim', 'nano', 'emacs', 'ssh', 'scp', 'rsync',
    # System
    'echo', 'export', 'env', 'set', 'unset', 'alias', 'unalias', 'which', 'where',
    'kill', 'ps', 'top', 'htop', 'systeminfo', 'tasklist',
    # Network
    'curl', 'wget', 'ping', 'netstat', 'ipconfig', 'ifconfig', 'nslookup', 'dig',
    # Archive
    'zip', 'unzip', 'tar', 'gzip', 'gunzip', '7z',
    # Other
    'clear', 'cls', 'history', 'man', 'help', 'exit', 'quit'
}


class CodeBlockRenderer(mistune.HTMLRenderer):
    def block_code(self, code, lang=None):
        return f'<pre style="background-color: #2E3440; color: #D8DEE9; padding: 10px; border-radius: 4px; font-family: Cascadia Code, Consolas, monospace;"><code>{mistune.escape(code)}</code></pre>'


class UnifiedShell(QWidget):
    """
    A unified shell for both terminal commands and natural language queries.
    Uses "lume>" prompt prefix for all input.
    """

    def __init__(self, command_dispatcher: CommandDispatcher, project_path=None, parent=None):
        super().__init__(parent)
        self.command_dispatcher = command_dispatcher
        self.project_path = project_path or os.getcwd()
        self._is_running = False
        self._current_prompt = self._get_prompt()
        self._setup_ui()

    def _get_prompt(self) -> str:
        """Get the current prompt with working directory."""
        # Get shortened path (last 2 segments)
        path = self.project_path
        parts = path.replace('\\', '/').split('/')
        if len(parts) > 2:
            short_path = '/'.join(parts[-2:])
        else:
            short_path = path.replace('\\', '/').split('/')[-1] or path
        
        return f"lume:{short_path}> "

    def set_project_path(self, path: str):
        """Update the project path for the prompt."""
        self.project_path = path
        self._update_prompt()

    def _update_prompt(self):
        """Update the prompt display."""
        self._current_prompt = self._get_prompt()
        self._update_input_style()

    def _setup_ui(self):
        """Initialize the unified shell UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Output view
        self.output_view = QTextEdit()
        self.output_view.setReadOnly(True)
        self.output_view.setFont(QFont("Cascadia Code", 11))
        self.output_view.setStyleSheet("""
            QTextEdit {
                background-color: #1E1E1E;
                color: #D4D4D4;
                border: none;
                padding: 8px;
                font-family: 'Cascadia Code', 'Consolas', monospace;
            }
        """)
        layout.addWidget(self.output_view, stretch=1)

        # Input area
        input_container = QWidget()
        input_container.setStyleSheet("""
            background-color: #252526;
            border-top: 1px solid #3C3C3C;
        """)
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(8, 8, 8, 8)
        input_layout.setSpacing(4)

        # Prompt label
        self.prompt_label = QLabel(self._current_prompt)
        self.prompt_label.setFont(QFont("Cascadia Code", 11))
        self.prompt_label.setStyleSheet(f"""
            QLabel {{
                color: {TERMINAL_COLORS['success']};
                background-color: transparent;
                padding: 0;
            }}
        """)
        input_layout.addWidget(self.prompt_label)

        # Input line
        self.input_line = QLineEdit()
        self.input_line.setFont(QFont("Cascadia Code", 11))
        self.input_line.setPlaceholderText("Type a command or ask Aura...")
        self.input_line.returnPressed.connect(self._on_command_entered)
        self.input_line.textChanged.connect(self._on_text_changed)
        self.input_line.setStyleSheet("""
            QLineEdit {
                border: none;
                background-color: transparent;
                color: #D4D4D4;
                padding: 0px;
                selection-background-color: #264F78;
            }
            QLineEdit:focus {
                border: none;
            }
        """)
        self.input_line.installEventFilter(self)
        input_layout.addWidget(self.input_line, stretch=1)

        layout.addWidget(input_container)
        
        # Initial prompt
        self._append_welcome()

    def eventFilter(self, obj, event):
        """Handle up/down arrow keys for command history."""
        if obj == self.input_line and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Up:
                self._navigate_history(-1)
                return True
            elif event.key() == Qt.Key.Key_Down:
                self._navigate_history(1)
                return True
        return super().eventFilter(obj, event)

    def _append_welcome(self):
        """Append welcome message."""
        welcome = f"""<pre style="color: {TERMINAL_COLORS['success']};">
╔══════════════════════════════════════════════════════════════╗
║                    Welcome to Lume IDE                      ║
║                                                              ║
║  Terminal Commands: Run shell commands directly              ║
║  Natural Language: Ask questions or request code changes     ║
║                                                              ║
║  Examples:                                                  ║
║    lume> python script.py      # Run Python script          ║
║    lume> git status            # Run git command             ║
║    lume> explain this code     # Ask AI to explain          ║
║    lume> fix the bug in main   # Ask AI to fix code         ║
╚══════════════════════════════════════════════════════════════╝
</pre>"""
        self.output_view.append(welcome)

    def _update_input_style(self):
        """Update prompt label."""
        self.prompt_label.setText(self._current_prompt)

    def _on_text_changed(self, text: str):
        """Handle text changes to provide visual hints."""
        pass  # Could add autocomplete here

    def _is_shell_command(self, text: str) -> bool:
        """Determine if the input is a shell command vs natural language."""
        text = text.strip()
        
        # Empty check
        if not text:
            return False
        
        # Check if first word is a known shell command
        first_word = text.split()[0].lower()
        if first_word in SHELL_COMMANDS:
            return True
        
        # Check for command patterns
        command_patterns = [
            r'^(cd|pwd|ls|dir)\s',  # Navigation
            r'^(python|py|pip|npm|yarn)\s',  # Executables
            r'^(git|gh)\s',  # Git
            r'^(mkdir|rm|cp|mv|rmdir|rm)\s',  # File ops
            r'^[a-zA-Z]:\\',  # Windows paths
            r'^/',  # Unix paths
            r'^\.\.?/',  # Relative paths
            r'^\$',  # Variables
            r'^export\s',  # Environment
            r'^source\s',
            r'^sudo\s',
        ]
        
        for pattern in command_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return True
        
        return False

    def _navigate_history(self, direction: int):
        """Navigate command history with up/down arrows."""
        if not hasattr(self, '_command_history'):
            self._command_history = []
        if not hasattr(self, '_history_index'):
            self._history_index = -1
        
        history = self._command_history
        if not history:
            return
        
        # Update index
        new_index = self._history_index + direction
        
        if direction > 0:  # Down
            if new_index >= len(history):
                self._history_index = len(history)
                self.input_line.setText("")
            elif new_index >= 0:
                self._history_index = new_index
                self.input_line.setText(history[new_index])
        else:  # Up
            if new_index < 0:
                new_index = 0
            if new_index < len(history):
                self._history_index = new_index
                self.input_line.setText(history[new_index])

    def _on_command_entered(self):
        """Handle command entry."""
        if self._is_running:
            return

        command = self.input_line.text()
        if not command.strip():
            self._append_prompt_line()
            return

        # Add to history
        if not hasattr(self, '_command_history'):
            self._command_history = []
        if command != (self._command_history[-1] if self._command_history else ""):
            self._command_history.append(command)
        self._history_index = len(self._command_history)

        # Display command with prompt
        self._append_command(command)
        self.input_line.clear()

        # Determine if shell or AI command
        if self._is_shell_command(command):
            self._run_shell_command(command)
        else:
            self._run_ai_command(command)

    def _append_command(self, command: str):
        """Append a command to the output view."""
        # Command with prompt styling
        html = f'''<span style="color: {TERMINAL_COLORS['success']};">{self._current_prompt}</span>'''
        html += f'<span style="color: {TERMINAL_COLORS['command']};">{self._escape_html(command)}</span><br/>'
        self.output_view.append(html)
        self._scroll_to_bottom()

    def _append_prompt_line(self):
        """Append an empty prompt line."""
        html = f'<span style="color: {TERMINAL_COLORS['success']};">{self._current_prompt}</span>'
        self.output_view.append(html)
        self._scroll_to_bottom()

    def _append_output(self, text: str, color: str = None):
        """Append output text."""
        if color:
            color_hex = TERMINAL_COLORS.get(color, color) if isinstance(color, str) else color
        else:
            color_hex = TERMINAL_COLORS['output']
        
        html = f'<span style="color: {color_hex}; font-family: Cascadia Code, Consolas, monospace;">{self._escape_html(text)}</span><br/>'
        self.output_view.append(html)
        self._scroll_to_bottom()

    def _append_ai_response(self, text: str):
        """Append AI response with markdown rendering."""
        renderer = CodeBlockRenderer()
        markdown = mistune.create_markdown(renderer=renderer)
        html = markdown(text)
        
        # Wrap in a styled container
        styled_html = f'''
        <div style="background-color: #252526; padding: 10px; border-radius: 4px; margin: 5px 0;">
            <span style="color: {TERMINAL_COLORS['ai_prefix']};">✨ Aura: </span>
            <div style="margin-top: 8px; color: {TERMINAL_COLORS['ai_response']};">
                {html}
            </div>
        </div>
        '''
        self.output_view.append(styled_html)
        self._scroll_to_bottom()

    def _append_error(self, text: str):
        """Append error text."""
        self._append_output(text, 'error')

    def _append_success(self, text: str):
        """Append success text."""
        self._append_output(text, 'success')

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        return (text
                .replace('&', '&')
                .replace('<', '<')
                .replace('>', '>')
                .replace('"', '"')
                .replace("'", '&#39;'))

    def _scroll_to_bottom(self):
        """Scroll output to bottom."""
        scrollbar = self.output_view.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _run_shell_command(self, command: str):
        """Run a shell command directly."""
        self._is_running = True
        self.input_line.setEnabled(False)
        
        # Update prompt to show running state
        original_prompt = self._current_prompt
        self._append_output("Running...", 'warning')
        
        # Run command via dispatcher
        result = self.command_dispatcher.dispatch(command)
        
        self._is_running = False
        self.input_line.setEnabled(True)
        self.input_line.setFocus()
        
        if result:
            output, color = result
            if color == 'error' or 'Error' in output:
                self._append_error(output)
            else:
                self._append_output(output, color)
        else:
            # Asynchronous result - handled by signals
            pass
        
        self._append_prompt_line()

    def _run_ai_command(self, command: str):
        """Route command to AI for natural language processing."""
        self._is_running = True
        self.input_line.setEnabled(False)
        
        # Show thinking indicator
        self._append_output("✨ Thinking...", 'ai_prefix')
        
        # Route to Aura via dispatcher
        self.command_dispatcher.dispatch(command)

    def on_aura_started_thinking(self):
        """Called when Aura starts thinking."""
        self._is_running = True
        self.input_line.setEnabled(False)

    def on_aura_tool_used(self, tool_name: str, tool_args: dict):
        """Called when Aura uses a tool."""
        self._append_output(f"[Tool] {tool_name}: {tool_args}", 'warning')

    def on_aura_finished(self, result: str):
        """Called when Aura finishes generating."""
        if result:
            # Clean up thinking message
            cursor = self.output_view.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            # Remove the "Thinking..." line
            # For simplicity, just append the response
            self._append_ai_response(result)
        else:
            self._append_error("Aura failed to generate a response.")
        
        self._is_running = False
        self.input_line.setEnabled(True)
        self.input_line.setFocus()
        self._append_prompt_line()

    def on_aura_error(self, error: str):
        """Called when Aura encounters an error."""
        self._append_error(f"Aura Error: {error}")
        self._is_running = False
        self.input_line.setEnabled(True)
        self.input_line.setFocus()
        self._append_prompt_line()

    def append_output(self, text: str, color: str = None):
        """Append raw output (for external use)."""
        self._append_output(text, color)

    def clear_output(self):
        """Clear the output view."""
        self.output_view.clear()
        self._append_prompt_line()

    def focus_input(self):
        """Focus the input line."""
        self.input_line.setFocus()


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
        self.setFont(QFont("Cascadia Code", 10))
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
    
    def __init__(self, command_dispatcher: CommandDispatcher, project_path=None, parent=None):
        super().__init__(parent)
        self.command_dispatcher = command_dispatcher
        self.project_path = project_path
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
                background-color: #1E1E1E;
            }
            QTabBar::tab {
                background-color: #252526;
                color: #969696;
                padding: 6px 16px;
                border: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #1E1E1E;
                color: #CCCCCC;
            }
            QTabBar::tab:hover:!selected {
                background-color: #2D2D2D;
                color: #CCCCCC;
            }
        """)
        
        # Unified Shell tab
        self.shell = UnifiedShell(self.command_dispatcher, self.project_path)
        
        # Log Viewer tab
        self.log_viewer = LogViewer()
        
        # Add tabs
        self.tabs.addTab(self.shell, "Terminal")
        self.tabs.addTab(self.log_viewer, "Logs")
        
        layout.addWidget(self.tabs)
    
    def set_project_path(self, path: str):
        """Update the project path for the shell prompt."""
        self.project_path = path
        self.shell.set_project_path(path)
    
    def append_output(self, text: str, color: str = None):
        """Append output to the shell."""
        self.shell.append_output(text, color)
    
    def clear_shell(self):
        """Clear shell output."""
        self.shell.clear_output()
    
    def log_request(self, data: dict):
        """Log a request to Log Viewer."""
        self.log_viewer.log_request(data)
        # Optionally switch to log viewer tab
        # self.tabs.setCurrentIndex(1)
    
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
__all__ = ['BottomPanel', 'UnifiedShell', 'LogViewer', 'TERMINAL_COLORS']
