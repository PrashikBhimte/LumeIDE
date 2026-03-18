"""
Venv Auto-Detector for LumeIDE

This module automatically finds and configures virtual environments (.venv)
when a folder is opened.
"""

import os
import sys
import subprocess
from typing import Optional, List, Tuple
from pathlib import Path


class VenvDetector:
    """
    Auto-detects and manages virtual environments for Python projects.
    Supports various venv patterns and can configure the interpreter.
    """
    
    # Common virtual environment directory names
    VENV_NAMES = [
        '.venv',           # Standard Python venv
        'venv',            # Alternative
        '.virtualenv',     # virtualenv package
        'virtualenv',
        'env',             # Conda default
        '.env',
        'venv37',         # Version-specific
        'venv38',
        'venv39',
        'venv310',
        'venv311',
        'venv312',
    ]
    
    # Scripts/executables to look for in venv
    VENV_BIN_PATHS = {
        'win32': ['Scripts', 'Scripts/python.exe', 'Scripts/python3.exe'],
        'linux': ['bin', 'bin/python', 'bin/python3'],
        'darwin': ['bin', 'bin/python', 'bin/python3'],
    }
    
    def __init__(self):
        self.detected_venvs: List[dict] = []
        self.active_venv: Optional[dict] = None
        self.project_root: Optional[str] = None
    
    def find_venv_in_directory(self, directory: str) -> Optional[dict]:
        """
        Find a virtual environment in the given directory or its parents.
        
        Args:
            directory: The directory to search in
            
        Returns:
            Dictionary with venv information or None if not found
        """
        start_path = Path(directory).resolve()
        
        # Check the directory itself
        venv_info = self._check_directory_for_venv(start_path)
        if venv_info:
            return venv_info
        
        # Check parent directories up to 5 levels
        for parent in start_path.parents[:5]:
            venv_info = self._check_directory_for_venv(parent)
            if venv_info:
                return venv_info
        
        return None
    
    def _check_directory_for_venv(self, directory: Path) -> Optional[dict]:
        """Check a specific directory for a virtual environment"""
        for venv_name in self.VENV_NAMES:
            venv_path = directory / venv_name
            
            if not venv_path.exists():
                continue
            
            # Check if it's a directory
            if not venv_path.is_dir():
                continue
            
            # Find the Python executable
            python_path = self._find_python_in_venv(venv_path)
            if python_path:
                # Verify the venv is valid
                if self._verify_venv(venv_path, python_path):
                    return {
                        'name': venv_name,
                        'path': str(venv_path),
                        'python_path': str(python_path),
                        'type': self._detect_venv_type(venv_path),
                        'is_active': self._is_venv_active(venv_path)
                    }
        
        return None
    
    def _find_python_in_venv(self, venv_path: Path) -> Optional[Path]:
        """Find the Python executable in a virtual environment"""
        platform = sys.platform
        
        # Get the appropriate bin paths for this platform
        if platform == 'win32':
            bin_candidates = ['Scripts']
        else:
            bin_candidates = ['bin']
        
        for bin_name in bin_candidates:
            bin_path = venv_path / bin_name
            
            if not bin_path.exists():
                continue
            
            # Look for python executable
            if platform == 'win32':
                python_candidates = ['python.exe', 'python3.exe', 'python']
            else:
                python_candidates = ['python3', 'python']
            
            for python_name in python_candidates:
                python_path = bin_path / python_name
                if python_path.exists():
                    return python_path
        
        return None
    
    def _verify_venv(self, venv_path: Path, python_path: Path) -> bool:
        """Verify that a virtual environment is valid"""
        try:
            # Try to get the Python version
            result = subprocess.run(
                [str(python_path), '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False
    
    def _detect_venv_type(self, venv_path: Path) -> str:
        """Detect the type of virtual environment"""
        # Check for pyvenv.cfg (venv module)
        if (venv_path / 'pyvenv.cfg').exists():
            return 'venv'
        
        # Check for activate script (virtualenv)
        if sys.platform == 'win32':
            activate_script = venv_path / 'Scripts' / 'activate.bat'
        else:
            activate_script = venv_path / 'bin' / 'activate'
        
        if activate_script.exists():
            return 'virtualenv'
        
        # Check for conda
        if (venv_path / 'conda-meta').exists():
            return 'conda'
        
        return 'unknown'
    
    def _is_venv_active(self, venv_path: Path) -> bool:
        """Check if this venv is currently active"""
        if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            try:
                active_path = Path(sys.prefix).resolve()
                return active_path == venv_path.resolve()
            except:
                pass
        return False
    
    def find_all_venvs_in_directory(self, directory: str, recursive: bool = False) -> List[dict]:
        """
        Find all virtual environments in a directory tree.
        
        Args:
            directory: The root directory to search
            recursive: Whether to search subdirectories
            
        Returns:
            List of virtual environment information dictionaries
        """
        self.detected_venvs = []
        root_path = Path(directory).resolve()
        
        if recursive:
            self._recursive_search(root_path)
        else:
            # Just check the directory and immediate children
            self._check_directory_for_venv(root_path)
            
            # Check immediate subdirectories
            try:
                for item in root_path.iterdir():
                    if item.is_dir() and not item.name.startswith('.'):
                        venv_info = self._check_directory_for_venv(item)
                        if venv_info:
                            self.detected_venvs.append(venv_info)
            except PermissionError:
                pass
        
        return self.detected_venvs
    
    def _recursive_search(self, directory: Path):
        """Recursively search for virtual environments"""
        try:
            for item in directory.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    venv_info = self._check_directory_for_venv(item)
                    if venv_info:
                        self.detected_venvs.append(venv_info)
                    else:
                        # Continue searching in subdirectories
                        self._recursive_search(item)
        except PermissionError:
            pass
    
    def get_python_info(self, venv_info: dict) -> dict:
        """
        Get detailed Python information from a virtual environment.
        
        Args:
            venv_info: Virtual environment information dictionary
            
        Returns:
            Dictionary with Python version and path info
        """
        python_path = venv_info.get('python_path')
        if not python_path:
            return {}
        
        try:
            result = subprocess.run(
                [python_path, '-c', 'import sys; print(sys.version); print(sys.executable)'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                return {
                    'version': lines[0] if lines else 'Unknown',
                    'executable': lines[1] if len(lines) > 1 else python_path,
                    'python_path': python_path
                }
        except:
            pass
        
        return {}
    
    def set_active_venv(self, venv_info: dict) -> bool:
        """
        Set a virtual environment as active.
        
        Args:
            venv_info: Virtual environment information dictionary
            
        Returns:
            True if successful, False otherwise
        """
        python_path = venv_info.get('python_path')
        if not python_path:
            return False
        
        # Update the interpreter path (this is for display purposes)
        # Actual Python interpreter switching would require modifying PATH
        # or using a different Python executable
        self.active_venv = venv_info
        return True
    
    def get_activation_command(self, venv_info: dict) -> dict:
        """
        Get platform-specific activation commands for a virtual environment.
        
        Args:
            venv_info: Virtual environment information dictionary
            
        Returns:
            Dictionary with activation commands for different shells
        """
        venv_path = venv_info.get('path', '')
        platform = sys.platform
        
        commands = {}
        
        if platform == 'win32':
            commands['cmd'] = f'"{venv_path}\\Scripts\\activate.bat"'
            commands['powershell'] = f'"{venv_path}\\Scripts\\Activate.ps1"'
            commands['python'] = f'"{venv_path}\\Scripts\\python.exe"'
        else:
            commands['bash'] = f'source "{venv_path}/bin/activate"'
            commands['zsh'] = f'source "{venv_path}/bin/activate"'
            commands['fish'] = f'source "{venv_path}/bin/activate.fish"'
            commands['python'] = f'"{venv_path}/bin/python"'
        
        return commands
    
    def is_venv_compatible(self, venv_info: dict, required_version: str = None) -> bool:
        """
        Check if a virtual environment is compatible with requirements.
        
        Args:
            venv_info: Virtual environment information dictionary
            required_version: Required Python version (e.g., "3.11")
            
        Returns:
            True if compatible, False otherwise
        """
        if not required_version:
            return True
        
        python_info = self.get_python_info(venv_info)
        version = python_info.get('version', '')
        
        # Simple version check
        if required_version in version:
            return True
        
        return False
    
    def scan_project(self, project_path: str) -> dict:
        """
        Scan a project directory for virtual environments and configuration.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            Dictionary with scan results
        """
        result = {
            'project_path': project_path,
            'venv_found': None,
            'all_venvs': [],
            'has_requirements': False,
            'has_pyproject': False,
            'has_setup': False,
            'recommendations': []
        }
        
        # Find virtual environment
        result['venv_found'] = self.find_venv_in_directory(project_path)
        if result['venv_found']:
            result['recommendations'].append(
                f"Virtual environment found: {result['venv_found']['name']}"
            )
        
        # Find all venvs
        result['all_venvs'] = self.find_all_venvs_in_directory(project_path)
        
        # Check for common project files
        project_path_obj = Path(project_path)
        result['has_requirements'] = (
            (project_path_obj / 'requirements.txt').exists() or
            (project_path_obj / 'requirements-dev.txt').exists()
        )
        result['has_pyproject'] = (project_path_obj / 'pyproject.toml').exists()
        result['has_setup'] = (
            (project_path_obj / 'setup.py').exists() or
            (project_path_obj / 'setup.cfg').exists()
        )
        
        # Generate recommendations
        if not result['venv_found']:
            result['recommendations'].append(
                "No virtual environment detected. Consider creating one with: python -m venv .venv"
            )
        
        if result['has_requirements'] and not result['venv_found']:
            result['recommendations'].append(
                "requirements.txt found. Install dependencies after setting up a venv."
            )
        
        return result
    
    def create_venv(self, directory: str, name: str = '.venv', 
                    system_site_packages: bool = False) -> Optional[dict]:
        """
        Create a new virtual environment.
        
        Args:
            directory: Directory to create the venv in
            name: Name of the venv directory
            system_site_packages: Whether to include system site-packages
            
        Returns:
            Virtual environment information dictionary or None on failure
        """
        venv_path = Path(directory) / name
        
        if venv_path.exists():
            return None  # Venv already exists
        
        try:
            cmd = [sys.executable, '-m', 'venv', str(venv_path)]
            if system_site_packages:
                cmd.append('--system-site-packages')
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # Verify and return info
                venv_info = self._check_directory_for_venv(venv_path)
                if venv_info:
                    return venv_info
        except Exception as e:
            print(f"Error creating venv: {e}")
        
        return None


# Export for use by other modules
__all__ = ['VenvDetector']
