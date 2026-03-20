import sys
from dotenv import load_dotenv
from PyQt6.QtWidgets import QApplication

from app.ui.main_window import MainWindow
from app.ui.styles import DARK_PLUS_QSS

load_dotenv()

def main():
    """
    Initializes and runs the Lume IDE application.
    """
    app = QApplication(sys.argv)
    
    # Load Dark+ High Contrast theme
    try:
        with open("dark_plus_high_contrast.qss", "r") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        print("Stylesheet 'dark_plus_high_contrast.qss' not found. Using default styles.")

    main_window = MainWindow()
    main_window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
