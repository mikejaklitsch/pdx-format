"""Formatting configuration."""
from dataclasses import dataclass


@dataclass
class FormatConfig:
    no_compact: bool = False
    compact_limit: int = 2
    compact_max_chars: int = 120
    block_spacing: int = 1
    add_bom: bool = True
