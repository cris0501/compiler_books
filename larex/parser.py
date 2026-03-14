"""
Parser principal. Dispatch loop + estado del AST.

Delega toda la lógica semántica a los handlers.
"""

import re

from .tokens import tokenize, Token
from .handlers import (
    handle_command, handle_begin, handle_end,
    handle_math, handle_item, handle_label, handle_ref,
)


class Parser:

    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0
        self.last_tok: Token | None = None
        self.tree: list = []
        self.stack = [{'node': self.tree, 'context': 'root', 'closer': None, 'opened_at': None}]
        self.refs = {}
        self.label_counter = 0

    @property
    def frame(self):
        return self.stack[-1]

    # ── Utilidades de lectura ──

    def _at(self) -> str:
        if self.last_tok is not None:
            return f" (línea {self.last_tok.line}, columna {self.last_tok.col})"
        return ""

    def consume(self) -> Token:
        tok = self.tokens[self.pos]
        self.last_tok = tok
        self.pos += 1
        return tok

    def skip_whitespace(self):
        while self.pos < len(self.tokens) and self.tokens[self.pos].kind == 'WHITESPACE':
            self.pos += 1

    def expect(self, kind: str) -> str:
        self.skip_whitespace()
        if self.pos >= len(self.tokens):
            raise SyntaxError(f"Fin de archivo inesperado, se esperaba {kind}{self._at()}")
        tok = self.consume()
        if tok.kind != kind:
            raise SyntaxError(f"Se esperaba {kind}, se encontró {tok.kind!r} ({tok.value!r}){self._at()}")
        return tok.value

    # ── AST ──

    def target(self) -> list:
        node = self.frame['node']
        return node if isinstance(node, list) else node['content']

    def add_node(self, node):
        target = self.target()
        if isinstance(node, str):
            text = node.strip()
            if not text:
                return
            if target and isinstance(target[-1], str):
                target[-1] += ' ' + text
            else:
                target.append(text)
        else:
            target.append(node)

    # ── Dispatch ──

    def _dispatch_command(self, cmd: str):
        match cmd:
            case '\\begin':  handle_begin(self)
            case '\\end':    handle_end(self)
            case '\\item':   handle_item(self)
            case '\\label':  handle_label(self)
            case '\\ref':    handle_ref(self)
            case _:          handle_command(self, cmd)

    def step(self):
        tok = self.consume()
        match tok.kind:
            case 'COMMAND':           self._dispatch_command(tok.value)
            case 'MATH_BLOCK':        handle_math(self, '$$')
            case 'MATH_INLINE':       handle_math(self, '$')
            case 'CLOSE_BRACE' | 'CLOSE_BRACKET':
                if len(self.stack) <= 1:
                    raise SyntaxError(f"'{tok.value}' inesperado: no hay bloque abierto{self._at()}")
                if self.frame['closer'] != tok.value:
                    raise SyntaxError(f"Se esperaba '{self.frame['closer']}', se encontró '{tok.value}'{self._at()}")
                self.stack.pop()
            case 'PARAGRAPH':         self.add_node({'kind': 'paragraph'})
            case 'DOUBLE_BACKSLASH':  self.add_node({'kind': 'newline'})
            case 'ESCAPED_CHAR':      self.add_node(tok.value)
            case 'OPEN_BRACE' | 'OPEN_BRACKET':
                raise SyntaxError(f"'{tok.value}' inesperado sin comando previo{self._at()}")
            case 'TEXT':
                if self.frame['context'] == 'parameter':
                    self.frame['node']['params'].append(tok.value.strip())
                else:
                    self.add_node(tok.value)

    def run(self) -> list:
        while self.pos < len(self.tokens):
            self.step()
        if len(self.stack) > 1: # Bloque abierto
            frame = next(
                (f for f in reversed(self.stack[1:]) if f['closer'] is not None),
                self.stack[-1],
            )
            closer = frame['closer']
            opened_at = frame.get('opened_at')
            loc = f" (línea {opened_at.line}, columna {opened_at.col})" if opened_at else ""
            raise SyntaxError(f"Fin de archivo: falta cerrar '{closer}', abierto{loc}")
        return self.tree


def compile_tex(src: str) -> dict:
    src = re.sub(r'(?<!\\)%.*', '', src)
    parser = Parser(tokenize(src))
    tree = parser.run()
    return {'content': tree, 'refs': parser.refs}

