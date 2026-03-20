import os
import threading
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from PyQt6.QtCore import QObject, pyqtSignal, QThread

# Use the latest google-genai SDK
from google import genai
from google.genai import types

from app.engine.tools import tool_read_file, tool_write_file


@dataclass
class GenerationResult:
    """Result of a generation request."""
    text: Optional[str]
    candidates: Optional[List[Any]] = None
    prompt_feedback: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class AuraWorker(QObject):
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
    Powered by the new google-genai SDK.
    """
    started_thinking = pyqtSignal()
    tool_used = pyqtSignal(str, dict)
    finished = pyqtSignal(object)
    
    def __init__(self, api_key: str = None, model_name: str = "gemini-2.5-flash"):
        super().__init__()
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
        
        self.tool_functions = {
            "tool_read_file": tool_read_file,
            "tool_write_file": tool_write_file,
        }
        self.thread = None
        self.worker = None
        
        # Initialize immediately
        self._initialize_client()

    def _initialize_client(self):
        try:
            # NEW SDK: Direct Client Initialization
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
        self.thread = QThread()
        # Pass 'self' so the worker can call our sync method
        self.worker = AuraWorker(self, prompt_text, tools, system_instruction)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_generation_finished)
        self.thread.finished.connect(self.thread.deleteLater)
        
        self.started_thinking.emit()
        self.thread.start()

    def on_generation_finished(self, result):
        self.finished.emit(result)
        self.thread.quit()

    def generate_response_sync(
        self,
        prompt_text: str,
        tools: List = None,
        system_instruction: str = None,
        stream: bool = False 
    ) -> GenerationResult:
        try:
            # 1. NEW SDK: Setup Configuration
            tools_list = tools or [tool_read_file, tool_write_file]
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=tools_list,
                # We disable automatic function calling so we can emit our UI signals manually
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                temperature=0.2 # Lower temperature is better for coding consistency
            )

            # 2. NEW SDK: Create Chat Session
            chat = self.client.chats.create(
                model=self.model_name,
                config=config
            )
            
            # 3. Send initial prompt
            response = chat.send_message(prompt_text)

            # 4. NEW SDK: Cleaner Function Call Extraction
            while response.function_calls:
                # Grab the first function call requested by the model
                function_call = response.function_calls[0]
                tool_name = function_call.name
                tool_args = function_call.args

                # Alert the UI that a tool is being used
                self.tool_used.emit(tool_name, tool_args)

                if tool_name in self.tool_functions:
                    tool_function = self.tool_functions[tool_name]
                    try:
                        # Execute the python function
                        tool_result = tool_function(**tool_args)
                        
                        # NEW SDK: Send the result back using Part.from_function_response
                        response = chat.send_message(
                            types.Part.from_function_response(
                                name=tool_name,
                                response={"result": str(tool_result)}
                            )
                        )
                    except Exception as e:
                        print(f"Error executing tool {tool_name}: {e}")
                        response = chat.send_message(
                            types.Part.from_function_response(
                                name=tool_name,
                                response={"error": str(e)}
                            )
                        )
                else:
                    print(f"Unknown tool: {tool_name}")
                    break
            
            return GenerationResult(
                text=response.text,
                candidates=getattr(response, 'candidates', None),
                prompt_feedback=getattr(response, 'prompt_feedback', None)
            )

        except Exception as e:
            return GenerationResult(text=None, error=str(e))