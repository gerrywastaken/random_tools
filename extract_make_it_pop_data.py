#!/usr/bin/env python3
"""
Extract make-it-pop extension data from IndexedDB storage.

Only extracts data matching the make-it-pop structure:
- groups: {id, name, lightBgColor, lightTextColor, darkBgColor, darkTextColor, phrases[]}
- domains: {id, pattern, mode, groupIds[]}

Skips all non-conforming entries.

Usage: ./extract_make_it_pop_data.py <database.sqlite> [output.json]
"""

import sqlite3
import json
import sys
import re

def extract_field_value(decoded, field_name, next_field_pos=None):
    """Extract value after a field name in the decoded binary data."""
    pos = decoded.find(field_name)
    if pos == -1:
        return None

    # Make sure it's a standalone field name
    before_ok = pos == 0 or not decoded[pos-1].isalnum()
    after_ok = pos + len(field_name) >= len(decoded) or not decoded[pos + len(field_name)].isalnum()
    if not (before_ok and after_ok):
        return None

    # Start after the field name
    value_start = pos + len(field_name)

    # End at next field or specified position
    if next_field_pos is not None:
        value_end = next_field_pos
    else:
        value_end = len(decoded)

    value_region = decoded[value_start:value_end]

    # Extract printable characters
    printable = []
    for c in value_region:
        if c.isprintable() and ord(c) >= 32:
            printable.append(c)

    return ''.join(printable).strip()

def parse_make_it_pop_entry(data_blob):
    """
    Parse a single entry, checking if it matches Group or Domain structure.
    Returns ('group', data), ('domain', data), or (None, None) if not a match.
    """
    if not isinstance(data_blob, bytes):
        return None, None

    decoded = data_blob.decode('utf-8', errors='ignore')

    # Check for Group fields
    group_indicators = ['lightBgColor', 'darkBgColor', 'phrases']
    has_group_fields = sum(1 for field in group_indicators if field in decoded) >= 2

    # Check for Domain fields
    domain_indicators = ['pattern', 'groupIds']
    has_domain_fields = sum(1 for field in domain_indicators if field in domain_indicators) >= 1

    if has_group_fields:
        # Parse as Group
        group = {}

        # Find all field positions
        fields = ['id', 'name', 'lightBgColor', 'lightTextColor', 'darkBgColor',
                  'darkTextColor', 'phrases']
        field_positions = {}

        for field in fields:
            pos = decoded.find(field)
            if pos != -1:
                # Verify it's a standalone field
                before_ok = pos == 0 or not decoded[pos-1].isalnum()
                after_ok = pos + len(field) >= len(decoded) or not decoded[pos + len(field)].isalnum()
                if before_ok and after_ok:
                    field_positions[field] = pos

        # Sort by position
        sorted_fields = sorted(field_positions.items(), key=lambda x: x[1])

        # Extract values
        for i, (field, pos) in enumerate(sorted_fields):
            value_start = pos + len(field)

            # End at next field
            if i + 1 < len(sorted_fields):
                value_end = sorted_fields[i + 1][1]
            else:
                value_end = len(decoded)

            value_region = decoded[value_start:value_end]

            # Extract printable text
            value_text = ''.join(c for c in value_region if c.isprintable() and ord(c) >= 32)
            value_text = value_text.strip()

            # Clean up - remove other field names that might have leaked in
            for other_field in fields:
                if value_text.endswith(other_field):
                    value_text = value_text[:-len(other_field)].strip()

            if value_text:
                # Special handling for specific fields
                if 'Color' in field:
                    # Extract hex color
                    hex_match = re.search(r'#[0-9A-Fa-f]{6,8}', value_text)
                    if hex_match:
                        group[field] = hex_match.group(0)
                elif field == 'phrases':
                    # This is tricky - just store what we can extract
                    group[field] = value_text[:200]
                else:
                    group[field] = value_text[:200]

        # Only return if we got at least id and name
        if 'id' in group or 'name' in group:
            return 'group', group

    elif has_domain_fields:
        # Parse as Domain
        domain = {}

        fields = ['id', 'pattern', 'mode', 'groupIds']
        field_positions = {}

        for field in fields:
            pos = decoded.find(field)
            if pos != -1:
                before_ok = pos == 0 or not decoded[pos-1].isalnum()
                after_ok = pos + len(field) >= len(decoded) or not decoded[pos + len(field)].isalnum()
                if before_ok and after_ok:
                    field_positions[field] = pos

        sorted_fields = sorted(field_positions.items(), key=lambda x: x[1])

        for i, (field, pos) in enumerate(sorted_fields):
            value_start = pos + len(field)

            if i + 1 < len(sorted_fields):
                value_end = sorted_fields[i + 1][1]
            else:
                value_end = len(decoded)

            value_region = decoded[value_start:value_end]
            value_text = ''.join(c for c in value_region if c.isprintable() and ord(c) >= 32)
            value_text = value_text.strip()

            # Clean up
            for other_field in fields:
                if value_text.endswith(other_field):
                    value_text = value_text[:-len(other_field)].strip()

            if value_text:
                if field == 'mode':
                    # Should be 'light' or 'dark'
                    if 'light' in value_text.lower():
                        domain[field] = 'light'
                    elif 'dark' in value_text.lower():
                        domain[field] = 'dark'
                else:
                    domain[field] = value_text[:200]

        if 'pattern' in domain:
            return 'domain', domain

    return None, None

def extract_make_it_pop_data(db_path):
    """Extract make-it-pop groups and domains from database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT key, data FROM object_data")
    rows = cursor.fetchall()
    conn.close()

    groups = []
    domains = []

    print(f"Scanning {len(rows)} entries...\n")

    for i, (key_blob, data_blob) in enumerate(rows, 1):
        entry_type, data = parse_make_it_pop_entry(data_blob)

        if entry_type == 'group':
            groups.append(data)
            name = data.get('name', 'unnamed')[:40]
            print(f"✓ Entry {i}: Group - {name}")
        elif entry_type == 'domain':
            domains.append(data)
            pattern = data.get('pattern', 'no pattern')[:40]
            print(f"✓ Entry {i}: Domain - {pattern}")
        # Silently skip non-matching entries

    return {
        "groups": groups,
        "domains": domains
    }

def main():
    if len(sys.argv) < 2:
        print("Usage: ./extract_make_it_pop_data.py <database.sqlite> [output.json]")
        print("Example: ./extract_make_it_pop_data.py path/to/extension.sqlite recovered.json")
        sys.exit(1)

    db_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"Extracting make-it-pop data from: {db_path}\n")

    try:
        result = extract_make_it_pop_data(db_path)

        print(f"\n{'='*60}")
        print(f"Summary:")
        print(f"  Groups found: {len(result['groups'])}")
        print(f"  Domains found: {len(result['domains'])}")

        if output_path:
            with open(output_path, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"\n✓✓✓ Saved to: {output_path}")
        else:
            print(f"\n{'='*60}")
            print("Recovered data:")
            print(json.dumps(result, indent=2))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
