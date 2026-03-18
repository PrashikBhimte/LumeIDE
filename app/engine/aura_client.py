"""
Aura Client Module for LumeIDE

Client for interacting with Google's Gemini models using the latest google-genai SDK.
"""

import os
import json
import threading
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass

# Use the latest google-genai SDK
from google import genai


def tool_read_file(path: str) -> str:
    """
    Reads the content of a file at the given path.
    This tool is meant to be used by the Gemini model.
    """
    try:
        normalized = os.path.normpath(path)
        with open(normalized, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: File not found at path: {path}"
    except Exception as e:
        return f"Error reading file at {path}: {e}"


def tool_write_file(path: str, content: str) -> str:
    """
    Writes or overwrites content to a file at the specified path.
    """
    try:
        normalized = os.path.normpath(path)
        # Ensure directories exist
        os.makedirs(os.path.dirname(normalized), exist_ok=True)
        with open(normalized, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote to {path}"
    except Exception as e:
        return f"Error writing to file at {path}: {str(e)}"


@dataclass
class GenerationResult:
    """Result of a generation request."""
    text: Optional[str]
    candidates: Optional[List]
    prompt_feedback: Optional[Dict]
    error: Optional[str] = None


class AuraClient:
    """
    A client for interacting with Google's Gemini models.
    Supports streaming responses and abort mechanism.
    """

    def __init__(self, api_key: str = None, model_name: str = "gemini-2.0-flash"):
        """
        Initializes the AuraClient.

        Args:
            api_key: The Google AI API key. If not provided, it's read from
                     the GEMINI_API_KEY environment variable.
            model_name: The name of the Gemini model to use.
        """
        if api_key is None:
            api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "API key for Gemini must be provided either as an argument or "
                "as the GEMINI_API_KEY environment variable."
            )

        self.api_key = api_key
        self.model_name = model_name
        self._client = None
        self._current_response = None
        self._abort_event = threading.Event()
        self._is_streaming = False
        self._callbacks = []

        # Initialize client
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the Gemini client."""
        try:
            self._client = genai.Client(api_key=self.api_key)
            print(f"AuraClient initialized with model: {self.model_name}")
        except Exception as e:
            print(f"Error initializing Gemini client: {e}")
            raise

    def register_callback(self, callback: Callable[[str], None]):
        """
        Register a callback for streaming responses.

        Args:
            callback: Function that receives text chunks as they arrive
        """
        self._callbacks.append(callback)

    def unregister_callback(self, callback: Callable[[str], None]):
        """Remove a registered callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _notify_callbacks(self, text: str):
        """Notify all registered callbacks of new text."""
        for callback in self._callbacks:
            try:
                callback(text)
            except Exception as e:
                print(f"Callback error: {e}")

    def send_prompt(
        self,
        prompt_text: str,
        tools: List = None,
        system_instruction: str = None,
        stream: bool = True
    ) -> GenerationResult:
        """
        Sends a prompt to the Gemini model and gets a response.
        Supports streaming for real-time responses.

        Args:
            prompt_text: The user's prompt
            tools: List of tool functions to make available to the model
            system_instruction: System-level instructions
            stream: Whether to stream the response

        Returns:
            GenerationResult with response data
        """
        self._abort_event.clear()
        self._is_streaming = stream

        try:
            # Build generation config
            config = genai.types.GenerateContentConfig(
                tools=tools or [
                    genai.types.Tool(
                        function_declarations=[
                            {
                                "name": "read_file",
                                "description": "Read the content of a file at the given path",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "path": {"type": "string", "description": "Path to the file to read"}
                                    },
                                    "required": ["path"]
                                }
                            },
                            {
                                "name": "write_file",
                                "description": "Write or overwrite content to a file",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "path": {"type": "string", "description": "Path to the file to write"},
                                        "content": {"type": "string", "description": "Content to write"}
                                    },
                                    "required": ["path", "content"]
                                }
                            }
                        ]
                    )
                ],
                system_instruction=system_instruction
            )

            # Generate content
            full_response = ""

            if stream:
                # Streaming response
                response_stream = self._client.models.generate_content_stream(
                    model=self.model_name,
                    contents=prompt_text,
                    config=config
                )

                for chunk in response_stream:
                    if self._abort_event.is_set():
                        # Abort was requested
                        return GenerationResult(
                            text=full_response,
                            candidates=None,
                            prompt_feedback=None,
                            error="Generation aborted by user"
                        )

                    if chunk.text:
                        full_response += chunk.text
                        self._notify_callbacks(chunk.text)

                self._is_streaming = False
                return GenerationResult(
                    text=full_response,
                    candidates=None,
                    prompt_feedback=None
                )
            else:
                # Non-streaming response
                response = self._client.models.generate_content(
                    model=self.model_name,
                    contents=prompt_text,
                    config=config
                )

                return GenerationResult(
                    text=response.text if hasattr(response, 'text') else None,
                    candidates=response.candidates if hasattr(response, 'candidates') else None,
                    prompt_feedback=response.prompt_feedback if hasattr(response, 'prompt_feedback') else None
                )

        except Exception as e:
            error_msg = str(e)
            print(f"Error generating content: {error_msg}")
            return GenerationResult(
                text=None,
                candidates=None,
                prompt_feedback=None,
                error=error_msg
            )

    def abort(self):
        """
        Abort the current generation request.
        Sets an internal flag that causes streaming to stop.
        """
        if self._is_streaming:
            self._abort_event.set()
            self._is_streaming = False
            print("Generation abort requested")

    def is_generating(self) -> bool:
        """Check if a generation is currently in progress."""
        return self._is_streaming

    def get_current_response(self) -> Optional[str]:
        """Get the current accumulated response text."""
        return self._current_response

    def configure_model(self, model_name: str):
        """Change the active model."""
        self.model_name = model_name
        print(f"Model changed to: {model_name}")


# Vault Toolset - Additional tools for Aura
class VaultToolset:
    """
    Additional tools for file operations and system commands.
    """

    def __init__(self, working_dir: str = None):
        self.working_dir = working_dir or os.getcwd()

    def pip_freeze(self) -> str:
        """
        Get list of installed packages using pip freeze.
        Returns the output of pip freeze command.
        """
        import subprocess
        try:
            # Try to use venv pip first
            venv_pip = os.path.join(self.working_dir, 'venv', 'Scripts', 'pip.exe')
            if os.path.exists(venv_pip):
                result = subprocess.run(
                    [venv_pip, 'freeze'],
                    capture_output=True,
                    text=True,
                    cwd=self.working_dir,
                    timeout=30
                )
            else:
                result = subprocess.run(
                    ['pip', 'freeze'],
                    capture_output=True,
                    text=True,
                    cwd=self.working_dir,
                    timeout=30
                )

            if result.returncode == 0:
                return result.stdout
            else:
                return f"Error: {result.stderr}"
        except subprocess.TimeoutExpired:
            return "Error: pip freeze timed out"
        except Exception as e:
            return f"Error running pip freeze: {str(e)}"

    def get_venv_packages(self) -> List[str]:
        """Get list of installed packages from venv."""
        freeze_output = self.pip_freeze()
        if freeze_output.startswith("Error:"):
            return []
        return [line.strip() for line in freeze_output.strip().split('\n') if line.strip()]


# Export
__all__ = ['AuraClient', 'VaultToolset', 'GenerationResult', 'tool_read_file', 'tool_write_file']
