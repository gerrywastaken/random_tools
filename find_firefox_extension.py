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
            # Handle different data types (BLOB, int, etc.)
            key_str = ''
            data_str = ''

            if isinstance(key_blob, bytes):
                key_str = key_blob.decode('utf-8', errors='ignore')
            elif key_blob is not None:
                key_str = str(key_blob)

            if isinstance(data_blob, bytes):
                data_str = data_blob.decode('utf-8', errors='ignore')
            elif data_blob is not None:
                data_str = str(data_blob)

            if search_term.lower() in key_str.lower() or search_term.lower() in data_str.lower():
                return True
        return False
    except Exception as e:
        print(f"Error reading {db_path}: {e}", file=sys.stderr)
        return False

def find_all_firefox_profiles():
    """Find all Firefox profile storage directories."""
    firefox_dir = os.path.expanduser("~/.mozilla/firefox")
    if not os.path.exists(firefox_dir):
        return []

    profiles = []
    for entry in os.listdir(firefox_dir):
        profile_dir = os.path.join(firefox_dir, entry)
        storage_dir = os.path.join(profile_dir, "storage", "default")
        if os.path.isdir(storage_dir):
            profiles.append(storage_dir)

    return profiles

def main():
    if len(sys.argv) < 2:
        print("Usage: ./find_firefox_extension.py <search_term> [storage_path]")
        print("Example: ./find_firefox_extension.py 'example.com' ~/.mozilla/firefox/xyz.default/storage/default")
        sys.exit(1)

    search_term = sys.argv[1]

    if len(sys.argv) > 2:
        search_path = sys.argv[2]
    else:
        # Find all available profiles
        profiles = find_all_firefox_profiles()
        if not profiles:
            print("Error: Could not find any Firefox profiles.", file=sys.stderr)
            print("Please specify storage path manually:", file=sys.stderr)
            print("Example: ./find_firefox_extension.py 'example.com' ~/.mozilla/firefox/xyz.default/storage/default", file=sys.stderr)
            sys.exit(1)
        elif len(profiles) == 1:
            search_path = profiles[0]
        else:
            print(f"Found {len(profiles)} Firefox profiles:", file=sys.stderr)
            for i, profile in enumerate(profiles, 1):
                print(f"  {i}. {profile}", file=sys.stderr)
            print("", file=sys.stderr)
            print("Please specify which profile to search:", file=sys.stderr)
            print(f"Example: ./find_firefox_extension.py '{search_term}' {profiles[0]}", file=sys.stderr)
            sys.exit(1)

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
