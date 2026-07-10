# PDX Format

CLI formatter and VS Code extension for Paradox Interactive script files (`.txt`, `.gui`).

Based on [F1r3Pr1nc3's paradox-formatter](https://github.com/F1r3Pr1nc3/paradox-formatter) (MIT License).

## Features

- Formats Paradox script syntax (`key = value`, `key = { block }`)
- Handles GUI-specific syntax (`types Name { }`, `type name = parent { }`)
- Preserves BOM encoding for GUI files
- Never compacts logical operators (AND, OR, NOT, etc.)
- Preserves comments and their positioning
- Refuses malformed input (mismatched or mis-nested braces) instead of
  truncating, and pinpoints the offending brace with context
- Built-in brace checker (`--brace`, merged from the standalone pdx-brace
  tool): comment-aware and string-aware, so it handles glued comments
  (`foo# }`), braces in strings (`"}"`), and multi-line string blobs in
  generated files

## Brace Checking

```bash
pdx-format --brace file.txt          # pinpoint unbalanced braces
pdx-format --brace some/dir          # check all .txt/.gui recursively
pdx-format --brace file.txt --context 5
cat file.txt | pdx-format --brace -  # check stdin
```

`pdx-brace` remains available as a thin alias taking the same arguments.
Formatting a file with brace problems automatically prints the same
pinpoint report instead of a bare "mismatched braces" count.

## CLI Installation

```bash
# Copy to local bin
cp pdx-format ~/.local/bin/
chmod +x ~/.local/bin/pdx-format

# Format a file in place
pdx-format path/to/file.txt

# Format from stdin
cat file.txt | pdx-format -

# Check formatting without modifying (exits 1 if changes needed)
pdx-format --check path/to/file.txt
```

## VS Code Extension Installation

```bash
# Copy extension to VS Code extensions directory
cp -r vscode-extension ~/.vscode-server/extensions/local.pdx-format-1.0.0/
# Or for local VS Code:
cp -r vscode-extension ~/.vscode/extensions/local.pdx-format-1.0.0/
```

Then reload VS Code and configure in `.vscode/settings.json`:

```json
{
    "[paradox]": {
        "editor.defaultFormatter": "local.pdx-format",
        "editor.formatOnSave": true
    },
    "files.associations": {
        "*.txt": "paradox",
        "*.gui": "paradox"
    }
}
```

## Configuration

The extension looks for `pdx-format` at `~/.local/bin/pdx-format` by default. Override with:

```json
{
    "pdxFormat.formatterPath": "/custom/path/to/pdx-format"
}
```

## Supported Games

Should work with any Paradox game using the clausewitz script format:
- Europa Universalis V
- Victoria 3
- Crusader Kings 3
- Hearts of Iron IV
- Stellaris

## License

MIT License
