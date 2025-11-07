#!/usr/bin/env python3
"""
Scan multiple Firefox SQLite databases to find IndexedDB databases with data.

Usage: ./scan_firefox_databases.py <path_pattern>

Examples:
  ./scan_firefox_databases.py ~/.mozilla/firefox/*/storage/default/**/*.sqlite
  ./scan_firefox_databases.py /path/to/firefox/storage/default/*/*.sqlite
"""

import sqlite3
import sys
import glob
import os

def is_indexeddb_database(db_path):
    """Check if a database is an IndexedDB database with data."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if it has object_data table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='object_data'")
        if not cursor.fetchone():
            conn.close()
            return False, 0

        # Count how many entries it has
        cursor.execute("SELECT COUNT(*) FROM object_data")
        count = cursor.fetchone()[0]

        conn.close()
        return True, count
    except Exception as e:
        return False, 0

def scan_databases(paths):
    """Scan multiple database files."""
    indexeddb_found = []
    other_dbs = []
    errors = []

    for path in paths:
        if not os.path.exists(path):
            continue

        if not os.path.isfile(path):
            continue

        try:
            is_idb, count = is_indexeddb_database(path)
            if is_idb:
                indexeddb_found.append((path, count))
            else:
                other_dbs.append(path)
        except Exception as e:
            errors.append((path, str(e)))

    return indexeddb_found, other_dbs, errors

def main():
    if len(sys.argv) < 2:
        print("Usage: ./scan_firefox_databases.py <path_pattern>")
        print()
        print("Examples:")
        print("  ./scan_firefox_databases.py ~/.mozilla/firefox/*/storage/default/**/*.sqlite")
        print("  ./scan_firefox_databases.py '/path/to/firefox/storage/default/*/*.sqlite'")
        print()
        print("Note: Wrap patterns in quotes to prevent premature shell expansion")
        sys.exit(1)

    # Expand glob patterns
    all_paths = []
    for pattern in sys.argv[1:]:
        expanded = glob.glob(pattern, recursive=True)
        all_paths.extend(expanded)

    if not all_paths:
        print(f"No files found matching pattern(s)")
        sys.exit(1)

    print(f"Scanning {len(all_paths)} database files...\n")

    indexeddb_found, other_dbs, errors = scan_databases(all_paths)

    # Report results
    print("=" * 70)
    print(f"INDEXEDDB DATABASES FOUND: {len(indexeddb_found)}")
    print("=" * 70)

    if indexeddb_found:
        for path, count in sorted(indexeddb_found, key=lambda x: x[1], reverse=True):
            print(f"✓ {count:4d} entries: {path}")
    else:
        print("(none)")

    print()
    print("=" * 70)
    print(f"OTHER SQLITE DATABASES: {len(other_dbs)}")
    print("=" * 70)

    if other_dbs:
        # Just show count, not all paths
        print(f"Found {len(other_dbs)} non-IndexedDB SQLite files")
        print("(Use --show-all to list them)")

        if '--show-all' in sys.argv:
            for path in sorted(other_dbs):
                print(f"  {path}")
    else:
        print("(none)")

    if errors:
        print()
        print("=" * 70)
        print(f"ERRORS: {len(errors)}")
        print("=" * 70)
        for path, error in errors:
            print(f"✗ {path}")
            print(f"  Error: {error}")

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total files scanned: {len(all_paths)}")
    print(f"IndexedDB databases: {len(indexeddb_found)}")
    print(f"Other databases: {len(other_dbs)}")
    print(f"Errors: {len(errors)}")

    if indexeddb_found:
        print()
        print("To extract data from an IndexedDB database, run:")
        print("  ./extract_firefox_extension_data.py <database.sqlite>")

if __name__ == '__main__':
    main()
