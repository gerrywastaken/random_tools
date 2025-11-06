#!/usr/bin/env python3
"""
Extract JSON data from Firefox extension IndexedDB storage.

Handles the BLOB encoding issue where IndexedDB stores data with metadata prefix bytes.

Usage: ./extract_firefox_extension_data.py <database.sqlite> [output.json]
"""

import sqlite3
import json
import sys

def decode_key(key_blob):
    """Decode key BLOB, trying different offsets to skip metadata bytes."""
    if not key_blob:
        return None

    # Handle non-BLOB types (int, etc.)
    if not isinstance(key_blob, bytes):
        return str(key_blob)

    # Try direct decode
    try:
        decoded = key_blob.decode('utf-8', errors='ignore').strip('\x00')
        if decoded and decoded.isprintable():
            return decoded
    except:
        pass

    # Try skipping metadata prefix bytes (usually first few bytes)
    for offset in range(min(20, len(key_blob))):
        try:
            test = key_blob[offset:].decode('utf-8', errors='ignore')
            cleaned = ''.join(c for c in test if c.isprintable())
            if cleaned and len(cleaned) >= 2:
                return cleaned
        except:
            continue

    return None

def decode_data(data_blob):
    """Decode data BLOB and extract JSON."""
    if not data_blob:
        return None

    # Handle non-BLOB types (int, etc.)
    if not isinstance(data_blob, bytes):
        # Try to parse as JSON if it's a string
        if isinstance(data_blob, str):
            try:
                return json.loads(data_blob)
            except:
                pass
        return None

    try:
        # Decode as UTF-8
        data_str = data_blob.decode('utf-8', errors='ignore')

        # Find JSON start marker ([ or {)
        json_start = -1
        for i, char in enumerate(data_str):
            if char == '[' or char == '{':
                json_start = i
                break

        if json_start >= 0:
            json_str = data_str[json_start:]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                return None

        return None
    except:
        return None

def extract_data(db_path):
    """Extract all data from the database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT key, data FROM object_data")
    rows = cursor.fetchall()
    conn.close()

    result = {}
    print(f"Found {len(rows)} entries in database\n")

    for key_blob, data_blob in rows:
        key = decode_key(key_blob)
        data = decode_data(data_blob)

        if key and data is not None:
            result[key] = data
            print(f"✓ Extracted: {key}")
        elif key:
            print(f"✗ Could not decode data for: {key}")
        else:
            print(f"✗ Could not decode key")

    return result

def main():
    if len(sys.argv) < 2:
        print("Usage: ./extract_firefox_extension_data.py <database.sqlite> [output.json]")
        print("Example: ./extract_firefox_extension_data.py path/to/extension.sqlite recovered.json")
        sys.exit(1)

    db_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"Extracting data from: {db_path}\n")

    try:
        data = extract_data(db_path)

        if output_path:
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"\n✓✓✓ Saved to: {output_path}")
        else:
            print(f"\nRecovered data:")
            print(json.dumps(data, indent=2))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
