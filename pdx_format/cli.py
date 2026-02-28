"""Command-line interface for pdx-format."""
import sys
import os
import argparse

from .config import FormatConfig
from .file_io import process_text, format_file


def main():
    parser = argparse.ArgumentParser(
        description='Format Paradox Interactive script files (.txt, .gui, .yml)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  pdx-format file.txt                    Format file in place
  pdx-format *.txt                       Format all .txt files
  pdx-format --check file.txt            Check if formatting needed
  pdx-format --diff file.txt             Show diff of changes
  cat file.txt | pdx-format -            Format stdin to stdout
        """
    )
    parser.add_argument('files', nargs='*', help='Files to format (use - for stdin)')
    parser.add_argument('--check', action='store_true',
                        help='Check if files need formatting (exit 1 if changes needed)')
    parser.add_argument('--diff', action='store_true', help='Show diff of changes')
    parser.add_argument('--no-compact', action='store_true',
                        help='Disable compacting of small blocks')
    parser.add_argument('--compact-limit', type=int, default=4, metavar='N',
                        help='Max key-value pairs in a compact single-line block (default: 4)')
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

    config = FormatConfig(
        no_compact=args.no_compact,
        compact_limit=args.compact_limit,
        block_spacing=args.block_spacing,
        add_bom=not args.no_bom,
    )

    # Handle stdin
    if args.files == ['-']:
        if sys.version_info >= (3, 7):
            sys.stdin.reconfigure(encoding='utf-8')
            sys.stdout.reconfigure(encoding='utf-8')
        content = sys.stdin.read()
        new_content, _ = process_text(content, config)
        sys.stdout.write(new_content)
        sys.exit(0)

    # Process files
    needs_formatting = []
    formatted = []
    errors = []

    for filepath in args.files:
        if not os.path.isfile(filepath):
            errors.append(filepath)
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
    if errors:
        sys.exit(1)
    sys.exit(0)
