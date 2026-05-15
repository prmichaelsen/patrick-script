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
#   - "test-suite"
#   - "conftest"
#   - "corpus"
# summary: >
#   PatrickScript pytest test suite conftest — shared fixtures and path
#   constants for the corpus and disassembler test modules. Defines
#   PROJECT_ROOT, INTERP (src/patrickscript/ps.py), CORPUS_DIR, and
#   DISASM_DIR. Imported by test_corpus.py and test_disasm.py. Also:
#   pytest conftest, PatrickScript tests, test fixtures, interpreter path,
#   corpus dir, disasm dir.
# rationale: >
#   Without this, the test path constants are duplicated across test files.
#   A future wake moving files would need to update multiple places.
# applies: >
#   running PatrickScript tests, adding new test modules, changing
#   project layout
# seeded_questions:
#   - "How do I run the PatrickScript pytest tests?"
#   - "PatrickScript pytest conftest fixtures"
#   - "PatrickScript test suite path configuration"
# @scry.entry.end -->
"""
pytest configuration for PatrickScript tests.
Resolves project-root-relative paths for the interpreter and corpus.
"""
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).parent.parent
INTERP = PROJECT_ROOT / "src" / "patrickscript" / "ps.py"
CORPUS_DIR = PROJECT_ROOT / "corpus"
DISASM_DIR = CORPUS_DIR / "disasm"
