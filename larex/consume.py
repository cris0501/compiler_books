"""
Helpers de consumo de tokens.

Sin semantica, solo lectura mecanica del stream de tokens.
Cada funcion recibe el parser (p) para acceder al stream
y sus utilidades de lectura.
"""
import os
import re
import sys


def consume_brace_block(p, node: dict, context: str, inline_only: bool = False):
    """Consume un bloque {...} y parsea su contenido recursivamente."""
    p.expect('OPEN_BRACE')
    frame = {
        'node': node,
        'context': context,
        'closer': '}',
        'opened_at': p.last_tok,
    }
    if inline_only:
        frame['inline_only'] = True
    p.stack.append(frame)
    depth = len(p.stack)
    while p.pos < len(p.tokens) and len(p.stack) >= depth:
        p.step()


def consume_raw_brace(p) -> str:
    """Consume un bloque {...} y devuelve su contenido como texto plano."""
    p.expect('OPEN_BRACE')
    parts = []
    depth = 1
    while p.pos < len(p.tokens) and depth > 0:
        tok = p.tokens[p.pos]
        if tok.kind == 'OPEN_BRACE':
            depth += 1
        elif tok.kind == 'CLOSE_BRACE':
            depth -= 1
            if depth == 0:
                p.pos += 1
                break
        parts.append(tok.value)
        p.pos += 1
    return ''.join(parts).strip()


def consume_opt_arg(p) -> str | None:
    """Intenta consumir un argumento opcional [...].
    Devuelve el texto o None si no hay [."""
    p.skip_whitespace()
    if p.pos >= len(p.tokens) or p.tokens[p.pos].kind != 'OPEN_BRACKET':
        return None
    p.pos += 1
    parts = []
    while p.pos < len(p.tokens):
        tok = p.tokens[p.pos]
        if tok.kind == 'CLOSE_BRACKET':
            p.pos += 1
            return ''.join(parts).strip()
        parts.append(tok.value)
        p.pos += 1
    raise SyntaxError("Fin de archivo: falta ]")


def consume_env_params(p, default_key: str = 'title') -> dict:
    """Consume un bloque [...] como pares key=value.
    Si no hay ningun =, asigna el contenido a default_key."""
    p.skip_whitespace()
    if p.pos >= len(p.tokens) or p.tokens[p.pos].kind != 'OPEN_BRACKET':
        return {}
    p.pos += 1
    parts = []
    while p.pos < len(p.tokens):
        tok = p.tokens[p.pos]
        if tok.kind == 'CLOSE_BRACKET':
            p.pos += 1
            break
        parts.append(tok.value)
        p.pos += 1
    else:
        raise SyntaxError("Fin de archivo: falta ]")

    raw = ''.join(parts).strip()
    if not raw:
        return {}

    if '=' in raw:
        params = {}
        for pair in raw.split(','):
            pair = pair.strip()
            if not pair:
                continue
            if '=' in pair:
                key, val = pair.split('=', 1)
                params[key.strip()] = val.strip()
            else:
                params[pair] = True
        return params

    return {default_key: raw}


def consume_raw_until_end(p, name: str) -> str:
    """Recolecta tokens como texto plano hasta encontrar \\end{name}."""
    parts = []
    while p.pos < len(p.tokens):
        tok = p.tokens[p.pos]
        if tok.kind == 'COMMAND' and tok.value == '\\end':
            save_pos = p.pos
            p.pos += 1
            try:
                p.expect('OPEN_BRACE')
                end_name = p.expect('TEXT')
                p.expect('CLOSE_BRACE')
                if end_name == name:
                    return ''.join(parts).strip()
            except SyntaxError:
                pass
            parts.append(tok.value)
            p.pos = save_pos + 1
            continue
        parts.append(tok.value)
        p.pos += 1
    raise SyntaxError(f"Fin de archivo: falta \\end{{{name}}}")


def skip_brace_args(p):
    """Consume bloques {...} que siguen a un comando desconocido."""
    while True:
        pos = p.pos
        while pos < len(p.tokens) and p.tokens[pos].kind == 'WHITESPACE':
            pos += 1
        if pos >= len(p.tokens) or p.tokens[pos].kind != 'OPEN_BRACE':
            break
        p.pos = pos + 1
        depth = 1
        while p.pos < len(p.tokens) and depth > 0:
            kind = p.tokens[p.pos].kind
            if kind == 'OPEN_BRACE':
                depth += 1
            elif kind == 'CLOSE_BRACE':
                depth -= 1
            p.pos += 1


def resolve_includes(src: str, base_path: str) -> str:
    """Reemplaza \\include{archivo} con el contenido del archivo."""
    pattern = re.compile(r'\\include\{([^}]+)\}')

    def replacer(match):
        filename = match.group(1)
        if not filename.endswith('.tex'):
            filename += '.tex'
        filepath = os.path.join(base_path, filename)
        try:
            with open(filepath) as f:
                child = f.read()
            # Recursivo: el archivo incluido puede tener sus propios \include
            return resolve_includes(child, os.path.dirname(filepath))
        except FileNotFoundError:
            print(f"Warning: archivo no encontrado '{filepath}'", file=sys.stderr)
            return ''

    return pattern.sub(replacer, src)

