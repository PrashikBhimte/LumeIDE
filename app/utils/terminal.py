from PyQt6.QtCore import QObject, QProcess, pyqtSignal

class Terminal(QObject):
    """
    A wrapper around QProcess to run a shell and handle its I/O.
    """
    output_received = pyqtSignal(str)
    error_received = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)

    def start(self, shell: str = "powershell.exe", args: list = None):
        """
        Starts the shell process.

        Args:
            shell (str): The command to start the shell (e.g., 'powershell.exe', 'cmd.exe').
            args (list): A list of arguments to pass to the shell command.
        """
        if self.process.state() == QProcess.ProcessState.NotRunning:
            if args:
                self.process.start(shell, args)
            else:
                self.process.start(shell)
            
            if not self.process.waitForStarted():
                self.error_received.emit(f"Failed to start: {self.process.errorString()}")
        else:
            self.error_received.emit("Shell is already running.")

    def run_command(self, command: str):
        """
        Writes a command to the shell's standard input. A newline is automatically appended.
        """
        if self.process.state() == QProcess.ProcessState.Running:
            command_to_write = command + '
'
            self.process.write(command_to_write.encode('utf-8'))
        else:
            self.error_received.emit("Cannot run command: Shell is not running.")

    def handle_stdout(self):
        """
        Reads and emits standard output from the process.
        """
        data = self.process.readAllStandardOutput().data().decode('utf-8', errors='ignore')
        self.output_received.emit(data)

    def handle_stderr(self):
        """
        Reads and emits standard error from the process.
        """
        data = self.process.readAllStandardError().data().decode('utf-8', errors='ignore')
        self.error_received.emit(data)

    def close(self):
        """
        Terminates the shell process gracefully.
        """
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.terminate()
            if not self.process.waitForFinished(3000):  # Wait 3s
                self.process.kill()
                self.process.waitForFinished()

if __name__ == '__main__':
    import sys
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import QTimer

    app = QApplication(sys.argv)

    print("--- Testing Terminal Class ---")
    terminal = Terminal()

    def display_output(text):
        print(f"STDOUT: {text.strip()}")

    def display_error(text):
        print(f"STDERR: {text.strip()}")

    terminal.output_received.connect(display_output)
    terminal.error_received.connect(display_error)
    
    # Start PowerShell
    terminal.start()

    # Run some commands
    terminal.run_command("echo Hello from Lume Terminal")
    terminal.run_command("$PSVersionTable.PSVersion")
    
    # Schedule to close the app and terminal after a delay
    QTimer.singleShot(3000, lambda: (terminal.close(), app.quit()))
    
    sys.exit(app.exec())
