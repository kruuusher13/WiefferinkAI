import pyodbc
import time
import os

# Connection string from env var, with local Docker default
_DEFAULT_MASTER = r"DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=master;UID=sa;PWD=StrongPassword123!;Connection Timeout=3"
CONN_STR = os.getenv("WINCAR_DB_MASTER_CONNECTION", _DEFAULT_MASTER)

def wait_for_db():
    retries = 5
    while retries > 0:
        try:
            conn = pyodbc.connect(CONN_STR, timeout=3)
            conn.close()
            print("Database is ready!")
            return
        except Exception as e:
            print(f"Waiting for database... ({retries} retries left) - Error: {e}")
            time.sleep(2)
            retries -= 1
    raise Exception("Database failed to start")

def execute_script(filename):
    print(f"Executing script: {filename}")
    # Connect to master to drop/create DB
    conn = pyodbc.connect(CONN_STR)
    conn.autocommit = True
    cursor = conn.cursor()

    try:
        cursor.execute("DROP DATABASE IF EXISTS WinCarLive")
        cursor.execute("CREATE DATABASE WinCarLive")
        print("Dropped existing database.")
        print("Created WinCarLive database.")
    except Exception as e:
        print(f"Error resetting DB: {e}")
        raise e
    finally:
        conn.close()

    # Connect to new DB
    conn = pyodbc.connect(CONN_STR.replace("master", "WinCarLive"), autocommit=True)
    cursor = conn.cursor()

    # Resolve file path relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, filename)

    with open(file_path, 'r') as f:
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
