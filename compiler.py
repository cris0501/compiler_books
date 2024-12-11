import pprint

# Variables globales
tree = []  # Árbol global donde se almacena la estructura
index = [{'node': tree, 'closer': None}]  # Pila de referencias con nodo y delimitador
globalContext = ['text']  # Pila de contextos de lectura ('text', 'command', 'math')

# Diccionario de comandos con propiedades
commands = {
    '\\section': {'name': 'section', 'type': 'block'},
    '\\def': {'name': 'definition', 'type': 'inline'}
}

# Delimitadores de apertura y cierre
closers = {  
    '{': '}',
    '[': ']',
    '$$': '$$',
    '$': '$'
}

# Texto de entrada
input = "texto {texto \\section{\\def{$ texto $}} te}xto"

# Función para leer y procesar mate
def readMath(value, opener):
    command_props = {
        'name': 'math',
        'type': 'inline'
    }

    current = index[-1]['node']  # Ultimo nodo al que se accede
    new_node = {
        'type': 'inline',
        'name': 'math',
        'content': []
    }
    current.append(new_node)  # Añadir el nuevo nodo al nodo actual
    # Actualizar referencia al nuevo bloque con su delimitador
    # Esto solo a bloques pues este sera el padre del contenido
    index.append({'node': new_node['content'], 'closer': opener})
    globalContext.append('math')  # Cambiar al contexto de comando

# Función para leer y procesar un comando
def readCommand(value, opener):
    command_props = commands.get(value)
    if not command_props:
        print(f"Error: Comando no reconocido '{value}'")
        exit(0)

    current = index[-1]['node']  # Ultimo nodo al que se accede
    new_node = {
        'type': command_props['type'],
        'name': command_props['name'],
        'content': []
    }
    current.append(new_node)  # Añadir el nuevo nodo al nodo actual
    # Actualizar referencia al nuevo bloque con su delimitador
    # Esto solo a bloques pues este sera el padre del contenido
    index.append({'node': new_node['content'], 'closer': closers[opener]})
    globalContext.append('command')  # Cambiar al contexto de comando

# Función para manejar el cierre de bloques
def closeMath(letter):
    if not index:
        print(f"Error: Intento de cerrar bloque sin apertura previa '{letter}'")
        exit(0)

    expected_closer = index[-1]['closer']
    if expected_closer == letter:
        index.pop()  # Eliminar la referencia actual (volver al nodo padre)
        globalContext.pop()  # Salir del contexto actual
    else:
        print(f"Error: Delimitador de cierre inesperado '{letter}', se esperaba '{expected_closer}'")
        exit(0)

# Función para manejar el cierre de bloques
def closeBlock(letter):
    if not index:
        print(f"Error: Intento de cerrar bloque sin apertura previa '{letter}'")
        exit(0)

    expected_closer = index[-1]['closer']
    if expected_closer == letter:
        index.pop()  # Eliminar la referencia actual (volver al nodo padre)
        globalContext.pop()  # Salir del contexto actual
    else:
        print(f"Error: Delimitador de cierre inesperado '{letter}', se esperaba '{expected_closer}'")
        exit(0)

# Función para agregar texto al nodo actual
def addText(value):
    current = index[-1]['node']  # Nodo actual
    if current and isinstance(current[-1], str):
        # Si el último elemento es texto, concatenar
        current[-1] += ' ' + value
    else:
        # Si no, agregar nuevo texto como un nuevo elemento
        current.append(value)

# Proceso de lectura del texto y comandos
newString = ''
for letter in input:
    if newString == '' and letter == '\\':  # Inicia comando
        globalContext.append('command')  # Cambiar al contexto de comando
        newString = letter
    elif globalContext[-1] == 'command':
        if letter in ['{', '[']:  # Validar si es un delimitador de apertura
            if newString in commands:
                readCommand(newString, letter)
                newString = ''  # Vaciar para capturar nuevo contenido
                globalContext[-1] = 'text'  # Volver al contexto de texto
            else:
                print(f"Error: Comando no reconocido '{newString}'")
                exit(0)
        else:
            newString += letter  # Acumula texto hasta encontrar un delimitador de apertura
    elif letter in ['$', '$$'] and globalContext[-1] == 'text':  # Inicio de bloque especial
        readMath(newString, letter)
    elif letter in ['$', '$$'] and globalContext[-1] == 'math':  # Cierre del bloque matemático
        expected_closer = index[-1]['closer']
        if expected_closer == letter:
            closeMath(letter)  # Cerrar el bloque actual
        else:
            newString += letter
    elif letter == ' ' and newString != '':  # Termina texto
        addText(newString)
        newString = ''  # Resetear después de procesar
    else:
        newString += letter  # Acumula texto

# Impresión del árbol resultante
print(input)
pprint.pprint(tree)

