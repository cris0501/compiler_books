import re
import sys
import json

# ─── 1. Tokenizer ────────────────────────────────────────────────────────────

TOKEN_SPECS = [
    ('MATH_BLOCK',    r'\$\$'),          # $$ antes que $ para que matchee primero
    ('MATH_INLINE',   r'\$'),
    ('COMMAND',       r'\\[a-zA-Z]+'),   # \section, \def, \newline ...
    ('OPEN_BRACE',    r'\{'),
    ('CLOSE_BRACE',   r'\}'),
    ('OPEN_BRACKET',  r'\['),
    ('CLOSE_BRACKET', r'\]'),
    ('WHITESPACE',    r'[ \t\n]+'),
    ('TEXT',          r'[^\\$\{\}\[\]\s]+'),
]

MASTER_RE = re.compile(
    '|'.join(f'(?P<{name}>{pat})' for name, pat in TOKEN_SPECS)
)

def tokenize(src: str) -> list[tuple[str, str]]:
    return [(m.lastgroup, m.group()) for m in MASTER_RE.finditer(src)]


# ─── 2. Registro de comandos ─────────────────────────────────────────────────
# Para agregar un comando nuevo: solo añadir una entrada aquí.

COMMANDS = {
    '\\section':    {'name': 'section',    'type': 'block',  'params': False},
    '\\subsection': {'name': 'subsection', 'type': 'block',  'params': False},
    '\\def':        {'name': 'definition', 'type': 'inline', 'params': True},
    '\\textbf':     {'name': 'bold',       'type': 'inline', 'params': False},
    '\\textit':     {'name': 'italic',     'type': 'inline', 'params': False},
    '\\newline':    {'name': 'newline',    'type': 'inline', 'params': False, 'self_closing': True},
    '\\n':          {'name': 'newline',    'type': 'inline', 'params': False, 'self_closing': True},
}


# ─── 3. Parser ───────────────────────────────────────────────────────────────

class Parser:
    def __init__(self, tokens: list[tuple[str, str]]):
        self.tokens = tokens
        self.pos = 0
        self.tree: list = []
        # Cada frame: {node, context ('root'|'content'|'parameter'), closer}
        self.stack = [{'node': self.tree, 'context': 'root', 'closer': None}]

    @property
    def frame(self): return self.stack[-1]

    def consume(self) -> tuple[str, str]:
        tok = self.tokens[self.pos]; self.pos += 1; return tok

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

    def target(self) -> list:
        node = self.frame['node']
        return node if isinstance(node, list) else node['content']

    def add_node(self, node):
        target = self.target()
        if isinstance(node, str):
            text = node.strip()
            if not text: return
            # Texto consecutivo se fusiona en un solo string
            if target and isinstance(target[-1], str):
                target[-1] += ' ' + text
            else:
                target.append(text)
        else:
            target.append(node)

    # ── Handlers ─────────────────────────────────────────────────────────────

    def _skip_brace_args(self):
        """Consume any {…} argument blocks that follow an unknown command."""
        while True:
            pos = self.pos
            while pos < len(self.tokens) and self.tokens[pos][0] == 'WHITESPACE':
                pos += 1
            if pos >= len(self.tokens) or self.tokens[pos][0] != 'OPEN_BRACE':
                break
            self.pos = pos + 1  # skip opening {
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
        type_ = 'block' if opener == '$$' else 'inline'
        # El contenido math se guarda como string crudo (para MathJax/KaTeX)
        raw = self._collect_math(opener)
        self.add_node({'type': type_, 'name': 'math', 'content': raw})

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

    def _collect_math(self, closer: str) -> str:
        """Recolecta el LaTeX crudo dentro de $...$ o $$...$$ """
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

    def _step(self):
        kind, value = self.consume()
        match kind:
            case 'COMMAND':                         self.on_command(value)
            case 'MATH_BLOCK':                      self.on_math('$$')
            case 'MATH_INLINE':                     self.on_math('$')
            case 'CLOSE_BRACE' | 'CLOSE_BRACKET':  self.on_close(value)
            case 'OPEN_BRACE'  | 'OPEN_BRACKET':
                raise SyntaxError(f"'{value}' inesperado sin comando previo")
            case 'TEXT':                            self.on_text(value)
            # WHITESPACE: ignorado a nivel estructural

    def run(self) -> list:
        while self.pos < len(self.tokens):
            self._step()
        if len(self.stack) > 1:
            raise SyntaxError("Fin de archivo: bloque sin cerrar")
        return self.tree


