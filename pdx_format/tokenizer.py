"""Regex-based lexer for PDX script files: the shared tokenizer in
pdx_utilities.script_parser, kept importable from here."""
from pdx_utilities.script_parser import TOKEN_PATTERN, format_comment, tokenize  # noqa: F401
