"""Regex-based lexer for PDX script files."""
import re

TOKEN_PATTERN = re.compile(
    r'(#.*)'            # comment
    r'|("[^"]*")'       # quoted string
    r'|(@\\?\[[^\]]+\])'  # @[] variable reference
    r'|(\[\[!?[^\]]*\])'  # [[]] scripted condition
    r'|(\?=|!=|>=|<=|[=\{\}<>!?])'  # operators
    r'|([^\s=\{\}<>!?]+)'  # word
    r'|\n'              # newline (for line counting)
)


def format_comment(val):
    """Normalize comment spacing: ensure space after # (except ## headers)."""
    if not val.startswith('##'):
        if len(val) > 1 and not val[1].isspace():
            return f"# {val[1:]}"
    return val


def tokenize(text):
    """Convert raw text into a list of token dicts.

    Each token has: type, val, line, pre (gap text), start, end.
    Tokens preceded by blank lines get a '_blank_before' flag.
    """
    tokens = []
    current_line = 1
    last_idx = 0

    for match in TOKEN_PATTERN.finditer(text):
        start, end = match.span()
        val = match.group(0)
        gap = text[last_idx:start]
        last_idx = end

        if val == '\n':
            current_line += 1
            continue

        if match.group(1):
            t_type = 'comment'
            val = format_comment(match.group(1))
        elif match.group(2):
            t_type = 'str'
            val = match.group(2)
        elif match.group(3):
            t_type = 'word'
            val = match.group(3)
            current_line += val.count('\n')
        elif match.group(4):
            t_type = 'word'
            val = match.group(4)
            current_line += val.count('\n')
        elif match.group(5):
            t_type = 'op'
            val = match.group(5)
        elif match.group(6):
            t_type = 'word'
            val = match.group(6)
        else:
            continue

        tokens.append({
            'type': t_type, 'val': val, 'line': current_line,
            'pre': gap, 'start': start, 'end': end,
        })

    # Mark tokens preceded by blank lines (line gap >= 2)
    for idx in range(1, len(tokens)):
        if tokens[idx]['line'] - tokens[idx - 1]['line'] >= 2:
            tokens[idx]['_blank_before'] = True

    return tokens
