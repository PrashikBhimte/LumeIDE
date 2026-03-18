"""
UI State Manager for LumeIDE

This module handles auto-saving UI states (tabs, scroll positions, etc.)
to Chronicle DB for persistence across sessions.
"""

import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal, QTimer


@dataclass
class TabState:
    """State information for a single tab"""
    tab_id: str
    title: str
    file_path: Optional[str] = None
    content: Optional[str] = None
    scroll_position: int = 0
    cursor_position: int = 0
    is_modified: bool = False
    order: int = 0


@dataclass
class WindowState:
    """Complete window state"""
    window_geometry: Optional[str] = None
    window_state: Optional[str] = None
    is_maximized: bool = False
    is_fullscreen: bool = False


class UIStateManager(QObject):
    """
    Manages UI state persistence across sessions.
    Auto-saves tab configurations, scroll positions, and other UI states.
    """
    
    # Signals
    state_loaded = pyqtSignal(dict)
    state_saved = pyqtSignal(str)
    
    def __init__(self, database=None, project_id: int = None):
        """
        Initialize the UI State Manager.
        
        Args:
            database: ChronicleDB instance for persistence
            project_id: ID of the current project
        """
        super().__init__()
        self.database = database
        self.project_id = project_id
        self._pending_saves: Dict[str, Any] = {}
        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._flush_pending_saves)
        self._debounce_delay = 500  # ms
        
        # In-memory cache
        self._state_cache: Dict[str, Any] = {}
        
        # State type constants
        self.TAB_STATE = 'tabs'
        self.WINDOW_STATE = 'window'
        self.SIDEBAR_STATE = 'sidebar'
        self.SETTINGS_STATE = 'settings'
        self.RECENT_FILES = 'recent_files'
    
    def set_database(self, database, project_id: int = None):
        """Set the database for persistence"""
        self.database = database
        if project_id is not None:
            self.project_id = project_id
    
    def set_project_id(self, project_id: int):
        """Set the current project ID"""
        self.project_id = project_id
        # Load state for new project
        self.load_all_states()
    
    def save_tab_state(self, tabs: List[Dict[str, Any]]):
        """
        Save the current tab configuration.
        
        Args:
            tabs: List of tab state dictionaries
        """
        if self.project_id is None:
            return
        
        # Convert to TabState objects for validation
        tab_states = []
        for i, tab_data in enumerate(tabs):
            tab_state = TabState(
                tab_id=tab_data.get('tab_id', f'tab_{i}'),
                title=tab_data.get('title', 'Untitled'),
                file_path=tab_data.get('file_path'),
                scroll_position=tab_data.get('scroll_position', 0),
                cursor_position=tab_data.get('cursor_position', 0),
                is_modified=tab_data.get('is_modified', False),
                order=i
            )
            tab_states.append(tab_state)
        
        # Store in pending saves
        self._pending_saves[self.TAB_STATE] = json.dumps([
            asdict(ts) for ts in tab_states
        ], default=str)
        
        self._schedule_save(self.TAB_STATE)
    
    def load_tab_state(self) -> List[Dict[str, Any]]:
        """
        Load saved tab configuration.
        
        Returns:
            List of tab state dictionaries
        """
        cache_key = self.TAB_STATE
        
        # Check cache first
        if cache_key in self._state_cache:
            return self._state_cache[cache_key]
        
        # Check pending saves
        if cache_key in self._pending_saves:
            return json.loads(self._pending_saves[cache_key])
        
        # Load from database
        if self.database and self.project_id is not None:
            state_dict = self.database.get_ui_state(
                self.project_id, 
                state_type=cache_key
            )
            
            if cache_key in state_dict:
                tabs_data = json.loads(state_dict[cache_key])
                self._state_cache[cache_key] = tabs_data
                return tabs_data
        
        return []
    
    def save_window_state(self, geometry: str = None, state: str = None,
                         is_maximized: bool = False, is_fullscreen: bool = False):
        """
        Save window geometry and state.
        
        Args:
            geometry: Window geometry string
            state: Window state string
            is_maximized: Whether window is maximized
            is_fullscreen: Whether window is in fullscreen mode
        """
        if self.project_id is None:
            return
        
        window_state = WindowState(
            window_geometry=geometry,
            window_state=state,
            is_maximized=is_maximized,
            is_fullscreen=is_fullscreen
        )
        
        self._pending_saves[self.WINDOW_STATE] = json.dumps(
            asdict(window_state), 
            default=str
        )
        self._schedule_save(self.WINDOW_STATE)
    
    def load_window_state(self) -> Optional[Dict[str, Any]]:
        """
        Load saved window state.
        
        Returns:
            Window state dictionary or None
        """
        cache_key = self.WINDOW_STATE
        
        # Check cache first
        if cache_key in self._state_cache:
            return self._state_cache[cache_key]
        
        # Check pending saves
        if cache_key in self._pending_saves:
            return json.loads(self._pending_saves[cache_key])
        
        # Load from database
        if self.database and self.project_id is not None:
            state_dict = self.database.get_ui_state(
                self.project_id,
                state_type=cache_key
            )
            
            if cache_key in state_dict:
                window_data = json.loads(state_dict[cache_key])
                self._state_cache[cache_key] = window_data
                return window_data
        
        return None
    
    def save_sidebar_state(self, width: int = None, is_visible: bool = True,
                          active_panel: str = None):
        """
        Save sidebar configuration.
        
        Args:
            width: Sidebar width
            is_visible: Whether sidebar is visible
            active_panel: Currently active panel name
        """
        if self.project_id is None:
            return
        
        sidebar_data = {
            'width': width,
            'is_visible': is_visible,
            'active_panel': active_panel
        }
        
        self._pending_saves[self.SIDEBAR_STATE] = json.dumps(sidebar_data)
        self._schedule_save(self.SIDEBAR_STATE)
    
    def load_sidebar_state(self) -> Dict[str, Any]:
        """
        Load saved sidebar configuration.
        
        Returns:
            Sidebar state dictionary
        """
        cache_key = self.SIDEBAR_STATE
        default = {'width': 250, 'is_visible': True, 'active_panel': 'explorer'}
        
        # Check cache first
        if cache_key in self._state_cache:
            return self._state_cache[cache_key]
        
        # Check pending saves
        if cache_key in self._pending_saves:
            return json.loads(self._pending_saves[cache_key])
        
        # Load from database
        if self.database and self.project_id is not None:
            state_dict = self.database.get_ui_state(
                self.project_id,
                state_type=cache_key
            )
            
            if cache_key in state_dict:
                sidebar_data = json.loads(state_dict[cache_key])
                self._state_cache[cache_key] = sidebar_data
                return sidebar_data
        
        return default
    
    def save_scroll_position(self, tab_id: str, position: int, 
                            cursor_pos: int = 0):
        """
        Save scroll position for a specific tab.
        
        Args:
            tab_id: Tab identifier
            position: Scroll position
            cursor_pos: Cursor position
        """
        if self.project_id is None:
            return
        
        scroll_key = f'scroll_{tab_id}'
        scroll_data = {
            'tab_id': tab_id,
            'position': position,
            'cursor': cursor_pos,
            'timestamp': datetime.now().isoformat()
        }
        
        self._pending_saves[scroll_key] = json.dumps(scroll_data)
        self._schedule_save(scroll_key)
    
    def load_scroll_position(self, tab_id: str) -> Optional[Dict[str, Any]]:
        """
        Load scroll position for a specific tab.
        
        Args:
            tab_id: Tab identifier
            
        Returns:
            Scroll position data or None
        """
        scroll_key = f'scroll_{tab_id}'
        
        # Check cache first
        if scroll_key in self._state_cache:
            return self._state_cache[scroll_key]
        
        # Check pending saves
        if scroll_key in self._pending_saves:
            return json.loads(self._pending_saves[scroll_key])
        
        # Load from database
        if self.database and self.project_id is not None:
            state_dict = self.database.get_ui_state(
                self.project_id,
                state_type='scroll',
                state_key=tab_id
            )
            
            if 'scroll' in state_dict and tab_id in state_dict['scroll']:
                scroll_data = json.loads(state_dict['scroll'][tab_id])
                self._state_cache[scroll_key] = scroll_data
                return scroll_data
        
        return None
    
    def save_recent_files(self, files: List[str], max_files: int = 20):
        """
        Save list of recent files.
        
        Args:
            files: List of file paths
            max_files: Maximum number of files to save
        """
        if self.project_id is None:
            return
        
        recent_files = files[:max_files]
        self._pending_saves[self.RECENT_FILES] = json.dumps(recent_files)
        self._schedule_save(self.RECENT_FILES)
    
    def load_recent_files(self) -> List[str]:
        """
        Load recent files list.
        
        Returns:
            List of recent file paths
        """
        cache_key = self.RECENT_FILES
        
        # Check cache first
        if cache_key in self._state_cache:
            return self._state_cache[cache_key]
        
        # Check pending saves
        if cache_key in self._pending_saves:
            return json.loads(self._pending_saves[cache_key])
        
        # Load from database
        if self.database and self.project_id is not None:
            state_dict = self.database.get_ui_state(
                self.project_id,
                state_type=cache_key
            )
            
            if cache_key in state_dict:
                recent_files = json.loads(state_dict[cache_key])
                self._state_cache[cache_key] = recent_files
                return recent_files
        
        return []
    
    def save_custom_state(self, state_type: str, state_key: str, value: Any):
        """
        Save a custom state value.
        
        Args:
            state_type: Type/category of the state
            state_key: Key within the state type
            value: Value to save (will be JSON serialized)
        """
        if self.project_id is None:
            return
        
        cache_key = f'{state_type}_{state_key}'
        self._pending_saves[cache_key] = json.dumps(value, default=str)
        self._schedule_save(cache_key)
    
    def load_custom_state(self, state_type: str, state_key: str, 
                          default: Any = None) -> Any:
        """
        Load a custom state value.
        
        Args:
            state_type: Type/category of the state
            state_key: Key within the state type
            default: Default value if not found
            
        Returns:
            The saved value or default
        """
        cache_key = f'{state_type}_{state_key}'
        
        # Check cache first
        if cache_key in self._state_cache:
            return self._state_cache[cache_key]
        
        # Check pending saves
        if cache_key in self._pending_saves:
            value = json.loads(self._pending_saves[cache_key])
            self._state_cache[cache_key] = value
            return value
        
        # Load from database
        if self.database and self.project_id is not None:
            state_dict = self.database.get_ui_state(
                self.project_id,
                state_type=state_type,
                state_key=state_key
            )
            
            if state_type in state_dict and state_key in state_dict[state_type]:
                value = json.loads(state_dict[state_type][state_key])
                self._state_cache[cache_key] = value
                return value
        
        return default
    
    def _schedule_save(self, key: str):
        """Schedule a debounced save operation"""
        self._debounce_timer.start(self._debounce_delay)
    
    def _flush_pending_saves(self):
        """Flush all pending saves to the database"""
        if not self.database or self.project_id is None:
            return
        
        for cache_key, value in self._pending_saves.items():
            # Determine state_type and state_key from cache_key
            if cache_key.startswith('scroll_'):
                state_type = 'scroll'
                state_key = cache_key[7:]  # Remove 'scroll_' prefix
            else:
                state_type = cache_key
                state_key = '_default'
            
            self.database.save_ui_state(
                self.project_id,
                state_type,
                state_key,
                value
            )
            self.state_saved.emit(cache_key)
        
        self._pending_saves.clear()
    
    def load_all_states(self):
        """Load all saved states from the database"""
        if not self.database or self.project_id is None:
            return
        
        all_states = self.database.get_ui_state(self.project_id)
        self._state_cache.update(all_states)
        self.state_loaded.emit(all_states)
    
    def save_all_immediately(self):
        """Force immediate save of all pending changes"""
        self._debounce_timer.stop()
        self._flush_pending_saves()
    
    def clear_all_states(self):
        """Clear all saved states for the current project"""
        if not self.database or self.project_id is None:
            return
        
        # Clear from database (would need a method for this)
        self._state_cache.clear()
        self._pending_saves.clear()
    
    def export_state(self) -> str:
        """
        Export all UI state as a JSON string.
        
        Returns:
            JSON string of all state
        """
        return json.dumps(self._state_cache, indent=2, default=str)
    
    def import_state(self, state_json: str):
        """
        Import UI state from a JSON string.
        
        Args:
            state_json: JSON string of state data
        """
        try:
            imported = json.loads(state_json)
            self._state_cache.update(imported)
            
            # Save to database
            for state_type, states in imported.items():
                if isinstance(states, dict):
                    for state_key, value in states.items():
                        if self.project_id is not None:
                            self.database.save_ui_state(
                                self.project_id,
                                state_type,
                                state_key,
                                json.dumps(value) if not isinstance(value, str) else value
                            )
        except json.JSONDecodeError:
            print("Invalid JSON in state import")


# Export for use by other modules
__all__ = ['UIStateManager', 'TabState', 'WindowState']
