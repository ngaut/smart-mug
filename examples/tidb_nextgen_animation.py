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
    Position and velocity are floats; we round to pixels at render."""

    def __init__(self, x, y, vx, vy):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.target = None     # (tx, ty), set during converge phase
        self.locked = False    # True once close enough to snap to target

    def step_flock(self, neighbors, drift_vx=-0.7):
        """Boid behaviors: separation (avoid crowding), alignment (match
        neighbor velocity), cohesion (steer toward neighbor center).
        Plus a constant leftward drift so the flock moves across the cup."""
        sep_x = sep_y = 0.0
        ali_x = ali_y = 0.0
        coh_x = coh_y = 0.0
        n_close = 0
        n_align = 0
        for o in neighbors:
            if o is self:
                continue
            dx = o.x - self.x
            dy = o.y - self.y
            d2 = dx * dx + dy * dy
            if d2 < 4:                       # too close → separate
                sep_x -= dx
                sep_y -= dy
                n_close += 1
            if d2 < 36:                      # nearby → align + cohere
                ali_x += o.vx
                ali_y += o.vy
                coh_x += o.x
                coh_y += o.y
                n_align += 1
        # Apply weights
        ax = ay = 0.0
        if n_close > 0:
            ax += sep_x * 0.3
            ay += sep_y * 0.3
        if n_align > 0:
            ali_x /= n_align; ali_y /= n_align
            coh_x = coh_x / n_align - self.x
            coh_y = coh_y / n_align - self.y
            ax += ali_x * 0.10 + coh_x * 0.04
            ay += ali_y * 0.10 + coh_y * 0.04
        # Drift leftward
        ax += (drift_vx - self.vx) * 0.06
        # Damping + integrate
        self.vx = self.vx * 0.92 + ax
        self.vy = self.vy * 0.92 + ay
        # Cap speed for visual coherence
        sp = math.hypot(self.vx, self.vy)
        if sp > 1.4:
            self.vx *= 1.4 / sp
            self.vy *= 1.4 / sp
        self.x += self.vx
        self.y += self.vy
        # Wrap on bottom/top so birds stay on screen during stream-in
        if self.y < -0.5: self.y = -0.5; self.vy = abs(self.vy)
        if self.y > H - 0.5: self.y = H - 0.5; self.vy = -abs(self.vy)

    def step_converge(self, k=0.10, snap_dist=0.7):
        """Accelerate toward target. When close enough, lock to target
        exactly so the formed letters are pixel-perfect."""
        if self.target is None:
            return
        if self.locked:
            self.x, self.y = self.target
            return
        tx, ty = self.target
        ax = (tx - self.x) * k
        ay = (ty - self.y) * k
        self.vx = self.vx * 0.85 + ax
        self.vy = self.vy * 0.85 + ay
        self.x += self.vx
        self.y += self.vy
        if math.hypot(tx - self.x, ty - self.y) <= snap_dist:
            self.x, self.y = tx, ty
            self.vx = self.vy = 0.0
            self.locked = True

    def step_disperse(self):
        """Free-fly with momentum, slowly losing speed."""
        self.vx *= 0.985
        self.vy *= 0.985
        self.x += self.vx
        self.y += self.vy


def init_flock(n_birds, rng):
    """Spawn `n_birds` just off the right edge in a vertically
    distributed band, all moving leftward with a shared base velocity
    plus per-bird perturbation. The shared component matters — that's
    what makes them look like a flock and not isolated drifters."""
    base_vx = -1.0
    base_vy = rng.uniform(-0.2, 0.2)
    birds = []
    for _ in range(n_birds):
        x = W + rng.uniform(0, 14)
        y = rng.uniform(0.5, H - 1.5)
        vx = base_vx + rng.uniform(-0.15, 0.15)
        vy = base_vy + rng.uniform(-0.15, 0.15)
        birds.append(Bird(x, y, vx, vy))
    return birds


def render(birds, bright=None):
    """Render birds. Optionally pass `bright` (a set of indices) to
    render those birds doubly bright by also lighting an adjacent pixel.
    Useful for the snap-to-formation moment and the disperse trigger."""
    f = blank()
    bright = bright or set()
    for i, b in enumerate(birds):
        x, y = int(round(b.x)), int(round(b.y))
        if 0 <= x < W and 0 <= y < H:
            f.putpixel((x, y), 1)
            if i in bright:
                # Halo: light one adjacent pixel for visual emphasis
                if x + 1 < W: f.putpixel((x + 1, y), 1)
    return f


def assign_targets_greedy(birds, targets, rng):
    """Greedy nearest-target assignment. For each bird (in random order
    so the result isn't biased toward any traversal axis), find the
    closest unassigned target and claim it. This produces an organic
    convergence shape — birds take the targets they're closest to,
    rather than all sweeping in lockstep along one axis."""
    free = list(targets)
    order = list(range(len(birds)))
    rng.shuffle(order)
    for i in order:
        b = birds[i]
        if not free:
            break
        # Pick the nearest free target
        best_idx = 0
        best_d2 = float('inf')
        for j, (tx, ty) in enumerate(free):
            d2 = (tx - b.x) ** 2 + (ty - b.y) ** 2
            if d2 < best_d2:
                best_d2 = d2
                best_idx = j
        b.target = free.pop(best_idx)


def build_frames():
    rng = random.Random(11)
    targets = tidb_target_pixels()
    n_birds = len(targets)
    birds = init_flock(n_birds, rng)
    frames = []

    # ---------- Stream-in: ~16 frames ----------
    # Birds enter from the right and develop flocking behavior. They
    # interact with each other — separation, alignment, cohesion —
    # so the cluster reads as a flock, not as isolated drifters.
    for _ in range(16):
        for b in birds:
            b.step_flock(birds)
        frames.append(render(birds))

    # ---------- Converge: ~22 frames ----------
    # Greedy nearest-target assignment so the convergence shape is
    # organic. Continue with light flocking influence early so the
    # cluster moves coherently before snapping into letters.
    assign_targets_greedy(birds, targets, rng)
    for step in range(22):
        # Early convergence: blend flocking + target attraction so
        # the flock pulls itself into the letters while still
        # behaving like a group. Late convergence: pure target lock.
        flock_weight = max(0.0, 0.5 - step * 0.04)
        for b in birds:
            if not b.locked and flock_weight > 0:
                # Pre-step a tiny flocking nudge before the convergence pull
                pre_vx, pre_vy = b.vx, b.vy
                b.step_flock(birds, drift_vx=-0.2)
                # Re-blend: most of the new motion is still target-driven
                b.vx = b.vx * flock_weight + pre_vx * (1 - flock_weight)
                b.vy = b.vy * flock_weight + pre_vy * (1 - flock_weight)
            b.step_converge(k=0.12 + step * 0.005, snap_dist=0.6)
        # Mark snap-frames with a halo on birds that JUST locked this step
        # (handled by tracking before/after lock state)
        frames.append(render(birds))

    # ---------- Snap: 1 punctuation frame ----------
    # All birds locked. One bright frame where every bird gets a tiny
    # halo — visually punctuates the moment of formation.
    snap_idx = set(range(len(birds)))
    frames.append(render(birds, bright=snap_idx))

    # ---------- Hold: 10 frames with subtle pulse ----------
    # Hold the formed "TIDB" with a gentle 2-frame "breath" cycle —
    # every 4 frames, a few birds fade by becoming invisible (a 1-frame
    # blink at staggered positions). Reads as the formation breathing,
    # not as static text.
    for hold_idx in range(10):
        f = blank()
        for i, b in enumerate(birds):
            tx, ty = b.target
            # Stagger occasional 1-frame blinks: ~1/20 chance per bird per frame
            blink = (i * 13 + hold_idx * 7) % 23 < 2
            if blink:
                continue
            f.putpixel(tx, ty) if False else f.putpixel((tx, ty), 1)
        if hold_idx & 1:
            f.putpixel((0, 0), 1)
        frames.append(f)

    # ---------- Disperse trigger: 1 wave frame ----------
    # Before the disperse, a single frame where ONE bird (the
    # "trigger") has a halo — as if startled. The eye reads this as
    # cause-and-effect.
    trigger = len(birds) // 2
    frames.append(render(birds, bright={trigger}))

    # ---------- Disperse: ~14 frames ----------
    # Give each bird outward velocity from screen center, with the
    # trigger bird's neighbors getting slightly more impulse (ripple
    # outward from the trigger).
    cx, cy = W / 2, H / 2
    trig = birds[trigger]
    for b in birds:
        b.x, b.y = b.target
        b.locked = False
        dx = b.x - cx
        dy = b.y - cy
        mag = max(0.5, math.hypot(dx, dy))
        # Distance from trigger affects impulse magnitude
        td = math.hypot(b.x - trig.x, b.y - trig.y)
        impulse = rng.uniform(1.0, 1.5) * (1.0 + max(0, 1.0 - td / 12))
        b.vx = (dx / mag) * impulse + rng.uniform(-0.3, 0.3)
        b.vy = (dy / mag) * impulse + rng.uniform(-0.3, 0.3)
    for _ in range(14):
        for b in birds:
            b.step_disperse()
        frames.append(render(birds))

    # ---------- Empty pause: 3 frames ----------
    # Brief silence before the next flock streams in — a beat of
    # negative space that frames the punchline of the next loop.
    for i in range(3):
        f = blank()
        if i & 1:
            f.putpixel((0, 0), 1)
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
