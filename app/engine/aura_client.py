"""
Multi-Model Orchestrator for LumeIDE

A unified client that intelligently routes requests to different AI models
based on user intent, with automatic failover and retry capabilities.

Features:
- ModelRouter: Intent-based routing (Groq for Scan/List, Gemini for Build/Fix)
- SafeRetry: Automatic retry with fallback to free models on rate limits
- Context Injection: Updates system instructions for backup models
- Standardized Tooling: OpenAI-compatible function calling format
"""

import os
import re
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum
from dotenv import load_dotenv
from PyQt6.QtCore import QObject, pyqtSignal

# Load environment variables
load_dotenv()


# ============================================================================
# Model Configuration
# ============================================================================

class ModelProvider(Enum):
    """Supported AI model providers."""
    GROQ = "groq"
    GEMINI = "gemini"
    OPENROUTER = "openrouter"


@dataclass
class ModelConfig:
    """Configuration for an AI model."""
    provider: ModelProvider
    model_id: str
    api_key_env: str
    base_url: Optional[str] = None
    supports_streaming: bool = True
    supports_functions: bool = True
    is_free: bool = False


# Model registry
MODEL_REGISTRY: Dict[str, ModelConfig] = {
    # Groq models (fast, good for scanning/listing)
    "groq/llama-3.3-70b-versatile": ModelConfig(
        provider=ModelProvider.GROQ,
        model_id="llama-3.3-70b-versatile",
        api_key_env="GROQ_API_KEY",
        base_url="https://api.groq.com/openai/v1",
    ),
    "groq/llama-3.1-8b-instant": ModelConfig(
        provider=ModelProvider.GROQ,
        model_id="llama-3.1-8b-instant",
        api_key_env="GROQ_API_KEY",
        base_url="https://api.groq.com/openai/v1",
    ),
    
    # Gemini models (powerful, good for building/fixing)
    "gemini/gemini-2.0-flash": ModelConfig(
        provider=ModelProvider.GEMINI,
        model_id="gemini-2.0-flash",
        api_key_env="GEMINI_API_KEY",
    ),
    "gemini/gemini-1.5-pro": ModelConfig(
        provider=ModelProvider.GEMINI,
        model_id="gemini-1.5-pro",
        api_key_env="GEMINI_API_KEY",
    ),
    
    # OpenRouter free models (fallback)
    "openrouter/auto-free": ModelConfig(
        provider=ModelProvider.OPENROUTER,
        model_id="openrouter/auto",
        api_key_env="OPENROUTER_API_KEY",
        base_url="https://openrouter.ai/api/v1",
        is_free=True,
    ),
}


# ============================================================================
# Intent Detection
# ============================================================================

class Intent(Enum):
    """User intent categories."""
    SCAN = "scan"      # Listing, exploring, reading
    BUILD = "build"    # Creating, writing, generating code
    FIX = "fix"        # Debugging, error fixing, refactoring
    EXPLAIN = "explain"  # Asking questions, explanations
    UNKNOWN = "unknown"


INTENT_PATTERNS = {
    Intent.SCAN: [
        r'\b(scan|list|show|find|search|look|view|browse|read|get|check|inspect)\b',
    ],
    Intent.BUILD: [
        r'\b(build|create|make|generate|add|new|write|implement)\b',
    ],
    Intent.FIX: [
        r'\b(fix|debug|repair|resolve|error|bug|issue|problem|correct|patch|refactor)\b',
    ],
    Intent.EXPLAIN: [
        r'\b(explain|what|how|why|tell|describe|understand|help)\b',
    ],
}


def detect_intent(user_input: str) -> Intent:
    """
    Detect user intent from input text.
    
    Args:
        user_input: The user's command/query
        
    Returns:
        Detected Intent enum value
    """
    text_lower = user_input.lower().strip()
    
    # Check for exact command matches first
    exact_matches = {
        "scan": Intent.SCAN,
        "list": Intent.SCAN,
        "build": Intent.BUILD,
        "fix": Intent.FIX,
    }
    
    first_word = text_lower.split()[0] if text_lower.split() else ""
    if first_word in exact_matches:
        return exact_matches[first_word]
    
    # Pattern-based detection
    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return intent
    
    return Intent.UNKNOWN


# ============================================================================
# Model Router
# ============================================================================

@dataclass
class RouteResult:
    """Result of a routing decision."""
    primary_model: str
    fallback_model: str
    intent: Intent
    reason: str


