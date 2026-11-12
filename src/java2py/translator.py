"""API pública del traductor Java -> Python."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path

from ._core import Base, Options
from ._decl import DeclMixin
from ._expr import ExprMixin
from ._parser import FRAGMENT_CLASS, parse
from ._stmt import StmtMixin


@dataclass
class TranslationResult:
    """Código Python generado y avisos sobre lo que conviene revisar a mano."""

    code: str
    warnings: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return self.code


class _Translator(DeclMixin, StmtMixin, ExprMixin, Base):
    def run(self, root) -> str:
        self.collect(root)
        self.mark_inner_classes()
        self.statements(root)
        body = self.lines
        while body and not body[-1].strip():
            body.pop()
        if self.opts.main_guard and self.mains:
            self.imports.add("import sys")
            body += ["", "", 'if __name__ == "__main__":', f"    {self.mains[0]}(sys.argv[1:])"]
        head = []
        if self.need_future and self.opts.type_hints:
            head.append("from __future__ import annotations")
            head.append("")
        head += self._import_lines()
        if head and head[-1]:
            head += ["", ""] if body and re.match(r"(class|def|@)", body[0]) else [""]
        while body and not body[0].strip():
            body.pop(0)
        text = "\n".join(head + body) + "\n"
        return re.sub(r"\n{4,}", "\n\n\n", text)

    def _import_lines(self) -> list[str]:
        plain = sorted(i for i in self.imports if i.startswith("import "))
        froms: dict[str, set[str]] = {}
        for imp in self.imports:
            if imp.startswith("from "):
                _, mod, _, names = imp.split(" ", 3)
                froms.setdefault(mod, set()).update(n.strip() for n in names.split(","))
        return plain + [f"from {m} import {', '.join(sorted(n))}" for m, n in sorted(froms.items())]


def translate_detailed(
    source: str, *, type_hints: bool = True, fstrings: bool = True, main_guard: bool = True
) -> TranslationResult:
    """Traduce código Java y devuelve el Python junto con los avisos.

    ``source`` puede ser un archivo completo, una clase, uno o varios
    métodos, sentencias sueltas o una sola expresión.
    """
    parsed = parse(source)
    tr = _Translator(parsed.source, Options(type_hints, fstrings, main_guard))
    if parsed.errors:
        tr.warn("el código Java tiene errores de sintaxis; las partes afectadas quedaron como comentarios TODO")
    if parsed.wrapped:
        tr.warn(f"el fragmento contenía miembros de clase sueltos; se envolvió en la clase '{FRAGMENT_CLASS}'")
    code = tr.run(parsed.root)
    try:
        ast.parse(code)
    except SyntaxError as exc:  # pragma: no cover - red de seguridad
        tr.warn(f"el Python generado no es válido cerca de la línea {exc.lineno}: {exc.msg}")
    return TranslationResult(code, tr.warnings)


def translate(source: str, **options) -> str:
    """Traduce código Java a Python y devuelve solo el código."""
    return translate_detailed(source, **options).code


def translate_file(path, output=None, *, encoding: str = "utf-8", **options) -> TranslationResult:
    """Traduce un archivo ``.java``; si se da ``output`` escribe ahí el ``.py``."""
    result = translate_detailed(Path(path).read_text(encoding=encoding), **options)
    if output is not None:
        Path(output).write_text(result.code, encoding=encoding)
    return result
