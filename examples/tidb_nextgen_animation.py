#!/usr/bin/env python3
"""TiDB Next-Gen architecture animation for the SGUAI-C3 cup (48×12).

Design history (so future-you doesn't repeat the iterations):
  v1: 4-tier diagram with drifting wave + flicker + trails — too busy.
  v2: Static 2-tier slab — too abstract without prior context.
  v3: Pure scrolling text — too simplified, no architecture.
  v4: Labeled architecture diagram with counter + arrows — still busy.
  v5 (this version): Same labeled architecture, decluttered to four
      elements: TIDB label, scaling nodes, S3 label, cylinder outline.

Layout — three labeled regions read left to right:

    ┌─────────────┬──────────────────────────┬───────────┐
    │   TIDB      │     N compute nodes      │    S3     │
    │             │     (dots scaling)       │           │
    │             │                          │ [cylinder]│
    └─────────────┴──────────────────────────┴───────────┘
       cols 0-14          cols 16-31            cols 33-47

The visible node count IS the scale indicator — no separate counter
needed. The S3 cylinder outline stays unchanged across all frames;
only the compute nodes grow. That side-by-side (compute scales,
storage doesn't) is the architectural punchline.

Animation (~6 s loop at speed=200):
    Phase 1 — Reveal: TIDB types in, S3 types in, cylinder draws.
    Phase 2 — Scale-out: ×1 → ×2 → ×4 → ×8, each beat held ~1 s
              with a halo flash on the new nodes.
"""

from pathlib import Path
from PIL import Image

W, H = 48, 12

# 7-row pixel font for the brand labels (matches the tidb_scale example)
GLYPHS_7 = {
    'T': ["█████", "··█··", "··█··", "··█··", "··█··", "··█··", "··█··"],
    'I': ["█",     "·",     "█",     "█",     "█",     "█",     "█"],
    'D': ["████·", "█···█", "█···█", "█···█", "█···█", "█···█", "████·"],
    'B': ["████·", "█···█", "████·", "█···█", "█···█", "█···█", "████·"],
    'S': ["·███", "█···", "·██·", "···█", "···█", "···█", "███·"],
    '3': ["███·", "···█", "·██·", "···█", "···█", "···█", "███·"],
    'X': ["·",   "█·█", "·█·", "·█·", "·█·", "█·█", "·"],
    '1': ["█",   "█",   "█",   "█",   "█",   "█",   "█"],
    '2': ["███", "··█", "··█", "·█·", "█··", "█··", "███"],
    '4': ["█·█", "█·█", "███", "··█", "··█", "··█", "··█"],
    '8': ["███", "█·█", "███", "█·█", "█·█", "█·█", "███"],
    ' ': ["·"]*7,
}


def stamp(img, text, x0, y0, max_x=None):
    """Stamp text starting at (x0,y0), 1-px gap between glyphs.
    max_x clips drawing so we can wipe-in characters partially."""
    x = x0
    for ch in text:
        g = GLYPHS_7.get(ch)
        if g is None:
            x += 4
            continue
        gw = max(len(row) for row in g)
        for ry, row in enumerate(g):
            for rx in range(gw):
                if rx < len(row) and row[rx] == '█':
                    px = x + rx
                    py = y0 + ry
                    if 0 <= px < W and 0 <= py < H:
                        if max_x is None or px < max_x:
                            img.putpixel((px, py), 1)
        x += gw + 1
    return x - 1


def blank():
    return Image.new('1', (W, H), 0)


# Layout constants
TIDB_X, TIDB_Y = 1, 1                      # 7-row label, ~14 px wide
NODE_REGION = (16, 31)                      # x range for compute nodes
ARROW_ROW = 9                                # data-flow arrows here
S3_X, S3_Y = 35, 1                          # "S3" label
CYL_TOP, CYL_BOT = 8, 11                    # storage cylinder rows
CYL_LEFT, CYL_RIGHT = 33, 47


def draw_tidb(img):
    stamp(img, "TIDB", TIDB_X, TIDB_Y)


