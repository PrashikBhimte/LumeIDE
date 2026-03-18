"""
Main Window Module for LumeIDE

Orchestrator that assembles all UI components:
- Activity Bar (left icon navigation)
- Sidebar (Explorer + Aura Chat)
- Editor Area (tabbed code editor)
- Bottom Panel (Terminal + Log Viewer)

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
from app.engine.tool_dispatcher import TaskDispatcher
from app.engine.error_recovery import ErrorRecovery
from app.engine.aura_client import AuraClient, VaultToolset
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
        self.db.create_tasks_table_migration()
        self.db.create_ui_state_table()

        # Engine components
        self.task_dispatcher = TaskDispatcher()
        self.error_recovery = ErrorRecovery(task_dispatcher=self.task_dispatcher)
        self.venv_detector = VenvDetector()
        self.vault_tools = VaultToolset()

        # Try to initialize Aura client (may fail if no API key)
        self.aura_client = None
        self._init_aura_client()

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

        # Sidebar (Explorer + Aura Chat)
        self.sidebar = Sidebar()
        self.sidebar.setMinimumWidth(200)
        self.sidebar.setMaximumWidth(400)
        horizontal_splitter.addWidget(self.sidebar)

        # Editor area (tabbed code editor)
        self.editor_area = EditorArea()
        horizontal_splitter.addWidget(self.editor_area)

        # Set initial sizes
        horizontal_splitter.setStretchFactor(0, 1)  # Sidebar
        horizontal_splitter.setStretchFactor(1, 3)  # Editor

        main_layout.addWidget(horizontal_splitter, stretch=1)

        # Bottom panel (Terminal + Log Viewer)
        self.bottom_panel = BottomPanel()
        self.bottom_panel.setMinimumHeight(100)
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
        run_action.triggered.connect(self._run_current_file)
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
        self.sidebar.message_sent.connect(self._on_aura_message)
        self.sidebar.aura_stopped.connect(self._on_aura_stopped)

        # Editor area
        self.editor_area.file_saved.connect(self._on_file_saved)
        self.editor_area.tab_changed.connect(self._on_tab_changed)

    def _on_view_changed(self, view_id: str):
        """Handle activity bar view changes."""
        if view_id == 'explorer':
            self.sidebar.tab_selector.setCurrentIndex(0)
        elif view_id == 'aura':
            self.sidebar.tab_selector.setCurrentIndex(1)
        elif view_id == 'settings':
            self._show_project_settings()

    def _on_aura_message(self, message: str):
        """Handle Aura chat message."""
        if not self.aura_client:
            self.sidebar.add_error("Aura is not configured. Set GEMINI_API_KEY environment variable.")
            return

        self.activity_bar.set_ai_active(True)
        self.bottom_panel.append_command(f"Send to Aura: {message}")

        # Create task
        task_id = self.db.create_task(self.current_project_id, message, "processing")

        # Send to Aura (async - in production would use threading)
        try:
            result = self.aura_client.send_prompt(message, stream=False)
            if result.error:
                self.sidebar.add_error(result.error)
                self.db.update_task_error(task_id, result.error)
            else:
                self.sidebar.add_response(result.text or "No response")
                self.db.update_task_result(task_id, result.text)
        except Exception as e:
            error_msg = str(e)
            self.sidebar.add_error(error_msg)
            self.db.update_task_error(task_id, error_msg)

        self.activity_bar.set_ai_active(False)

    def _on_aura_stopped(self):
        """Handle Aura stop request."""
        if self.aura_client:
            self.aura_client.abort()
        self.activity_bar.set_ai_active(False)

    def _on_file_saved(self, file_path: str):
        """Handle file saved event."""
        import os
        self.bottom_panel.append_success(f"Saved: {os.path.basename(file_path)}")

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

        # Register project
        project_name = os.path.basename(normalized)
        self.current_project_id = self.db.register_project(project_name, normalized)

        # Setup task dispatcher
        self.task_dispatcher.set_working_directory(normalized)

        # Setup vault tools
        self.vault_tools.working_dir = normalized

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
            self.venv_label.setText(f"venv: {venv_info['name']}")
            self.bottom_panel.append_terminal_output(
                f"Detected: {normalized_venv}", "#4EC9B0"
            )
        else:
            self.venv_label.setText("No venv detected")

    def _show_onboarding(self, path: str, name: str):
        """Show project onboarding dialog."""
        dialog = ProjectOnboardingDialog(path, name, self)
        dialog.project_configured.connect(self._on_project_configured)
        dialog.exec()

    def _on_project_configured(self, config: dict):
        """Handle project configuration."""
        self.bottom_panel.append_terminal_output(
            f"Project configured: {config['project_name']}", "#4EC9B0"
        )

        # Install packages if specified
        packages = config.get('packages', [])
        if packages:
            self._install_packages(packages)

    def _install_packages(self, packages: list):
        """Install packages via pip."""
        self.bottom_panel.append_command(f"pip install {' '.join(packages)}")

        for package in packages:
            try:
                from app.engine.tool_dispatcher import tool_run_command
                result = tool_run_command(
                    f"pip install {package}",
                    cwd=self.current_project_path
                )
                self.bottom_panel.append_terminal_output(result)
            except Exception as e:
                self.bottom_panel.append_error(str(e))

    def _run_current_file(self):
        """Run the current Python file."""
        file_path = self.editor_area.get_current_file()
        if not file_path:
            return

        if not file_path.endswith('.py'):
            self.bottom_panel.append_error("Not a Python file")
            return

        self.bottom_panel.append_command(f"python {file_path}")

        # Get venv python if available
        venv_info = self.venv_detector.find_venv_in_directory(self.current_project_path)
        if venv_info and venv_info.get('python_path'):
            python_path = os.path.normpath(venv_info['python_path'])
            cmd = f'"{python_path}" "{os.path.normpath(file_path)}"'
        else:
            cmd = f'python "{os.path.normpath(file_path)}"'

        try:
            from app.engine.tool_dispatcher import tool_run_command
            result = tool_run_command(cmd, cwd=self.current_project_path, timeout=60)
            self.bottom_panel.append_terminal_output(result)
        except Exception as e:
            self.bottom_panel.append_error(str(e))

    def _stop_execution(self):
        """Stop current execution."""
        if self.aura_client and self.aura_client.is_generating():
            self.aura_client.abort()
            self.bottom_panel.append_terminal_output("Execution stopped", "#F14C4C")

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
            "A modern Python IDE with AI-powered assistance.\n\n"
            "Features:\n"
            "• AI Code Generation with Gemini\n"
            "• Virtual Environment Detection\n"
            "• Diff Preview for Code Changes\n"
            "• Auto-Save for UI State\n"
            "• Error Recovery System\n"
            "• Project Onboarding"
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
