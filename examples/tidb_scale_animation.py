#!/usr/bin/env python3
"""TiDB scalability animation for the SGUAI-C3 cup (48×12 monochrome).

Produces an animated GIF that tells a "horizontal scale-out" story in
~4 seconds at speed=255:

    Phase 1 — "TiDB" text wipes in left-to-right like a progress bar
              booting up. Sparse Matrix-rain dots fall in the right
              region, suggesting an idle cluster.
    Phase 2 — Nodes scale 1 → 2 → 4 → 8 → 16. Each beat shows a "spawn"
              frame (filled diamond + 1-px halo) followed by a "settled"
              frame. The diamonds shrink as count grows; at n=16 they're
              single pixels.
    Phase 3 — A 3-pixel-wide bright wave packet sweeps L→R across the
              16-node steady state, reading as data flowing through the
              scaled cluster.
    Phase 4 — Sting: the entire display inverts for one frame, then
              briefly holds steady before looping.

Layered effects (Matrix rain + scaling diamonds + wave packet + text
wipe + inversion sting) work together to create motion density that
reads as "scalable distributed system" on a 1-bit LED matrix.

Usage
-----
    # Generate the GIF (overwrites tidb_scale.gif next to this script):
    uv run --with pillow examples/tidb_scale_animation.py

    # Send to cup at max speed for fluid motion (~4 s loop):
    uv run python/smart_mug.py animate examples/tidb_scale.gif -s 255

The pre-rendered tidb_scale.gif is checked in alongside this script
so you can upload without running the generator.
"""

from pathlib import Path
import random

from PIL import Image

W, H = 48, 12

# Hand-rolled 4-pixel-tall-ish glyphs (tightest legible "TiDB").
# The display is only 12 rows tall and we need to fit the brand
# alongside a node visualization, so the font has to be tiny.
GLYPHS = {
    'T': ["███████", "···█···", "···█···", "···█···", "···█···", "···█···", "···█···"],
    'i': ["█",       "·",       "█",       "█",       "█",       "█",       "█"],
    'D': ["█████",   "█···█",   "█···█",   "█···█",   "█···█",   "█···█",   "█████"],
    'B': ["█████",   "█···█",   "█···█",   "█████",   "█···█",   "█···█",   "█████"],
}

# Layout: text 0..20, gap, nodes 23..47.
TEXT_W = 7 + 1 + 1 + 1 + 5 + 1 + 5  # 21
TEXT_Y = (H - 7) // 2                # 2
NODE_X0 = TEXT_W + 2                 # 23
NODE_X1 = W - 1                      # 47
NODE_W = NODE_X1 - NODE_X0 + 1       # 25


def stamp(img, text, x0, y0, mask_x_max=None):
    """Stamp `text` at (x0, y0). If mask_x_max is given, only pixels
    with `x < mask_x_max` are drawn — used for the left-to-right wipe."""
    x = x0
    for ch in text:
        g = GLYPHS[ch]
        gw = max(len(r) for r in g)
        for ry, row in enumerate(g):
            for rx in range(gw):
                if rx < len(row) and row[rx] == "█":
                    px, py = x + rx, y0 + ry
                    if 0 <= px < W and 0 <= py < H:
                        if mask_x_max is None or px < mask_x_max:
                            img.putpixel((px, py), 1)
        x += gw + 1
    return x - 1


def blank():
    return Image.new('1', (W, H), 0)


def filled_diamond(img, cx, cy, r):
    """Diamond shape (Manhattan-distance disc) centered at (cx, cy)."""
    if r == 0:
        if 0 <= cx < W and 0 <= cy < H:
            img.putpixel((cx, cy), 1)
        return
    for dx in range(-r, r + 1):
        dy_max = r - abs(dx)
        for dy in range(-dy_max, dy_max + 1):
            x, y = cx + dx, cy + dy
            if 0 <= x < W and 0 <= y < H:
                img.putpixel((x, y), 1)


def diamond_halo(img, cx, cy, r):
    """Outline-only diamond at radius r+1 (the spawn flash)."""
    rr = r + 1
    for dx in range(-rr, rr + 1):
        dy = rr - abs(dx)
        for sign in (-1, 1):
            x, y = cx + dx, cy + sign * dy
            if 0 <= x < W and 0 <= y < H:
                img.putpixel((x, y), 1)


