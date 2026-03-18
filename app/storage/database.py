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

    def close(self):
        if self.connection:
            self.connection.close()
            print("Database connection closed.")
