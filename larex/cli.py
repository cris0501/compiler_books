"""
Entry point para uso por línea de comandos.

Uso:
    python -m larex examples/test.tex
    python -m larex examples/test.tex -o output.json
"""

import sys
import json
import os
import re

from .parser import compile_tex
from .consume import _resolve_includes


def main():
    if len(sys.argv) < 2:
        print("Uso: python -m larex <archivo.tex> [-f save in dist]", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    base_path = os.path.dirname(os.path.abspath(path))

    # Salida: -o archivo.json o stdout
    out_path = None
    if '-f' in sys.argv:
        os.makedirs('examples/dist', exist_ok=True)
        name = os.path.splitext(os.path.basename(path))[0]
        out_path = f'examples/dist/{name}.json'

        # Guardar el tex resuelto (con includes inyectados, sin comentarios)
        with open(path) as f:
            raw = f.read()
        resolved = _resolve_includes(raw, base_path)
        resolved = re.sub(r'(?<!\\)%.*', '', resolved)
        with open(f'examples/dist/{name}.tex', 'w') as f:
            f.write(resolved)
        print(f"-> examples/dist/{name}.tex", file=sys.stderr)

    with open(path) as f:
        try:
            ast = compile_tex(f.read(), base_path=os.path.dirname(os.path.abspath(path)))
        except SyntaxError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    if '--pretty' in sys.argv:
        result = json.dumps(ast, indent=2, ensure_ascii=False)
    else:
        result = json.dumps(ast, ensure_ascii=False, separators=(',', ':'))

    if out_path:
        with open(out_path, 'w') as f:
            f.write(result)
        print(f"-> {out_path}", file=sys.stderr)
    else:
        print(result)


if __name__ == '__main__':
    main()



