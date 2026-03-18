"""
Project Onboarding Dialog for LumeIDE

A professional popup that asks for the project's purpose and tech stack
to help configure the IDE appropriately.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QComboBox, QCheckBox, QGroupBox,
    QListWidget, QListWidgetItem, QScrollArea, QWidget, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon


# Common project purposes
PROJECT_PURPOSES = [
    "Web Development",
    "Desktop Application",
    "Mobile Application",
    "Data Science / Machine Learning",
    "Game Development",
    "DevOps / Automation",
    "API Development",
    "CLI Tool",
    "Library / Package",
    "Other"
]

# Common tech stacks
TECH_STACKS = {
    "Web Development": [
        "Django", "Flask", "FastAPI", "Pyramid",
        "React", "Vue.js", "Angular", "Next.js",
        "Node.js", "Express.js", "NestJS"
    ],
    "Desktop Application": [
        "PyQt / PySide", "Tkinter", "Kivy", "BeeWare",
        "Electron", "Tauri", "wxPython"
    ],
    "Data Science / ML": [
        "NumPy", "Pandas", "Scikit-learn", "TensorFlow",
        "PyTorch", "Jupyter", "Matplotlib", "Seaborn"
    ],
    "API Development": [
        "FastAPI", "Flask-RESTful", "Django REST", "Connexion"
    ],
    "General": [
        "Standard Library", "Testing", "Database", "Logging"
    ]
}

# Common dependencies
COMMON_PACKAGES = [
    "requests", "pytest", "black", "flake8", "mypy",
    "pip", "setuptools", "wheel", "python-dotenv"
]


class ProjectOnboardingDialog(QDialog):
    """
    A professional dialog for onboarding new projects.
    Collects project purpose, tech stack, and configuration.
    """
    
    # Signal emitted when project is configured
    project_configured = pyqtSignal(dict)
    
    def __init__(self, project_path: str = "", project_name: str = "", parent=None):
        super().__init__(parent)
        self.project_path = project_path
        self.project_name = project_name or self._extract_project_name(project_path)
        
        self.setWindowTitle("Project Onboarding - Configure Your Project")
        self.setMinimumSize(650, 550)
        self.setModal(True)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint
        )
        
        self._config = {
            'project_name': self.project_name,
            'project_path': self.project_path,
            'purpose': '',
            'tech_stack': [],
            'packages': [],
            'python_version': '3.11',
            'venv_auto': True,
            'enable_linting': True,
            'enable_testing': False
        }
        
        self._setup_ui()
    
    def _extract_project_name(self, path: str) -> str:
        """Extract project name from path"""
        import os
        if path:
            return os.path.basename(os.path.normpath(path))
        return "New Project"
    
    def _setup_ui(self):
        """Initialize the UI components"""
        layout = QVBoxLayout(self)
        
        # Header
        header_label = QLabel("🚀 Welcome to LumeIDE")
        header_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #4EC9B0;
                padding: 10px;
            }
        """)
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header_label)
        
        # Subtitle
        subtitle = QLabel(f"Let's configure <b>{self.project_name}</b> for the best experience")
        subtitle.setStyleSheet("color: #888; padding-bottom: 10px;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #3C3C3C;
                border-radius: 4px;
                background-color: #252526;
            }
        """)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(15)
        
        # Project Name Section
        name_group = self._create_name_section()
        scroll_layout.addWidget(name_group)
        
        # Purpose Section
        purpose_group = self._create_purpose_section()
        scroll_layout.addWidget(purpose_group)
        
        # Tech Stack Section
        tech_group = self._create_tech_stack_section()
        scroll_layout.addWidget(tech_group)
        
        # Python Version Section
        version_group = self._create_version_section()
        scroll_layout.addWidget(version_group)
        
        # Packages Section
        packages_group = self._create_packages_section()
        scroll_layout.addWidget(packages_group)
        
        # Options Section
        options_group = self._create_options_section()
        scroll_layout.addWidget(options_group)
        
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 1)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        skip_btn = QPushButton("Skip Setup")
        skip_btn.setStyleSheet("""
            QPushButton {
                background-color: #3C3C3C;
                color: #888;
                border: 1px solid #555;
                padding: 10px 20px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #4C4C4C;
            }
        """)
        skip_btn.clicked.connect(self._on_skip)
        button_layout.addWidget(skip_btn)
        
        next_btn = QPushButton("Configure Project →")
        next_btn.setStyleSheet("""
            QPushButton {
                background-color: #0E639C;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1177BB;
            }
        """)
        next_btn.clicked.connect(self._on_next)
        button_layout.addWidget(next_btn)
        
        layout.addLayout(button_layout)
    
    def _create_name_section(self) -> QGroupBox:
        """Create the project name input section"""
        group = QGroupBox("📁 Project Information")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #3C3C3C;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        layout = QVBoxLayout()
        
        # Project name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Project Name:"))
        self.name_input = QLineEdit(self.project_name)
        self.name_input.setStyleSheet("""
            QLineEdit {
                background-color: #3C3C3C;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 5px 10px;
                color: white;
            }
            QLineEdit:focus {
                border: 1px solid #0E639C;
            }
        """)
        self.name_input.textChanged.connect(lambda t: self._config.update({'project_name': t}))
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)
        
        # Project path (read-only)
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("Path:"))
        path_label = QLabel(self.project_path or "No folder selected")
        path_label.setStyleSheet("color: #888;")
        path_layout.addWidget(path_label)
        layout.addLayout(path_layout)
        
        group.setLayout(layout)
        return group
    
    def _create_purpose_section(self) -> QGroupBox:
        """Create the project purpose selection section"""
        group = QGroupBox("🎯 Project Purpose")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #3C3C3C;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.addWidget(QLabel("What will this project be used for?"))
        
        self.purpose_combo = QComboBox()
        self.purpose_combo.addItems(PROJECT_PURPOSES)
        self.purpose_combo.setStyleSheet("""
            QComboBox {
                background-color: #3C3C3C;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 8px;
                color: white;
            }
            QComboBox:focus {
                border: 1px solid #0E639C;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)
        self.purpose_combo.currentTextChanged.connect(self._on_purpose_changed)
        layout.addWidget(self.purpose_combo)
        
        # Description
        self.purpose_desc = QLabel("Select the main purpose of your project")
        self.purpose_desc.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.purpose_desc)
        
        group.setLayout(layout)
        return group
    
    def _create_tech_stack_section(self) -> QGroupBox:
        """Create the tech stack selection section"""
        group = QGroupBox("🛠️ Tech Stack")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #3C3C3C;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Select technologies you'll be using:"))
        
        self.tech_list = QListWidget()
        self.tech_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.tech_list.setStyleSheet("""
            QListWidget {
                background-color: #2D2D2D;
                border: 1px solid #3C3C3C;
                border-radius: 4px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 5px;
                border-radius: 3px;
            }
            QListWidget::item:selected {
                background-color: #0E639C;
            }
            QListWidget::item:hover {
                background-color: #3C3C3C;
            }
        """)
        self.tech_list.itemSelectionChanged.connect(self._on_tech_selection_changed)
        layout.addWidget(self.tech_list)
        
        # Quick add buttons
        quick_layout = QHBoxLayout()
        quick_layout.addWidget(QLabel("Quick add:"))
        
        common_btn = QPushButton("Common Packages")
        common_btn.clicked.connect(self._add_common_packages)
        common_btn.setStyleSheet("padding: 5px 10px; border-radius: 3px;")
        quick_layout.addWidget(common_btn)
        
        quick_layout.addStretch()
        layout.addLayout(quick_layout)
        
        group.setLayout(layout)
        return group
    
    def _create_version_section(self) -> QGroupBox:
        """Create the Python version section"""
        group = QGroupBox("🐍 Python Version")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #3C3C3C;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        layout = QHBoxLayout()
        layout.addWidget(QLabel("Python Version:"))
        
        self.python_version_combo = QComboBox()
        self.python_version_combo.addItems(["3.8", "3.9", "3.10", "3.11", "3.12"])
        self.python_version_combo.setCurrentText("3.11")
        self.python_version_combo.setStyleSheet("""
            QComboBox {
                background-color: #3C3C3C;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 5px 10px;
                color: white;
            }
        """)
        self.python_version_combo.currentTextChanged.connect(
            lambda v: self._config.update({'python_version': v})
        )
        layout.addWidget(self.python_version_combo)
        layout.addStretch()
        
        group.setLayout(layout)
        return group
    
    def _create_packages_section(self) -> QGroupBox:
        """Create the packages section"""
        group = QGroupBox("📦 Initial Packages")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #3C3C3C;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Packages to install (comma-separated):"))
        
        self.packages_input = QLineEdit()
        self.packages_input.setPlaceholderText("e.g., requests, pytest, black")
        self.packages_input.setStyleSheet("""
            QLineEdit {
                background-color: #3C3C3C;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 8px;
                color: white;
            }
            QLineEdit:focus {
                border: 1px solid #0E639C;
            }
        """)
        self.packages_input.textChanged.connect(self._on_packages_changed)
        layout.addWidget(self.packages_input)
        
        group.setLayout(layout)
        return group
    
    def _create_options_section(self) -> QGroupBox:
        """Create the options section"""
        group = QGroupBox("⚙️ Options")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #3C3C3C;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        layout = QVBoxLayout()
        
        self.auto_venv_cb = QCheckBox("Auto-detect and use virtual environment (.venv)")
        self.auto_venv_cb.setChecked(True)
        self.auto_venv_cb.setStyleSheet("color: white;")
        self.auto_venv_cb.stateChanged.connect(
            lambda s: self._config.update({'venv_auto': s == Qt.CheckState.Checked})
        )
        layout.addWidget(self.auto_venv_cb)
        
        self.linting_cb = QCheckBox("Enable code linting and formatting")
        self.linting_cb.setChecked(True)
        self.linting_cb.setStyleSheet("color: white;")
        self.linting_cb.stateChanged.connect(
            lambda s: self._config.update({'enable_linting': s == Qt.CheckState.Checked})
        )
        layout.addWidget(self.linting_cb)
        
        self.testing_cb = QCheckBox("Set up testing framework")
        self.testing_cb.setStyleSheet("color: white;")
        self.testing_cb.stateChanged.connect(
            lambda s: self._config.update({'enable_testing': s == Qt.CheckState.Checked})
        )
        layout.addWidget(self.testing_cb)
        
        group.setLayout(layout)
        return group
    
    def _on_purpose_changed(self, purpose: str):
        """Handle purpose selection change"""
        self._config['purpose'] = purpose
        
        # Update tech stack list based on purpose
        self.tech_list.clear()
        tech_items = TECH_STACKS.get(purpose, TECH_STACKS.get("General", []))
        for tech in tech_items:
            self.tech_list.addItem(tech)
    
    def _on_tech_selection_changed(self):
        """Handle tech stack selection change"""
        selected = [item.text() for item in self.tech_list.selectedItems()]
        self._config['tech_stack'] = selected
    
    def _on_packages_changed(self, text: str):
        """Handle packages input change"""
        packages = [p.strip() for p in text.split(',') if p.strip()]
        self._config['packages'] = packages
    
    def _add_common_packages(self):
        """Add common packages to the packages input"""
        current = self.packages_input.text()
        if current:
            current += ", "
        current += ", ".join(COMMON_PACKAGES)
        self.packages_input.setText(current)
    
    def _on_skip(self):
        """Handle skip button click"""
        reply = QMessageBox.question(
            self,
            "Skip Setup",
            "Are you sure you want to skip project configuration?\n"
            "You can always configure it later from Settings.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.reject()
    
    def _on_next(self):
        """Handle next button click"""
        # Validate
        if not self.name_input.text().strip():
            QMessageBox.warning(
                self,
                "Missing Information",
                "Please enter a project name."
            )
            return
        
        self._config['project_name'] = self.name_input.text().strip()
        self.project_configured.emit(self._config)
        self.accept()
    
    def get_configuration(self) -> dict:
        """Get the collected configuration"""
        return self._config.copy()


# Export for use by other modules
__all__ = ['ProjectOnboardingDialog', 'PROJECT_PURPOSES', 'TECH_STACKS']
