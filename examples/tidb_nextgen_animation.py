#!/usr/bin/env python3
"""TiDB Next-Gen tagline marquee for the SGUAI-C3 cup (48×12).

Lessons from earlier drafts:
- Abstract pixel diagrams (tiers, arrows, nodes) on 48×12 don't read
  without prior context. Words are clearer.
- Tiny TrueType fonts (Helvetica 11) render at ~5 px wide per char,
  barely legible on a physical LED matrix at this scale.
- 4 phrases × full-width scroll = >300 frames, exceeds the cup's
  255-frame protocol limit.

So this version uses a **hand-rolled bold 9-row pixel font** for max
legibility (each letter is 6–7 px wide, distinctly readable), and
scrolls a single punchy tagline:

    TIDB NEXT-GEN ▸ INFINITE SCALE

Total ~80 frames. Loop at speed=200 → ~13 s per scroll.

Usage
-----
    uv run --with pillow python examples/tidb_nextgen_animation.py
    cd python && uv run smart_mug.py animate ../examples/tidb_nextgen.gif -s 200
"""

from pathlib import Path
from PIL import Image

W, H = 48, 12

# 9-row hand-pixel font, designed for maximum readability on a 12-row
# LED matrix. Each glyph is variable-width; '·' = off, '█' = on.
GLYPHS = {
    'T': ["█████",
          "··█··",
          "··█··",
          "··█··",
          "··█··",
          "··█··",
          "··█··",
          "··█··",
          "··█··"],
    'I': ["███",
          "·█·",
          "·█·",
          "·█·",
          "·█·",
          "·█·",
          "·█·",
          "·█·",
          "███"],
    'D': ["████·",
          "█···█",
          "█···█",
          "█···█",
          "█···█",
          "█···█",
          "█···█",
          "█···█",
          "████·"],
    'B': ["████·",
          "█···█",
          "█···█",
          "████·",
          "█···█",
          "█···█",
          "█···█",
          "█···█",
          "████·"],
    'N': ["█···█",
          "██··█",
          "██··█",
          "█·█·█",
          "█·█·█",
          "█·█·█",
          "█··██",
          "█··██",
          "█···█"],
    'E': ["█████",
          "█····",
          "█····",
          "█····",
          "█████",
          "█····",
          "█····",
          "█····",
          "█████"],
    'X': ["█···█",
          "█···█",
          "·█·█·",
          "·█·█·",
          "··█··",
          "·█·█·",
          "·█·█·",
          "█···█",
          "█···█"],
    '-': ["·····",
          "·····",
          "·····",
          "·····",
          "█████",
          "·····",
          "·····",
          "·····",
          "·····"],
    'G': ["·████",
          "█····",
          "█····",
          "█····",
          "█·███",
          "█···█",
          "█···█",
          "█···█",
          "·████"],
    'F': ["█████",
          "█····",
          "█····",
          "█····",
          "█████",
          "█····",
          "█····",
          "█····",
          "█····"],
    'S': ["·████",
          "█····",
          "█····",
          "█····",
          "·███·",
          "····█",
          "····█",
          "····█",
          "████·"],
    'C': ["·████",
          "█····",
          "█····",
          "█····",
          "█····",
          "█····",
          "█····",
          "█····",
          "·████"],
    'A': ["··█··",
          "·█·█·",
          "·█·█·",
          "█···█",
          "█████",
          "█···█",
          "█···█",
          "█···█",
          "█···█"],
    'L': ["█····",
          "█····",
          "█····",
          "█····",
          "█····",
          "█····",
          "█····",
          "█····",
          "█████"],
    ' ': ["···",
          "···",
          "···",
          "···",
          "···",
          "···",
          "···",
          "···",
          "···"],
    '·': ["·",
          "·",
          "·",
          "·",
          "·",
          "█",
          "·",
          "·",
          "·"],
    '*': ["·",
          "·",
          "·",
          "█",
          "█",
          "█",
          "·",
          "·",
          "·"],   # 3-pixel midline dot used as separator
}

GLYPH_H = 9
GLYPH_GAP = 1   # pixels between adjacent glyphs

# The phrase to scroll. Uppercase only — that's all the font has.
PHRASE = "TIDB NEXT-GEN * INFINITE SCALE"


def render_phrase(text):
    """Render the phrase to a wide 1-bit image. Returns the image and
    its true text width (without leading/trailing margin)."""
    # Compute total width
    widths = []
    for ch in text:
        g = GLYPHS.get(ch)
        if g is None:
            continue
        widths.append(max(len(row) for row in g))
    text_w = sum(widths) + GLYPH_GAP * (len(widths) - 1)

    # Add 1×W of leading/trailing blank so the marquee enters from the
    # right edge and exits past the left edge cleanly.
    canvas = Image.new('1', (text_w + 2 * W, H), 0)
    x = W  # start drawing after the leading blank
    y = (H - GLYPH_H) // 2   # vertical center; leaves 1 row top/bottom

    for ch in text:
        g = GLYPHS.get(ch)
        if g is None:
            continue
        gw = max(len(row) for row in g)
        for ry, row in enumerate(g):
            for rx in range(gw):
                if rx < len(row) and row[rx] == '█':
                    px = x + rx
                    py = y + ry
                    if 0 <= px < canvas.width and 0 <= py < H:
                        canvas.putpixel((px, py), 1)
        x += gw + GLYPH_GAP

    return canvas


def crop_window(strip, x_offset):
    """48×12 viewport into the strip at column x_offset."""
    win = Image.new('1', (W, H), 0)
    src = strip.crop((x_offset, 0, x_offset + W, H))
    win.paste(src, (0, 0))
    return win


def build_frames():
    strip = render_phrase(PHRASE)
    max_offset = strip.width - W
    # Scroll at 3 px/frame: at speed=200 (~160 ms/frame) that's ~19 px/s,
    # comfortable reading pace for tall text.
    PIXELS_PER_FRAME = 3
    frames = []
    x = 0
    while x <= max_offset:
        frames.append(crop_window(strip, x))
        x += PIXELS_PER_FRAME
    # Ensure final frame at exactly max_offset (so the trailing blank
    # is fully visible before the cup loops back to frame 0)
    if frames[-1] is not None and (max_offset - (x - PIXELS_PER_FRAME)) > 0:
        frames.append(crop_window(strip, max_offset))
    return frames


def main():
    frames = build_frames()
    if len(frames) > 255:
        raise RuntimeError(f"frame count {len(frames)} exceeds protocol limit (255)")
    out = Path(__file__).resolve().parent / "tidb_nextgen.gif"
    frames[0].save(
        out,
        save_all=True,
        append_images=frames[1:],
        duration=160,
        loop=0,
        optimize=False,
        disposal=2,
    )
    print(f"✓ wrote {out} ({len(frames)} frames)")


if __name__ == "__main__":
    main()
