"""
Diff Preview Window for LumeIDE

This module provides a professional overlay/window for previewing and approving
code changes before they are saved to disk.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QLabel, QScrollArea, QWidget, QGroupBox, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QTextCharFormat, QSyntaxHighlighter, QTextDocument
import difflib


class DiffHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for diff output"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._diff_formatting = {}
    
    def highlightBlock(self, text):
        if text.startswith('+') and not text.startswith('+++'):
            format = QTextCharFormat()
            format.setForeground(QColor("#4EC9B0"))  # Green for additions
            format.setBackground(QColor("#1E3D2F"))
            self.setFormat(0, len(text), format)
        elif text.startswith('-') and not text.startswith('---'):
            format = QTextCharFormat()
            format.setForeground(QColor("#F14C4C"))  # Red for deletions
            format.setBackground(QColor("#3D1E1E"))
            self.setFormat(0, len(text), format)
        elif text.startswith('@@'):
            format = QTextCharFormat()
            format.setForeground(QColor("#CCA700"))  # Yellow for metadata
            format.setFontWeight(QFont.Weight.Bold)
            self.setFormat(0, len(text), format)


class DiffPreviewWindow(QDialog):
    """
    A professional dialog window that shows code changes before saving.
    Allows users to review diffs and approve/reject modifications.
    """
    
    # Signals
    approved = pyqtSignal(str, str)  # Emits (file_path, approved_content)
    rejected = pyqtSignal(str)  # Emits (file_path)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Code Changes Preview")
        self.setMinimumSize(900, 600)
        self._file_path = None
        self._original_content = None
        self._new_content = None
        self._pending_changes = []
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Initialize the UI components"""
        layout = QVBoxLayout(self)
        
        # Header with file info
        header_layout = QHBoxLayout()
        self.file_label = QLabel("File: ")
        self.file_label.setStyleSheet("font-weight: bold; color: #4EC9B0;")
        header_layout.addWidget(self.file_label)
        
        self.change_count_label = QLabel("0 changes")
        self.change_count_label.setStyleSheet("color: #888;")
        header_layout.addWidget(self.change_count_label)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Diff view in scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #3C3C3C;
                border-radius: 4px;
                background-color: #1E1E1E;
            }
        """)
        
        self.diff_container = QWidget()
        self.diff_layout = QVBoxLayout(self.diff_container)
        self.diff_layout.setContentsMargins(10, 10, 10, 10)
        self.diff_layout.setSpacing(0)
        
        scroll.setWidget(self.diff_container)
        layout.addWidget(scroll, 1)
        
        # Stats group
        stats_group = QGroupBox("Change Statistics")
        stats_layout = QHBoxLayout()
        
        self.additions_label = QLabel("➕ Additions: 0")
        self.additions_label.setStyleSheet("color: #4EC9B0;")
        stats_layout.addWidget(self.additions_label)
        
        self.deletions_label = QLabel("➖ Deletions: 0")
        self.deletions_label.setStyleSheet("color: #F14C4C;")
        stats_layout.addWidget(self.deletions_label)
        
        self.modified_label = QLabel("📝 Modified: 0 Lines")
        self.modified_label.setStyleSheet("color: #CCA700;")
        stats_layout.addWidget(self.modified_label)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.select_all_cb = QCheckBox("Apply all changes")
        self.select_all_cb.setChecked(True)
        self.select_all_cb.stateChanged.connect(self._on_select_all_changed)
        button_layout.addWidget(self.select_all_cb)
        
        button_layout.addStretch()
        
        self.reject_btn = QPushButton("❌ Reject Changes")
        self.reject_btn.setStyleSheet("""
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
        """)
        self.reject_btn.clicked.connect(self._on_reject)
        button_layout.addWidget(self.reject_btn)
        
        self.approve_btn = QPushButton("✅ Approve & Save")
        self.approve_btn.setStyleSheet("""
            QPushButton {
                background-color: #1E3D2F;
                color: #4EC9B0;
                border: 1px solid #4EC9B0;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2E4D3F;
            }
        """)
        self.approve_btn.clicked.connect(self._on_approve)
        button_layout.addWidget(self.approve_btn)
        
        layout.addLayout(button_layout)
    
    def load_diff(self, file_path: str, original_content: str, new_content: str):
        """
        Load the diff to display.
        
        Args:
            file_path: Path to the file being modified
            original_content: Original file content
            new_content: New proposed content
        """
        self._file_path = file_path
        self._original_content = original_content
        self._new_content = new_content
        
        # Update header
        self.file_label.setText(f"File: {file_path}")
        
        # Generate unified diff
        original_lines = original_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            original_lines,
            new_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            lineterm=''
        )
        
        diff_text = '\n'.join(diff)
        
        # Clear previous diff views
        while self.diff_layout.count():
            item = self.diff_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not diff_text.strip():
            # No changes detected
            no_change_label = QLabel("No changes detected between original and new content.")
            no_change_label.setStyleSheet("color: #888; padding: 20px;")
            no_change_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.diff_layout.addWidget(no_change_label)
            self.change_count_label.setText("No changes")
            self._update_stats(0, 0, 0)
        else:
            # Create diff text display
            diff_edit = QTextEdit()
            diff_edit.setReadOnly(True)
            diff_edit.setPlainText(diff_text)
            diff_edit.setFont(QFont("Consolas", 10))
            diff_edit.setStyleSheet("""
                QTextEdit {
                    background-color: #1E1E1E;
                    color: #D4D4D4;
                    border: none;
                    padding: 10px;
                }
            """)
            
            # Apply syntax highlighting
            highlighter = DiffHighlighter(diff_edit.document())
            
            self.diff_layout.addWidget(diff_edit)
            
            # Calculate stats
            additions = sum(1 for line in diff_text.splitlines() if line.startswith('+') and not line.startswith('+++'))
            deletions = sum(1 for line in diff_text.splitlines() if line.startswith('-') and not line.startswith('---'))
            modified = additions + deletions
            
            self.change_count_label.setText(f"{modified} changes")
            self._update_stats(additions, deletions, modified)
    
    def _update_stats(self, additions: int, deletions: int, modified: int):
        """Update the statistics display"""
        self.additions_label.setText(f"➕ Additions: {additions}")
        self.deletions_label.setText(f"➖ Deletions: {deletions}")
        self.modified_label.setText(f"📝 Lines Modified: {modified}")
    
    def _on_select_all_changed(self, state):
        """Handle select all checkbox state change"""
        self.approve_btn.setEnabled(state == Qt.CheckState.Checked.value or 
                                     self._pending_changes)
    
    def _on_approve(self):
        """Handle approve button click"""
        if self._file_path:
            self.approved.emit(self._file_path, self._new_content)
            self.accept()
    
    def _on_reject(self):
        """Handle reject button click"""
        if self._file_path:
            self.rejected.emit(self._file_path)
            self.reject()


class InlineDiffWidget(QWidget):
    """
    A compact inline diff widget for showing individual file changes.
    Can be used in lists or compact views.
    """
    
    clicked = pyqtSignal(str)  # Emits file path
    
    def __init__(self, file_path: str, original_content: str, new_content: str, parent=None):
        super().__init__(parent)
        self._file_path = file_path
        self._original = original_content
        self._new = new_content
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Header
        header = QLabel(f"📄 {file_path}")
        header.setStyleSheet("font-weight: bold; color: #4EC9B0;")
        layout.addWidget(header)
        
        # Stats
        stats = self._calculate_stats()
        stats_label = QLabel(f"➕{stats['additions']} ➖{stats['deletions']}")
        stats_label.setStyleSheet("color: #888;")
        layout.addWidget(stats_label)
        
        # Preview button
        preview_btn = QPushButton("Preview Changes")
        preview_btn.clicked.connect(lambda: self.clicked.emit(self._file_path))
        layout.addWidget(preview_btn)
    
    def _calculate_stats(self):
        """Calculate diff statistics"""
        original_lines = self._original.splitlines()
        new_lines = self._new.splitlines()
        
        diff = list(difflib.unified_diff(original_lines, new_lines, lineterm=''))
        
        additions = sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))
        deletions = sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))
        
        return {'additions': additions, 'deletions': deletions}


# Export for use by other modules
__all__ = ['DiffPreviewWindow', 'InlineDiffWidget']
