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
import re

from .tokens import tokenize, Token
from .registry import COMMANDS, ENVIRONMENTS


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0
        self.last_tok: Token | None = None
        self.tree: list = []
        self.stack = [{'node': self.tree, 'context': 'root', 'closer': None, 'opened_at': None}] # AST inicial

    @property
    def frame(self):
        return self.stack[-1]

    # ── Utilidades de lectura ─────────────────────────────────────────────

    def _at(self) -> str:
        """Devuelve la posición del último token consumido para mensajes de error."""
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

    def _consume_brace_block(self, node: dict, context: str, inline_only: bool = False):
        """Consume un bloque {…} sincrónicamente (espera a que cierre)."""
        self.expect('OPEN_BRACE')
        frame = {'node': node, 'context': context, 'closer': '}', 'opened_at': self.last_tok}
        if inline_only:
            frame['inline_only'] = True
        self.stack.append(frame)
        depth = len(self.stack) # Variable local por llamada, cada invocacion tiene profundidad
        while self.pos < len(self.tokens) and len(self.stack) >= depth:
            # len(stack)-1 cuando cierra } -> stack.pop, condicion local de salida
            self._step()

    def _consume_opt_arg(self) -> str | None:
        """Intenta consumir un argumento opcional [...]. Devuelve el texto o None."""
        self.skip_whitespace()
        if self.pos >= len(self.tokens):
            return None
        if self.tokens[self.pos][0] != 'OPEN_BRACKET':
            return None

        self.pos += 1  # consume [
        parts = []
        while self.pos < len(self.tokens):
            kind, value, line, col = self.tokens[self.pos]
            if kind == 'CLOSE_BRACKET':
                self.pos += 1
                return ''.join(parts).strip()
            parts.append(value)
            self.pos += 1

        raise SyntaxError("Fin de archivo: falta ]")

    def _consume_raw_brace(self) -> str:
        """Consume un bloque {…} y devuelve su contenido como texto plano."""
        self.expect('OPEN_BRACE')
        parts = []
        depth = 1
        while self.pos < len(self.tokens) and depth > 0:
            kind, value, linea, col = self.tokens[self.pos]
            if kind == 'OPEN_BRACE':
                depth += 1
            elif kind == 'CLOSE_BRACE':
                depth -= 1
                if depth == 0:
                    self.pos += 1
                    break
            parts.append(value)
            self.pos += 1
        return ''.join(parts).strip()

    # ── Handlers por tipo de token ────────────────────────────────────────

    def _skip_brace_args(self):
        """Consume bloques {…} que siguen a un comando desconocido."""
        while True:
            pos = self.pos
            while pos < len(self.tokens) and self.tokens[pos].kind == 'WHITESPACE':
                pos += 1
            if pos >= len(self.tokens) or self.tokens[pos].kind != 'OPEN_BRACE':
                break
            self.pos = pos + 1
            depth = 1
            while self.pos < len(self.tokens) and depth > 0:
                kind = self.tokens[self.pos].kind
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
        # ── Casos especiales, irrumpimos el proceso ──
        if cmd == '\\begin':
            self.on_begin()
            return
        if cmd == '\\end':
            self.on_end()
            return
        if cmd == '\\item':
            self._on_item()
            return

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

        # ── Args como texto plano (no se parsean recursivamente) ──
        if props.get('raw_args'):
            node = {'kind': props['produces']}
            node.update(props.get('extra', {}))

            opt_count = props.get('opt_args', 0)
            for _ in range(opt_count):
                opt = self._consume_opt_arg()
                if opt is not None:
                    if 'options' not in node:
                        node['options'] = []
                    node['options'].append(opt)

            total_args = props.get('args', 0)
            if total_args > 0:
                node['params'] = []
            for _ in range(total_args):
                node['params'].append(self._consume_raw_brace())

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

        # ── Consumir argumentos opcionales [...]  ──
        opt_count = props.get('opt_args', 0)
        for _ in range(opt_count):
            opt = self._consume_opt_arg()
            if opt is not None:
                if 'options' not in node:
                    node['options'] = []
                node['options'].append(opt)

        self.add_node(node)

        # ── Consumir argumentos: primero params, luego content ──
        for _ in range(param_args):
            self._consume_brace_block(node, 'parameter')

        inline_only = props.get('inline_only', False)
        for _ in range(content_args):
            self._consume_brace_block(node, 'content', inline_only=inline_only)

    def on_begin(self):
        """Handler para \\begin{nombre}. Abre un environment."""
        if self.frame.get('inline_only'):
            raise SyntaxError(f"Environments no permitidos en este contexto{self._at()}")

        begin_tok = self.last_tok  # Token del \begin, antes de consumir argumentos
        self.expect('OPEN_BRACE')
        name = self.expect('TEXT') # Nombre del nodo
        self.expect('CLOSE_BRACE')

        props = ENVIRONMENTS.get(name)
        if props is None:
            print(f"Warning: environment desconocido '{name}'", file=sys.stderr)
            return

        # ── Environment con contenido raw (equation, etc.) ──
        if props.get('raw'):
            raw = self._collect_until_end(name)
            node = {'kind': props['produces']}
            node.update(props.get('extra', {}))
            node['raw'] = raw
            self.add_node(node)
            return

        # ── Environment con contenido parseado (enumerate, etc.) ──
        node = {'kind': props['produces']}
        node.update(props.get('extra', {}))
        node['content'] = []

        self.add_node(node)
        self.stack.append({'node': node, 'context': 'content', 'closer': '\\end{' + name + '}', 'opened_at': begin_tok})

    def on_end(self):
        """Handler para \\end{nombre}. Cierra el environment."""
        self.expect('OPEN_BRACE')
        name = self.expect('TEXT')
        self.expect('CLOSE_BRACE')

        expected_closer = '\\end{' + name + '}'

        # Si hay un \item abierto, cerrarlo
        if len(self.stack) > 1 and self.frame.get('context') == 'item':
            self.stack.pop()

        if len(self.stack) <= 1:
            raise SyntaxError(f"\\end{{{name}}} sin \\begin correspondiente{self._at()}")
        if self.frame['closer'] != expected_closer:
            raise SyntaxError(f"Se esperaba {self.frame['closer']}, se encontró {expected_closer}{self._at()}")
        self.stack.pop()

    def _on_item(self):
        """Handler para \\item. Cierra el item anterior si existe."""
        # Cierre implícito: si ya hay un item abierto, cerrarlo
        if len(self.stack) > 1 and self.frame.get('context') == 'item':
            self.stack.pop()

        node = {'kind': 'item', 'content': []}
        self.add_node(node)
        self.stack.append({'node': node, 'context': 'item', 'closer': None})

    def on_math(self, opener: str):
        mode = 'display' if opener == '$$' else 'inline'
        if mode == 'display' and self.frame.get('inline_only'):
            raise SyntaxError(f"Math display ($$) no permitido en este contexto{self._at()}")
        raw = self._collect_math(opener)
        self.add_node({'kind': 'math', 'mode': mode, 'raw': raw})

    def on_close(self, closer: str):
        if len(self.stack) <= 1:
            raise SyntaxError(f"'{closer}' inesperado: no hay bloque abierto{self._at()}")
        if self.frame['closer'] != closer:
            raise SyntaxError(f"Se esperaba '{self.frame['closer']}', se encontró '{closer}'{self._at()}")
        self.stack.pop()

    def on_text(self, value: str):
        if self.frame['context'] == 'parameter':
            self.frame['node']['params'].append(value.strip())
        else:
            self.add_node(value)

    # ── Recolección de math ─────────────────────────────────────────
    def _collect_math(self, closer: str) -> str:
        """Recolecta el LaTeX crudo dentro de $...$ o $$...$$"""
        parts = []
        while self.pos < len(self.tokens):
            tok = self.tokens[self.pos]
            is_end = (tok.kind == 'MATH_BLOCK' and closer == '$$') or \
                     (tok.kind == 'MATH_INLINE' and closer == '$')
            if is_end:
                self.pos += 1
                break
            parts.append(tok.value)
            self.pos += 1
        return ''.join(parts).strip()

    def _collect_until_end(self, name: str) -> str:
        """Recolecta contenido raw hasta \\end{nombre}."""
        parts = []
        while self.pos < len(self.tokens):
            tok = self.tokens[self.pos]

            # ¿Es \end?
            if tok.kind == 'COMMAND' and tok.value == '\\end':
                # Verificar que sea \end{name}
                save_pos = self.pos
                self.pos += 1
                try:
                    self.expect('OPEN_BRACE')
                    end_name = self.expect('TEXT') # Nombre del entorno
                    self.expect('CLOSE_BRACE')
                    if end_name == name:
                        return ''.join(parts).strip()
                except SyntaxError:
                    pass
                # No era el \end correcto, restaurar y seguir
                parts.append(tok.value)
                self.pos = save_pos + 1
                continue

            parts.append(tok.value)
            self.pos += 1

        raise SyntaxError(f"Fin de archivo: falta \\end{{{name}}}{self._at()}")

    # ── Loop principal ────────────────────────────────────────────────────

    def _step(self):
        tok = self.consume()
        match tok.kind:
            case 'COMMAND':                          self.on_command(tok.value)
            case 'MATH_BLOCK':                       self.on_math('$$')
            case 'MATH_INLINE':                      self.on_math('$')
            case 'CLOSE_BRACE' | 'CLOSE_BRACKET':    self.on_close(tok.value)
            case 'PARAGRAPH':                        self.add_node({'kind': 'paragraph'})
            case 'DOUBLE_BACKSLASH':                 self.add_node({'kind': 'newline'})
            case 'ESCAPED_CHAR':                     self.add_node(tok.value)
            case 'OPEN_BRACE' | 'OPEN_BRACKET':
                raise SyntaxError(f"'{tok.value}' inesperado sin comando previo{self._at()}")
            case 'TEXT':                             self.on_text(tok.value)
            # WHITESPACE: ignorado a nivel estructural

    def run(self) -> list:
        while self.pos < len(self.tokens):
            self._step()
        if len(self.stack) > 1:
            # Buscar el frame sin cerrar más relevante (ignorar \item que cierra implícitamente)
            frame = next((f for f in reversed(self.stack[1:]) if f['closer'] is not None), self.stack[-1])
            closer = frame['closer']
            opened_at = frame.get('opened_at')
            loc = f" (línea {opened_at.line}, columna {opened_at.col})" if opened_at else ""
            raise SyntaxError(f"Fin de archivo: falta cerrar '{closer}', abierto{loc}")
        return self.tree


# ── API pública ───────────────────────────────────────────────────────────

def compile_tex(src: str) -> list:
    """Recibe código LaTeX y devuelve el AST como lista de nodos."""
    src = re.sub(r'(?<!\\)%.*', '', src)
    return Parser(tokenize(src)).run()




