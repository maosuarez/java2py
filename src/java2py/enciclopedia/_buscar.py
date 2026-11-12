"""Búsqueda por palabras clave, solo con la librería estándar."""

from __future__ import annotations

import difflib
import re
import unicodedata
from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from . import Entrada

_VACIAS = frozenset(
    "a al como con de del el en es la las lo los mas o para por que se sin su un una y algoritmo "
    "the of to and in for".split()
)

# Peso de cada campo de la ficha en el puntaje.
_PESOS = (
    ("nombre", 6.0),
    ("id", 6.0),
    ("alias", 5.0),
    ("etiquetas", 3.0),
    ("categoria", 2.5),
    ("resumen", 1.5),
    ("descripcion", 1.0),
    ("cuando_usar", 1.0),
)


@dataclass(frozen=True)
class Resultado:
    entrada: "Entrada"
    puntaje: float
    coincidencias: tuple[str, ...]


def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes, solo letras/números separados por un espacio."""
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return " ".join(re.findall(r"[a-z0-9]+", sin_tildes.lower()))


def _tokens(texto: str) -> list[str]:
    return [t for t in normalizar(texto).split() if t not in _VACIAS]


def _campos(e: "Entrada") -> list[tuple[str, float]]:
    out = []
    for nombre, peso in _PESOS:
        valor = getattr(e, nombre)
        if nombre == "categoria":
            valor = f"{e.categoria} {e.categoria_nombre}"
        if isinstance(valor, list):
            valor = " | ".join(valor)
        out.append((normalizar(str(valor)), peso))
    return out


def _puntuar(consulta: str, e: "Entrada") -> tuple[float, list[str]]:
    frase = normalizar(consulta)
    toks = _tokens(consulta) or frase.split()
    if not toks:
        return 0.0, []
    total = 0.0
    hallados: set[str] = set()
    for texto, peso in _campos(e):
        palabras = set(texto.split())
        if len(toks) > 1 and frase in texto:
            total += peso * 2
        for t in toks:
            if t in palabras:
                total += peso
                hallados.add(t)
            elif len(t) >= 3 and any(p.startswith(t) for p in palabras):
                total += peso * 0.7
                hallados.add(t)
            elif len(t) >= 4 and difflib.get_close_matches(t, palabras, n=1, cutoff=0.8):
                total += peso * 0.5
                hallados.add(t)
    # Premia que aparezcan todas las palabras de la consulta.
    total *= (len(hallados) / len(toks)) ** 2
    return total, sorted(hallados)


def buscar_en(consulta: str, entradas: Iterable["Entrada"], limite: int = 10) -> list[Resultado]:
    resultados = []
    for e in entradas:
        puntaje, hallados = _puntuar(consulta, e)
        if puntaje > 0:
            resultados.append(Resultado(e, round(puntaje, 2), tuple(hallados)))
    resultados.sort(key=lambda r: (-r.puntaje, r.entrada.nombre))
    return resultados[:limite]


def sugerencias(clave: str, entradas: Iterable["Entrada"], n: int = 3) -> list[str]:
    entradas = list(entradas)
    candidatos = {normalizar(x): e.id for e in entradas for x in (e.id, e.nombre, *e.alias)}
    parecidos = difflib.get_close_matches(normalizar(clave), list(candidatos), n=n * 2, cutoff=0.6)
    ids = list(dict.fromkeys(candidatos[p] for p in parecidos))
    if not ids:
        ids = [r.entrada.id for r in buscar_en(clave, entradas, n)]
    return ids[:n]
