#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# ///
"""Build the PatrickScript /play visualizer page.

# @scry.entry
# id: code.patrickscript-play-build~e6f1c2b8
# kind: code
# status: active
# weight: 0.85
# tags:
#   - "topic:patrickscript"
#   - "patrickscript"
#   - "topic:play"
#   - "play"
#   - "topic:stepper"
#   - "stepper"
#   - "topic:site-build"
#   - "site-build"
#   - "topic:esbuild"
#   - "esbuild"
#   - "scope:patrick-script"
#   - "patrick-script"
# summary: >
#   Build script for the patrickscript.com/play visualizer. Reads the
#   template at site/play.html.template, compiles the TypeScript
#   interpreter at site/js/ps-interpreter.ts into an IIFE bundle via
#   npx esbuild (global name `PS`), assembles each .psa example into
#   its .ps form via the `psa` CLI, builds a JS examples object, and
#   writes site/play.html. Stdlib-only Python: esbuild and the assembler
#   are external subprocesses. Run as:
#     uv run site/build_play.py
#     uv run site/build_play.py --check
#   Also: build_play.py, PatrickScript play page build, /play HTML
#   builder, esbuild IIFE bundle, examples JSON, ps-interpreter.iife,
#   patrickscript.com/play generator.
# rationale: >
#   Without this script the /play page would either ship a hand-copied
#   interpreter (drift risk) or run TypeScript in the browser (no
#   transpiler available). The build resolves both: the .ts is the
#   single source of truth; esbuild produces a browser-ready IIFE.
# applies: rebuilding patrickscript.com/play, adding/removing example
#   programs, refreshing the interpreter bundle after a .ts change
# seeded_questions:
#   - "How is patrickscript.com/play built?"
#   - "How do I rebuild the PatrickScript stepper?"
#   - "Where do /play examples come from?"
#   - "esbuild PatrickScript bundle"
#   - "build_play.py uv run"
# @scry.entry.end

The /play visualizer is generated from:
  - site/play.html.template      (HTML/CSS/JS shell)
  - site/js/ps-interpreter.ts    (the interpreter; compiled via esbuild)
  - examples/<slug>.psa or .ps   (sources; .psa is assembled via ./psa)

Output: site/play.html (single-file, no external resources).

Run:
    uv run site/build_play.py            # writes site/play.html
    uv run site/build_play.py --check    # build to a temp string and diff
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = PROJECT_ROOT / "site" / "play.html.template"
OUTPUT_PATH = PROJECT_ROOT / "site" / "play.html"
INTERPRETER_TS = PROJECT_ROOT / "site" / "js" / "ps-interpreter.ts"
EXAMPLES_DIR = PROJECT_ROOT / "examples"
CORPUS_DIR = PROJECT_ROOT / "corpus"
PSA_TOOL = PROJECT_ROOT / "psa"

PLACEHOLDER_IIFE = "<!--__PS_INTERPRETER_IIFE__-->"
PLACEHOLDER_EXAMPLES = "<!--__PS_EXAMPLES_JSON__-->"
PLACEHOLDER_ORDER = "<!--__PS_EXAMPLE_ORDER_JSON__-->"

# (slug, source-file, optional stdin) — order is the display order in the
# example dropdown. Slug is the URL hash (/play#<slug>).
EXAMPLE_SET = [
    {
        "slug": "hello-world",
        "label": "hello world",
        "source": "hello-world.ps",
        "stdin": "",
    },
    {
        "slug": "fibonacci",
        "label": "fibonacci (first 10)",
        "source": "fibonacci.psa",
        "stdin": "",
    },
    {
        "slug": "factorial-recursive",
        "label": "factorial (recursive)",
        "source": "factorial-recursive.psa",
        "stdin": "",
    },
    {
        "slug": "fizzbuzz",
        "label": "fizzbuzz (1..15)",
        "source": "fizzbuzz.ps",
        "stdin": "",
    },
    {
        "slug": "brainfuck",
        "label": "brainfuck interpreter (reads BF program from stdin)",
        "source": "brainfuck.ps",
        # The PatrickScript brainfuck interpreter reads its BF program
        # from stdin to EOF, then executes it. Hand the corpus's classic
        # "Hello, World!" BF program so /play#brainfuck prints HW out of
        # the box. Crank speed to ∞ — the BF interpreter takes ~100k+
        # PatrickScript opcodes to print 13 characters.
        "stdin_corpus": "brainfuck-hello.stdin",
    },
]


class BuildError(Exception):
    """Raised when the play page cannot be built."""


def compile_interpreter() -> str:
    """Compile ps-interpreter.ts into a browser-ready IIFE bundle."""
    if not INTERPRETER_TS.exists():
        raise BuildError(f"interpreter not found at {INTERPRETER_TS}")
    if not shutil.which("npx"):
        raise BuildError("npx not found on PATH (need Node.js to run esbuild)")
    cmd = [
        "npx",
        "--yes",
        "esbuild",
        str(INTERPRETER_TS),
        "--bundle",
        "--format=iife",
        "--global-name=PS",
        "--target=es2022",
        "--minify",
        "--legal-comments=none",
    ]
    print(f"→ Compiling interpreter: {' '.join(cmd[:6])} …")
    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=PROJECT_ROOT
    )
    if result.returncode != 0:
        raise BuildError(
            f"esbuild failed (exit {result.returncode}):\n{result.stderr.strip()}"
        )
    bundle = result.stdout
    if not bundle.strip():
        raise BuildError("esbuild produced empty bundle")
    print(f"  ✓ bundle: {len(bundle):,} bytes")
    return bundle


def load_example_source(filename: str) -> str:
    """Load a .ps source by name; assemble first if it's a .psa."""
    src_path = EXAMPLES_DIR / filename
    if not src_path.exists():
        raise BuildError(f"example source not found: {src_path}")
    if filename.endswith(".ps"):
        return src_path.read_text(encoding="utf-8")
    if filename.endswith(".psa"):
        if not PSA_TOOL.exists():
            raise BuildError(f"psa assembler not found at {PSA_TOOL}")
        result = subprocess.run(
            [str(PSA_TOOL), str(src_path)],
            capture_output=True, text=True, cwd=PROJECT_ROOT,
        )
        if result.returncode != 0:
            raise BuildError(
                f"psa failed for {filename} (exit {result.returncode}):\n"
                f"{result.stderr.strip()}"
            )
        return result.stdout
    raise BuildError(f"unrecognized example extension: {filename}")


