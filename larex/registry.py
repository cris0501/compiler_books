"""
Registro de comandos conocidos.

Cada entrada le dice al parser CÓMO consumir un comando:
  - produces:     qué 'kind' de nodo genera en el AST
  - args:         cuántos bloques {…} consume (default 0)
  - param_args:   cuántos de esos args van a 'params' (default 0)
                  los restantes van a 'content'
  - extra:        campos fijos que se copian al nodo (ej: level)
  - self_closing: True si no consume argumentos

El parser es genérico: lee estas propiedades y actúa en
consecuencia. Para agregar un comando nuevo, solo se añade
una entrada aquí. El parser no necesita cambios.

Ejemplo de cómo se lee:
  '\\section' produce un nodo kind='heading' con level=1,
  consume 1 argumento {…} que va a content.

  '\\def' produce un nodo kind='note',
  consume 2 argumentos: el primero va a params, el segundo a content.
"""

COMMANDS: dict[str, dict] = {
    # Estructura
    '\\section':    {'produces': 'heading',  'args': 1, 'extra': {'level': 1}},
    '\\subsection': {'produces': 'heading',  'args': 1, 'extra': {'level': 2}},

    # Formato inline
    '\\textbf':     {'produces': 'bold',     'args': 1},
    '\\textit':     {'produces': 'italic',   'args': 1},

    # Bloques con parámetro + contenido
    '\\def':        {'produces': 'note',     'args': 2, 'param_args': 1},

    # Sin argumentos
    '\\newline':    {'produces': 'newline',  'args': 0, 'self_closing': True},
    '\\n':          {'produces': 'newline',  'args': 0, 'self_closing': True},
    
    # Close siblings or implicit close
    '\\item':     {'produces': 'item', 'args': 0, 'self_closing': False, 'implicit_close': True},
}

ENVIRONMENTS: dict[str, dict] = {
    'enumerate': {'produces': 'list', 'extra': {'ordered': True}},
    'itemize':   {'produces': 'list', 'extra': {'ordered': False}},
    'equation':  {'produces': 'math', 'extra': {'mode': 'display'}, 'raw': True},
}