class ModelRouter:
    """
    Routes requests to appropriate models based on detected intent.
    
    Routing Strategy:
    - Scan/List operations -> Groq (fast, cost-effective)
    - Build/Fix operations -> Gemini (powerful reasoning)
    - Rate limited requests -> OpenRouter free fallback
    """
    
    # Intent to model mapping
    INTENT_MODELS = {
        Intent.SCAN: "groq/llama-3.3-70b-versatile",
        Intent.BUILD: "gemini/gemini-2.0-flash",
        Intent.FIX: "gemini/gemini-2.0-flash",
        Intent.EXPLAIN: "gemini/gemini-2.0-flash",
        Intent.UNKNOWN: "gemini/gemini-2.0-flash",
    }
    
    FALLBACK_MODEL = "openrouter/auto-free"
    
    def __init__(self):
        self._route_cache: Dict[str, RouteResult] = {}
    
    def route(self, user_input: str) -> RouteResult:
        """
        Determine the best model for the given input.
        
        Args:
            user_input: The user's command/query
            
        Returns:
            RouteResult with primary and fallback model recommendations
        """
        intent = detect_intent(user_input)
        primary = self.INTENT_MODELS.get(intent, self.INTENT_MODELS[Intent.UNKNOWN])
        
        return RouteResult(
            primary_model=primary,
            fallback_model=self.FALLBACK_MODEL,
            intent=intent,
            reason=f"Intent '{intent.value}' routes to {primary.split('/')[0].upper()}",
        )
    
    def get_model_config(self, model_key: str) -> Optional[ModelConfig]:
        """Get configuration for a model."""
        return MODEL_REGISTRY.get(model_key)


# ============================================================================
# Safe Retry Handler
# ============================================================================

@dataclass
class RetryContext:
    """Context for retry operations."""
    original_model: str
    current_model: str
    attempt: int
    max_attempts: int
    last_error: Optional[str] = None
    is_fallback: bool = False


BACKUP_SYSTEM_INSTRUCTION = """You are a backup model for Lume IDE. The primary model hit a rate limit. Continue the task precisely.

Important guidelines:
1. Maintain consistency with any previous context or file modifications
2. If you need to read files, use the read_file tool
3. If you need to write files, use the write_file tool
4. Be precise and complete in your task
5. Do not re-explain what happened - just continue the work
"""


class SafeRetry:
    """
    Handles automatic retry with fallback on rate limit (429) or server (500) errors.
    
    Strategy:
    1. Try primary model
    2. On 429/500 error, switch to openrouter/auto-free (free fallback)
    3. Retry once with fallback
    4. If still fails, propagate error
    """
    
    RETRYABLE_ERRORS = {429, 500, 502, 503, 504}
    MAX_RETRIES = 1
    
    def __init__(self, router: ModelRouter):
        self.router = router
        self.retry_history: List[RetryContext] = []
    
    def should_retry(self, error_code: int) -> bool:
        """Check if an error is retryable."""
        return error_code in self.RETRYABLE_ERRORS
    
    def get_retry_context(self, original_model: str, error_code: int) -> RetryContext:
        """Create retry context for switching models."""
        return RetryContext(
            original_model=original_model,
            current_model=self.router.FALLBACK_MODEL,
            attempt=1,
            max_attempts=self.MAX_RETRIES + 1,
            last_error=f"HTTP {error_code}",
            is_fallback=True,
        )
    
    def get_backup_system_instruction(self, original_instruction: str) -> str:
        """Get updated system instruction for backup model."""
        return f"{original_instruction}\n\n{BACKUP_SYSTEM_INSTRUCTION}"
    
    def record_retry(self, context: RetryContext):
        """Record retry attempt in history."""
        self.retry_history.append(context)
        if len(self.retry_history) > 50:
            self.retry_history.pop(0)
    
    def get_last_retry(self) -> Optional[RetryContext]:
        """Get the most recent retry context."""
        return self.retry_history[-1] if self.retry_history else None


# ============================================================================
# API Client Abstraction
# ============================================================================

class APIClientBase:
    """Base class for API clients."""
    
    def __init__(self, config: ModelConfig, system_instruction: str = ""):
        self.config = config
        self.system_instruction = system_instruction
        self._client = None
        self._init_client()
    
    def _init_client(self):
        """Initialize the API client. Override in subclasses."""
        raise NotImplementedError
    
    def send_message(self, messages: List[Dict[str, str]], 
                     tools: Optional[List[Dict]] = None,
                     stream: bool = True) -> Any:
        """Send a message to the model. Override in subclasses."""
        raise NotImplementedError
    
    def get_error_code(self, exception: Exception) -> Optional[int]:
        """Extract error code from exception. Override in subclasses."""
        raise NotImplementedError


