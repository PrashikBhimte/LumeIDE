"""
Main Window Module for LumeIDE

Orchestrator that assembles all UI components:
- Activity Bar (left icon navigation)
- Sidebar (Explorer)
- Editor Area (tabbed code editor)
- Bottom Panel (Unified Shell + Log Viewer)

Manages the overall layout and coordinates between components.
"""

import os
import sys

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QFileDialog, QMessageBox, QMenuBar, QMenu,
    QToolBar, QStatusBar, QDockWidget, QProgressBar, QLabel
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QKeySequence, QAction

# Import UI components
from app.ui.activity_bar import ActivityBar
from app.ui.sidebar import Sidebar
from app.ui.editor_area import EditorArea
from app.ui.bottom_panel import BottomPanel

# Import core modules
from app.storage.database import ChronicleDB
from app.engine.dispatcher import CommandDispatcher
from app.models.project_context import ProjectContext
from app.engine.aura_client import AuraClient
from app.utils.venv_detector import VenvDetector
from app.ui.onboarding import ProjectOnboardingDialog


class MainWindow(QMainWindow):
    """
    Main IDE Window - Orchestrator that assembles all components.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lume IDE")
        self.resize(1200, 800)

        # Core state
        self.current_project_path = None
        self.current_project_id = None
        self._project_opened = False
        self.project_context = ProjectContext()

        # Initialize core modules
        self._init_core_modules()

        # Setup UI components
        self._setup_ui()
        self._create_menus()
        self._create_toolbar()
        self._connect_signals()

        # Auto-save timer
        self._auto_save_timer = QTimer()
        self._auto_save_timer.timeout.connect(self._auto_save_session)
        self._auto_save_timer.start(30000)  # 30 seconds

    def _init_core_modules(self):
        """Initialize core modules."""
        # Database
        self.db = ChronicleDB('lume_ide.db')
        self.db.connect()
        self.db.create_tables()

        # Engine components
        self.venv_detector = VenvDetector()
        self.editor_area = EditorArea() # Editor area needs to be created before dispatcher

        # Try to initialize Aura client (may fail if no API key)
        self.aura_client = None
        self._init_aura_client()

        # Command Dispatcher
        self.command_dispatcher = CommandDispatcher(
            project_context=self.project_context,
            aura_client=self.aura_client,
            editor_area=self.editor_area,
        )

    def _init_aura_client(self):
        """Initialize Aura client."""
        try:
            self.aura_client = AuraClient()
        except ValueError:
            print("Gemini API key not configured. Aura features disabled.")
            self.aura_client = None

    def _setup_ui(self):
        """Setup the main UI layout."""
        # Central widget with splitter
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Activity bar (left icon navigation)
        self.activity_bar = ActivityBar()
        self.activity_bar.setFixedWidth(48)
        main_layout.addWidget(self.activity_bar)

        # Horizontal splitter for sidebar and editor
        horizontal_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Sidebar (Explorer)
        self.sidebar = Sidebar()
        self.sidebar.setMinimumWidth(200)
        self.sidebar.setMaximumWidth(400)
        horizontal_splitter.addWidget(self.sidebar)

        # Editor area (tabbed code editor)
        horizontal_splitter.addWidget(self.editor_area)

        # Set initial sizes
        horizontal_splitter.setStretchFactor(0, 1)  # Sidebar
        horizontal_splitter.setStretchFactor(1, 3)  # Editor

        main_layout.addWidget(horizontal_splitter, stretch=1)

        # Bottom panel (Unified Shell + Log Viewer)
        self.bottom_panel = BottomPanel(command_dispatcher=self.command_dispatcher)
        self.bottom_panel.setMinimumHeight(150)
        self.bottom_panel.setMaximumHeight(400)

        # Create dock for bottom panel
        self.bottom_dock = QDockWidget("Output", self)
        self.bottom_dock.setWidget(self.bottom_panel)
        self.bottom_dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.bottom_dock)

        # Status bar
        self._setup_statusbar()

    def _setup_statusbar(self):
        """Setup the status bar."""
        self.statusBar = QStatusBar(self)
        self.setStatusBar(self.statusBar)

        self.status_label = QLabel("Ready")
        self.statusBar.addPermanentWidget(self.status_label)

        self.venv_label = QLabel("No venv")
        self.statusBar.addPermanentWidget(self.venv_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(150)
        self.progress_bar.setVisible(False)
        self.statusBar.addPermanentWidget(self.progress_bar)

    def _create_menus(self):
        """Create the menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        open_folder_action = QAction("&Open Folder...", self)
        open_folder_action.setShortcut(QKeySequence.StandardKey.Open)
        open_folder_action.triggered.connect(self.open_folder)
        file_menu.addAction(open_folder_action)

        file_menu.addSeparator()

        save_action = QAction("&Save", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.editor_area.save_current)
        file_menu.addAction(save_action)

        save_all_action = QAction("Save A&ll", self)
        save_all_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_all_action.triggered.connect(self.editor_area.save_all)
        file_menu.addAction(save_all_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View menu
        view_menu = menubar.addMenu("&View")

        toggle_sidebar_action = QAction("Toggle &Sidebar", self)
        toggle_sidebar_action.setShortcut(QKeySequence("Ctrl+B"))
        toggle_sidebar_action.triggered.connect(
            lambda: self.sidebar.setVisible(not self.sidebar.isVisible())
        )
        view_menu.addAction(toggle_sidebar_action)

        toggle_terminal_action = QAction("Toggle &Terminal", self)
        toggle_terminal_action.setShortcut(QKeySequence("Ctrl+`"))
        toggle_terminal_action.triggered.connect(
            lambda: self.bottom_dock.setVisible(not self.bottom_dock.isVisible())
        )
        view_menu.addAction(toggle_terminal_action)

        # Project menu
        project_menu = menubar.addMenu("&Project")

        project_settings_action = QAction("&Project Settings...", self)
        project_settings_action.triggered.connect(self._show_project_settings)
        project_menu.addAction(project_settings_action)

        detect_venv_action = QAction("&Detect Virtual Environment", self)
        detect_venv_action.triggered.connect(self._detect_venv)
        project_menu.addAction(detect_venv_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("&About LumeIDE", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _create_toolbar(self):
        """Create the toolbar."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Open folder
        open_action = QAction("📂", self)
        open_action.setToolTip("Open Folder")
        open_action.triggered.connect(self.open_folder)
        toolbar.addAction(open_action)

        toolbar.addSeparator()

        # Save
        save_action = QAction("💾", self)
        save_action.setToolTip("Save File")
        save_action.triggered.connect(self.editor_area.save_current)
        toolbar.addAction(save_action)

        toolbar.addSeparator()

        # Run
        run_action = QAction("▶️", self)
        run_action.setToolTip("Run Python File")
        run_action.triggered.connect(lambda: self.command_dispatcher.dispatch("run this"))
        toolbar.addAction(run_action)

        # Stop
        stop_action = QAction("⏹️", self)
        stop_action.setToolTip("Stop Execution")
        stop_action.triggered.connect(self._stop_execution)
        toolbar.addAction(stop_action)

    def _connect_signals(self):
        """Connect signals between components."""
        # Activity bar -> View changes
        self.activity_bar.view_changed.connect(self._on_view_changed)

        # Sidebar -> File operations
        self.sidebar.file_double_clicked.connect(self.editor_area.open_file)

        # Editor area
        self.editor_area.file_saved.connect(self._on_file_saved)
        self.editor_area.tab_changed.connect(self._on_tab_changed)

        # Aura client signals
        if self.aura_client:
            self.aura_client.started_thinking.connect(
                self.bottom_panel.shell.on_aura_started_thinking
            )
            self.aura_client.tool_used.connect(self._on_aura_tool_used)
            self.aura_client.finished.connect(
                self.bottom_panel.shell.on_aura_finished
            )

    def _on_aura_tool_used(self, tool_name, tool_args):
        self.bottom_panel.shell.on_aura_tool_used(tool_name, tool_args)
        if tool_name == 'write_file':
            file_path = tool_args.get('file_path')
            if file_path:
                self.editor_area.open_file(file_path)

    def _on_view_changed(self, view_id: str):
        """Handle activity bar view changes."""
        if view_id == 'explorer':
            self.sidebar.show_explorer()
        elif view_id == 'settings':
            self._show_project_settings()

    def _on_file_saved(self, file_path: str):
        """Handle file saved event."""
        self.bottom_panel.append_output(f"Saved: {os.path.basename(file_path)}", "green")

    def _on_tab_changed(self, index: int):
        """Handle tab change."""
        pass

    def open_folder(self):
        """Open a folder and setup the project."""
        path = QFileDialog.getExistingDirectory(self, "Open Folder")
        if not path:
            return

        normalized = os.path.normpath(path)
        self.current_project_path = normalized
        self.project_context.root_path = normalized

        # Register project
        project_name = os.path.basename(normalized)
        self.current_project_id = self.db.register_project(project_name, normalized)

        # Update sidebar
        self.sidebar.set_root_path(normalized)

        # Detect venv
        self._detect_venv()

        # Show onboarding (only first time)
        if not self._project_opened:
            self._show_onboarding(normalized, project_name)
            self._project_opened = True

        # Update status
        self.status_label.setText(f"Project: {project_name}")

        # Load previous session if exists
        self._load_session()

    def _detect_venv(self):
        """Auto-detect virtual environment."""
        if not self.current_project_path:
            return

        venv_info = self.venv_detector.find_venv_in_directory(self.current_project_path)
        if venv_info:
            normalized_venv = os.path.normpath(venv_info['path'])
            self.project_context.venv_path = normalized_venv
            self.venv_label.setText(f"venv: {venv_info['name']}")
            self.bottom_panel.append_output(
                f"Detected venv: {normalized_venv}", "green"
            )
        else:
            self.project_context.venv_path = None
            self.venv_label.setText("No venv detected")

    def _show_onboarding(self, path: str, name: str):
        """Show project onboarding dialog."""
        dialog = ProjectOnboardingDialog(path, name, self)
        dialog.project_configured.connect(self._on_project_configured)
        dialog.exec()

    def _on_project_configured(self, config: dict):
        """Handle project configuration."""
        self.bottom_panel.append_output(
            f"Project configured: {config['project_name']}", "green"
        )

        # Install packages if specified
        packages = config.get('packages', [])
        if packages:
            command = f"pip install {' '.join(packages)}"
            self.command_dispatcher.dispatch(command)

    def _stop_execution(self):
        """Stop current execution."""
        # This might need to be re-wired to the dispatcher if it handles long-running processes
        if self.aura_client and self.aura_client.is_generating():
            self.aura_client.abort()
            self.bottom_panel.append_output("Aura generation stopped.", "red")

    def _show_project_settings(self):
        """Show project settings."""
        if not self.current_project_path:
            QMessageBox.information(self, "No Project", "Please open a folder first.")
            return

        dialog = ProjectOnboardingDialog(self.current_project_path, "", self)
        dialog.exec()

    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About LumeIDE",
            "LumeIDE\n\n"
            "A modern Python IDE with AI-powered assistance."
        )

    def _auto_save_session(self):
        """Auto-save session state."""
        if not self.current_project_id:
            return

        # Save open tabs
        open_tabs = self.editor_area.get_open_files()

        # Save window geometry
        geometry = self.saveGeometry().toBase64().data().decode()

        # Save session
        self.db.save_session(
            project_path=self.current_project_path,
            open_tabs=open_tabs,
            window_geometry=geometry
        )

    def _load_session(self):
        """Load previous session state."""
        session = self.db.load_session()

        # Reopen tabs
        open_tabs = session.get('open_tabs', [])
        for file_path in open_tabs:
            if os.path.exists(file_path):
                self.editor_area.open_file(file_path)

        # Restore window geometry
        geometry = session.get('window_geometry')
        if geometry:
            try:
                self.restoreGeometry(geometry.encode())
            except:
                pass

    def closeEvent(self, event):
        """Handle window close."""
        # Save session before closing
        self._auto_save_session()

        # Close database
        self.db.close()

        event.accept()


# Export
__all__ = ['MainWindow']
