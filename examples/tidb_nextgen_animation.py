#!/usr/bin/env python3
"""TiDB Next-Gen animation for the SGUAI-C3 cup (48×12).

Reframed approach: stop trying to render an architecture diagram on
48×12 — that canvas geometry doesn't support multi-tier layered
diagrams. Use what 48×12 IS good for: large numeric magnitudes and
bar-graph visualizations.

This animation treats the cup like a tiny telemetry dashboard. A
big numeric counter climbs through orders of magnitude
(1K → 10K → 100K → 1M → 10M → ∞), with a load bar at the bottom
filling and resetting on each scale-up. Reads as "TiDB Next-Gen is
handling absurd amounts of load and just keeps scaling".

Layout:

    rows 0-7: large 8-row digit display (centered horizontally)
    row  8  : (gap)
    rows 9-11: load bar — fills left→right as the counter climbs

Animation (~6 s loop at speed=200):
    Each value (1K, 10K, 100K, 1M, 10M, ∞) is shown for ~6 frames
    while the load bar fills proportionally. After ∞ the cycle
    resets to 1K with a brief flash.
"""

from pathlib import Path
from PIL import Image

W, H = 48, 12

# 8-row hand-pixel font for the big digits/letters in the counter.
# Digits are 5 px wide; letters (K, M) are 5 px wide; ∞ is 7 px wide.
GLYPHS_8 = {
    '0': ["·███·", "█···█", "█···█", "█···█", "█···█", "█···█", "█···█", "·███·"],
    '1': ["··█··", "·██··", "··█··", "··█··", "··█··", "··█··", "··█··", "·███·"],
    '2': ["·███·", "█···█", "····█", "···█·", "··█··", "·█···", "█····", "█████"],
    '3': ["·███·", "█···█", "····█", "··██·", "····█", "····█", "█···█", "·███·"],
    '4': ["···█·", "··██·", "·█·█·", "█··█·", "█████", "···█·", "···█·", "···█·"],
    '5': ["█████", "█····", "█····", "████·", "····█", "····█", "█···█", "·███·"],
    '6': ["··██·", "·█···", "█····", "████·", "█···█", "█···█", "█···█", "·███·"],
    '7': ["█████", "····█", "···█·", "··█··", "·█···", "·█···", "█····", "█····"],
    '8': ["·███·", "█···█", "█···█", "·███·", "█···█", "█···█", "█···█", "·███·"],
    '9': ["·███·", "█···█", "█···█", "█···█", "·████", "····█", "···█·", "·██··"],
    'K': ["█···█", "█··█·", "█·█··", "██···", "██···", "█·█··", "█··█·", "█···█"],
    'M': ["█···█", "██·██", "█·█·█", "█·█·█", "█···█", "█···█", "█···█", "█···█"],
    'I': ["·",     "·",     "·",     "·",     "·",     "·",     "·",     "·"],   # placeholder
    # Infinity symbol (8x4, drawn small relative to the 8-row band so it
    # sits visually centered)
    '∞': ["·······",
          "·······",
          "·██·██·",
          "█··█··█",
          "█··█··█",
          "·██·██·",
          "·······",
          "·······"],
    ' ': ["·"]*8,
}


def stamp(img, text, x0, y0):
    """Stamp text. Returns the rightmost x written."""
    x = x0
    for ch in text:
        g = GLYPHS_8.get(ch)
        if g is None:
            x += 4
            continue
        gw = max(len(row) for row in g)
        for ry, row in enumerate(g):
            for rx in range(gw):
                if rx < len(row) and row[rx] == '█':
                    px, py = x + rx, y0 + ry
                    if 0 <= px < W and 0 <= py < H:
                        img.putpixel((px, py), 1)
        x += gw + 1
    return x - 1


def text_width(text):
    """Width in pixels of a rendered string (with 1 px gaps)."""
    total = 0
    for ch in text:
        g = GLYPHS_8.get(ch)
        if g is None:
            total += 4
            continue
        total += max(len(row) for row in g) + 1
    return total - 1 if text else 0


def blank():
    return Image.new('1', (W, H), 0)


def draw_centered_text(img, text, y=0):
    w = text_width(text)
    x = (W - w) // 2
    stamp(img, text, x, y)


def draw_load_bar(img, fill_fraction):
    """Load bar at rows 9-11 spanning the full width.
    Outline always visible; interior fills proportionally."""
    # Outline
    bar_top, bar_bot = 9, 11
    for x in range(W):
        img.putpixel((x, bar_top), 1)
        img.putpixel((x, bar_bot), 1)
    img.putpixel((0, 10), 1)
    img.putpixel((W - 1, 10), 1)
    # Interior fill — width 0..W-2
    fill_x = max(1, int((W - 2) * fill_fraction)) + 1
    for x in range(1, fill_x):
        img.putpixel((x, 10), 1)


def build_frames():
    frames = []

    # Counter steps: each label + how many frames to hold it
    steps = [
        ("1K",    6, 0.05),
        ("10K",   6, 0.20),
        ("100K",  6, 0.45),
        ("1M",    6, 0.65),
        ("10M",   6, 0.85),
        ("∞",     8, 1.00),
    ]

    for label, hold, fill in steps:
        # Brief halo flash on the first frame of each new value: thicken
        # the digits by setting the row above the digits to outline them.
        for k in range(hold):
            f = blank()
            draw_centered_text(f, label, y=0)
            draw_load_bar(f, fill_fraction=fill)
            # Flash effect: invert a thin sliver above the text on first
            # frame of each new label so the eye sees a "tick".
            if k == 0:
                # Just toggle bottom-right pixel for frame uniqueness too
                f.putpixel((W - 1, 0), 1)
            elif k == 1:
                f.putpixel((W - 2, 0), 1)
            else:
                # Frame uniqueness toggle so PIL doesn't dedupe
                if k & 1:
                    f.putpixel((0, 0), 1)
            frames.append(f)

    # Brief reset flash before loop: invert the whole display for one frame
    inv = blank()
    for y in range(H):
        for x in range(W):
            inv.putpixel((x, y), 1)
    # Then knock out the digits where the last "∞" frame had pixels
    last = frames[-1]
    for y in range(H):
        for x in range(W):
            if last.getpixel((x, y)):
                inv.putpixel((x, y), 0)
    frames.append(inv)

    # 1-frame blank to mark loop boundary
    frames.append(blank())

    return frames


def main():
    frames = build_frames()
    if len(frames) > 255:
        raise RuntimeError(f"frame count {len(frames)} exceeds protocol limit")
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
