"""Piezas compartidas por el traductor: emisor de líneas, ámbitos y modelos."""

from __future__ import annotations

import keyword
import re
from contextlib import contextmanager
from dataclasses import dataclass, field

from tree_sitter import Node

from . import _types as T

# Precedencias de operadores en Python (mayor = liga más fuerte).
LAMBDA, TERN, OR, AND, NOT, CMP, BOR, BXOR, BAND, SHIFT, ADD, MUL, UNARY, POW, ATOM = (
    1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 16,
)
STMT = 0  # el "valor" es en realidad una sentencia (p. ej. ``m[k] = v``)

TODO = "TODO(java2py)"

# Nombres que el código generado usa como funciones de Python: una variable
# local de Java llamada igual (``max``, ``sum``, ``list``...) se renombra con
# guion bajo final para no taparlas.
_BUILTINS = {
    "max", "min", "len", "str", "int", "float", "list", "sum", "abs", "range", "print",
    "input", "set", "dict", "hash", "chr", "ord", "sorted", "type", "bool", "pow", "round",
    "map", "filter", "all", "any", "object", "tuple", "reversed", "isinstance", "super",
    "self", "iter", "bin", "hex", "math", "sys", "heapq", "deque", "random", "time", "re",
    "functools",
}


class Unsupported(Exception):
    """Construcción de Java que no tiene traducción automática."""


@dataclass
class E:
    """Resultado de traducir una expresión."""

    code: str
    prec: int = ATOM
    type: str | None = None          # tipo Java (texto) si se pudo deducir
    parts: list | None = None        # trozos de una concatenación de cadenas
    neg: str | None = None           # forma negada lista para usar (``a != b`` para ``a == b``)


@dataclass
class MethodInfo:
    name: str
    params: list[str | None]
    ret: str | None
    static: bool
    varargs: bool = False


@dataclass
class ClassInfo:
    name: str | None
    kind: str = "class"              # class | interface | enum | record | module
    superclass: str | None = None
    outer: "ClassInfo | None" = None
    fields: dict = field(default_factory=dict)       # nombre -> (tipo, es_static)
    methods: dict = field(default_factory=dict)      # nombre -> [MethodInfo]
    constants: list = field(default_factory=list)    # constantes de un enum
    type_params: list = field(default_factory=list)
    needs_outer: bool = False        # clase interna que usa miembros de la externa

    def in_chain(self, owner: "ClassInfo", classes: dict) -> bool:
        """True si ``owner`` es esta clase o una de sus superclases."""
        c, seen = self, set()
        while c is not None and id(c) not in seen:
            if c is owner:
                return True
            seen.add(id(c))
            c = classes.get(c.superclass) if c.superclass else None
        return False

    @property
    def is_module(self) -> bool:
        return self.kind == "module"

    def py_field(self, name: str) -> str:
        """Nombre Python de un campo. Si la clase tiene un método con el mismo
        nombre (``size`` y ``size()``), el campo pasa a llamarse ``_size``."""
        name = attr_name(name)
        return "_" + name if name in self.methods else name


@dataclass
class Options:
    type_hints: bool = True
    fstrings: bool = True
    main_guard: bool = True


def txt(node: Node) -> str:
    return node.text.decode("utf-8")


def P(e: E, prec: int) -> str:
    """Código de ``e``, entre paréntesis si liga menos que ``prec``."""
    return e.code if e.prec >= prec else f"({e.code})"


def attr_name(name: str) -> str:
    """Nombre válido para un atributo o método."""
    return name + "_" if keyword.iskeyword(name) else name


def local_name(name: str) -> str:
    """Nombre válido para una variable local o parámetro."""
    return name + "_" if keyword.iskeyword(name) or name in _BUILTINS else name


def comment_lines(text: str) -> list[str]:
    """Convierte un comentario Java (``//`` o ``/* */``) en líneas ``#``."""
    text = text.strip()
    if text.startswith("//"):
        return ["# " + text[2:].strip() if text[2:].strip() else "#"]
    return ["# " + line if line else "#" for line in doc_text(text)]


def doc_text(text: str) -> list[str]:
    """Líneas de texto de un comentario de bloque, sin ``/*``, ``*/`` ni ``*``."""
    text = text.strip()
    text = re.sub(r"^/\*+", "", text)
    text = re.sub(r"\*+/$", "", text)
    text = re.sub(r"\{@(?:code|link|linkplain|literal)\s+([^}]*)\}", r"\1", text)
    text = re.sub(r"</?(?:p|pre|code|b|i|em|strong|ul|ol|br)\s*/?>", "", text)
    text = re.sub(r"<li>\s*", "- ", text).replace("</li>", "")
    lines = [re.sub(r"^\s*\*? ?", "", ln).rstrip() for ln in text.splitlines()]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return lines


