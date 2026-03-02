"""
Entry point para uso por línea de comandos.

Uso:
    python -m larex examples/test.tex
    python -m larex examples/test.tex -o output.json
"""

import sys
import json

from .parser import compile_tex


def main():
    if len(sys.argv) < 2:
        print("Uso: python -m larex <archivo.tex> [-o salida.json]", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]

    # Salida: -o archivo.json o stdout
    out_path = None
    if '-o' in sys.argv:
        idx = sys.argv.index('-o')
        if idx + 1 < len(sys.argv):
            out_path = sys.argv[idx + 1]

    with open(path) as f:
        ast = compile_tex(f.read())

    result = json.dumps(ast, indent=2, ensure_ascii=False)

    if out_path:
        with open(out_path, 'w') as f:
            f.write(result)
        print(f"→ {out_path}", file=sys.stderr)
    else:
        print(result)


if __name__ == '__main__':
    main()

