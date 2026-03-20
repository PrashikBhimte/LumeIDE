"""
LumeIDE - AI-Native Development Environment

Main entry point for the application.
"""

import sys
import os
import importlib.util
from dotenv import load_dotenv
from PyQt6.QtWidgets import QApplication

from app.ui.main_window import MainWindow

# Load environment variables
load_dotenv()


def check_dependency_conflicts():
    """
    Dependency Guard: Check for conflicting packages.
    Prints a warning if incompatible packages are detected.
    
    LumeIDE uses ONLY google-genai (Client-based SDK).
    Conflicts with google-generativeai will cause import errors.
    """
    conflicts = []
    
    # Check for google-generativeai (old SDK - conflicts with google-genai)
    if importlib.util.find_spec("google-generativeai") is not None:
        conflicts.append("google-generativeai")
    
    # Check if both genai modules are present
    genai_spec = importlib.util.find_spec("google.genai")
    old_genai_spec = importlib.util.find_spec("google.generativeai")
    
    if genai_spec and old_genai_spec:
        conflicts.append("google.genai AND google.generativeai (both present)")
    
    if conflicts:
        print("=" * 60)
        print("⚠️  DEPENDENCY CONFLICT DETECTED!")
        print("=" * 60)
        print("\nLumeIDE requires ONLY 'google-genai' (google.genai module).")
        print("The following conflicting packages were detected:")
        for conflict in conflicts:
            print(f"  - {conflict}")
        print("\nPlease uninstall conflicting packages:")
        print("  pip uninstall google-generativeai")
        print("\nExpected package:")
        print("  pip install google-genai")
        print("=" * 60)
        return False
    
    return True


def main():
    """
    Initializes and runs the Lume IDE application.
    """
    # Run dependency check before importing app modules
    if not check_dependency_conflicts():
        print("\nAborting startup due to dependency conflicts.")
        sys.exit(1)
    
    app = QApplication(sys.argv)
    
    # Set application metadata
    app.setApplicationName("LumeIDE")
    app.setOrganizationName("Lume")
    
    # Load Dark+ High Contrast theme
    try:
        with open("dark_plus_high_contrast.qss", "r") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        print("Stylesheet 'dark_plus_high_contrast.qss' not found. Using default styles.")

    # Create and show main window
    main_window = MainWindow()
    main_window.show()

    # Start the event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
