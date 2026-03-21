"""
Activity Bar Module for LumeIDE

Provides the far-left icon navigation bar for quick access to different IDE views.
Only functional views are shown (Explorer and AI Chat).
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QToolButton, QLabel
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QColor


class LedIndicator(QWidget):
    """Visual indicator for AI activity status."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._active = False
        self.setFixedSize(12, 12)

    def setActive(self, active: bool):
        self._active = active
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        color = QColor(0, 255, 0, 255) if self._active else QColor(100, 100, 100, 255)
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        
        rect = self.rect()
        center = rect.center()
        radius = min(rect.width(), rect.height()) / 2 - 2
        painter.drawEllipse(center, int(radius), int(radius))


class ActivityBar(QWidget):
    """
    Far-left icon navigation bar for IDE views.
    VS Code-style activity bar showing only functional views.
    """
    
    # Signals
    view_changed = pyqtSignal(str)  # Emits view name
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_view = 'explorer'
        self._buttons = {}
        self._setup_ui()
    
    def _setup_ui(self):
        """Initialize the activity bar UI."""
        self.setFixedWidth(48)
        self.setStyleSheet("""
            QWidget {
                background-color: #333333;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 8, 4, 8)
        layout.setSpacing(4)
        
        # Title bar area at top (VS Code style)
        self.title_area = QWidget()
        self.title_area.setFixedHeight(35)
        title_layout = QVBoxLayout(self.title_area)
        title_layout.setContentsMargins(0, 8, 0, 0)
        title_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.logo_label = QLabel("L")
        self.logo_label.setStyleSheet("""
            QLabel {
                color: #007ACC;
                font-size: 24px;
                font-weight: bold;
                font-family: 'Segoe UI', sans-serif;
            }
        """)
        title_layout.addWidget(self.logo_label)
        layout.addWidget(self.title_area)
        
        # Separator
        self._add_separator(layout)
        
        # View buttons with icons (VS Code-style icons using text symbols)
        # Only functional views are shown
        views = [
            ('explorer', '📁', 'Explorer'),  # File explorer
            ('aura', '🤖', 'Aura AI'),        # AI Chat
        ]
        
        for view_id, icon, tooltip in views:
            btn = QToolButton()
            btn.setText(icon)
            btn.setFixedSize(40, 40)
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            btn.setCheckable(True)
            btn.setToolTip(tooltip)
            btn.clicked.connect(lambda checked, v=view_id: self._on_view_clicked(v))
            btn.setStyleSheet("""
                QToolButton {
                    border: none;
                    border-radius: 4px;
                    background-color: transparent;
                    color: #AAAAAA;
                }
                QToolButton:hover {
                    background-color: #2A2D2E;
                }
                QToolButton:checked {
                    background-color: #1E1E1E;
                    border-left: 2px solid #007ACC;
                    color: #FFFFFF;
                }
            """)
            self._buttons[view_id] = btn
            layout.addWidget(btn)
        
        # Set default selection
        self._buttons[self._current_view].setChecked(True)
        
        # Spacer
        layout.addStretch()
        
        # Separator before bottom items
        self._add_separator(layout)
        
        # AI status indicator
        status_layout = QVBoxLayout()
        status_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_layout.setSpacing(2)
        
        self.ai_indicator = LedIndicator()
        self.ai_label = QLabel("AI")
        self.ai_label.setStyleSheet("""
            QLabel {
                color: #858585;
                font-size: 9px;
            }
        """)
        status_layout.addWidget(self.ai_indicator)
        status_layout.addWidget(self.ai_label)
        layout.addLayout(status_layout)
        
        # Settings button at very bottom
        settings_btn = QToolButton()
        settings_btn.setText('⚙️')
        settings_btn.setFixedSize(40, 40)
        settings_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        settings_btn.setToolTip("Settings")
        settings_btn.clicked.connect(lambda: self.view_changed.emit('settings'))
        settings_btn.setStyleSheet("""
            QToolButton {
                border: none;
                border-radius: 4px;
                background-color: transparent;
                color: #AAAAAA;
            }
            QToolButton:hover {
                background-color: #2A2D2E;
            }
        """)
        layout.addWidget(settings_btn)
    
    def _add_separator(self, layout):
        """Add a horizontal separator."""
        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: #3C3C3C; margin: 4px 8px;")
        layout.addWidget(separator)
    
    def _on_view_clicked(self, view_id: str):
        """Handle view button click."""
        self._current_view = view_id
        
        # Update button states
        for vid, btn in self._buttons.items():
            btn.setChecked(vid == view_id)
        
        self.view_changed.emit(view_id)
    
    def set_current_view(self, view_id: str):
        """Set the current view programmatically."""
        if view_id in self._buttons:
            self._buttons[view_id].setChecked(True)
            self._current_view = view_id
    
    def set_ai_active(self, active: bool):
        """Set AI activity indicator state."""
        self.ai_indicator.setActive(active)


# Export
__all__ = ['ActivityBar', 'LedIndicator']
