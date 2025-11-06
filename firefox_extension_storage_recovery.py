#!/usr/bin/env python3
"""
Firefox Extension Storage Recovery Tool

Extracts chrome.storage.local data from Firefox extension's IndexedDB storage.
Useful for recovering data from temporary extensions that have been reloaded
with a new UUID, or for data migration and backup purposes.

Author: Claude Code
License: MIT
"""

import sqlite3
import json
import sys
import os
import argparse
import glob
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum


class OutputFormat(Enum):
    """Supported output formats"""
    JSON = "json"
    PRETTY = "pretty"
    SUMMARY = "summary"
    ALL = "all"


@dataclass
class ExtensionData:
    """Represents recovered data from an extension"""
    uuid: str
    database_name: str
    database_path: str
    entries: List[Dict[str, Any]]
    raw_entries: List[Tuple[bytes, bytes]]


class BlobDecoder:
    """Handles decoding of IndexedDB BLOB data"""

    @staticmethod
    def decode_key(key_blob: bytes) -> Optional[str]:
        """
        Decode a key BLOB to string.

        IndexedDB keys may have metadata prefix bytes. This method tries
        multiple strategies to extract the actual key string.

        Args:
            key_blob: Raw BLOB data from database

        Returns:
            Decoded key string or None if decoding fails
        """
        if not key_blob:
            return None

        # Strategy 1: Direct UTF-8 decode
        try:
            decoded = key_blob.decode('utf-8', errors='ignore').strip('\x00')
            if decoded and len(decoded) >= 2 and decoded.isprintable():
                return decoded
        except Exception:
            pass

        # Strategy 2: Try different offsets to skip metadata bytes
        # IndexedDB often uses prefix bytes for type information
        for offset in range(min(20, len(key_blob))):
            try:
                test = key_blob[offset:].decode('utf-8', errors='ignore')
                # Clean up null bytes and control characters
                cleaned = ''.join(c for c in test if c.isprintable())
                if cleaned and len(cleaned) >= 2:
                    return cleaned
            except Exception:
                continue

        # Strategy 3: Look for common key patterns in hex
        hex_str = key_blob.hex()
        # Common patterns might be identifiable here in future versions

        return None

    @staticmethod
    def decode_data(data_blob: bytes) -> Tuple[Optional[str], Optional[Any]]:
        """
        Decode a data BLOB and extract JSON if present.

        IndexedDB data may have metadata prefix before the actual JSON payload.
        This method attempts to locate and extract valid JSON from the BLOB.

        Args:
            data_blob: Raw BLOB data from database

        Returns:
            Tuple of (raw_string, parsed_json) or (raw_string, None) if no JSON found
        """
        if not data_blob:
            return None, None

        try:
            # Decode as UTF-8, allowing for some binary prefix
            data_str = data_blob.decode('utf-8', errors='ignore')

            # Look for JSON start markers ([ or {)
            json_start = -1
            for i, char in enumerate(data_str):
                if char == '[' or char == '{':
                    json_start = i
                    break

            if json_start >= 0:
                json_candidate = data_str[json_start:]

                # Try to parse as JSON
                try:
                    parsed = json.loads(json_candidate)
                    return json_candidate, parsed
                except json.JSONDecodeError:
                    # JSON parse failed, return raw string
                    return data_str, None

            return data_str, None

        except Exception:
            return None, None

    @staticmethod
    def identify_data_type(key: Optional[str], data: Any) -> Optional[str]:
        """
        Attempt to identify what type of data this is based on key name or content.

        Args:
            key: Decoded key string
            data: Parsed JSON data

        Returns:
            String describing the data type or None
        """
        if not data:
            return None

        # Check key name
        if key:
            key_lower = key.lower()
            for keyword in ['group', 'domain', 'setting', 'config', 'user', 'pref']:
                if keyword in key_lower:
                    return keyword

        # Check data structure for common patterns
        if isinstance(data, list) and data:
            first_item = data[0]
            if isinstance(first_item, dict):
                # Look for distinctive field names
                fields = set(first_item.keys())
                if 'phrases' in fields:
                    return 'groups'
                elif 'pattern' in fields:
                    return 'domains'
                elif 'id' in fields and 'name' in fields:
                    return 'items'

        return None


