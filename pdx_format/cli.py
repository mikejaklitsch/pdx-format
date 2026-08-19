"""Command-line interface for pdx-format."""
import sys
import os
import argparse

from .config import FormatConfig
from .constants import BOM_ONLY_EXTENSIONS
from .file_io import process_text, format_file
from . import brace

FORMAT_EXTENSIONS = {'.txt', '.gui'} | BOM_ONLY_EXTENSIONS


def expand_targets(paths, extensions, quiet=False):
    """Expand files and directories into a flat file list. Directories are
    searched recursively for matching extensions, skipping tool/VCS dirs.
    Returns (files, missing_count)."""
    from pathlib import Path
    files = []
    missing = 0
    for raw in paths:
        p = Path(raw)
        if p.is_file():
            files.append(raw)
        elif p.is_dir():
            found = []
            for ext in sorted(extensions):
                found.extend(sorted(p.rglob(f"*{ext}")))
            files.extend(str(f) for f in found
                         if not brace.EXCLUDE_PARTS.intersection(f.parts))
        else:
            missing += 1
            if not quiet:
                print(f"File not found: {raw}", file=sys.stderr)
    return files, missing


def main():
    parser = argparse.ArgumentParser(
        description='Format Paradox Interactive script files (.txt, .gui, .yml)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  pdx-format file.txt                    Format file in place
  pdx-format *.txt                       Format all .txt files
  pdx-format some/dir                    Format a directory recursively
  pdx-format --check file.txt            Check if formatting needed
  pdx-format --diff file.txt             Show diff of changes
  pdx-format --brace file.txt            Check brace balance only (pdx-brace)
  cat file.txt | pdx-format -            Format stdin to stdout
        """
    )
    parser.add_argument('files', nargs='*',
                        help='Files or directories to format (use - for stdin)')
    parser.add_argument('--check', action='store_true',
                        help='Check if files need formatting (exit 1 if changes needed)')
    parser.add_argument('--diff', action='store_true', help='Show diff of changes')
    parser.add_argument('--brace', action='store_true',
                        help='Check brace balance only, no formatting '
                             '(exit 1 if problems found)')
    parser.add_argument('--context', type=int, default=2, metavar='N',
                        help='Context lines around --brace problems (default: 2)')
    parser.add_argument('--no-compact', action='store_true',
                        help='Disable compacting of small blocks')
    parser.add_argument('--compact-limit', type=int, default=2, metavar='N',
                        help='Max key-value pairs in a compact single-line block (default: 2)')
    parser.add_argument('--compact-max-chars', type=int, default=120, metavar='N',
                        help='Max characters for a compact single-line block (default: 120)')
    parser.add_argument('--block-spacing', type=int, default=1, metavar='N',
                        help='Blank lines between top-level blocks (default: 1)')
    parser.add_argument('--no-bom', action='store_true',
                        help='Do not add UTF-8 BOM (BOM is added by default)')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='Suppress output except errors')

    args = parser.parse_args()

    if not args.files:
        parser.print_help()
        sys.exit(0)

    # Brace-check mode (merged pdx-brace)
    if args.brace:
        if args.files == ['-']:
            problems = brace.check_text(sys.stdin.read(), '<stdin>', args.context)
            for p in problems:
                print(p)
                print()
            if problems:
                print(f"Found {len(problems)} brace problem"
                      f"{'s' if len(problems) != 1 else ''}")
            elif not args.quiet:
                print("All balanced (stdin)")
            sys.exit(1 if problems else 0)
        sys.exit(brace.run_check(args.files, args.context, args.quiet))

    config = FormatConfig(
        no_compact=args.no_compact,
        compact_limit=args.compact_limit,
        compact_max_chars=args.compact_max_chars,
        block_spacing=args.block_spacing,
        add_bom=not args.no_bom,
    )

    # Handle stdin
    if args.files == ['-']:
        sys.stdin.reconfigure(encoding='utf-8')
        sys.stdout.reconfigure(encoding='utf-8')
        content = sys.stdin.read()
        new_content, _ = process_text(content, config)
        sys.stdout.write(new_content)
        sys.exit(0)

    # Process files
    needs_formatting = []
    formatted = []
    files, missing = expand_targets(args.files, FORMAT_EXTENSIONS, args.quiet)
    errors = missing > 0

    for filepath in files:
        if not os.path.isfile(filepath):
            errors = True
            if not args.quiet:
                print(f"File not found: {filepath}", file=sys.stderr)
            continue

        changed = format_file(filepath, config, check_only=args.check, show_diff=args.diff)
        if changed:
            if args.check:
                needs_formatting.append(filepath)
            else:
                formatted.append(filepath)

    # Output results
    if not args.quiet and not args.diff:
        if args.check:
            if needs_formatting:
                print(f"Would reformat: {', '.join(needs_formatting)}")
            else:
                print("All files are formatted correctly")
        else:
            if formatted:
                print(f"Formatted: {', '.join(formatted)}")

    if args.check and needs_formatting:
        sys.exit(1)
    sys.exit(1 if errors else 0)


def brace_main():
    if len(sys.argv) < 2:
        print("Usage: pdx-brace <file|dir> [--context N]")
        sys.exit(1)
    sys.argv = [sys.argv[0], '--brace'] + sys.argv[1:]
    main()