class GroqClient(APIClientBase):
    """Groq API client using OpenAI-compatible interface."""
    
    def _init_client(self):
        api_key = os.getenv(self.config.api_key_env)
        if not api_key:
            raise ValueError(f"Missing API key: {self.config.api_key_env}")
        
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=api_key, base_url=self.config.base_url)
        except ImportError:
            raise ImportError("openai package required for Groq. Install: pip install openai")
    
    def send_message(self, messages: List[Dict[str, str]], 
                     tools: Optional[List[Dict]] = None,
                     stream: bool = True) -> Any:
        kwargs = {"model": self.config.model_id, "messages": messages, "stream": stream}
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        return self._client.chat.completions.create(**kwargs)
    
    def get_error_code(self, exception: Exception) -> Optional[int]:
        error_str = str(exception).lower()
        if "429" in error_str or "rate limit" in error_str:
            return 429
        if "500" in error_str or "internal server error" in error_str:
            return 500
        return None


class GeminiClient(APIClientBase):
    """Google Gemini API client."""
    
    def _init_client(self):
        api_key = os.getenv(self.config.api_key_env)
        if not api_key:
            raise ValueError(f"Missing API key: {self.config.api_key_env}")
        
        try:
            from google import genai
            self._client = genai.Client(api_key=api_key)
        except ImportError:
            raise ImportError("google-genai package required. Install: pip install google-genai")
    
    def send_message(self, messages: List[Dict[str, str]], 
                     tools: Optional[List[Dict]] = None,
                     stream: bool = True) -> Any:
        contents = []
        for msg in messages:
            if msg["role"] == "user":
                contents.append({"role": "user", "parts": [{"text": msg["content"]}]})
            elif msg["role"] == "assistant":
                contents.append({"role": "model", "parts": [{"text": msg["content"]}]})
        
        config = {"generation_config": {"candidate_count": 1}}
        if tools:
            gemini_tools = self._convert_tools(tools)
            config["tools"] = gemini_tools
        
        return self._client.models.generate_content(
            model=self.config.model_id, contents=contents, config=config)
    
    def _convert_tools(self, tools: List[Dict]) -> List[Dict]:
        gemini_tools = []
        for tool in tools:
            if tool.get("type") == "function":
                func = tool.get("function", {})
                gemini_tools.append({
                    "function_declarations": [{
                        "name": func.get("name"),
                        "description": func.get("description"),
                        "parameters": func.get("parameters", {}),
                    }]
                })
        return gemini_tools
    
    def get_error_code(self, exception: Exception) -> Optional[int]:
        error_str = str(exception).lower()
        if "429" in error_str or "rate limit" in error_str:
            return 429
        if "500" in error_str or "internal server error" in error_str:
            return 500
        return None


class OpenRouterClient(APIClientBase):
    """OpenRouter API client for free model fallback."""
    
    def _init_client(self):
        api_key = os.getenv(self.config.api_key_env, "sk-or-v1-placeholder")
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=api_key, base_url=self.config.base_url)
        except ImportError:
            raise ImportError("openai package required. Install: pip install openai")
    
    def send_message(self, messages: List[Dict[str, str]], 
                     tools: Optional[List[Dict]] = None,
                     stream: bool = True) -> Any:
        kwargs = {"model": self.config.model_id, "messages": messages, "stream": stream}
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        return self._client.chat.completions.create(**kwargs)
    
    def get_error_code(self, exception: Exception) -> Optional[int]:
        error_str = str(exception).lower()
        if "429" in error_str or "rate limit" in error_str:
            return 429
        if "500" in error_str or "internal server error" in error_str:
            return 500
        return None


def create_api_client(config: ModelConfig, system_instruction: str = "") -> APIClientBase:
    """Factory function to create API clients."""
    clients = {
        ModelProvider.GROQ: GroqClient,
        ModelProvider.GEMINI: GeminiClient,
        ModelProvider.OPENROUTER: OpenRouterClient,
    }
    client_class = clients.get(config.provider)
    if not client_class:
        raise ValueError(f"Unknown provider: {config.provider}")
    return client_class(config, system_instruction)


# ============================================================================
# Tool Executor
# ============================================================================

