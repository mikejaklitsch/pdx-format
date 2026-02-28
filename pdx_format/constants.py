"""Keyword sets and constant tuples for PDX script formatting."""

RAW_BLOCKS = ('in_breach_of', 'inverted_switch')

KEYWORDS_TO_LOWER_START = ('ROOT.', 'PREV.', 'FROM.', 'OWNER.', 'CONTROLLER.')
KEYWORDS_TO_LOWER_END = ('.ROOT', '.PREV', '.FROM', '.OWNER', '.CONTROLLER')
KEYWORDS_TO_LOWER = (
    'ROOT', 'PREV', 'FROMFROM', 'FROMFROMFROM', 'FROMFROMFROMFROM', 'THIS',
    'Owner', 'Controller', "From", "FromFrom", "Root", "Prev", 'BREAK', 'CONTINUE'
)
VAL_KEYWORDS_TO_LOWER = KEYWORDS_TO_LOWER + ('Yes', 'No', 'YES', 'NO', 'FROM', "From")
KEYWORDS_TO_LOWER_LIST = KEYWORDS_TO_LOWER + (
    'FROM', 'OWNER', 'EFFECT', 'TRIGGER', 'SWITCH', 'IF', 'ELSE', 'ELSE_IF', 'LIMIT', 'WHILE'
)

KEYWORDS_TO_UPPER = {'OR', 'NOR', 'NAND', 'NOT', 'AND'}
NON_NEGATABLE_SCOPES = ('if', 'else_if', 'else', 'while', 'switch', 'calc_true_if')

COMPACT_SUFFIXES = ('_trigger', '_condition', '_weight', '_score', '_mult', '_factor')
NON_COMPACT_SUFFIXES = ('potential', 'allow', 'effect')

BOM_ONLY_EXTENSIONS = {'.yml', '.yaml'}
