#!/usr/bin/env python3
"""TiDB Next-Gen architecture animation for the SGUAI-C3 cup (48×12).

Design history (so future-you doesn't repeat the iterations):
  v1: 4-tier diagram with drifting wave + flicker + trails — too busy.
  v2: Static 2-tier slab — too abstract without prior context.
  v3: Pure scrolling text — too simplified, no architecture.
  v4 (this version): Labeled architecture diagram with animated flow.

Layout — three labeled regions read left to right:

    ┌─────────────┬──────────────────────────┬───────────┐
    │   TIDB ×N   │     N compute nodes      │    S3     │
    │             │     (dots scaling)       │           │
    │             ▶─── data flow arrows ───▶ │ [cylinder]│
    └─────────────┴──────────────────────────┴───────────┘
       cols 0-14          cols 16-31            cols 33-47

The "×N" counter next to TIDB and the matching node count both grow
(1 → 2 → 4 → 8), so the viewer sees the *number* and the *visual*
agreeing — that's the architectural point: compute scales horizontally,
storage stays the same.

Animation (~13 s loop at speed=200):
    Phase 1 — Reveal: the architecture diagram draws itself in
              (TIDB types, S3 types, cylinder fills, arrows pulse)
    Phase 2 — Scale-out: ×1 → ×2 → ×4 → ×8, each beat held ~1 s
              with a halo flash on the new nodes
    Phase 3 — Sustained throughput: data dots flow continuously
              left → right from compute to storage at full scale
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
    """Storage cylinder: rounded-cap rectangle in the bottom-right.
    fill_fraction 0..1 controls how much is drawn (for the reveal)."""
    width = CYL_RIGHT - CYL_LEFT + 1
    end_x = CYL_LEFT + int(width * fill_fraction)
    # Top and bottom solid lines
    for x in range(CYL_LEFT, end_x):
        img.putpixel((x, CYL_TOP), 1)
        img.putpixel((x, CYL_BOT), 1)
    # Left and right walls (only if cylinder is mostly drawn)
    if fill_fraction > 0.2:
        for y in range(CYL_TOP, CYL_BOT + 1):
            img.putpixel((CYL_LEFT, y), 1)
    if fill_fraction > 0.95:
        for y in range(CYL_TOP, CYL_BOT + 1):
            img.putpixel((CYL_RIGHT, y), 1)
    # Interior dot row in the middle to suggest "data inside"
    if fill_fraction >= 1.0:
        for x in range(CYL_LEFT + 2, CYL_RIGHT, 2):
            img.putpixel((x, (CYL_TOP + CYL_BOT) // 2), 1)


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


def draw_counter(img, n):
    """'×N' counter next to the TIDB label. Renders below TIDB at row 8-11
    so it doesn't compete with the brand."""
    stamp(img, f"X{n}", TIDB_X + 1, 8)


def draw_arrow(img, x_start, x_end, frame_phase):
    """A short horizontal stream of dots traveling from x_start to x_end at
    ARROW_ROW. frame_phase shifts the dot pattern for animation."""
    length = x_end - x_start
    for i in range(length):
        if (i + frame_phase) % 4 == 0:
            x = x_start + i
            if 0 <= x < W:
                img.putpixel((x, ARROW_ROW), 1)


def build_frames():
    frames = []

    # Phase 1 — Reveal (~3 s)
    # 1a. TIDB types in
    for end in range(1, 5):
        f = blank()
        stamp(f, "TIDB"[:end], TIDB_X, TIDB_Y)
        frames.append(f)
    # 1b. Hold full TIDB
    f = blank()
    draw_tidb(f)
    frames.append(f)

    # 1c. S3 types in
    for end in range(1, 3):
        f = blank()
        draw_tidb(f)
        stamp(f, "S3"[:end], S3_X, S3_Y)
        frames.append(f)
    f = blank()
    draw_tidb(f)
    draw_s3(f)
    frames.append(f)

    # 1d. Cylinder fills in
    for frac in (0.3, 0.6, 1.0):
        f = blank()
        draw_tidb(f)
        draw_s3(f)
        draw_cylinder(f, fill_fraction=frac)
        frames.append(f)

    # Phase 2 — Scale-out, with flowing arrows. Each level held for 6 frames.
    HOLD = 6
    for n in (1, 2, 4, 8):
        # Spawn frame: nodes appear with halo flash
        f = blank()
        draw_tidb(f)
        draw_s3(f)
        draw_cylinder(f)
        draw_counter(f, n)
        draw_nodes(f, n, halo_indices=range(n))
        frames.append(f)

        # Settle frames: nodes steady, arrows flowing left → right
        for hold_i in range(HOLD - 1):
            f = blank()
            draw_tidb(f)
            draw_s3(f)
            draw_cylinder(f)
            draw_counter(f, n)
            draw_nodes(f, n)
            draw_arrow(f, NODE_REGION[0] + 1, CYL_LEFT, frame_phase=hold_i)
            frames.append(f)

    # Phase 3 — Sustained throughput at ×8, dense flow
    for phase in range(10):
        f = blank()
        draw_tidb(f)
        draw_s3(f)
        draw_cylinder(f)
        draw_counter(f, 8)
        draw_nodes(f, 8)
        draw_arrow(f, NODE_REGION[0] + 1, CYL_LEFT, frame_phase=phase)
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
