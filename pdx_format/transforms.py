"""AST transformation passes for keyword normalization."""
from .constants import (
    KEYWORDS_TO_LOWER, KEYWORDS_TO_LOWER_START, KEYWORDS_TO_LOWER_END,
    KEYWORDS_TO_LOWER_LIST, KEYWORDS_TO_UPPER, VAL_KEYWORDS_TO_LOWER,
)


def lowercase_keys(node_list):
    """Normalize certain keywords to lowercase (ROOT -> root, PREV -> prev, etc.)."""
    changed = False
    for node in node_list:
        if node['type'] != 'node':
            continue
        is_block = isinstance(node.get('val'), list)
        if 'key' in node:
            key = node['key']
            if (key in KEYWORDS_TO_LOWER or
                    key.endswith(KEYWORDS_TO_LOWER_END) or
                    key.startswith(KEYWORDS_TO_LOWER_START) or
                    (is_block and key in KEYWORDS_TO_LOWER_LIST)):
                lower = key.lower()
                if key != lower:
                    node['key'] = lower
                    changed = True
        if is_block:
            if lowercase_keys(node['val']):
                changed = True
    return changed


def uppercase_keys(node_list):
    """Normalize logic operators to uppercase (or -> OR, not -> NOT, etc.)."""
    changed = False
    for node in node_list:
        if node['type'] != 'node':
            continue
        if 'key' in node and isinstance(node.get('val'), list):
            key = node['key']
            upper = key.upper()
            if upper in KEYWORDS_TO_UPPER and key != upper:
                node['key'] = upper
                changed = True
        if isinstance(node.get('val'), list):
            if uppercase_keys(node['val']):
                changed = True
    return changed


def lowercase_yes_no_values(node_list):
    """Normalize yes/no and scope values to lowercase."""
    changed = False
    for node in node_list:
        if node['type'] != 'node':
            continue
        val = node.get('val')
        if isinstance(val, list):
            if lowercase_yes_no_values(val):
                changed = True
        elif val in VAL_KEYWORDS_TO_LOWER:
            node['val'] = val.lower()
            changed = True
    return changed
