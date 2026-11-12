"""Traducción de sentencias Java (if, for, while, switch, try...)."""

from __future__ import annotations

import re

from . import _types as T
from ._core import CMP, NOT, P, STMT, UNARY, E, Unsupported, comment_lines, doc_text, local_name, txt
from ._expr import SB_MUTATORS, kids

TYPE_DECLS = ("class_declaration", "interface_declaration", "enum_declaration", "record_declaration")
_DECLS = TYPE_DECLS + ("method_declaration", "constructor_declaration")
_PATTERN = re.compile(r'^-?\d[\w.]*$|^".*"$|^[A-Za-z_]\w*(\.[A-Za-z_]\w*)+$', re.S)


def _walk(node):
    yield node
    for ch in node.named_children:
        yield from _walk(ch)


class StmtMixin:
    pending_doc = None
    method_ret = None

    # ------------------------------------------------------------- despacho
    def stmt(self, node) -> None:
        t = node.type
        if t in ("line_comment", "block_comment"):
            for line in comment_lines(txt(node)):
                self.emit(line)
            return
        fn = getattr(self, "s_" + t, None)
        if fn is None:
            self.todo(node, f"sentencia no soportada ({t})")
            return
        saved = (self.pre, self.post, len(self.lines), self.level, len(self.scopes), len(self.loops))
        self.pre = self.post = None
        try:
            fn(node)
        except Unsupported as exc:
            del self.lines[saved[2]:]
            self.level = saved[3]
            del self.scopes[saved[4]:]
            del self.loops[saved[5]:]
            self.todo(node, str(exc))
        finally:
            self.pre, self.post = saved[0], saved[1]

    def statements(self, node_or_list) -> None:
        """Traduce una secuencia de sentencias, conservando los comentarios."""
        children = node_or_list if isinstance(node_or_list, list) else node_or_list.named_children
        prev = None
        for i, ch in enumerate(children):
            if ch.type in ("line_comment", "block_comment"):
                nxt = next((c for c in children[i + 1:] if c.type not in ("line_comment", "block_comment")), None)
                is_decl = nxt is not None and nxt.type in _DECLS
                if ch.type == "block_comment" and txt(ch).startswith("/**") and is_decl:
                    self.pending_doc = doc_text(txt(ch))
                    continue
                same_row = (
                    prev is not None and ch.type == "line_comment"
                    and ch.start_point[0] == prev.end_point[0] == prev.start_point[0]
                )
                if same_row and self.lines and self.lines[-1].strip() and not self.lines[-1].strip().startswith("#"):
                    self.lines[-1] += "  " + comment_lines(txt(ch))[0]
                    continue
                if is_decl:
                    self.blank(2 if self.level == 0 else 1)
            self.stmt(ch)
            if ch.type not in ("line_comment", "block_comment"):
                prev = ch

    def body(self, node, tail=None, head=None) -> None:
        """Cuerpo indentado de un bloque (o de una sola sentencia)."""
        self.level += 1
        start = len(self.lines)
        with self.scope():
            if head:
                head()
            if isinstance(node, list):
                self.statements(node)
            elif node.type in ("block", "constructor_body"):
                self.statements(node)
            else:
                self.stmt(node)
            if tail:
                tail()
        if not any(ln.strip() and not ln.strip().startswith("#") for ln in self.lines[start:]):
            self.emit("pass")
        self.level -= 1

    def simple(self, node, build, post_ok=True) -> None:
        """Sentencia simple: permite sacar ``i++`` o lambdas a líneas aparte."""
        saved = (self.pre, self.post)
        self.pre, self.post = [], ([] if post_ok else None)
        try:
            lines = build()
            pre, post = self.pre, self.post or []
        except Unsupported as exc:
            self.pre, self.post = saved
            self.todo(node, str(exc))
            return
        finally:
            self.pre, self.post = saved
        for line in pre + lines + post:
            self.emit(line)

    # ------------------------------------------------------ sentencias simples
    def s_expression_statement(self, node):
        self.stmt_expression(kids(node)[0], node)

    def stmt_expression(self, e, node) -> None:
        if e.type == "switch_expression":
            self.s_switch_expression(e)
            return

        def build():
            if e.type == "assignment_expression":
                return [self.assign_code(e)]
            if e.type == "update_expression":
                target = kids(e)[0]
                self.note_write(target)
                t = self.expr(target)
                sign = "+" if any(c.type == "++" for c in e.children) else "-"
                if self.k(t.type) == "char":
                    return [f"{t.code} = chr(ord({t.code}) {sign} 1)"]
                return [f"{t.code} {sign}= 1"]
            if e.type == "method_invocation":
                code = self.sb_statement(e)
                if code:
                    return [code]
            v = self.expr(e)
            return [] if v.code == "None" else [v.code]

        self.simple(node, build)

    def sb_statement(self, e) -> str | None:
        """``sb.append(x);`` -> ``sb += str(x)`` (StringBuilder es un str en Python)."""
        root = e
        while (
            root.type == "method_invocation"
            and txt(root.child_by_field_name("name")) in SB_MUTATORS
            and root.child_by_field_name("object") is not None
        ):
            root = root.child_by_field_name("object")
        if root is e or root.type not in ("identifier", "field_access"):
            return None
        r = self.expr(root)
        if self.k(r.type) != "sb":
            return None
        self.note_write(root)
        val = self.expr(e)
        if val.code.startswith(r.code + " + "):
            return f"{r.code} += {val.code[len(r.code) + 3:]}"
        return f"{r.code} = {val.code}"

    def s_local_variable_declaration(self, node):
        jt = T.clean(txt(node.child_by_field_name("type")))
        for d in node.children_by_field_name("declarator"):
            name = txt(d.child_by_field_name("name"))
            dims = d.child_by_field_name("dimensions")
            djt = jt + "[]" * (txt(dims).count("[") if dims is not None else 0)
            value = d.child_by_field_name("value")

            def build(name=name, djt=djt, value=value):
                if value is None:
                    pn = self.declare(name, djt)
                    hint = self.hint(djt)
                    return [f"{pn}: {hint}" if hint else f"{pn} = None"]
                if djt == "var":
                    v = self.expr(value)
                    rec = v.type
                else:
                    v = self.coerce(self.expr_decl(value, djt), djt)
                    rec = djt
                    if self.k(v.type) == "pq" and self.k(djt) in ("deque", "list"):
                        rec = v.type
                if v.prec == STMT:
                    raise Unsupported("llamada sin valor usada como valor")
                return [f"{self.declare(name, rec)} = {v.code}"]

            self.simple(node, build)

    def s_return_statement(self, node):
        ks = kids(node)

        def build():
            if not ks:
                return ["return"]
            v = self.coerce(self.expr(ks[0]), self.method_ret)
            return [f"return {v.code}"]

        self.simple(node, build, post_ok=False)

    def s_throw_statement(self, node):
        self.simple(node, lambda: [f"raise {self.expr(kids(node)[0]).code}"], post_ok=False)

    def s_assert_statement(self, node):
        ks = kids(node)
        code = f"assert {self.expr(ks[0]).code}"
        if len(ks) > 1:
            code += f", {self.expr(ks[1]).code}"
        self.emit(code)

    def s_explicit_constructor_invocation(self, node):
        which = node.child_by_field_name("constructor").type

        def build():
            codes = [x.code for x in self.args(self.arg_nodes(node))]
            if which != "super" and self.cls.needs_outer:
                codes.insert(0, "self._outer")
            a = ", ".join(codes)
            return [f"super().__init__({a})" if which == "super" else f"self.__init__({a})"]

        self.simple(node, build)

    def s_block(self, node):
        with self.scope():
            self.statements(node)

    def s_labeled_statement(self, node):
        self.stmt(kids(node)[-1])

    def s_synchronized_statement(self, node):
        self.s_block(kids(node)[-1])

    def s_yield_statement(self, node):
        raise Unsupported("'yield' dentro de un switch")

    def s_ERROR(self, node):
        raise Unsupported("Java con error de sintaxis")

    def s_package_declaration(self, node):
        pass

    s_import_declaration = s_package_declaration

    def s_class_declaration(self, node):
        self.emit_class(node)

    s_interface_declaration = s_enum_declaration = s_record_declaration = s_class_declaration

    def s_annotation_type_declaration(self, node):
        pass

    def s_method_declaration(self, node):
        self.emit_method_group([node], self.cls) if not self.cls.is_module else self.emit_module_function(node)

    # --------------------------------------------------------------- control
    def s_if_statement(self, node):
        cur, word = node, "if"
        while True:
            cn = cur.child_by_field_name("condition")
            if word == "if" and self.safe_to_hoist(cn):
                self.pre = []           # ``if (--x == 0)`` -> ``x -= 1`` antes del if
                c = self.cond(cn)
                for line in self.pre:
                    self.emit(line)
                self.pre = None
            else:
                c = self.cond(cn)
            self.emit(f"{word} {c.code}:")
            self.body(cur.child_by_field_name("consequence"))
            alt = cur.child_by_field_name("alternative")
            if alt is None:
                return
            if alt.type != "if_statement":
                self.emit("else:")
                self.body(alt)
                return
            cur, word = alt, "elif"

    @staticmethod
    def safe_to_hoist(cond) -> bool:
        """True si los ``++x`` / asignaciones de la condición se evalúan siempre
        (no están a la derecha de ``&&``/``||`` ni dentro de un ``?:``)."""
        def visit(node, risky):
            if node.type in ("update_expression", "assignment_expression", "lambda_expression") and risky:
                return False
            for i, ch in enumerate(node.named_children):
                r = risky
                if node.type == "binary_expression" and i == 1 and \
                        txt(node.child_by_field_name("operator")) in ("&&", "||"):
                    r = True
                if node.type == "ternary_expression" and i > 0:
                    r = True
                if not visit(ch, r):
                    return False
            return True
        return visit(cond, False)

    def loop(self, body, cont=None, tail=None):
        self.loops.append({"kind": "loop", "cont": cont})
        try:
            self.body(body, tail=tail)
        finally:
            self.loops.pop()

    def s_while_statement(self, node):
        if self.while_iterator(node):
            return
        c = self.cond(node.child_by_field_name("condition"))
        self.emit(f"while {c.code}:")
        self.loop(node.child_by_field_name("body"))

    def while_iterator(self, node) -> bool:
        """``while (it.hasNext()) { T x = it.next(); ... }`` -> ``for x in it:``"""
        cn = node.child_by_field_name("condition")
        cn = kids(cn)[0] if cn.type == "parenthesized_expression" else cn
        body = node.child_by_field_name("body")
        if cn.type != "method_invocation" or txt(cn.child_by_field_name("name")) != "hasNext":
            return False
        obj = cn.child_by_field_name("object")
        stmts = kids(body) if body.type == "block" else []
        if obj is None or not stmts or stmts[0].type != "local_variable_declaration":
            return False
        decls = stmts[0].children_by_field_name("declarator")
        value = decls[0].child_by_field_name("value") if len(decls) == 1 else None
        if value is None or txt(value).replace(" ", "") != txt(obj).replace(" ", "") + ".next()":
            return False
        for n in _walk(body):
            if n.type == "method_invocation" and n.id != value.id and n.child_by_field_name("object") is not None \
                    and txt(n.child_by_field_name("object")) == txt(obj):
                return False                        # usa el iterador de otra forma (remove, etc.)
        it = self.expr(obj)
        with self.scope():
            jt = T.clean(txt(stmts[0].child_by_field_name("type")))
            pn = self.declare(txt(decls[0].child_by_field_name("name")), jt)
            self.emit(f"for {pn} in {it.code}:")
            rest = [c for c in body.named_children if c.id != stmts[0].id]
            self.loop(rest)
        return True

    def s_do_statement(self, node):
        c = self.cond(node.child_by_field_name("condition"))

        def check():
            self.emit(f"if {self.negate(c).code}:")
            self.emit("    break")

        self.emit("while True:")
        self.loop(node.child_by_field_name("body"), cont=check, tail=check)

    def s_for_statement(self, node):
        inits = node.children_by_field_name("init")
        cond = node.child_by_field_name("condition")
        updates = node.children_by_field_name("update")
        body = node.child_by_field_name("body")
        with self.scope():
            rng = self.for_range(inits, cond, updates, body)
            if rng:
                self.emit(f"for {rng[0]} in {rng[1]}:")
                self.loop(body)
                return
            for init in inits:
                if init.type == "local_variable_declaration":
                    self.s_local_variable_declaration(init)
                else:
                    self.stmt_expression(init, init)
            self.emit(f"while {self.cond(cond).code if cond is not None else 'True'}:")

            def step():
                for u in updates:
                    self.stmt_expression(u, u)

            self.loop(body, cont=step, tail=step)

    def for_range(self, inits, cond, updates, body):
        """Detecta el ``for`` clásico con contador y lo convierte en ``range``."""
        if len(inits) != 1 or cond is None or len(updates) != 1:
            return None
        init = inits[0]
        if init.type != "local_variable_declaration":
            return None
        decls = init.children_by_field_name("declarator")
        jt = T.clean(txt(init.child_by_field_name("type")))
        if len(decls) != 1 or self.k(jt) != "int":
            return None
        value = decls[0].child_by_field_name("value")
        var = txt(decls[0].child_by_field_name("name"))
        if value is None or cond.type != "binary_expression":
            return None
        left, right = cond.child_by_field_name("left"), cond.child_by_field_name("right")
        op = txt(cond.child_by_field_name("operator"))
        if left.type != "identifier" or txt(left) != var or op not in ("<", "<=", ">", ">="):
            return None
        u, step_node = updates[0], None
        if u.type == "update_expression":
            target = kids(u)[0]
            up = any(c.type == "++" for c in u.children)
        elif u.type == "assignment_expression" and txt(u.child_by_field_name("operator")) in ("+=", "-="):
            target = u.child_by_field_name("left")
            up = txt(u.child_by_field_name("operator")) == "+="
            step_node = u.child_by_field_name("right")
        else:
            return None
        if target.type != "identifier" or txt(target) != var or up != (op in ("<", "<=")):
            return None
        bound_names = {txt(n) for n in _walk(right) if n.type == "identifier"}
        if var in bound_names or (step_node is not None and var in {txt(n) for n in _walk(step_node)}):
            return None
        for n in _walk(body):
            tgt = None
            if n.type == "assignment_expression":
                tgt = n.child_by_field_name("left")
            elif n.type == "update_expression":
                tgt = kids(n)[0]
            if tgt is not None and tgt.type == "identifier" and (txt(tgt) == var or txt(tgt) in bound_names):
                return None
        try:
            start, stop = self.expr(value), self.expr(right)
            step = self.expr(step_node) if step_node is not None else E("1")
        except Unsupported:
            return None
        if self.k(stop.type) not in ("int", None) or self.k(start.type) not in ("int", None):
            return None
        stop_code = stop.code if op in ("<", ">") else self.plus(stop, 1 if up else -1)
        pn = self.declare(var, jt)
        if up and step.code == "1":
            return pn, (f"range({stop_code})" if start.code == "0" else f"range({start.code}, {stop_code})")
        step_code = step.code if up else f"-{P(step, UNARY)}"
        return pn, f"range({start.code}, {stop_code}, {step_code})"

    def s_enhanced_for_statement(self, node):
        jt = T.clean(txt(node.child_by_field_name("type")))
        value = node.child_by_field_name("value")
        if (
            value.type == "method_invocation"
            and txt(value.child_by_field_name("name")) == "toCharArray"
            and value.child_by_field_name("object") is not None
        ):
            it = self.expr(value.child_by_field_name("object"))
        else:
            it = self.expr(value)
        if jt == "var":
            jt = T.elem(it.type, self.user)
        with self.scope():
            pn = self.declare(txt(node.child_by_field_name("name")), jt)
            self.emit(f"for {pn} in {it.code}:")
            self.loop(node.child_by_field_name("body"))

    def s_break_statement(self, node):
        if kids(node):
            raise Unsupported("'break' con etiqueta (Python no tiene; usa una bandera o una función)")
        if self.loops and self.loops[-1]["kind"] == "switch":
            raise Unsupported("'break' en medio de un case de switch")
        self.emit("break")

    def s_continue_statement(self, node):
        if kids(node):
            raise Unsupported("'continue' con etiqueta (Python no tiene; usa una bandera o una función)")
        for entry in reversed(self.loops):
            if entry["kind"] == "loop":
                if entry["cont"]:
                    entry["cont"]()
                break
        self.emit("continue")

    # ------------------------------------------------------------- try/catch
    def s_try_statement(self, node):
        resources = node.child_by_field_name("resources")
        catches = [c for c in node.children if c.type == "catch_clause"]
        final = next((c for c in node.children if c.type == "finally_clause"), None)
        body = node.child_by_field_name("body")
        with self.scope():
            items = []
            if resources is not None:
                for r in kids(resources):
                    name, value = r.child_by_field_name("name"), r.child_by_field_name("value")
                    if name is not None and value is not None:
                        v = self.expr(value)
                        tn = r.child_by_field_name("type")
                        items.append(f"{v.code} as {self.declare(txt(name), T.clean(txt(tn)) if tn else v.type)}")
                    else:
                        items.append(self.expr(kids(r)[0]).code)
            wrap = bool(catches or final) or not items
            if wrap:
                self.emit("try:")
            if items:
                if wrap:
                    self.level += 1
                self.emit(f"with {', '.join(items)}:")
                self.body(body)
                if wrap:
                    self.level -= 1
            else:
                self.body(body)
            for c in catches:
                param = next(k for k in kids(c) if k.type == "catch_formal_parameter")
                types = [T.clean(txt(t)) for t in kids(next(k for k in kids(param) if k.type == "catch_type"))]
                names = []
                for t in types:
                    n = self.py_class_name(t, catching=True)
                    if n not in names:
                        names.append(n)
                name = txt(param.child_by_field_name("name"))
                spec = names[0] if len(names) == 1 else "(" + ", ".join(names) + ")"
                with self.scope():
                    self.emit(f"except {spec} as {self.declare(name, types[0])}:")
                    self.body(c.child_by_field_name("body"))
            if final is not None:
                self.emit("finally:")
                self.body(kids(final)[0])

    s_try_with_resources_statement = s_try_statement

    # ----------------------------------------------------------------- switch
    def s_switch_expression(self, node):
        subj = self.cond(node.child_by_field_name("condition"))
        groups, pending, pending_default = [], [], False
        for g in kids(node.child_by_field_name("body")):
            ks = kids(g)
            labels = [k for k in ks if k.type == "switch_label"]
            stmts = [k for k in g.named_children if k.type != "switch_label"]
            for lab in labels:
                if kids(lab):
                    pending += kids(lab)
                else:
                    pending_default = True
            real = [s for s in stmts if s.type not in ("line_comment", "block_comment")]
            if g.type != "switch_rule" and not real:
                continue                     # etiquetas agrupadas: case 1: case 2:
            if len(real) == 1 and real[0].type == "block":
                stmts = real[0].named_children
                real = kids(real[0])
            fall = False
            if g.type != "switch_rule":
                if real and real[-1].type == "break_statement" and not kids(real[-1]):
                    stmts = [s for s in stmts if s.id != real[-1].id]
                elif not real or real[-1].type not in ("return_statement", "throw_statement", "continue_statement"):
                    fall = True
            groups.append([None if pending_default else pending, stmts, fall])
            pending, pending_default = [], False
        if groups:
            groups[-1][2] = False
        default = [g for g in groups if g[0] is None]
        if default and groups[-1][0] is not None and not any(g[2] for g in groups):
            groups = [g for g in groups if g[0] is not None] + default
        values = [None if g[0] is None else self.case_values(g[0], subj) for g in groups]
        use_match = all(v is None or all(_PATTERN.match(x) for x in v) for v in values)
        s = subj.code
        if not use_match and not re.fullmatch(r"[\w.]+", s):
            self.emit(f"valor = {s}")
            s = "valor"
        if use_match:
            self.emit(f"match {s}:")
            self.level += 1
        first = True
        for (labels, stmts, fall), vals in zip(groups, values):
            if use_match:
                self.emit(f"case {' | '.join(vals) if vals else '_'}:")
            elif vals is None:
                self.emit("else:" if not first else "if True:")
            else:
                test = f"{P(E(s), CMP + 1)} == {vals[0]}" if len(vals) == 1 else f"{s} in ({', '.join(vals)})"
                self.emit(f"{'if' if first else 'elif'} {test}:")
            first = False
            self.loops.append({"kind": "switch"})
            try:
                def note():
                    self.warn("un 'case' sin 'break' continúa al siguiente en Java (fall-through); revísalo")
                    self.emit("# TODO(java2py): en Java este case sigue ejecutando el siguiente (no tiene break)")

                self.body(list(stmts), tail=note if fall else None)
            finally:
                self.loops.pop()
        if use_match:
            self.level -= 1


__all__ = ["StmtMixin", "TYPE_DECLS", "local_name"]
