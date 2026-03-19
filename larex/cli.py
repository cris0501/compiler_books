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
import shutil

from .parser import compile_tex
from .consume import resolve_includes


def main():
    if len(sys.argv) < 2:
        print("Uso: python -m larex <archivo.tex> [-f] [--pretty]", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    base_path = os.path.dirname(os.path.abspath(path))

    with open(path) as f:
        raw = f.read()

    # Preproceso: includes + comentarios
    resolved = resolve_includes(raw, base_path)
    resolved = re.sub(r'^\s*%.*\n?', '', resolved, flags=re.MULTILINE)
    resolved = re.sub(r'(?<!\\)%.*', '', resolved)

    # Parsear
    try:
        ast = compile_tex(resolved, base_path=base_path)
    except SyntaxError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Output
    if '--pretty' in sys.argv:
        result = json.dumps(ast, indent=2, ensure_ascii=False)
    else:
        result = json.dumps(ast, ensure_ascii=False, separators=(',', ':'))

    if '-f' in sys.argv:
        os.makedirs(base_path+'/dist', exist_ok=True)
        name = os.path.splitext(os.path.basename(path))[0]

        with open(f'{base_path}/dist/{name}.tex', 'w') as f:
            f.write(resolved)
        print(f"-> {base_path}/dist/{name}.tex", file=sys.stderr)

        with open(f'{base_path}/dist/{name}.json', 'w') as f:
            f.write(result)
        print(f"-> {base_path}/dist/{name}.json", file=sys.stderr)

        assets_src = os.path.join(base_path, 'assets')
        if os.path.isdir(assets_src):
            assets_dst = os.path.join(base_path, 'dist', 'assets')
            shutil.copytree(assets_src, assets_dst, dirs_exist_ok=True)
            print(f"-> {assets_dst}", file=sys.stderr)
    else:
        print(result)


if __name__ == '__main__':
    main()




