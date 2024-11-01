import sqlite3

# Absolute path to the database
DATABASE_PATH = r'G:\PythonCoding-master\temperature_data.db'

def create_db():
    try:
        # Connect to the SQLite database (creates the file if it does not exist)
        conn = sqlite3.connect(DATABASE_PATH)
        c = conn.cursor()
        
        # Create table if it does not exist
        c.execute('''
            CREATE TABLE IF NOT EXISTS vessel_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id INTEGER,
                level INTEGER,
                timestamp TEXT
            )
        ''')
        
        # Commit the changes
        conn.commit()
        # Close the connection
        conn.close()
        print("Database and table created successfully.")
    except sqlite3.Error as e:
        print(f"Error creating database or table: {e}")

if __name__ == "__main__":
    create_db()