def build_examples_object() -> tuple[dict, list[str]]:
    """Return ({slug: {label, source, stdin}}, [slug, …])."""
    examples: dict = {}
    order: list[str] = []
    for entry in EXAMPLE_SET:
        slug = entry["slug"]
        print(f"→ Loading example: {slug}  ({entry['source']})")
        source = load_example_source(entry["source"])
        if "stdin_corpus" in entry:
            stdin_path = CORPUS_DIR / entry["stdin_corpus"]
            if not stdin_path.exists():
                raise BuildError(f"corpus stdin not found: {stdin_path}")
            stdin = stdin_path.read_text(encoding="utf-8")
        else:
            stdin = entry.get("stdin", "")
        examples[slug] = {
            "label": entry["label"],
            "source": source,
            "stdin": stdin,
        }
        order.append(slug)
        print(f"  ✓ {len(source):,} bytes source / {len(stdin):,} bytes stdin")
    return examples, order


def build(check: bool = False) -> int:
    if not TEMPLATE_PATH.exists():
        print(f"error: template not found at {TEMPLATE_PATH}", file=sys.stderr)
        return 2

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    for placeholder in (PLACEHOLDER_IIFE, PLACEHOLDER_EXAMPLES, PLACEHOLDER_ORDER):
        if placeholder not in template:
            print(
                f"error: placeholder {placeholder!r} not found in {TEMPLATE_PATH}",
                file=sys.stderr,
            )
            return 2

    iife = compile_interpreter()
    examples, order = build_examples_object()

    # JSON-encode the examples table. Use ensure_ascii=False so multibyte
    # characters (e.g. brainfuck's output bytes) survive; the page is UTF-8.
    examples_json = json.dumps(examples, ensure_ascii=False)
    order_json = json.dumps(order)

    output = template
    output = output.replace(PLACEHOLDER_IIFE, iife, 1)
    output = output.replace(PLACEHOLDER_EXAMPLES, examples_json, 1)
    output = output.replace(PLACEHOLDER_ORDER, order_json, 1)

    banner = (
        "<!-- GENERATED FILE — do not edit by hand.\n"
        f"     Source: site/play.html.template + site/js/ps-interpreter.ts\n"
        f"     Build : uv run site/build_play.py\n"
        "-->\n"
    )
    output = re.sub(
        r"^(<!doctype html>\s*\n)",
        r"\1" + banner,
        output,
        count=1,
        flags=re.IGNORECASE,
    )

    if check:
        if OUTPUT_PATH.exists() and OUTPUT_PATH.read_text(encoding="utf-8") == output:
            print(f"✓ {OUTPUT_PATH} is up to date ({len(output):,} bytes)")
            return 0
        print(f"✗ {OUTPUT_PATH} is stale (would write {len(output):,} bytes)")
        return 1

    OUTPUT_PATH.write_text(output, encoding="utf-8")
    print(f"\n✓ wrote {OUTPUT_PATH} ({len(output):,} bytes)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify that site/play.html is up to date; do not write.",
    )
    args = parser.parse_args(argv)
    try:
        return build(check=args.check)
    except BuildError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
