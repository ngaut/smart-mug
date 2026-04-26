#!/usr/bin/env python3
"""TiDB Next-Gen animation for the SGUAI-C3 cup (48×12) — "Breath".

The single property that distinguishes TiDB Next-Gen from generic
"distributed database" imagery is *ephemeral compute on a permanent
shared-storage core*. Compute spins up on demand and back down to
nothing; storage is the one thing that doesn't move.

Visual encoding of exactly that property:

  - A horizontal storage line through the middle of the display
    (row 6, full width). It is permanent — every frame, every loop,
    forever. It is the reference frame for everything else.
  - Compute dots live in the rows above and below the line. Their
    population breathes — expanding outward when "demand arrives,"
    contracting back into the line when "demand passes." Each dot is
    a compute instance; total count breathes between ~0 and ~50.
  - The breath is eased (sin² shape), not linear: slow at the
    extremes, fast through the middle, like real respiration.
  - Top half and bottom half mirror each other, so the line is
    visibly the axis of symmetry — reinforcing "storage is the
    permanent center; compute is what comes and goes."

The display LITERALLY breathes, in sync with someone holding the cup.

No labels, no counter, no text. The metaphor is the whole point and
labels would only dilute it. 60 frames at speed=200 ≈ 9.6 s per
breath cycle — close to a slow human breath rate.
"""

from pathlib import Path
import math
import random

from PIL import Image

W, H = 48, 12
STORAGE_ROW = 6


def blank():
    return Image.new('1', (W, H), 0)


def draw_storage(img):
    """The permanent storage line. Drawn identically every frame."""
    for x in range(W):
        img.putpixel((x, STORAGE_ROW), 1)


def compute_population_for(t):
    """Return the desired *number* of compute dots at normalized time
    t ∈ [0, 1] within one breath cycle. sin² gives the eased breath
    curve: slow near extremes, fast through midpoints."""
    # Two breaths per loop = sin(t * 2π) for one full inhale-exhale.
    # We use sin² so we get a positive curve peaking once per breath.
    # Then scale to a peak population.
    peak = 50  # max compute instances at full inhale
    return int(peak * (math.sin(math.pi * t) ** 2))


def populate_compute(img, count, rng):
    """Sprinkle `count` compute dots in the rows above and below the
    storage line. Symmetric around the line: each dot draws a mirrored
    pair (above + below) so the visual axis-of-symmetry is unmissable.

    Density is highest near the storage line and falls off with
    distance — compute that's "close to" storage is more common, far
    compute is rare. This reads as the cluster radiating outward from
    the data substrate."""
    drawn_above = 0
    drawn_below = 0
    target_each = count // 2

    # Probability a row is selected falls off with distance from the line.
    # Rows just above/below: high probability. Far rows: lower.
    # Distances 1..5 (above) and 1..5 (below) — H=12, line at row 6.
    row_weights_above = [(STORAGE_ROW - d, 6 - d) for d in range(1, STORAGE_ROW + 1)]
    row_weights_below = [(STORAGE_ROW + d, 6 - d) for d in range(1, H - STORAGE_ROW)]

    def sample_row(rows):
        # Weighted random pick
        total = sum(w for _, w in rows)
        r = rng.uniform(0, total)
        acc = 0
        for row, w in rows:
            acc += w
            if r <= acc:
                return row
        return rows[-1][0]

    placed_above = set()
    placed_below = set()
    attempts = 0
    while (drawn_above < target_each or drawn_below < target_each) and attempts < count * 3:
        attempts += 1
        if drawn_above < target_each:
            y = sample_row(row_weights_above)
            x = rng.randrange(W)
            if (x, y) not in placed_above:
                placed_above.add((x, y))
                img.putpixel((x, y), 1)
                drawn_above += 1
        if drawn_below < target_each:
            y = sample_row(row_weights_below)
            x = rng.randrange(W)
            if (x, y) not in placed_below:
                placed_below.add((x, y))
                img.putpixel((x, y), 1)
                drawn_below += 1


def build_frames():
    """One full breath cycle: inhale (population grows) → exhale
    (population shrinks) → tiny pause at zero before next cycle."""
    frames = []
    N_FRAMES = 60   # one cycle

    # Use a fixed seed per cycle for visual coherence — same population
    # count produces visually similar (not identical) layouts, so the
    # breathing reads as the SAME cluster expanding/contracting rather
    # than randomly different clusters each frame.
    base_seed = 12345

    for i in range(N_FRAMES):
        t = i / N_FRAMES
        count = compute_population_for(t)

        # Per-frame seed: use base_seed but vary slightly so each frame's
        # exact dot positions are different (which makes the cluster
        # *shimmer* slightly even at constant population, like a living
        # thing). Mostly the count change is what drives perception.
        rng = random.Random(base_seed + i)

        f = blank()
        draw_storage(f)
        populate_compute(f, count, rng)
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
