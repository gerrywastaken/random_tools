# Firefox Extension Storage Recovery Tool

A Python utility for recovering `chrome.storage.local` data from Firefox extension's IndexedDB storage. This tool is particularly useful for developers working with temporary extensions that lose data when reloaded.

## Table of Contents

- [Problem Statement](#problem-statement)
- [How It Works](#how-it-works)
- [Installation](#installation)
- [Usage](#usage)
- [Examples](#examples)
- [Technical Details](#technical-details)
- [Use Cases](#use-cases)
- [Limitations](#limitations)
- [Contributing](#contributing)
- [License](#license)

## Problem Statement

When developing Firefox extensions using temporary loading (via `about:debugging`), Firefox assigns a new internal UUID each time the extension is reloaded. This causes the extension to lose access to its previous `chrome.storage.local` data, which is stored in IndexedDB.

**The problem:**
- Extension uses `chrome.storage.local.set()` to save data
- Developer reloads the extension from `about:debugging`
- Extension gets a new UUID
- Old data is "orphaned" under the previous UUID
- Extension appears to have lost all stored data

**The reality:**
- The data still exists on disk
- It's just inaccessible under the old UUID
- This tool recovers that orphaned data

## How It Works

Firefox stores extension data in SQLite databases at:
```
<firefox-profile>/storage/default/moz-extension+++<uuid>/idb/*.sqlite
```

The tool:
1. Scans for extension database files
2. Extracts data from the `object_data` table
3. Decodes binary BLOBs (which contain IndexedDB metadata + your JSON)
4. Identifies and extracts valid JSON data
5. Organizes recovered data by type
6. Exports to readable JSON files

## Installation

### Requirements
- Python 3.6+
- No external dependencies (uses only standard library)

### Setup

```bash
# Clone or download the script
wget https://raw.githubusercontent.com/your-repo/firefox_extension_storage_recovery.py

# Make it executable
chmod +x firefox_extension_storage_recovery.py

# Optional: Install system-wide
sudo cp firefox_extension_storage_recovery.py /usr/local/bin/firefox-storage-recovery
```

## Usage

### Basic Syntax

```bash
python3 firefox_extension_storage_recovery.py [OPTIONS] <path>
```

### Options

| Option | Description |
|--------|-------------|
| `path` | Path to Firefox profile storage directory or specific .sqlite file |
| `--search TERM`, `-s TERM` | Filter extensions by search term (searches keys and data) |
| `--format FORMAT`, `-f FORMAT` | Output format: `summary`, `pretty`, `json`, or `all` (default: summary) |
| `--output-dir DIR`, `-o DIR` | Directory to save recovered JSON files |
| `--verbose`, `-v` | Enable verbose logging |
| `--help`, `-h` | Show help message |

## Examples

### Example 1: Scan All Extensions in Profile

```bash
python3 firefox_extension_storage_recovery.py \
  ~/.mozilla/firefox/abc123.default/storage/default
```

Output:
```
================================================================================
Firefox Extension Storage Recovery - Summary
================================================================================

Extension UUID: 0bf3b9e0-1736-41bb-a599-67139424b155
Database: 1145992490atuhtgoi_lhhig.sqlite
Path: /home/user/.mozilla/firefox/abc123.default/storage/default/moz-extension+++0bf3b9e0.../idb/1145992490atuhtgoi_lhhig.sqlite
Total entries: 3

Entries by type:
  - groups: 1 entries (1 with valid JSON)
  - domains: 1 entries (1 with valid JSON)
  - settings: 1 entries (1 with valid JSON)

Keys found:
  [✓] groups (type: groups)
  [✓] domains (type: domains)
  [✓] userSettings (type: settings)
```

### Example 2: Search for Specific Extension

```bash
python3 firefox_extension_storage_recovery.py \
  ~/.mozilla/firefox/abc123.default/storage/default \
  --search "example.com"
```

This will only show databases that contain "example.com" in their keys or data.

### Example 3: Export Data to Files

```bash
python3 firefox_extension_storage_recovery.py \
  path/to/database.sqlite \
  --output-dir ./recovered_data \
  --format all
```

This creates:
```
recovered_data/
└── extension_<uuid>/
    ├── groups.json       # All "groups" type data
    ├── domains.json      # All "domains" type data
    ├── settings.json     # All "settings" type data
    └── all_data.json     # Combined data
```

### Example 4: Pretty-Print with Details

```bash
python3 firefox_extension_storage_recovery.py \
  database.sqlite \
  --format pretty \
  --verbose
```

Output includes:
- Full decoded keys and values
- JSON data preview
- Data type identification
- Hex representation of binary keys

### Example 5: Export as JSON for Processing

```bash
python3 firefox_extension_storage_recovery.py \
  database.sqlite \
  --format json > recovered.json
```

Then process with `jq` or other tools:
```bash
jq '.extensions[0].entries[] | select(.has_json) | .data' recovered.json
```

## Technical Details

### Database Schema

Firefox uses SQLite for IndexedDB storage with this schema:

```sql
CREATE TABLE object_data (
    object_store_id INTEGER,
    key BLOB,
    data BLOB,
    ...
);
```

### BLOB Encoding

IndexedDB stores data as binary BLOBs with metadata:

```
[metadata bytes][actual data][null padding]
```

The tool handles this by:
1. **Key Decoding**: Tries direct UTF-8 decode, then iteratively strips prefix bytes
2. **Data Decoding**: Searches for JSON markers (`{` or `[`) after UTF-8 decode
3. **JSON Extraction**: Validates and parses JSON from the located offset
4. **Type Detection**: Identifies data types by key names or content structure

### Data Type Detection

The tool attempts to identify data types using:
- **Key-based**: Looks for keywords like "group", "domain", "settings" in key names
- **Structure-based**: Examines JSON structure for distinctive fields
  - Lists with `phrases` field → "groups"
  - Lists with `pattern` field → "domains"
  - Objects with `id` and `name` → "items"

## Use Cases

### 1. Development Recovery

You're developing an extension and accidentally reload it:

```bash
# Find your old data
python3 firefox_extension_storage_recovery.py \
  ~/.mozilla/firefox/*.default/storage/default \
  --search "myextension" \
  --output-dir ./backup

# Now manually import backup/extension_*/all_data.json in your extension
```

### 2. Data Migration

Moving from temporary to permanent extension:

```bash
# Extract data from temporary extension
python3 firefox_extension_storage_recovery.py \
  <profile>/storage/default \
  --output-dir ./migration_data

# Import the recovered JSON in your new extension code
```

### 3. Debugging

Understanding what's stored:

```bash
# Get detailed view
python3 firefox_extension_storage_recovery.py \
  database.sqlite \
  --format pretty
```

### 4. Backup

Regular backups of extension data:

```bash
# Cron job for daily backups
0 2 * * * python3 /usr/local/bin/firefox-storage-recovery \
  ~/.mozilla/firefox/*.default/storage/default \
  --output-dir ~/backups/firefox-extensions/$(date +\%Y\%m\%d)
```

### 5. Forensics

Recovering data from old profiles:

```bash
# Scan old profile
python3 firefox_extension_storage_recovery.py \
  /mnt/backup/old-firefox-profile/storage/default \
  --format all \
  --output-dir ./recovered
```

## Limitations

1. **Binary Data**: Only extracts JSON data; binary blobs without JSON are shown as previews
2. **Corrupted Databases**: Cannot recover from corrupted SQLite databases
3. **Encrypted Data**: Cannot decrypt if extension uses additional encryption
4. **Complex Encodings**: Some extensions may use custom serialization formats
5. **Active Extensions**: Best used on inactive/closed extensions to avoid locks

## Workflow Integration

### Import Recovered Data in Extension

After recovery, import the data back:

```javascript
// In your extension's background script
async function importRecoveredData() {
  // Load the recovered JSON file (via file picker or hardcoded for dev)
  const recoveredData = /* load JSON */;

  // Import back to storage
  await chrome.storage.local.set(recoveredData);

  console.log('Data recovered successfully!');
}
```

### Automated Recovery Script

Create a wrapper script:

```bash
#!/bin/bash
# auto-recover.sh

PROFILE=$(find ~/.mozilla/firefox -name "*.default*" | head -1)
TEMP_DIR=$(mktemp -d)

echo "Recovering from profile: $PROFILE"

python3 firefox_extension_storage_recovery.py \
  "$PROFILE/storage/default" \
  --search "yourextension.com" \
  --output-dir "$TEMP_DIR" \
  --format json

echo "Recovered data available in: $TEMP_DIR"
echo "Copy the JSON and import it in your extension"
```

## Contributing

Contributions welcome! Areas for improvement:

- [ ] Support for Chrome/Chromium extension storage
- [ ] GUI for easier recovery
- [ ] Automatic re-import into extensions
- [ ] Support for more encoding formats
- [ ] Better data type detection
- [ ] Diff tool for comparing storage states

## Troubleshooting

### "Database is locked"

Firefox is still running. Close Firefox or copy the database:
```bash
cp database.sqlite /tmp/db-copy.sqlite
python3 firefox_extension_storage_recovery.py /tmp/db-copy.sqlite
```

### "No JSON found"

Your extension might use binary storage or custom encoding. Use `--format pretty` to see raw data:
```bash
python3 firefox_extension_storage_recovery.py database.sqlite --format pretty
```

### "Permission denied"

Database files are usually readable, but if not:
```bash
sudo python3 firefox_extension_storage_recovery.py /path/to/database.sqlite
```

## License

MIT License - Feel free to use, modify, and distribute.

## Credits

Developed to solve the common frustration of losing extension data during Firefox development.

## Related Resources

- [Firefox Extension Workshop](https://extensionworkshop.com/)
- [chrome.storage API Documentation](https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/API/storage)
- [IndexedDB API](https://developer.mozilla.org/en-US/docs/Web/API/IndexedDB_API)

---

**Star this repo if it saved your data!** ⭐
