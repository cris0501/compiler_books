"""Handlers para \\item, \\label, \\ref."""

from ..consume import consume_raw_brace

def handle_item(p):
    if len(p.stack) > 1 and p.frame.get('context') == 'item':
        # Cierre del item anterior
        p.stack.pop()

    node = {'kind': 'item', 'content': []}
    p.add_node(node)
    p.stack.append({'node': node, 'context': 'item', 'closer': None})


def handle_label(p):
    label_id = consume_raw_brace(p)
    p.label_counter += 1

    if label_id in p.refs:
        raise SyntaxError(f"Label duplicado: '{label_id}'")

    p.refs[label_id] = {'index': p.label_counter}

    target = p.target()
    if target and isinstance(target[-1], dict):
        target[-1]['id'] = label_id
        target[-1]['index'] = p.label_counter
    else:
        p.add_node({'kind': 'label', 'id': label_id, 'index': p.label_counter})


def handle_ref(p):
    ref_id = consume_raw_brace(p)
    if ref_id not in p.refs:
        import sys
        print(f"Warning: referencia '{ref_id}' no definida", file=sys.stderr)
    index = p.refs.get(ref_id, {}).get('index')
    p.add_node({'kind': 'ref', 'target': ref_id, 'index': index})


