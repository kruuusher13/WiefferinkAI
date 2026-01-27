import pyodbc
import time
import os

# Connection Settings matching docker-compose
SERVER = 'localhost'
DATABASE = 'master' # Connect to master first
USERNAME = 'sa'
PASSWORD = 'StrongPassword123!'
DRIVER = '{ODBC Driver 17 for SQL Server}'

CONN_STR = f'DRIVER={DRIVER};SERVER={SERVER};DATABASE={DATABASE};UID={USERNAME};PWD={PASSWORD}'

def wait_for_db():
    retries = 30
    while retries > 0:
        try:
            conn = pyodbc.connect(CONN_STR)
            conn.close()
            print("Database is ready!")
            return
        except Exception as e:
            print(f"Waiting for database... ({retries} retries left) - Error: {e}")
            time.sleep(2)
            retries -= 1
    raise Exception("Database failed to start")

def execute_script(filename):
    # Connect to master to create DB
    conn = pyodbc.connect(CONN_STR)
    conn.autocommit = True
    cursor = conn.cursor()
    
    # Drop/Create WinCarLive DB
    try:
        # Ensure we aren't hanging on to old connections
        cursor.execute("USE master")
        try:
            cursor.execute("ALTER DATABASE WinCarLive SET SINGLE_USER WITH ROLLBACK IMMEDIATE")
            cursor.execute("DROP DATABASE WinCarLive")
            print("Dropped existing database.")
        except Exception as e:
            # Maybe it doesn't exist, that's fine
            print(f"Note: drop database failed (might not exist): {e}")
            pass
        
        cursor.execute("CREATE DATABASE WinCarLive")
        print("Created WinCarLive database.")
    except Exception as e:
        print(f"Critical Error creating database: {e}")
        raise e
    finally:
        conn.close()

    # Connect to new DB
    conn = pyodbc.connect(CONN_STR.replace("master", "WinCarLive"), autocommit=True)
    cursor = conn.cursor()

    with open(filename, 'r') as f:
        sql_content = f.read()
        
    # Split by simple semicolon logic (naive but works for this seed file)
    commands = sql_content.split(';')
    
    for command in commands:
        if command.strip():
            try:
                cursor.execute(command)
            except Exception as e:
                print(f"Error executing command: {command[:50]}...\n{e}")
                
    print("Schema and Seed data applied successfully.")
    conn.close()

if __name__ == "__main__":
    wait_for_db()
    execute_script("mock_wincar_db.sql")
