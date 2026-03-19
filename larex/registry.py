"""
Registro de comandos y environments conocidos.

Cada entrada le dice al handler COMO consumir un comando o environment
y que nodo producir en el AST. El parser no necesita cambios para
agregar entradas nuevas.

Opciones disponibles:

  produces     - (obligatorio) valor de 'kind' en el nodo del AST
  extra        - campos fijos que se copian al nodo tal cual
  args         - cantidad de bloques {} a consumir, todos van a 'content'
  opt_args     - maximo de bloques [] posicionales a intentar (nativo LaTeX)
  kv           - si es True, el [] se parsea como pares key=value (custom esfm)
  raw_args     - si es True, los {} se leen como texto plano sin parsear
  raw          - (solo environments) el cuerpo entero se recolecta sin parsear
  self_closing - si es True, no consume ningun argumento
  inline_only  - si es True, no permite environments ni $$ dentro

Notas:
  - opt_args y kv son mutuamente excluyentes
  - raw_args aplica a los {} de un comando
  - raw aplica al cuerpo de un environment

Custom
\ comando[key1=val1, key2=val2]{contenido}
         \___ un solo [] ____/\_ args _/
Vanilla
\comando[opt1][opt2]{arg1}{arg2}
         \_ max N _/\__ args __/
"""

COMMANDS: dict[str, dict] = {
    # -- LaTeX estandar (posicional) --
    '\\chapter':         {'produces': 'heading', 'args': 1, 'extra': {'level': 0}},
    '\\section':         {'produces': 'heading', 'args': 1, 'extra': {'level': 1}},
    '\\subsection':      {'produces': 'heading', 'args': 1, 'extra': {'level': 2}},
    '\\textbf':          {'produces': 'bold',    'args': 1},
    '\\textit':          {'produces': 'italic',  'args': 1},
    '\\includegraphics': {'produces': 'image',   'args': 1, 'opt_args': 1, 'raw_args': True},
    '\\caption':         {'produces': 'caption', 'args': 1},
    '\\emph':            {'produces': 'italic',     'args': 1},
    '\\underline':       {'produces': 'underline',  'args': 1},
    '\\texttt':          {'produces': 'monospace',  'args': 1},
    '\\textsc':          {'produces': 'smallcaps',  'args': 1},
    '\\textsf':          {'produces': 'sansserif',  'args': 1},

    # Links
    '\\url':             {'produces': 'url',        'args': 1, 'raw_args': True},

    # Self-closing
    '\\noindent':   {'produces': 'noindent',   'self_closing': True},
    '\\newpage':    {'produces': 'pagebreak',  'self_closing': True},
    '\\newline':    {'produces': 'newline',      'self_closing': True},
    '\\n':          {'produces': 'newline',      'self_closing': True},
    '\\backslash':  {'produces': 'backslash',    'self_closing': True},
    '\\qed':        {'produces': 'qed',          'self_closing': True},
    '\\obs':        {'produces': 'observation',  'self_closing': True},
    '\\dem':        {'produces': 'proof-mark',   'self_closing': True},
    
    # Groups or modifiers
    '\\bfseries':   {'modifier': 'bold', 'self_closing': True},
    
    # -- Custom components ordinaries
    '\\alert':      {'produces': 'alert', 'args': 1},

    # -- Custom esfm (key-value en [], contenido en {}) --
    '\\note':       {'produces': 'note', 'args': 1, 'kv': True, 'inline_only': True},
}

ENVIRONMENTS: dict[str, dict] = {
    # -- LaTeX estandar (posicional) --
    'enumerate':    {'produces': 'list',   'extra': {'ordered': True}, 'opt_args': 1},
    'itemize':      {'produces': 'list',   'extra': {'ordered': False}},
    'figure':       {'produces': 'figure', 'opt_args': 1},
    'verbatim':     {'produces': 'verbatim', 'raw': True},
    'tabular':      {'produces': 'table', 'table': True},

    # -- Raw: el cuerpo se recolecta como texto plano --
    'equation':     {'produces': 'math', 'extra': {'mode': 'display'}, 'raw': True},
    'align':        {'produces': 'math', 'extra': {'mode': 'display'}, 'raw': True},
    'cases':        {'produces': 'math', 'extra': {'mode': 'display'}, 'raw': True},
    'pmatrix':      {'produces': 'math', 'extra': {'mode': 'display'}, 'raw': True},

    # -- Custom esfm (key-value: label, title) --
    'definition':   {'produces': 'definition',  'kv': True},
    'axiom':        {'produces': 'axiom',       'kv': True},
    'theorem':      {'produces': 'theorem',     'kv': True},
    'lemma':        {'produces': 'lemma',       'kv': True},
    'proposition':  {'produces': 'proposition', 'kv': True},
    'corollary':    {'produces': 'corollary',   'kv': True},
    'exercise':     {'produces': 'exercise',    'kv': True},
    'convention':   {'produces': 'convention',  'kv': True},
    'proof':        {'produces': 'proof',       'kv': True},
    'block':        {'produces': 'block',       'kv': True},
}

