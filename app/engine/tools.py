"""
Tool Functions for LumeIDE Aura Client

These functions are called by the AI model to perform file operations.
Each function has robust error handling to prevent IDE crashes.
"""

import os
from typing import Optional


def tool_read_file(path: str) -> str:
    """
    Reads the content of a file at the given path.
    
    Args:
        path: The path to the file to read.
    
    Returns:
        The file content as a string, or an error message.
    """
    try:
        normalized = os.path.normpath(path)
        if not os.path.exists(normalized):
            return f"Error: File not found at path: {normalized}"
        if not os.path.isfile(normalized):
            return f"Error: Path is not a file: {normalized}"
        
        with open(normalized, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"[Aura] Read file: {normalized}")
        return content
        
    except FileNotFoundError:
        return f"Error: File not found at path: {path}"
    except PermissionError:
        return f"Error: Permission denied reading file: {path}"
    except UnicodeDecodeError:
        return f"Error: Could not decode file (not UTF-8): {path}"
    except Exception as e:
        return f"Error reading file at {path}: {str(e)}"


def tool_write_file(path: str, content: str) -> str:
    """
    Writes or overwrites content to a file at the specified path.
    
    Args:
        path: The path to the file to write.
        content: The content to write to the file.
    
    Returns:
        Success message or an error message.
    """
    try:
        normalized = os.path.normpath(path)
        
        # Ensure parent directories exist
        parent_dir = os.path.dirname(normalized)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        
        with open(normalized, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"[Aura] Wrote file: {normalized}")
        return f"Successfully wrote to {normalized}"
        
    except PermissionError:
        return f"Error: Permission denied writing to file: {path}"
    except OSError as e:
        return f"Error writing to file at {path}: {str(e)}"
    except Exception as e:
        return f"Error writing to file at {path}: {str(e)}"


def tool_create_directory(path: str) -> str:
    """
    Creates a directory at the specified path.
    
    Args:
        path: The path to the directory to create.
    
    Returns:
        Success message or an error message.
    """
    try:
        normalized = os.path.normpath(path)
        os.makedirs(normalized, exist_ok=True)
        print(f"[Aura] Created directory: {normalized}")
        return f"Successfully created directory: {normalized}"
        
    except PermissionError:
        return f"Error: Permission denied creating directory: {path}"
    except OSError as e:
        return f"Error creating directory at {path}: {str(e)}"
    except Exception as e:
        return f"Error creating directory at {path}: {str(e)}"


def tool_list_directory(path: str) -> str:
    """
    Lists the contents of a directory.
    
    Args:
        path: The path to the directory to list.
    
    Returns:
        A formatted list of directory contents or an error message.
    """
    try:
        normalized = os.path.normpath(path)
        if not os.path.exists(normalized):
            return f"Error: Directory not found at path: {normalized}"
        if not os.path.isdir(normalized):
            return f"Error: Path is not a directory: {normalized}"
        
        entries = os.listdir(normalized)
        result_lines = [f"Contents of {normalized}:", ""]
        
        for entry in sorted(entries):
            full_path = os.path.join(normalized, entry)
            if os.path.isdir(full_path):
                result_lines.append(f"  [DIR]  {entry}/")
            else:
                size = os.path.getsize(full_path)
                result_lines.append(f"  [FILE] {entry} ({size} bytes)")
        
        return "\n".join(result_lines)
        
    except PermissionError:
        return f"Error: Permission denied listing directory: {path}"
    except Exception as e:
        return f"Error listing directory at {path}: {str(e)}"


# Export all tool functions for easy registration
TOOL_FUNCTIONS = {
    "read_file": tool_read_file,
    "write_file": tool_write_file,
    "create_directory": tool_create_directory,
    "list_directory": tool_list_directory,
}


__all__ = [
    'tool_read_file',
    'tool_write_file', 
    'tool_create_directory',
    'tool_list_directory',
    'TOOL_FUNCTIONS',
]
