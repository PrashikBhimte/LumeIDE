
from PyQt6.QtCore import QObject, pyqtSignal

class AuraWorker(QObject):
    finished = pyqtSignal(object)

    def __init__(self, aura_client, prompt, stream):
        super().__init__()
        self.aura_client = aura_client
        self.prompt = prompt
        self.stream = stream

    def run(self):
        result = self.aura_client.send_prompt(self.prompt, stream=self.stream)
        self.finished.emit(result)
