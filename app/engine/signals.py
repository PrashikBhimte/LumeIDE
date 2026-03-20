from PyQt6.QtCore import QObject, pyqtSignal

class AuraSignals(QObject):
    started_thinking = pyqtSignal()
    tool_used = pyqtSignal(str, dict)
    finished = pyqtSignal(object)
