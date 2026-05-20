#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["pillow>=10.0"]
# ///
"""Render examples/brainfuck.ps as a VS Code-dark-themed PNG.

# @scry.entry
# id: code.patrickscript-render-brainfuck~ddf2cca6
# kind: code
# status: active
# weight: 0.7
# tags:
#   - "topic:patrickscript"
#   - "patrickscript"
#   - "topic:site-build"
#   - "site-build"
#   - "topic:brainfuck-image"
#   - "brainfuck-image"
#   - "scope:patrick-script"
#   - "patrick-script"
#   - "topic:render-pipeline"
#   - "render-pipeline"
# summary: >
#   Re-renders examples/brainfuck.ps to site/assets/brainfuck-ps.png — a
#   VS Code-dark-themed PNG showing the compiled Brainfuck interpreter as
#   it appears in an editor. The image is the on-page proof artifact for
#   patrickscript.com §8 (Turing completeness): 14,266 bytes of the word
#   `patrick` and spaces, arranged correctly. Width tuned for the 880px
#   max-width site layout. Run as `uv run site/render_brainfuck.py` from
#   the patrick-script project root.
#   Also: brainfuck.ps render, brainfuck-ps.png, site asset render, PIL
#   editor mock, the proof image, VS Code dark theme, patrickscript.com
#   visual artifact, build-time render, PEP 723 pillow.
# rationale: >
#   Without this script the brainfuck.ps proof artifact on patrickscript.com
#   is a hand-copied PNG that silently drifts when brainfuck.ps evolves.
#   The render script lets a build (or a hand re-run) regenerate the
#   image from the canonical source.
# applies: re-rendering the brainfuck.ps proof image, updating site/assets/brainfuck-ps.png after a spec/interpreter change, debugging the editor-style mock render
# seeded_questions:
#   - "How is site/assets/brainfuck-ps.png generated?"
#   - "Where does patrickscript.com's §8 proof image come from?"
#   - "brainfuck.ps PNG render script"
#   - "PatrickScript site asset render"
# @scry.entry.end
"""

from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont  # type: ignore[import-not-found]


ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "examples" / "brainfuck.ps"
OUT_DIR = ROOT / "site" / "assets"
OUT = OUT_DIR / "brainfuck-ps.png"

# VS Code dark+ palette
BG = (30, 30, 30)
FG = (212, 212, 212)
HIGHLIGHT_BG = (58, 61, 65)
GUTTER_FG = (133, 133, 133)
LINE_NUM_FG = (133, 133, 133)
TAB_BG = (37, 37, 38)
TAB_FG = (212, 212, 212)

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
]
FONT_SIZE = 12

# Layout tuned for a ~1100-px-wide image — fits comfortably inside the
# site's 880px max-width when scaled by the browser, while keeping the
# texture of individual `patrick` tokens legible.
WRAP_W = 130
MAX_DISPLAY_LINES = 80

TAB_H = 30
HEADER_H = 28
GUTTER_W = 50
PADDING_L = 16
PADDING_T = 8


def load_font(size: int = FONT_SIZE) -> ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def wrap_preserve_words(text: str, width: int) -> list[str]:
    """Wrap on space boundaries so 'patrick' is never split."""
    lines: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        end = min(i + width, n)
        if end < n:
            back = text.rfind(" ", i, end)
            if back > i:
                end = back
        lines.append(text[i:end])
        i = end
        if i < n and text[i] == " ":
            i += 1
    return lines


def render() -> Path:
    if not SRC.exists():
        raise SystemExit(f"source not found: {SRC}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    content = SRC.read_text()
    font = load_font()
    bbox = font.getbbox("x")
    char_w = bbox[2] - bbox[0]
    line_h = (bbox[3] - bbox[1]) + 6

    lines = wrap_preserve_words(content, WRAP_W)
    display = lines[:MAX_DISPLAY_LINES]
    truncated = len(lines) > MAX_DISPLAY_LINES

    content_h = len(display) * line_h + PADDING_T * 2
    img_w = GUTTER_W + PADDING_L + WRAP_W * char_w + 50
    img_h = TAB_H + HEADER_H + content_h

    img = Image.new("RGB", (img_w, img_h), BG)
    draw = ImageDraw.Draw(img)

    # Tab bar
    draw.rectangle((0, 0, img_w, TAB_H), fill=TAB_BG)
    tab_label = "≡ brainfuck.ps"
    tab_w = font.getbbox(tab_label)[2] + 36
    draw.rectangle((0, 0, tab_w, TAB_H), fill=BG)
    draw.text((10, 8), tab_label, fill=TAB_FG, font=font)
    draw.text((tab_w - 20, 8), "×", fill=(180, 180, 180), font=font)

    # Breadcrumb
    breadcrumb = "patrick-script  >  examples  >  ≡ brainfuck.ps"
    draw.text((PADDING_L, TAB_H + 6), breadcrumb, fill=GUTTER_FG, font=font)

    # Editor content
    y0 = TAB_H + HEADER_H + PADDING_T
    for idx, line in enumerate(display):
        y = y0 + idx * line_h
        draw.text((PADDING_L, y), str(idx + 1), fill=LINE_NUM_FG, font=font)
        x = GUTTER_W + PADDING_L
        tokens = re.split(r"(patrick)", line)
        occ = 0
        for tok in tokens:
            if not tok:
                continue
            if tok == "patrick":
                highlight = ((idx + occ) % 3 == 0) or ((idx * 5 + occ * 7) % 11 < 3)
                occ += 1
                tw = char_w * len(tok)
                if highlight:
                    draw.rectangle((x, y - 1, x + tw, y + line_h - 3), fill=HIGHLIGHT_BG)
                draw.text((x, y), tok, fill=FG, font=font)
                x += tw
            else:
                tw = char_w * len(tok)
                draw.text((x, y), tok, fill=FG, font=font)
                x += tw

    # Minimap stub
    mini_x = img_w - 32
    draw.rectangle((mini_x, TAB_H + HEADER_H, img_w, img_h), fill=(40, 40, 40))
    for i in range(min(len(display), 60)):
        yy = TAB_H + HEADER_H + 4 + i * 2
        draw.line((mini_x + 4, yy, img_w - 4, yy), fill=(80, 80, 80), width=1)

    img.save(OUT, "PNG", optimize=True)
    sz = OUT.stat().st_size
    print(f"✓ wrote {OUT.relative_to(ROOT)} ({sz:,} bytes; {img_w}x{img_h})")
    print(f"  source: {SRC.relative_to(ROOT)} ({len(content):,} bytes)")
    print(f"  lines : {len(display)}{'  (truncated)' if truncated else ''}")
    return OUT


if __name__ == "__main__":
    render()