class FirefoxStorageRecovery:
    """Main class for recovering Firefox extension storage data"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.decoder = BlobDecoder()

    def log(self, message: str, level: str = "INFO"):
        """Print log message if verbose mode is enabled"""
        if self.verbose:
            print(f"[{level}] {message}", file=sys.stderr)

    def find_extension_databases(self, search_path: str) -> List[str]:
        """
        Find all Firefox extension database files.

        Args:
            search_path: Path to Firefox profile storage directory or specific .sqlite file

        Returns:
            List of absolute paths to .sqlite database files
        """
        search_path = os.path.expanduser(search_path)

        # If it's a direct path to a .sqlite file
        if search_path.endswith('.sqlite') and os.path.isfile(search_path):
            self.log(f"Using specific database: {search_path}")
            return [search_path]

        # If it's a directory, search for extension databases
        if os.path.isdir(search_path):
            pattern = os.path.join(search_path, "moz-extension+++*", "idb", "*.sqlite")
            databases = glob.glob(pattern)
            self.log(f"Found {len(databases)} extension databases in {search_path}")
            return sorted(databases)

        self.log(f"Invalid path: {search_path}", "ERROR")
        return []

    def extract_extension_uuid(self, db_path: str) -> str:
        """Extract extension UUID from database path"""
        parts = db_path.split(os.sep)
        for part in parts:
            if part.startswith('moz-extension+++'):
                return part.replace('moz-extension+++', '')
        return "unknown"

    def recover_data_from_database(self, db_path: str) -> ExtensionData:
        """
        Recover all data from a single extension database.

        Args:
            db_path: Path to .sqlite database file

        Returns:
            ExtensionData object containing recovered information
        """
        uuid = self.extract_extension_uuid(db_path)
        db_name = os.path.basename(db_path)

        self.log(f"Processing database: {db_path}")

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Get all data from object_data table
            cursor.execute("SELECT key, data FROM object_data")
            rows = cursor.fetchall()

            self.log(f"Found {len(rows)} rows in database")

            entries = []
            raw_entries = []

            for key_blob, data_blob in rows:
                raw_entries.append((key_blob, data_blob))

                # Decode key and data
                key_str = self.decoder.decode_key(key_blob)
                data_str, parsed_data = self.decoder.decode_data(data_blob)

                entry = {
                    'key': key_str,
                    'key_hex': key_blob[:20].hex() if len(key_blob) > 20 else key_blob.hex(),
                    'has_json': parsed_data is not None,
                    'data': parsed_data,
                    'data_preview': data_str[:200] if data_str else None,
                    'data_type': self.decoder.identify_data_type(key_str, parsed_data)
                }

                entries.append(entry)

            conn.close()

            return ExtensionData(
                uuid=uuid,
                database_name=db_name,
                database_path=db_path,
                entries=entries,
                raw_entries=raw_entries
            )

        except Exception as e:
            self.log(f"Error processing database {db_path}: {e}", "ERROR")
            return ExtensionData(
                uuid=uuid,
                database_name=db_name,
                database_path=db_path,
                entries=[],
                raw_entries=[]
            )

    def search_databases(self, databases: List[str], search_term: str) -> List[ExtensionData]:
        """
        Search multiple databases for a specific term.

        Args:
            databases: List of database paths to search
            search_term: Search term to look for in keys or data

        Returns:
            List of ExtensionData objects that contain the search term
        """
        results = []
        search_lower = search_term.lower()

        for db_path in databases:
            ext_data = self.recover_data_from_database(db_path)

            # Check if search term appears in any entry
            found = False
            for entry in ext_data.entries:
                key = entry.get('key', '') or ''
                data_preview = entry.get('data_preview', '') or ''

                if search_lower in key.lower() or search_lower in data_preview.lower():
                    found = True
                    break

            if found:
                results.append(ext_data)
                self.log(f"Search term '{search_term}' found in {db_path}")

        return results

    def format_output_summary(self, ext_data_list: List[ExtensionData]) -> str:
        """Generate summary output"""
        lines = []
        lines.append("=" * 80)
        lines.append("Firefox Extension Storage Recovery - Summary")
        lines.append("=" * 80)
        lines.append("")

        for ext_data in ext_data_list:
            lines.append(f"Extension UUID: {ext_data.uuid}")
            lines.append(f"Database: {ext_data.database_name}")
            lines.append(f"Path: {ext_data.database_path}")
            lines.append(f"Total entries: {len(ext_data.entries)}")
            lines.append("")

            # Group by data type
            by_type = {}
            for entry in ext_data.entries:
                dtype = entry.get('data_type') or 'unknown'
                if dtype not in by_type:
                    by_type[dtype] = []
                by_type[dtype].append(entry)

            lines.append("Entries by type:")
            for dtype, entries in sorted(by_type.items()):
                json_count = sum(1 for e in entries if e['has_json'])
                lines.append(f"  - {dtype}: {len(entries)} entries ({json_count} with valid JSON)")

            lines.append("")
            lines.append("Keys found:")
            for entry in ext_data.entries:
                key = entry.get('key', '(binary)')
                has_json = "✓" if entry['has_json'] else "✗"
                dtype = entry.get('data_type') or 'unknown'
                lines.append(f"  [{has_json}] {key} (type: {dtype})")

            lines.append("")
            lines.append("-" * 80)
            lines.append("")

        return "\n".join(lines)

    def format_output_pretty(self, ext_data_list: List[ExtensionData]) -> str:
        """Generate pretty-printed output with data preview"""
        lines = []

        for ext_data in ext_data_list:
            lines.append("=" * 80)
            lines.append(f"Extension UUID: {ext_data.uuid}")
            lines.append(f"Database: {ext_data.database_name}")
            lines.append("=" * 80)
            lines.append("")

            for i, entry in enumerate(ext_data.entries, 1):
                lines.append(f"Entry {i}:")
                lines.append(f"  Key: {entry.get('key', '(binary)')}")
                lines.append(f"  Key hex: {entry['key_hex']}")
                lines.append(f"  Has JSON: {entry['has_json']}")
                lines.append(f"  Data type: {entry.get('data_type', 'unknown')}")

                if entry['has_json']:
                    lines.append(f"  Data (JSON):")
                    json_str = json.dumps(entry['data'], indent=4)
                    for line in json_str.split('\n')[:20]:  # Limit preview
                        lines.append(f"    {line}")
                    if json_str.count('\n') > 20:
                        lines.append("    ... (truncated)")
                else:
                    lines.append(f"  Data preview: {entry['data_preview']}")

                lines.append("")

        return "\n".join(lines)

    def format_output_json(self, ext_data_list: List[ExtensionData]) -> Dict:
        """Generate JSON output"""
        result = {
            'extensions': []
        }

        for ext_data in ext_data_list:
            ext_info = {
                'uuid': ext_data.uuid,
                'database_name': ext_data.database_name,
                'database_path': ext_data.database_path,
                'entries': []
            }

            for entry in ext_data.entries:
                entry_info = {
                    'key': entry.get('key'),
                    'data_type': entry.get('data_type'),
                    'has_json': entry['has_json']
                }

                if entry['has_json']:
                    entry_info['data'] = entry['data']
                else:
                    entry_info['data_preview'] = entry['data_preview']

                ext_info['entries'].append(entry_info)

            result['extensions'].append(ext_info)

        return result

    def save_recovered_data(self, ext_data_list: List[ExtensionData], output_dir: str):
        """
        Save recovered data to separate files organized by data type.

        Args:
            ext_data_list: List of recovered extension data
            output_dir: Directory to save recovered files
        """
        os.makedirs(output_dir, exist_ok=True)

        for ext_data in ext_data_list:
            # Create subdirectory for each extension
            ext_dir = os.path.join(output_dir, f"extension_{ext_data.uuid}")
            os.makedirs(ext_dir, exist_ok=True)

            # Save by data type
            by_type = {}
            for entry in ext_data.entries:
                if entry['has_json']:
                    dtype = entry.get('data_type') or 'unknown'
                    key = entry.get('key', f'data_{len(by_type)}')

                    if dtype not in by_type:
                        by_type[dtype] = {}

                    by_type[dtype][key] = entry['data']

            # Write separate files for each type
            for dtype, data_dict in by_type.items():
                filepath = os.path.join(ext_dir, f"{dtype}.json")
                with open(filepath, 'w') as f:
                    json.dump(data_dict, f, indent=2)
                print(f"✓ Saved {dtype} data to: {filepath}")

            # Also save combined file
            combined_path = os.path.join(ext_dir, "all_data.json")
            with open(combined_path, 'w') as f:
                json.dump(by_type, f, indent=2)
            print(f"✓ Saved combined data to: {combined_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Recover chrome.storage.local data from Firefox extension IndexedDB storage',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan all extensions in a Firefox profile
  %(prog)s ~/.mozilla/firefox/abc123.default/storage/default

  # Recover data from a specific database
  %(prog)s path/to/moz-extension+++uuid/idb/database.sqlite

  # Search for extensions containing specific term
  %(prog)s ~/.mozilla/firefox/abc123.default/storage/default --search "example.com"

  # Export recovered data to files
  %(prog)s database.sqlite --output-dir ./recovered --format all

  # Get detailed information
  %(prog)s database.sqlite --format pretty --verbose
        """
    )

    parser.add_argument(
        'path',
        help='Path to Firefox profile storage directory or specific .sqlite file'
    )

    parser.add_argument(
        '--search', '-s',
        help='Search term to filter extensions (searches in keys and data)',
        default=None
    )

    parser.add_argument(
        '--format', '-f',
        choices=['json', 'pretty', 'summary', 'all'],
        default='summary',
        help='Output format (default: summary)'
    )

    parser.add_argument(
        '--output-dir', '-o',
        help='Directory to save recovered data files (organized by data type)',
        default=None
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Initialize recovery tool
    recovery = FirefoxStorageRecovery(verbose=args.verbose)

    # Find databases
    databases = recovery.find_extension_databases(args.path)

    if not databases:
        print("Error: No extension databases found", file=sys.stderr)
        sys.exit(1)

    # Recover data
    if args.search:
        ext_data_list = recovery.search_databases(databases, args.search)
        if not ext_data_list:
            print(f"No extensions found containing search term: {args.search}", file=sys.stderr)
            sys.exit(1)
    else:
        ext_data_list = [recovery.recover_data_from_database(db) for db in databases]

    # Output results
    if args.format == 'summary' or args.format == 'all':
        print(recovery.format_output_summary(ext_data_list))

    if args.format == 'pretty' or args.format == 'all':
        print(recovery.format_output_pretty(ext_data_list))

    if args.format == 'json' or args.format == 'all':
        json_output = recovery.format_output_json(ext_data_list)
        print(json.dumps(json_output, indent=2))

    # Save files if output directory specified
    if args.output_dir:
        recovery.save_recovered_data(ext_data_list, args.output_dir)
        print(f"\n✓✓✓ Data recovery complete! Files saved to: {args.output_dir}")


if __name__ == '__main__':
    main()
