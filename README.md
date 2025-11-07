# random_tools

Small scripts and utilities.

## Firefox Extension Data Recovery

Scripts for recovering data from Firefox extension storage when extensions get reloaded with new UUIDs.

**find_firefox_extension.py** - Find which extension database contains a keyword
```bash
./find_firefox_extension.py "showjuice.com"
./find_firefox_extension.py "example.com" ~/.mozilla/firefox/xyz.default/storage/default
```

**extract_firefox_extension_data.py** - Extract JSON data from a database (handles BLOB encoding)
```bash
./extract_firefox_extension_data.py path/to/extension.sqlite
./extract_firefox_extension_data.py path/to/extension.sqlite output.json
./extract_firefox_extension_data.py path/to/extension.sqlite --verbose  # debug mode
./extract_firefox_extension_data.py path/to/extension.sqlite --extract-text  # for binary data
```

**parse_indexeddb_structured.py** - Parse IndexedDB's structured clone format (for JavaScript objects)
```bash
./parse_indexeddb_structured.py path/to/extension.sqlite
./parse_indexeddb_structured.py path/to/extension.sqlite recovered.json
```

**extract_make_it_pop_data.py** - Extract make-it-pop extension data (groups and domains)
```bash
./extract_make_it_pop_data.py path/to/extension.sqlite
./extract_make_it_pop_data.py path/to/extension.sqlite recovered.json
```