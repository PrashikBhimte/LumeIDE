"""
Aura Client Module for LumeIDE

Client for interacting with Google's Gemini models using the google-genai SDK.
Handles AI-powered code generation and tool execution.
"""

import os
import threading
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Callable

from PyQt6.QtCore import QObject, pyqtSignal, QThread

# Use the google-genai SDK (NOT google-generativeai)
from google import genai
from google.genai import types

from app.engine.tools import TOOL_FUNCTIONS


@dataclass
class GenerationResult:
    """Result of a generation request."""
    text: Optional[str]
    candidates: Optional[List[Any]] = None
    prompt_feedback: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class AuraWorker(QObject):
    """Worker thread for async generation."""
    finished = pyqtSignal(object)

    def __init__(self, client_instance, prompt_text, tools, system_instruction):
        super().__init__()
        self.client_instance = client_instance
        self.prompt_text = prompt_text
        self.tools = tools
        self.system_instruction = system_instruction

    def run(self):
        result = self.client_instance.generate_response_sync(
            self.prompt_text, 
            self.tools, 
            self.system_instruction
        )
        self.finished.emit(result)


class AuraClient(QObject):
    """
    A client for interacting with Google's Gemini models.
    Powered by the google-genai SDK.
    
    Supports tool calling for file operations and provides
    signals for UI updates during generation.
    """
    
    # Signals for UI updates
    started_thinking = pyqtSignal()
    tool_used = pyqtSignal(str, dict)
    finished = pyqtSignal(object)
    
    def __init__(self, api_key: str = None, model_name: str = "gemini-2.0-flash"):
        super().__init__()
        
        # Get API key from argument or environment
        if api_key is None:
            api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "API key for Gemini must be provided either as an argument or "
                "as the GEMINI_API_KEY environment variable."
            )

        self.api_key = api_key
        self.model_name = model_name
        self.client = None
        self._abort_event = threading.Event()
        
        # Tool functions dictionary - keys MUST match function names EXACTLY
        # These are the names the model will use when calling tools
        self.tool_functions: Dict[str, Callable] = {
            "read_file": TOOL_FUNCTIONS["read_file"],
            "write_file": TOOL_FUNCTIONS["write_file"],
            "create_directory": TOOL_FUNCTIONS["create_directory"],
            "list_directory": TOOL_FUNCTIONS["list_directory"],
        }
        
        self.thread = None
        self.worker = None
        self._is_streaming = False
        
        # Initialize the client
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the Gemini client using google-genai SDK."""
        try:
            self.client = genai.Client(api_key=self.api_key)
            print(f"AuraClient initialized with model: {self.model_name}")
        except Exception as e:
            print(f"Error initializing Gemini client: {e}")
            raise

    def generate_response(
        self,
        prompt_text: str,
        tools: List = None,
        system_instruction: str = None
    ):
        """
        Generate a response asynchronously using a worker thread.
        
        Args:
            prompt_text: The user's prompt
            tools: List of tool functions (optional, defaults to built-in tools)
            system_instruction: System-level instructions
        """
        self.thread = QThread()
        self.worker = AuraWorker(self, prompt_text, tools, system_instruction)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_generation_finished)
        self.thread.finished.connect(self.thread.deleteLater)
        
        self.started_thinking.emit()
        self.thread.start()

    def on_generation_finished(self, result):
        """Handle generation completion."""
        self.finished.emit(result)
        self.thread.quit()

    def generate_response_sync(
        self,
        prompt_text: str,
        tools: List = None,
        system_instruction: str = None,
        stream: bool = False 
    ) -> GenerationResult:
        """
        Generate a response synchronously with tool execution support.
        
        Args:
            prompt_text: The user's prompt
            tools: List of tool functions
            system_instruction: System-level instructions
            stream: Whether to stream the response (not fully implemented)
        
        Returns:
            GenerationResult with response text or error
        """
        try:
            # Use built-in tools if none provided
            if tools is None:
                tools = list(self.tool_functions.values())
            
            # Build function declarations for the API
            function_declarations = self._build_function_declarations()
            
            # Configure generation with tools
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=[
                    types.Tool(
                        function_declarations=function_declarations
                    )
                ],
                # Disable automatic function calling so we can handle it manually
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                temperature=0.2  # Lower temperature for coding consistency
            )

            # Create chat session
            chat = self.client.chats.create(
                model=self.model_name,
                config=config
            )
            
            # Send initial prompt
            response = chat.send_message(prompt_text)

            # Handle function calls in a loop
            max_iterations = 10  # Prevent infinite loops
            iteration = 0
            
            while response.function_calls and iteration < max_iterations:
                iteration += 1
                
                # Get the first function call
                function_call = response.function_calls[0]
                tool_name = function_call.name
                tool_args = dict(function_call.args) if function_call.args else {}
                
                # Emit signal for UI to show tool usage
                self.tool_used.emit(tool_name, tool_args)

                # Execute the tool with robust error handling
                if tool_name in self.tool_functions:
                    tool_function = self.tool_functions[tool_name]
                    try:
                        # Execute the tool function
                        tool_result = tool_function(**tool_args)
                        
                        # Send result back to the model
                        response = chat.send_message(
                            types.Part.from_function_response(
                                name=tool_name,
                                response={"result": str(tool_result)}
                            )
                        )
                    except TypeError as e:
                        # Handle wrong arguments passed to tool
                        error_msg = f"Tool '{tool_name}' received invalid arguments: {tool_args}. Error: {str(e)}"
                        print(f"Tool error: {error_msg}")
                        response = chat.send_message(
                            types.Part.from_function_response(
                                name=tool_name,
                                response={"error": error_msg}
                            )
                        )
                    except Exception as e:
                        # Catch any other tool execution errors
                        error_msg = f"Error executing tool '{tool_name}': {str(e)}"
                        print(f"Tool error: {error_msg}")
                        response = chat.send_message(
                            types.Part.from_function_response(
                                name=tool_name,
                                response={"error": error_msg}
                            )
                        )
                else:
                    # Unknown tool - report back to model
                    print(f"Warning: Unknown tool requested: '{tool_name}'")
                    error_msg = f"Unknown tool: '{tool_name}'. Available tools: {list(self.tool_functions.keys())}"
                    response = chat.send_message(
                        types.Part.from_function_response(
                            name=tool_name,
                            response={"error": error_msg}
                        )
                    )
                    break  # Exit loop on unknown tool
            
            if iteration >= max_iterations:
                print("Warning: Maximum tool call iterations reached")

            return GenerationResult(
                text=response.text if hasattr(response, 'text') else None,
                candidates=getattr(response, 'candidates', None),
                prompt_feedback=getattr(response, 'prompt_feedback', None)
            )

        except Exception as e:
            error_msg = str(e)
            print(f"Error generating content: {error_msg}")
            return GenerationResult(text=None, error=error_msg)

    def _build_function_declarations(self) -> List[Dict]:
        """
        Build function declarations for the Gemini API.
        These define the tool schema that the model uses.
        """
        return [
            {
                "name": "read_file",
                "description": "Read the complete content of a file from the filesystem. Use this when you need to see the contents of a file to understand, debug, or modify it.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "The absolute or relative path to the file to read"
                        }
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "write_file",
                "description": "Create or overwrite a file with the specified content. Use this to write or modify code files, configuration files, or any text-based files.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "The path where the file should be created or overwritten"
                        },
                        "content": {
                            "type": "string",
                            "description": "The complete content to write to the file"
                        }
                    },
                    "required": ["path", "content"]
                }
            },
            {
                "name": "create_directory",
                "description": "Create a new directory (folder) at the specified path. Creates parent directories as needed.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "The path where the directory should be created"
                        }
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "list_directory",
                "description": "List the contents of a directory showing files and subdirectories.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "The path to the directory to list"
                        }
                    },
                    "required": ["path"]
                }
            }
        ]

    def abort(self):
        """
        Abort the current generation request if streaming.
        """
        if self._is_streaming:
            self._abort_event.set()
            self._is_streaming = False
            print("Aura generation abort requested")

    def is_generating(self) -> bool:
        """Check if a generation is currently in progress."""
        return self._is_streaming


# Export for easy importing
__all__ = ['AuraClient', 'GenerationResult']
