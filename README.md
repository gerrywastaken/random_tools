# random_tools

A collection of small, focused utilities and scripts for solving specific problems. Each tool does one thing well, whether that's data recovery, format conversion, automation, or anything else that proves useful.

This repo is intentionally eclectic—tools here may have nothing in common except that they were needed at some point. Add new tools as you need them; no overarching theme required.

## Available Tools

### Firefox Extension Data Recovery

Tools for recovering data from Firefox extension storage (useful when extensions get reloaded with new UUIDs):

- `scan_firefox_databases.py` - Scan multiple SQLite files to find IndexedDB databases
- `find_firefox_extension.py` - Search for keywords across extension databases
- `extract_firefox_extension_data.py` - Extract JSON data from databases (handles BLOB encoding)
- `parse_indexeddb_structured.py` - Parse IndexedDB's structured clone format
- `extract_make_it_pop_data.py` - Extract make-it-pop extension-specific data

<details>
<summary>Usage examples</summary>

```bash
# Scan for IndexedDB databases
./scan_firefox_databases.py ~/.mozilla/firefox/*/storage/default/**/*.sqlite

# Find which database contains specific data
./find_firefox_extension.py "showjuice.com"

# Extract data from a database
./extract_firefox_extension_data.py path/to/extension.sqlite output.json

# Parse structured clone format
./parse_indexeddb_structured.py path/to/extension.sqlite recovered.json
```

</details>

---

More tools will be added as needed. Check individual scripts for detailed usage information.