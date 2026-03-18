import sys

from PyQt6.QtWidgets import (
    QMainWindow, QApplication, QTabWidget, QDockWidget, QTreeView, QLabel,
    QStatusBar, QFileDialog, QWidget, QVBoxLayout, QTextEdit, QPushButton
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QStandardItemModel, QStandardItem, QPainter, QColor

from app.utils.file_system import scan_directory_to_tree


class LedIndicator(QWidget):
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
        radius = min(rect.width(), rect.height()) / 2 - 2
        painter.drawEllipse(center, radius, radius)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lume IDE")
        self.resize(1200, 800)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.setCentralWidget(self.tabs)

        self.create_menus()
        self.create_sidebar()
        self.create_statusbar()

        self.set_ai_active(False)

    def create_menus(self):
        file_menu = self.menuBar().addMenu("&File")
        open_folder_action = QAction("&Open Folder", self)
        open_folder_action.triggered.connect(self.open_folder)
        file_menu.addAction(open_folder_action)

    def open_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Open Folder")
        if path:
            self.model.clear()
            tree = scan_directory_to_tree(path)
            self.model.setHorizontalHeaderLabels([tree['name']])
            self.populate_tree(self.model.invisibleRootItem(), tree['children'])

    def populate_tree(self, parent_item, children):
        for item_data in children:
            item = QStandardItem(item_data['name'])
            parent_item.appendRow(item)
            if item_data['type'] == 'directory':
                self.populate_tree(item, item_data.get('children', []))

    def create_sidebar(self):
        self.sidebar = QDockWidget("Project Explorer")
        self.sidebar.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.sidebar)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.project_view = QTreeView()
        self.project_view.setHeaderHidden(True)
        self.model = QStandardItemModel()
        self.project_view.setModel(self.model)
        
        self.chat_input = QTextEdit()
        self.chat_input.setPlaceholderText("Describe what you want to build...")
        
        self.send_button = QPushButton("Send to Aura")
        self.send_button.clicked.connect(self.send_chat_task)

        layout.addWidget(self.project_view)
        layout.addWidget(self.chat_input)
        layout.addWidget(self.send_button)
        
        self.sidebar.setWidget(container)

    def send_chat_task(self):
        user_request = self.chat_input.toPlainText()
        if user_request:
            print(f"User request: {user_request}")
            self.chat_input.clear()
            
            self.set_ai_active(True)
            QTimer.singleShot(2000, lambda: self.set_ai_active(False))

    def create_statusbar(self):
        self.setStatusBar(QStatusBar(self))
        self.vibe_indicator = LedIndicator()
        self.statusBar().addPermanentWidget(self.vibe_indicator)

    def set_ai_active(self, active: bool):
        self.vibe_indicator.setActive(active)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())
