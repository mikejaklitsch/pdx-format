"""AST to formatted text output."""
from .config import FormatConfig
from .constants import (
    COMPACT_SUFFIXES, NON_COMPACT_SUFFIXES, KEYWORDS_TO_UPPER,
    NON_NEGATABLE_SCOPES,
)


def _find_prev_non_comment(children, i):
    """Walk backwards to find the previous non-comment node."""
    for j in range(i - 1, -1, -1):
        if children[j].get('type') != 'comment':
            return children[j]
    return None


def _is_expanded_block(child, depth, config):
    """Check if a block child would be rendered as expanded (multi-line)."""
    if not isinstance(child.get('val'), list) or child.get('type') != 'node':
        return False
    child_key = child.get('key', '')
    child_depth = depth + 1
    can_compact = (
        not config.no_compact and
        child_depth > 0 and
        (child_depth > 1 or child_key.endswith(COMPACT_SUFFIXES)) and
        not child_key.endswith(NON_COMPACT_SUFFIXES)
    )
    return not (can_compact and should_be_compact(child, config))


def _should_add_blank_within_block(child, i, children, depth, config,
                                   prev_is_expanded, prev_is_block,
                                   prev_was_comment, prev_was_header,
                                   is_comment, is_expanded, is_block,
                                   comment_is_header, child_key):
    """Determine whether to insert a blank line before a child node inside a block."""
    if i == 0:
        return False

    add_space = False
    if ((not is_comment and (not prev_was_comment or prev_was_header)) or
            (comment_is_header and not prev_was_comment) or
            (is_comment and prev_is_block)):
        if depth == 0:
            if is_block or prev_is_block:
                add_space = True
        else:
            if is_expanded or prev_is_expanded:
                add_space = True

    # Suppress blanks in certain cases
    if add_space and is_block:
        if (child_key in NON_NEGATABLE_SCOPES or
                child_key.endswith(COMPACT_SUFFIXES) or
                child_key in KEYWORDS_TO_UPPER):
            add_space = False
        else:
            prev_node = _find_prev_non_comment(children, i)
            if prev_node and isinstance(prev_node.get('val'), list):
                prev_key = prev_node.get('key')
                if child_key == prev_key:
                    add_space = False
                elif prev_key and (prev_key in NON_NEGATABLE_SCOPES or
                                   prev_key.endswith(COMPACT_SUFFIXES) or
                                   prev_key in KEYWORDS_TO_UPPER):
                    add_space = False
            elif prev_node and prev_node.get('key') in ("exists", "optimize_memory"):
                add_space = False

    # Preserve user's intentional blank lines
    if not add_space and child.get('_blank_before'):
        add_space = True

    return add_space


def should_be_compact(node, config):
    """Determine if a block node should be rendered on a single line."""
    if node.get('type') != 'node':
        return False
    val = node.get('val')
    if not isinstance(val, list):
        return False

    key = node.get('key', '')
    cm_close = node.get('_cm_close', "")

    # Any child comment prevents compacting
    for c in val:
        if c.get('type') == 'comment':
            return False

    children = [c for c in val if c['type'] == 'node']

    if len(children) > config.compact_limit:
        return False
    if key.endswith(NON_COMPACT_SUFFIXES):
        return False
    if key in KEYWORDS_TO_UPPER:
        return False

    total_len = len(key) + 6
    for child in children:
        if child.get('_cm_preceding') or child.get('_cm_open'):
            return False
        if child.get('_cm_inline') or child.get('_cm_close'):
            return False
        child_key = child.get('key', '')
        child_val = child.get('val')

        if isinstance(child_val, list):
            if len([c for c in child_val if c['type'] == 'node']) > 2:
                return False
            if not should_be_compact(child, config):
                return False
            child_len = sum(
                len(c.get('key', '')) + len(str(c.get('val', ''))) + 5
                for c in child_val if c['type'] == 'node'
            )
            child_len += len(child_key) + 6
        else:
            child_len = len(child_key) + len(str(child_val or '')) + 5
        total_len += child_len

    if key.endswith(COMPACT_SUFFIXES):
        total_len /= 2
    if total_len > 80 and not cm_close:
        return False
    return True


def node_to_string(node, depth=0, *, config, be_compact=False):
    """Convert a single AST node to its formatted string representation."""
    indent = "\t" * depth

    if node.get('type') == 'comment':
        return f"{indent}{node['val'].rstrip()}"

    if node.get('type') == 'raw_block':
        content = node['val'].rstrip().rstrip('}').rstrip()
        return f"{indent}{content}\n{indent}}}"

    key = node.get('key')
    op = node.get('op')

    # Block node (has children)
    if isinstance(node.get('val'), list):
        return _block_node_to_string(node, depth, config=config, be_compact=be_compact)

    # Scalar node
    val = node.get('val')
    cm_inline = node.get('_cm_inline', "")
    if cm_inline and not cm_inline[0].isspace():
        cm_inline = " " + cm_inline
    if val is None:
        return f"{indent}{key}{cm_inline}"
    op_str = f" {op}" if op else ""
    return f"{indent}{key}{op_str} {val}{cm_inline}"