class Base:
    """Estado y utilidades del traductor."""

    def __init__(self, source: bytes, options: Options):
        self.source = source
        self.opts = options
        self.lines: list[str] = []
        self.level = 0
        self.imports: set[str] = set()
        self.warnings: list[str] = []
        self.classes: dict[str, ClassInfo] = {}
        self.module = ClassInfo(None, kind="module")
        self.cls: ClassInfo = self.module
        self.static_ctx = True
        self.in_class_body = False
        self.scopes: list[dict] = [{}]
        self.func_depth = 0
        self.global_writes: set[str] | None = None
        self.loops: list[dict] = []
        self.pre: list[str] | None = None
        self.post: list[str] | None = None
        self.lambda_count = 0
        self.need_future = False
        self.mains: list[str] = []
        self.inner_nodes: list = []

    # ------------------------------------------------------------- emisión
    def emit(self, text: str = "") -> None:
        for line in text.split("\n"):
            self.lines.append(("    " * self.level + line) if line.strip() else "")

    def blank(self, n: int = 1) -> None:
        """Deja ``n`` líneas en blanco antes de lo siguiente (sin duplicar)."""
        if not self.lines or self.lines[-1].rstrip().endswith(":"):
            return
        have = 0
        for line in reversed(self.lines):
            if line.strip():
                break
            have += 1
        self.lines.extend([""] * max(0, n - have))

    @contextmanager
    def capture(self):
        saved = (self.lines, self.level)
        self.lines, self.level = [], 0
        box = self.lines
        try:
            yield box
        finally:
            self.lines, self.level = saved

    def warn(self, message: str, node: Node | None = None) -> None:
        if node is not None:
            message = f"línea {node.start_point[0] + 1}: {message}"
        if message not in self.warnings:
            self.warnings.append(message)

    def todo(self, node: Node, reason: str) -> None:
        """Deja el Java original comentado, con una nota de por qué."""
        self.warn(reason, node)
        self.emit(f"# {TODO}: {reason}")
        for line in txt(node).splitlines():
            self.emit("#   " + line.strip())

    # -------------------------------------------------------------- ámbitos
    @contextmanager
    def scope(self):
        self.scopes.append({})
        try:
            yield
        finally:
            self.scopes.pop()

    def declare(self, name: str, jtype: str | None) -> str:
        self.scopes[-1][name] = jtype
        return local_name(name)

    def lookup_local(self, name: str):
        """(encontrado, tipo, índice de ámbito)."""
        for i in range(len(self.scopes) - 1, -1, -1):
            if name in self.scopes[i]:
                return True, self.scopes[i][name], i
        return False, None, -1

    # ---------------------------------------------------------------- tipos
    @property
    def user(self):
        return self.classes.keys()

    def k(self, jtype: str | None) -> str | None:
        return T.kind(jtype, self.user)

    def class_of(self, jtype: str | None) -> ClassInfo | None:
        return self.classes.get(T.base(jtype)) if jtype else None

    def find_field(self, cls: ClassInfo | None, name: str):
        """Busca un campo en la clase, sus superclases y sus clases externas."""
        outer = cls
        while outer is not None:
            c, seen = outer, set()
            while c is not None and id(c) not in seen:
                seen.add(id(c))
                if name in c.fields:
                    jtype, static = c.fields[name]
                    return c, jtype, static
                if name in c.constants:
                    return c, c.name, True
                c = self.classes.get(c.superclass) if c.superclass else None
            outer = outer.outer
        return None

    def find_method(self, cls: ClassInfo | None, name: str):
        outer = cls
        while outer is not None:
            c, seen = outer, set()
            while c is not None and id(c) not in seen:
                seen.add(id(c))
                if name in c.methods:
                    return c, c.methods[name]
                c = self.classes.get(c.superclass) if c.superclass else None
            outer = outer.outer
        if name in self.module.methods:
            return self.module, self.module.methods[name]
        return None

    def subst(self, jtype: str | None, ci: ClassInfo | None, recv_type: str | None) -> str | None:
        """Sustituye parámetros genéricos: ``T`` -> ``String`` si el receptor es ``Stack<String>``."""
        if not jtype or ci is None or not ci.type_params:
            return jtype
        args = T.type_args(recv_type)
        if len(args) != len(ci.type_params):
            return None if T.base(jtype) in ci.type_params else jtype
        for param, arg in zip(ci.type_params, args):
            if arg:
                jtype = re.sub(rf"\b{param}\b", arg, jtype)
            elif re.search(rf"\b{param}\b", jtype):
                return None
        return jtype

    def hint(self, jtype: str | None) -> str | None:
        """Anotación de tipo de Python para un tipo Java (o None)."""
        if not self.opts.type_hints or not jtype:
            return None
        return self._hint(jtype)

    def _hint(self, jtype: str | None) -> str | None:
        if not jtype:
            return None
        if jtype == "void":
            return "None"
        if T.is_array(jtype):
            inner = self._hint(jtype[:-2])
            return f"list[{inner}]" if inner else "list"
        b = T.base(jtype)
        if b in self.cls.type_params or (self.cls.outer and b in self.cls.outer.type_params):
            return None
        if b in self.classes:
            self.need_future = True
            return b
        k = T.kind(jtype)
        py = T.PY_TYPE_NAMES.get(k)
        if py is None:
            return None
        args = [self._hint(a) for a in T.type_args(jtype)]
        if k == "deque":
            self.need_future = True
            self.imports.add("from collections import deque")
        if k == "map" and len(args) == 2 and all(args):
            return f"dict[{args[0]}, {args[1]}]"
        if k in ("list", "stack", "pq", "deque", "set") and len(args) == 1 and args[0]:
            return f"{py}[{args[0]}]"
        return py

    def py_class_name(self, jtype: str, catching: bool = False) -> str:
        """Nombre de clase Python para usar en isinstance / except / new."""
        b = T.base(jtype)
        if b in self.classes:
            return b
        if b in T.EXCEPTIONS:
            if catching and b == "RuntimeException":
                return "Exception"
            return T.EXCEPTIONS[b]
        k = T.kind(jtype)
        if k == "deque":
            self.imports.add("from collections import deque")
        return T.PY_TYPE_NAMES.get(k, b)
