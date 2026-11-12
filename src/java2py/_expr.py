"""Traducción de expresiones Java a expresiones Python."""

from __future__ import annotations

import re
import textwrap

from . import _types as T
from ._core import (
    ADD, AND, ATOM, BAND, BOR, BXOR, CMP, E, LAMBDA, MUL, NOT, OR, P, SHIFT, STMT, TERN, UNARY,
    Unsupported, attr_name, local_name, txt,
)

_BIN_PREC = {
    "||": OR, "&&": AND, "|": BOR, "^": BXOR, "&": BAND, "<<": SHIFT, ">>": SHIFT, ">>>": SHIFT,
    "+": ADD, "-": ADD, "*": MUL, "/": MUL, "%": MUL,
}
_CONSTANTS = {
    "Integer.MAX_VALUE": ("2**31 - 1", ADD, "int"),
    "Integer.MIN_VALUE": ("-2**31", UNARY, "int"),
    "Long.MAX_VALUE": ("2**63 - 1", ADD, "long"),
    "Long.MIN_VALUE": ("-2**63", UNARY, "long"),
    "Double.MAX_VALUE": ("sys.float_info.max", ATOM, "double"),
    "Double.MIN_VALUE": ("5e-324", ATOM, "double"),
    "Float.MAX_VALUE": ("sys.float_info.max", ATOM, "double"),
    "Double.POSITIVE_INFINITY": ('float("inf")', ATOM, "double"),
    "Double.NEGATIVE_INFINITY": ('float("-inf")', ATOM, "double"),
    "Float.POSITIVE_INFINITY": ('float("inf")', ATOM, "double"),
    "Float.NEGATIVE_INFINITY": ('float("-inf")', ATOM, "double"),
    "Double.NaN": ('float("nan")', ATOM, "double"),
    "BigInteger.ZERO": ("0", ATOM, "BigInteger"),
    "BigInteger.ONE": ("1", ATOM, "BigInteger"),
    "BigInteger.TWO": ("2", ATOM, "BigInteger"),
    "BigInteger.TEN": ("10", ATOM, "BigInteger"),
    "Math.PI": ("math.pi", ATOM, "double"),
    "Math.E": ("math.e", ATOM, "double"),
}
_MATH_SAME = {
    "sqrt", "floor", "ceil", "log", "log10", "exp", "sin", "cos", "tan", "asin", "acos", "atan",
    "atan2", "hypot", "pow", "sinh", "cosh", "tanh",
}
_CHAR_TESTS = {
    "isDigit": "isdigit", "isLetter": "isalpha", "isAlphabetic": "isalpha",
    "isLetterOrDigit": "isalnum", "isUpperCase": "isupper", "isLowerCase": "islower",
    "isWhitespace": "isspace", "isSpaceChar": "isspace",
}
_STATIC_CLASSES = {
    "Math", "Integer", "Long", "Short", "Byte", "Double", "Float", "Boolean", "Character",
    "String", "Arrays", "Collections", "Objects", "List", "Set", "Map", "System", "Thread", "BigInteger",
    "StrictMath",
}
SB_MUTATORS = {"append", "reverse", "insert", "deleteCharAt", "delete", "setLength", "setCharAt"}
_NUMERIC = ("int", "char", "float")


def _unwrap_str(code: str) -> str:
    """``str(x)`` -> ``x`` (dentro de un f-string el str() sobra)."""
    for prefix in ("str(", "("):
        if not (code.startswith(prefix) and code.endswith(")")) or ":=" in code:
            continue
        depth = 0
        for ch in code[len(prefix):-1]:
            depth += ch == "("
            depth -= ch == ")"
            if depth < 0:
                break
        if depth == 0:
            return _unwrap_str(code[len(prefix):-1]) if prefix == "(" else code[len(prefix):-1]
    return code


def _strip_parens(code: str) -> str:
    """Quita unos paréntesis exteriores redundantes: ``(a + b)`` -> ``a + b``."""
    if not (code.startswith("(") and code.endswith(")")) or ":=" in code:
        return code
    depth = 0
    for ch in code[1:-1]:
        depth += ch == "("
        depth -= ch == ")"
        if depth < 0:
            return code
    return code[1:-1] if depth == 0 else code


def kids(node):
    """Hijos con nombre de un nodo, sin comentarios."""
    return [c for c in node.named_children if c.type not in ("line_comment", "block_comment")]


