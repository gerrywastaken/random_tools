#!/usr/bin/env python3
"""
Find Firefox extension databases containing a keyword.

Usage: ./find_firefox_extension.py <search_term> [storage_path]
"""

import sqlite3
import sys
import glob
import os

def find_extension_databases(search_path):
    """Find all Firefox extension database files."""
    pattern = os.path.join(search_path, "moz-extension+++*", "idb", "*.sqlite")
    return glob.glob(pattern)

def search_database(db_path, search_term):
    """Check if database contains the search term."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT key, data FROM object_data")
        rows = cursor.fetchall()
        conn.close()

        for key_blob, data_blob in rows:
            # Decode and search in both key and data
            key_str = key_blob.decode('utf-8', errors='ignore')
            data_str = data_blob.decode('utf-8', errors='ignore')

            if search_term.lower() in key_str.lower() or search_term.lower() in data_str.lower():
                return True
        return False
    except Exception as e:
        print(f"Error reading {db_path}: {e}", file=sys.stderr)
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: ./find_firefox_extension.py <search_term> [storage_path]")
        print("Example: ./find_firefox_extension.py 'example.com' ~/.mozilla/firefox/*.default/storage/default")
        sys.exit(1)

    search_term = sys.argv[1]
    search_path = sys.argv[2] if len(sys.argv) > 2 else os.path.expanduser("~/.mozilla/firefox/*.default/storage/default")

    # Handle glob in path
    import glob as glob_module
    paths = glob_module.glob(search_path)
    if not paths:
        print(f"No paths found matching: {search_path}", file=sys.stderr)
        sys.exit(1)

    search_path = paths[0]

    print(f"Searching for '{search_term}' in {search_path}")
    print()

    databases = find_extension_databases(search_path)

    if not databases:
        print("No extension databases found")
        sys.exit(1)

    matches = []
    for db_path in databases:
        if search_database(db_path, search_term):
            matches.append(db_path)

    if matches:
        print(f"Found {len(matches)} extension(s) containing '{search_term}':")
        print()
        for db_path in matches:
            print(f"  {db_path}")
    else:
        print(f"No extensions found containing '{search_term}'")
        sys.exit(1)

if __name__ == '__main__':
    main()
