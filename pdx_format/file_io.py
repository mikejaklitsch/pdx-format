"""File I/O and formatting orchestration."""
import os
import sys

from .config import FormatConfig
from .constants import BOM_ONLY_EXTENSIONS
from .tokenizer import tokenize
from .parser import parse
from .transforms import lowercase_keys, uppercase_keys, lowercase_yes_no_values
from .formatter import block_to_string


def process_text(content, config, filepath=None):
    """Format PDX script text. Returns (new_content, changed)."""
    try:
        original_content = content
        content = content.replace('\r\n', '\n')
        tokens = tokenize(content)

        # Guard against malformed input - mismatched braces cause data loss
        open_count = sum(1 for t in tokens if t['type'] == 'op' and t['val'] == '{')
        close_count = sum(1 for t in tokens if t['type'] == 'op' and t['val'] == '}')
        if open_count != close_count:
            label = filepath or "<input>"
            print(f"Error: {label}: mismatched braces ({open_count} open, {close_count} close), "
                  f"skipping to prevent data loss", file=sys.stderr)
            return content, False

        tree = parse(tokens, content)
        lowercase_keys(tree)
        uppercase_keys(tree)
        lowercase_yes_no_values(tree)

        new_content = block_to_string(tree, config)
        if new_content and not new_content.endswith('\n'):
            new_content += '\n'

        if new_content != original_content:
            return new_content, True
        return original_content, False
    except Exception as e:
        print(f"Error processing: {e}", file=sys.stderr)
        return content, False


def _read_file_with_bom(filepath):
    """Read a file, detecting BOM. Returns (content, has_bom)."""
    with open(filepath, 'rb') as f:
        has_bom = f.read(3) == b'\xef\xbb\xbf'
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        content = f.read()
    return content, has_bom


def _write_file(filepath, content, want_bom):
    """Write content to file with optional BOM."""
    encoding = 'utf-8-sig' if want_bom else 'utf-8'
    with open(filepath, 'w', encoding=encoding, newline='\n') as f:
        f.write(content)


def bom_only_file(filepath, config, check_only=False, show_diff=False):
    """Add/remove BOM on files that shouldn't be reformatted. Returns True if changed."""
    try:
        content, has_bom = _read_file_with_bom(filepath)
        want_bom = config.add_bom or has_bom
        if want_bom == has_bom:
            return False
    except Exception as e:
        print(f"Error reading {filepath}: {e}", file=sys.stderr)
        return False

    if show_diff:
        label = "add" if want_bom else "remove"
        print(f"{filepath}: would {label} UTF-8 BOM")
        return True

    if check_only:
        return True

    try:
        _write_file(filepath, content, want_bom)
        return True
    except Exception as e:
        print(f"Error writing {filepath}: {e}", file=sys.stderr)
        return False


def format_file(filepath, config, check_only=False, show_diff=False):
    """Format a single file. Returns True if file was changed/needs changes."""
    ext = os.path.splitext(filepath)[1].lower()
    if ext in BOM_ONLY_EXTENSIONS:
        return bom_only_file(filepath, config, check_only, show_diff)

    try:
        content, has_bom = _read_file_with_bom(filepath)
    except Exception as e:
        print(f"Error reading {filepath}: {e}", file=sys.stderr)
        return False

    new_content, changed = process_text(content, config, filepath)

    want_bom = config.add_bom or has_bom
    bom_changed = want_bom != has_bom

    if not changed and not bom_changed:
        return False

    if show_diff:
        import difflib
        diff = difflib.unified_diff(
            content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"a/{filepath}",
            tofile=f"b/{filepath}"
        )
        sys.stdout.writelines(diff)
        return True

    if check_only:
        return True

    try:
        _write_file(filepath, new_content, want_bom)
        return True
    except Exception as e:
        print(f"Error writing {filepath}: {e}", file=sys.stderr)
        return False
