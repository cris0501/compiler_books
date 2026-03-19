""" Table handler """

def parse_col_spec(spec: str) -> list:
    """Parsea |l|c|r| en una lista de columnas."""
    columns = []
    border_next = False
    for ch in spec.strip():
        if ch == '|':
            if columns:
                columns[-1]['border_right'] = True
            else:
                border_next = True
        elif ch in ('l', 'c', 'r'):
            align = {'l': 'left', 'c': 'center', 'r': 'right'}[ch]
            col = {'align': align}
            if border_next:
                col['border_left'] = True
                border_next = False
            columns.append(col)
    return columns

def parse_table_rows(p, name: str) -> list:
    """Parsea filas y celdas hasta \\end{name}."""
    rows = []
    current_row = []
    
    def start_cell():
        """Abre una celda nueva en el stack."""
        cell = {'kind': 'cell', 'content': []}
        current_row.append(cell)
        p.stack.append({'node': cell, 'context': 'content', 'closer': None})
    
    def close_cell():
        """Cierra la celda actual del stack."""
        if p.stack[-1].get('context') == 'content' and \
           isinstance(p.stack[-1]['node'], dict) and \
           p.stack[-1]['node'].get('kind') == 'cell':
          p.stack.pop()
    
    def flush_row():
        close_cell()
        if current_row:
            cells = [c['content'] for c in current_row]
            # Solo agregar si hay celda con contenido
            if any(cell for cell in cells):
                rows.append({'cells': cells})
            current_row.clear()
    
    # -- Init parser --
    start_cell()
    
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
                    flush_row()
                    return rows
            except SyntaxError:
                pass
            p.pos = save_pos + 1
            continue
        
        # \hline
        if tok.kind == 'COMMAND' and tok.value == '\\hline':
            flush_row()
            rows.append({'hline': True})
            p.pos += 1
            start_cell()
            continue
        
        # \\ = fin de fila
        if tok.kind == 'DOUBLE_BACKSLASH':
            flush_row()
            p.pos += 1
            start_cell()
            continue
        
        # & = separador de celda
        if tok.kind == 'AMPERSAND':
            close_cell()
            p.pos += 1
            start_cell()
            continue
        
        # Cualquier otro token: parseo normal
        p.step()
    
    raise SyntaxError(f"Fin de archivo: falta \\end{{{name}}}")

