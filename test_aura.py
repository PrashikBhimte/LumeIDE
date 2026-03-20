r"""
test_aura.py - CLI Harness for LumeIDE Aura Agent

A lightweight test script to validate the Aura AI agent before GUI integration.
NO PYQT6 - Pure terminal-based testing harness.

Usage:
    .\venv\Scripts\python.exe test_aura.py

Commands:
    /exit or /quit - Exit the CLI
    /reset - Reset the conversation
    /tools - List available tools
    /help - Show this help message
"""

import os
import sys
import json
import importlib.util
from pathlib import Path

# Ensure we use the venv Python
venv_python = os.path.join(os.path.dirname(__file__), 'venv', 'Scripts', 'python.exe')
if sys.executable.lower() != venv_python.lower() and os.path.exists(venv_python):
    print(f"WARNING: This script should be run with: {venv_python}")
    print(f"Current Python: {sys.executable}")
    print()

# Load environment
from dotenv import load_dotenv
load_dotenv()


def load_tools_module():
    """
    Load tools.py directly without triggering package __init__.py
    This avoids circular import issues.
    """
    tools_path = os.path.join(os.path.dirname(__file__), 'app', 'engine', 'tools.py')
    spec = importlib.util.spec_from_file_location("app_engine_tools", tools_path)
    tools_module = importlib.util.module_from_spec(spec)
    sys.modules['app_engine_tools'] = tools_module
    spec.loader.exec_module(tools_module)
    return tools_module


def get_project_context() -> str:
    """
    Gather project awareness information for the AI agent.
    Returns a formatted string with current directory and file listing.
    """
    context_lines = []
    context_lines.append("=" * 60)
    context_lines.append("PROJECT CONTEXT")
    context_lines.append("=" * 60)
    
    # Current working directory
    cwd = os.getcwd()
    context_lines.append(f"\nCurrent Working Directory: {cwd}")
    
    # Project root info
    project_root = Path(cwd)
    context_lines.append(f"Project Root: {project_root}")
    
    # List Python files
    context_lines.append("\n--- Python Files in Project ---")
    py_files = sorted(project_root.rglob("*.py"))
    for f in py_files:
        try:
            rel_path = f.relative_to(project_root)
            size = f.stat().st_size
            context_lines.append(f"  {rel_path} ({size} bytes)")
        except ValueError:
            context_lines.append(f"  {f} ({f.stat().st_size} bytes)")
    
    # List main directories
    context_lines.append("\n--- Directory Structure (Top 2 Levels) ---")
    for item in sorted(project_root.iterdir()):
        if item.is_dir() and not item.name.startswith('.') and item.name != '__pycache__':
            sub_items = list(item.iterdir())[:5]
            context_lines.append(f"  {item.name}/")
            for sub in sub_items:
                context_lines.append(f"      |__ {sub.name}")
    
    context_lines.append("\n" + "=" * 60)
    return "\n".join(context_lines)


def get_system_instruction() -> str:
    """
    Create a comprehensive system instruction that includes project awareness.
    """
    project_context = get_project_context()
    
    return f"""You are the Lume Architect, an expert AI assistant for the LumeIDE development environment.

You have access to file system tools that allow you to read, write, and explore files in the project.

{project_context}

IMPORTANT INSTRUCTIONS:
1. When asked to read a file, use the read_file tool with the exact path
2. When asked to write code, use the write_file tool
3. Always be thorough in your analysis of code files
4. If a file doesn't exist, report this clearly
5. Think step-by-step before calling any tool

Your goal is to help developers understand and work with their codebase effectively."""


def init_google_genai():
    """
    Initialize Google GenAI client directly.
    """
    # Import Google GenAI SDK
    from google import genai
    from google.genai import types
    
    # Get API key
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not found in environment or .env file")
        print("\nPlease create a .env file with your API key:")
        print("GEMINI_API_KEY=your_api_key_here")
        sys.exit(1)
    
    # Initialize the client
    client = genai.Client(api_key=api_key)
    print(f"[✓] Google GenAI Client initialized")
    
    return client, api_key, genai, types


