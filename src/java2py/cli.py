"""Línea de comandos: ``java2py Archivo.java`` o ``python -m java2py``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .translator import translate_detailed

_EPILOG = """ejemplos:
  java2py Pila.java                  muestra el Python en pantalla
  java2py Pila.java -o pila.py       lo guarda en un archivo
  java2py src/ -o py/                traduce todos los .java de una carpeta
  java2py -c "int x = 7 / 2;"        traduce un fragmento
  cat Pila.java | java2py -          lee de la entrada estándar
  java2py -i                         modo interactivo (pega Java, línea vacía para traducir)
"""


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="java2py",
        description="Traduce código Java a Python (sin IA) para estudiar el mismo material en Python.",
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("source", nargs="?", help="archivo .java, carpeta, o '-' para leer de stdin")
    p.add_argument("-o", "--output", help="archivo .py (o carpeta) de salida")
    p.add_argument("-c", "--code", help="fragmento de Java a traducir")
    p.add_argument("-i", "--interactive", action="store_true", help="modo interactivo")
    p.add_argument("--no-type-hints", action="store_true", help="no generar anotaciones de tipo")
    p.add_argument("--no-fstrings", action="store_true", help="concatenar con + y str() en vez de f-strings")
    p.add_argument("--no-main", action="store_true", help='no añadir el bloque if __name__ == "__main__"')
    p.add_argument("-q", "--quiet", action="store_true", help="no mostrar avisos")
    p.add_argument("-V", "--version", action="version", version=f"java2py {__version__}")
    return p


def _run(text: str, args, label: str = "") -> str:
    result = translate_detailed(
        text,
        type_hints=not args.no_type_hints,
        fstrings=not args.no_fstrings,
        main_guard=not args.no_main,
    )
    if not args.quiet:
        for w in result.warnings:
            print(f"java2py: aviso{' [' + label + ']' if label else ''}: {w}", file=sys.stderr)
    return result.code


def _interactive(args) -> int:
    print("java2py interactivo. Pega código Java y deja una línea vacía para traducir. Ctrl+D para salir.")
    buf: list[str] = []
    while True:
        try:
            line = input("java> " if not buf else "....> ")
        except EOFError:
            print()
            return 0
        if line.strip():
            buf.append(line)
            continue
        if buf:
            print(_run("\n".join(buf), args))
            buf = []


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.interactive:
        return _interactive(args)
    if args.code is not None:
        text, label = args.code, ""
    elif args.source in (None, "-"):
        if args.source is None and sys.stdin.isatty():
            _build_parser().print_help()
            return 2
        text, label = sys.stdin.read(), ""
    else:
        src = Path(args.source)
        if src.is_dir():
            out_dir = Path(args.output) if args.output else src
            files = sorted(src.rglob("*.java"))
            for f in files:
                target = out_dir / f.relative_to(src).with_suffix(".py")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(_run(f.read_text(encoding="utf-8"), args, f.name), encoding="utf-8")
                print(f"{f} -> {target}", file=sys.stderr)
            if not files:
                print(f"java2py: no hay archivos .java en {src}", file=sys.stderr)
                return 1
            return 0
        if not src.is_file():
            print(f"java2py: no existe el archivo {src}", file=sys.stderr)
            return 1
        text, label = src.read_text(encoding="utf-8"), src.name
    code = _run(text, args, label)
    if args.output:
        Path(args.output).write_text(code, encoding="utf-8")
    else:
        sys.stdout.write(code)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
