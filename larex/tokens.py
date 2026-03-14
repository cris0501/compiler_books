"""
Análisis léxico (scanner).

Convierte un string de LaTeX en una lista de tokens.
Cada token es un Token(kind, value, line, col).

El tokenizer NO sabe de semántica: no distingue entre un comando
conocido y uno desconocido. Eso lo decide el parser consultando
el registry.
"""

import re
from typing import NamedTuple


class Token(NamedTuple):
    kind: str
    value: str
    line: int
    col: int

TOKEN_SPECS = [
    ('MATH_BLOCK',    r'\$\$'),           # $$ antes que $ (longest match manual)
    ('MATH_INLINE',   r'\$'),
    ('DOUBLE_BACKSLASH', r'\\\\'),        # Nueva linea
    ('ESCAPED_CHAR',     r'\\[{}$%&#_]'), # \{ \} \$ \% etc.
    ('COMMAND',       r'\\[a-zA-Z]+'),    # \section, \textbf, \newline ...
    ('OPEN_BRACE',    r'\{'),
    ('CLOSE_BRACE',   r'\}'),
    ('OPEN_BRACKET',  r'\['),
    ('CLOSE_BRACKET', r'\]'),
    ('PARAGRAPH',     r'\n[ \t]*\n'),
    ('WHITESPACE',    r'[ \t\n]+'),
    ('TEXT',          r'[^\\$\{\}\[\]\s]+'),
]

_MASTER_RE = re.compile(
    '|'.join(f'(?P<{name}>{pat})' for name, pat in TOKEN_SPECS)
)


def tokenize(src: str) -> list[Token]:
    """
    Recibe código LaTeX crudo y devuelve una lista de tokens con posición.

    >>> [(t.kind, t.value) for t in tokenize(r"\\textbf{hola}")]
    [('COMMAND', '\\\\textbf'), ('OPEN_BRACE', '{'), ('TEXT', 'hola'), ('CLOSE_BRACE', '}')]
    """
    tokens = []
    for m in _MASTER_RE.finditer(src):
        start = m.start()
        line = src.count('\n', 0, start) + 1
        col = start - src.rfind('\n', 0, start)  # rfind devuelve -1 si no hay \n → col = start+1
        tokens.append(Token(m.lastgroup, m.group(), line, col))
    return tokens

