# random_tools

Small scripts and utilities.

## Firefox Extension Data Recovery

Two simple scripts for recovering data from Firefox extension storage when extensions get reloaded with new UUIDs.

**find_firefox_extension.py** - Find which extension database contains a keyword
```bash
./find_firefox_extension.py "showjuice.com"
./find_firefox_extension.py "example.com" ~/.mozilla/firefox/xyz.default/storage/default
```

**extract_firefox_extension_data.py** - Extract JSON data from a database (handles BLOB encoding)
```bash
./extract_firefox_extension_data.py path/to/extension.sqlite
./extract_firefox_extension_data.py path/to/extension.sqlite output.json
```