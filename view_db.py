import sqlite3
import pandas as pd

def view_database(db_path="cleaned_data.db"):
    try:
        conn = sqlite3.connect(db_path)
        
        print(f"\n{'='*50}")
        print("SALES TABLE")
        print(f"{'='*50}")
        sales_df = pd.read_sql("SELECT * FROM sales LIMIT 5", conn)
        print(sales_df.to_string(index=False))
        
        print(f"\n{'='*50}")
        print("SERVER_LOGS TABLE")
        print(f"{'='*50}")
        logs_df = pd.read_sql("SELECT * FROM server_logs LIMIT 5", conn)
        print(logs_df.to_string(index=False))
        
        conn.close()
    except Exception as e:
        print(f"Error reading database: {e}")

if __name__ == "__main__":
    view_database()
