# <!-- @scry.entry
# id: code.patrickscript-test-disasm~c58af944
# kind: code
# status: active
# weight: 0.8
# tags:
#   - "topic:patrickscript"
#   - "topic:testing"
#   - "patrickscript"
#   - "pytest"
#   - "disassembler"
#   - "round-trip"
# summary: >
#   PatrickScript pytest disassembler test suite. Parametrized over all
#   *.ps files in corpus/disasm/. Runs --disassemble on each and checks
#   stdout against *.expected. Also: PatrickScript disasm tests, round-trip,
#   pytest parametrize, disassembler conformance.
# rationale: >
#   Without this, the only disasm test runner is a bash script. pytest gives
#   better output and CI integration.
# applies: >
#   running PatrickScript disassembler tests, adding disasm corpus, CI setup
# seeded_questions:
#   - "How do I run PatrickScript disassembler tests?"
#   - "PatrickScript disasm pytest round-trip"
# @scry.entry.end -->
"""
PatrickScript disassembler round-trip tests — pytest test suite.

Discovers every *.ps file in corpus/disasm/ and runs it through the
reference interpreter's --disassemble flag, comparing the output to the
corresponding *.expected file.

A disassembler test passes iff:
  1. The interpreter exits 0.
  2. Stdout matches the *.expected file exactly.
"""
import subprocess
import sys
from pathlib import Path

import pytest

from .conftest import DISASM_DIR, INTERP


def _disasm_cases():
    """Yield (ps_path, expected_path) for every disasm test."""
    for ps_file in sorted(DISASM_DIR.glob("*.ps")):
        name = ps_file.stem
        yield pytest.param(
            ps_file,
            DISASM_DIR / f"{name}.expected",
            id=name,
        )


@pytest.mark.parametrize("ps_path,expected_path", _disasm_cases())
def test_disasm(ps_path, expected_path):
    """Disassemble a .ps file and verify the mnemonic output."""
    expected = expected_path.read_text() if expected_path.exists() else ""

    result = subprocess.run(
        [sys.executable, str(INTERP), "--disassemble", str(ps_path)],
        capture_output=True,
    )

    actual_stdout = result.stdout.decode()

    assert result.returncode == 0, (
        f"{ps_path.name}: disassembler exited {result.returncode}; "
        f"stderr={result.stderr.decode()!r}"
    )
    assert actual_stdout == expected, (
        f"{ps_path.name}: disasm mismatch\n"
        f"  expected: {expected!r}\n"
        f"  actual:   {actual_stdout!r}"
    )
