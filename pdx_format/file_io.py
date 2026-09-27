"""File I/O and formatting orchestration."""
import os
import sys

from .config import FormatConfig
from .constants import BOM_ONLY_EXTENSIONS
from .tokenizer import tokenize
from .parser import parse, MisnestedBracesError
from .transforms import lowercase_keys, uppercase_keys, lowercase_yes_no_values
from .formatter import block_to_string
from .brace import check_text


def _print_brace_pinpoint(content, label, limit=3):
    """Show where the brace problem is, so 'skipping' is actionable."""
    problems = check_text(content, label)
    for p in problems[:limit]:
        print(p, file=sys.stderr)
    if len(problems) > limit:
        print(f"  ... {len(problems) - limit} more "
              f"(run: pdx-format --brace {label})", file=sys.stderr)


def _name_keyless(nodes):
    """Give keyless blocks (`{ 0.0 1.0 }` in a list) an empty key for the formatter."""
    for node in nodes:
        if node.get('type') == 'node':
            if node.get('key') is None:
                node['key'] = ''
            if isinstance(node.get('val'), list):
                _name_keyless(node['val'])


def _content_mismatch(before, after):
    """Describe how two token streams differ in content, or return None.

    Code tokens must match in order; the key transforms only change case.
    Comments must match as a multiset, because a brace-line comment can be
    hoisted above its block.
    """
    code_a = [t['val'].lower() for t in before if t['type'] != 'comment']
    code_b = [t['val'].lower() for t in after if t['type'] != 'comment']
    if code_a != code_b:
        for i, (a, b) in enumerate(zip(code_a, code_b)):
            if a != b:
                return f"code token {i}: {a!r} became {b!r}"
        return f"code token count {len(code_a)} became {len(code_b)}"
    com_a = sorted(t['val'].rstrip() for t in before if t['type'] == 'comment')
    com_b = sorted(t['val'].rstrip() for t in after if t['type'] == 'comment')
    if com_a != com_b:
        missing = set(com_a) - set(com_b)
        sample = next(iter(missing)) if missing else ''
        return f"{len(com_a)} comments became {len(com_b)}; lost {sample!r}"
    return None


def process_text(content, config, filepath=None):
    """Format PDX script text. Returns (new_content, changed)."""
    label = filepath or "<input>"
    try:
        original_content = content
        content = content.replace('\r\n', '\n')
        tokens = tokenize(content)

        # Guard against malformed input - mismatched braces cause data loss
        open_count = sum(1 for t in tokens if t['type'] == 'op' and t['val'] == '{')
        close_count = sum(1 for t in tokens if t['type'] == 'op' and t['val'] == '}')
        if open_count != close_count:
            print(f"Error: {label}: mismatched braces ({open_count} open, {close_count} close), "
                  f"skipping to prevent data loss", file=sys.stderr)
            _print_brace_pinpoint(content, label)
            return content, False

        tree = parse(tokens, content, keyless=True)
        _name_keyless(tree)
        lowercase_keys(tree)
        uppercase_keys(tree)
        lowercase_yes_no_values(tree)

        new_content = block_to_string(tree, config)
        if new_content and not new_content.endswith('\n'):
            new_content += '\n'

        lost = _content_mismatch(tokens, tokenize(new_content))
        if lost:
            print(f"Error: {label}: formatting would change content ({lost}), "
                  f"skipping to prevent data loss", file=sys.stderr)
            return original_content, False

        if new_content != original_content:
            return new_content, True
        return original_content, False
    except MisnestedBracesError as e:
        print(f"Error: {label}: {e}, skipping to prevent data loss",
              file=sys.stderr)
        _print_brace_pinpoint(content, label)
        return content, False
    except Exception as e:
        print(f"Error processing {label}: {e}", file=sys.stderr)
        return content, False


from pdx_utilities.fileio import read_with_bom as _read_file_with_bom  # noqa: E402
from pdx_utilities.fileio import write_with_bom as _write_with_bom  # noqa: E402


def _write_file(filepath, content, want_bom):
    """Write content to file with optional BOM."""
    _write_with_bom(filepath, content, bom=want_bom)


def bom_only_file(filepath, config, check_only=False, show_diff=False):
    """Add/remove BOM on files that shouldn't be reformatted. Returns True if changed."""
    try:
        content, has_bom = _read_file_with_bom(filepath)
        want_bom = config.add_bom
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

    want_bom = config.add_bom
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
