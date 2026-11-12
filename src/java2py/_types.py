"""Utilidades para razonar sobre tipos de Java representados como texto.

El traductor no necesita un sistema de tipos completo: le basta saber de
qué "familia" es cada expresión (entero, cadena, lista, mapa...) para
elegir el equivalente correcto en Python (``//`` vs ``/``, ``append`` vs
``add``, ``len(x)``, etc.).
"""

from __future__ import annotations

import re

INT_TYPES = {"int", "long", "short", "byte", "Integer", "Long", "Short", "Byte", "BigInteger"}
FLOAT_TYPES = {"double", "float", "Double", "Float", "BigDecimal"}
BOOL_TYPES = {"boolean", "Boolean"}
CHAR_TYPES = {"char", "Character"}
STR_TYPES = {"String", "CharSequence"}
SB_TYPES = {"StringBuilder", "StringBuffer"}
LIST_TYPES = {"List", "ArrayList", "Vector", "Collection", "Iterable", "CopyOnWriteArrayList"}
DEQUE_TYPES = {"Queue", "Deque", "ArrayDeque", "LinkedList"}
STACK_TYPES = {"Stack"}
MAP_TYPES = {"Map", "HashMap", "TreeMap", "LinkedHashMap", "Hashtable", "SortedMap", "ConcurrentHashMap"}
SET_TYPES = {"Set", "HashSet", "TreeSet", "LinkedHashSet", "SortedSet"}
PQ_TYPES = {"PriorityQueue"}

_KIND_TABLE: dict[str, str] = {}
for _names, _kind in (
    (INT_TYPES, "int"), (FLOAT_TYPES, "float"), (BOOL_TYPES, "bool"), (CHAR_TYPES, "char"),
    (STR_TYPES, "str"), (SB_TYPES, "sb"), (LIST_TYPES, "list"), (DEQUE_TYPES, "deque"),
    (STACK_TYPES, "stack"), (MAP_TYPES, "map"), (SET_TYPES, "set"), (PQ_TYPES, "pq"),
    ({"Scanner"}, "scanner"), ({"Random"}, "random"), ({"Iterator", "ListIterator"}, "iterator"),
    ({"Entry"}, "entry"), ({"Object"}, "object"),
):
    for _n in _names:
        _KIND_TABLE[_n] = _kind

# Excepciones de Java -> excepciones de Python.
EXCEPTIONS = {
    "Exception": "Exception",
    "RuntimeException": "RuntimeError",
    "Throwable": "BaseException",
    "Error": "Exception",
    "IllegalArgumentException": "ValueError",
    "IllegalStateException": "RuntimeError",
    "IndexOutOfBoundsException": "IndexError",
    "ArrayIndexOutOfBoundsException": "IndexError",
    "StringIndexOutOfBoundsException": "IndexError",
    "NullPointerException": "AttributeError",
    "ArithmeticException": "ZeroDivisionError",
    "NumberFormatException": "ValueError",
    "InputMismatchException": "ValueError",
    "NegativeArraySizeException": "ValueError",
    "UnsupportedOperationException": "NotImplementedError",
    "NoSuchElementException": "LookupError",
    "EmptyStackException": "IndexError",
    "ClassCastException": "TypeError",
    "IOException": "OSError",
    "FileNotFoundException": "FileNotFoundError",
    "InterruptedException": "InterruptedError",
    "StackOverflowError": "RecursionError",
    "OutOfMemoryError": "MemoryError",
    "ConcurrentModificationException": "RuntimeError",
    "CloneNotSupportedException": "Exception",
    "AssertionError": "AssertionError",
}

# Nombre de tipo Java -> nombre de tipo Python (para isinstance y anotaciones).
PY_TYPE_NAMES = {
    "int": "int", "float": "float", "bool": "bool", "char": "str", "str": "str", "sb": "str",
    "list": "list", "stack": "list", "pq": "list", "deque": "deque", "map": "dict",
    "set": "set", "array": "list", "object": "object",
}


def clean(text: str | None) -> str | None:
    """Normaliza el texto de un tipo: sin espacios, anotaciones ni ``final``."""
    if text is None:
        return None
    text = re.sub(r"@\w+(\([^)]*\))?", "", text)
    text = re.sub(r"\bfinal\b", "", text)
    text = re.sub(r"\s+", "", text)
    return text or None


def is_array(t: str | None) -> bool:
    return bool(t) and t.endswith("[]")


def base(t: str | None) -> str | None:
    """``java.util.Map.Entry<K,V>`` -> ``Entry``; ``int[]`` -> ``int``."""
    if not t:
        return None
    t = t.split("<", 1)[0].replace("[]", "")
    return t.rsplit(".", 1)[-1]


def type_args(t: str | None) -> list[str]:
    """Argumentos genéricos de primer nivel: ``Map<K,List<V>>`` -> [K, List<V>]."""
    if not t or is_array(t) or "<" not in t:
        return []
    inner = t[t.index("<") + 1 : t.rindex(">")]
    args, depth, cur = [], 0, ""
    for ch in inner:
        if ch == "<":
            depth += 1
        elif ch == ">":
            depth -= 1
        if ch == "," and depth == 0:
            args.append(cur)
            cur = ""
        else:
            cur += ch
    if cur:
        args.append(cur)
    out = []
    for a in args:
        a = re.sub(r"^\?(extends|super)", "", a)
        out.append(None if a == "?" else a)
    return out


def kind(t: str | None, user: frozenset[str] | set[str] = frozenset()) -> str | None:
    """Familia a la que pertenece un tipo Java (o None si se desconoce)."""
    if not t:
        return None
    if is_array(t):
        return "array"
    b = base(t)
    if b in user:
        return "user"
    return _KIND_TABLE.get(b)


def elem(t: str | None, user=frozenset()) -> str | None:
    """Tipo de los elementos de un arreglo, colección o cadena."""
    if not t:
        return None
    if is_array(t):
        return t[:-2]
    k = kind(t, user)
    if k in ("str", "sb"):
        return "char"
    if k in ("list", "deque", "stack", "set", "pq", "iterator"):
        args = type_args(t)
        return args[0] if args else None
    return None


def default_value(t: str | None, user=frozenset()) -> str:
    """Valor por defecto de Java para un tipo, escrito en Python."""
    k = kind(t, user)
    b = base(t) if t else None
    if is_array(t):
        return "None"
    if b in ("int", "long", "short", "byte"):
        return "0"
    if b in ("double", "float"):
        return "0.0"
    if b == "boolean":
        return "False"
    if b == "char":
        return '""'
    del k
    return "None"