class ToolExecutor:
    """Executes tool calls returned by AI models."""
    
    def __init__(self):
        self._tools = self._load_tools()
    
    def _load_tools(self) -> Dict[str, Callable]:
        """Load available tool functions."""
        from app.engine.tools import TOOL_FUNCTIONS
        return TOOL_FUNCTIONS
    
    def execute(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool call."""
        tool_func = self._tools.get(tool_name)
        if not tool_func:
            return f"Error: Unknown tool '{tool_name}'"
        try:
            result = tool_func(**arguments)
            return result if isinstance(result, str) else str(result)
        except Exception as e:
            return f"Error executing {tool_name}: {str(e)}"
    
    def execute_tool_calls(self, tool_calls: List[Dict]) -> List[Dict[str, Any]]:
        """Execute multiple tool calls."""
        results = []
        for call in tool_calls:
            if "function" in call:
                func = call["function"]
                tool_name = func["name"]
                arguments = func.get("arguments", {})
            else:
                tool_name = call.get("name", call.get("id"))
                arguments = call.get("parameters", call.get("args", {}))
            
            if isinstance(arguments, str):
                import json
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = {}
            
            result = self.execute(tool_name, arguments)
            results.append({
                "tool_call_id": call.get("id", call.get("call_id")),
                "tool_name": tool_name,
                "result": result,
            })
        return results


# ============================================================================
# Multi-Model Orchestrator (Main Aura Client)
# ============================================================================

@dataclass
class OrchestratorConfig:
    """Configuration for the Multi-Model Orchestrator."""
    default_system_instruction: str = (
        "You are the Lume Architect, a world-class expert in software development. "
        "You help users build, fix, and understand their code. "
        "Use the available tools to read files, write code, create directories, and list contents. "
        "Always be precise and helpful."
    )
    enable_routing: bool = True
    enable_retry: bool = True
    max_tool_iterations: int = 10


class MultiModelOrchestrator(QObject):
    """
    Multi-Model Orchestrator - The main Aura Client for LumeIDE.
    
    Features:
    - Intent-based model routing (Groq for scan, Gemini for build/fix)
    - Automatic retry with free model fallback
    - Standardized OpenAI-compatible tool format
    - Tool execution with automatic loop handling
    """
    
    # PyQt Signals
    started_thinking = pyqtSignal()
    tool_used = pyqtSignal(str, dict)
    finished = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, config: Optional[OrchestratorConfig] = None):
        super().__init__()
        self.config = config or OrchestratorConfig()
        self.router = ModelRouter()
        self.retry_handler = SafeRetry(self.router)
        self.tool_executor = ToolExecutor()
        self._is_generating = False
        self._should_abort = False
        self._messages: List[Dict[str, str]] = []
    
    def _get_api_client(self, model_key: str, system_instruction: str = None) -> APIClientBase:
        """Get or create an API client for the specified model."""
        model_config = self.router.get_model_config(model_key)
        if not model_config:
            raise ValueError(f"Unknown model: {model_key}")
        instruction = system_instruction or self.config.default_system_instruction
        return create_api_client(model_config, instruction)
    
    def _build_messages(self, prompt: str, system_instruction: str = None) -> List[Dict[str, str]]:
        """Build message list for API call."""
        messages = []
        instruction = system_instruction or self.config.default_system_instruction
        messages.append({"role": "system", "content": instruction})
        messages.extend(self._messages)
        messages.append({"role": "user", "content": prompt})
        return messages
    
    def _get_openai_tools(self) -> list:
        """Get tools in OpenAI-compatible format."""
        from app.engine.tools import get_openai_tools
        return get_openai_tools()
    
    def generate_response(self, prompt: str, system_instruction: str = None,
                         stream: bool = True) -> Optional[str]:
        """Generate a response using the appropriate model."""
        self._is_generating = True
        self._should_abort = False
        self.started_thinking.emit()
        
        try:
            route = self.router.route(prompt)
            print(f"[Aura] Routed to: {route.primary_model} ({route.reason})")
            
            client = self._get_api_client(route.primary_model, system_instruction)
            messages = self._build_messages(prompt, system_instruction)
            tools = self._get_openai_tools()
            
            response = self._execute_with_retry(client, messages, tools, route, stream)
            
            if response:
                self._messages.append({"role": "user", "content": prompt})
                self._messages.append({"role": "assistant", "content": response})
                if len(self._messages) > 20:
                    self._messages = self._messages[-20:]
                self.finished.emit(response)
                return response
            return None
        
        except Exception as e:
            error_msg = f"Error generating response: {str(e)}"
            print(f"[Aura] {error_msg}")
            self.error_occurred.emit(error_msg)
            return None
        finally:
            self._is_generating = False
    
    def _execute_with_retry(self, client: APIClientBase, messages: List[Dict[str, str]],
                            tools: List[Dict], route: RouteResult, stream: bool) -> Optional[str]:
        """Execute API call with retry logic."""
        attempt = 0
        current_client = client
        current_messages = messages
        system_instruction = self.config.default_system_instruction
        
        while attempt <= self.retry_handler.MAX_RETRIES:
            try:
                response = current_client.send_message(
                    messages=current_messages, tools=tools, stream=stream)
                result = self._process_response(response, current_messages, tools, stream)
                return result
            except Exception as e:
                error_code = current_client.get_error_code(e)
                if error_code and self.retry_handler.should_retry(error_code) and attempt < self.retry_handler.MAX_RETRIES:
                    attempt += 1
                    print(f"[Aura] Rate limit hit ({error_code}). Switching to fallback model...")
                    fallback_config = self.router.get_model_config(route.fallback_model)
                    if fallback_config:
                        system_instruction = self.retry_handler.get_backup_system_instruction(
                            self.config.default_system_instruction)
                        current_client = create_api_client(fallback_config, system_instruction)
                        current_messages = messages
                        retry_context = self.retry_handler.get_retry_context(route.primary_model, error_code)
                        self.retry_handler.record_retry(retry_context)
                        continue
                raise
        return None
    
    def _process_response(self, response, messages: List[Dict[str, str]],
                          tools: List[Dict], stream: bool) -> str:
        """Process API response, handling tool calls."""
        iteration = 0
        while iteration < self.config.max_tool_iterations:
            iteration += 1
            response_text = ""
            tool_calls = None
            
            if stream:
                tool_calls_buffer = []
                for chunk in response:
                    if hasattr(chunk, "choices") and chunk.choices:
                        choice = chunk.choices[0]
                        if hasattr(choice, "delta"):
                            delta = choice.delta
                            if hasattr(delta, "content") and delta.content:
                                response_text += delta.content
                            if hasattr(delta, "tool_calls") and delta.tool_calls:
                                tool_calls_buffer.extend(delta.tool_calls)
                if tool_calls_buffer:
                    tool_calls = self._format_tool_calls(tool_calls_buffer)
            else:
                if hasattr(response, "text"):
                    response_text = response.text
                elif hasattr(response, "choices"):
                    for choice in response.choices:
                        if hasattr(choice, "message"):
                            msg = choice.message
                            response_text = msg.content or ""
                            tool_calls = msg.tool_calls
            
            if not tool_calls:
                return response_text
            
            print(f"[Aura] Executing {len(tool_calls)} tool call(s)...")
            tool_results = self.tool_executor.execute_tool_calls(tool_calls)
            
            messages.append({"role": "assistant", "content": response_text, "tool_calls": tool_calls})
            for result in tool_results:
                messages.append({
                    "role": "tool",
                    "tool_call_id": result["tool_call_id"],
                    "content": result["result"],
                })
                self.tool_used.emit(result["tool_name"], {"result": result["result"]})
            
            tool_summary = "\n".join([f"[{r['tool_name']}]: {r['result'][:200]}..." for r in tool_results])
            return f"{response_text}\n\nTool Results:\n{tool_summary}"
        return "Max tool iterations reached."
    
    def _format_tool_calls(self, tool_calls) -> List[Dict]:
        """Format tool calls from streaming chunks."""
        formatted = []
        for tc in tool_calls:
            if hasattr(tc, "function"):
                formatted.append({
                    "id": getattr(tc, "id", f"call_{len(formatted)}"),
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                })
        return formatted
    
    def send_prompt(self, prompt: str, stream: bool = True) -> Optional[str]:
        """Send a prompt and get a response (alias for generate_response)."""
        return self.generate_response(prompt, stream=stream)
    
    def is_generating(self) -> bool:
        """Check if currently generating a response."""
        return self._is_generating
    
    def abort(self):
        """Abort current generation."""
        self._should_abort = True
        self._is_generating = False
    
    def clear_history(self):
        """Clear conversation history."""
        self._messages.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics."""
        return {
            "total_retries": len(self.retry_handler.retry_history),
            "conversation_length": len(self._messages),
            "last_retry": self.retry_handler.get_last_retry().__dict__ if self.retry_handler.get_last_retry() else None,
        }


# Backward compatibility alias
AuraClient = MultiModelOrchestrator


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    'MultiModelOrchestrator', 'AuraClient', 'ModelRouter', 'SafeRetry',
    'ModelProvider', 'ModelConfig', 'Intent', 'RouteResult', 'RetryContext',
    'OrchestratorConfig', 'detect_intent', 'create_api_client',
]
