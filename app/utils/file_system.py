import os
from pathlib import Path
from typing import Dict, List, Union

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