class AuraCLIHarness:
    """
    A CLI harness for testing the Aura AI agent.
    Focuses on showing raw JSON tool calls and AI thoughts.
    """
    
    def __init__(self):
        print("=" * 60)
        print("LumeIDE Aura Agent - CLI Test Harness")
        print("=" * 60)
        
        # Load tools module directly (bypass __init__.py to avoid circular imports)
        self.tools_module = load_tools_module()
        TOOL_FUNCTIONS = self.tools_module.TOOL_FUNCTIONS
        
        # Initialize Google GenAI
        self.client, self.api_key, self.genai, self.types = init_google_genai()
        self.model_name = "gemini-2.5-flash"
        self.chat = None
        self.system_instruction = get_system_instruction()
        
        # Map tool names to functions
        self.tool_functions = {
            "read_file": TOOL_FUNCTIONS["read_file"],
            "write_file": TOOL_FUNCTIONS["write_file"],
            "create_directory": TOOL_FUNCTIONS["create_directory"],
            "list_directory": TOOL_FUNCTIONS["list_directory"],
        }
        
        print(f"Model: {self.model_name}")
        print(f"API Key: {'*' * 20}{self.api_key[-4:]}")
        print(f"Project: {os.getcwd()}")
        print("=" * 60)
        print()
        
        # Initialize chat session
        self._init_chat()
    
    def _build_function_declarations(self):
        """Build function declarations for the API."""
        return [
            {
                "name": "read_file",
                "description": "Read the complete content of a file from the filesystem.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "The path to the file to read"}
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "write_file",
                "description": "Create or overwrite a file with the specified content.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "The path where the file should be created"},
                        "content": {"type": "string", "description": "The complete content to write"}
                    },
                    "required": ["path", "content"]
                }
            },
            {
                "name": "create_directory",
                "description": "Create a new directory at the specified path.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "The path where the directory should be created"}
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "list_directory",
                "description": "List the contents of a directory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "The path to the directory to list"}
                    },
                    "required": ["path"]
                }
            }
        ]
    
    def _init_chat(self):
        """Initialize a new chat session."""
        config = self.types.GenerateContentConfig(
            system_instruction=self.system_instruction,
            tools=[
                self.types.Tool(
                    function_declarations=self._build_function_declarations()
                )
            ],
            automatic_function_calling=self.types.AutomaticFunctionCallingConfig(disable=True),
            temperature=0.2
        )
        
        self.chat = self.client.chats.create(
            model=self.model_name,
            config=config
        )
        print("[✓] Chat session initialized\n")
    
    def generate_with_tools(self, prompt: str) -> str:
        """
        Generate a response with tool execution, printing all details.
        """
        print(f"\n{'='*70}")
        print(f"[USER INPUT]")
        print(f"{prompt}")
        print(f"{'='*70}")
        
        try:
            # Send initial prompt
            print("[📤] Sending initial prompt to Gemini...")
            response = self.chat.send_message(prompt)
            
            print(f"[📥] Received response")
            print()
            
            # Handle function calls
            max_iterations = 10
            iteration = 0
            total_tool_calls = []
            
            while response.function_calls and iteration < max_iterations:
                iteration += 1
                
                # Get function call
                function_call = response.function_calls[0]
                tool_name = function_call.name
                tool_args = dict(function_call.args) if function_call.args else {}
                
                # LOG ITERATION
                print(f"\n{'='*70}")
                print(f"[📍 ITERATION {iteration}/{max_iterations}] Processing tool: {tool_name}")
                print(f"{'='*70}")
                
                # THOUGHT LOGGER: Show AI reasoning
                print(f"\n[🤔 AI THOUGHT] I am going to call {tool_name} with:")
                for key, value in tool_args.items():
                    value_str = str(value)
                    if len(value_str) > 100:
                        value_str = value_str[:100] + "..."
                    print(f"    {key}: {value_str}")
                
                # Print RAW JSON
                print(f"\n[📄 RAW FUNCTION CALL JSON]:")
                print(json.dumps({"name": tool_name, "args": tool_args}, indent=2))
                
                total_tool_calls.append({"name": tool_name, "args": tool_args})
                
                # Execute tool
                if tool_name in self.tool_functions:
                    tool_function = self.tool_functions[tool_name]
                    try:
                        print(f"\n[⚙️  EXECUTING] Calling {tool_function.__name__}...")
                        tool_result = tool_function(**tool_args)
                        
                        # Log result
                        result_preview = str(tool_result)[:500]
                        print(f"\n[🔧 TOOL RESULT] {tool_name}:")
                        print(f"    {result_preview}")
                        if len(str(tool_result)) > 500:
                            print(f"    ... (truncated, full: {len(str(tool_result))} chars)")
                        
                        # Send result back
                        print(f"\n[📤] Sending tool result back to Gemini...")
                        response = self.chat.send_message(
                            self.types.Part.from_function_response(
                                name=tool_name,
                                response={"result": str(tool_result)}
                            )
                        )
                    except Exception as e:
                        error_msg = f"Error executing tool '{tool_name}': {str(e)}"
                        print(f"\n[❌ TOOL ERROR] {error_msg}")
                        response = self.chat.send_message(
                            self.types.Part.from_function_response(
                                name=tool_name,
                                response={"error": error_msg}
                            )
                        )
                else:
                    error_msg = f"Unknown tool: '{tool_name}'"
                    print(f"\n[⚠️  UNKNOWN TOOL] {error_msg}")
                    response = self.chat.send_message(
                        self.types.Part.from_function_response(
                            name=tool_name,
                            response={"error": error_msg}
                        )
                    )
                    break
                
                print()
            
            # Summary
            print(f"\n{'='*70}")
            print(f" AURA GENERATION COMPLETE")
            print(f"{'='*70}")
            print(f"[📊 SUMMARY]:")
            print(f"    - Total iterations: {iteration}")
            print(f"    - Total tool calls: {len(total_tool_calls)}")
            for tc in total_tool_calls:
                print(f"      - {tc['name']}({list(tc['args'].keys())})")
            
            print(f"\n[💬 FINAL RESPONSE]:")
            print("-" * 70)
            final_text = response.text if hasattr(response, 'text') else None
            if final_text:
                print(final_text)
            else:
                print("(No text response)")
            print("-" * 70)
            
            return final_text or "(No response)"
            
        except Exception as e:
            error_msg = f"Exception during generation: {str(e)}"
            print(f"\n{'='*70}")
            print(f"[❌ ERROR]: {error_msg}")
            print(f"{'='*70}")
            import traceback
            traceback.print_exc()
            return error_msg
    
    def reset(self):
        """Reset the conversation."""
        print("\n[🔄] Resetting chat session...")
        self._init_chat()
        print("[SYSTEM] Chat history cleared. New session started.")
    
    def list_tools(self):
        """List available tools."""
        print("\n[AVAILABLE TOOLS]")
        print("-" * 40)
        for name, func in self.tool_functions.items():
            print(f"  - {name}")
        print("-" * 40)


