"""
Aura Client Module for LumeIDE

Client for interacting with Google's Gemini models using the google-genai SDK.
Handles AI-powered code generation and tool execution.

Logging:
    All operations are logged to stdout for debugging.
    Use THOUGHT logs to see AI reasoning before tool execution.
"""

import os
import json
import threading
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any, Callable

from PyQt6.QtCore import QObject, pyqtSignal, QThread

# Use the google-genai SDK (NOT google-generativeai)
from google import genai
from google.genai import types

from app.engine.tools import TOOL_FUNCTIONS
from app.engine.utils.tool_utils import build_all_tool_declarations # <--- NEW IMPORT


# ============================================================================
# LOGGING UTILITIES
# ============================================================================

def log_header(title: str):
    """Print a formatted log header."""
    print(f"\n{'='*70}")
    print(f" {title}")
    print(f"{'='*70}")

def log_thought(tool_name: str, args: Dict[str, Any]):
    """Print the AI's thought process before tool execution."""
    print(f"\n[🤔 AI THOUGHT] I am going to call {tool_name} with:")
    for key, value in args.items():
        # Truncate long values for display
        value_str = str(value)
        if len(value_str) > 100:
            value_str = value_str[:100] + "..."
        print(f"    {key}: {value_str}")

def log_tool_execution(tool_name: str, result: str):
    """Print the result of tool execution."""
    # Truncate long results
    result_preview = result[:500] if len(result) > 500 else result
    print(f"\n[🔧 TOOL RESULT] {tool_name}:")
    print(f"    {result_preview}")
    if len(result) > 500:
        print(f"    ... (truncated, full result: {len(result)} chars)")

def log_error(tool_name: str, error: str):
    """Print an error during tool execution."""
    print(f"\n[❌ TOOL ERROR] {tool_name}: {error}")

def log_iteration(iteration: int, total: int, tool_name: str):
    """Print iteration progress."""
    print(f"\n[📍 ITERATION {iteration}/{total}] Processing tool: {tool_name}")


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class GenerationResult:
    """Result of a generation request."""
    text: Optional[str]
    candidates: Optional[List[Any]] = None
    prompt_feedback: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class ToolCall:
    """Represents a tool call with its arguments."""
    name: str
    args: Dict[str, Any]
    
    def to_dict(self) -> Dict:
        return asdict(self)


# ============================================================================
# WORKER THREAD
# ============================================================================

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


# ============================================================================
# MAIN AURA CLIENT
# ============================================================================

