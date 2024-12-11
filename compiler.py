import pprint

# Variables globales
tree = []  # Árbol global donde se almacena la estructura
index = [{'node': tree, 'closer': None}]  # Pila de referencias con nodo y delimitador
globalContext = 'text'  # Contexto global de lectura ('text' o 'command')
commands = ['\\section', '\\def' , '$']  # Comandos que se pueden procesar
closers = {  # Delimitadores de apertura y cierre para cada tipo de bloque
    '{': '}',
    '[': ']',
    '$$': '$$',
    '$': '$'
}
input = "texto texto \\section{\\def{ texto }} texto"  # Texto de entrada

# Función para leer y procesar un comando
def readCommand(value, begin=None):
    current = index[-1]['node']  # Nodo actual
    new_node = {
        'type': value,
        'content': []
    }
    current.append(new_node)  # Añadir el nuevo nodo al nodo actual
    # Actualizar referencia al nuevo bloque con su delimitador
    index.append({'node': new_node['content'], 'closer': closers.get(begin)})

# Función para manejar el cierre de bloques
def closeBlock():
    if len(index) > 1:
        index.pop()  # Eliminar la referencia actual (volver al nodo padre)
    else:
        print("Error: No hay bloques para cerrar")  # Error si no hay bloque para cerrar

# Función para agregar texto al nodo actual
def addText(value):
    current = index[-1]['node']  # Nodo actual
    if current and isinstance(current[-1], str):
        # Si el último elemento es texto, concatenar
        current[-1] += ' '+value
    else:
        # Si no, agregar nuevo texto como un nuevo elemento
        current.append(value)

# Proceso de lectura del texto y comandos
newString = ''
for letter in input:
    if newString == '' and letter == '\\':  # Inicia comando
        globalContext = 'command'
        newString = letter
    elif globalContext == 'command':
        if letter in ['{', '[']:  # Buscar en comandos si el bloque es válido
            if newString in commands:
                readCommand(newString, letter)
                newString = ''  # Vaciar para capturar nuevo contenido
                globalContext = 'text'
            else:
                print("Error: Comando no reconocido")  # Error de comando
                exit(0)
        else:
            newString += letter  # Acumula texto hasta encontrar '{' o '['
    elif letter in ['}', ']']:  # Cierre de un bloque
        # Verificar si el delimitador cierra correctamente el bloque
        expected_closer = index[-1]['closer']
        if expected_closer == letter:
            closeBlock()  # Cerrar el bloque actual
            globalContext = 'text'  # Volver al contexto de texto
        else:
            print(f"Error: Delimitador de cierre inesperado '{letter}'")
            exit(0)
    elif letter == ' ' and newString != '':  # Termina texto
        addText(newString)
        newString = ''  # Resetear después de procesar
    else:
        newString += letter  # Acumula texto

# Impresión del árbol resultante
pprint.pprint(tree)