class ExprMixin:
    decl_ctx = None

    # ------------------------------------------------------------ despacho
    def expr(self, node) -> E:
        fn = getattr(self, "x_" + node.type, None)
        if fn is None:
            raise Unsupported(f"expresión no soportada ({node.type})")
        return fn(node)

    def expr_decl(self, node, jtype) -> E:
        """Traduce un inicializador sabiendo el tipo declarado de la variable."""
        saved = self.decl_ctx
        self.decl_ctx = (node.id, jtype)
        try:
            return self.expr(node)
        finally:
            self.decl_ctx = saved

    def cond(self, node) -> E:
        """Condición de if/while/switch: sin los paréntesis obligatorios de Java."""
        if node.type == "parenthesized_expression":
            return self.expr(kids(node)[0])
        return self.expr(node)

    def args(self, nodes) -> list[E]:
        return [self.expr(n) for n in nodes]

    @staticmethod
    def arg_nodes(node):
        al = node.child_by_field_name("arguments")
        return kids(al) if al is not None else []

    def is_free_name(self, name: str) -> bool:
        """True si ``name`` no es una variable local ni un campo (o sea, una clase)."""
        return not self.lookup_local(name)[0] and not self.find_field(self.cls, name)

    def note_write(self, node) -> None:
        """Registra escrituras a variables de módulo (para emitir ``global``)."""
        if node.type == "identifier" and self.global_writes is not None:
            found, _, idx = self.lookup_local(txt(node))
            if found and idx == 0:
                self.global_writes.add(local_name(txt(node)))

    # ------------------------------------------------------------- literales
    def x_decimal_integer_literal(self, node):
        t = txt(node)
        jt = "long" if t[-1] in "lL" else "int"
        t = t.rstrip("lL")
        if len(t) > 1 and t[0] == "0" and t.replace("_", "").isdigit():
            t = "0o" + t[1:]
        return E(t, ATOM, jt)

    def x_hex_integer_literal(self, node):
        return E(txt(node).rstrip("lL"), ATOM, "int")

    x_binary_integer_literal = x_hex_integer_literal

    def x_octal_integer_literal(self, node):
        t = txt(node).rstrip("lL").replace("_", "")
        return E("0o" + t[1:] if len(t) > 1 else t, ATOM, "int")

    def x_decimal_floating_point_literal(self, node):
        t = txt(node).rstrip("fFdD")
        if not re.search(r"[.eE]", t):
            t += ".0"
        return E(t, ATOM, "double")

    def x_hex_floating_point_literal(self, node):
        return E(f'float.fromhex("{txt(node).rstrip("fFdD")}")', ATOM, "double")

    def x_true(self, node):
        return E("True", ATOM, "boolean")

    def x_false(self, node):
        return E("False", ATOM, "boolean")

    def x_null_literal(self, node):
        return E("None", ATOM, None)

    def x_this(self, node):
        return E("self", ATOM, self.cls.name)

    def x_character_literal(self, node):
        inner = txt(node)[1:-1]
        if inner == '"':
            inner = '\\"'
        elif inner == "\\'":
            inner = "'"
        return E(f'"{inner}"', ATOM, "char", parts=[("lit", inner)])

    def x_string_literal(self, node):
        t = txt(node)
        if t.startswith('"""'):
            body = textwrap.dedent(t[3:-3].lstrip(" \t").removeprefix("\r").removeprefix("\n"))
            return E('"""' + body.replace('"""', '\\"\\"\\"') + '"""', ATOM, "String")
        return E(t, ATOM, "String", parts=[("lit", t[1:-1])])

    def x_class_literal(self, node):
        return E(self.py_class_name(txt(kids(node)[0])), ATOM, "Class")

    # --------------------------------------------------------- identificadores
    def x_identifier(self, node):
        return self.resolve(txt(node))

    def resolve(self, name: str) -> E:
        found, jtype, _ = self.lookup_local(name)
        if found:
            return E(local_name(name), ATOM, jtype)
        f = self.find_field(self.cls, name)
        if f:
            owner, jtype, static = f
            pf = owner.py_field(name)
            if not static:
                if self.cls.needs_outer and not self.cls.in_chain(owner, self.classes):
                    return E(f"self._outer.{pf}", ATOM, jtype)
                return E(f"self.{pf}", ATOM, jtype)
            if self.in_class_body and owner is self.cls:
                return E(pf, ATOM, jtype)
            return E(f"{owner.name}.{pf}", ATOM, jtype)
        return E(attr_name(name), ATOM, None)

    def x_field_access(self, node):
        obj = node.child_by_field_name("object")
        name = txt(node.child_by_field_name("field"))
        full = txt(node).replace(" ", "")
        if full in _CONSTANTS and self.is_free_name(full.split(".")[0]):
            code, prec, jt = _CONSTANTS[full]
            for mod in ("sys", "math"):
                if code.startswith(mod + "."):
                    self.imports.add(f"import {mod}")
            return E(code, prec, jt)
        if obj.type in ("this", "super"):
            f = self.find_field(self.cls, name)
            return E(f"self.{f[0].py_field(name) if f else attr_name(name)}", ATOM, f[1] if f else None)
        if obj.type == "identifier" and txt(obj) in self.classes and self.is_free_name(txt(obj)):
            ci = self.classes[txt(obj)]
            f = self.find_field(ci, name)
            return E(f"{ci.name}.{f[0].py_field(name) if f else attr_name(name)}", ATOM, f[1] if f else None)
        recv = self.expr(obj)
        ci = self.class_of(recv.type)
        if name == "length":
            known = ci is not None and self.find_field(ci, "length")
            maybe = recv.type is None and any("length" in c.fields for c in self.classes.values())
            if not known and not maybe:
                return E(f"len({recv.code})", ATOM, "int")
        f = self.find_field(ci, name) if ci else None
        if f:
            pf = f[0].py_field(name)
            f = (f[0], self.subst(f[1], f[0], recv.type), f[2])
        else:
            pf = attr_name(name)
            if recv.type is None:           # tipo desconocido: ¿algún campo renombrado se llama así?
                owners = [c for c in self.classes.values() if name in c.fields and name in c.methods]
                if owners:
                    pf = owners[0].py_field(name)
        return E(f"{P(recv, ATOM)}.{pf}", ATOM, f[1] if f else None)

    def x_array_access(self, node):
        arr = self.expr(node.child_by_field_name("array"))
        idx = self.as_int(self.expr(node.child_by_field_name("index")))
        return E(f"{P(arr, ATOM)}[{idx.code}]", ATOM, T.elem(arr.type, self.user))

    def x_parenthesized_expression(self, node):
        inner = self.expr(kids(node)[0])
        if inner.prec >= ATOM:
            return inner
        return E(f"({inner.code})", ATOM, inner.type, inner.parts, inner.neg)

    # ------------------------------------------------------------ operadores
    def as_int(self, e: E) -> E:
        """Un ``char`` usado como número necesita ``ord()`` en Python."""
        if self.k(e.type) == "char":
            return E(f"ord({e.code})", ATOM, "int")
        return e

    def num_type(self, a: E, b: E) -> str | None:
        ka, kb = self.k(a.type), self.k(b.type)
        if "float" in (ka, kb) and ka in _NUMERIC and kb in _NUMERIC:
            return "double"
        if ka in ("int", "char") and kb in ("int", "char"):
            return "int"
        return None

    def x_binary_expression(self, node):
        op = txt(node.child_by_field_name("operator"))
        l = self.expr(node.child_by_field_name("left"))
        r = self.expr(node.child_by_field_name("right"))
        kl, kr = self.k(l.type), self.k(r.type)

        if op in ("&&", "||"):
            prec = _BIN_PREC[op]
            word = "and" if op == "&&" else "or"
            return E(f"{P(l, prec)} {word} {P(r, prec + 1)}", prec, "boolean")

        if op in ("==", "!=", "<", ">", "<=", ">="):
            simpler = self.compare_to_zero(node, op)
            if simpler is not None:
                return simpler
            if op in ("==", "!="):
                none = "None" in (l.code, r.code)
                ident = "user" in (kl, kr) or (kl is None and kr is None and "self" in (l.code, r.code))
                if none or ident:
                    op = "is" if op == "==" else "is not"
            if "char" in (kl, kr) and "int" in (kl, kr):
                l, r = self.as_int(l), self.as_int(r)
            return self.cmp_e(P(l, CMP + 1), op, P(r, CMP + 1))

        if op == "+" and (kl in ("str", "sb") or kr in ("str", "sb")):
            return self.concat(self.str_parts(l) + self.str_parts(r))

        prec = _BIN_PREC[op]
        jt = self.num_type(l, r)
        if op in ("+", "-", "*", "/", "%") or op in ("<<", ">>", ">>>"):
            l, r = self.as_int(l), self.as_int(r)
        elif "char" in (kl, kr):
            l, r = self.as_int(l), self.as_int(r)
        if op == "/" and jt == "int":
            op = "//"
        if op == ">>>":
            op = ">>"
            self.warn("'>>>' se tradujo como '>>' (Python no tiene enteros de 32 bits)", node)
        if op in ("&", "|", "^") and kl == "bool":
            jt = "boolean"
        elif op in ("&", "|", "^", "<<", ">>") and jt is None and "int" in (kl, kr):
            jt = "int"
        return E(f"{P(l, prec)} {op} {P(r, prec + 1)}", prec, jt)

    _NEGATED = {"==": "!=", "!=": "==", "<": ">=", ">": "<=", "<=": ">", ">=": "<",
                "is": "is not", "is not": "is", "in": "not in", "not in": "in"}

    def cmp_e(self, left: str, op: str, right: str) -> E:
        """Comparación ``left op right`` que recuerda su forma negada."""
        return E(f"{left} {op} {right}", CMP, "boolean", neg=f"{left} {self._NEGATED[op]} {right}")

    def negate(self, e: E) -> E:
        """``not e`` escrito de la forma más natural posible."""
        if e.neg is not None:
            return E(e.neg, CMP, "boolean", neg=e.code if e.prec == CMP else None)
        return E(f"not {P(e, NOT)}", NOT, "boolean")

    def compare_to_zero(self, node, op):
        """``a.compareTo(b) < 0`` -> ``a < b`` (solo cuando es seguro)."""
        left, right = node.child_by_field_name("left"), node.child_by_field_name("right")
        if left.type != "method_invocation" or txt(right) != "0":
            return None
        obj = left.child_by_field_name("object")
        argn = self.arg_nodes(left)
        if txt(left.child_by_field_name("name")) != "compareTo" or obj is None or len(argn) != 1:
            return None
        a, b = self.expr(obj), self.expr(argn[0])
        ka = self.k(a.type)
        if ka in ("str", "int", "float", "char") or (ka is None and op in ("<", ">") and obj.type != "this"):
            return self.cmp_e(P(a, CMP + 1), op, P(b, CMP + 1))
        return None

    # -- concatenación de cadenas ------------------------------------------
    def str_parts(self, e: E) -> list:
        if e.parts is not None and self.k(e.type) in ("str", "char"):
            return list(e.parts)
        return [("expr", e)]

    def str_operand(self, e: E) -> str:
        if self.k(e.type) in ("str", "char", "sb"):
            return P(e, ADD + 1)
        return f"str({e.code})"

    def concat(self, parts: list) -> E:
        lits = [p for p in parts if p[0] == "lit"]
        exprs = [p[1] for p in parts if p[0] == "expr"]
        if lits and not exprs:
            return E('"' + "".join(p[1] for p in lits) + '"', ATOM, "String", parts)
        if all(p[1] == "" for p in lits) and len(exprs) == 1:
            e = exprs[0]
            if self.k(e.type) in ("str", "char", "sb"):
                return E(e.code, e.prec, "String", parts)
            return E(f"str({e.code})", ATOM, "String", parts)
        ok = lambda c: not re.search(r'["\\\n#{}]|lambda', c)  # noqa: E731
        if lits and self.opts.fstrings and all(ok(e.code) for e in exprs):
            out = ""
            for kind_, val in parts:
                if kind_ == "lit":
                    out += val.replace("{", "{{").replace("}", "}}")
                else:
                    out += "{" + _unwrap_str(val.code) + "}"
            return E(f'f"{out}"', ATOM, "String", parts)
        pieces, buf = [], None
        for kind_, val in parts:
            if kind_ == "lit":
                buf = (buf or "") + val
            else:
                if buf:
                    pieces.append(f'"{buf}"')
                buf = None
                pieces.append(self.str_operand(val))
        if buf:
            pieces.append(f'"{buf}"')
        return E(" + ".join(pieces), ADD if len(pieces) > 1 else ATOM, "String", parts)

    def x_unary_expression(self, node):
        op = txt(node.child_by_field_name("operator"))
        e = self.expr(node.child_by_field_name("operand"))
        if op == "!":
            return self.negate(e)
        e = self.as_int(e)
        return E(f"{op}{P(e, UNARY)}", UNARY, e.type)

    def x_ternary_expression(self, node):
        c = self.expr(node.child_by_field_name("condition"))
        a = self.expr(node.child_by_field_name("consequence"))
        b = self.expr(node.child_by_field_name("alternative"))
        return E(f"{P(a, OR)} if {P(c, OR)} else {P(b, TERN)}", TERN, a.type or b.type)

    def x_update_expression(self, node):
        prefix = node.children[0].type in ("++", "--")
        sign = "+" if any(c.type == "++" for c in node.children) else "-"
        target = kids(node)[0]
        self.note_write(target)
        tgt = self.expr(target)
        stmt = f"{tgt.code} {sign}= 1"
        if prefix and self.pre is not None:
            self.pre.append(stmt)
            return tgt
        if not prefix and self.post is not None:
            self.post.append(stmt)
            return tgt
        if target.type == "identifier" and self.lookup_local(txt(target))[0]:
            c = tgt.code
            if prefix:
                return E(f"({c} := {c} {sign} 1)", ATOM, tgt.type)
            inv = "-" if sign == "+" else "+"
            return E(f"({c} := {c} {sign} 1) {inv} 1", ADD, tgt.type)
        raise Unsupported("'++'/'--' dentro de una expresión sobre un campo o arreglo")

    def assign_code(self, node) -> str:
        """Código Python de una asignación Java usada como sentencia."""
        left = node.child_by_field_name("left")
        op = txt(node.child_by_field_name("operator"))
        right = node.child_by_field_name("right")
        self.note_write(left)
        if op == "=":
            targets = [left]
            while right.type == "assignment_expression" and txt(right.child_by_field_name("operator")) == "=":
                targets.append(right.child_by_field_name("left"))
                self.note_write(targets[-1])
                right = right.child_by_field_name("right")
            ltypes = [self.expr(t) for t in targets]
            val = self.coerce(self.expr_decl(right, ltypes[0].type), ltypes[0].type)
            if val.prec == STMT:
                raise Unsupported("llamada sin valor usada como valor")
            return " = ".join([t.code for t in ltypes] + [val.code])
        l, r = self.expr(left), self.expr(right)
        pyop = op[:-1]
        kl = self.k(l.type)
        if pyop == "+" and kl in ("str", "sb"):
            return f"{l.code} += {self.concat(self.str_parts(r)).code}"
        if pyop == "+" and kl == "char":
            return f"{l.code} = chr(ord({l.code}) + {P(self.as_int(r), ADD + 1)})"
        if pyop in ("+", "-", "*", "/", "%"):
            r = self.as_int(r)
        if pyop == "/" and kl == "int":
            pyop = "//"
        if pyop == ">>>":
            pyop = ">>"
        if kl == "int" and self.k(r.type) == "float" and pyop in ("+", "-", "*"):
            return f"{l.code} = int({l.code} {pyop} {P(r, MUL + 1)})"
        return f"{l.code} {pyop}= {r.code}"

    def coerce(self, val: E, jtype: str | None) -> E:
        """Ajusta un valor al tipo declarado (conversiones implícitas de Java)."""
        kd, kv = self.k(jtype), self.k(val.type)
        if kd == "int" and kv == "char":
            return self.as_int(val)
        if kd == "char" and kv == "int":
            return E(f"chr({val.code})", ATOM, "char")
        if kd == "float" and re.fullmatch(r"-?\d+", val.code):
            return E(val.code + ".0", val.prec, "double")
        if kd == "float" and kv == "int" and T.base(jtype) in ("double", "float"):
            return E(f"float({val.code})", ATOM, "double")
        return val

    def coerce_args(self, args: list[E], info, infos) -> list[E]:
        """Conversión implícita int -> double al pasar argumentos."""
        same = [i for i in infos if len(i.params) == len(args)]
        if len(same) != 1 or info.varargs or len(info.params) != len(args):
            return args
        return [self.coerce(a, t) for a, t in zip(args, info.params)]

    def find_method_chain(self, ci, name):
        """Como find_method, pero solo en la clase y sus superclases."""
        seen = set()
        while ci is not None and id(ci) not in seen:
            seen.add(id(ci))
            if name in ci.methods:
                return ci, ci.methods[name]
            ci = self.classes.get(ci.superclass) if ci.superclass else None
        return None

    def chain_known(self, ci) -> bool:
        """True si toda la cadena de herencia está definida en el código."""
        seen = set()
        while ci is not None and id(ci) not in seen:
            seen.add(id(ci))
            if ci.superclass and ci.superclass not in self.classes:
                return False
            ci = self.classes.get(ci.superclass) if ci.superclass else None
        return True

    def x_assignment_expression(self, node):
        left = node.child_by_field_name("left")
        op = txt(node.child_by_field_name("operator"))
        is_local = left.type == "identifier" and (
            self.lookup_local(txt(left))[0] or re.fullmatch(r"\w+", self.resolve(txt(left)).code))
        if is_local and op == "=":
            _, jtype, _ = self.lookup_local(txt(left))
            r = self.coerce(self.expr(node.child_by_field_name("right")), jtype)
            return E(f"({local_name(txt(left))} := {r.code})", ATOM, jtype)
        if self.pre is not None:
            self.pre.append(self.assign_code(node))
            return self.expr(left)
        if is_local:
            code = self.assign_code(node)          # "x op= valor"
            m = re.match(r"(\w+) (\S+)= (.*)$", code, re.S)
            if m:
                return E(f"({m[1]} := {m[1]} {m[2]} ({m[3]}))", ATOM, self.lookup_local(txt(left))[1])
        raise Unsupported("asignación dentro de una expresión")

    def x_cast_expression(self, node):
        jt = T.clean(txt(node.child_by_field_name("type")))
        v = self.expr(node.child_by_field_name("value"))
        kt, kv = self.k(jt), self.k(v.type)
        if kt == "int":
            if kv == "char":
                return self.as_int(v)
            if kv == "int":
                return E(v.code, v.prec, jt)
            return E(f"int({_strip_parens(v.code)})", ATOM, jt)
        if kt == "float":
            return E(f"float({_strip_parens(v.code)})", ATOM, jt)
        if kt == "char":
            if kv in ("char", "str"):
                return v
            return E(f"chr({_strip_parens(v.code)})", ATOM, "char")
        return E(v.code, v.prec, jt, v.parts)

    def x_instanceof_expression(self, node):
        left = self.expr(node.child_by_field_name("left"))
        right = node.child_by_field_name("right")
        cls = self.py_class_name(T.clean(txt(right)))
        name = node.child_by_field_name("name")
        code = left.code
        if name is not None:
            code = f"({self.declare(txt(name), T.clean(txt(right)))} := {left.code})"
        return E(f"isinstance({code}, {cls})", ATOM, "boolean")

    # ---------------------------------------------------------------- lambdas
    def x_lambda_expression(self, node):
        params = node.child_by_field_name("parameters")
        body = node.child_by_field_name("body")
        if params.type == "identifier":
            names = [(txt(params), None)]
        elif params.type == "inferred_parameters":
            names = [(txt(c), None) for c in kids(params)]
        else:
            names = []
            for c in kids(params):
                tn = c.child_by_field_name("type")
                names.append((txt(c.child_by_field_name("name")), T.clean(txt(tn)) if tn else None))
        self.scopes.append({})
        try:
            ps = ", ".join(self.declare(n, t) for n, t in names)
            head = f"lambda {ps}:" if ps else "lambda:"
            single = body
            if body.type == "block":
                stmts = kids(body)
                single = None
                if len(stmts) == 1 and stmts[0].type == "return_statement" and kids(stmts[0]):
                    single = kids(stmts[0])[0]
                elif len(stmts) == 1 and stmts[0].type == "expression_statement":
                    single = kids(stmts[0])[0]
            if single is not None:
                saved = (self.pre, self.post)
                self.pre = self.post = None
                try:
                    b = self.expr(single)
                except Unsupported:
                    b = None
                finally:
                    self.pre, self.post = saved
                if b is not None and b.prec != STMT:
                    return E(f"{head} {b.code}", LAMBDA, None)
                if body.type != "block":
                    raise Unsupported("lambda cuyo cuerpo no es una expresión en Python")
            if self.pre is None:
                raise Unsupported("lambda con bloque de código en este contexto")
            self.lambda_count += 1
            fname = f"_lambda_{self.lambda_count}"
            saved_loops, self.loops = self.loops, []
            with self.capture() as box:
                self.emit(f"def {fname}({ps}):")
                self.func_depth += 1
                if body.type == "block":
                    self.body(body)
                else:
                    self.level += 1
                    self.stmt_expression(body, body)
                    self.level -= 1
                self.func_depth -= 1
            self.loops = saved_loops
            self.pre.extend(box)
            return E(fname, ATOM, None)
        finally:
            self.scopes.pop()

    def x_method_reference(self, node):
        t = txt(node).replace(" ", "")
        table = {
            "String::valueOf": "str", "Integer::parseInt": "int", "Integer::valueOf": "int",
            "Double::parseDouble": "float", "System.out::println": "print",
            "Integer::sum": "lambda a, b: a + b", "Math::max": "max", "Math::min": "min",
            "Integer::compare": "lambda a, b: (a > b) - (a < b)",
            "String::length": "len", "String::toUpperCase": "str.upper",
            "String::toLowerCase": "str.lower", "ArrayList::new": "list", "HashSet::new": "set",
            "HashMap::new": "dict", "Integer::intValue": "int",
        }
        if t in table:
            return E(table[t], LAMBDA if t.startswith("Integer::") and "lambda" in table[t] else ATOM)
        left, right = t.split("::")
        if right == "new":
            return E(self.py_class_name(left))
        if left == "this":
            return E(f"self.{attr_name(right)}")
        return E(f"{self.expr(kids(node)[0]).code}.{attr_name(right)}")

    def x_switch_expression(self, node):
        subj = self.cond(node.child_by_field_name("condition"))
        s = P(subj, CMP + 1)
        arms, default = [], None
        for rule in kids(node.child_by_field_name("body")):
            parts = kids(rule)
            if rule.type != "switch_rule" or parts[1].type != "expression_statement":
                raise Unsupported("switch usado como expresión con bloques o 'yield'")
            v = self.expr(kids(parts[1])[0])
            labels = kids(parts[0])
            if not labels:
                default = v
            else:
                arms.append((self.case_values(labels, subj), v))
        if default is None:
            raise Unsupported("switch usado como expresión sin 'default'")
        code = ""
        for vals, v in arms:
            test = f"{s} == {vals[0]}" if len(vals) == 1 else f"{s} in ({', '.join(vals)})"
            code += f"{P(v, OR)} if {test} else "
        return E(code + P(default, TERN), TERN, default.type)

    def case_values(self, labels, subj: E) -> list[str]:
        out = []
        enum = self.class_of(subj.type)
        for lab in labels:
            if lab.type == "identifier" and enum is not None and txt(lab) in enum.constants:
                out.append(f"{enum.name}.{txt(lab)}")
            else:
                out.append(P(self.expr(lab), CMP + 1))
        return out

    # ------------------------------------------------------- creación de objetos
    def x_object_creation_expression(self, node):
        if any(c.type == "class_body" for c in node.children):
            raise Unsupported("clase anónima (define una clase con nombre o usa una función)")
        jt = T.clean(txt(node.child_by_field_name("type")))
        b = T.base(jt)
        argn = self.arg_nodes(node)
        decl = self.decl_ctx[1] if self.decl_ctx and self.decl_ctx[0] == node.id else None
        if b in self.classes:
            a = self.args(argn)
            ctors = self.classes[b].methods.get("<init>")
            if ctors:
                a = self.coerce_args(a, self.pick(ctors, len(a)), ctors)
            codes = [x.code for x in a]
            target = self.classes[b]
            if target.needs_outer:              # clase interna: recibe la instancia externa
                if self.cls is target or (self.cls.needs_outer and self.cls.outer is target.outer):
                    codes.insert(0, "self._outer")
                elif not self.static_ctx and target.outer is not None and self.cls.in_chain(target.outer, self.classes):
                    codes.insert(0, "self")
                else:
                    codes.insert(0, "None")
                    self.warn(f"'{b}' es una clase interna que usa su clase externa: pásale esa instancia como primer argumento", node)
            return E(f"{b}({', '.join(codes)})", ATOM, jt)
        k = self.k(jt)
        a = self.args(argn)
        a0 = a[0] if a else None
        from_coll = a0 is not None and self.k(a0.type) not in ("int",)
        if k == "deque" and self.k(decl) in ("list",):
            k = "list"
        if k == "list":
            return E(f"list({a0.code})" if from_coll else "[]", ATOM, jt)
        if k == "stack":
            return E("[]", ATOM, jt)
        if k == "deque":
            self.imports.add("from collections import deque")
            return E(f"deque({a0.code})" if from_coll else "deque()", ATOM, jt)
        if k == "map":
            if b in ("TreeMap",):
                self.warn("TreeMap se tradujo como dict: no mantiene las claves ordenadas", node)
            return E(f"dict({a0.code})" if from_coll else "{}", ATOM, jt)
        if k == "set":
            if b in ("TreeSet",):
                self.warn("TreeSet se tradujo como set: no mantiene el orden", node)
            return E(f"set({a0.code})" if from_coll else "set()", ATOM, jt)
        if k == "pq":
            if argn and argn[-1].type in ("lambda_expression", "method_invocation", "method_reference"):
                msg = "PriorityQueue con comparador: heapq siempre es un min-heap (guarda tuplas (prioridad, dato) o valores negados)"
                self.warn(msg, node)
                if self.pre is not None:
                    self.pre.append(f"# TODO(java2py): {msg}")
                return E("[]", ATOM, jt)
            if from_coll:
                return E(f"sorted({a0.code})", ATOM, jt)
            return E("[]", ATOM, jt)
        if k == "sb":
            if a0 is None or self.k(a0.type) == "int":
                return E('""', ATOM, jt)
            return E(a0.code if self.k(a0.type) in ("str", "sb") else f"str({a0.code})", ATOM, jt)
        if k == "str":
            if a0 is None:
                return E('""', ATOM, "String")
            if self.k(a0.type) == "array":
                return E(f'"".join({a0.code})', ATOM, "String")
            return E(f"str({a0.code})", ATOM, "String")
        if k == "scanner":
            self.imports.add("import sys")
            return E("sys.stdin", ATOM, "Scanner")
        if k == "random":
            self.imports.add("import random")
            return E(f"random.Random({', '.join(x.code for x in a)})", ATOM, "Random")
        if k == "object":
            return E("object()", ATOM, jt)
        if k in ("int", "float", "bool", "char") and a0 is not None:
            fn = {"int": "int", "float": "float", "bool": "bool", "char": "str"}[k]
            return E(a0.code if self.k(a0.type) == k else f"{fn}({a0.code})", ATOM, jt)
        name = self.py_class_name(jt)
        return E(f"{name}({', '.join(x.code for x in a)})", ATOM, jt)

    def x_array_creation_expression(self, node):
        value = node.child_by_field_name("value")
        base_t = T.clean(txt(node.child_by_field_name("type")))
        dims = [kids(d)[0] for d in node.children_by_field_name("dimensions") if d.type == "dimensions_expr"]
        empty = sum(txt(d).count("[") for d in node.children_by_field_name("dimensions") if d.type == "dimensions")
        total = len(dims) + empty
        if value is not None:
            return self.array_init(value, base_t + "[]" * total)
        code = "None" if empty else T.default_value(base_t)
        sizes = [self.expr(d) for d in dims]
        code = f"[{code}] * {P(sizes[-1], MUL + 1)}"
        for size in reversed(sizes[:-1]):
            code = f"[{code} for _ in range({size.code})]"
        return E(code, MUL if len(sizes) == 1 else ATOM, base_t + "[]" * total)

    def x_array_initializer(self, node):
        jt = self.decl_ctx[1] if self.decl_ctx and self.decl_ctx[0] == node.id else None
        return self.array_init(node, jt)

    def array_init(self, node, jt) -> E:
        et = T.elem(jt) if T.is_array(jt) else None
        items = []
        for c in kids(node):
            if c.type == "array_initializer":
                items.append(self.array_init(c, et).code)
            else:
                items.append(self.coerce(self.expr(c), et).code)
        return E("[" + ", ".join(items) + "]", ATOM, jt)

    # ----------------------------------------------------- llamadas a métodos
    def x_method_invocation(self, node):
        name = txt(node.child_by_field_name("name"))
        obj = node.child_by_field_name("object")
        argn = self.arg_nodes(node)
        if obj is None:
            return self.call_unqualified(name, argn)
        ot = txt(obj).replace(" ", "")
        qualified = obj.type == "field_access" and re.match(r"javax?\.", ot) is not None
        if qualified:
            ot = ot.rsplit(".", 1)[-1]
        if obj.type == "super":
            a = ", ".join(x.code for x in self.args(argn))
            found = self.find_method(self.cls, name)
            special = {"toString": "__str__", "equals": "__eq__", "hashCode": "__hash__"}
            return E(f"super().{special.get(name, attr_name(name))}({a})", ATOM,
                     self.pick(found[1], len(argn)).ret if found else None)
        if obj.type == "this":
            return self.call_unqualified(name, argn, force_self=True)
        if ot in ("System.out", "System.err") and self.is_free_name("System"):
            return self.call_print(name, argn, ot.endswith("err"))
        if ot == "StdOut" and self.is_free_name(ot) and ot not in self.classes and name in ("println", "print", "printf"):
            return self.call_print(name, argn, False)
        if qualified or (obj.type == "identifier" and self.is_free_name(ot)):
            if ot in self.classes:
                return self.call_user_static(self.classes[ot], name, argn)
            if ot in _STATIC_CLASSES:
                r = self.call_static(ot, name, argn, node)
                if r is not None:
                    return r
        return self.call_instance(self.expr(obj), name, argn, node, obj)

    @staticmethod
    def pick(infos, n):
        for info in infos:
            if len(info.params) == n:
                return info
        return infos[0]

    def call_unqualified(self, name, argn, force_self=False) -> E:
        in_instance = not self.cls.is_module and not self.static_ctx
        if in_instance and not self.find_method(self.cls, name):
            me = E("self", ATOM, self.cls.name)
            if name in ("toString", "hashCode", "getClass") and not argn:
                return self.call_instance(me, name, argn, None, None)
        al = self.args(argn)
        found = self.find_method(self.cls, name)
        n = attr_name(name)
        if found:
            al = self.coerce_args(al, self.pick(found[1], len(argn)), found[1])
        a = ", ".join(x.code for x in al)
        if found:
            owner, infos = found
            info = self.pick(infos, len(argn))
            if owner.is_module:
                return E(f"{n}({a})", ATOM, info.ret)
            if info.static:
                return E(f"{owner.name}.{n}({a})", ATOM, info.ret)
            if self.cls.needs_outer and not self.cls.in_chain(owner, self.classes):
                return E(f"self._outer.{n}({a})", ATOM, info.ret)
            return E(f"self.{n}({a})", ATOM, info.ret)
        if force_self or (in_instance and self.cls.superclass):
            return E(f"self.{n}({a})", ATOM, None)
        return E(f"{n}({a})", ATOM, None)

    def call_user_static(self, ci, name, argn) -> E:
        a = self.args(argn)
        if ci.kind == "enum" and name == "values" and not a:
            return E(f"list({ci.name})", ATOM, ci.name + "[]")
        if ci.kind == "enum" and name == "valueOf" and len(a) == 1:
            return E(f"{ci.name}[{a[0].code}]", ATOM, ci.name)
        found = self.find_method(ci, name)
        ret = self.pick(found[1], len(a)).ret if found else None
        if found:
            a = self.coerce_args(a, self.pick(found[1], len(a)), found[1])
        return E(f"{ci.name}.{attr_name(name)}({', '.join(x.code for x in a)})", ATOM, ret)

    # -- System.out.println y familia ----------------------------------------
    def call_print(self, name, argn, err) -> E:
        a = self.args(argn)
        extra = ""
        if err:
            self.imports.add("import sys")
            extra = ", file=sys.stderr"
        if name == "println":
            body = a[0].code if a else ""
            if not a:
                extra = extra[2:]
            return E(f"print({body}{extra})", ATOM, None)
        if name == "print":
            return E(f'print({a[0].code}, end=""{extra})', ATOM, None)
        if name in ("printf", "format"):
            fmt, end = self.format_code(a, strip_newline=True)
            return E(f"print({fmt}{end}{extra})", ATOM, None)
        raise Unsupported(f"System.out.{name}")

    def format_code(self, a, strip_newline=False):
        """``String.format``/``printf`` -> operador ``%`` de Python."""
        fmt, rest = a[0], a[1:]
        end = ', end=""' if strip_newline else ""
        code = fmt.code
        if fmt.parts is not None and len(fmt.parts) == 1 and fmt.parts[0][0] == "lit":
            inner = fmt.parts[0][1].replace("%n", "\\n").replace("%b", "%s").replace("%,d", "%d")
            if strip_newline and inner.endswith("\\n") and not inner.endswith("\\\\n"):
                inner, end = inner[:-2], ""
            code = f'"{inner}"'
        else:
            code = P(fmt, MUL)
        if len(rest) == 1:
            tup = f"({rest[0].code},)"
        else:
            tup = "(" + ", ".join(x.code for x in rest) + ")"
        return f"{code} % {tup}", end

    # -- métodos estáticos de la biblioteca de Java ---------------------------
    def cmp_code(self, x: E, y: E) -> E:
        a, b = P(x, CMP + 1), P(y, CMP + 1)
        return E(f"({a} > {b}) - ({a} < {b})", ADD, "int")

    def sort_kw(self, node) -> str:
        t = txt(node).replace(" ", "")
        if node.type == "null_literal":
            return ""
        if t in ("Collections.reverseOrder()", "Comparator.reverseOrder()"):
            return "reverse=True"
        if t == "Comparator.naturalOrder()":
            return ""
        if node.type == "method_invocation" and t.startswith("Comparator.comparing"):
            return f"key={self.expr(self.arg_nodes(node)[0]).code}"
        self.imports.add("import functools")
        return f"key=functools.cmp_to_key({self.expr(node).code})"

    def plus(self, e: E, k: int = 1) -> str:
        """Código de ``e + k`` simplificado cuando se puede."""
        if re.fullmatch(r"-?\d+", e.code):
            return str(int(e.code) + k)
        if e.prec == ADD:
            m = re.match(r"^(.*) ([+-]) (\d+)$", e.code, re.S)
            if m:
                v = (int(m[3]) if m[2] == "+" else -int(m[3])) + k
                if v == 0:
                    return m[1]
                return f"{m[1]} {'+' if v > 0 else '-'} {abs(v)}"
        return f"{P(e, ADD)} {'+' if k > 0 else '-'} {abs(k)}"

    def call_static(self, cls, name, argn, node):
        a = self.args(argn)
        n = len(a)
        c = [x.code for x in a]
        joined = ", ".join(c)
        if cls in ("Math", "StrictMath"):
            if name in ("max", "min") and n == 2:
                return E(f"{name}({joined})", ATOM, self.num_type(a[0], a[1]))
            if name == "abs":
                return E(f"abs({joined})", ATOM, a[0].type)
            if name in _MATH_SAME:
                self.imports.add("import math")
                jt = "int" if name in ("floor", "ceil") else "double"
                return E(f"math.{name}({joined})", ATOM, jt)
            if name == "random":
                self.imports.add("import random")
                return E("random.random()", ATOM, "double")
            if name == "round":
                self.imports.add("import math")
                return E(f"math.floor({P(a[0], ADD)} + 0.5)", ATOM, "int")
            if name == "floorDiv":
                return E(f"{P(a[0], MUL)} // {P(a[1], MUL + 1)}", MUL, "int")
            if name == "floorMod":
                return E(f"{P(a[0], MUL)} % {P(a[1], MUL + 1)}", MUL, "int")
            if name == "cbrt":
                return E(f"{P(a[0], ATOM)} ** (1 / 3)", UNARY, "double")
            if name in ("toRadians", "toDegrees"):
                self.imports.add("import math")
                return E(f"math.{name[2:].lower()}({joined})", ATOM, "double")
            if name == "signum":
                return E(self.cmp_code(a[0], E("0")).code, ADD, "double")
            return None
        if cls in ("Integer", "Long", "Short", "Byte"):
            if name in ("parseInt", "parseLong", "valueOf", "parseShort"):
                if n == 1 and self.k(a[0].type) == "int":
                    return E(a[0].code, a[0].prec, "Integer" if name == "valueOf" else "int")
                return E(f"int({joined})", ATOM, "int")
            if name == "toString" and n == 1:
                return E(f"str({joined})", ATOM, "String")
            if name == "toBinaryString":
                return E(f"bin({joined})[2:]", ATOM, "String")
            if name == "toHexString":
                return E(f"hex({joined})[2:]", ATOM, "String")
            if name == "compare":
                return self.cmp_code(a[0], a[1])
            if name in ("max", "min"):
                return E(f"{name}({joined})", ATOM, "int")
            if name == "sum":
                return E(f"{P(a[0], ADD)} + {P(a[1], ADD + 1)}", ADD, "int")
            if name == "bitCount":
                return E(f'bin({joined}).count("1")', ATOM, "int")
            if name == "signum":
                return self.cmp_code(a[0], E("0"))
            return None
        if cls in ("Double", "Float"):
            if name in ("parseDouble", "parseFloat", "valueOf"):
                return E(f"float({joined})", ATOM, "double")
            if name == "compare":
                return self.cmp_code(a[0], a[1])
            if name == "toString":
                return E(f"str({joined})", ATOM, "String")
            if name == "isNaN":
                self.imports.add("import math")
                return E(f"math.isnan({joined})", ATOM, "boolean")
            return None
        if cls == "Boolean":
            if name == "parseBoolean":
                return E(f'{P(a[0], ATOM)}.lower() == "true"', CMP, "boolean")
            return None
        if cls == "Character":
            if name in _CHAR_TESTS:
                return E(f"{P(a[0], ATOM)}.{_CHAR_TESTS[name]}()", ATOM, "boolean")
            if name in ("toUpperCase", "toLowerCase"):
                return E(f"{P(a[0], ATOM)}.{name[2:5].lower()}er()", ATOM, "char")
            if name == "getNumericValue":
                return E(f"int({joined})", ATOM, "int")
            if name in ("toString", "valueOf"):
                return E(c[0], a[0].prec, "String" if name == "toString" else "char")
            if name == "compare":
                return self.cmp_code(a[0], a[1])
            return None
        if cls == "String":
            if name in ("valueOf", "copyValueOf") and n == 1:
                k0 = self.k(a[0].type)
                if k0 == "array":
                    return E(f'"".join({c[0]})', ATOM, "String")
                if k0 in ("str", "char"):
                    return E(c[0], a[0].prec, "String")
                return E(f"str({c[0]})", ATOM, "String")
            if name == "format":
                return E(self.format_code(a)[0], MUL, "String")
            if name == "join" and n >= 2:
                seq = c[1] if n == 2 else "[" + ", ".join(c[1:]) + "]"
                return E(f"{P(a[0], ATOM)}.join({seq})", ATOM, "String")
            return None
        if cls == "Arrays":
            if name == "sort":
                if n == 1:
                    return E(f"{P(a[0], ATOM)}.sort()", ATOM, None)
                if n == 2:
                    return E(f"{P(a[0], ATOM)}.sort({self.sort_kw(argn[1])})", ATOM, None)
                if n == 3:
                    sl = f"{P(a[0], ATOM)}[{c[1]}:{c[2]}]"
                    return E(f"{sl} = sorted({sl})", STMT, None)
            if name == "fill" and n == 2:
                return E(f"{P(a[0], ATOM)}[:] = [{c[1]}] * len({c[0]})", STMT, None)
            if name in ("toString", "deepToString"):
                return E(f"str({c[0]})", ATOM, "String")
            if name == "asList":
                if n == 1 and self.k(a[0].type) == "array":
                    return E(f"list({c[0]})", ATOM, "List")
                return E(f"[{joined}]", ATOM, "List")
            if name == "copyOf" and n == 2:
                if txt(argn[1]).replace(" ", "") == txt(argn[0]).replace(" ", "") + ".length":
                    return E(f"{P(a[0], ATOM)}[:]", ATOM, a[0].type)
                d = T.default_value(T.elem(a[0].type))
                return E(f"{P(a[0], ATOM)}[:{c[1]}] + [{d}] * ({c[1]} - len({c[0]}))", ADD, a[0].type)
            if name == "copyOfRange" and n == 3:
                return E(f"{P(a[0], ATOM)}[{c[1]}:{c[2]}]", ATOM, a[0].type)
            if name in ("equals", "deepEquals"):
                return E(f"{P(a[0], CMP + 1)} == {P(a[1], CMP + 1)}", CMP, "boolean")
            return None
        if cls == "Collections":
            if name == "sort":
                kw = self.sort_kw(argn[1]) if n == 2 else ""
                return E(f"{P(a[0], ATOM)}.sort({kw})", ATOM, None)
            if name == "reverse":
                return E(f"{P(a[0], ATOM)}.reverse()", ATOM, None)
            if name == "swap" and n == 3:
                x = P(a[0], ATOM)
                return E(f"{x}[{c[1]}], {x}[{c[2]}] = {x}[{c[2]}], {x}[{c[1]}]", STMT, None)
            if name in ("max", "min") and n == 1:
                return E(f"{name}({joined})", ATOM, T.elem(a[0].type, self.user))
            if name == "shuffle":
                self.imports.add("import random")
                return E(f"random.shuffle({c[0]})", ATOM, None)
            if name in ("emptyList", "emptyMap", "emptySet"):
                return E({"emptyList": "[]", "emptyMap": "{}", "emptySet": "set()"}[name], ATOM, None)
            if name.startswith("unmodifiable") or name.startswith("synchronized"):
                return a[0]
            if name == "singletonList":
                return E(f"[{joined}]", ATOM, "List")
            if name == "frequency":
                return E(f"{P(a[0], ATOM)}.count({c[1]})", ATOM, "int")
            if name == "addAll":
                return E(f"{P(a[0], ATOM)}.extend([{', '.join(c[1:])}])", ATOM, None)
            return None
        if cls == "Objects":
            if name == "equals":
                return E(f"{P(a[0], CMP + 1)} == {P(a[1], CMP + 1)}", CMP, "boolean")
            if name == "hash":
                return E(f"hash(({joined}{',' if n == 1 else ''}))", ATOM, "int")
            if name == "hashCode":
                return E(f"hash({joined})", ATOM, "int")
            if name == "isNull":
                return E(f"{P(a[0], CMP + 1)} is None", CMP, "boolean")
            if name == "nonNull":
                return E(f"{P(a[0], CMP + 1)} is not None", CMP, "boolean")
            if name == "requireNonNull":
                return a[0]
            if name == "toString":
                return E(f"str({c[0]})", ATOM, "String")
            return None
        if cls == "List" and name in ("of", "copyOf"):
            return E(f"[{joined}]" if name == "of" else f"list({joined})", ATOM, "List")
        if cls == "Set" and name in ("of", "copyOf"):
            if name == "copyOf":
                return E(f"set({joined})", ATOM, "Set")
            return E("{" + joined + "}" if n else "set()", ATOM, "Set")
        if cls == "Map" and name == "of":
            pairs = ", ".join(f"{c[i]}: {c[i + 1]}" for i in range(0, n - 1, 2))
            return E("{" + pairs + "}", ATOM, "Map")
        if cls == "Map" and name == "entry" and n == 2:
            return E(f"({joined})", ATOM, "Map.Entry")
        if cls == "System":
            if name == "currentTimeMillis":
                self.imports.add("import time")
                return E("int(time.time() * 1000)", ATOM, "long")
            if name == "nanoTime":
                self.imports.add("import time")
                return E("time.perf_counter_ns()", ATOM, "long")
            if name == "exit":
                self.imports.add("import sys")
                return E(f"sys.exit({joined})", ATOM, None)
            if name == "arraycopy" and n == 5:
                def rng(start: E, length: E) -> str:
                    if start.code == "0":
                        return f":{length.code}"
                    if re.fullmatch(r"\d+", start.code) and re.fullmatch(r"\d+", length.code):
                        return f"{start.code}:{int(start.code) + int(length.code)}"
                    return f"{start.code}:{P(start, ADD)} + {P(length, ADD + 1)}"
                dst = f"{P(a[2], ATOM)}[{rng(a[3], a[4])}]"
                return E(f"{dst} = {P(a[0], ATOM)}[{rng(a[1], a[4])}]", STMT, None)
            if name == "lineSeparator":
                return E('"\\n"', ATOM, "String")
            if name == "identityHashCode":
                return E(f"id({joined})", ATOM, "int")
            return None
        if cls == "BigInteger" and name == "valueOf" and n == 1:
            return E(c[0], a[0].prec, "BigInteger")
        if cls == "Thread" and name == "sleep":
            self.imports.add("import time")
            return E(f"time.sleep({P(a[0], MUL)} / 1000)", ATOM, None)
        return None

    # -- métodos de instancia --------------------------------------------------
    def call_instance(self, recv: E, name, argn, node, obj_node) -> E:
        k = self.k(recv.type)
        n = len(argn)
        R = P(recv, ATOM)
        ci = self.class_of(recv.type)

        # Métodos que todo objeto de Java tiene.
        if name == "toString" and n == 0:
            if k in ("str", "sb"):
                return E(recv.code, recv.prec, "String")
            return E(f"str({recv.code})", ATOM, "String")
        if name == "hashCode" and n == 0:
            return E(f"hash({recv.code})", ATOM, "int")
        if name == "getClass" and n == 0:
            return E(f"type({recv.code})", ATOM, "Class")
        if name in ("getName", "getSimpleName") and recv.type == "Class":
            return E(f"{R}.__name__", ATOM, "String")
        a = self.args(argn)
        c = [x.code for x in a]
        joined = ", ".join(c)
        if name == "equals" and n == 1:
            return self.cmp_e(P(recv, CMP + 1), "==", P(a[0], CMP + 1))

        # Clases definidas en el propio código: llamada normal.
        if ci is not None:
            if ci.kind == "record" and n == 0 and name in ci.fields:
                return E(f"{R}.{attr_name(name)}", ATOM, ci.fields[name][0])
            if ci.kind == "enum" and n == 0 and name == "name":
                return E(f"{R}.name", ATOM, "String")
            if ci.kind == "enum" and n == 0 and name == "ordinal":
                return E(f"list({ci.name}).index({recv.code})", ATOM, "int")
            found = self.find_method_chain(ci, name)
            if found or self.chain_known(ci):
                if found:
                    info = self.pick(found[1], n)
                    joined = ", ".join(x.code for x in self.coerce_args(a, info, found[1]))
                ret = self.subst(info.ret, found[0], recv.type) if found else None
                return E(f"{R}.{attr_name(name)}({joined})", ATOM, ret)

        el = T.elem(recv.type, self.user)
        targs = T.type_args(recv.type)

        if name in ("compareTo", "compareToIgnoreCase") and n == 1:
            if name.endswith("IgnoreCase"):
                return self.cmp_code(E(f"{R}.lower()"), E(f"{P(a[0], ATOM)}.lower()"))
            return self.cmp_code(recv, a[0])
        if name in ("length", "size") and n == 0:
            return E(f"len({recv.code})", ATOM, "int")
        if name in ("isEmpty", "empty") and n == 0:
            return E(f"len({recv.code}) == 0", CMP, "boolean", neg=f"len({recv.code}) > 0")
        if name == "contains" and n == 1:
            return self.cmp_e(P(a[0], CMP + 1), "in", P(recv, CMP + 1))
        if name in ("intValue", "longValue", "shortValue", "booleanValue", "charValue") and n == 0:
            return E(f"int({recv.code})" if k == "float" else recv.code,
                     ATOM if k == "float" else recv.prec, recv.type)
        if name in ("doubleValue", "floatValue") and n == 0:
            return E(f"float({recv.code})", ATOM, "double")

        # ---- BigInteger (los int de Python no tienen límite de tamaño) ----
        if k == "int":
            ops = {"add": ("+", ADD), "subtract": ("-", ADD), "multiply": ("*", MUL), "divide": ("//", MUL),
                   "mod": ("%", MUL), "remainder": ("%", MUL), "xor": ("^", BXOR), "and": ("&", BAND),
                   "or": ("|", BOR), "shiftLeft": ("<<", SHIFT), "shiftRight": (">>", SHIFT)}
            if name in ops and n == 1:
                sym, prec = ops[name]
                return E(f"{P(recv, prec)} {sym} {P(a[0], prec + 1)}", prec, recv.type)
            if name == "pow" and n == 1:
                return E(f"{P(recv, ATOM)} ** {P(a[0], UNARY)}", UNARY, recv.type)
            if name == "modPow" and n == 2:
                return E(f"pow({recv.code}, {joined})", ATOM, recv.type)
            if name == "negate" and n == 0:
                return E(f"-{P(recv, UNARY)}", UNARY, recv.type)
            if name == "abs" and n == 0:
                return E(f"abs({recv.code})", ATOM, recv.type)
            if name == "signum" and n == 0:
                return self.cmp_code(recv, E("0"))
            if name == "gcd" and n == 1:
                self.imports.add("import math")
                return E(f"math.gcd({recv.code}, {c[0]})", ATOM, recv.type)
            if name == "bitLength" and n == 0:
                return E(f"{R}.bit_length()", ATOM, "int")
            if name in ("max", "min") and n == 1:
                return E(f"{name}({recv.code}, {c[0]})", ATOM, recv.type)

        # ---- StringBuilder (se traduce como str inmutable) ----
        if k == "sb":
            if name == "append" and n == 1:
                return self._sb_append(recv, a[0])
            if name == "reverse":
                return E(f"{R}[::-1]", ATOM, recv.type)
            if name == "insert":
                return E(f"{R}[:{c[0]}] + {self.str_operand(a[1])} + {R}[{c[0]}:]", ADD, recv.type)
            if name == "deleteCharAt":
                return E(f"{R}[:{c[0]}] + {R}[{self.plus(a[0])}:]", ADD, recv.type)
            if name == "delete":
                return E(f"{R}[:{c[0]}] + {R}[{c[1]}:]", ADD, recv.type)
            if name == "setLength":
                return E(f"{R}[:{c[0]}]", ATOM, recv.type)
            if name == "setCharAt":
                return E(f"{R}[:{c[0]}] + {P(a[1], ADD + 1)} + {R}[{self.plus(a[0])}:]", ADD, recv.type)
            if name == "replace" and n == 3:
                return E(f"{R}[:{c[0]}] + {P(a[2], ADD + 1)} + {R}[{c[1]}:]", ADD, recv.type)

        # ---- String ----
        if name in ("charAt", "codePointAt") and n == 1:
            ch = E(f"{R}[{c[0]}]", ATOM, "char")
            return ch if name == "charAt" else self.as_int(ch)
        if name == "substring":
            return E(f"{R}[{c[0]}:{c[1] if n == 2 else ''}]", ATOM, "String")
        if name == "subSequence" and n == 2:
            return E(f"{R}[{c[0]}:{c[1]}]", ATOM, "String")
        if name in ("indexOf", "lastIndexOf"):
            if k in ("list", "deque", "stack", "array"):
                self.warn("indexOf sobre una lista se tradujo como .index(): lanza ValueError si no está (Java devuelve -1)", node)
                return E(f"{R}.index({joined})", ATOM, "int")
            return E(f"{R}.{'find' if name == 'indexOf' else 'rfind'}({joined})", ATOM, "int")
        simple = {
            "startsWith": ("startswith", "boolean"), "endsWith": ("endswith", "boolean"),
            "toUpperCase": ("upper", "String"), "toLowerCase": ("lower", "String"),
            "trim": ("strip", "String"), "strip": ("strip", "String"),
        }
        if name in simple and k in ("str", "char", None):
            return E(f"{R}.{simple[name][0]}({joined})", ATOM, simple[name][1])
        if name == "isBlank" and n == 0:
            return E(f'{R}.strip() == ""', CMP, "boolean")
        if name == "split" and n >= 1:
            raw = txt(argn[0])
            if raw in ('"\\\\s+"', '" +"', '"\\\\s"'):
                return E(f"{R}.split()", ATOM, "String[]")
            if raw == '""':
                return E(f"list({recv.code})", ATOM, "String[]")
            return E(f"{R}.split({c[0]})", ATOM, "String[]")
        if name == "toCharArray" and n == 0:
            return E(f"list({recv.code})", ATOM, "char[]")
        if name == "replace" and n == 2:
            return E(f"{R}.replace({joined})", ATOM, "String")
        if name in ("replaceAll", "replaceFirst") and n == 2:
            self.imports.add("import re")
            cnt = ", count=1" if name == "replaceFirst" else ""
            return E(f"re.sub({c[0]}, {c[1]}, {recv.code}{cnt})", ATOM, "String")
        if name == "matches" and n == 1:
            self.imports.add("import re")
            return E(f"re.fullmatch({c[0]}, {recv.code}) is not None", CMP, "boolean")
        if name == "concat" and n == 1:
            return E(f"{P(recv, ADD)} + {P(a[0], ADD + 1)}", ADD, "String")
        if name == "equalsIgnoreCase" and n == 1:
            return E(f"{R}.lower() == {P(a[0], ATOM)}.lower()", CMP, "boolean")
        if name == "repeat" and n == 1:
            return E(f"{P(recv, MUL)} * {P(a[0], MUL + 1)}", MUL, "String")
        if name == "intern" and n == 0:
            return recv

        # ---- Map ----
        if name == "put" and n == 2:
            return E(f"{R}[{c[0]}] = {c[1]}", STMT, None)
        if name == "getOrDefault" and n == 2:
            return E(f"{R}.get({joined})", ATOM, targs[1] if len(targs) == 2 else a[1].type)
        if name == "containsKey" and n == 1:
            return self.cmp_e(P(a[0], CMP + 1), "in", P(recv, CMP + 1))
        if name == "containsValue" and n == 1:
            return E(f"{P(a[0], CMP + 1)} in {R}.values()", CMP, "boolean")
        if name == "keySet" and n == 0:
            return E(f"{R}.keys()", ATOM, f"Set<{targs[0]}>" if len(targs) == 2 and targs[0] else "Set")
        if name == "values" and n == 0:
            return E(f"{R}.values()", ATOM, f"Collection<{targs[1]}>" if len(targs) == 2 and targs[1] else "Collection")
        if name == "entrySet" and n == 0:
            jt = f"Set<Map.Entry<{targs[0]},{targs[1]}>>" if len(targs) == 2 and all(targs) else "Set"
            return E(f"{R}.items()", ATOM, jt)
        if name == "getKey" and n == 0:
            return E(f"{R}[0]", ATOM, targs[0] if targs else None)
        if name == "getValue" and n == 0:
            return E(f"{R}[1]", ATOM, targs[1] if len(targs) == 2 else None)
        if name == "putIfAbsent" and n == 2:
            return E(f"{R}.setdefault({joined})", ATOM, None)
        if name == "computeIfAbsent" and n == 2 and argn[1].type == "lambda_expression":
            body = argn[1].child_by_field_name("body")
            if body.type != "block":
                with self.scope():
                    return E(f"{R}.setdefault({c[0]}, {self.expr(body).code})", ATOM,
                             targs[1] if len(targs) == 2 else None)
        if name == "merge" and n == 3 and txt(argn[2]).replace(" ", "") == "Integer::sum":
            return E(f"{R}[{c[0]}] = {R}.get({c[0]}, 0) + {P(a[1], ADD + 1)}", STMT, None)
        if name in ("firstKey", "first") and n == 0:
            return E(f"min({recv.code})", ATOM, targs[0] if targs else None)
        if name in ("lastKey", "last") and n == 0:
            return E(f"max({recv.code})", ATOM, targs[0] if targs else None)
        if k == "map":
            if name == "get" and n == 1:
                return E(f"{R}.get({c[0]})", ATOM, targs[1] if len(targs) == 2 else None)
            if name == "remove" and n == 1:
                return E(f"{R}.pop({c[0]}, None)", ATOM, targs[1] if len(targs) == 2 else None)
            if name == "putAll" and n == 1:
                return E(f"{R}.update({c[0]})", ATOM, None)

        # ---- Set ----
        if k == "set":
            table = {"add": "add", "remove": "discard", "addAll": "update",
                     "retainAll": "intersection_update", "removeAll": "difference_update"}
            if name in table and n == 1:
                return E(f"{R}.{table[name]}({c[0]})", ATOM, None)

        # ---- PriorityQueue ----
        if k == "pq":
            self.imports.add("import heapq")
            if name in ("add", "offer") and n == 1:
                return E(f"heapq.heappush({recv.code}, {c[0]})", ATOM, None)
            if name in ("poll", "remove") and n == 0:
                return E(f"heapq.heappop({recv.code})", ATOM, el)
            if name in ("peek", "element") and n == 0:
                return E(f"{R}[0]", ATOM, el)

        # ---- Stack ----
        if k == "stack" or (k in (None, "list") and name in ("push", "pop", "peek")):
            if name == "push" and n == 1:
                return E(f"{R}.append({c[0]})", ATOM, None)
            if name == "pop" and n == 0:
                return E(f"{R}.pop()", ATOM, el)
            if name == "peek" and n == 0:
                return E(f"{R}[-1]", ATOM, el)

        # ---- Queue / Deque ----
        if k == "deque" or (k is None and name in ("offer", "poll", "offerLast", "pollFirst")):
            if name in ("offer", "offerLast", "addLast", "add") and n == 1:
                return E(f"{R}.append({c[0]})", ATOM, None)
            if name in ("push", "addFirst", "offerFirst") and n == 1:
                return E(f"{R}.appendleft({c[0]})", ATOM, None)
            if name in ("poll", "pollFirst", "remove", "removeFirst", "pop") and n == 0:
                return E(f"{R}.popleft()", ATOM, el)
            if name in ("peek", "peekFirst", "getFirst", "element") and n == 0:
                return E(f"{R}[0]", ATOM, el)
            if name in ("pollLast", "removeLast") and n == 0:
                return E(f"{R}.pop()", ATOM, el)
            if name in ("peekLast", "getLast") and n == 0:
                return E(f"{R}[-1]", ATOM, el)

        # ---- Scanner / Random / excepciones / iteradores ----
        if k == "scanner":
            if name in ("nextInt", "nextLong", "nextShort"):
                return E("int(input())", ATOM, "int")
            if name in ("nextDouble", "nextFloat"):
                return E("float(input())", ATOM, "double")
            if name in ("nextLine", "next"):
                return E("input()", ATOM, "String")
            if name == "close":
                return E("None", ATOM, None)
            raise Unsupported(f"Scanner.{name}() no tiene equivalente directo; usa input()")
        if k == "random":
            if name == "nextInt":
                return E(f"{R}.randrange({joined})" if n else f"{R}.randrange(-2**31, 2**31)", ATOM, "int")
            if name == "nextDouble":
                return E(f"{R}.random()", ATOM, "double")
            if name == "nextBoolean":
                return E(f"{R}.random() < 0.5", CMP, "boolean")
        if name == "getMessage" and n == 0:
            return E(f"str({recv.code})", ATOM, "String")
        if name == "printStackTrace" and n == 0:
            self.imports.add("import traceback")
            return E("traceback.print_exc()", ATOM, None)
        if name == "iterator" and n == 0:
            return E(f"iter({recv.code})", ATOM, f"Iterator<{el}>" if el else "Iterator")
        if name == "hasNext" and n == 0 and k in ("iterator", None):
            raise Unsupported("Iterator.hasNext(): en Python se recorre con 'for x in coleccion'")
        if name == "next" and n == 0 and k == "iterator":
            return E(f"next({recv.code})", ATOM, el)

        # ---- List (y tipo desconocido: se asume lista) ----
        if name == "add":
            if n == 1:
                return E(f"{R}.append({c[0]})", ATOM, None)
            if n == 2:
                return E(f"{R}.insert({joined})", ATOM, None)
        if name == "addAll" and n == 1:
            return E(f"{R}.extend({c[0]})", ATOM, None)
        if name == "get" and n == 1:
            if k is None and self.k(a[0].type) in ("str", "char"):
                return E(f"{R}.get({c[0]})", ATOM, None)
            return E(f"{R}[{c[0]}]", ATOM, el)
        if name == "set" and n == 2:
            return E(f"{R}[{c[0]}] = {c[1]}", STMT, None)
        if name == "remove":
            if n == 0:
                return E(f"{R}.pop(0)", ATOM, el)
            if self.k(a[0].type) == "int" and T.base(a[0].type) not in ("Integer",):
                return E(f"{R}.pop({c[0]})", ATOM, el)
            return E(f"{R}.remove({c[0]})", ATOM, None)
        if name == "clear" and n == 0:
            return E(f"{R}.clear()", ATOM, None)
        if name == "sort" and n == 1:
            return E(f"{R}.sort({self.sort_kw(argn[0])})", ATOM, None)
        if name == "toArray":
            return E(f"list({recv.code})", ATOM, (el + "[]") if el else None)
        if name == "subList" and n == 2:
            return E(f"{R}[{c[0]}:{c[1]}]", ATOM, recv.type)
        if name in ("getFirst", "getLast") and n == 0:
            return E(f"{R}[{0 if name == 'getFirst' else -1}]", ATOM, el)
        if name == "removeFirst" and n == 0:
            return E(f"{R}.pop(0)", ATOM, el)
        if name == "removeLast" and n == 0:
            return E(f"{R}.pop()", ATOM, el)
        if name == "addFirst" and n == 1:
            return E(f"{R}.insert(0, {c[0]})", ATOM, None)
        if name == "addLast" and n == 1:
            return E(f"{R}.append({c[0]})", ATOM, None)
        if name == "clone" and n == 0:
            return E(f"{R}[:]" if k == "array" else f"list({recv.code})", ATOM, recv.type)
        if name in ("stream", "forEach", "removeIf", "chars", "mapToInt"):
            raise Unsupported(f".{name}(): los streams/funcionales de Java no se traducen; usa un for o una comprensión")

        if k is not None and node is not None:
            self.warn(f"no conozco el equivalente en Python de .{name}(); se dejó igual", node)
        return E(f"{R}.{attr_name(name)}({joined})", ATOM, None)

    def _sb_append(self, recv: E, arg: E) -> E:
        right = self.concat(self.str_parts(arg))
        return E(f"{P(recv, ADD)} + {P(right, ADD)}", ADD, recv.type)
