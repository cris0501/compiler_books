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
from .consume import _resolve_includes


class Parser:

    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0
        self.last_tok: Token | None = None
        self.tree: list = []
        self.stack = [{'node': self.tree, 'context': 'root', 'closer': None, 'opened_at': None}]
        self.refs = {}
        self.label_counter = 0
        self.chapters = {}
        self.chapter_counter = 0

    @property
    def frame(self):
        return self.stack[-1]

    # -- Utilidades de lectura --

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

    # -- AST --

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
                sep = '' if target[-1].endswith(' ') else ' '
                target[-1] += sep + text
            else:
                target.append(text)
        else:
            target.append(node)

    # -- Dispatch --

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
            case 'COMMAND':                          self._dispatch_command(tok.value)
            case 'MATH_BLOCK':                       handle_math(self, '$$')
            case 'MATH_INLINE':                      handle_math(self, '$')
            case 'DISPLAY_MATH_OPEN':                handle_math(self, '\\[')
            case 'DISPLAY_MATH_CLOSE':               pass
            case 'PARAGRAPH':                        self.add_node({'kind': 'paragraph'})
            case 'DOUBLE_BACKSLASH':                 self.add_node({'kind': 'newline'})
            case 'ESCAPED_CHAR':                     self.add_node(tok.value[1])
            case 'OPEN_BRACKET' | 'CLOSE_BRACKET':   self.add_node(tok.value)
            case 'WHITESPACE':
                target = self.target()
                if target:
                    if isinstance(target[-1], str):
                        if not target[-1].endswith(' '):
                            target[-1] += ' '
                    elif isinstance(target[-1], dict):
                        target.append(' ')
            case 'CLOSE_BRACE':
                if len(self.stack) <= 1:
                    raise SyntaxError(f"'{tok.value}' inesperado: no hay bloque abierto{self._at()}")
                if self.frame['closer'] != tok.value:
                    raise SyntaxError(f"Se esperaba '{self.frame['closer']}', se encontró '{tok.value}'{self._at()}")
                self.stack.pop()
            case 'OPEN_BRACE':
                node = {'kind': 'group', 'content': []}
                self.add_node(node)
                self.stack.append({'node': node, 'context': 'content', 'closer': '}'})
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


def compile_tex(src: str, base_path: str = '.') -> dict:
    """ Funcion inicial """
    src = _resolve_includes(src, base_path)
    src = re.sub(r'(?<!\\)%.*', '', src)

    preamble, body = _split_document(src)
    meta = _parse_preamble(preamble)

    parser = Parser(tokenize(body))
    tree = parser.run()

    result = {'content': tree}
    if parser.refs:
        result['refs'] = parser.refs
    if parser.chapters:
        result['chapters'] = parser.chapters
    if meta:
        result['meta'] = meta
    return result

def _split_document(src: str) -> tuple[str, str]:
    """ Separa preámbulo y cuerpo del documento """
    begin = re.search(r'\\begin\{document\}', src)
    end = re.search(r'\\end\{document\}', src)

    if begin and end:
        preamble = src[:begin.start()]
        body = src[begin.end():end.start()]
        return preamble, body

    # Sin \begin{document}: todo es cuerpo (compatibilidad con tex simples)
    return '', src


def _parse_preamble(preamble: str) -> dict:
    """ Extrae metadata del preámbulo """
    if not preamble:
        return {}

    meta = {}

    # documentclass
    dc = re.search(r'\\documentclass(?:\[([^\]]*)\])?\{([^}]+)\}', preamble)
    if dc:
        meta['documentclass'] = dc.group(2)
        if dc.group(1):
            meta['documentclass_options'] = dc.group(1)

    # usepackage
    packages = re.findall(r'\\usepackage(?:\[([^\]]*)\])?\{([^}]+)\}', preamble)
    if packages:
        meta['dependencies'] = []
        for opts, name in packages:
            dep = {'name': name}
            if opts:
                dep['options'] = opts
            meta['dependencies'].append(dep)

    return meta
