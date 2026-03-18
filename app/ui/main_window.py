import sys

from PyQt6.QtWidgets import (
    QMainWindow, QApplication, QTabWidget, QDockWidget, QListWidget, QLabel,
    QStatusBar
)
from PyQt6.QtCore import Qt


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lume IDE")
        self.resize(1200, 800)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.setCentralWidget(self.tabs)

        self.create_sidebar()
        self.create_statusbar()

    def create_sidebar(self):
        self.sidebar = QDockWidget("Aura Sidebar")
        self.sidebar.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.sidebar)

        # Placeholder content for the sidebar
        self.project_view = QListWidget()
        self.sidebar.setWidget(self.project_view)

    def create_statusbar(self):
        self.setStatusBar(QStatusBar(self))
        self.vibe_label = QLabel("Vibe: Ready")
        self.statusBar().addPermanentWidget(self.vibe_label)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())
