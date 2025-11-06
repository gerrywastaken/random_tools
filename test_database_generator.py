#!/usr/bin/env python3
"""
Test Database Generator for Firefox Extension Storage Recovery Tool

Creates a mock Firefox extension IndexedDB database with sample data
for testing the recovery tool.

Usage:
    python3 test_database_generator.py [output_path]
"""

import sqlite3
import json
import sys
import os


def create_test_database(db_path: str):
    """
    Create a test IndexedDB database that mimics Firefox extension storage.

    The database will contain sample data with different types (groups, domains, settings)
    encoded as BLOBs similar to how Firefox stores them.
    """

    # Sample data that might be stored by an extension
    test_data = {
        'groups': [
            {
                'id': 'group1',
                'name': 'Important Sites',
                'phrases': ['example.com', 'test.org'],
                'enabled': True
            },
            {
                'id': 'group2',
                'name': 'Social Media',
                'phrases': ['facebook.com', 'twitter.com', 'reddit.com'],
                'enabled': False
            }
        ],
        'domains': [
            {
                'pattern': '*.example.com',
                'action': 'block',
                'priority': 1
            },
            {
                'pattern': 'trusted.org',
                'action': 'allow',
                'priority': 10
            }
        ],
        'settings': {
            'theme': 'dark',
            'notifications': True,
            'autoSave': False,
            'version': '1.2.3'
        }
    }

    # Create directory if needed
    os.makedirs(os.path.dirname(db_path) or '.', exist_ok=True)

    # Create database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create table (simplified IndexedDB schema)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS object_data (
            object_store_id INTEGER,
            key BLOB,
            data BLOB
        )
    ''')

    # Function to encode data like IndexedDB does
    def encode_key(key_str: str) -> bytes:
        """Encode key with some metadata bytes (simulating IndexedDB encoding)"""
        # Add some prefix bytes to simulate IndexedDB metadata
        # Real IndexedDB uses various prefixes for type information
        prefix = b'\x00\x01'  # Simple prefix
        return prefix + key_str.encode('utf-8')

    def encode_data(data: any) -> bytes:
        """Encode data with metadata prefix (simulating IndexedDB encoding)"""
        json_str = json.dumps(data)
        # Add metadata prefix (in real IndexedDB this is more complex)
        prefix = b'\x00\x00\x01\x00'  # Simple prefix
        return prefix + json_str.encode('utf-8')

    # Insert test data
    for key, value in test_data.items():
        key_blob = encode_key(key)
        data_blob = encode_data(value)
        cursor.execute(
            'INSERT INTO object_data (object_store_id, key, data) VALUES (?, ?, ?)',
            (1, key_blob, data_blob)
        )

    # Add an additional entry with a different encoding style
    # This tests the tool's ability to handle variations
    alt_key = b'\x00\x02\x03userPreferences'  # Different prefix
    alt_data = b'\x00\x01\x02\x00{"darkMode": true, "fontSize": 14}'
    cursor.execute(
        'INSERT INTO object_data (object_store_id, key, data) VALUES (?, ?, ?)',
        (1, alt_key, alt_data)
    )

    conn.commit()
    conn.close()

    print(f"✓ Test database created: {db_path}")
    print(f"  - {len(test_data)} primary entries")
    print(f"  - Sample keys: {', '.join(test_data.keys())}")
    print(f"\nTest the recovery tool with:")
    print(f"  python3 firefox_extension_storage_recovery.py {db_path}")
    print(f"  python3 firefox_extension_storage_recovery.py {db_path} --format pretty")
    print(f"  python3 firefox_extension_storage_recovery.py {db_path} --output-dir ./test_recovery")


def create_realistic_directory_structure(base_path: str):
    """
    Create a realistic Firefox profile storage directory structure
    with multiple extension databases for testing.
    """

    # Create multiple extension directories
    extensions = [
        {
            'uuid': 'abc123-test-extension-uuid-1',
            'db_name': '1234567890atuhtgoi_lhhig.sqlite',
            'data': {
                'domains': ['example.com', 'test.org'],
                'enabled': True
            }
        },
        {
            'uuid': 'xyz789-test-extension-uuid-2',
            'db_name': '0987654321btuhtgoi_lhhig.sqlite',
            'data': {
                'bookmarks': [
                    {'title': 'Test', 'url': 'https://test.com'},
                    {'title': 'Example', 'url': 'https://example.com'}
                ]
            }
        }
    ]

    for ext in extensions:
        ext_dir = os.path.join(base_path, f"moz-extension+++{ext['uuid']}", "idb")
        db_path = os.path.join(ext_dir, ext['db_name'])

        os.makedirs(ext_dir, exist_ok=True)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS object_data (
                object_store_id INTEGER,
                key BLOB,
                data BLOB
            )
        ''')

        for key, value in ext['data'].items():
            key_blob = b'\x00\x01' + key.encode('utf-8')
            data_blob = b'\x00\x00\x01\x00' + json.dumps(value).encode('utf-8')
            cursor.execute(
                'INSERT INTO object_data (object_store_id, key, data) VALUES (?, ?, ?)',
                (1, key_blob, data_blob)
            )

        conn.commit()
        conn.close()

        print(f"✓ Created extension database: {db_path}")

    print(f"\n✓✓✓ Created realistic directory structure in: {base_path}")
    print(f"\nTest with:")
    print(f"  python3 firefox_extension_storage_recovery.py {base_path}")
    print(f"  python3 firefox_extension_storage_recovery.py {base_path} --search 'example.com'")


def main():
    if len(sys.argv) > 1:
        output_path = sys.argv[1]
    else:
        output_path = './test_extension_storage.sqlite'

    print("Firefox Extension Storage Recovery Tool - Test Database Generator")
    print("=" * 70)
    print()

    if output_path.endswith('.sqlite'):
        # Single database
        create_test_database(output_path)
    else:
        # Full directory structure
        create_realistic_directory_structure(output_path)


if __name__ == '__main__':
    main()
