"""Handler para bloques matemáticos."""

def handle_math(p, opener: str):
    mode = 'display' if opener == '$$' else 'inline'
    if mode == 'display' and p.frame.get('inline_only'):
        raise SyntaxError(f"Math display ($$) no permitido en este contexto{p._at()}")
    raw = _collect_math(p, opener)
    p.add_node({'kind': 'math', 'mode': mode, 'raw': raw})


def _collect_math(p, closer: str) -> str:
    parts = []
    while p.pos < len(p.tokens):
        tok = p.tokens[p.pos]
        is_end = (tok.kind == 'MATH_BLOCK' and closer == '$$') or \
                 (tok.kind == 'MATH_INLINE' and closer == '$')
        if is_end:
            p.pos += 1
            break
        parts.append(tok.value)
        p.pos += 1
    return ''.join(parts).strip()
