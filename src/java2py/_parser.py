"""Análisis sintáctico de Java con tree-sitter.

Acepta archivos completos y también fragmentos sueltos (un método, unas
cuantas sentencias, miembros de una clase o una sola expresión).
"""

from __future__ import annotations

from dataclasses import dataclass

import tree_sitter_java
from tree_sitter import Language, Node, Parser

_LANGUAGE = Language(tree_sitter_java.language())

FRAGMENT_CLASS = "Fragmento"


@dataclass
class Parsed:
    root: Node
    source: bytes
    wrapped: bool       # True si el fragmento se envolvió en una clase ficticia
    errors: int         # nodos con error de sintaxis que quedaron en el árbol


def _count_errors(node: Node) -> int:
    if not node.has_error:
        return 0
    total = 1 if (node.type == "ERROR" or node.is_missing) else 0
    for child in node.children:
        total += _count_errors(child)
    return total


def _parse(text: str) -> tuple[Node, bytes, int]:
    data = text.encode("utf-8")
    root = Parser(_LANGUAGE).parse(data).root_node
    return root, data, _count_errors(root)


def parse(source: str) -> Parsed:
    """Analiza ``source`` probando distintas formas de interpretarlo."""
    candidates = [
        (source, False),
        (source.rstrip() + ";", False),                              # expresión suelta
        (f"class {FRAGMENT_CLASS} {{\n{source}\n}}", True),            # miembros de clase
    ]
    best: Parsed | None = None
    for text, wrapped in candidates:
        root, data, errors = _parse(text)
        parsed = Parsed(root, data, wrapped, errors)
        if errors == 0:
            return parsed
        if best is None or errors < best.errors:
            best = parsed
    assert best is not None
    return best
