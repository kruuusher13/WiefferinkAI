import pyodbc
import pandas as pd

# Connection Settings
SERVER = 'localhost'
DATABASE = 'WinCarLive'
USERNAME = 'sa'
PASSWORD = 'StrongPassword123!'
DRIVER = '{ODBC Driver 17 for SQL Server}'

CONN_STR = f'DRIVER={DRIVER};SERVER={SERVER};DATABASE={DATABASE};UID={USERNAME};PWD={PASSWORD}'

def view_table(table_name):
    try:
        conn = pyodbc.connect(CONN_STR)
        query = f"SELECT * FROM {table_name}"
        df = pd.read_sql(query, conn)
        
        print(f"\n======== 📂 TABLE: {table_name} ========")
        if df.empty:
            print("(Empty Table)")
        else:
            print(df.to_markdown(index=False))
        conn.close()
    except Exception as e:
        print(f"Error reading {table_name}: {e}")

def main():
    print("👀 GarageAI Database Viewer")
    print("----------------------------")
    
    view_table("Communicatie_Relaties")
    view_table("Werkplaats_Werkorders")
    view_table("Magazijn_Artikelen")

if __name__ == "__main__":
    main()
