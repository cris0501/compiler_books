"""
larex – transpilador LaTeX → JSON para libros interactivos.

Uso:
    from larex import compile_tex
    ast = compile_tex(r"\\section{Hola} texto $x^2$")
"""

from .parser import compile_tex

__all__ = ['compile_tex']

