"""Enciclopedia de algoritmos y estructuras de datos incluida en java2py.

Cada entrada se guarda en Java (``datos/<id>/``) junto con su ficha (``entrada.json``)
y la salida real del programa en Java (``salida.txt``). El Python se genera con el
traductor de esta misma librería, así que no hay dos versiones que mantener a mano.

    >>> from java2py import enciclopedia as enc
    >>> [r.entrada.id for r in enc.buscar("camino mas corto")][:1]
    ['dijkstra']
    >>> enc.obtener("dijkstra").complejidad["espacio"]
    'O(V + E)'
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from functools import cached_property, lru_cache
from importlib import resources

from ._buscar import Resultado, buscar_en, normalizar, sugerencias

__all__ = [
    "Entrada",
    "Resultado",
    "entradas",
    "obtener",
    "buscar",
    "categorias",
    "CATEGORIAS",
]

#: Nombre legible de cada categoría, en el orden en que se listan.
CATEGORIAS: dict[str, str] = {
    "estructuras": "Estructuras de datos",
    "ordenamiento": "Ordenamiento",
    "busqueda": "Búsqueda",
    "grafos": "Grafos",
    "programacion-dinamica": "Programación dinámica",
    "cadenas": "Cadenas",
}


@dataclass(frozen=True)
class Entrada:
    """Una ficha de la enciclopedia. ``java`` y ``python`` dan el código completo."""

    id: str
    nombre: str
    categoria: str
    archivo: str
    resumen: str
    descripcion: str
    complejidad: dict
    alias: list[str] = field(default_factory=list)
    etiquetas: list[str] = field(default_factory=list)
    cuando_usar: list[str] = field(default_factory=list)
    ventajas: list[str] = field(default_factory=list)
    desventajas: list[str] = field(default_factory=list)
    relacionados: list[str] = field(default_factory=list)
    python_estandar: str = ""

    def _leer(self, nombre: str) -> str:
        return (resources.files(__package__) / "datos" / self.id / nombre).read_text(encoding="utf-8")

    @cached_property
    def java(self) -> str:
        """Código Java de la entrada (incluye un ``main`` de ejemplo)."""
        return self._leer(self.archivo)

    @cached_property
    def python(self) -> str:
        """El mismo programa traducido a Python con java2py."""
        from ..translator import translate

        return translate(self.java)

    @cached_property
    def salida_esperada(self) -> str:
        """Lo que imprime el ejemplo al ejecutarse en Java."""
        return self._leer("salida.txt")

    @property
    def categoria_nombre(self) -> str:
        return CATEGORIAS.get(self.categoria, self.categoria)

    def ejecutar(self, timeout: float = 30) -> str:
        """Ejecuta el ejemplo traducido a Python y devuelve lo que imprime."""
        run = subprocess.run(
            [sys.executable, "-c", self.python], capture_output=True, text=True, timeout=timeout
        )
        if run.returncode != 0:
            raise RuntimeError(run.stderr.strip())
        return run.stdout


@lru_cache(maxsize=None)
def _cargar() -> tuple[Entrada, ...]:
    raiz = resources.files(__package__) / "datos"
    resultado = []
    for carpeta in raiz.iterdir():
        ficha = carpeta / "entrada.json"
        if carpeta.is_dir() and ficha.is_file():
            resultado.append(Entrada(**json.loads(ficha.read_text(encoding="utf-8"))))
    orden = list(CATEGORIAS)
    resultado.sort(key=lambda e: (orden.index(e.categoria) if e.categoria in orden else len(orden), e.nombre))
    return tuple(resultado)


def entradas(categoria: str | None = None) -> list[Entrada]:
    """Todas las entradas, o solo las de una categoría."""
    todas = list(_cargar())
    if categoria is None:
        return todas
    cat = normalizar(categoria).replace(" ", "-")
    return [e for e in todas if e.categoria == cat or normalizar(e.categoria_nombre) == normalizar(categoria)]


def categorias() -> dict[str, list[Entrada]]:
    """Entradas agrupadas por categoría (solo las categorías con contenido)."""
    grupos: dict[str, list[Entrada]] = {}
    for e in _cargar():
        grupos.setdefault(e.categoria, []).append(e)
    return grupos


def obtener(clave: str) -> Entrada:
    """Busca una entrada por id, nombre o alias exactos (sin importar tildes ni mayúsculas).

    Si no existe, lanza ``KeyError`` con sugerencias.
    """
    objetivo = normalizar(clave).replace("-", " ")
    for e in _cargar():
        nombres = [e.id, e.nombre, *e.alias]
        if any(normalizar(n).replace("-", " ") == objetivo for n in nombres):
            return e
    parecidas = sugerencias(clave, _cargar())
    pista = f" ¿Quisiste decir: {', '.join(parecidas)}?" if parecidas else ""
    raise KeyError(f"No hay ninguna entrada llamada {clave!r}.{pista}")


def buscar(consulta: str, limite: int = 10, categoria: str | None = None) -> list[Resultado]:
    """Busca por palabras clave en nombre, alias, etiquetas y descripción.

    Tolera tildes, mayúsculas y errores de escritura pequeños. Devuelve los
    resultados ordenados de más a menos relevante.
    """
    return buscar_en(consulta, entradas(categoria), limite)
