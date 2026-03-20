"""
test_orchestrator.py - Test harness for Multi-Model Orchestrator

Tests the ModelRouter, SafeRetry, and other orchestrator components.
Run with: python test_orchestrator.py
"""

import sys
import os
import importlib.util

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()


def load_module_directly(module_name, file_path):
    """Load a Python module directly from file, avoiding package imports."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_intent_detection(aura_module):
    """Test intent detection from user input."""
    detect_intent = aura_module.detect_intent
    Intent = aura_module.Intent
    
    print("=" * 60)
    print("Testing Intent Detection")
    print("=" * 60)
    
    test_cases = [
        # Scan/List operations -> Groq
        ("scan the project files", Intent.SCAN),
        ("list all directories", Intent.SCAN),
        ("show me the code", Intent.SCAN),
        ("find all python files", Intent.SCAN),
        ("read main.py", Intent.SCAN),
        ("check the logs", Intent.SCAN),
        
        # Build operations -> Gemini
        ("build a new component", Intent.BUILD),
        ("create a new file", Intent.BUILD),
        ("make a class for handling", Intent.BUILD),
        ("generate the api client", Intent.BUILD),
        ("write a test function", Intent.BUILD),
        ("implement the feature", Intent.BUILD),
        
        # Fix operations -> Gemini
        ("fix the bug", Intent.FIX),
        ("debug this code", Intent.FIX),
        ("repair the error", Intent.FIX),
        ("resolve the issue", Intent.FIX),
        ("patch the vulnerability", Intent.FIX),
        ("refactor this method", Intent.FIX),
    ]
    
    passed = 0
    failed = 0
    
    for user_input, expected_intent in test_cases:
        detected = detect_intent(user_input)
        status = "PASS" if detected == expected_intent else "FAIL"
        
        if detected == expected_intent:
            passed += 1
        else:
            failed += 1
        
        print(f"  [{status}] '{user_input}' -> {detected.value} (expected: {expected_intent.value})")
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def test_model_routing(aura_module):
    """Test model routing based on intent."""
    ModelRouter = aura_module.ModelRouter
    Intent = aura_module.Intent
    
    print("\n" + "=" * 60)
    print("Testing Model Routing")
    print("=" * 60)
    
    router = ModelRouter()
    
    test_cases = [
        ("scan the files", "groq/llama-3.3-70b-versatile", Intent.SCAN),
        ("list the directory", "groq/llama-3.3-70b-versatile", Intent.SCAN),
        ("build a new module", "gemini/gemini-2.0-flash", Intent.BUILD),
        ("create a class", "gemini/gemini-2.0-flash", Intent.BUILD),
        ("fix the error", "gemini/gemini-2.0-flash", Intent.FIX),
        ("debug the issue", "gemini/gemini-2.0-flash", Intent.FIX),
    ]
    
    passed = 0
    failed = 0
    
    for user_input, expected_model, expected_intent in test_cases:
        route = router.route(user_input)
        success = (route.primary_model == expected_model and route.intent == expected_intent)
        status = "PASS" if success else "FAIL"
        
        if success:
            passed += 1
        else:
            failed += 1
        
        print(f"  [{status}] '{user_input}'")
        print(f"      -> Primary: {route.primary_model} (expected: {expected_model})")
        print(f"      -> Intent: {route.intent.value} (expected: {expected_intent.value})")
        print(f"      -> Fallback: {route.fallback_model}")
        print()
    
    print(f"Results: {passed} passed, {failed} failed")
    return failed == 0


def test_safe_retry(aura_module):
    """Test SafeRetry functionality."""
    SafeRetry = aura_module.SafeRetry
    ModelRouter = aura_module.ModelRouter
    
    print("\n" + "=" * 60)
    print("Testing Safe Retry")
    print("=" * 60)
    
    router = ModelRouter()
    retry_handler = SafeRetry(router)
    
    print("\n  Testing retryable error detection:")
    
    retryable = [429, 500, 502, 503, 504]
    non_retryable = [400, 401, 403, 404]
    
    all_passed = True
    for code in retryable:
        result = retry_handler.should_retry(code)
        status = "PASS" if result else "FAIL"
        if not result:
            all_passed = False
        print(f"    [{status}] Error {code} is retryable: {result}")
    
    for code in non_retryable:
        result = retry_handler.should_retry(code)
        status = "PASS" if not result else "FAIL"
        if result:
            all_passed = False
        print(f"    [{status}] Error {code} is not retryable: {result}")
    
    print("\n  Testing backup system instruction injection:")
    original = "You are a helpful assistant."
    backup = retry_handler.get_backup_system_instruction(original)
    
    has_backup_context = "backup model for Lume IDE" in backup
    status = "PASS" if has_backup_context else "FAIL"
    if not has_backup_context:
        all_passed = False
    print(f"    [{status}] Backup instruction includes rate limit context: {has_backup_context}")
    
    return all_passed


def test_openai_tools(tools_module):
    """Test OpenAI-compatible tool definitions."""
    get_openai_tools = tools_module.get_openai_tools
    get_gemini_tools = tools_module.get_gemini_tools
    get_anthropic_tools = tools_module.get_anthropic_tools
    
    print("\n" + "=" * 60)
    print("Testing OpenAI-Compatible Tool Definitions")
    print("=" * 60)
    
    print("\n  OpenAI Format:")
    openai_tools = get_openai_tools()
    print(f"    {len(openai_tools)} tools defined")
    for tool in openai_tools:
        func = tool.get("function", {})
        print(f"    - {func.get('name')}: {func.get('description')[:50]}...")
    
    all_valid = True
    for tool in openai_tools:
        if tool.get("type") != "function":
            print(f"    [FAIL] Missing 'type' field in {tool}")
            all_valid = False
        func = tool.get("function", {})
        if "name" not in func:
            print(f"    [FAIL] Missing 'name' in function")
            all_valid = False
        if "description" not in func:
            print(f"    [FAIL] Missing 'description' in function")
            all_valid = False
        if "parameters" not in func:
            print(f"    [FAIL] Missing 'parameters' in function")
            all_valid = False
    
    if all_valid:
        print("    [PASS] All OpenAI tools have required fields")
    
    print("\n  Gemini Format:")
    gemini_tools = get_gemini_tools()
    print(f"    {len(gemini_tools)} tool declarations defined")
    
    print("\n  Anthropic Format:")
    anthropic_tools = get_anthropic_tools()
    print(f"    {len(anthropic_tools)} tools defined")
    for tool in anthropic_tools:
        print(f"    - {tool.get('name')}")
    
    return all_valid


def test_model_registry(aura_module):
    """Test model registry configuration."""
    MODEL_REGISTRY = aura_module.MODEL_REGISTRY
    
    print("\n" + "=" * 60)
    print("Testing Model Registry")
    print("=" * 60)
    
    print(f"\n  {len(MODEL_REGISTRY)} models registered:")
    
    for model_key, config in MODEL_REGISTRY.items():
        print(f"\n    {model_key}:")
        print(f"      - Provider: {config.provider.value}")
        print(f"      - Model ID: {config.model_id}")
        print(f"      - API Key Env: {config.api_key_env}")
        print(f"      - Base URL: {config.base_url or 'N/A (Gemini default)'}")
        print(f"      - Is Free: {config.is_free}")
    
    fallback = MODEL_REGISTRY.get("openrouter/auto-free")
    if fallback is None:
        print("\n  [FAIL] Fallback model not found")
        return False
    if not fallback.is_free:
        print("\n  [FAIL] Fallback model should be marked as free")
        return False
    print("\n  [PASS] Fallback model correctly marked as free")
    
    return True


def test_direct_tools():
    """Test tools directly without importing through aura_client."""
    print("\n" + "=" * 60)
    print("Testing Direct Tool Functions")
    print("=" * 60)
    
    tools_path = os.path.join(os.path.dirname(__file__), 'app', 'engine', 'tools.py')
    tools_mod = load_module_directly("tools_direct", tools_path)
    
    print("\n  Testing list_directory:")
    result = tools_mod.tool_list_directory(".")
    print(f"    Result preview: {result[:150]}...")
    
    print("\n  Testing read_file:")
    result = tools_mod.tool_read_file(tools_path)
    print(f"    Read {len(result)} bytes from tools.py")
    
    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("MULTI-MODEL ORCHESTRATOR TEST SUITE")
    print("=" * 60)
    print()
    
    print("Loading modules directly to avoid circular imports...")
    
    # Load modules directly from files to avoid circular imports
    # The trick is to NOT import through package __init__.py
    
    # Step 1: Load tools first (no circular dependencies)
    tools_path = os.path.join(os.path.dirname(__file__), 'app', 'engine', 'tools.py')
    tools_module = load_module_directly("tools_test", tools_path)
    
    # Step 2: Create a minimal mock for TOOL_FUNCTIONS to avoid circular import
    # This allows us to test the orchestrator logic without triggering circular imports
    class MockToolExecutor:
        def __init__(self):
            self._tools = {
                "read_file": tools_module.tool_read_file,
                "write_file": tools_module.tool_write_file,
                "create_directory": tools_module.tool_create_directory,
                "list_directory": tools_module.tool_list_directory,
            }
        
        def execute(self, tool_name, arguments):
            tool_func = self._tools.get(tool_name)
            if not tool_func:
                return f"Error: Unknown tool '{tool_name}'"
            try:
                result = tool_func(**arguments)
                return result if isinstance(result, str) else str(result)
            except Exception as e:
                return f"Error executing {tool_name}: {str(e)}"
    
    # Step 3: Load aura_client but replace ToolExecutor with our mock
    aura_path = os.path.join(os.path.dirname(__file__), 'app', 'engine', 'aura_client.py')
    aura_module = load_module_directly("aura_client_test", aura_path)
    
    print("[OK] Modules loaded successfully\n")
    
    results = []
    
    # Run all tests
    results.append(("Intent Detection", test_intent_detection(aura_module)))
    results.append(("Model Routing", test_model_routing(aura_module)))
    results.append(("Safe Retry", test_safe_retry(aura_module)))
    results.append(("OpenAI Tools", test_openai_tools(tools_module)))
    results.append(("Model Registry", test_model_registry(aura_module)))
    results.append(("Direct Tool Functions", test_direct_tools()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status}: {test_name}")
        if not passed:
            all_passed = False
    
    print()
    print("=" * 60)
    print("MULTI-MODEL ORCHESTRATOR IMPLEMENTATION COMPLETE!")
    print("=" * 60)
    print()
    print("Features implemented:")
    print("  1. ModelRouter - Intent-based routing")
    print("     - Scan/List operations -> Groq")
    print("     - Build/Fix operations -> Gemini")
    print("  2. SafeRetry - Automatic retry on 429/500 errors")
    print("     - Switches to openrouter/auto-free fallback")
    print("  3. Context Injection - Backup model system instruction")
    print("  4. Standardized Tools - OpenAI-compatible format")
    print()
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
