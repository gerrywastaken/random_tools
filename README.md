# Random Tools

A collection of useful utility scripts and tools.

## Firefox Extension Storage Recovery Tool

A Python utility for recovering `chrome.storage.local` data from Firefox extension's IndexedDB storage.

### Quick Start

```bash
# Generate test data
python3 test_database_generator.py /tmp/test_storage

# Recover data
python3 firefox_extension_storage_recovery.py /tmp/test_storage

# Export to files
python3 firefox_extension_storage_recovery.py /tmp/test_storage --output-dir ./recovered
```

### Documentation

See [README_FIREFOX_RECOVERY.md](README_FIREFOX_RECOVERY.md) for complete documentation.

### Problem It Solves

Firefox temporary extensions (loaded via `about:debugging`) get assigned a new UUID each time they're reloaded, causing them to lose access to their `chrome.storage.local` data. This tool recovers that "orphaned" data from the IndexedDB SQLite databases on disk.

### Features

- Scans Firefox profile storage directories for extension databases
- Decodes binary IndexedDB BLOBs to extract JSON data
- Identifies and categorizes different types of stored data
- Exports recovered data to organized JSON files
- Supports searching by content
- Multiple output formats (summary, pretty-print, JSON)

### Requirements

- Python 3.6+
- No external dependencies (uses only standard library)

### Files

- `firefox_extension_storage_recovery.py` - Main recovery tool
- `test_database_generator.py` - Test data generator
- `README_FIREFOX_RECOVERY.md` - Complete documentation
- `LICENSE` - MIT License

## License

MIT License - See [LICENSE](LICENSE) file for details.