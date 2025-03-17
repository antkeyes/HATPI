#!/usr/bin/env python3

import sqlite3
import json
import os

JSON_FILE = "/nfs/hatops/ar0/hatpi-website/keyboard_flags.json"
DB_PATH = "/nfs/hatops/ar0/hatpi-website/data/image_flags.db"

def main():
    if not os.path.exists(JSON_FILE):
        print(f"JSON file not found at {JSON_FILE}. Exiting.")
        return
    
    # read the json file
    with open(JSON_FILE, 'r') as f:
        data = json.load(f)
        
    # open db connection
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Example: if your DB column is actually 'file_path', use that below
    # If you kept it as 'file_name', then keep "file_name" here instead
    column_name = "file_path"  # or "file_name" if you didn't rename

    # upsert to DB
    for file_path, info in data.items():
        flags_list = info.get("flags", [])
        flags_str = json.dumps(flags_list)  # store as JSON text
        timestamp = info.get("timestamp", "")
        author = info.get("author", "")
        
        # "INSERT OR REPLACE" means if the key already exists, it updates the row.
        sql = f"""
            INSERT OR REPLACE INTO image_flags ({column_name}, flags, timestamp, author)
            VALUES (?, ?, ?, ?)
        """
        cursor.execute(sql, (file_path, flags_str, timestamp, author))
        
    conn.commit()
    conn.close()
    print("sync complete")
    
if __name__ == "__main__":
    main()
