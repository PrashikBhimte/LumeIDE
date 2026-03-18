"""
Error Recovery Module for LumeIDE

This module handles sending errors back to Gemini for automatic code fixing.
It provides a workflow for error handling and recovery.
"""

import json
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ErrorContext:
    """Context information for an error that occurred"""
    error_message: str
    error_type: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    command: Optional[str] = None
    stack_trace: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> dict:
        return {
            'error_message': self.error_message,
            'error_type': self.error_type,
            'file_path': self.file_path,
            'line_number': self.line_number,
            'command': self.command,
            'stack_trace': self.stack_trace,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }


class ErrorRecovery:
    """
    Error Recovery system that sends errors back to Gemini for automatic fixing.
    Maintains a history of errors and recovery attempts.
    """
    
    def __init__(self, aura_client=None, task_dispatcher=None):
        """
        Initialize the Error Recovery system.
        
        Args:
            aura_client: Instance of AuraClient for Gemini communication
            task_dispatcher: Instance of TaskDispatcher for executing fixes
        """
        self.aura_client = aura_client
        self.task_dispatcher = task_dispatcher
        self.error_history: List[ErrorContext] = []
        self.max_history = 50
        self.recovery_attempts = 0
        self.max_recovery_attempts = 3
    
    def set_aura_client(self, client):
        """Set the Aura client for Gemini communication"""
        self.aura_client = client
    
    def set_task_dispatcher(self, dispatcher):
        """Set the Task Dispatcher"""
        self.task_dispatcher = dispatcher
    
    def log_error(self, error_context: ErrorContext):
        """Log an error to the history"""
        self.error_history.append(error_context)
        if len(self.error_history) > self.max_history:
            self.error_history.pop(0)
    
    def parse_error(self, error_output: str) -> ErrorContext:
        """
        Parse an error output into an ErrorContext.
        
        Args:
            error_output: The raw error output string
            
        Returns:
            ErrorContext with parsed information
        """
        error_type = "Unknown"
        file_path = None
        line_number = None
        error_message = error_output
        
        # Try to parse Python traceback
        if "Traceback (most recent call last):" in error_output:
            error_type = "PythonError"
            lines = error_output.split('\n')
            for i, line in enumerate(lines):
                if 'File "' in line and 'line ' in line:
                    try:
                        # Parse file path and line number
                        parts = line.split('"')
                        if len(parts) >= 2:
                            file_path = parts[1]
                        # Extract line number
                        import re
                        match = re.search(r'line (\d+)', line)
                        if match:
                            line_number = int(match.group(1))
                    except:
                        pass
                elif i == len(lines) - 2 and lines[i + 1].strip():
                    error_message = lines[i + 1].strip()
        
        # Try to parse command execution errors
        elif "Command failed" in error_output:
            error_type = "CommandError"
            if "pip" in error_output.lower():
                error_type = "PipError"
            elif "python" in error_output.lower():
                error_type = "PythonExecutionError"
        
        # Try to parse syntax errors
        elif "SyntaxError" in error_output:
            error_type = "SyntaxError"
        
        # Try to parse import errors
        elif "ImportError" in error_output or "ModuleNotFoundError" in error_output:
            error_type = "ImportError"
        
        return ErrorContext(
            error_message=error_message,
            error_type=error_type,
            stack_trace=error_output if len(error_output) > 200 else None
        )
    
    def create_fix_prompt(self, error_context: ErrorContext, context: str = "") -> str:
        """
        Create a prompt for Gemini to fix the error.
        
        Args:
            error_context: The error context
            context: Additional context (e.g., file content)
            
        Returns:
            A prompt string to send to Gemini
        """
        prompt = f"""An error occurred while executing code. Please analyze the error and provide a fix.

## Error Information
- Error Type: {error_context.error_type}
- Error Message: {error_context.error_message}
- File: {error_context.file_path or 'Unknown'}
- Line: {error_context.line_number or 'Unknown'}
"""
        
        if error_context.stack_trace:
            prompt += f"""
## Stack Trace
```
{error_context.stack_trace}
```
"""
        
        if context:
            prompt += f"""
## File Context
```
{context}
```
"""
        
        prompt += """
## Instructions
1. Analyze the error carefully
2. If the error is in a file, read the current file content first
3. Fix the error and provide the corrected code
4. Use the write_file tool to save the fix if needed
5. If the error requires running a command (like pip install), use the run_command tool
6. Provide a brief explanation of what was wrong and how you fixed it
"""
        
        return prompt
    
    def attempt_recovery(self, error_output: str, context: str = "") -> Dict[str, Any]:
        """
        Attempt to recover from an error by sending it to Gemini for fixing.
        
        Args:
            error_output: The error output to recover from
            context: Additional context (e.g., file content)
            
        Returns:
            Dictionary with recovery result and details
        """
        if self.recovery_attempts >= self.max_recovery_attempts:
            return {
                'success': False,
                'error': 'Maximum recovery attempts reached',
                'attempts': self.recovery_attempts
            }
        
        if not self.aura_client:
            return {
                'success': False,
                'error': 'Aura client not configured'
            }
        
        # Parse the error
        error_context = self.parse_error(error_output)
        self.log_error(error_context)
        
        # Create fix prompt
        fix_prompt = self.create_fix_prompt(error_context, context)
        
        try:
            self.recovery_attempts += 1
            
            # Send to Gemini
            response = self.aura_client.send_prompt(fix_prompt)
            
            if response:
                return {
                    'success': True,
                    'response': response,
                    'error_context': error_context,
                    'attempts': self.recovery_attempts
                }
            else:
                return {
                    'success': False,
                    'error': 'No response from Gemini',
                    'error_context': error_context,
                    'attempts': self.recovery_attempts
                }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'error_context': error_context,
                'attempts': self.recovery_attempts
            }
    
    def execute_fix_with_retry(self, tool_calls: List[Dict], 
                                on_error: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Execute a series of tool calls with automatic error recovery.
        
        Args:
            tool_calls: List of tool calls to execute
            on_error: Optional callback for error handling
            
        Returns:
            Dictionary with execution results
        """
        if not self.task_dispatcher:
            return {'success': False, 'error': 'Task dispatcher not configured'}
        
        results = []
        
        for i, tool_call in enumerate(tool_calls):
            tool_name = tool_call.get('name')
            parameters = tool_call.get('parameters', {})
            
            try:
                result = self.task_dispatcher.dispatch(tool_name, parameters)
                results.append(result)
                
                if not result.get('success', False):
                    error_msg = result.get('error', 'Unknown error')
                    
                    # Trigger error callback
                    if on_error:
                        on_error(error_msg, tool_call, i)
                    
                    # Attempt recovery
                    recovery_result = self.attempt_recovery(error_msg)
                    
                    if recovery_result.get('success'):
                        # Gemini provided a fix, add to results
                        results.append({
                            'type': 'recovery',
                            'success': True,
                            'response': recovery_result.get('response')
                        })
                    else:
                        # Recovery failed
                        return {
                            'success': False,
                            'error': error_msg,
                            'failed_at': i,
                            'recovery_attempted': True,
                            'recovery_result': recovery_result,
                            'partial_results': results
                        }
            
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e),
                    'failed_at': i,
                    'partial_results': results
                }
        
        return {
            'success': True,
            'results': results
        }
    
    def get_error_history(self) -> List[Dict]:
        """Get the error history as a list of dictionaries"""
        return [err.to_dict() for err in self.error_history]
    
    def get_last_error(self) -> Optional[ErrorContext]:
        """Get the most recent error"""
        return self.error_history[-1] if self.error_history else None
    
    def clear_history(self):
        """Clear the error history"""
        self.error_history.clear()
        self.recovery_attempts = 0
    
    def export_error_report(self) -> str:
        """Export a formatted error report"""
        if not self.error_history:
            return "No errors recorded."
        
        report = ["# Error Recovery Report", "=" * 50, ""]
        report.append(f"Total Errors: {len(self.error_history)}")
        report.append(f"Recovery Attempts: {self.recovery_attempts}")
        report.append("")
        
        for i, error in enumerate(self.error_history, 1):
            report.append(f"## Error {i}")
            report.append(f"- Type: {error.error_type}")
            report.append(f"- Message: {error.error_message}")
            if error.file_path:
                report.append(f"- File: {error.file_path}")
            if error.line_number:
                report.append(f"- Line: {error.line_number}")
            report.append(f"- Time: {error.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            report.append("")
        
        return "\n".join(report)


# Export for use by other modules
__all__ = ['ErrorRecovery', 'ErrorContext']
