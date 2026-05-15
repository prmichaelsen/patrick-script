# <!-- @scry.entry
# id: code.patrickscript-pytest-suite~eb722a5c
# kind: code
# status: active
# weight: 0.8
# tags:
#   - "topic:patrickscript"
#   - "topic:testing"
#   - "patrickscript"
#   - "pytest"
#   - "corpus"
#   - "conformance"
# summary: >
#   PatrickScript pytest conformance corpus runner. Parametrized over all
#   *.ps files in corpus/ (excluding corpus/disasm/). Strips trailing
#   newlines before comparing stdout to *.expected, matching bash
#   command-substitution semantics. Also: PatrickScript tests, corpus runner,
#   pytest parametrize, conformance test suite.
# rationale: >
#   Without this, the only test runner is a bash script. pytest gives better
#   output, CI integration, and runs via `uv run pytest`.
# applies: >
#   running PatrickScript conformance tests, adding corpus tests, CI setup
# seeded_questions:
#   - "How do I run PatrickScript conformance tests?"
#   - "PatrickScript pytest corpus runner"
# @scry.entry.end -->
"""
PatrickScript conformance corpus — pytest test suite.

Discovers every *.ps file in corpus/ (excluding corpus/disasm/) and runs it
through the reference interpreter, comparing stdout to the corresponding
*.expected file.

Comparison rules mirror the shell corpus runner (corpus/run-tests.sh):
  - Trailing newlines are stripped from both actual and expected before
    comparison. This matches bash command-substitution semantics ($(...)).
  - Exit code is not checked. Some tests intentionally trigger runtime
    errors (exit 1) and produce empty stdout; they pass because the empty
    expected file matches the empty actual stdout after stripping.
"""
import subprocess
import sys
from pathlib import Path

import pytest

from .conftest import CORPUS_DIR, INTERP


def _corpus_cases():
    """
    Yield (ps_path, stdin_path, expected_path) for every corpus test.
    Excludes files inside corpus/disasm/.
    """
    for ps_file in sorted(CORPUS_DIR.glob("*.ps")):
        name = ps_file.stem
        yield pytest.param(
            ps_file,
            CORPUS_DIR / f"{name}.stdin",
            CORPUS_DIR / f"{name}.expected",
            id=name,
        )


@pytest.mark.parametrize("ps_path,stdin_path,expected_path", _corpus_cases())
def test_corpus(ps_path, stdin_path, expected_path):
    """Run a corpus test and verify stdout matches expected output."""
    stdin_bytes = (
        stdin_path.read_bytes()
        if stdin_path.exists() and stdin_path.stat().st_size > 0
        else b""
    )
    expected = (expected_path.read_text() if expected_path.exists() else "").rstrip(
        "\n"
    )

    result = subprocess.run(
        [sys.executable, str(INTERP), str(ps_path)],
        input=stdin_bytes,
        capture_output=True,
    )

    actual_stdout = result.stdout.decode().rstrip("\n")

    assert actual_stdout == expected, (
        f"{ps_path.name}: stdout mismatch\n"
        f"  expected: {expected!r}\n"
        f"  actual:   {actual_stdout!r}"
    )