def print_help():
    """Print help message."""
    help_text = """
╔══════════════════════════════════════════════════════════════╗
║                    LUME AURA CLI HELP                      ║
╠══════════════════════════════════════════════════════════════╣
║  /exit, /quit    - Exit the CLI harness                    ║
║  /reset          - Clear conversation history               ║
║  /tools          - List available AI tools                 ║
║  /context        - Show current project context            ║
║  /help           - Show this help message                  ║
╠══════════════════════════════════════════════════════════════╣
║  Example queries:                                           ║
║    "Read main.py and tell me the name of the main class"   ║
║    "What files are in the app/engine directory?"            ║
║    "Create a test function in a new file"                  ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(help_text)


def main():
    """Main CLI loop."""
    try:
        harness = AuraCLIHarness()
    except Exception as e:
        print(f"Failed to initialize Aura harness: {e}")
        print("\nMake sure you have:")
        print("  1. A valid GEMINI_API_KEY in your .env file")
        print("  2. Installed requirements: pip install -r requirements.txt")
        print("  3. Activated the venv: .\\venv\\Scripts\\activate")
        sys.exit(1)
    
    print_help()
    
    # Initial test prompt
    # print("\n[SYSTEM] Running initial project awareness test...\n")
    # initial_prompt = """Read main.py and tell me:
    #     1. What is the name of the main class?
    #     2. What does the main() function do?
    #     3. What imports does it use?"""
    # harness.generate_with_tools(initial_prompt)
    # print("\n" + "-" * 60)
    # print("Initial test complete. Now you can ask questions.")
    # print("-" * 60 + "\n")
    
    # Main CLI loop
    while True:
        try:
            user_input = input("Lume> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n[SYSTEM] Exiting Lume Aura CLI...")
            break
        
        if not user_input:
            continue
        
        # Handle commands
        if user_input.lower() in ['/exit', '/quit']:
            print("\n[SYSTEM] Exiting Lume Aura CLI...")
            break
        
        elif user_input.lower() in ['/reset']:
            harness.reset()
            continue
        
        elif user_input.lower() in ['/tools']:
            harness.list_tools()
            continue
        
        elif user_input.lower() in ['/context']:
            print("\n" + get_project_context() + "\n")
            continue
        
        elif user_input.lower() in ['/help', '?']:
            print_help()
            continue
        
        # Regular prompt
        response = harness.generate_with_tools(user_input)
        print()


if __name__ == "__main__":
    main()
