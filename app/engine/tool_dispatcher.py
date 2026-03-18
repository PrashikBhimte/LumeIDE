"""
Task Dispatcher Module for LumeIDE

This module handles routing of Gemini's tool use requests to the appropriate
Python functions. It acts as a central hub for executing AI-suggested actions.
"""

import subprocess
import os
import json
from typing import Any, Callable, Dict, Optional
from app.utils.file_system import tool_read_file, tool_write_file


class TaskDispatcher:
    """
    Task Dispatcher that routes Gemini's tool use requests to the right Python function.
    Supports execution of pip/python commands and file operations.
    """
    
    def __init__(self, working_dir: str = None):
        """
        Initialize the Task Dispatcher.
        
        Args:
            working_dir: The current working directory for command execution
        """
        self.working_dir = working_dir or os.getcwd()
        self.last_error: Optional[str] = None
        self.last_output: Optional[str] = None
        
        # Registry of available tools
        self._tools: Dict[str, Callable] = {
            'read_file': self._exec_read_file,
            'write_file': self._exec_write_file,
            'run_command': self._exec_run_command,
            'pip_install': self._exec_pip_install,
            'python_execute': self._exec_python,
            'list_directory': self._exec_list_directory,
            'create_directory': self._exec_create_directory,
            'delete_file': self._exec_delete_file,
        }
    
    def dispatch(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dispatch a tool call to the appropriate handler.
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Dictionary of parameters for the tool
            
        Returns:
            Dictionary containing success status and result/error
        """
        self.last_error = None
        self.last_output = None
        
        if tool_name not in self._tools:
            error_msg = f"Unknown tool: {tool_name}. Available tools: {list(self._tools.keys())}"
            self.last_error = error_msg
            return {
                'success': False,
                'error': error_msg,
                'tool': tool_name
            }
        
        try:
            result = self._tools[tool_name](parameters)
            self.last_output = str(result)
            return {
                'success': True,
                'result': result,
                'tool': tool_name
            }
        except Exception as e:
            error_msg = f"Error executing {tool_name}: {str(e)}"
            self.last_error = error_msg
            return {
                'success': False,
                'error': error_msg,
                'tool': tool_name,
                'exception': str(e)
            }
    
    def _exec_read_file(self, params: Dict[str, Any]) -> str:
        """Execute read_file tool"""
        path = params.get('path')
        if not path:
            raise ValueError("path parameter is required for read_file")
        return tool_read_file(path)
    
    def _exec_write_file(self, params: Dict[str, Any]) -> str:
        """Execute write_file tool"""
        path = params.get('path')
        content = params.get('content')
        if not path:
            raise ValueError("path parameter is required for write_file")
        if content is None:
            raise ValueError("content parameter is required for write_file")
        return tool_write_file(path, content)
    
    def _exec_run_command(self, params: Dict[str, Any]) -> str:
        """Execute a shell command"""
        cmd = params.get('cmd')
        if not cmd:
            raise ValueError("cmd parameter is required for run_command")
        
        cwd = params.get('cwd', self.working_dir)
        timeout = params.get('timeout', 60)
        
        return tool_run_command(cmd, cwd=cwd, timeout=timeout)
    
    def _exec_pip_install(self, params: Dict[str, Any]) -> str:
        """Execute pip install command"""
        packages = params.get('packages', [])
        if isinstance(packages, str):
            packages = [packages]
        
        cmd = f"pip install {' '.join(packages)}"
        return tool_run_command(cmd, cwd=self.working_dir)
    
    def _exec_python(self, params: Dict[str, Any]) -> str:
        """Execute a Python script or command"""
        script = params.get('script')
        file_path = params.get('file')
        
        if file_path:
            cmd = f"python {file_path}"
        elif script:
            cmd = f"python -c \"{script}\""
        else:
            raise ValueError("Either 'script' or 'file' parameter is required for python_execute")
        
        return tool_run_command(cmd, cwd=self.working_dir)
    
    def _exec_list_directory(self, params: Dict[str, Any]) -> str:
        """List contents of a directory"""
        path = params.get('path', self.working_dir)
        try:
            contents = os.listdir(path)
            return json.dumps({'files': contents, 'path': path})
        except Exception as e:
            raise RuntimeError(f"Failed to list directory: {str(e)}")
    
    def _exec_create_directory(self, params: Dict[str, Any]) -> str:
        """Create a directory"""
        path = params.get('path')
        if not path:
            raise ValueError("path parameter is required for create_directory")
        
        os.makedirs(path, exist_ok=True)
        return f"Directory created: {path}"
    
    def _exec_delete_file(self, params: Dict[str, Any]) -> str:
        """Delete a file"""
        path = params.get('path')
        if not path:
            raise ValueError("path parameter is required for delete_file")
        
        if os.path.isfile(path):
            os.remove(path)
            return f"File deleted: {path}"
        elif os.path.isdir(path):
            import shutil
            shutil.rmtree(path)
            return f"Directory deleted: {path}"
        else:
            raise FileNotFoundError(f"Path not found: {path}")
    
    def get_available_tools(self) -> list:
        """Return list of available tool names"""
        return list(self._tools.keys())
    
    def set_working_directory(self, path: str):
        """Set the working directory for command execution"""
        if os.path.isdir(path):
            self.working_dir = path
        else:
            raise ValueError(f"Invalid directory: {path}")


def tool_run_command(cmd: str, cwd: str = None, timeout: int = 60) -> str:
    """
    Execute a shell command (pip/python) and return the output.
    
    Args:
        cmd: The command to execute
        cwd: Working directory for the command (defaults to current directory)
        timeout: Maximum time to wait for command completion (seconds)
        
    Returns:
        Combined stdout and stderr output from the command
        
    Raises:
        RuntimeError: If the command fails or times out
    """
    if cwd is None:
        cwd = os.getcwd()
    
    try:
        # Execute the command
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        # Combine stdout and stderr
        output = result.stdout
        if result.stderr:
            output = output + "\n[STDERR]\n" + result.stderr
        
        if result.returncode != 0:
            raise RuntimeError(
                f"Command failed with exit code {result.returncode}:\n{output}"
            )
        
        return output if output else "Command executed successfully (no output)"
    
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Command timed out after {timeout} seconds: {cmd}")
    except Exception as e:
        raise RuntimeError(f"Failed to execute command '{cmd}': {str(e)}")


# Export for use by other modules
__all__ = ['TaskDispatcher', 'tool_run_command']
