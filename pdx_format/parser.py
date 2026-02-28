"""Token stream to AST parser.

The AST is a list of node dicts. Each node has:
  - type: 'node', 'comment', or 'raw_block'
  - key: the keyword/identifier (for 'node' type)
  - op: operator like '=', '>', '<' etc. (or None)
  - val: scalar value, 'PENDING_BLOCK' during parsing, or list of child nodes
  - Optional metadata: _blank_before, _cm_preceding, _cm_inline, _cm_open, _cm_close
"""
from .constants import RAW_BLOCKS


def _get_inline_comment(tokens, current_idx, current_line):
    """Check if the next token is an inline comment on the same line.

    Returns (comment_text, offset) where offset is 1 if found, 0 if not.
    """
    if current_idx + 1 < len(tokens):
        next_t = tokens[current_idx + 1]
        if next_t['type'] == 'comment' and next_t['line'] == current_line:
            return next_t['pre'] + next_t['val'], 1
    return None, 0


def _attach_metadata(node, token, preceding_comments):
    """Attach preceding comments and blank-before flag to a node."""
    if preceding_comments:
        node['_cm_preceding'] = [c['val'] for c in preceding_comments]
    if token.get('_blank_before'):
        node['_blank_before'] = True


def _skip_comments(tokens, start_idx):
    """Advance past comment tokens, returning the next non-comment index."""
    idx = start_idx
    while idx < len(tokens) and tokens[idx]['type'] == 'comment':
        idx += 1
    return idx


def _parse_raw_block(tokens, text, token, i):
    """Try to parse a raw block (switch, inverted_switch). Returns (node, next_i) or None."""
    token_val = tokens[i]['val']
    if tokens[i]['type'] != 'word' or token_val not in RAW_BLOCKS:
        return None

    op_idx = _skip_comments(tokens, i + 1)
    if op_idx >= len(tokens) or tokens[op_idx]['val'] != '=':
        return None

    brace_idx = _skip_comments(tokens, op_idx + 1)
    if brace_idx >= len(tokens) or tokens[brace_idx]['val'] != '{':
        return None

    # Scan for matching close brace
    brace_level = 1
    scan_idx = brace_idx + 1
    while scan_idx < len(tokens):
        if tokens[scan_idx]['val'] == '{':
            brace_level += 1
        elif tokens[scan_idx]['val'] == '}':
            brace_level -= 1
            if brace_level == 0:
                raw_text = text[token['start']:tokens[scan_idx]['end']]
                node = {'type': 'raw_block', 'val': raw_text}
                if token.get('_blank_before'):
                    node['_blank_before'] = True
                return node, scan_idx + 1
        scan_idx += 1

    return None


def _collect_lookahead(tokens, start_idx, count=5):
    """Collect up to `count` non-comment tokens starting at start_idx."""
    lookahead = []
    idx = start_idx
    while idx < len(tokens) and len(lookahead) < count:
        if tokens[idx]['type'] != 'comment':
            lookahead.append((idx, tokens[idx]))
        idx += 1
    return lookahead


