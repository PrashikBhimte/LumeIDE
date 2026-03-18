"""
Activity Bar Module for LumeIDE

Provides the far-left icon navigation bar for quick access to different IDE views.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QToolButton
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QIcon


class LedIndicator(QWidget):
    """Visual indicator for AI activity status."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._active = False
        self.setFixedSize(16, 16)

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
        # Explicitly cast radius to int to avoid float precision issues
        radius = min(rect.width(), rect.height()) / 2 - 2
        painter.drawEllipse(center, int(radius), int(radius))


class ActivityBar(QWidget):
    """
    Far-left icon navigation bar for IDE views.
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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 8, 4, 8)
        layout.setSpacing(4)
        
        # View buttons with icons
        views = [
            ('explorer', '📁'),
            ('search', '🔍'),
            ('aura', '🤖'),
            ('tasks', '📋'),
            ('extensions', '🧩'),
        ]
        
        for view_id, icon in views:
            btn = QToolButton()
            btn.setText(icon)
            btn.setFixedSize(40, 40)
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, v=view_id: self._on_view_clicked(v))
            self._buttons[view_id] = btn
            layout.addWidget(btn)
        
        # Set default selection
        self._buttons[self._current_view].setChecked(True)
        
        layout.addStretch()
        
        # AI status indicator at bottom
        self.ai_indicator = LedIndicator()
        layout.addWidget(self.ai_indicator, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Settings button at very bottom
        settings_btn = QToolButton()
        settings_btn.setText('⚙️')
        settings_btn.setFixedSize(40, 40)
        settings_btn.clicked.connect(lambda: self.view_changed.emit('settings'))
        layout.addWidget(settings_btn)
    
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
