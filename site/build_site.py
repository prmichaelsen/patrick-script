#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["markdown>=3.5"]
# ///
"""Build the PatrickScript landing page by transcluding the canonical spec.

# @scry.entry
# id: code.patrickscript-site-build~605b2302
# kind: code
# status: active
# weight: 0.8
# tags:
#   - "topic:patrickscript"
#   - "patrickscript"
#   - "topic:site-build"
#   - "site-build"
#   - "topic:landing-page"
#   - "landing-page"
#   - "scope:patrick-script"
#   - "patrick-script"
#   - "topic:transclusion"
#   - "transclusion"
#   - "topic:markdown"
#   - "markdown"
# summary: >
#   PatrickScript landing-page build script. Reads the canonical spec at
#   spec/patrickscript.md, strips its @scry.entry marker, renders the
#   remaining Markdown to HTML, and substitutes it into the
#   `<!-- SPEC_HTML -->` placeholder in site/index.html.template, writing
#   the result to site/index.html. The build-time include guarantees the
#   on-page Full Specification section cannot silently drift from the
#   canonical spec source — a spec change is a redeploy, not a sync step.
#   Run as: `uv run site/build_site.py` from the patrick-script project
#   root. PEP-723 inline script metadata declares the `markdown` runtime
#   dependency so the script is self-contained.
#   Also: build_site.py, PatrickScript site build, spec transclusion,
#   landing page generator, markdown to HTML, uv run inline metadata,
#   PEP 723, no-duplicate spec, build-time include, drift-free embed.
# rationale: >
#   Without this script the embedded Full Specification on patrickscript.com
#   would be a hand-copied duplicate of the canonical spec, which silently
#   diverges on every spec change. The build script enforces a single
#   source of truth.
# applies: editing the patrickscript.com landing page, updating the embedded full spec, syncing the site after a spec change, regenerating site/index.html
# seeded_questions:
#   - "How is the PatrickScript landing page built?"
#   - "Where does the embedded full spec on patrickscript.com come from?"
#   - "How do I regenerate patrickscript.com after a spec change?"
#   - "PatrickScript site build script"
#   - "build_site.py uv run"
#   - "PatrickScript spec transclusion"
# @scry.entry.end

The on-page Full Specification section is generated from
`spec/patrickscript.md` at build time. There is no hand-copied duplicate
to keep in sync.

Run:
    uv run site/build_site.py            # writes site/index.html
    uv run site/build_site.py --check    # build to a temp file and diff

The script is intentionally small and stdlib-only except for the
`markdown` package (declared in the PEP-723 inline metadata above).
"""

from __future__ import annotations

import argparse
import base64
import re
import sys
from pathlib import Path

import markdown  # type: ignore[import-not-found]


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SPEC_PATH = PROJECT_ROOT / "spec" / "patrickscript.md"
TEMPLATE_PATH = PROJECT_ROOT / "site" / "index.html.template"
OUTPUT_PATH = PROJECT_ROOT / "site" / "index.html"
BRAINFUCK_PNG_PATH = PROJECT_ROOT / "site" / "assets" / "brainfuck-ps.png"

PLACEHOLDER = "<!--__PATRICKSCRIPT_SPEC_HTML__-->"
BRAINFUCK_PLACEHOLDER = "<!--__PATRICKSCRIPT_BRAINFUCK_PNG_DATAURI__-->"

# The opening HTML comment that introduces the @scry.entry block at the
# top of the canonical spec. We strip the entire comment so it doesn't
# render on the page.
SCRY_MARKER_RE = re.compile(
    r"^<!--\s*@scry\.entry.*?@scry\.entry\.end\s*-->\s*",
    re.DOTALL,
)

# After stripping the marker the spec begins with `# PatrickScript
# Language Specification`. The page already has its own h1, so we demote
# the spec's single h1 to h2-equivalent (we render it as <h2 class="spec-title">).
# All other headings (## → h2, ### → h3, etc.) keep their level. The
# embedded spec is wrapped in <section class="spec-embed"> so we can scope
# CSS to it without leaking into the rest of the page.


def strip_marker(text: str) -> str:
    """Strip the leading @scry.entry HTML comment block from the spec."""
    return SCRY_MARKER_RE.sub("", text, count=1).lstrip()


def render_spec_html(spec_md: str) -> str:
    """Render the spec Markdown to HTML, wrapped in <section class="spec-embed">."""
    body = strip_marker(spec_md)
    md = markdown.Markdown(
        extensions=["tables", "fenced_code", "sane_lists", "attr_list"],
        output_format="html5",
    )
    rendered = md.convert(body)
    # Wrap in a scoping section so CSS can target the embedded spec
    # without leaking into the rest of the page.
    return f'<section class="spec-embed" aria-label="PatrickScript v1.3.0 — full specification">\n{rendered}\n</section>'


def build(check: bool = False) -> int:
    if not SPEC_PATH.exists():
        print(f"error: spec not found at {SPEC_PATH}", file=sys.stderr)
        return 2
    if not TEMPLATE_PATH.exists():
        print(f"error: template not found at {TEMPLATE_PATH}", file=sys.stderr)
        return 2

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    if PLACEHOLDER not in template:
        print(
            f"error: placeholder {PLACEHOLDER!r} not found in template "
            f"{TEMPLATE_PATH}",
            file=sys.stderr,
        )
        return 2

    spec_md = SPEC_PATH.read_text(encoding="utf-8")
    spec_html = render_spec_html(spec_md)

    output = template.replace(PLACEHOLDER, spec_html, 1)

    # Inline the brainfuck.ps proof image as a base64 data URI. The
    # patrickscript-landing Cloudflare Worker inlines the HTML, so a
    # data URI is the simplest path: one Worker, one response, no
    # separate asset route to maintain. The PNG is regenerated by
    # `uv run site/render_brainfuck.py` and committed alongside this
    # template; the build reads whatever is at site/assets/brainfuck-ps.png
    # at build time.
    if BRAINFUCK_PLACEHOLDER in output:
        if not BRAINFUCK_PNG_PATH.exists():
            print(
                f"error: brainfuck PNG not found at {BRAINFUCK_PNG_PATH}\n"
                f"       run `uv run site/render_brainfuck.py` first.",
                file=sys.stderr,
            )
            return 2
        png_bytes = BRAINFUCK_PNG_PATH.read_bytes()
        b64 = base64.b64encode(png_bytes).decode("ascii")
        data_uri = f"data:image/png;base64,{b64}"
        output = output.replace(BRAINFUCK_PLACEHOLDER, data_uri, 1)

    # Generated-file banner — sits inside the existing <!doctype html>
    # comment chain so the file remains valid HTML5 and so a human
    # opening the file sees the provenance up front.
    banner = (
        "<!-- GENERATED FILE — do not edit by hand.\n"
        f"     Source: site/index.html.template + spec/patrickscript.md\n"
        f"     Build : uv run site/build_site.py\n"
        "-->\n"
    )
    # Insert banner immediately after the doctype declaration.
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
    print(f"✓ wrote {OUTPUT_PATH} ({len(output):,} bytes)")
    print(f"  spec    : {SPEC_PATH.relative_to(PROJECT_ROOT)} "
          f"({len(spec_md):,} bytes md → {len(spec_html):,} bytes html)")
    print(f"  template: {TEMPLATE_PATH.relative_to(PROJECT_ROOT)} "
          f"({len(template):,} bytes)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify that site/index.html is up to date; do not write.",
    )
    args = parser.parse_args(argv)
    return build(check=args.check)


if __name__ == "__main__":
    sys.exit(main())
