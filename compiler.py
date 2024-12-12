import sys
import pprint

# Variables globales
tree = []  # Árbol global donde se almacena la estructura
index = [{'node': tree, 'context': 'text', 'closer': None, 'parameters': False}]  # Pila de referencias con nodo y delimitador

# Diccionario de comandos con propiedades
commands = {
    '\\section': {'name': 'section', 'type': 'block', 'parameters': False},
    '\\def': {'name': 'definition', 'type': 'inline', 'parameters': True}
}

# Delimitadores de apertura y cierre
closers = {
    '{': '}',
    '[': ']',
    '$$': '$$',
    '$': '$'
}

# Funcion para agregar nodo
def addNode(current, node):
    """Agrega el nodo al arbol o al contenido de otro nodo"""
    if current is tree:
        current.append(node)
    else:
        current['content'].append(node)

# Funciones auxiliares
def handle_math_opener(opener):
    """Gestiona la apertura de bloques matemáticos."""
    current = index[-1]['node']
    type_ = 'inline' if opener == '$' else 'block'
    new_node = {
        'type': type_,
        'name': 'math',
        'content': []
    }
    addNode(current, new_node)
    index.append({'node': new_node, 'context': 'math', 'closer': opener, 'parameters': False})

def handle_command(command, opener):
    """Procesa comandos reconocidos y crea nuevos nodos."""
    command_props = commands.get(command)
    params = command_props.get('parameters')

    if not command_props:
        print(f"Error: Comando no reconocido '{command}'")
        exit(0)

    current = index[-1]['node']
    new_node = {
        'type': command_props['type'],
        'name': command_props['name'],
        'parameters': [],
        'content': []
    }
    addNode(current, new_node)

    context_ = 'parameter' if params else 'content'
    index.append({
        'node': new_node,
        'context': context_,
        'parameters': params,
        'closer': closers.get(opener)
    })

def close_block(letter):
    """Cierra un bloque de acuerdo al delimitador esperado."""
    if not index:
        print(f"Error: Intento de cerrar bloque sin apertura previa '{letter}'")
        exit(0)

    expected_closer = index[-1]['closer']
    if expected_closer == letter:
        if index[-1]['context'] == 'parameter':
            index[-1]['context'] = 'content'
        else:
            index.pop()
    else:
        print(f"Error: Delimitador de cierre inesperado '{letter}', se esperaba '{expected_closer}'")
        exit(0)

def add_text(value):
    """Agrega texto al nodo actual."""
    current = index[-1]
    current_node = current['node']

    if current['context'] in ['text', 'math']:
        addNode(current_node, value)
    elif current['context'] == 'parameter' and value != '':
        current_node["parameters"].append(value)
    else:
        if current_node['content'] and isinstance(current_node['content'][-1], str):
            current_node['content'][-1] += ' ' + value
        else:
            addNode(current_node, value)

# Texto de entrada
input_ = ''
# input_ = "\\def{t}{\\section{cuerpo} $$ x + y $$}"
# Abrir y leer el archivo línea por línea
file_path = sys.argv[1] if len(sys.argv) > 1 else 'examples/test.tex'  # Reemplaza con la ruta de tu archivo
print(f"{file_path}")
with open(file_path, 'r') as file:
    for line in file:
        line = line.strip()  # Eliminar saltos de línea y espacios innecesarios
        input_ += line + ' '  # Agregar un espacio para separar líneas

# Proceso de lectura del texto y comandos
newString = ''
math_opener = ''
skip_next = False # Para $$
for i, letter in enumerate(input_):
    next_char = input_[i + 1] if i + 1 < len(input_) else ''
    if skip_next:
        skip_next = False
        continue

    if letter in ['{', '[']:
        if index[-1]['context'] == 'math':
            newString += letter
            continue
        if newString:  # Es un comando
            handle_command(newString, letter)
            newString = ''
        elif index[-1]['parameters']: # Tiene param y esta justo en el cambio
            continue # No se crea nodo y tampoco error de vacio
        else:
            print(f"Error: Comando vacío antes de '{letter}'")
            exit(0)
    elif letter in ['}', ']']:
        if index[-1]['context'] == 'math':
            newString += letter
            continue
        add_text(newString)
        close_block(letter)
        newString = ''
    elif letter == '$':
        math_opener = '$$' if next_char == '$' else '$'
        if index[-1]['context'] == 'math':
            add_text(newString)
            close_block(math_opener)
            newString = ''
        else:
            handle_math_opener(math_opener)
        if math_opener == '$$': skip_next = True
        math_opener = ''
    elif letter == ' ' and newString:
        add_text(newString)
        newString = ''
    elif letter == ' ':
        continue # Elimina el espacio en '$ tex'
    else:
        newString += letter

# Procesar cualquier texto restante
if newString:
    add_text(newString)

# Impresión del árbol resultante
print(input_)
pprint.pprint(tree)

