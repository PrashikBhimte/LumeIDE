
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QTextEdit, QPushButton, QLabel, QMessageBox, QPlainTextEdit, QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QRect, QEvent
from PyQt6.QtGui import (
    QFont, QTextCursor, QColor, QTextFormat, QPainter, QPalette, QTextDocument
)

from app.ui.syntax_highlighter import SyntaxHighlighter


class SearchBar(QWidget):
    search_requested = pyqtSignal(str, bool)
    replace_requested = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search...")
        self.search_input.returnPressed.connect(self.search_next)
        layout.addWidget(self.search_input)

        self.next_button = QPushButton("Next")
        self.next_button.clicked.connect(self.search_next)
        layout.addWidget(self.next_button)

        self.prev_button = QPushButton("Previous")
        self.prev_button.clicked.connect(self.search_prev)
        layout.addWidget(self.prev_button)

        self.close_button = QPushButton("×")
        self.close_button.clicked.connect(self.hide)
        layout.addWidget(self.close_button)

    def search_next(self):
        text = self.search_input.text()
        if text:
            self.search_requested.emit(text, True)

    def search_prev(self):
        text = self.search_input.text()
        if text:
            self.search_requested.emit(text, False)


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.editor.lineNumberAreaPaintEvent(event)


class CodeEditor(QPlainTextEdit):
    """
    Simple code editor widget with file tracking and syntax highlighting.
    """
    
    # Signals
    content_changed = pyqtSignal()
    cursor_changed = pyqtSignal(int, int)  # line, column
    
    def __init__(self, file_path: str = None, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.original_content = ""
        self.lineNumberArea = LineNumberArea(self)
        self._setup_ui()
        self._connect_signals()
        self.updateLineNumberAreaWidth(0)
        
        # Setup syntax highlighter
        self.highlighter = SyntaxHighlighter(self.document())
        if file_path:
            self.highlighter.set_file_path(file_path)

    def _setup_ui(self):
        """Initialize the editor UI."""
        self.setFont(QFont("Cascadia Code", 11))
        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1E1E1E;
                color: #D4D4D4;
                border: none;
                padding: 4px;
                selection-background-color: #264F78;
            }
            QPlainTextEdit:focus {
                border: none;
            }
        """)
    
    def _connect_signals(self):
        """Connect signals."""
        self.textChanged.connect(self.content_changed.emit)
        self.cursorPositionChanged.connect(self._on_cursor_changed)
        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)

    def _on_cursor_changed(self):
        """Handle cursor position change."""
        cursor = self.textCursor()
        line = cursor.blockNumber() + 1
        column = cursor.columnNumber() + 1
        self.cursor_changed.emit(line, column)
        self.highlightCurrentLine()

    def highlightCurrentLine(self):
        extraSelections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            lineColor = QColor("#283457")
            selection.format.setBackground(lineColor)
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extraSelections.append(selection)
        self.setExtraSelections(extraSelections)

    def search(self, text, forward=True):
        find_flags = QTextDocument.FindFlag()
        if not forward:
            find_flags |= QTextDocument.FindFlag.FindBackward

        found = self.find(text, find_flags)

        if not found:
            # Wrap search
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start if forward else QTextCursor.MoveOperation.End)
            self.setTextCursor(cursor)
            self.find(text, find_flags)

    def lineNumberAreaWidth(self):
        digits = 1
        max_val = max(1, self.blockCount())
        while max_val >= 10:
            max_val /= 10
            digits += 1
        space = 3 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def updateLineNumberAreaWidth(self, _):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect, dy):
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), QColor("#1E1E1E"))  # Line number background (VS Code style)
        
        # VS Code uses slightly different colors for active line number
        is_active = True  # Simplified - you could check if this is the current block
        
        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        
        cursor_block = self.textCursor().blockNumber()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                
                # VS Code style: active line number is brighter
                if blockNumber == cursor_block:
                    painter.setPen(QColor("#C6C6C6"))  # Active line number
                else:
                    painter.setPen(QColor("#858585"))   # Inactive line number
                    
                painter.drawText(0, int(top), self.lineNumberArea.width(), self.fontMetrics().height(),
                                 Qt.AlignmentFlag.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            blockNumber += 1

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
            
            # Update syntax highlighter based on file type
            self.highlighter.set_file_path(normalized)
            
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
    file_saved = pyqtSignal(str)
    tab_changed = pyqtSignal(int)
    editor_status_changed = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.installEventFilter(self)

    def eventFilter(self, source, event):
        if (event.type() == QEvent.Type.KeyPress and
                event.key() == Qt.Key.Key_F and
                event.modifiers() == Qt.KeyboardModifier.ControlModifier):
            self.toggle_search_bar()
            return True
        return super().eventFilter(source, event)

    def _setup_ui(self):
        """Initialize the editor area UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.search_bar = SearchBar(self)
        self.search_bar.hide()
        self.search_bar.search_requested.connect(self.on_search_requested)
        layout.addWidget(self.search_bar)
        
        self.welcome_widget = self._create_welcome_tab()
        
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self._on_tab_close)
        self.tabs.currentChanged.connect(self._on_current_changed)
        
        # VS Code-style tab bar
        self.tabs.setStyleSheet("""
            QTabBar::tab {
                background-color: #2D2D2D;
                color: #CCCCCC;
                border: none;
                padding: 8px 12px;
                margin: 0px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:!selected {
                background-color: #252526;
                color: #969696;
                border-bottom: 1px solid #2D2D2D;
            }
            QTabBar::tab:selected {
                background-color: #1E1E1E;
                color: #FFFFFF;
                border-bottom: 1px solid #1E1E1E;
            }
            QTabBar::tab:hover:!selected {
                background-color: #2A2A2A;
                color: #CCCCCC;
            }
            QTabBar::tab:first {
                border-top-left-radius: 0px;
            }
            QTabWidget::pane {
                border: 1px solid #1E1E1E;
                background-color: #1E1E1E;
            }
            QTabWidget {
                background-color: #1E1E1E;
            }
        """)
        
        self.tabs.addTab(self.welcome_widget, "Welcome")
        layout.addWidget(self.tabs)
    
    def _create_welcome_tab(self) -> QWidget:
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

    def toggle_search_bar(self):
        if self.search_bar.isVisible():
            self.search_bar.hide()
        else:
            self.search_bar.show()
            self.search_bar.search_input.setFocus()

    def on_search_requested(self, text, forward):
        editor = self.get_current_editor()
        if editor:
            editor.search(text, forward)

    def _on_tab_close(self, index: int):
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
        if index >= 0:
            self.tab_changed.emit(index)
            self._check_modified_state()
    
    def _check_modified_state(self):
        has_modified = False
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if isinstance(widget, CodeEditor) and widget.is_modified():
                has_modified = True
                break
        self.editor_status_changed.emit(has_modified)
    
    def open_file(self, file_path: str) -> bool:
        import os
        normalized = os.path.normpath(file_path)
        
        # Check if file is already open
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if isinstance(widget, CodeEditor) and widget.file_path == normalized:
                self.tabs.setCurrentIndex(i)
                return True
        
        editor = CodeEditor(normalized)
        success = editor.load_file(normalized)
        if not success:
            return False
        
        # Show modified indicator if file was modified externally
        file_name = editor.get_file_name()
        index = self.tabs.addTab(editor, file_name)
        self.tabs.setCurrentIndex(index)
        
        # Remove welcome tab when opening first file
        if self.tabs.widget(0) == self.welcome_widget:
            self.tabs.removeTab(0)

        return True
    
    def save_current(self) -> bool:
        widget = self.tabs.currentWidget()
        if isinstance(widget, CodeEditor):
            success, error = widget.save_file()
            if success:
                self.file_saved.emit(widget.file_path)
                index = self.tabs.currentIndex()
                # Update tab text (remove * if present)
                self.tabs.setTabText(index, widget.get_file_name())
            return success
        return False
    
    def save_all(self) -> int:
        saved_count = 0
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if isinstance(widget, CodeEditor) and widget.is_modified():
                if widget.save_file()[0]:
                    saved_count += 1
                    self.tabs.setTabText(i, widget.get_file_name())
                    self.file_saved.emit(widget.file_path)
        return saved_count
    
    def get_current_editor(self) -> CodeEditor:
        widget = self.tabs.currentWidget()
        return widget if isinstance(widget, CodeEditor) else None
    
    def get_current_file(self) -> str:
        editor = self.get_current_editor()
        return editor.file_path if editor else None
    
    def close_all_tabs(self, force: bool = False) -> bool:
        can_close = True
        if not force:
            for i in range(self.tabs.count() - 1, -1, -1):
                self._on_tab_close(i)
                if self.tabs.count() > 1 and i > 0: # check if tab is still there
                     can_close = False
        
        if can_close:
            while self.tabs.count() > 1:
                self.tabs.removeTab(1)
        
        return can_close
    
    def has_modified_files(self) -> bool:
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if isinstance(widget, CodeEditor) and widget.is_modified():
                return True
        return False
    
    def get_open_files(self) -> list:
        files = []
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if isinstance(widget, CodeEditor) and widget.file_path:
                files.append(widget.file_path)
        return files


# Export
__all__ = ['EditorArea', 'CodeEditor']
