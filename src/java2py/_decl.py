"""Traducción de declaraciones: clases, interfaces, enums, métodos y campos."""

from __future__ import annotations

import re

from . import _types as T
from ._core import STMT, ClassInfo, MethodInfo, Unsupported, attr_name, comment_lines, doc_text, txt
from ._expr import kids
from ._stmt import TYPE_DECLS

_KIND_OF = {
    "class_declaration": "class", "interface_declaration": "interface",
    "enum_declaration": "enum", "record_declaration": "record",
}
_SPECIAL = {("toString", 0): "__str__", ("equals", 1): "__eq__", ("hashCode", 0): "__hash__"}
_ISINSTANCE = {
    "int": "int", "float": "float", "str": "str", "char": "str", "bool": "bool", "list": "list",
    "array": "list", "stack": "list", "pq": "list", "map": "dict", "set": "set",
}
_COMMENTS = ("line_comment", "block_comment")


def modifiers(node) -> set[str]:
    for ch in node.children:
        if ch.type == "modifiers":
            return {txt(c) for c in ch.children}
    return set()


def param_info(node) -> list[tuple[str, str | None, bool]]:
    """[(nombre, tipo Java, es_varargs)] de unos ``formal_parameters``."""
    out = []
    if node is None:
        return out
    for p in kids(node):
        if p.type == "formal_parameter":
            jt = T.clean(txt(p.child_by_field_name("type")))
            dims = p.child_by_field_name("dimensions")
            if dims is not None:
                jt += "[]" * txt(dims).count("[")
            out.append((txt(p.child_by_field_name("name")), jt, False))
        elif p.type == "spread_parameter":
            tn = next(c for c in kids(p) if c.type not in ("modifiers", "variable_declarator"))
            decl = next(c for c in kids(p) if c.type == "variable_declarator")
            out.append((txt(decl.child_by_field_name("name")), T.clean(txt(tn)) + "[]", True))
    return out


def members_of(node) -> list:
    """Miembros del cuerpo de una clase/enum/interfaz (con comentarios)."""
    body = node.child_by_field_name("body")
    out = []
    if body is None:
        return out
    for ch in body.named_children:
        if ch.type == "enum_body_declarations":
            out.extend(ch.named_children)
        else:
            out.append(ch)
    return out


