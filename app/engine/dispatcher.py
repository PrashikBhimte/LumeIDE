"""
Unified Command Dispatcher for LumeIDE
"""

import os
import subprocess
from typing import Optional, Any

from app.engine.aura_client import AuraClient
from app.models.project_context import ProjectContext
from app.ui.editor_area import EditorArea

class CommandDispatcher:
    """
    Dispatches commands from the Unified Shell to local execution or Aura.
    """

    def __init__(
        self,
        project_context: ProjectContext,
        aura_client: AuraClient,
        editor_area: EditorArea,
    ):
        self.project_context = project_context
        self.aura_client = aura_client
        self.editor_area = editor_area
        self.terminal_history: list[str] = []

    def dispatch(self, command: str) -> Optional[tuple[str, str]]:
        """
        Dispatches a command. For local commands, it returns the output and color.
        For Aura commands, it initiates the generation and returns None.

        Args:
            command: The command string from the user.

        Returns:
            A tuple of (output, color) for local commands, otherwise None.
        """
        self.terminal_history.append(f"User: {command}")
        if len(self.terminal_history) > 10:
            self.terminal_history.pop(0)

        command_lower = command.lower().strip()
        parts = command_lower.split()
        
        # Local Execution
        if parts[0] in ["python", "pip", "dir", "cd", "git", "echo"]:
            output = self._run_local_command(command)
            color = "green"
            self.terminal_history.append(f"Shell: {output}")
            return output, color

        # Intent Parsing
        if command_lower in ["run this", "run file", "execute"]:
            active_file = self.editor_area.get_current_file()
            if active_file and active_file.endswith(".py"):
                python_executable = os.path.join(
                    self.project_context.venv_path, "Scripts", "python.exe"
                ) if self.project_context.venv_path else "python"
                run_command = f"{python_executable} {active_file}"
                output = self._run_local_command(run_command)
                color = "green"
                self.terminal_history.append(f"Shell: {output}")
                return output, color
            else:
                output = "Error: No active Python file to run."
                color = "red"
                self.terminal_history.append(f"Error: {output}")
                return output, color

        # Aura Brain
        else:
            active_file_path = self.editor_area.get_current_file()
            file_content = ""
            if active_file_path:
                try:
                    with open(active_file_path, "r") as f:
                        file_content = f.read()
                except Exception:
                    # Silently fail for now, or add logging
                    pass

            terminal_context = "\n".join(self.terminal_history[-5:])
            
            prompt = f"Active File: {active_file_path}\n"
            prompt += f"File Content:\n```\n{file_content}\n```\n\n"
            prompt += f"Terminal Context:\n{terminal_context}\n\n"
            prompt += f"User Query: {command}"

            self.aura_client.generate_response(prompt)
            return None

    def _run_local_command(self, command: str) -> str:
        """
        Executes a command locally in the project's root directory.
        """
        try:
            # Change directory to project root if needed
            # For simplicity, assuming the CWD is correct for now.
            # A more robust solution would use self.project_context.root_path
            
            # Special handling for 'cd'
            if command.strip().startswith("cd "):
                path = command.strip().split(" ", 1)[1]
                try:
                    os.chdir(path)
                    return f"Changed directory to {os.getcwd()}"
                except FileNotFoundError:
                    return f"Error: Directory not found: {path}"
                except Exception as e:
                    return f"Error changing directory: {e}"

            # Use venv python if specified
            if command.strip().startswith("python ") and self.project_context.venv_path:
                 command = command.replace("python", os.path.normpath(os.path.join(self.project_context.venv_path, "Scripts", "python.exe")), 1)
            
            if command.strip().startswith("pip ") and self.project_context.venv_path:
                 command = command.replace("pip", os.path.normpath(os.path.join(self.project_context.venv_path, "Scripts", "pip.exe")), 1)


            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=self.project_context.root_path,
            )
            
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()

            if stderr and result.returncode != 0:
                # For commands like 'git' that use stderr for info, we don't want to always show it as an error
                if "error" in stderr.lower() or "fatal" in stderr.lower():
                     return f"Error:{stderr}"
                else:
                    return f"{stdout}{stderr}"
            return stdout if stdout else stderr

        except Exception as e:
            return f"Execution Error: {str(e)}"

__all__ = ["CommandDispatcher"]
