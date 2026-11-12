"""``java2py-enc``: consulta la enciclopedia desde la terminal."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from . import CATEGORIAS, Entrada, buscar, categorias, entradas, obtener

_EPILOG = """ejemplos:
  java2py-enc buscar camino mas corto     busca por palabras clave
  java2py-enc ver dijkstra                ficha + código Python
  java2py-enc ver heap --lang ambos       ficha + Java + Python
  java2py-enc listar --categoria grafos   índice de una categoría
  java2py-enc comparar quicksort heap     tabla de complejidades
  java2py-enc ejecutar pila               corre el ejemplo en Python
  java2py-enc guardar dijkstra -o d.py    guarda el código en un archivo
  java2py-enc dijkstra                    atajo: ver si existe, si no buscar
"""

_COMANDOS = {"buscar", "ver", "listar", "comparar", "ejecutar", "guardar"}


class _Estilo:
    def __init__(self) -> None:
        self.on = sys.stdout.isatty() and not os.environ.get("NO_COLOR")

    def _c(self, cod: str, s: str) -> str:
        return f"\033[{cod}m{s}\033[0m" if self.on else s

    def titulo(self, s: str) -> str:
        return self._c("1;36", s)

    def neg(self, s: str) -> str:
        return self._c("1", s)

    def tenue(self, s: str) -> str:
        return self._c("2", s)


E = _Estilo()


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="java2py-enc",
        description="Enciclopedia de algoritmos y estructuras de datos (Java y Python).",
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="cmd", required=True, metavar="comando")

    s = sub.add_parser("buscar", help="buscar por palabras clave")
    s.add_argument("consulta", nargs="+")
    s.add_argument("-n", type=int, default=10, help="máximo de resultados")
    s.add_argument("--categoria")

    s = sub.add_parser("ver", help="ver la ficha y el código de una entrada")
    s.add_argument("entrada", nargs="+")
    s.add_argument("--lang", choices=["py", "java", "ambos", "ninguno"], default="py")

    s = sub.add_parser("listar", help="índice por categorías")
    s.add_argument("--categoria")

    s = sub.add_parser("comparar", help="comparar complejidades de varias entradas")
    s.add_argument("entradas", nargs="+")

    s = sub.add_parser("ejecutar", help="ejecutar el ejemplo traducido a Python")
    s.add_argument("entrada", nargs="+")

    s = sub.add_parser("guardar", help="guardar el código en un archivo")
    s.add_argument("entrada", nargs="+")
    s.add_argument("-o", "--output", required=True)
    s.add_argument("--lang", choices=["py", "java"], default=None, help="por defecto, según la extensión")
    return p


def _lista(titulo: str, items: list[str]) -> list[str]:
    return [E.neg(titulo), *[f"  • {x}" for x in items]] if items else []


def _complejidad(e: Entrada) -> list[str]:
    lineas = [E.neg("Complejidad")]
    for caso, valor in e.complejidad.get("tiempo", {}).items():
        lineas.append(f"  tiempo ({caso}): {valor}")
    if "espacio" in e.complejidad:
        lineas.append(f"  espacio: {e.complejidad['espacio']}")
    return lineas


def _ficha(e: Entrada) -> str:
    out = [
        E.titulo(e.nombre) + E.tenue(f"  [{e.id} · {e.categoria_nombre}]"),
        e.resumen,
        "",
        e.descripcion,
        "",
        *_complejidad(e),
        *_lista("Cuándo usarlo", e.cuando_usar),
        *_lista("Ventajas", e.ventajas),
        *_lista("Desventajas", e.desventajas),
    ]
    if e.python_estandar:
        out.append(f"{E.neg('En la librería estándar de Python:')} {e.python_estandar}")
    if e.relacionados:
        out.append(f"{E.neg('Relacionados:')} {', '.join(e.relacionados)}")
    if e.alias:
        out.append(E.tenue("También: " + ", ".join(e.alias)))
    return "\n".join(out)


def _bloque(titulo: str, codigo: str) -> str:
    return f"\n{E.titulo('── ' + titulo + ' ' + '─' * max(0, 60 - len(titulo)))}\n{codigo.rstrip()}\n"


def _ver(e: Entrada, lang: str) -> None:
    print(_ficha(e))
    if lang in ("java", "ambos"):
        print(_bloque(f"Java · {e.archivo}", e.java))
    if lang in ("py", "ambos"):
        print(_bloque("Python (traducido por java2py)", e.python))
    if lang != "ninguno":
        print(_bloque("Salida del ejemplo", e.salida_esperada))


def _buscar(consulta: str, n: int, categoria: str | None) -> int:
    res = buscar(consulta, limite=n, categoria=categoria)
    if not res:
        print(f"Sin resultados para {consulta!r}. Prueba con otras palabras o `java2py-enc listar`.")
        return 1
    ancho = max(len(r.entrada.id) for r in res)
    for r in res:
        e = r.entrada
        print(f"{E.neg(e.id.ljust(ancho))}  {e.nombre} {E.tenue('· ' + e.categoria_nombre)}")
        print(f"{' ' * ancho}  {E.tenue(e.resumen)}")
    print(E.tenue(f"\nVer una: java2py-enc ver {res[0].entrada.id}"))
    return 0


def _listar(categoria: str | None) -> int:
    grupos = categorias()
    if categoria:
        sel = entradas(categoria)
        if not sel:
            print(f"Categoría desconocida: {categoria!r}. Disponibles: {', '.join(grupos)}", file=sys.stderr)
            return 1
        grupos = {sel[0].categoria: sel}
    for cat, es in grupos.items():
        print(E.titulo(f"{CATEGORIAS.get(cat, cat)} ({len(es)})"))
        ancho = max(len(e.id) for e in es)
        for e in es:
            print(f"  {e.id.ljust(ancho)}  {E.tenue(e.resumen)}")
    return 0


def _comparar(es: list[Entrada]) -> int:
    filas = []
    for e in es:
        tiempo = "; ".join(f"{k}: {v}" for k, v in e.complejidad.get("tiempo", {}).items())
        filas.append((e.nombre, tiempo, e.complejidad.get("espacio", "")))
    cab = ("Entrada", "Tiempo", "Espacio")
    anchos = [max(len(f[i]) for f in [cab, *filas]) for i in range(3)]
    linea = lambda f: "  ".join(c.ljust(a) for c, a in zip(f, anchos)).rstrip()  # noqa: E731
    print(E.neg(linea(cab)))
    print("  ".join("─" * a for a in anchos))
    for f in filas:
        print(linea(f))
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    # Atajo: `java2py-enc dijkstra` -> ver si existe, si no buscar.
    if argv and not argv[0].startswith("-") and argv[0] not in _COMANDOS:
        consulta = " ".join(argv)
        try:
            _ver(obtener(consulta), "py")
            return 0
        except KeyError:
            return _buscar(consulta, 10, None)

    args = _build_parser().parse_args(argv)
    try:
        if args.cmd == "buscar":
            return _buscar(" ".join(args.consulta), args.n, args.categoria)
        if args.cmd == "listar":
            return _listar(args.categoria)
        if args.cmd == "comparar":
            return _comparar([obtener(x) for x in args.entradas])
        e = obtener(" ".join(args.entrada))
        if args.cmd == "ver":
            _ver(e, args.lang)
        elif args.cmd == "ejecutar":
            print(e.ejecutar(), end="")
        elif args.cmd == "guardar":
            lang = args.lang or ("java" if args.output.endswith(".java") else "py")
            Path(args.output).write_text(e.java if lang == "java" else e.python, encoding="utf-8")
            print(f"Guardado {args.output} ({'Java' if lang == 'java' else 'Python'})")
        return 0
    except KeyError as exc:
        print(f"java2py-enc: {exc.args[0]}", file=sys.stderr)
        return 1
    except BrokenPipeError:
        return 0


if __name__ == "__main__":
    sys.exit(main())