class DeclMixin:
    inner_nodes: list
    # ------------------------------------------------- primera pasada: símbolos
    def collect(self, node, outer: ClassInfo | None = None) -> None:
        for ch in node.named_children:
            if ch.type in TYPE_DECLS:
                self.collect(ch, self.collect_type(ch, outer))
            elif ch.type == "method_declaration" and node.type == "program":
                self.module.methods.setdefault(txt(ch.child_by_field_name("name")), []).append(
                    self.method_info(ch, force_static=True))
                self.collect(ch, outer)
            else:
                self.collect(ch, outer)

    def method_info(self, node, force_static=False) -> MethodInfo:
        params = param_info(node.child_by_field_name("parameters"))
        tn = node.child_by_field_name("type")
        return MethodInfo(
            txt(node.child_by_field_name("name")),
            [p[1] for p in params],
            T.clean(txt(tn)) if tn is not None else None,
            force_static or "static" in modifiers(node),
            any(p[2] for p in params),
        )

    def collect_type(self, node, outer) -> ClassInfo:
        ci = ClassInfo(txt(node.child_by_field_name("name")), _KIND_OF[node.type], outer=outer)
        sup = node.child_by_field_name("superclass")
        if sup is not None:
            ci.superclass = T.base(T.clean(txt(kids(sup)[0])))
        tp = node.child_by_field_name("type_parameters")
        if tp is not None:
            ci.type_params = [re.match(r"\w+", txt(p))[0] for p in kids(tp)]
        if ci.kind == "record":
            for name, jt, _ in param_info(node.child_by_field_name("parameters")):
                ci.fields[name] = (jt, False)
        for m in members_of(node):
            if m.type == "enum_constant":
                ci.constants.append(txt(m.child_by_field_name("name")))
            elif m.type in ("field_declaration", "constant_declaration"):
                jt = T.clean(txt(m.child_by_field_name("type")))
                static = "static" in modifiers(m) or ci.kind == "interface"
                for d in m.children_by_field_name("declarator"):
                    dims = d.child_by_field_name("dimensions")
                    djt = jt + "[]" * (txt(dims).count("[") if dims is not None else 0)
                    value = d.child_by_field_name("value")
                    if value is not None and value.type == "object_creation_expression":
                        vt = T.clean(txt(value.child_by_field_name("type")))
                        if T.kind(vt) == "pq" and T.kind(djt) in ("deque", "list"):
                            djt = vt
                    ci.fields[txt(d.child_by_field_name("name"))] = (djt, static)
            elif m.type == "method_declaration":
                info = self.method_info(m)
                ci.methods.setdefault(info.name, []).append(info)
            elif m.type == "constructor_declaration":
                params = param_info(m.child_by_field_name("parameters"))
                ci.methods.setdefault("<init>", []).append(MethodInfo(
                    "<init>", [p[1] for p in params], ci.name, False, any(p[2] for p in params)))
        if ci.name in self.classes:
            self.warn(f"hay dos clases llamadas '{ci.name}'; en Python quedan al mismo nivel y la segunda reemplaza a la primera", node)
        self.classes[ci.name] = ci
        if outer is not None and ci.kind == "class" and outer.kind != "interface" and "static" not in modifiers(node):
            self.inner_nodes.append((ci, node))
        return ci

    def mark_inner_classes(self) -> None:
        """Marca las clases internas (no static) que usan campos o métodos de
        instancia de su clase externa: en Python hay que pasarles esa instancia."""
        for ci, node in self.inner_nodes:
            fields = {n for n, (_, st) in ci.outer.fields.items() if not st} - set(ci.fields)
            methods = {n for n, infos in ci.outer.methods.items()
                       if n != "<init>" and not all(i.static for i in infos)} - set(ci.methods)
            stack = [node.child_by_field_name("body")]
            while stack:
                n = stack.pop()
                stack.extend(n.named_children)
                if n.type != "identifier" or n.parent is None:
                    continue
                p = n.parent
                name = txt(n)
                if p.type == "method_invocation" and p.child_by_field_name("name").id == n.id:
                    if p.child_by_field_name("object") is None and name in methods:
                        ci.needs_outer = True
                elif p.type == "field_access" and p.child_by_field_name("field").id == n.id:
                    pass
                elif name in fields:
                    declared = p.type in ("variable_declarator", "formal_parameter") \
                        and p.child_by_field_name("name").id == n.id
                    if not declared:
                        ci.needs_outer = True

    # ------------------------------------------------------------------ clases
    def take_doc(self):
        doc, self.pending_doc = self.pending_doc, None
        return doc

    def emit_doc(self, doc) -> None:
        if not doc:
            return
        lines = [ln.replace("\\", "\\\\").replace('"""', "'''") for ln in doc]
        if len(lines) == 1:
            self.emit(f'"""{lines[0]}"""')
        else:
            self.emit('"""' + lines[0])
            for ln in lines[1:]:
                self.emit(ln)
            self.emit('"""')

    def emit_class(self, node) -> None:
        ci = self.classes[txt(node.child_by_field_name("name"))]
        members = members_of(node)
        doc = self.take_doc()
        for i, m in enumerate(members):         # las clases anidadas salen al nivel superior
            if m.type in TYPE_DECLS:
                notes = []
                for c in reversed(members[:i]):
                    if c.type not in _COMMENTS:
                        break
                    notes.insert(0, c)
                for c in notes:
                    if txt(c).startswith("/**"):
                        self.pending_doc = doc_text(txt(c))
                    else:
                        self.blank(2 if self.level == 0 else 1)
                        for line in comment_lines(txt(c)):
                            self.emit(line)
                self.emit_class(m)
        mods = modifiers(node)
        bases = []
        if ci.superclass:
            if ci.superclass in self.classes or ci.superclass in T.EXCEPTIONS:
                bases.append(self.py_class_name(ci.superclass))
            else:
                self.warn(f"la clase base '{ci.superclass}' no está en el código y se omitió", node)
        for ch in node.children:
            if ch.type in ("super_interfaces", "extends_interfaces"):
                for t in kids(kids(ch)[0]):
                    b = T.base(T.clean(txt(t)))
                    if b in self.classes and b not in bases:
                        bases.append(b)
        abstract = "abstract" in mods or ci.kind == "interface"
        if abstract:
            bases.append("ABC")
            self.imports.add("from abc import ABC, abstractmethod")
        if ci.kind == "enum":
            bases.append("Enum")
            self.imports.add("from enum import Enum")
        self.blank(2 if self.level == 0 else 1)
        if ci.kind == "record":
            self.imports.add("from dataclasses import dataclass")
            self.emit("@dataclass(frozen=True)")
        self.emit(f"class {ci.name}({', '.join(bases)}):" if bases else f"class {ci.name}:")

        saved = (self.cls, self.static_ctx, self.scopes, self.loops, self.in_class_body,
                 self.global_writes, self.method_ret)
        self.cls, self.static_ctx, self.scopes, self.loops = ci, True, [{}], []
        self.global_writes = None
        self.level += 1
        start = len(self.lines)
        self.emit_doc(doc)
        static_blocks = []
        try:
            self.class_body(node, ci, members, static_blocks)
        finally:
            if not any(ln.strip() for ln in self.lines[start:]):
                self.emit("pass")
            self.level -= 1
            for blk in static_blocks:           # bloques ``static { ... }``
                self.blank(1)
                self.statements(blk)
            (self.cls, self.static_ctx, self.scopes, self.loops, self.in_class_body,
             self.global_writes, self.method_ret) = saved
        self.blank(2 if self.level == 0 else 1)

    def class_body(self, node, ci, members, static_blocks) -> None:
        real = [m for m in members if m.type not in _COMMENTS]

        def next_real(i):
            return next((m for m in members[i + 1:] if m.type not in _COMMENTS), None)

        def is_inst_field(m):
            return m is not None and m.type == "field_declaration" and "static" not in modifiers(m) \
                and ci.kind != "interface"

        # Constantes de enum y componentes de record.
        for m in real:
            if m.type == "enum_constant":
                argn = self.arg_nodes(m)
                self.in_class_body = True
                try:
                    vals = [self.expr(a).code for a in argn]
                except Unsupported:
                    vals = []
                self.in_class_body = False
                name = txt(m.child_by_field_name("name"))
                if not vals:
                    self.imports.add("from enum import auto")
                    self.emit(f"{name} = auto()")
                else:
                    self.emit(f"{name} = {vals[0] if len(vals) == 1 else '(' + ', '.join(vals) + ')'}")
        if ci.kind == "record":
            for name, (jt, _) in ci.fields.items():
                self.emit(f"{attr_name(name)}: {self._hint(jt) or 'object'}")

        # Campos de instancia: sus valores iniciales van dentro de __init__.
        self.static_ctx = False
        with self.capture() as field_lines:
            prev = None
            for i, m in enumerate(members):
                if m.type in _COMMENTS:
                    same_row = prev is not None and m.start_point[0] == prev.end_point[0]
                    if same_row and is_inst_field(prev) and self.lines:
                        self.lines[-1] += "  " + comment_lines(txt(m))[0]
                    elif not same_row and is_inst_field(next_real(i)):
                        for line in comment_lines(txt(m)):
                            self.emit(line)
                    continue
                prev = m
                if is_inst_field(m) and ci.kind != "record":
                    self.field_inits(m, instance=True)
        self.static_ctx = True

        ctors = [m for m in real if m.type in ("constructor_declaration", "compact_constructor_declaration")]
        groups: dict[str, list] = {}
        for m in real:
            if m.type == "method_declaration":
                groups.setdefault(txt(m.child_by_field_name("name")), []).append(m)
        implicit_super = ci.superclass in self.classes and ci.kind == "class"
        state = {"init": bool(ctors) or ci.kind in ("interface", "record"), "ctors": False}
        outer_lines = ["self._outer = outer"] if ci.needs_outer else []
        outer_param = ", outer" if ci.needs_outer else ""

        def ensure_init():
            if state["init"]:
                return
            state["init"] = True
            if not field_lines and not implicit_super and not outer_lines:
                return
            if ci.kind == "enum":
                return
            self.blank(1)
            self.emit(f"def __init__(self{outer_param}):")
            self.level += 1
            if implicit_super:
                self.emit("super().__init__()")
            for line in outer_lines + self.init_lines(field_lines, None):
                self.emit(line)
            self.level -= 1
            self.blank(1)

        done = set()
        prev = None
        for i, m in enumerate(members):
            if m.type in _COMMENTS:
                same_row = prev is not None and m.start_point[0] == prev.end_point[0]
                nxt = next_real(i)
                if same_row and is_inst_field(prev):
                    continue
                if not same_row and (is_inst_field(nxt) or (nxt is not None and nxt.type in TYPE_DECLS)):
                    continue
                if txt(m).startswith("/**") and nxt is not None and nxt.type in (
                        "method_declaration", "constructor_declaration"):
                    self.pending_doc = doc_text(txt(m))
                    continue
                if same_row and prev.type == "field_declaration" and self.lines and self.lines[-1].strip():
                    self.lines[-1] += "  " + comment_lines(txt(m))[0]
                    continue
                if nxt is not None and nxt.type in ("method_declaration", "constructor_declaration"):
                    ensure_init()
                    self.blank(1)
                for line in comment_lines(txt(m)):
                    self.emit(line)
                continue
            prev = m
            if m.type in ("field_declaration", "constant_declaration"):
                if not is_inst_field(m):
                    self.in_class_body = True
                    self.field_inits(m, instance=False)
                    self.in_class_body = False
            elif m.type in ("constructor_declaration", "compact_constructor_declaration"):
                if not state["ctors"]:
                    state["ctors"] = True
                    self.emit_ctors(ctors, ci, field_lines, implicit_super)
            elif m.type == "method_declaration":
                ensure_init()
                name = txt(m.child_by_field_name("name"))
                if name not in done:
                    done.add(name)
                    self.emit_method_group(groups[name], ci)
            elif m.type == "static_initializer":
                static_blocks.append(kids(m)[0])
            elif m.type == "block":
                self.todo(m, "bloque inicializador de instancia: mueve este código a __init__")
            elif m.type in TYPE_DECLS or m.type == "enum_constant":
                pass
            else:
                self.todo(m, f"miembro de clase no soportado ({m.type})")
        ensure_init()
        own = {name: [i for i in infos if not i.static and not i.params] for name, infos in ci.methods.items()}
        if own.get("hasNext") and own.get("next"):
            self.blank(1)
            self.emit("# Protocolo de iteración de Python, apoyado en hasNext()/next() de Java.")
            self.emit("def __iter__(self):")
            self.emit("    return self")
            self.blank(1)
            self.emit("def __next__(self):")
            self.emit("    if not self.hasNext():")
            self.emit("        raise StopIteration")
            self.emit("    return self.next()")
        if own.get("iterator"):
            self.blank(1)
            self.emit("def __iter__(self):")
            self.emit('    """Permite ``for x in objeto`` (equivale a implementar Iterable)."""')
            self.emit("    return iter(self.iterator())")
        if ci.kind == "enum" and "toString" not in ci.methods:
            self.blank(1)
            self.emit("def __str__(self) -> str:")
            self.emit("    return self.name")

    def field_inits(self, node, instance: bool) -> None:
        jt = T.clean(txt(node.child_by_field_name("type")))
        for d in node.children_by_field_name("declarator"):
            raw = txt(d.child_by_field_name("name"))
            name = self.cls.py_field(raw)
            dims = d.child_by_field_name("dimensions")
            djt = jt + "[]" * (txt(dims).count("[") if dims is not None else 0)
            value = d.child_by_field_name("value")
            if instance and value is None:
                self.emit(f"#default:{raw}")        # marca: valor por defecto, omitible

            def build(name=name, djt=djt, value=value):
                if value is None:
                    code = T.default_value(djt)
                else:
                    v = self.coerce(self.expr_decl(value, djt), djt)
                    if v.prec == STMT:
                        raise Unsupported("llamada sin valor usada como valor")
                    code = v.code
                return [f"self.{name} = {code}" if instance else f"{name} = {code}"]

            self.simple(node, build)

    # ------------------------------------------------------------ constructores
    def emit_ctors(self, ctors, ci, field_lines, implicit_super) -> None:
        outer_lines = ["self._outer = outer"] if ci.needs_outer else []
        if len(ctors) == 1:
            self.emit_ctor(ctors[0], "__init__", outer_lines + field_lines, implicit_super)
            return
        versions = []
        for k, c in enumerate(ctors, 1):
            vname = f"_init_v{k}"
            self.emit_ctor(c, vname, None, implicit_super)
            params = param_info(c.child_by_field_name("parameters"))
            versions.append((vname, [p[1] for p in params], any(p[2] for p in params), False))
        self.blank(1)
        self.emit(f"def __init__(self{', outer' if ci.needs_outer else ''}, *args):")
        self.level += 1
        self.emit(f'"""Java tiene {len(ctors)} constructores; aquí se elige según los argumentos."""')
        for line in outer_lines + self.init_lines(field_lines, None):
            self.emit(line)
        self.dispatch(versions, ci, f"{ci.name}()", returns=False)
        self.level -= 1
        self.blank(1)

    def emit_ctor(self, node, pyname, field_lines, implicit_super) -> None:
        params = param_info(node.child_by_field_name("parameters"))
        doc = self.take_doc()
        self.blank(1)
        saved = (self.static_ctx, self.method_ret, self.loops)
        self.static_ctx, self.method_ret, self.loops = False, None, []
        self.scopes.append({})
        self.func_depth += 1
        try:
            plist = ["self"] + (["outer"] if self.cls.needs_outer and pyname == "__init__" else [])
            plist += self.param_list(params)
            self.emit(f"def {pyname}({', '.join(plist)}):")
            body = node.child_by_field_name("body")
            stmts = list(body.named_children) if body is not None else []
            real = [s for s in stmts if s.type not in _COMMENTS]
            explicit = real[0] if real and real[0].type == "explicit_constructor_invocation" else None

            def head():
                self.emit_doc(doc)
                if explicit is not None:
                    self.stmt(explicit)
                elif implicit_super:
                    self.emit("super().__init__()")
                which = explicit.child_by_field_name("constructor").type if explicit is not None else None
                if field_lines and which != "this":
                    for line in self.init_lines(field_lines, body):
                        self.emit(line)
                elif field_lines and field_lines[0] == "self._outer = outer":
                    self.emit(field_lines[0])

            rest = [s for s in stmts if explicit is None or s.id != explicit.id]
            self.body(rest, head=head)
        finally:
            self.func_depth -= 1
            self.scopes.pop()
            self.static_ctx, self.method_ret, self.loops = saved
        self.blank(1)

    def init_lines(self, field_lines, ctor_body) -> list[str]:
        """Líneas ``self.x = ...`` de los campos. Un campo sin valor inicial que
        el constructor asigna directamente no necesita su valor por defecto."""
        assigned = set()
        if ctor_body is not None:
            for st in kids(ctor_body):
                e = kids(st)[0] if st.type == "expression_statement" and kids(st) else None
                while e is not None and e.type == "assignment_expression":
                    left = e.child_by_field_name("left")
                    if left.type == "identifier":
                        assigned.add(txt(left))
                    elif left.type == "field_access" and left.child_by_field_name("object").type == "this":
                        assigned.add(txt(left.child_by_field_name("field")))
                    e = e.child_by_field_name("right")
        out, skip = [], False
        for line in field_lines:
            if line.startswith("#default:"):
                skip = line[9:] in assigned
                continue
            if not skip:
                out.append(line)
            skip = False
        return out

    def param_list(self, params) -> list[str]:
        out = []
        for name, jt, varargs in params:
            pn = self.declare(name, jt)
            if varargs:
                out.append("*" + pn)
            else:
                hint = self.hint(jt)
                out.append(f"{pn}: {hint}" if hint else pn)
        return out

    # ------------------------------------------------------------------ métodos
    def s_method_declaration(self, node):
        """Método suelto (fuera de una clase): se traduce como función."""
        name = txt(node.child_by_field_name("name"))
        if self.cls.is_module and self.level == 0:
            group = [c for c in node.parent.named_children
                     if c.type == "method_declaration" and txt(c.child_by_field_name("name")) == name]
            if group[0].id == node.id:
                self.emit_method_group(group, self.module)
            return
        self.emit_method_group([node], self.cls)

    def emit_method_group(self, nodes, ci) -> None:
        name = txt(nodes[0].child_by_field_name("name"))
        if len(nodes) == 1:
            self.emit_method(nodes[0], ci, None)
            return
        versions = []
        for k, m in enumerate(nodes, 1):
            vname = f"_{name}_v{k}"
            self.emit_method(m, ci, vname)
            params = param_info(m.child_by_field_name("parameters"))
            static = "static" in modifiers(m) or ci.is_module
            versions.append((vname, [p[1] for p in params], any(p[2] for p in params), static))
        all_static = all(v[3] for v in versions)
        self.blank(2 if self.level == 0 else 1)
        if ci.is_module:
            self.emit(f"def {attr_name(name)}(*args):")
        elif all_static:
            self.emit("@staticmethod")
            self.emit(f"def {attr_name(name)}(*args):")
        else:
            self.emit(f"def {attr_name(name)}(self, *args):")
        self.level += 1
        self.emit(f'"""Java tiene {len(nodes)} versiones de {name} (sobrecarga); aquí se elige según los argumentos."""')
        self.dispatch(versions, ci, name, returns=True)
        self.level -= 1
        self.blank(2 if self.level == 0 else 1)

    def dispatch(self, versions, ci, what, returns) -> None:
        by_arity: dict[int, list] = {}
        for v in versions:
            by_arity.setdefault(len(v[1]), []).append(v)
        for k, (vname, ptypes, varargs, static) in enumerate(versions):
            n = len(ptypes)
            cond = f"len(args) >= {n - 1}" if varargs else f"len(args) == {n}"
            rivals = [v for v in by_arity[n] if v[0] != vname]
            tests = []
            for i, jt in enumerate(ptypes):
                if any(r[1][i] != jt for r in rivals):
                    kind = self.k(jt)
                    py = T.base(jt) if kind == "user" else _ISINSTANCE.get(kind)
                    if py:
                        tests.append(f"isinstance(args[{i}], {py})")
            if rivals and not tests and vname != by_arity[n][-1][0]:
                self.warn(f"no se pudo distinguir por tipo entre las versiones de {what} con {n} argumentos")
            cond = " and ".join([cond] + tests)
            if ci.is_module:
                target = vname
            elif static:
                target = f"{ci.name}.{vname}"
            else:
                target = f"self.{vname}"
            self.emit(f"{'if' if k == 0 else 'elif'} {cond}:")
            self.emit(f"    {'return ' if returns else ''}{target}(*args)")
        self.emit("else:")
        self.emit(f'    raise TypeError("ninguna versión de {what} acepta esos argumentos")')

    def emit_method(self, node, ci, pyname) -> None:
        name = txt(node.child_by_field_name("name"))
        mods = modifiers(node)
        params = param_info(node.child_by_field_name("parameters"))
        body = node.child_by_field_name("body")
        tn = node.child_by_field_name("type")
        ret = T.clean(txt(tn)) if tn is not None else None
        static = "static" in mods or ci.is_module
        doc = self.take_doc()
        special = None if static or pyname else _SPECIAL.get((name, len(params)))
        pyname = pyname or special or attr_name(name)

        self.blank(2 if self.level == 0 else 1)
        if static and not ci.is_module:
            self.emit("@staticmethod")
        if body is None and not ci.is_module:
            self.imports.add("from abc import ABC, abstractmethod")
            self.emit("@abstractmethod")

        saved = (self.static_ctx, self.method_ret, self.loops, self.global_writes, self.cls)
        self.cls = ci
        self.static_ctx, self.method_ret, self.loops = static, ret, []
        self.scopes.append({})
        self.func_depth += 1
        try:
            plist = ([] if static else ["self"]) + self.param_list(params)
            hint = self.hint(ret)
            self.emit(f"def {pyname}({', '.join(plist)}){' -> ' + hint if hint else ''}:")
            if ci.is_module:
                self.global_writes = set()
            mark = len(self.lines)
            if body is None:
                self.level += 1
                self.emit_doc(doc)
                self.emit("pass")
                self.level -= 1
            else:
                self.body(body, head=lambda: self.emit_doc(doc))
            if ci.is_module and self.global_writes:
                at = mark
                indent = "    " * (self.level + 1)
                if doc:                                     # después del docstring
                    at += 1 if len(doc) == 1 else len(doc) + 1
                self.lines.insert(at, indent + "global " + ", ".join(sorted(self.global_writes)))
        finally:
            self.func_depth -= 1
            self.scopes.pop()
            self.static_ctx, self.method_ret, self.loops, self.global_writes, self.cls = saved

        if name == "compareTo" and len(params) == 1 and not static and special is None and body is not None:
            self.blank(1)
            self.emit("def __lt__(self, other) -> bool:")
            self.emit('    """Permite usar <, sorted() y heapq con estos objetos (equivale a Comparable)."""')
            self.emit(f"    return self.{pyname}(other) < 0")
        if name == "main" and static and len(params) == 1 and T.base(params[0][1]) == "String":
            self.mains.append("main" if ci.is_module else f"{ci.name}.main")
        self.blank(2 if self.level == 0 else 1)
