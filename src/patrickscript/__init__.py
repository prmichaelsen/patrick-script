# <!-- @scry.entry
# id: code.patrickscript-pkg-init~70744bf4
# kind: code
# status: active
# weight: 0.6
# tags:
#   - "topic:patrickscript"
#   - "patrickscript"
#   - "topic:packaging"
#   - "packaging"
#   - "pypi"
# summary: >
#   PatrickScript Python package init. Entry point for the `patrickscript`
#   PyPI package (src/patrickscript/__init__.py). Exports version string;
#   console scripts `patrickscript` and `patrickscript-asm` delegate to
#   ps.main() and psa.main() respectively. Also: patrickscript package,
#   PyPI packaging, pyproject.toml, src layout, console scripts.
# rationale: >
#   Without this, the patrickscript package is not importable after pip
#   install. This is the package root that hatchling builds.
# applies: installing PatrickScript via pip, building the PyPI package
# seeded_questions:
#   - "patrickscript PyPI package init"
#   - "How to install PatrickScript via pip?"
# @scry.entry.end -->
"""PatrickScript — a language with exactly two lexical tokens."""

__version__ = "1.3.0"