def _parse_node_pattern(tokens, token, i, lookahead):
    """Determine the node pattern from lookahead tokens.

    Returns (node_dict, skip_to_index) or (None, None).
    Patterns handled:
      word {                  -> key { block }
      word = value            -> key = value
      word = {                -> key = { block }
      word = value {          -> key = val_key { block }
      word word {             -> key val_key { block }
      word "str" {            -> key val_key { block }
      word word = word {      -> key mid_key = val_key { block }
    """
    token_val = token['val']
    if not lookahead:
        return None, None

    t1_idx, t1 = lookahead[0]

    # word {
    if t1['val'] == '{':
        node = {'key': token_val, 'op': None, 'val': 'PENDING_BLOCK', 'type': 'node',
                '_token_start': token['start']}
        return node, t1_idx

    # word = ...
    if t1['type'] == 'op' and t1['val'] not in ['{', '}']:
        operator = t1['val']
        if len(lookahead) >= 2:
            t2_idx, t2 = lookahead[1]
            # word = {
            if t2['val'] == '{':
                node = {'key': token_val, 'op': operator, 'val': 'PENDING_BLOCK', 'type': 'node',
                        '_token_start': token['start']}
                return node, t2_idx
            # word = value ...
            if t2['type'] in ('word', 'str'):
                if len(lookahead) >= 3:
                    t3_idx, t3 = lookahead[2]
                    # word = value {
                    if t3['val'] == '{':
                        node = {'key': token_val, 'op': operator, 'val_key': t2['val'],
                                'val': 'PENDING_BLOCK', 'type': 'node', '_token_start': token['start']}
                        return node, t3_idx
                # word = value (no block)
                node = {'key': token_val, 'op': operator, 'val': t2['val'], 'type': 'node'}
                cm, offset = _get_inline_comment(tokens, t2_idx, t2['line'])
                if cm:
                    node['_cm_inline'] = cm
                    t2_idx += offset
                return node, t2_idx + 1
        return None, None

    # word word ... or word "str" ...
    if t1['type'] in ('word', 'str'):
        mid_val = t1['val']
        if len(lookahead) >= 2:
            t2_idx, t2 = lookahead[1]
            # word word {
            if t2['val'] == '{':
                node = {'key': token_val, 'op': None, 'val_key': mid_val,
                        'val': 'PENDING_BLOCK', 'type': 'node', '_token_start': token['start']}
                return node, t2_idx
            # word word = ...
            if t2['type'] == 'op' and t2['val'] not in ['{', '}']:
                operator = t2['val']
                if len(lookahead) >= 3:
                    t3_idx, t3 = lookahead[2]
                    if t3['type'] in ('word', 'str'):
                        if len(lookahead) >= 4:
                            t4_idx, t4 = lookahead[3]
                            # word word = value {
                            if t4['val'] == '{':
                                node = {'key': token_val, 'op': operator, 'mid_key': mid_val,
                                        'val_key': t3['val'], 'val': 'PENDING_BLOCK', 'type': 'node',
                                        '_token_start': token['start']}
                                return node, t4_idx
                        # word word = value (no block) - treat as word word { pending
                        node = {'key': token_val, 'op': None, 'val_key': mid_val,
                                'val': 'PENDING_BLOCK', 'type': 'node', '_token_start': token['start']}
                        return node, t2_idx

    return None, None


def parse(tokens, text):
    """Parse a token list into an AST (nested list of node dicts)."""
    stack = []
    current_list = []
    i = 0
    preceding_comments = []

    while i < len(tokens):
        token = tokens[i]
        token_line = token['line']
        token_val = token['val']

        # Handle raw blocks (switch, inverted_switch)
        result = _parse_raw_block(tokens, text, token, i)
        if result:
            node, next_i = result
            preceding_comments = []
            current_list.append(node)
            i = next_i
            continue

        # Comments
        if token['type'] == 'comment':
            current_list.append(token)
            preceding_comments.append(token)
            i += 1
            continue

        # Close brace
        if token_val == '}':
            if not stack:
                break
            finished_list = current_list
            current_list = stack.pop()
            if current_list and current_list[-1].get('val') == 'PENDING_BLOCK':
                parent_node = current_list[-1]
                parent_node['val'] = finished_list
                if parent_node.get('key') == 'switch' and '_token_start' in parent_node:
                    parent_node['_raw'] = text[parent_node['_token_start']:token['end']]
                cm, offset = _get_inline_comment(tokens, i, token_line)
                if cm:
                    parent_node['_cm_close'] = cm
                    i += offset
            preceding_comments = []
            i += 1
            continue

        # Open brace (bare block without key)
        if token_val == '{':
            if current_list and current_list[-1].get('val') == 'PENDING_BLOCK':
                cm, offset = _get_inline_comment(tokens, i, token_line)
                if cm:
                    current_list[-1]['_cm_open'] = cm
                    i += offset
            stack.append(current_list)
            current_list = []
            i += 1
            continue

        # Word/string token - determine pattern via lookahead
        lookahead = _collect_lookahead(tokens, i + 1)
        node, skip_to = _parse_node_pattern(tokens, token, i, lookahead)

        if node:
            _attach_metadata(node, token, preceding_comments)
            preceding_comments = []
            current_list.append(node)
            i = skip_to
            continue

        # Fallback: standalone word
        node = {'key': token_val, 'val': None, 'type': 'node'}
        _attach_metadata(node, token, preceding_comments)
        preceding_comments = []
        cm, offset = _get_inline_comment(tokens, i, token_line)
        if cm:
            node['_cm_inline'] = cm
            i += offset
        current_list.append(node)
        i += 1

    return current_list
