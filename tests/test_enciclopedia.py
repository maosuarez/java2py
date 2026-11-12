"""La enciclopedia: cada entrada debe traducir sin TODO y dar la misma salida que en Java."""

import json
import re
import subprocess
import sys
from importlib import resources

import pytest

from java2py import enciclopedia as enc
from java2py.enciclopedia.cli import main

ENTRADAS = enc.entradas()
CAMPOS = {"id", "nombre", "categoria", "archivo", "resumen", "descripcion", "complejidad"}


def _normalize(java_output: str) -> str:
    out = re.sub(r"\btrue\b", "True", java_output)
    out = re.sub(r"\bfalse\b", "False", out)
    return re.sub(r"\bnull\b", "None", out)


def test_hay_entradas():
    assert len(ENTRADAS) >= 5


@pytest.mark.parametrize("e", ENTRADAS, ids=lambda e: e.id)
def test_ficha_completa(e):
    raiz = resources.files("java2py.enciclopedia") / "datos" / e.id
    datos = json.loads((raiz / "entrada.json").read_text(encoding="utf-8"))
    assert CAMPOS <= datos.keys()
    assert e.categoria in enc.CATEGORIAS
    assert (raiz / e.archivo).is_file() and (raiz / "salida.txt").is_file()
    ids = {x.id for x in ENTRADAS}
    assert set(e.relacionados) <= ids, "relacionados apunta a entradas que no existen"


@pytest.mark.parametrize("e", ENTRADAS, ids=lambda e: e.id)
def test_traduce_y_ejecuta_igual_que_java(e, tmp_path):
    from java2py import translate_detailed

    result = translate_detailed(e.java)
    assert not result.warnings, result.warnings
    assert "TODO(java2py)" not in result.code
    script = tmp_path / f"{e.id.replace('-', '_')}.py"
    script.write_text(result.code, encoding="utf-8")
    run = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stderr
    assert run.stdout == _normalize(e.salida_esperada)


def test_alias_unicos():
    vistos = {}
    for e in ENTRADAS:
        for n in (e.id, e.nombre, *e.alias):
            k = enc.normalizar(n) if hasattr(enc, "normalizar") else n.lower()
            assert vistos.setdefault(k, e.id) == e.id, f"{n!r} repetido en {vistos[k]} y {e.id}"


@pytest.mark.parametrize(
    "consulta, esperado",
    [
        ("camino más corto", "dijkstra"),
        ("CAMINO MAS CORTO", "dijkstra"),
        ("ordenar rapido", "quicksort"),
        ("lifo", "pila"),
        ("cola de prioridad", "heap-binario"),
        ("arreglo ordenado", "busqueda-binaria"),
        ("dijkstr", "dijkstra"),  # error de escritura
        ("monticulo", "heap-binario"),
    ],
)
def test_buscar(consulta, esperado):
    res = enc.buscar(consulta)
    assert res and res[0].entrada.id == esperado


def test_buscar_sin_resultados():
    assert enc.buscar("xyzzy qwerty") == []


def test_obtener_por_alias_y_sugerencias():
    assert enc.obtener("Stack").id == "pila"
    assert enc.obtener("Búsqueda Binaria").id == "busqueda-binaria"
    with pytest.raises(KeyError, match="dijkstra"):
        enc.obtener("dikstra")


def test_ejecutar():
    assert enc.obtener("pila").ejecutar().startswith("tamano: 5")


def test_cli(capsys, tmp_path):
    assert main(["buscar", "camino", "corto"]) == 0
    assert "dijkstra" in capsys.readouterr().out
    assert main(["ver", "heap", "--lang", "ambos"]) == 0
    out = capsys.readouterr().out
    assert "class MinHeap" in out and "def insertar" in out
    assert main(["listar"]) == 0
    assert main(["comparar", "quicksort", "heap"]) == 0
    assert "O(n²)" in capsys.readouterr().out
    destino = tmp_path / "d.py"
    assert main(["guardar", "dijkstra", "-o", str(destino)]) == 0
    assert "def distancias" in destino.read_text(encoding="utf-8")
    assert main(["dijkstra"]) == 0  # atajo
    assert main(["ver", "noexiste"]) == 1
