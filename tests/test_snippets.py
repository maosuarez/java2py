"""Pruebas unitarias sobre fragmentos: Java de entrada -> Python esperado."""

import ast

import pytest

from java2py import translate, translate_detailed
from java2py.cli import main

SNIPPETS = [
    ("int doble(int x) { return x * 2; }",
     "def doble(x: int) -> int:\n    return x * 2\n"),
    ('System.out.println("Hola " + nombre + ", tienes " + edad + " años");',
     'print(f"Hola {nombre}, tienes {edad} años")\n'),
    ("int x = 7 / 2; double y = x / 2.0;",
     "x = 7 // 2\ny = x / 2.0\n"),
    ("int[][] m = new int[3][4]; boolean[] v = new boolean[5]; double[] d = {1, 2};",
     "m = [[0] * 4 for _ in range(3)]\nv = [False] * 5\nd = [1.0, 2.0]\n"),
    ('Map<String, Integer> m = new HashMap<>(); m.put("a", 1); if (m.containsKey("b")) m.remove("b");',
     'm = {}\nm["a"] = 1\nif "b" in m:\n    m.pop("b", None)\n'),
    ("Stack<Integer> st = new Stack<>(); st.push(1); int t = st.peek(); st.pop(); boolean e = st.isEmpty();",
     "st = []\nst.append(1)\nt = st[-1]\nst.pop()\ne = len(st) == 0\n"),
    ('Queue<String> q = new LinkedList<>(); q.offer("a"); String h = q.peek(); q.poll();',
     'from collections import deque\n\nq = deque()\nq.append("a")\nh = q[0]\nq.popleft()\n'),
    ("PriorityQueue<Integer> pq = new PriorityQueue<>(); pq.add(3); int m = pq.peek(); pq.poll();",
     "import heapq\n\npq = []\nheapq.heappush(pq, 3)\nm = pq[0]\nheapq.heappop(pq)\n"),
    ('StringBuilder sb = new StringBuilder(); sb.append("a").append(1); sb.reverse(); String r = sb.toString();',
     'sb = ""\nsb += "a" + str(1)\nsb = sb[::-1]\nr = sb\n'),
    ("for (int i = 0; i < n; i++) total += i;",
     "for i in range(n):\n    total += i\n"),
    ("for (int i = n - 1; i >= 0; i--) { System.out.println(arr[i]); }",
     "for i in range(n - 1, -1, -1):\n    print(arr[i])\n"),
    ("for (int i = 1; i < n; i *= 2) { if (i == 4) continue; k++; }",
     "i = 1\nwhile i < n:\n    if i == 4:\n        i *= 2\n        continue\n    k += 1\n    i *= 2\n"),
    ("do { i++; } while (i < 10);",
     "while True:\n    i += 1\n    if i >= 10:\n        break\n"),
    ('switch (op) { case "+": r = a + b; break; case "-": r = a - b; break; default: r = 0; }',
     'match op:\n    case "+":\n        r = a + b\n    case "-":\n        r = a - b\n    case _:\n        r = 0\n'),
    ("try { x = Integer.parseInt(s); } catch (NumberFormatException e) { x = 0; } finally { done = true; }",
     "try:\n    x = int(s)\nexcept ValueError as e:\n    x = 0\nfinally:\n    done = True\n"),
    ("char c = s.charAt(0); int d = c - '0'; boolean b = Character.isDigit(c);",
     'c = s[0]\nd = ord(c) - ord("0")\nb = c.isdigit()\n'),
    ("if (a.equals(b) && !c.isEmpty() || d == null) { return; }",
     "if a == b and len(c) > 0 or d is None:\n    return\n"),
    ("int v = cond ? 1 : 2;", "v = 1 if cond else 2\n"),
    ("int a = 5; int b = a++ + 2; int c = ++a;",
     "a = 5\nb = a + 2\na += 1\na += 1\nc = a\n"),
    ("int in = 3; int max = Math.max(in, 2);", "in_ = 3\nmax_ = max(in_, 2)\n"),
    ("Arrays.sort(arr, (a, b) -> a[1] - b[1]);",
     "import functools\n\narr.sort(key=functools.cmp_to_key(lambda a, b: a[1] - b[1]))\n"),
    ("while (it.hasNext()) { String s = it.next(); total += s.length(); }",
     "for s in it:\n    total += len(s)\n"),
    ("list.size()", "len(list)\n"),
    ("if (x.compareTo(y) < 0) { x = y; }", "if x < y:\n    x = y\n"),
    ('record Par(int a, String b) {} Par p = new Par(1, "x"); int v = p.a();',
     'from dataclasses import dataclass\n\n\n@dataclass(frozen=True)\nclass Par:\n    a: int\n    b: str\n\n\n'
     'p = Par(1, "x")\nv = p.a\n'),
]


@pytest.mark.parametrize("java, python", SNIPPETS, ids=[s[0][:40] for s in SNIPPETS])
def test_snippet(java, python):
    assert translate(java) == python


def test_class_with_fields_constructor_and_tostring():
    java = """
    public class Punto {
        private int x;
        private int y;
        public Punto(int x, int y) { this.x = x; this.y = y; }
        public int getX() { return x; }
        @Override public String toString() { return "(" + x + ", " + y + ")"; }
    }
    """
    assert translate(java) == (
        "class Punto:\n"
        "    def __init__(self, x: int, y: int):\n"
        "        self.x = x\n"
        "        self.y = y\n"
        "\n"
        "    def getX(self) -> int:\n"
        "        return self.x\n"
        "\n"
        "    def __str__(self) -> str:\n"
        '        return f"({self.x}, {self.y})"\n'
    )


def test_field_and_method_with_same_name():
    code = translate("class Pila { private int size; int size() { return size; } void inc() { size++; } }")
    assert "return self._size" in code and "self._size += 1" in code and "def size(self)" in code


def test_overloads_get_a_dispatcher():
    code = translate("class A { int f(int a) { return a; } int f(int a, int b) { return a + b; } }")
    assert "def f(self, *args):" in code and "def _f_v1(self, a: int)" in code and "def _f_v2" in code
    ns = {}
    exec(code, ns)
    assert ns["A"]().f(2) == 2 and ns["A"]().f(2, 3) == 5


def test_options():
    java = 'String saludo(String n) { return "Hola " + n + 1; }'
    assert translate(java, type_hints=False).startswith("def saludo(n):")
    assert '"Hola " + n + str(1)' in translate(java, fstrings=False)
    with_main = "class M { public static void main(String[] args) { } }"
    assert "__main__" in translate(with_main) and "__main__" not in translate(with_main, main_guard=False)


def test_unsupported_code_is_kept_as_todo_comment():
    result = translate_detailed("int x = 1;\nxs.stream().map(a -> a * 2).forEach(System.out::println);\nint y = 2;")
    assert result.code.startswith("x = 1\n# TODO(java2py):")
    assert result.code.endswith("y = 2\n")
    assert len(result.warnings) == 1 and "línea 2" in result.warnings[0]
    ast.parse(result.code)


def test_never_raises_on_garbage():
    for text in ["", "esto no es java", "class {", "int x = ;", "}}}}", "public void f( {"]:
        ast.parse(translate(text))


def test_cli(tmp_path, capsys):
    src = tmp_path / "Hola.java"
    src.write_text('class Hola { public static void main(String[] a) { System.out.println("hola"); } }')
    out = tmp_path / "hola.py"
    assert main([str(src), "-o", str(out)]) == 0
    assert 'print("hola")' in out.read_text()
    assert main(["-c", "int x = 1;"]) == 0
    assert capsys.readouterr().out == "x = 1\n"
