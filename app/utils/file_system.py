import os
from pathlib import Path
from typing import Dict, List, Union


def tool_read_file(path: str) -> str:
    """
    Reads the content of a file at the given path.
    This tool is meant to be used by the Gemini model.
    
    Args:
        path: Path to the file to read
        
    Returns:
        File contents as string or error message
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: File not found at path: {path}"
    except Exception as e:
        return f"Error reading file at {path}: {e}"


def tool_write_file(path: str, content: str) -> str:
    """
    Writes or overwrites content to a file at the specified path.
    
    Args:
        path: Path to the file to write
        content: Content to write to the file
        
    Returns:
        Success or error message
    """
    try:
        safe_path = os.path.normpath(path)
        # Ensure directories exist
        os.makedirs(os.path.dirname(safe_path), exist_ok=True)
        with open(safe_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote to {path}"
    except Exception as e:
        return f"Error writing to file at {path}: {str(e)}"


def scan_directory_to_tree(path: str) -> Dict[str, Union[str, List]]:
    """
    Scans a directory and returns a JSON-ready tree structure.

    Args:
        path: The absolute or relative path to the directory.

    Returns:
        A dictionary representing the directory tree.
        Example:
        {
            "name": "directory_name",
            "path": "/path/to/directory",
            "type": "directory",
            "children": [
                {
                    "name": "file.txt",
                    "path": "/path/to/directory/file.txt",
                    "type": "file"
                },
                {
                    "name": "subdirectory",
                    "path": "/path/to/directory/subdirectory",
                    "type": "directory",
                    "children": []
                }
            ]
        }
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")

    if not p.is_dir():
       return {
            "name": p.name,
            "path": str(p.resolve()),
            "type": "file",
        }

    dir_info = {
        "name": p.name,
        "path": str(p.resolve()),
        "type": "directory",
        "children": []
    }

    for item in sorted(p.iterdir()):
        if item.is_dir():
            dir_info["children"].append(scan_directory_to_tree(str(item)))
        else:
            dir_info["children"].append({
                "name": item.name,
                "path": str(item.resolve()),
                "type": "file"
            })
    return dir_info