def node_positions(n):
    """Evenly-spaced node centers across the right region, vertically centered."""
    if n <= 0:
        return []
    if n == 1:
        return [(NODE_X0 + NODE_W // 2, H // 2)]
    spacing = NODE_W / n
    return [(int(NODE_X0 + spacing * (i + 0.5)), H // 2) for i in range(n)]


def init_rain(seed=7, drops=6):
    random.seed(seed)
    return [
        [random.randint(NODE_X0, NODE_X1),
         random.randint(-H, 0),
         random.randint(2, 4)]
        for _ in range(drops)
    ]


def step_rain(rain, img):
    """Advance each drop by one row; respawn when it falls off the bottom."""
    for drop in rain:
        drop[1] += 1
        if drop[1] - drop[2] > H:
            drop[0] = random.randint(NODE_X0, NODE_X1)
            drop[1] = -random.randint(0, 3)
            drop[2] = random.randint(2, 4)
    for x, y, length in rain:
        for k in range(length):
            yy = y - k
            if 0 <= yy < H and 0 <= x < W:
                if k == 0 or (k % 2 == 0):  # head bright + sparse tail
                    img.putpixel((x, yy), 1)


def gaussian_wave(img, center_x):
    """3-pixel-wide vertical wave column. Center column is full-height,
    flanking columns clip the top/bottom 2 rows."""
    for dx in (-1, 0, 1):
        x = center_x + dx
        if not (0 <= x < W):
            continue
        if dx == 0:
            for y in range(H):
                img.putpixel((x, y), 1)
        else:
            for y in range(2, H - 2):
                img.putpixel((x, y), 1)


def invert(img):
    out = blank()
    for y in range(H):
        for x in range(W):
            if not img.getpixel((x, y)):
                out.putpixel((x, y), 1)
    return out


def build_frames():
    frames = []
    rain = init_rain()

    # Phase 1 — text wipe-in (8 frames, no nodes yet).
    for i in range(8):
        f = blank()
        step_rain(rain, f)
        wipe_x = int((i + 1) / 8 * (TEXT_W + 1))
        stamp(f, "TiDB", 0, TEXT_Y, mask_x_max=wipe_x)
        frames.append(f)

    # Phase 2 — scale-out, with spawn + settle frames per beat.
    radii = {1: 3, 2: 2, 4: 2, 8: 1, 16: 0}
    for n in (1, 2, 4, 8, 16):
        centers = node_positions(n)
        r = radii[n]

        # Spawn frame: filled diamonds + halo ring
        f = blank()
        step_rain(rain, f)
        stamp(f, "TiDB", 0, TEXT_Y)
        for cx, cy in centers:
            filled_diamond(f, cx, cy, r)
            diamond_halo(f, cx, cy, r)
        frames.append(f)

        # Settle frame: just the diamonds
        f = blank()
        step_rain(rain, f)
        stamp(f, "TiDB", 0, TEXT_Y)
        for cx, cy in centers:
            filled_diamond(f, cx, cy, r)
        frames.append(f)

    # Phase 3 — wave packet sweeps L→R across 16-node steady state.
    final_centers = node_positions(16)
    for sweep_x in range(NODE_X0, NODE_X1 + 1, 2):
        f = blank()
        step_rain(rain, f)
        stamp(f, "TiDB", 0, TEXT_Y)
        for cx, cy in final_centers:
            f.putpixel((cx, cy), 1)
        gaussian_wave(f, sweep_x)
        frames.append(f)

    # Phase 4 — sting: invert the last frame for one beat.
    frames.append(invert(frames[-1]))

    # Hold steady briefly before loop wraps.
    for _ in range(2):
        f = blank()
        step_rain(rain, f)
        stamp(f, "TiDB", 0, TEXT_Y)
        for cx, cy in final_centers:
            f.putpixel((cx, cy), 1)
        frames.append(f)

    return frames


def main():
    frames = build_frames()
    out = Path(__file__).resolve().parent / "tidb_scale.gif"
    frames[0].save(
        out,
        save_all=True,
        append_images=frames[1:],
        duration=125,    # for the GIF preview only; the cup uses its
                         # own speed byte (pass -s 255 for fluid playback)
        loop=0,
        optimize=False,
        disposal=2,
    )
    print(f"✓ wrote {out} ({len(frames)} frames)")


if __name__ == "__main__":
    main()
