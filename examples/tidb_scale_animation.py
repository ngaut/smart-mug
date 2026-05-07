#!/usr/bin/env python3
"""TiDB scalability animation for the SGUAI-C3 cup (48×12 monochrome).

Produces an animated GIF that tells a "horizontal scale-out" story.
Each beat is paced for human comprehension — the viewer can actually
count 1 → 2 → 4 → 8 → 16, see the wave sweep, and register the sting.

    Phase 1 — Boot. "TiDB" wipes in left-to-right like a progress bar,
              with sparse Matrix-rain dots falling in the right region.
              ~1.6 s.
    Phase 2 — Scale out. Nodes 1 → 2 → 4 → 8 → 16, drawn as diamonds
              that shrink as count grows. Each beat is one "spawn"
              frame (filled diamond + halo flash) plus four "settle"
              frames (~800 ms total per beat — long enough to count).
              ~4 s total.
    Phase 3 — Wave. A 3-px-wide bright wave packet sweeps L→R across
              the 16-node steady state, reading as data flowing
              through the cluster. ~2 s.
    Phase 4 — Sting. The entire display inverts for two beats, then
              returns to steady state for three beats before looping.
              ~800 ms.

Tuning notes
------------
The pacing assumes speed=200 (APK formula `10·(260−s)` → 600 ms/frame).
At max speed=255 (50 ms/frame) the loop runs 12× faster — fine for
"motion vibe" but the scale-out beats become too fleeting to count.

Usage
-----
    # Generate the GIF (overwrites tidb_scale.gif next to this script):
    uv run --with pillow examples/tidb_scale_animation.py

    # Send to cup at the human-readable pace (~9 s loop):
    uv run python/smart_mug.py animate examples/tidb_scale.gif -s 200

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
    """Pace each beat for human reading at speed=200 (~160 ms/frame).
    Hold frames vary the rain so the GIF encoder doesn't dedupe them
    (each "settle" frame steps the rain, producing a unique payload)."""
    frames = []
    rain = init_rain()

    # Phase 1 — text wipe-in. 8 wipe steps + 2 hold frames so the
    # finished "TiDB" lingers a beat before the cluster starts.
    for i in range(8):
        f = blank()
        step_rain(rain, f)
        wipe_x = int((i + 1) / 8 * (TEXT_W + 1))
        stamp(f, "TiDB", 0, TEXT_Y, mask_x_max=wipe_x)
        frames.append(f)
    for _ in range(2):
        f = blank()
        step_rain(rain, f)
        stamp(f, "TiDB", 0, TEXT_Y)
        frames.append(f)

    # Phase 2 — scale-out. 1 spawn + 4 settle frames per beat ≈ 800 ms
    # at speed=200 — long enough for the viewer to count the nodes
    # before the next doubling.
    radii = {1: 3, 2: 2, 4: 2, 8: 1, 16: 0}
    SETTLE = 4
    for n in (1, 2, 4, 8, 16):
        centers = node_positions(n)
        r = radii[n]

        # Spawn frame: filled diamonds + halo ring (one beat of "flash")
        f = blank()
        step_rain(rain, f)
        stamp(f, "TiDB", 0, TEXT_Y)
        for cx, cy in centers:
            filled_diamond(f, cx, cy, r)
            diamond_halo(f, cx, cy, r)
        frames.append(f)

        # Settle frames: just the diamonds, rain continues moving.
        for _ in range(SETTLE):
            f = blank()
            step_rain(rain, f)
            stamp(f, "TiDB", 0, TEXT_Y)
            for cx, cy in centers:
                filled_diamond(f, cx, cy, r)
            frames.append(f)

    # Phase 3 — wave packet sweeps L→R across the 16-node steady state.
    # Step=2 means ~13 frames at 160 ms ≈ 2 s of fluid motion.
    final_centers = node_positions(16)
    for sweep_x in range(NODE_X0, NODE_X1 + 1, 2):
        f = blank()
        step_rain(rain, f)
        stamp(f, "TiDB", 0, TEXT_Y)
        for cx, cy in final_centers:
            f.putpixel((cx, cy), 1)
        gaussian_wave(f, sweep_x)
        frames.append(f)

    # Phase 4 — sting. Invert for two beats so the flip is unmistakable.
    last_steady = blank()
    step_rain(rain, last_steady)
    stamp(last_steady, "TiDB", 0, TEXT_Y)
    for cx, cy in final_centers:
        last_steady.putpixel((cx, cy), 1)
    sting = invert(last_steady)
    frames.append(sting)
    frames.append(sting)

    # Hold steady for three beats so the loop boundary feels deliberate.
    for _ in range(3):
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
        duration=160,    # GIF-preview pace; the cup uses its own speed
                         # byte (recommend -s 200 for human-readable pacing)
        loop=0,
        optimize=False,
        disposal=2,
    )
    print(f"✓ wrote {out} ({len(frames)} frames)")


if __name__ == "__main__":
    main()
