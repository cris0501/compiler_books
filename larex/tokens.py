"""
Análisis léxico (scanner).

Convierte un string de LaTeX en una lista de tokens (tipo, valor).
Cada token es una tupla ('TIPO', 'valor_original').

El tokenizer NO sabe de semántica: no distingue entre un comando
conocido y uno desconocido. Eso lo decide el parser consultando
el registry.
"""

import re

TOKEN_SPECS = [
    ('MATH_BLOCK',    r'\$\$'),           # $$ antes que $ (longest match manual)
    ('MATH_INLINE',   r'\$'),
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


def tokenize(src: str) -> list[tuple[str, str]]:
    """
    Recibe código LaTeX crudo y devuelve una lista de tokens.

    >>> tokenize(r"\\textbf{hola}")
    [('COMMAND', '\\\\textbf'), ('OPEN_BRACE', '{'), ('TEXT', 'hola'), ('CLOSE_BRACE', '}')]
    """
    return [(m.lastgroup, m.group()) for m in _MASTER_RE.finditer(src)]


