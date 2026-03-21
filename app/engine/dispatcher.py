"""
Unified Command Dispatcher for LumeIDE

Handles routing of commands from the unified terminal to either:
- Shell execution (for terminal commands)
- Aura AI (for natural language queries)

The dispatcher intelligently determines which execution path to use based on
the input format.
"""

import os
import subprocess
import re
from typing import Optional, Any, Tuple

from app.engine.aura_client import AuraClient
from app.models.project_context import ProjectContext
from app.ui.editor_area import EditorArea


class CommandDispatcher:
    """
    Dispatches commands from the Unified Shell to local execution or Aura.
    
    Command Detection Logic:
    - Shell commands: git, python, npm, cd, etc. are executed locally
    - Natural language: questions, explanations, code requests go to Aura
    """

    # Known shell commands that should always be executed locally
    SHELL_COMMANDS = {
        # Navigation
        'cd', 'pwd', 'ls', 'dir', 'll', 'la', 'll',
        # File operations
        'mkdir', 'rmdir', 'rm', 'del', 'copy', 'cp', 'move', 'mv', 'ren', 'rename',
        'cat', 'type', 'head', 'tail', 'grep', 'find', 'locate', 'touch', 'chmod', 'chown',
        'findstr', 'fc', 'comp',
        # Git
        'git', 'gh',
        # Python
        'python', 'python3', 'py', 'pip', 'pip3', 'conda', 'uv', 'poetry',
        # Package managers
        'npm', 'yarn', 'pnpm', 'bun', 'cargo', 'go', 'mvn', 'gradle', 'make', 'cmake',
        # Development
        'code', 'vim', 'nvim', 'nano', 'emacs', 'ssh', 'scp', 'rsync', 'docker', 'docker-compose',
        # System
        'echo', 'print', 'printf', 'export', 'env', 'set', 'unset', 'alias', 'unalias', 
        'which', 'where', 'whereis', 'type', 'command',
        'kill', 'ps', 'pkill', 'top', 'htop', 'systeminfo', 'tasklist', 'taskkill',
        'wmic', 'reg', 'icacls',
        # Network
        'curl', 'wget', 'ping', 'netstat', 'ipconfig', 'ifconfig', 'nslookup', 'dig',
        'traceroute', 'tracert', 'net', 'nbtstat', 'arp', 'route',
        # Archive
        'zip', 'unzip', 'tar', 'gzip', 'gunzip', '7z', 'rar', 'bunzip2',
        # Text processing
        'sed', 'awk', 'cut', 'sort', 'uniq', 'wc', 'diff', 'patch',
        # Other
        'clear', 'cls', 'history', 'man', 'help', 'exit', 'quit', 'q', 'logout',
        'reboot', 'shutdown', 'sleep', 'wait', 'sleep',
        # Build tools
        'build', 'run', 'start', 'stop', 'restart', 'deploy',
        # Process
        'taskmgr', 'services', 'compmgmt', 'devmgmt', 'diskmgmt',
    }

    # Patterns that indicate shell commands
    SHELL_PATTERNS = [
        r'^[a-zA-Z]:\\',  # Windows absolute paths (C:\)
        r'^/',  # Unix absolute paths
        r'^\.\.?/',  # Relative paths
        r'^~/',  # Home directory paths
        r'^\\',  # UNC paths
        r'^\$[a-zA-Z_]',  # Environment variables
        r'^%[a-zA-Z_]+%',  # Windows environment variables
        r'^\|\s',  # Pipe
        r'^>\s',  # Output redirect
        r'^<\s',  # Input redirect
        r'^2>\s',  # Error redirect
        r'^&&\s',  # And
        r'^\|\|\s',  # Or
    ]

    # Patterns that indicate natural language (AI commands)
    AI_PATTERNS = [
        r'^what\s', r'^how\s', r'^why\s', r'^when\s', r'^where\s', r'^who\s',
        r'^explain\s', r'^describe\s', r'^tell\s', r'^show\s',
        r'^can\syou\s', r'^could\syou\s', r'^would\syou\s',
        r'^please\s', r'^can\si\s',
        r'^what\sis\s', r'^what\sdoes\s', r'^what\sare\s',
        r'^how\sdo\s', r'^how\sdoes\s', r'^how\scan\s',
        r'^why\sis\s', r'^why\sdoes\s', r'^why\sdoes\s',
        r'^fix\s', r'^fix\s', r'^bug\s',
        r'^create\s', r'^make\s', r'^build\s', r'^add\s',
        r'^write\s', r'^generate\s', r'^implement\s',
        r'^help\s', r'^assist\s', r'^assist\s',
        r'^debug\s', r'^debug\s', r'^error\s',
        r'^refactor\s', r'^optimize\s', r'^improve\s',
        r'^test\s', r'^run\s', r'^execute\s', r'^run\s',
        r'^review\s', r'^check\s', r'^validate\s', r'^verify\s',
    ]

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

    def is_shell_command(self, command: str) -> bool:
        """
        Determine if the command should be executed as a shell command.
        
        Args:
            command: The command string to check
            
        Returns:
            True if it should be executed locally, False if it should go to Aura
        """
        command = command.strip()
        if not command:
            return False
        
        command_lower = command.lower()
        
        # Check if first word is a known shell command
        first_word = command_lower.split()[0] if command.split() else ''
        
        # Remove any path prefixes for the check
        clean_first = first_word.replace('\\', '/').split('/')[-1]
        
        if clean_first in self.SHELL_COMMANDS:
            return True
        
        # Check for path patterns
        for pattern in self.SHELL_PATTERNS:
            if re.match(pattern, command):
                return True
        
        # Check for command operators
        if '|' in command or '>' in command or '&' in command:
            return True
        
        return False

    def dispatch(self, command: str) -> Optional[Tuple[str, str]]:
        """
        Dispatches a command. For local commands, it returns the output and color.
        For Aura commands, it initiates the generation and returns None.

        Args:
            command: The command string from the user.

        Returns:
            A tuple of (output, color) for local commands, otherwise None.
        """
        command = command.strip()
        if not command:
            return ("", None)

        self.terminal_history.append(command)
        if len(self.terminal_history) > 50:
            self.terminal_history.pop(0)

        # Determine if shell or AI command
        if self.is_shell_command(command):
            return self._execute_shell(command)
        else:
            return self._execute_ai(command)

    def _execute_shell(self, command: str) -> Tuple[str, str]:
        """Execute a shell command locally."""
        output = self._run_local_command(command)
        color = "error" if output.startswith("Error:") or "error" in output.lower()[:50] else "green"
        self.terminal_history.append(f"Shell: {output}")
        return output, color

    def _execute_ai(self, command: str) -> None:
        """Route command to Aura AI."""
        if not self.aura_client:
            return ("Error: Aura AI not configured. Please set your API key.", "error")

        # Build context for AI
        active_file_path = self.editor_area.get_current_file()
        file_content = ""
        if active_file_path:
            try:
                with open(active_file_path, "r", encoding='utf-8') as f:
                    file_content = f.read()
            except Exception:
                pass

        # Build context prompt
        context_parts = []
        
        if active_file_path:
            context_parts.append(f"Active File: {active_file_path}")
        
        if file_content:
            # Truncate large files
            if len(file_content) > 4000:
                file_content = file_content[:4000] + "\n... (truncated)"
            context_parts.append(f"File Content:\n```\n{file_content}\n```")
        
        if self.terminal_history[-5:-1]:
            context_parts.append(f"Recent Commands:\n" + "\n".join(self.terminal_history[-5:-1]))
        
        context = "\n\n".join(context_parts)
        
        prompt = f"""{context}

User Request: {command}

Please help with this request. Use the available tools to read files, write code, and perform necessary actions."""

        self.aura_client.generate_response(prompt)
        return None

    def _run_local_command(self, command: str) -> str:
        """
        Executes a command locally in the project's root directory.
        """
        try:
            # Special handling for 'cd' - just change directory
            if command.strip().lower().startswith("cd "):
                path = command.strip()[3:].strip()
                
                # Handle quoted paths
                if path.startswith('"') and path.endswith('"'):
                    path = path[1:-1]
                elif path.startswith("'") and path.endswith("'"):
                    path = path[1:-1]
                
                # Handle home directory
                if path == '~' or path == '$HOME':
                    path = os.path.expanduser('~')
                
                try:
                    os.chdir(path)
                    return os.getcwd()
                except FileNotFoundError:
                    return f"Error: Directory not found: {path}"
                except Exception as e:
                    return f"Error changing directory: {e}"

            # Use venv python if specified and available
            working_command = command
            if self.project_context.venv_path:
                venv_python = os.path.normpath(os.path.join(self.project_context.venv_path, "Scripts", "python.exe"))
                venv_pip = os.path.normpath(os.path.join(self.project_context.venv_path, "Scripts", "pip.exe"))
                
                if command.strip().lower().startswith("python "):
                    working_command = command.replace("python ", f'"{venv_python}" ', 1)
                elif command.strip().lower().startswith("pip "):
                    working_command = command.replace("pip ", f'"{venv_pip}" ', 1)

            # Determine working directory
            cwd = self.project_context.root_path or os.getcwd()
            
            # Run command
            result = subprocess.run(
                working_command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=120,  # 2 minute timeout
                encoding='utf-8',
                errors='replace'
            )
            
            # Combine stdout and stderr
            output = result.stdout.strip() if result.stdout else ""
            stderr = result.stderr.strip() if result.stderr else ""
            
            if stderr and result.returncode != 0:
                if "error" in stderr.lower() or "fatal" in stderr.lower():
                    return f"Error: {stderr}"
                elif output:
                    return f"{output}\n{stderr}"
                else:
                    return stderr
            
            return output if output else (stderr if stderr else "")

        except subprocess.TimeoutExpired:
            return "Error: Command timed out after 2 minutes"
        except Exception as e:
            return f"Error: {str(e)}"


__all__ = ["CommandDispatcher"]