# ─── 4. API pública ───────────────────────────────────────────────────────────

def compile_tex(src: str) -> list:
    return Parser(tokenize(src)).run()


# ─── 5. Transpiler: JSON → LaTeX ─────────────────────────────────────────────

def transpile_json_to_tex(data: dict) -> str:
    def process_content(content):
        if isinstance(content, str):
            return content
        elif isinstance(content, list):
            parts = []
            for i, item in enumerate(content):
                rendered = process_item(item)
                if rendered is not None:
                    if parts:
                        prev = parts[-1]
                        space = needs_space(prev, rendered)
                        if space:
                            parts.append(' ')
                    parts.append(rendered)
            return ''.join(parts)
        return ''
    
    def needs_space(before: str, after: str) -> bool:
        if not before or not after:
            return False
        before = before.rstrip()
        after = after.lstrip()
        if not before or not after:
            return False
        
        b_end = before[-1] if before else ''
        a_start = after[0] if after else ''
        
        if before.endswith('$') and after.startswith('$'):
            return True
        if before.endswith('$$') and after.startswith('$$'):
            return False
        if before.endswith('}') and after.startswith('$'):
            return False
        
        if before.endswith('$') and a_start.isalnum():
            return True
        if b_end.isalnum() and after.startswith('$'):
            return True
        if b_end.isalnum() and a_start.isalnum():
            return True
        if b_end == '}' and a_start.isalnum():
            return True
        
        return False
    
    def process_item(item):
        if isinstance(item, str):
            return item
        
        item_type = item.get('type')
        
        if item_type == 'text':
            return item.get('content', '')
        
        elif item_type == 'equation':
            return f"${item.get('content', '')}$"
        
        elif item_type == 'block_math':
            return f"$${item.get('content', '')}$$"
        
        elif item_type == 'new_line':
            return '\n'
        
        elif item_type == 'note':
            title = process_content(item.get('title', {}).get('content', ''))
            note_content = process_content(item.get('content', {}).get('content', []))
            return f"\\textbf{{{title}}}: {note_content}"
        
        elif item_type == 'block':
            items = item.get('items', [])
            return '\\begin{itemize}\n' + ''.join(process_item(i) for i in items) + '\\end{itemize}\n'
        
        elif item_type == 'item':
            content = process_content(item.get('content', []))
            return f"\\item {content}\n"
        
        elif item_type == 'image':
            url = item.get('url', {}).get('content', '')
            style = item.get('style', {}).get('content', '100')
            img_content = process_content(item.get('content', {}).get('content', []))
            return f"\\begin{{figure}}[H]\n\\centering\n\\includegraphics[width={style}% ]{{{url}}}\n\\caption{{{img_content}}}\n\\end{{figure}}\n"
        
        elif item_type == 'alert':
            alert_content = process_content(item.get('content', []))
            return f"\\begin{{alert}}\n{alert_content}\\end{{alert}}\n"
        
        elif item_type == 'start':
            return process_content(item.get('content', []))
        
        return None
    
    result = process_content(data.get('content', []))
    
    result = re.sub(r'\$\$([^\n])', r'$$\n\1', result)
    result = re.sub(r'([^\n])\$\$', r'\1\n$$', result)
    result = re.sub(r'\n{3,}', '\n\n', result)
    result = re.sub(r' +\n', '\n', result)
    result = re.sub(r'\n +', '\n', result)
    
    return result.strip()


# ─── 6. CLI ───────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else 'examples/test.tex'
    with open(path) as f:
        result = compile_tex(f.read())
    print(json.dumps(result, indent=2, ensure_ascii=False))
