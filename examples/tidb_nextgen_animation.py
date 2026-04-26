#!/usr/bin/env python3
"""TiDB Next-Gen animation for the SGUAI-C3 cup (48×12) — "Rising".

Six previous iterations of this example all tried to render an
architecture diagram on a coffee-mug LED matrix and got pushed back
on for being busy, abstract, thin, or hard to read. This version
abandons the architecture-diagram framing entirely.

A coffee mug at hand-holding distance, glanced at while sipping, is
never going to be a distributed-systems explainer. It IS great at
being a small piece of beauty that someone notices and likes. So:

A horizon line near the bottom — the architectural floor. From below,
small bright dots ("data" / "sparks" / call them what you want) rise
up, drifting horizontally as they ascend, then fade at the top. No
wordmark — the physical cup is already TiDB-branded; the LED
animation is the ambient piece.

What it implies, without stating:
  - Scaling, growth, infinity (everything keeps rising)
  - Distribution (many independent particles)
  - Architecture (the horizon as foundation, particles as workload)
  - Aliveness (constant motion, never finished)

What it stops trying to do:
  - Teach you the architecture's tiers
  - Render labels for layers
  - Explain compute/storage separation
  - Be a slide-deck figure on a 48×12 LED matrix

It's just nice to look at.

~80 frames at speed=200, ~13 s loop.
"""

from pathlib import Path
import random

from PIL import Image

W, H = 48, 12

HORIZON_ROW = 10  # the architectural "floor", near the bottom edge

# Particle physics
N_PARTICLES = 8       # how many sparks alive at any moment
PARTICLE_RISE_SPEED = 0.35   # rows per frame (fractional)
PARTICLE_DRIFT = 0.15        # max horizontal drift per frame


def draw_horizon(img, frame_idx):
    """Faint horizon line. Sparse dotted pattern that subtly drifts so
    it feels more like a breathing surface than a hard line."""
    pattern_offset = (frame_idx // 4) % 3
    for x in range(W):
        if (x + pattern_offset) % 3 == 0:
            img.putpixel((x, HORIZON_ROW), 1)


class Particle:
    """A single rising spark. Floats up from the horizon, drifts a bit
    horizontally, fades at the top by being culled and respawned."""

    def __init__(self, rng):
        self.respawn(rng)

    def respawn(self, rng):
        self.x = rng.uniform(2, W - 3)
        self.y = HORIZON_ROW - 0.5     # just above the horizon
        # A bit of horizontal drift so the rises aren't dead-vertical
        self.vx = rng.uniform(-PARTICLE_DRIFT, PARTICLE_DRIFT)
        # Slight variation in rise speed so particles don't move in lockstep
        self.vy = -rng.uniform(0.7, 1.3) * PARTICLE_RISE_SPEED
        self.age = 0
        # Initial offset along trajectory so a fresh batch isn't a row
        self.y += rng.uniform(0, 6) * self.vy
        self.x += rng.uniform(0, 6) * self.vx

    def step(self, rng):
        self.x += self.vx
        self.y += self.vy
        self.age += 1
        # Cull when above the top, off the sides, or too old
        if self.y < -1 or self.x < -1 or self.x > W + 1:
            self.respawn(rng)


def build_frames():
    rng = random.Random(42)
    particles = [Particle(rng) for _ in range(N_PARTICLES)]
    frames = []

    # Run the simulation; record one frame per step. ~80 frames lets
    # particles cycle through several lifetimes for a richer-looking
    # but still loopable animation.
    N_FRAMES = 80

    for frame_idx in range(N_FRAMES):
        f = Image.new('1', (W, H), 0)

        # Horizon: subtle dotted line that drifts
        draw_horizon(f, frame_idx)

        # Particles
        for p in particles:
            px, py = int(round(p.x)), int(round(p.y))
            # Main particle pixel
            if 0 <= px < W and 0 <= py < H:
                f.putpixel((px, py), 1)
            # As a particle rises higher, draw a faint trailing pixel
            # below it (motion suggestion). Skip for very fresh particles.
            if p.age >= 3:
                ty = py + 1
                if 0 <= px < W and 0 <= ty < HORIZON_ROW:
                    # Sparse trail: only every other frame to thin it out
                    if frame_idx & 1:
                        f.putpixel((px, ty), 1)

        # Tiny pixel-toggle for frame uniqueness so PIL doesn't dedupe
        # any visually-identical frames during GIF encode
        if frame_idx & 1:
            f.putpixel((W - 1, 0), 1)

        frames.append(f)
        for p in particles:
            p.step(rng)

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