class AuraClient(QObject):
    """
    A client for interacting with Google's Gemini models.
    Powered by the google-genai SDK.
    
    Supports tool calling for file operations and provides
    signals for UI updates during generation.
    
    Logging:
        All operations print to stdout for debugging.
        Thought Logger shows AI reasoning before tool execution.
    """
    
    # Signals for UI updates
    started_thinking = pyqtSignal()
    tool_used = pyqtSignal(str, dict)
    finished = pyqtSignal(object)
    
    def __init__(self, api_key: str = None, model_name: str = "gemini-2.5-flash"):
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
        self._verbose = True  # Enable verbose logging
        
        # Initialize the client
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the Gemini client using google-genai SDK."""
        try:
            self.client = genai.Client(api_key=self.api_key)
            print(f"[✓] AuraClient initialized with model: {self.model_name}")
        except Exception as e:
            print(f"[✗] Error initializing Gemini client: {e}")
            raise

    def set_verbose(self, verbose: bool):
        """Enable or disable verbose logging."""
        self._verbose = verbose

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
        
        Logging:
            Prints detailed logs of AI thoughts and tool execution.
        """
        log_header("AURA GENERATION START")
        print(f"[📝 PROMPT]: {prompt_text[:200]}{'...' if len(prompt_text) > 200 else ''}")
        if system_instruction:
            print(f"[📋 SYSTEM INSTRUCTION]: {len(system_instruction)} chars")
        print()
        
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
            print("[💬] Creating chat session...")
            chat = self.client.chats.create(
                model=self.model_name,
                config=config
            )
            
            # Send initial prompt
            print("[📤] Sending initial prompt to Gemini...")
            response = chat.send_message(prompt_text)
            
            print(f"[📥] Received response with {len(response.function_calls) if response.function_calls else 0} function calls")
            print()

            # Handle function calls in a loop
            max_iterations = 10  # Prevent infinite loops
            iteration = 0
            total_tool_calls = []
            
            while response.function_calls and iteration < max_iterations:
                iteration += 1
                
                # Get the first function call
                function_call = response.function_calls[0]
                tool_name = function_call.name
                tool_args = dict(function_call.args) if function_call.args else {}
                
                # Log iteration
                log_iteration(iteration, max_iterations, tool_name)
                
                # Store tool call for history
                tool_call_record = ToolCall(name=tool_name, args=tool_args)
                total_tool_calls.append(tool_call_record)
                
                # THOUGHT LOGGER: Show AI reasoning before execution
                log_thought(tool_name, tool_args)
                
                # Print raw JSON of the function call
                if self._verbose:
                    print(f"\n[📄 RAW FUNCTION CALL JSON]:")
                    print(json.dumps(tool_call_record.to_dict(), indent=2))
                
                # Emit signal for UI to show tool usage
                self.tool_used.emit(tool_name, tool_args)

                # Execute the tool with robust error handling
                if tool_name in self.tool_functions:
                    tool_function = self.tool_functions[tool_name]
                    try:
                        print(f"\n[⚙️  EXECUTING] Calling {tool_function.__name__}...")
                        
                        # Execute the tool function
                        tool_result = tool_function(**tool_args)
                        
                        # Log successful execution
                        log_tool_execution(tool_name, tool_result)
                        
                        # Send result back to the model
                        print(f"\n[📤] Sending tool result back to Gemini...")
                        response = chat.send_message(
                            types.Part.from_function_response(
                                name=tool_name,
                                response={"result": str(tool_result)}
                            )
                        )
                        
                        print(f"[📥] Next response: {len(response.function_calls) if response.function_calls else 0} function calls remaining")
                        
                    except TypeError as e:
                        # Handle wrong arguments passed to tool
                        error_msg = f"Tool '{tool_name}' received invalid arguments: {tool_args}. Error: {str(e)}"
                        log_error(tool_name, error_msg)
                        print(f"\n[📤] Sending error back to Gemini...")
                        response = chat.send_message(
                            types.Part.from_function_response(
                                name=tool_name,
                                response={"error": error_msg}
                            )
                        )
                    except Exception as e:
                        # Catch any other tool execution errors
                        error_msg = f"Error executing tool '{tool_name}': {str(e)}"
                        log_error(tool_name, error_msg)
                        print(f"\n[📤] Sending error back to Gemini...")
                        response = chat.send_message(
                            types.Part.from_function_response(
                                name=tool_name,
                                response={"error": error_msg}
                            )
                        )
                else:
                    # Unknown tool - report back to model
                    error_msg = f"Unknown tool: '{tool_name}'. Available tools: {list(self.tool_functions.keys())}"
                    print(f"\n[⚠️  UNKNOWN TOOL] {error_msg}")
                    print(f"[📤] Sending error back to Gemini...")
                    response = chat.send_message(
                        types.Part.from_function_response(
                            name=tool_name,
                            response={"error": error_msg}
                        )
                    )
                    break  # Exit loop on unknown tool
                
                print()
            
            if iteration >= max_iterations:
                print(f"[⚠️  WARNING] Maximum tool call iterations ({max_iterations}) reached")
            
            # Log final response
            log_header("AURA GENERATION COMPLETE")
            print(f"[📊 SUMMARY]:")
            print(f"    - Total iterations: {iteration}")
            print(f"    - Total tool calls: {len(total_tool_calls)}")
            for tc in total_tool_calls:
                print(f"      • {tc.name}({list(tc.args.keys())})")
            print(f"\n[💬 FINAL RESPONSE]:")
            print("-" * 70)
            final_text = response.text if hasattr(response, 'text') else None
            if final_text:
                print(final_text)
            else:
                print("(No text response)")
            print("-" * 70)

            return GenerationResult(
                text=response.text if hasattr(response, 'text') else None,
                candidates=getattr(response, 'candidates', None),
                prompt_feedback=getattr(response, 'prompt_feedback', None)
            )

        except Exception as e:
            error_msg = str(e)
            log_header("AURA GENERATION ERROR")
            print(f"[❌ ERROR]: {error_msg}")
            import traceback
            traceback.print_exc()
            return GenerationResult(text=None, error=error_msg)

    def _build_function_declarations(self) -> List[Dict]:
        """
        Build function declarations for the Gemini API.
        These define the tool schema that the model uses.
        """
        # Dynamically build function declarations from TOOL_FUNCTIONS
        return build_all_tool_declarations(self.tool_functions) # <--- MODIFIED LINE

    def abort(self):
        """
        Abort the current generation request if streaming.
        """
        if self._is_streaming:
            self._abort_event.set()
            self._is_streaming = False
            print("[⏹️  ABORT] Aura generation abort requested")

    def is_generating(self) -> bool:
        """
        Check if a generation is currently in progress.
        """
        return self._is_streaming


# Export for easy importing
__all__ = ['AuraClient', 'GenerationResult', 'ToolCall', 'log_header', 'log_thought', 'log_tool_execution', 'log_error']
