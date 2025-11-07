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

def extract_readable_text(data_blob):
    """Extract all readable text strings from binary data."""
    if not isinstance(data_blob, bytes):
        return []

    # Decode and extract strings of printable characters
    decoded = data_blob.decode('utf-8', errors='ignore')

    # Extract sequences of printable characters (minimum 3 chars)
    import re
    strings = re.findall(r'[\x20-\x7e]{3,}', decoded)

    return [s.strip() for s in strings if s.strip()]

def extract_data(db_path, verbose=False, extract_text=False):
    """Extract all data from the database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT key, data FROM object_data")
    rows = cursor.fetchall()
    conn.close()

    result = {}
    print(f"Found {len(rows)} entries in database\n")

    for i, (key_blob, data_blob) in enumerate(rows, 1):
        key = decode_key(key_blob)

        if extract_text:
            # Extract readable text from binary data
            text_strings = extract_readable_text(data_blob)
            if text_strings:
                print(f"Entry {i} (key: {key or 'unknown'}):")
                for text in text_strings:
                    print(f"  {text}")
                print()
                result[key or f"entry_{i}"] = {"text_extracted": text_strings}
            continue

        data = decode_data(data_blob)

        if verbose:
            print(f"Entry {i}:")
            if isinstance(key_blob, bytes):
                print(f"  Key (hex): {key_blob[:40].hex()}")
            else:
                print(f"  Key (raw): {key_blob}")
            print(f"  Key (decoded): {key}")

            if isinstance(data_blob, bytes):
                print(f"  Data (hex): {data_blob[:60].hex()}")
                decoded_preview = data_blob.decode('utf-8', errors='ignore')[:100]
                print(f"  Data (preview): {repr(decoded_preview)}")
            else:
                print(f"  Data (raw): {data_blob}")
            print(f"  JSON extracted: {data is not None}")
            print()

        if key and data is not None:
            result[key] = data
            if not verbose:
                print(f"✓ Extracted: {key}")
        elif key:
            if not verbose:
                print(f"✗ Could not decode data for: {key}")
        else:
            if not verbose:
                print(f"✗ Could not decode key")

    return result

def main():
    if len(sys.argv) < 2:
        print("Usage: ./extract_firefox_extension_data.py <database.sqlite> [output.json] [options]")
        print()
        print("Options:")
        print("  -v, --verbose        Show detailed hex/binary data for debugging")
        print("  --extract-text       Extract readable text from binary data (for non-JSON storage)")
        print()
        print("Examples:")
        print("  ./extract_firefox_extension_data.py path/to/extension.sqlite recovered.json")
        print("  ./extract_firefox_extension_data.py path/to/extension.sqlite --verbose")
        print("  ./extract_firefox_extension_data.py path/to/extension.sqlite --extract-text")
        sys.exit(1)

    # Parse arguments
    verbose = '--verbose' in sys.argv or '-v' in sys.argv
    extract_text = '--extract-text' in sys.argv
    args = [arg for arg in sys.argv[1:] if arg not in ['--verbose', '-v', '--extract-text']]

    db_path = args[0]
    output_path = args[1] if len(args) > 1 else None

    if extract_text:
        print(f"Extracting readable text from: {db_path}\n")
    else:
        print(f"Extracting data from: {db_path}\n")

    try:
        data = extract_data(db_path, verbose=verbose, extract_text=extract_text)

        if output_path:
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"\n✓✓✓ Saved to: {output_path}")
        else:
            if not verbose and not extract_text:
                print(f"\nRecovered data:")
                print(json.dumps(data, indent=2))
            elif extract_text and data:
                print(f"\n✓✓✓ Extracted text from {len(data)} entries")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
