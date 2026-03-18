"""Handlers para \\begin/\\end."""

import sys

from ..registry import ENVIRONMENTS
from ..consume import (
      consume_env_params,
      consume_opt_arg,
      consume_raw_until_end
  )


def handle_begin(p):
    if p.frame.get('inline_only'):
        raise SyntaxError(f"Environments no permitidos en este contexto{p._at()}")

    begin_tok = p.last_tok
    p.expect('OPEN_BRACE')
    name = p.expect('TEXT')
    p.expect('CLOSE_BRACE')

    props = ENVIRONMENTS.get(name)
    if props is None:
        print(f"Warning: environment desconocido '{name}'", file=sys.stderr)
        return

    # -- Params: kv o posicional según registry --
    kv = {}
    opts = []
    if props.get('kv'):
        kv = consume_env_params(p)
    else:
        for _ in range(props.get('opt_args', 0)):
            opt = consume_opt_arg(p)
            if opt is None:
                break
            opts.append(opt)

    # -- Raw environments (equation, etc.) --
    if props.get('raw'):
        raw = consume_raw_until_end(p, name)
        node = {'kind': props['produces']}
        node.update(props.get('extra', {}))
        node['raw'] = raw
        if kv:
            node['params'] = kv
        if opts:
            node['options'] = opts
        p.add_node(node)
        return

    # -- Parsed environments --
    node = {'kind': props['produces']}
    node.update(props.get('extra', {}))
    if kv:
        node['params'] = kv
    if opts:
        node['options'] = opts
    node['content'] = []

    # -- Register reference --
    _register_label(p, node, kv)

    p.add_node(node)
    p.stack.append({
        'node': node,
        'context': 'content',
        'closer': '\\end{' + name + '}',
        'opened_at': begin_tok,
    })


def handle_end(p):
    p.expect('OPEN_BRACE')
    name = p.expect('TEXT')
    p.expect('CLOSE_BRACE')

    expected = '\\end{' + name + '}'

    if len(p.stack) > 1 and p.frame.get('context') == 'item':
        p.stack.pop()

    if len(p.stack) <= 1:
        raise SyntaxError(f"\\end{{{name}}} sin \\begin correspondiente{p._at()}")
    if p.frame['closer'] != expected:
        raise SyntaxError(f"Se esperaba {p.frame['closer']}, se encontró {expected}{p._at()}")
    p.stack.pop()


def _collect_until_end(p, name: str) -> str:
    """
        Lee contenido hasta cerrar bloque
        \begin { equation }
            raw
        \end { equation }
        se colecta por token
    """
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
    raise SyntaxError(f"Fin de archivo: falta \\end{{{name}}}{p._at()}")

# -- Util methods --
def _register_label(p, node: dict, kv: dict):
    """Si hay label en los kv params, registra la referencia."""
    label_id = kv.get('label')
    if not label_id:
        return

    p.label_counter += 1

    if label_id in p.refs:
        raise SyntaxError(f"Label duplicado: '{label_id}'")

    p.refs[label_id] = {'index': p.label_counter}
    node['id'] = label_id
    node['index'] = p.label_counter


