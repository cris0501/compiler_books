"""
Análisis sintáctico.

Consume tokens (de tokens.py) y, usando las definiciones del
registry, construye un AST representado como lista de nodos JSON.

Arquitectura:
  - self.tree   → la raíz del AST (lista de nodos)
  - self.stack  → pila de frames {node, context, closer}
                  cada frame apunta al nodo padre actual
                  lo que le confiere contexto
  - self.frame  → el frame en el tope de la pila

La pila permite que cada nodo sepa quién es su padre sin
preocuparse por sus hermanos. El padre determina qué puede
contener: por ejemplo, dentro de math no se abre otro math.
"""

import sys

from .tokens import tokenize
from .registry import COMMANDS


class Parser:
    def __init__(self, tokens: list[tuple[str, str]]):
        self.tokens = tokens
        self.pos = 0
        self.tree: list = []
        # Cada frame: {node, context ('root'|'content'|'parameter'), closer}
        self.stack = [{'node': self.tree, 'context': 'root', 'closer': None}]

    @property
    def frame(self):
        return self.stack[-1]

    # ── Utilidades de lectura ─────────────────────────────────────────────

    def consume(self) -> tuple[str, str]:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def skip_whitespace(self):
        while self.pos < len(self.tokens) and self.tokens[self.pos][0] == 'WHITESPACE':
            self.pos += 1

    def expect(self, kind: str) -> str:
        self.skip_whitespace()
        if self.pos >= len(self.tokens):
            raise SyntaxError(f"Fin de archivo inesperado, se esperaba {kind}")
        tok_kind, tok_val = self.consume()
        if tok_kind != kind:
            raise SyntaxError(f"Se esperaba {kind}, se encontró {tok_kind!r} ({tok_val!r})")
        return tok_val

    # ── Inserción en el AST ───────────────────────────────────────────────

    def target(self) -> list:
        """Devuelve la lista donde insertar el próximo nodo hijo."""
        node = self.frame['node']
        return node if isinstance(node, list) else node['content']

    def add_node(self, node):
        target = self.target()
        if isinstance(node, str):
            text = node.strip()
            if not text:
                return
            # Texto consecutivo se fusiona en un solo string
            if target and isinstance(target[-1], str):
                target[-1] += ' ' + text
            else:
                target.append(text)
        else:
            target.append(node)

    # ── Handlers por tipo de token ────────────────────────────────────────

    def _skip_brace_args(self):
        """Consume bloques {…} que siguen a un comando desconocido."""
        while True:
            pos = self.pos
            while pos < len(self.tokens) and self.tokens[pos][0] == 'WHITESPACE':
                pos += 1
            if pos >= len(self.tokens) or self.tokens[pos][0] != 'OPEN_BRACE':
                break
            self.pos = pos + 1
            depth = 1
            while self.pos < len(self.tokens) and depth > 0:
                kind, _ = self.tokens[self.pos]
                if kind == 'OPEN_BRACE':
                    depth += 1
                elif kind == 'CLOSE_BRACE':
                    depth -= 1
                self.pos += 1

    def on_command(self, cmd: str):
        props = COMMANDS.get(cmd)
        if props is None:
            print(f"Warning: comando desconocido '{cmd}'", file=sys.stderr)
            self._skip_brace_args()
            return

        if props.get('self_closing'):
            self.add_node({'type': props['type'], 'name': props['name']})
            return

        new_node = {'type': props['type'], 'name': props['name'], 'content': []}
        if props['params']:
            new_node['parameters'] = []

        self.add_node(new_node)

        # Bloque de parámetros (ej: \def{param}{content})
        if props['params']:
            self.expect('OPEN_BRACE')
            self.stack.append({'node': new_node, 'context': 'parameter', 'closer': '}'})
            depth = len(self.stack)
            while self.pos < len(self.tokens) and len(self.stack) >= depth:
                self._step()

        # Bloque de contenido
        self.expect('OPEN_BRACE')
        self.stack.append({'node': new_node, 'context': 'content', 'closer': '}'})

    def on_math(self, opener: str):
        mode = 'block' if opener == '$$' else 'inline'
        raw = self._collect_math(opener)
        self.add_node({'type': mode, 'name': 'math', 'content': raw})

    def on_close(self, closer: str):
        if len(self.stack) <= 1:
            raise SyntaxError(f"'{closer}' inesperado: no hay bloque abierto")
        if self.frame['closer'] != closer:
            raise SyntaxError(f"Se esperaba '{self.frame['closer']}', se encontró '{closer}'")
        self.stack.pop()

    def on_text(self, value: str):
        if self.frame['context'] == 'parameter':
            self.frame['node']['parameters'].append(value.strip())
        else:
            self.add_node(value)

    # ── Recolección de math crudo ─────────────────────────────────────────

    def _collect_math(self, closer: str) -> str:
        """Recolecta el LaTeX crudo dentro de $...$ o $$...$$"""
        parts = []
        while self.pos < len(self.tokens):
            kind, value = self.tokens[self.pos]
            is_end = (kind == 'MATH_BLOCK' and closer == '$$') or \
                     (kind == 'MATH_INLINE' and closer == '$')
            if is_end:
                self.pos += 1
                break
            parts.append(value)
            self.pos += 1
        return ''.join(parts).strip()

    # ── Loop principal ────────────────────────────────────────────────────

    def _step(self):
        kind, value = self.consume()
        match kind:
            case 'COMMAND':                         self.on_command(value)
            case 'MATH_BLOCK':                      self.on_math('$$')
            case 'MATH_INLINE':                     self.on_math('$')
            case 'CLOSE_BRACE' | 'CLOSE_BRACKET':   self.on_close(value)
            case 'OPEN_BRACE' | 'OPEN_BRACKET':
                raise SyntaxError(f"'{value}' inesperado sin comando previo")
            case 'TEXT':                            self.on_text(value)
            # WHITESPACE: ignorado a nivel estructural

    def run(self) -> list:
        while self.pos < len(self.tokens):
            self._step()
        if len(self.stack) > 1:
            raise SyntaxError("Fin de archivo: bloque sin cerrar")
        return self.tree


# ── API pública ───────────────────────────────────────────────────────────

def compile_tex(src: str) -> list:
    """Recibe código LaTeX y devuelve el AST como lista de nodos."""
    return Parser(tokenize(src)).run()

