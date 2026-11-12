"""Pruebas de extremo a extremo.

Cada ``cases/X.java`` es un programa completo cuya salida real en Java está
guardada en ``cases/X.expected``. Aquí se traduce a Python, se ejecuta y se
compara la salida (Java imprime true/false/null; Python True/False/None).
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest

from java2py import translate_detailed

CASES = sorted((Path(__file__).parent / "cases").glob("*.java"))


def _normalize(java_output: str) -> str:
    out = re.sub(r"\btrue\b", "True", java_output)
    out = re.sub(r"\bfalse\b", "False", out)
    return re.sub(r"\bnull\b", "None", out)


@pytest.mark.parametrize("case", CASES, ids=lambda p: p.stem)
def test_program_output_matches_java(case, tmp_path):
    result = translate_detailed(case.read_text(encoding="utf-8"))
    assert "TODO(java2py)" not in result.code, result.warnings
    script = tmp_path / f"{case.stem.lower()}.py"
    script.write_text(result.code, encoding="utf-8")
    run = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stderr
    assert run.stdout == _normalize(case.with_suffix(".expected").read_text(encoding="utf-8"))
