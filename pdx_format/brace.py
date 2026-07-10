"""Brace balance checking (merged from the standalone pdx-brace tool).

Pinpoints which opening brace has no closer (or which closing brace has no
opener), with surrounding context so you can see the block label.

The scanner mirrors engine semantics: a comment starts at any '#' outside a
string literal — even glued to the preceding token (`foo = bar# }` is a
comment from '#' on). Braces inside string literals (`text = "}"`) are not
structure. String state carries across lines: generated gfx files hold
multi-line string blobs whose closing line is `"}`  — that close brace IS
structural, and braces inside the blob are not.
"""
from pathlib import Path

EXTENSIONS = {".txt", ".gui"}
SKIP_PARTS = {".claude", "__pycache__", ".git", ".gui_workspace"}


def structural_code(line: str, in_string: bool) -> tuple[str, bool]:
    """Return (line with comments removed and string contents blanked,
    string state at end of line), so only structural braces remain."""
    out = []
    for ch in line:
        if ch == '"':
            in_string = not in_string
            out.append(" ")
        elif in_string:
            out.append(" ")
        elif ch == "#":
            break
        else:
            out.append(ch)
    return "".join(out), in_string


def find_problems(text: str) -> list[tuple[int, str]]:
    """Scan text and return [(lineno, kind)] where kind is 'extra_close'
    or 'unclosed'. Empty list means balanced."""
    stack = []
    problems = []
    in_string = False

    for lineno, raw_line in enumerate(text.splitlines(), 1):
        stripped, in_string = structural_code(raw_line, in_string)
        for ch in stripped:
            if ch == "{":
                stack.append(lineno)
            elif ch == "}":
                if stack:
                    stack.pop()
                else:
                    problems.append((lineno, "extra_close"))

    problems.extend((lineno, "unclosed") for lineno in stack)
    return problems


def render_problem(label: str, lines: list[str], lineno: int, kind: str,
                   ctx: int = 2) -> str:
    if kind == "extra_close":
        header = f"{label}:{lineno}: extra '}}' with no matching opener"
    else:
        header = f"{label}:{lineno}: block opened here is never closed"

    snippet_lines = []
    start = max(0, lineno - 1 - ctx)
    end = min(len(lines), lineno + ctx)
    for i in range(start, end):
        marker = " >> " if i == lineno - 1 else "    "
        snippet_lines.append(f"  {marker}{i + 1:>5} | {lines[i]}")

    return header + "\n" + "\n".join(snippet_lines)


def check_text(text: str, label: str, ctx: int = 2) -> list[str]:
    """Return rendered problem reports for a text blob."""
    lines = text.splitlines()
    return [render_problem(label, lines, lineno, kind, ctx)
            for lineno, kind in find_problems(text)]


def check_file(path: Path, ctx: int = 2) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except Exception as e:
        return [f"{path}: read error: {e}"]
    return check_text(text, str(path), ctx)


def collect_files(target: Path) -> list[Path]:
    """Expand a file or directory target into checkable files."""
    if target.is_file():
        return [target]
    files = []
    for ext in sorted(EXTENSIONS):
        files.extend(sorted(target.rglob(f"*{ext}")))
    return [f for f in files if not SKIP_PARTS.intersection(f.parts)]


def run_check(targets: list[str], ctx: int = 2, quiet: bool = False) -> int:
    """CLI entry: check files/dirs, print reports, return exit code."""
    import sys

    files = []
    for t in targets:
        p = Path(t)
        if not p.exists():
            print(f"Not found: {p}", file=sys.stderr)
            return 1
        files.extend(collect_files(p))

    total_problems = 0
    for f in files:
        problems = check_file(f, ctx)
        for p in problems:
            print(p)
            print()
        total_problems += len(problems)

    plural_p = "s" if total_problems != 1 else ""
    plural_f = "s" if len(files) != 1 else ""
    if total_problems == 0:
        if not quiet:
            print(f"All balanced ({len(files)} file{plural_f} checked)")
        return 0
    print(f"Found {total_problems} brace problem{plural_p} "
          f"in {len(files)} file{plural_f}")
    return 1
