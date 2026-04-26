#!/usr/bin/env python3
"""TiDB Next-Gen animation for the SGUAI-C3 cup (48×12) — "Murmuration".

A flock of pixel-birds streams across the cup. They look like chaos.
Then — for one beat — they assemble into the letters TIDB, hold,
disperse back into chaos, and a fresh flock streams in.

The metaphor: many independent agents resolving into a coherent
brand identity, then returning to motion. It's a flocking simulation
with a punchline. Each bird is a pixel; the whole flock IS the brand.

Why this works on a coffee mug:
  - Visually arresting (flocks captivate at any scale)
  - Has an actual surprise (the moment of assembly)
  - Reads as "many → one → many" which IS the TiDB shape (lots of
    distributed pieces forming a single coherent product)
  - Loops cleanly
  - Hand-rolled physics, not a generic effect

Animation phases (~13 s loop at speed=200):
    Stream-in (15 frames):  Birds enter from the right edge in a
                            ragged cloud, drifting leftward.
    Converge   (20 frames):  Each bird picks a target pixel in the
                            TIDB rendering and accelerates toward it.
    Hold       (8 frames):   "TIDB" formed, steady (with subtle
                            shimmer from per-frame jitter).
    Disperse   (15 frames):  Birds scatter outward with random
                            velocities, fly off the edges.
    Return     (8 frames):   Empty display briefly, then loop.
"""

from pathlib import Path
import math
import random

from PIL import Image

W, H = 48, 12

# 7-row pixel font for the brand target
GLYPHS_7 = {
    'T': ["█████", "··█··", "··█··", "··█··", "··█··", "··█··", "··█··"],
    'I': ["█",     "·",     "█",     "█",     "█",     "█",     "█"],
    'D': ["████·", "█···█", "█···█", "█···█", "█···█", "█···█", "████·"],
    'B': ["████·", "█···█", "████·", "█···█", "█···█", "█···█", "████·"],
}


def tidb_target_pixels():
    """Return a list of (x, y) pixel positions that, when all lit,
    spell TIDB in 7-row font, centered horizontally and vertically."""
    text = "TIDB"
    # Compute total width
    widths = [max(len(r) for r in GLYPHS_7[c]) for c in text]
    total_w = sum(widths) + len(widths) - 1  # 1-px gaps
    x0 = (W - total_w) // 2
    y0 = (H - 7) // 2
    pixels = []
    x = x0
    for ch in text:
        g = GLYPHS_7[ch]
        gw = max(len(r) for r in g)
        for ry, row in enumerate(g):
            for rx in range(gw):
                if rx < len(row) and row[rx] == '█':
                    pixels.append((x + rx, y0 + ry))
        x += gw + 1
    return pixels


def blank():
    return Image.new('1', (W, H), 0)


class Bird:
    """One pixel-bird with position, velocity, and an assigned target.
    Position and velocity are floats so motion is smooth; we round to
    pixels only when rendering."""

    def __init__(self, x, y, vx, vy):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.target = None    # (tx, ty), set during converge phase

    def step_freeflight(self, drift_vx=-0.6, jitter=0.15):
        """Drift leftward with a touch of vertical jitter."""
        self.vx = self.vx * 0.7 + drift_vx * 0.3
        self.vy = self.vy * 0.7 + random.uniform(-jitter, jitter)
        self.x += self.vx
        self.y += self.vy

    def step_converge(self, k=0.18):
        """Accelerate toward target with damping."""
        if self.target is None:
            return
        tx, ty = self.target
        ax = (tx - self.x) * k
        ay = (ty - self.y) * k
        self.vx = self.vx * 0.75 + ax
        self.vy = self.vy * 0.75 + ay
        self.x += self.vx
        self.y += self.vy

    def step_disperse(self):
        """Free-fly with momentum (set at start of disperse)."""
        self.vx *= 0.97
        self.vy *= 0.97
        self.x += self.vx
        self.y += self.vy


def init_flock(n_birds):
    """Spawn `n_birds` just off the right edge of the display in a
    loose vertical band, drifting leftward."""
    rng = random.Random(7)
    birds = []
    for _ in range(n_birds):
        x = W + rng.uniform(0, 12)        # right of the screen
        y = rng.uniform(0, H - 1)
        vx = -rng.uniform(0.5, 1.0)
        vy = rng.uniform(-0.3, 0.3)
        birds.append(Bird(x, y, vx, vy))
    return birds


def render(birds):
    f = blank()
    for b in birds:
        x, y = int(round(b.x)), int(round(b.y))
        if 0 <= x < W and 0 <= y < H:
            f.putpixel((x, y), 1)
    return f


def build_frames():
    targets = tidb_target_pixels()
    n_birds = len(targets)
    birds = init_flock(n_birds)
    rng = random.Random(11)
    frames = []

    # ---------- Stream-in: 15 frames ----------
    # Birds drift leftward into the display from the right.
    for _ in range(15):
        for b in birds:
            b.step_freeflight()
        frames.append(render(birds))

    # ---------- Converge: 20 frames ----------
    # Assign each bird the nearest still-unassigned target. This makes
    # short-distance moves likely (so the flock SETTLES into the letters
    # rather than crossing all over each other).
    free_targets = list(targets)
    # Sort birds and targets by x-position so leftmost birds get
    # leftmost targets — they tend to converge cleanly.
    birds_by_x = sorted(birds, key=lambda b: b.x)
    targets_by_x = sorted(free_targets, key=lambda t: t[0])
    for b, t in zip(birds_by_x, targets_by_x):
        b.target = t

    for _ in range(20):
        for b in birds:
            b.step_converge()
        frames.append(render(birds))

    # ---------- Hold: 8 frames ----------
    # Snap each bird exactly to its target pixel for a clean "TIDB"
    # render, with subtle per-frame shimmer (a few birds do a tiny
    # one-pixel jiggle).
    for hold_idx in range(8):
        f = blank()
        for i, b in enumerate(birds):
            tx, ty = b.target
            # Shimmer: every 5 frames, a few birds wiggle by 1 px
            if hold_idx % 3 == 0 and (i + hold_idx) % 7 == 0:
                tx += rng.choice((-1, 0, 1))
                ty += rng.choice((-1, 0, 1))
            tx = max(0, min(W - 1, tx))
            ty = max(0, min(H - 1, ty))
            f.putpixel((tx, ty), 1)
        # Force frame uniqueness for PIL
        if hold_idx & 1:
            f.putpixel((0, 0), 1)
        frames.append(f)

    # ---------- Disperse: 15 frames ----------
    # Give each bird a random outward velocity from its current target.
    # Birds fly off the edges.
    for b in birds:
        b.x, b.y = b.target  # snap to formed position
        # Outward velocity: away from screen center, plus randomness
        cx, cy = W / 2, H / 2
        dx = b.x - cx
        dy = b.y - cy
        mag = max(0.5, math.hypot(dx, dy))
        b.vx = (dx / mag) * rng.uniform(0.8, 1.6) + rng.uniform(-0.3, 0.3)
        b.vy = (dy / mag) * rng.uniform(0.8, 1.6) + rng.uniform(-0.3, 0.3)
    for _ in range(15):
        for b in birds:
            b.step_disperse()
        frames.append(render(birds))

    # ---------- Return: 4 frames empty ----------
    # A few empty frames before the loop wraps so the eye registers
    # "the flock is gone" before the new flock arrives.
    for i in range(4):
        f = blank()
        if i & 1:
            f.putpixel((0, 0), 1)  # frame uniqueness
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
