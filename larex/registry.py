"""
Registro de comandos conocidos.

Cada entrada define cómo el parser debe consumir un comando:
  - name:         nombre semántico del nodo resultante
  - type:         'block' | 'inline' (layout hint para el frontend)
  - params:       True si el comando tiene un bloque de parámetros
                  antes del contenido, ej: \\def{param}{content}
  - self_closing: True si el comando no consume argumentos {…}

Para agregar un comando nuevo, solo se añade una entrada aquí.
El parser no necesita cambios.
"""

COMMANDS: dict[str, dict] = {
    '\\section':    {'name': 'section',    'type': 'block',  'params': False},
    '\\subsection': {'name': 'subsection', 'type': 'block',  'params': False},
    '\\def':        {'name': 'definition', 'type': 'inline', 'params': True},
    '\\textbf':     {'name': 'bold',       'type': 'inline', 'params': False},
    '\\textit':     {'name': 'italic',     'type': 'inline', 'params': False},
    '\\newline':    {'name': 'newline',    'type': 'inline', 'params': False, 'self_closing': True},
    '\\n':          {'name': 'newline',    'type': 'inline', 'params': False, 'self_closing': True},
}

