"""
Análisis sintáctico.

Consume tokens (de tokens.py) y, usando las definiciones del
registry, construye un AST representado como lista de nodos JSON.

Arquitectura:
  - self.tree   → la raíz del AST (lista de nodos)
  - self.stack  → pila de frames {node, context, closer}
                   cada frame apunta al nodo padre actual
  - self.frame  → el frame en el tope de la pila

La pila permite que cada nodo sepa quién es su padre sin
preocuparse por sus hermanos. El padre determina qué puede
contener: por ejemplo, dentro de math no se abre otro math.

Esquema de nodos (el contrato con el frontend):
  Texto:    "string directo" (siempre dentro de un content[])
  Math:     {kind: "math", mode: "inline"|"display", raw: "\\frac{1}{2}"}
  Comando:  {kind: <produces>, content: [...], params?: [...], **extra}
  Newline:  {kind: "newline"}
"""

import sys

from .tokens import tokenize
from .registry import COMMANDS


class Parser:
    def __init__(self, tokens: list[tuple[str, str]]):
        self.tokens = tokens
        self.pos = 0
        self.tree: list = []
        self.stack = [{'node': self.tree, 'context': 'root', 'closer': None}] # AST inicial

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
        node = self.frame['node'] # Ultimo elemento del stack
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

    # ── Consumir bloque sincrónico ────────────────────────────────────────

    def _consume_brace_block(self, node: dict, context: str):
        """Consume un bloque {…} sincrónicamente (espera a que cierre)."""
        self.expect('OPEN_BRACE')
        self.stack.append({'node': node, 'context': context, 'closer': '}'})
        depth = len(self.stack) # Variable local por llamada, cada invocacion tiene profundidad
        while self.pos < len(self.tokens) and len(self.stack) >= depth:
            # len(stack)-1 cuando cierra } -> stack.pop, condicion local de salida
            self._step()

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
        """
        Handler genérico de comandos.

        Lee la definición del registry y actúa en consecuencia:
        no hay ningún if por nombre de comando específico.
        """
        props = COMMANDS.get(cmd)
        if props is None:
            print(f"Warning: comando desconocido '{cmd}'", file=sys.stderr)
            self._skip_brace_args()
            return

        # ── Self-closing (sin argumentos) ──
        if props.get('self_closing'):
            node = {'kind': props['produces']}
            node.update(props.get('extra', {}))
            self.add_node(node)
            return

        # ── Construir el nodo ──
        total_args = props.get('args', 1) # Bloques de argumento {p1}{p2}{content}
        param_args = props.get('param_args', 0) # Argumentos que son parametros
        content_args = total_args - param_args

        node = {'kind': props['produces']}
        node.update(props.get('extra', {}))
        if param_args > 0:
            node['params'] = []
        node['content'] = []

        self.add_node(node)

        # ── Consumir argumentos: primero params, luego content ──
        for _ in range(param_args):
            self._consume_brace_block(node, 'parameter')

        for _ in range(content_args):
            self._consume_brace_block(node, 'content')

    def on_math(self, opener: str):
        mode = 'display' if opener == '$$' else 'inline'
        raw = self._collect_math(opener)
        self.add_node({'kind': 'math', 'mode': mode, 'raw': raw})

    def on_close(self, closer: str):
        if len(self.stack) <= 1:
            raise SyntaxError(f"'{closer}' inesperado: no hay bloque abierto")
        if self.frame['closer'] != closer:
            raise SyntaxError(f"Se esperaba '{self.frame['closer']}', se encontró '{closer}'")
        self.stack.pop()

    def on_text(self, value: str):
        if self.frame['context'] == 'parameter':
            self.frame['node']['params'].append(value.strip())
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
            case 'COMMAND':                          self.on_command(value)
            case 'MATH_BLOCK':                       self.on_math('$$')
            case 'MATH_INLINE':                      self.on_math('$')
            case 'CLOSE_BRACE' | 'CLOSE_BRACKET':   self.on_close(value)
            case 'OPEN_BRACE' | 'OPEN_BRACKET':
                raise SyntaxError(f"'{value}' inesperado sin comando previo")
            case 'TEXT':                             self.on_text(value)
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

