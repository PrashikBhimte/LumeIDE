from dataclasses import dataclass
from typing import Optional

@dataclass
class ProjectContext:
    """
    Holds the context for the current project.
    """
    description: Optional[str] = None
    tech_stack: Optional[str] = "Python/AI"
    venv_path: Optional[str] = None
