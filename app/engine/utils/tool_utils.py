import inspect
from typing import Callable, Dict, Any, List

def get_tool_function_schema(func: Callable) -> Dict[str, Any]:
    """
    Generates a Gemini API-compatible function declaration schema for a given Python function.

    Args:
        func: The Python function to generate the schema for.

    Returns:
        A dictionary representing the function's schema.
    """
    signature = inspect.signature(func)
    parameters = {}
    required_params = []

    # Parse docstring for overall description and parameter descriptions
    docstring = inspect.getdoc(func)
    overall_description = f"Performs the operation of {func.__name__}."
    param_descriptions = {}

    if docstring:
        lines = docstring.strip().split('\n')
        # The first non-empty line is usually the short description
        for line in lines:
            if line.strip():
                overall_description = line.strip()
                break
        
        # Basic parsing for @param or Args: sections
        # This is a simple approach and can be made more robust with a docstring parser library
        for i, line in enumerate(lines):
            if line.strip().startswith("Args:"):
                for j in range(i + 1, len(lines)):
                    param_line = lines[j].strip()
                    if not param_line:
                        break
                    if param_line.startswith("Returns:") or param_line.startswith("Raises:"):
                        break
                    
                    # Expecting format: param_name: Description
                    if ":" in param_line:
                        parts = param_line.split(":", 1)
                        param_name = parts[0].strip()
                        description = parts[1].strip()
                        if param_name.endswith(":"): # Handle cases like "path: The path..."
                            param_name = param_name[:-1].strip()
                        param_descriptions[param_name] = description
                    elif param_line.startswith("    "): # Handle indented descriptions
                        # This is a very basic attempt, a full parser would be better
                        last_param = list(param_descriptions.keys())[-1] if param_descriptions else None
                        if last_param:
                            param_descriptions[last_param] += " " + param_line.strip()


    for name, param in signature.parameters.items():
        if name == 'self':  # Skip 'self' for methods
            continue

        param_type = 'string' # Default to string
        # Attempt to infer type from annotation
        if param.annotation is not inspect.Parameter.empty:
            if param.annotation is str:
                param_type = 'string'
            elif param.annotation is int or param.annotation is float:
                param_type = 'number'
            elif param.annotation is bool:
                param_type = 'boolean'
            elif param.annotation is list:
                param_type = 'array'
            elif param.annotation is dict:
                param_type = 'object'
            # For Optional[str], etc., we'd need more advanced parsing (e.g., typing_inspect)
            # For now, we'll keep it simple.
            elif hasattr(param.annotation, '__origin__'):
                if param.annotation.__origin__ is list:
                    param_type = 'array'
                elif param.annotation.__origin__ is dict:
                    param_type = 'object'
                # Handle Optional types
                if param.annotation.__origin__ is Optional:
                    # Get the actual type from Optional[Type]
                    actual_type = param.annotation.__args__[0]
                    if actual_type is str:
                        param_type = 'string'
                    elif actual_type is int or actual_type is float:
                        param_type = 'number'
                    elif actual_type is bool:
                        param_type = 'boolean'
                    elif actual_type is list:
                        param_type = 'array'
                    elif actual_type is dict:
                        param_type = 'object'


        parameters[name] = {
            "type": param_type,
            "description": param_descriptions.get(name, f"Parameter '{name}' for {func.__name__}.")
        }
        if param.default is inspect.Parameter.empty:
            required_params.append(name)

    return {
        "name": func.__name__,
        "description": overall_description,
        "parameters": {
            "type": "object",
            "properties": parameters,
            "required": required_params
        }
    }

def build_all_tool_declarations(tool_functions: Dict[str, Callable]) -> List[Dict]:
    """
    Builds a list of Gemini API-compatible function declarations for all provided tool functions.

    Args:
        tool_functions: A dictionary of tool names to callable functions.

    Returns:
        A list of dictionaries, each representing a tool's function declaration.
    """
    declarations = []
    for tool_name, func in tool_functions.items():
        # Ensure the name in the schema matches the key in TOOL_FUNCTIONS
        schema = get_tool_function_schema(func)
        schema["name"] = tool_name # Override with the key from TOOL_FUNCTIONS to ensure consistency
        declarations.append(schema)
    return declarations
