import sqlite3

class ChronicleDB:
    def __init__(self, db_path):
        self.db_path = db_path
        self.connection = None

    def connect(self):
        try:
            self.connection = sqlite3.connect(self.db_path)
            print(f"Successfully connected to database at {self.db_path}")
            return True
        except sqlite3.Error as e:
            print(f"Error connecting to database: {e}")
            return False

    def create_tables(self):
        if not self.connection:
            print("Not connected to the database.")
            return

        cursor = self.connection.cursor()

        create_projects_table = """
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            path TEXT NOT NULL UNIQUE
        );
        """

        create_tasks_table = """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            title TEXT NOT NULL,
            status TEXT NOT NULL,
            result TEXT,
            error TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects (id)
        );
        """

        create_settings_table = """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """

        try:
            cursor.execute(create_projects_table)
            cursor.execute(create_tasks_table)
            cursor.execute(create_settings_table)
            self.connection.commit()
            print("Tables 'projects', 'tasks', and 'settings' created successfully.")
        except sqlite3.Error as e:
            print(f"Error creating tables: {e}")

    def save_setting(self, key, value):
        if not self.connection:
            print("Not connected to the database.")
            return
        
        cursor = self.connection.cursor()
        try:
            cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
            self.connection.commit()
            print(f"Setting '{key}' saved.")
        except sqlite3.Error as e:
            print(f"Error saving setting: {e}")

    def get_setting(self, key):
        if not self.connection:
            print("Not connected to the database.")
            return None
        
        cursor = self.connection.cursor()
        try:
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row[0] if row else None
        except sqlite3.Error as e:
            print(f"Error getting setting: {e}")
            return None

    def register_project(self, name, path):
        if not self.connection:
            print("Not connected to the database.")
            return None
        
        cursor = self.connection.cursor()
        try:
            cursor.execute("INSERT INTO projects (name, path) VALUES (?, ?)", (name, path))
            self.connection.commit()
            project_id = cursor.lastrowid
            print(f"Project '{name}' registered with id {project_id}.")
            return project_id
        except sqlite3.IntegrityError:
            print(f"Project with name '{name}' or path '{path}' already exists.")
            cursor.execute("SELECT id FROM projects WHERE name = ? OR path = ?", (name, path))
            project = cursor.fetchone()
            if project:
                return project[0]
            return None
        except sqlite3.Error as e:
            print(f"Error registering project: {e}")
            return None

    def create_tasks_table_migration(self):
        """Add missing columns to tasks table for new features"""
        if not self.connection:
            print("Not connected to the database.")
            return False
        
        cursor = self.connection.cursor()
        try:
            # Check if columns exist and add if they don't
            cursor.execute("PRAGMA table_info(tasks)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'result' not in columns:
                cursor.execute("ALTER TABLE tasks ADD COLUMN result TEXT")
            if 'error' not in columns:
                cursor.execute("ALTER TABLE tasks ADD COLUMN error TEXT")
            if 'created_at' not in columns:
                cursor.execute("ALTER TABLE tasks ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            if 'updated_at' not in columns:
                cursor.execute("ALTER TABLE tasks ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            
            self.connection.commit()
            print("Tasks table migration completed.")
            return True
        except sqlite3.Error as e:
            print(f"Error migrating tasks table: {e}")
            return False

    def create_ui_state_table(self):
        """Create table for storing UI state (tabs, scroll position, etc.)"""
        if not self.connection:
            print("Not connected to the database.")
            return
        
        cursor = self.connection.cursor()
        create_ui_state_table = """
        CREATE TABLE IF NOT EXISTS ui_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            state_type TEXT NOT NULL,
            state_key TEXT NOT NULL,
            state_value TEXT,
            FOREIGN KEY (project_id) REFERENCES projects (id),
            UNIQUE(project_id, state_type, state_key)
        );
        """
        
        try:
            cursor.execute(create_ui_state_table)
            self.connection.commit()
            print("UI state table created successfully.")
        except sqlite3.Error as e:
            print(f"Error creating ui_state table: {e}")

    def create_task(self, project_id: int, title: str, status: str = "pending") -> int:
        """Create a new task and return its ID"""
        if not self.connection:
            print("Not connected to the database.")
            return None
        
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                "INSERT INTO tasks (project_id, title, status) VALUES (?, ?, ?)",
                (project_id, title, status)
            )
            self.connection.commit()
            task_id = cursor.lastrowid
            print(f"Task '{title}' created with id {task_id}.")
            return task_id
        except sqlite3.Error as e:
            print(f"Error creating task: {e}")
            return None

    def update_task_result(self, task_id: int, result: str, status: str = "completed"):
        """Update task result and status"""
        if not self.connection:
            print("Not connected to the database.")
            return False
        
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                "UPDATE tasks SET result = ?, status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (result, status, task_id)
            )
            self.connection.commit()
            print(f"Task {task_id} result updated.")
            return True
        except sqlite3.Error as e:
            print(f"Error updating task result: {e}")
            return False

    def update_task_error(self, task_id: int, error: str, status: str = "failed"):
        """Update task error and status"""
        if not self.connection:
            print("Not connected to the database.")
            return False
        
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                "UPDATE tasks SET error = ?, status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (error, status, task_id)
            )
            self.connection.commit()
            print(f"Task {task_id} error updated.")
            return True
        except sqlite3.Error as e:
            print(f"Error updating task error: {e}")
            return False

    def get_tasks(self, project_id: int = None, status: str = None) -> list:
        """Get tasks, optionally filtered by project or status"""
        if not self.connection:
            print("Not connected to the database.")
            return []
        
        cursor = self.connection.cursor()
        query = "SELECT id, project_id, title, status, result, error, created_at, updated_at FROM tasks WHERE 1=1"
        params = []
        
        if project_id is not None:
            query += " AND project_id = ?"
            params.append(project_id)
        if status is not None:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY created_at DESC"
        
        try:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'project_id': row[1],
                    'title': row[2],
                    'status': row[3],
                    'result': row[4],
                    'error': row[5],
                    'created_at': row[6],
                    'updated_at': row[7]
                }
                for row in rows
            ]
        except sqlite3.Error as e:
            print(f"Error getting tasks: {e}")
            return []

    def save_ui_state(self, project_id: int, state_type: str, state_key: str, state_value: str):
        """Save UI state (tabs, scroll position, etc.)"""
        if not self.connection:
            print("Not connected to the database.")
            return False
        
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                """INSERT OR REPLACE INTO ui_state 
                   (project_id, state_type, state_key, state_value) 
                   VALUES (?, ?, ?, ?)""",
                (project_id, state_type, state_key, state_value)
            )
            self.connection.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error saving UI state: {e}")
            return False

    def get_ui_state(self, project_id: int, state_type: str = None, state_key: str = None) -> dict:
        """Get saved UI state"""
        if not self.connection:
            print("Not connected to the database.")
            return {}
        
        cursor = self.connection.cursor()
        query = "SELECT state_type, state_key, state_value FROM ui_state WHERE project_id = ?"
        params = [project_id]
        
        if state_type is not None:
            query += " AND state_type = ?"
            params.append(state_type)
        if state_key is not None:
            query += " AND state_key = ?"
            params.append(state_key)
        
        try:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            result = {}
            for row in rows:
                if row[0] not in result:
                    result[row[0]] = {}
                result[row[0]][row[1]] = row[2]
            return result
        except sqlite3.Error as e:
            print(f"Error getting UI state: {e}")
            return {}

    def save_session(self, project_path: str = None, open_tabs: list = None, 
                    window_geometry: str = None, sidebar_state: dict = None):
        """
        Save the current session state.
        
        Args:
            project_path: Path to the last opened project
            open_tabs: List of open file paths
            window_geometry: Window geometry string
            sidebar_state: Sidebar state dictionary
        """
        if not self.connection:
            print("Not connected to the database.")
            return False
        
        cursor = self.connection.cursor()
        
        try:
            # Save session metadata
            if project_path:
                cursor.execute(
                    "INSERT OR REPLACE INTO settings (key, value) VALUES ('last_project', ?)",
                    (project_path,)
                )
            
            if open_tabs:
                import json
                cursor.execute(
                    "INSERT OR REPLACE INTO settings (key, value) VALUES ('open_tabs', ?)",
                    (json.dumps(open_tabs),)
                )
            
            if window_geometry:
                cursor.execute(
                    "INSERT OR REPLACE INTO settings (key, value) VALUES ('window_geometry', ?)",
                    (window_geometry,)
                )
            
            if sidebar_state:
                import json
                cursor.execute(
                    "INSERT OR REPLACE INTO settings (key, value) VALUES ('sidebar_state', ?)",
                    (json.dumps(sidebar_state),)
                )
            
            self.connection.commit()
            print("Session saved successfully.")
            return True
        
        except sqlite3.Error as e:
            print(f"Error saving session: {e}")
            return False

    def load_session(self) -> dict:
        """
        Load the saved session state.
        
        Returns:
            Dictionary with session data
        """
        if not self.connection:
            print("Not connected to the database.")
            return {}
        
        cursor = self.connection.cursor()
        session = {}
        
        try:
            cursor.execute("SELECT key, value FROM settings WHERE key IN ('last_project', 'open_tabs', 'window_geometry', 'sidebar_state')")
            rows = cursor.fetchall()
            
            import json
            for key, value in rows:
                if key == 'open_tabs' or key == 'sidebar_state':
                    try:
                        session[key] = json.loads(value)
                    except json.JSONDecodeError:
                        session[key] = value
                else:
                    session[key] = value
            
            return session
        
        except sqlite3.Error as e:
            print(f"Error loading session: {e}")
            return {}

    def close(self):
        if self.connection:
            self.connection.close()
            print("Database connection closed.")