def draw_s3(img):
    stamp(img, "S3", S3_X, S3_Y)


def draw_cylinder(img, fill_fraction=1.0):
    """Storage cylinder outline (rectangle). No interior decoration —
    the eye should register the shape, not parse pattern. fill_fraction
    0..1 controls how much is drawn (for the reveal)."""
    width = CYL_RIGHT - CYL_LEFT + 1
    end_x = CYL_LEFT + int(width * fill_fraction)
    # Top and bottom edges
    for x in range(CYL_LEFT, end_x):
        img.putpixel((x, CYL_TOP), 1)
        img.putpixel((x, CYL_BOT), 1)
    # Left edge appears once we're 20% drawn
    if fill_fraction > 0.2:
        for y in range(CYL_TOP, CYL_BOT + 1):
            img.putpixel((CYL_LEFT, y), 1)
    # Right edge appears at the very end (closing the box)
    if fill_fraction >= 1.0:
        for y in range(CYL_TOP, CYL_BOT + 1):
            img.putpixel((CYL_RIGHT, y), 1)


# Compute-node positions for each scale level. Nodes are 1-px dots in a
# horizontal row, vertically positioned in the middle of the display.
NODE_Y = 5
NODE_LAYOUTS = {
    1: [24],
    2: [20, 28],
    4: [18, 22, 26, 30],
    8: [16, 18, 20, 23, 25, 27, 29, 31],
}


def draw_nodes(img, n, halo_indices=()):
    """Draw n compute nodes as small filled blocks at NODE_Y.
    Each node is 1×2 (single column, 2 rows tall) for visibility.
    halo_indices get an extra pixel above/below to suggest a flash."""
    if n not in NODE_LAYOUTS:
        return
    for i, x in enumerate(NODE_LAYOUTS[n]):
        if not (0 <= x < W):
            continue
        for y_off in (0, 1):
            img.putpixel((x, NODE_Y + y_off), 1)
        if i in halo_indices:
            if NODE_Y - 1 >= 0:
                img.putpixel((x, NODE_Y - 1), 1)
            if NODE_Y + 2 < H:
                img.putpixel((x, NODE_Y + 2), 1)


def _add_frame_id_pixel(img, frame_idx):
    """Toggle a single pixel near the top-left corner per frame so PIL
    doesn't dedupe byte-identical settle frames during GIF encoding.
    The pixel is at row 0 col 0 — visually negligible against the
    architecture in rows 1-11."""
    if frame_idx & 1:
        img.putpixel((0, 0), 1)


def build_frames():
    frames = []

    # Phase 1 — Reveal: architecture draws itself in.
    for end in range(1, 5):  # TIDB types in
        f = blank()
        stamp(f, "TIDB"[:end], TIDB_X, TIDB_Y)
        frames.append(f)
    f = blank(); draw_tidb(f); frames.append(f)  # hold

    for end in range(1, 3):  # S3 types in
        f = blank()
        draw_tidb(f)
        stamp(f, "S3"[:end], S3_X, S3_Y)
        frames.append(f)
    f = blank(); draw_tidb(f); draw_s3(f); frames.append(f)

    for frac in (0.4, 0.7, 1.0):  # cylinder draws in
        f = blank()
        draw_tidb(f)
        draw_s3(f)
        draw_cylinder(f, fill_fraction=frac)
        frames.append(f)

    # Phase 2 — Scale-out, ×1 → ×8. Each level held ~1 s.
    HOLD = 6
    for n in (1, 2, 4, 8):
        # Spawn frame: halo flash on new nodes
        f = blank()
        draw_tidb(f); draw_s3(f); draw_cylinder(f)
        draw_nodes(f, n, halo_indices=range(n))
        frames.append(f)
        # Settle frames: still scene; toggle frame-id pixel so PIL
        # doesn't dedupe them during GIF encoding
        for hold_i in range(HOLD - 1):
            f = blank()
            draw_tidb(f); draw_s3(f); draw_cylinder(f)
            draw_nodes(f, n)
            _add_frame_id_pixel(f, hold_i)
            frames.append(f)

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
