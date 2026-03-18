# LumeIDE UI Package
# Components
from app.ui.activity_bar import ActivityBar, LedIndicator
from app.ui.sidebar import Sidebar, FileExplorer, AuraChat
from app.ui.editor_area import EditorArea, CodeEditor
from app.ui.bottom_panel import BottomPanel, TerminalOutput, LogViewer
from app.ui.main_window import MainWindow

# Dialogs
from app.ui.diff_preview import DiffPreviewWindow, InlineDiffWidget
from app.ui.onboarding import ProjectOnboardingDialog, PROJECT_PURPOSES, TECH_STACKS

# State Management
from app.ui.state_manager import UIStateManager, TabState, WindowState

__all__ = [
    # Components
    'ActivityBar', 'LedIndicator',
    'Sidebar', 'FileExplorer', 'AuraChat',
    'EditorArea', 'CodeEditor',
    'BottomPanel', 'TerminalOutput', 'LogViewer',
    'MainWindow',
    
    # Dialogs
    'DiffPreviewWindow', 'InlineDiffWidget',
    'ProjectOnboardingDialog', 'PROJECT_PURPOSES', 'TECH_STACKS',
    
    # State
    'UIStateManager', 'TabState', 'WindowState'
]