def _block_node_to_string(node, depth, *, config, be_compact=False):
    """Format a block node (one with children in a list)."""
    indent = "\t" * depth
    key = node.get('key')
    op = node.get('op')
    children = node['val']
    cm_open = node.get('_cm_open', "")
    cm_close = node.get('_cm_close', "")

    # Try compact rendering
    is_compactable = False
    if (not config.no_compact and not be_compact and depth and
            (depth > 1 or key.endswith(COMPACT_SUFFIXES)) and
            not key.endswith(NON_COMPACT_SUFFIXES)):
        is_compactable = should_be_compact(node, config)

    if be_compact or is_compactable:
        result = _try_compact_render(node, children, depth, config, be_compact, cm_close)
        if result is not None:
            return result

    # Expanded rendering
    mid_key_str = f" {node.get('mid_key')}" if node.get('mid_key') else ""
    op_str = f" {op}" if op else ""
    val_key_str = f" {node.get('val_key')}" if node.get('val_key') else ""

    # GUI 'types' declarations need brace on new line
    if key == 'types' and val_key_str and not op:
        lines = [f"{indent}{key}{val_key_str}", f"{indent}{{{cm_open}"]
    else:
        lines = [f"{indent}{key}{mid_key_str}{op_str}{val_key_str} {{{cm_open}"]

    prev_was_header = False
    prev_was_comment = False
    prev_is_block = False
    prev_is_expanded = False

    for i, child in enumerate(children):
        is_comment = child.get('type') == 'comment'
        is_block = isinstance(child.get('val'), list)
        child_key = child.get('key')
        is_expanded = _is_expanded_block(child, depth, config) if is_block else False
        comment_is_header = is_comment and child.get('val', '').startswith('##')

        if _should_add_blank_within_block(
            child, i, children, depth, config,
            prev_is_expanded, prev_is_block,
            prev_was_comment, prev_was_header,
            is_comment, is_expanded, is_block,
            comment_is_header, child_key,
        ):
            lines.append("")

        lines.append(node_to_string(child, depth + 1, config=config))
        prev_was_header = comment_is_header
        prev_was_comment = is_comment
        prev_is_block = is_block
        prev_is_expanded = is_expanded

    lines.append(f"{indent}}}{cm_close}")
    formatted_str = "\n".join(lines)

    # For switch blocks, use raw text if it's more compact
    if node.get('_raw') and node.get('key') == 'switch':
        raw_val = node['_raw']
        if raw_val.count('\n') < formatted_str.count('\n'):
            content = raw_val.rstrip().rstrip('}').rstrip()
            return f"{indent}{content}\n{indent}}}"

    return formatted_str


def _try_compact_render(node, children, depth, config, be_compact, cm_close):
    """Try to render a block node as a single compact line. Returns string or None."""
    indent = "\t" * depth
    key = node.get('key')
    op = node.get('op')
    child_strs = []
    is_compactable = True

    for c in children:
        if not be_compact and not cm_close:
            if c.get('_cm_inline'):
                cm_close = c.get('_cm_inline', '')
                del c['_cm_inline']
            elif c.get('_cm_close'):
                cm_close = c.get('_cm_close', '')
                del c['_cm_close']
        elif (be_compact or not cm_close) and (c.get('_cm_inline') or c.get('_cm_close')):
            is_compactable = False
            break
        if is_compactable:
            s = node_to_string(c, depth=-1, config=config, be_compact=True)
            child_strs.append(s)

    if not is_compactable:
        return None

    joined = " ".join(child_strs)
    mid_key_str = f" {node.get('mid_key')}" if node.get('mid_key') else ""
    op_str = f" {op}" if op else ""
    val_key_str = f" {node.get('val_key')}" if node.get('val_key') else ""
    return f"{indent}{key}{mid_key_str}{op_str}{val_key_str} {{ {joined} }}{cm_close}"


def block_to_string(block_list, config):
    """Convert a top-level AST (list of nodes) to formatted text."""
    lines = []
    prev_was_header = False
    prev_was_comment = False
    prev_is_block = False
    i = 0

    for node in block_list:
        is_comment = node['type'] == 'comment'
        comment_is_header = False
        is_var = False
        key = None
        is_block = False

        if is_comment:
            comment_text = node['val'][1:]
            comment_is_header = comment_text.startswith(('#', '}', ' }'))
        else:
            if node['type'] == 'node':
                is_block = isinstance(node['val'], list)
                key = node.get('key', '')
                if key and not is_block and key.startswith('@'):
                    is_var = True
            elif node['type'] == 'raw_block':
                is_block = True

        add_space = (
            (not is_comment and not is_var and
             (not prev_was_comment or prev_was_header or is_block)) or
            (comment_is_header and not prev_was_comment and i) or
            (is_comment and prev_is_block)
        )
        # Preserve user's intentional blank lines
        if not add_space and i and node.get('_blank_before'):
            add_space = True
        if add_space:
            count = config.block_spacing if prev_is_block else 1
            lines.extend([""] * count)

        i += 1
        prev_was_header = comment_is_header
        prev_was_comment = is_comment
        prev_is_block = is_block

        cm_open = node.get('_cm_open')
        node_to_print = node
        if node['type'] == 'node' and is_block and cm_open:
            lines.append(cm_open.strip())
            node_to_print = node.copy()
            del node_to_print['_cm_open']

        lines.append(node_to_string(node_to_print, depth=0, config=config))

    return "\n".join(lines)
