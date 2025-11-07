#!/usr/bin/env python3
"""
Simple parser for IndexedDB structured clone format.

Attempts to extract field-value pairs from Firefox's binary serialization.
This is a heuristic parser - it won't be perfect but should extract most data.

Usage: ./parse_indexeddb_structured.py <database.sqlite> [output.json]
"""

import sqlite3
import json
import sys
import re

def parse_structured_data(data_blob):
    """
    Heuristic parser for IndexedDB structured clone format.
    Looks for common patterns: field names followed by values.
    """
    if not isinstance(data_blob, bytes):
        return None

    result = {}
    decoded = data_blob.decode('utf-8', errors='ignore')

    # Strategy 1: Look for field names with known patterns
    # Common field names: id, name, data, value, etc.
    known_fields = ['id', 'name', 'data', 'value', 'type', 'enabled', 'disabled',
                    'url', 'pattern', 'regex', 'rule', 'rules', 'config', 'settings',
                    'options', 'preferences', 'groups', 'items', 'list', 'array',
                    'timestamp', 'date', 'created', 'updated', 'modified', 'title',
                    'description', 'category', 'tags', 'status']

    # Find each known field in the decoded data
    field_positions = []
    for field in known_fields:
        pos = decoded.find(field)
        while pos != -1:
            # Check if this looks like a field name (surrounded by non-alphanumeric)
            before_ok = pos == 0 or not decoded[pos-1].isalnum()
            after_ok = pos + len(field) >= len(decoded) or not decoded[pos + len(field)].isalnum()
            if before_ok and after_ok:
                field_positions.append((pos, field))
            pos = decoded.find(field, pos + 1)

    # Sort by position
    field_positions.sort()

    # Extract value after each field
    for i, (pos, field) in enumerate(field_positions):
        start = pos + len(field)
        # Find end (next field or end of string)
        if i + 1 < len(field_positions):
            end = field_positions[i + 1][0]
        else:
            end = len(decoded)

        # Extract value region
        value_region = decoded[start:end]

        # Skip control chars and extract printable content
        printable = []
        for c in value_region:
            if c.isprintable() and c not in '\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f':
                printable.append(c)
            elif printable and c == ' ':
                printable.append(c)

        value_text = ''.join(printable).strip()

        if value_text and len(value_text) > 0:
            # Skip if it's just another field name
            if value_text.lower() not in known_fields:
                result[field] = value_text[:500]  # Limit value length

    return result if result else None

def extract_all_data(db_path):
    """Extract structured data from all entries."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT key, data FROM object_data")
    rows = cursor.fetchall()
    conn.close()

    results = []
    print(f"Found {len(rows)} entries in database\n")

    for i, (key_blob, data_blob) in enumerate(rows, 1):
        # Decode key
        if isinstance(key_blob, bytes):
            key = key_blob.decode('utf-8', errors='ignore').strip('\x00')
            # Clean up key
            key = ''.join(c for c in key if c.isprintable()).strip()
        else:
            key = str(key_blob) if key_blob else f"entry_{i}"

        # Parse structured data
        parsed = parse_structured_data(data_blob)

        if parsed:
            entry = {"_key": key, **parsed}
            results.append(entry)
            print(f"✓ Entry {i} (key: {key})")
            for field, value in parsed.items():
                value_preview = str(value)[:80]
                print(f"    {field}: {value_preview}")
        else:
            print(f"✗ Entry {i} (key: {key}) - could not parse")

    return results

def main():
    if len(sys.argv) < 2:
        print("Usage: ./parse_indexeddb_structured.py <database.sqlite> [output.json]")
        print("Example: ./parse_indexeddb_structured.py path/to/extension.sqlite recovered.json")
        sys.exit(1)

    db_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"Parsing IndexedDB structured data from: {db_path}\n")

    try:
        results = extract_all_data(db_path)

        if output_path:
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\n✓✓✓ Saved {len(results)} entries to: {output_path}")
        else:
            print(f"\n{'='*60}")
            print(f"Recovered {len(results)} entries:")
            print(json.dumps(results, indent=2))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
