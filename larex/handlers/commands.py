"""Handlers para comandos \\nombre."""

import sys

from ..registry import COMMANDS
from ..consume import (
    consume_brace_block,
    consume_env_params,
    consume_opt_arg,
    consume_raw_brace,
    skip_brace_args,
)


def handle_command(p, cmd: str):
    props = COMMANDS.get(cmd)
    if props is None:
        print(f"Warning: comando desconocido '{cmd}'", file=sys.stderr)
        skip_brace_args(p)
        return

    if props.get('self_closing'):
        _self_closing(p, props)
    elif props.get('raw_args'):
        _raw(p, props)
    else:
        _node(p, props)


def _self_closing(p, props: dict):
    node = {'kind': props['produces']}
    node.update(props.get('extra', {}))
    p.add_node(node)


def _raw(p, props: dict):
    node = {'kind': props['produces']}
    node.update(props.get('extra', {}))

    if props.get('kv'):
        kv = consume_env_params(p)
        if kv:
            node['params'] = kv

    for _ in range(props.get('opt_args', 0)):
        opt = consume_opt_arg(p)
        if opt is not None:
            node.setdefault('options', []).append(opt)

    total = props.get('args', 0)
    if total > 0:
        node.setdefault('params', [])
    for _ in range(total):
        node['params'].append(consume_raw_brace(p))

    p.add_node(node)


def _node(p, props: dict):
    node = {'kind': props['produces']}
    node.update(props.get('extra', {}))

    if props.get('kv'):
        kv = consume_env_params(p)
        if kv:
            node['params'] = kv

    for _ in range(props.get('opt_args', 0)):
        opt = consume_opt_arg(p)
        if opt is None:
            break
        node.setdefault('options', []).append(opt)

    node['content'] = []
    p.add_node(node)

    inline_only = props.get('inline_only', False)
    for _ in range(props.get('args', 1)):
        consume_brace_block(p, node, 'content', inline_only=inline_only)

