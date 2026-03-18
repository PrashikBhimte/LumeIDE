import sys
from PyQt6.QtWidgets import QApplication

from app.ui.main_window import MainWindow
from app.ui.styles import DARK_PLUS_QSS


def main():
    """
    Initializes and runs the Lume IDE application.
    """
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_PLUS_QSS)

    main_window = MainWindow()
    main_window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
