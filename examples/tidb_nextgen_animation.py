#!/usr/bin/env python3
"""TiDB Next-Gen animation for the SGUAI-C3 cup (48×12) — "Survive & Scale".

A four-act story in pixels:

    Act I  — ORDER:   A small calm cluster, regular heartbeat. The
                      system is at rest. Establishing the baseline.
    Act II — CRISIS:  Particles stream in from both edges. Workload
                      overwhelms the cluster, which scatters and
                      nearly extinguishes. Dark night of the soul.
    Act III— SCALE:   From the surviving dots, the cluster cell-divides
                      outward in waves: 4 → 8 → 16 → 32. Each wave
                      absorbs more of the incoming load. Chaos
                      resolves into ordered structure.
    Act IV — TRIUMPH: The dots, having reached scaled-out form,
                      organize into the letters TIDB. Snap (halo) +
                      whole-display inverse flash (2 frames).
    Coda  — STEADY:   The longest section. With the letters formed,
                      a sequence of distinct operational beats:
                        • elastic scale (Tiny → Medium → Large with
                          halo apex → Medium → Tiny — TiDB's
                          signature elastic scaling demonstrated)
                        • data wave L→R (data flowing through)
                        • heartbeat × 2 (the system is alive)
                        • T-I-D-B announce + full-word halo (identity)
                        • sonar ping (concentric rings, broadcasting)
                        • data packets (concurrent multi-stream traffic)
                        • vertical scan (top-to-bottom system readout)
                        • scatter & reform (letters explode outward,
                          then magnetically pull back to formation)
                        • 3D rotation (letters spin around the vertical
                          axis: full → edge-on → mirrored → back)
                        • glitch & self-heal (random pixel corruption
                          inside the letters, recovery halo flash —
                          fault tolerance demonstrated)
                        • constellation (T-I-D-B as ring nodes with
                          diagonal edges zigzagging across — topology)
                        • hold + collapse back to the Act-I cluster
                      Each beat occupies a different visual axis or
                      motif — horizontal, radial, point-particles,
                      vertical, explosive — no mirror duplications.

The TIDB letters are EARNED by the narrative — they're the answer to
the question the animation poses (will the system survive the load?),
not a gratuitous logo. Three short, intense acts of struggle resolve
into the brand, then a long coda lets the system breathe and operate
before looping.

~85 frames at speed=200 ≈ 13.5 s per loop. Pre-TIDB ≈ 5.5 s, post ≈ 8 s.
"""

from pathlib import Path
import math
import random

from PIL import Image

W, H = 48, 12

# 7-row font for the TIDB target (medium / canonical size)
GLYPHS_7 = {
    'T': ["█████", "··█··", "··█··", "··█··", "··█··", "··█··", "··█··"],
    'I': ["█",     "·",     "█",     "█",     "█",     "█",     "█"],
    'D': ["████·", "█···█", "█···█", "█···█", "█···█", "█···█", "████·"],
    'B': ["████·", "█···█", "████·", "█···█", "█···█", "█···█", "████·"],
}

# Five font sizes to make the scale beat read clearly as continuous
# growth. Each size adds ~1-2 rows so the bell curve has visible
# intermediate steps instead of jump-cutting between extremes.

# 4-row tiny font (13 wide × 4 tall)
GLYPHS_TINY = {
    'T': ["███", "·█·", "·█·", "·█·"],
    'I': ["█",   "·",   "█",   "█"],
    'D': ["██·", "█·█", "█·█", "██·"],
    'B': ["██·", "███", "██·", "███"],
}

# 5-row small font (16 wide × 5 tall)
GLYPHS_SMALL = {
    'T': ["████", "·██·", "·██·", "·██·", "·██·"],
    'I': ["█",    "·",    "█",    "█",    "█"],
    'D': ["███·", "█··█", "█··█", "█··█", "███·"],
    'B': ["███·", "█··█", "███·", "█··█", "███·"],
}

# 8-row big font (21 wide × 8 tall)
GLYPHS_BIG = {
    'T': ["██████", "··██··", "··██··", "··██··",
          "··██··", "··██··", "··██··", "··██··"],
    'I': ["█", "·", "█", "█", "█", "█", "█", "█"],
    'D': ["█████·", "█····█", "█····█", "█····█",
          "█····█", "█····█", "█····█", "█████·"],
    'B': ["█████·", "█····█", "█····█", "█████·",
          "█····█", "█····█", "█····█", "█████·"],
}

# 10-row large font (25 wide × 10 tall) — apex of the bell curve
GLYPHS_LARGE = {
    'T': ["███████", "···█···", "···█···", "···█···", "···█···",
          "···█···", "···█···", "···█···", "···█···", "···█···"],
    'I': ["█", "·", "█", "█", "█", "█", "█", "█", "█", "█"],
    'D': ["██████·", "█·····█", "█·····█", "█·····█", "█·····█",
          "█·····█", "█·····█", "█·····█", "█·····█", "██████·"],
    'B': ["██████·", "█·····█", "█·····█", "██████·", "█·····█",
          "█·····█", "█·····█", "█·····█", "█·····█", "██████·"],
}


def render_tidb_at_size(glyphs):
    """Render TIDB centered on screen using the given glyph dict.
    Auto-centers vertically and horizontally. Used by the scale beat."""
    text = "TIDB"
    widths = [max(len(r) for r in glyphs[c]) for c in text]
    total_w = sum(widths) + len(widths) - 1
    height = max(len(glyphs[c]) for c in text)
    x0 = (W - total_w) // 2
    y0 = (H - height) // 2
    f = blank()
    x = x0
    for ch in text:
        g = glyphs[ch]
        gw = max(len(r) for r in g)
        for ry, row in enumerate(g):
            for rx in range(gw):
                if rx < len(row) and row[rx] == '█':
                    px, py = x + rx, y0 + ry
                    if 0 <= px < W and 0 <= py < H:
                        f.putpixel((px, py), 1)
        x += gw + 1
    return f


def tidb_target_pixels():
    text = "TIDB"
    widths = [max(len(r) for r in GLYPHS_7[c]) for c in text]
    total_w = sum(widths) + len(widths) - 1
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


class Particle:
    __slots__ = ('x', 'y', 'vx', 'vy', 'alive', 'target', 'role')

    def __init__(self, x, y, vx=0.0, vy=0.0, role='cluster'):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.alive = True
        self.target = None
        self.role = role     # 'cluster' or 'load'


def render(particles, halo=False, invert=False):
    f = blank()
    for p in particles:
        if not p.alive:
            continue
        x, y = int(round(p.x)), int(round(p.y))
        if 0 <= x < W and 0 <= y < H:
            f.putpixel((x, y), 1)
            if halo:
                if x + 1 < W: f.putpixel((x + 1, y), 1)
                if y + 1 < H: f.putpixel((x, y + 1), 1)
    if invert:
        out = blank()
        for y in range(H):
            for x in range(W):
                if not f.getpixel((x, y)):
                    out.putpixel((x, y), 1)
        return out
    return f


def heartbeat_offset(t, period=8):
    """sin² heartbeat offset for the resting cluster: small bob in y."""
    return math.sin(2 * math.pi * t / period) * 0.6


def build_frames():
    rng = random.Random(7)
    frames = []

    # ────────── ACT I — ORDER (6 frames) ──────────
    # A small tight cluster of 6 dots in the center, gently bobbing.
    # Tightened from 10 frames so the eye doesn't dwell on baseline.
    cluster_center = (W / 2, H / 2)
    cluster = []
    for i in range(6):
        ang = 2 * math.pi * i / 6
        cluster.append(Particle(
            cluster_center[0] + math.cos(ang) * 2.5,
            cluster_center[1] + math.sin(ang) * 1.5,
            role='cluster'
        ))

    for i in range(6):
        bob = heartbeat_offset(i)
        f = blank()
        for p in cluster:
            x, y = int(round(p.x)), int(round(p.y + bob))
            if 0 <= x < W and 0 <= y < H:
                f.putpixel((x, y), 1)
        # Frame uniqueness
        if i & 1:
            f.putpixel((0, 0), 1)
        frames.append(f)

    # ────────── ACT II — CRISIS (12 frames) ──────────
    # Particles stream in from both edges. Cluster dots get knocked
    # around. Near-extinction beat in the middle. Compressed from 16
    # so the crisis hits harder and resolves faster.
    load = []
    for stream in range(8):
        # Left-side incoming
        load.append(Particle(
            -rng.uniform(2, 12),
            rng.uniform(0, H - 1),
            vx=rng.uniform(0.8, 1.4),
            vy=rng.uniform(-0.2, 0.2),
            role='load'
        ))
        # Right-side incoming
        load.append(Particle(
            W + rng.uniform(2, 12),
            rng.uniform(0, H - 1),
            vx=-rng.uniform(0.8, 1.4),
            vy=rng.uniform(-0.2, 0.2),
            role='load'
        ))

    # During crisis, cluster dots get jostled toward the cup edges
    # (visible "stress"). 3 of them get extinguished entirely (deaths).
    for p in cluster:
        p.vx = rng.uniform(-0.4, 0.4)
        p.vy = rng.uniform(-0.4, 0.4)

    for i in range(12):
        # Update load particles
        for p in load:
            p.x += p.vx
            p.y += p.vy
        # Update cluster: jostle and dampen
        for p in cluster:
            p.vx = p.vx * 0.85 + rng.uniform(-0.15, 0.15)
            p.vy = p.vy * 0.85 + rng.uniform(-0.15, 0.15)
            p.x += p.vx
            p.y += p.vy

        # Mid-crisis: kill 3 cluster particles to show the system
        # nearly losing (frame 4, ~33% in — felt earlier than before).
        if i == 4:
            for p in cluster[:3]:
                p.alive = False

        # Turning point: bring them back fully revived (frame 8, ~66%
        # in) — the system survives, transitioning into Act III.
        if i == 8:
            for p in cluster:
                p.alive = True
                p.x = cluster_center[0] + rng.uniform(-3, 3)
                p.y = cluster_center[1] + rng.uniform(-2, 2)
                p.vx = p.vy = 0.0

        # Render: only show particles still on-screen
        f = blank()
        for p in load:
            x, y = int(round(p.x)), int(round(p.y))
            if 0 <= x < W and 0 <= y < H:
                f.putpixel((x, y), 1)
        for p in cluster:
            if not p.alive:
                continue
            x, y = int(round(p.x)), int(round(p.y))
            if 0 <= x < W and 0 <= y < H:
                f.putpixel((x, y), 1)
        if i & 1:
            f.putpixel((W - 1, 0), 1)
        frames.append(f)

    # ────────── ACT III — SCALE (~12 frames) ──────────
    # From 6 surviving cluster dots, cell-divide outward in waves:
    # 6 → 12 → 24 → 48 → 55. Each wave: existing dots split, the new
    # spawned dots fly outward a bit, then settle. Tightened from 4 to
    # 3 settle frames per wave.
    # Build a growing population that we'll then organize into TIDB.

    targets = tidb_target_pixels()
    n_target = len(targets)

    # Start with the 6 survivors. Each scale wave doubles the count
    # roughly until we hit n_target.
    scaled = list(cluster)
    while len(scaled) < n_target:
        # Each existing particle "spawns" a copy; the spawn appears
        # at a small offset and over the next few frames migrates to
        # an organic position. Limit growth to n_target.
        new_count = min(len(scaled) * 2, n_target) - len(scaled)
        new_particles = []
        for _ in range(new_count):
            parent = rng.choice(scaled)
            ang = rng.uniform(0, 2 * math.pi)
            r = rng.uniform(2, 6)
            child = Particle(
                parent.x + math.cos(ang) * r,
                parent.y + math.sin(ang) * r,
                vx=math.cos(ang) * 0.3,
                vy=math.sin(ang) * 0.3,
                role='cluster'
            )
            new_particles.append(child)
        scaled.extend(new_particles)

        # Animate: render 3 frames of the new spawn motion + load decay
        for k in range(3):
            f = blank()
            # Update load (still streaming in but fading)
            for p in load:
                p.x += p.vx
                p.y += p.vy * 0.95
                # Cull load particles that flew past the cluster
                if p.x < -2 or p.x > W + 2:
                    p.alive = False
                if p.alive:
                    x, y = int(round(p.x)), int(round(p.y))
                    if 0 <= x < W and 0 <= y < H:
                        f.putpixel((x, y), 1)
            # Update scaled cluster: damped spread
            for p in scaled:
                p.vx *= 0.85
                p.vy *= 0.85
                p.x += p.vx
                p.y += p.vy
                # Bounce off edges so the population stays on screen
                if p.x < 1: p.x = 1; p.vx = abs(p.vx)
                if p.x > W - 2: p.x = W - 2; p.vx = -abs(p.vx)
                if p.y < 1: p.y = 1; p.vy = abs(p.vy)
                if p.y > H - 2: p.y = H - 2; p.vy = -abs(p.vy)
                x, y = int(round(p.x)), int(round(p.y))
                if 0 <= x < W and 0 <= y < H:
                    f.putpixel((x, y), 1)
            if k & 1:
                f.putpixel((0, 0), 1)
            frames.append(f)

    # Trim scaled list to exactly n_target so we have one bird per
    # target pixel
    scaled = scaled[:n_target]

    # ────────── ACT IV — TRIUMPH (~14 frames) ──────────
    # Particles converge to TIDB target positions (greedy nearest).
    rng_assign = random.Random(13)
    free = list(targets)
    order = list(range(len(scaled)))
    rng_assign.shuffle(order)
    for i in order:
        p = scaled[i]
        if not free:
            break
        best = 0; best_d2 = float('inf')
        for j, (tx, ty) in enumerate(free):
            d2 = (tx - p.x) ** 2 + (ty - p.y) ** 2
            if d2 < best_d2:
                best_d2 = d2; best = j
        p.target = free.pop(best)

    # Convergence: 6 frames pulling toward targets (snappier — the
    # arrival, not the journey, is the moment).
    for step in range(6):
        f = blank()
        for p in scaled:
            if p.target is None:
                continue
            tx, ty = p.target
            # Stronger pull since we have fewer frames to converge in
            ax = (tx - p.x) * (0.35 + step * 0.08)
            ay = (ty - p.y) * (0.35 + step * 0.08)
            p.vx = p.vx * 0.7 + ax
            p.vy = p.vy * 0.7 + ay
            p.x += p.vx
            p.y += p.vy
            # Wider snap radius so the snappier easing doesn't cause
            # particles to overshoot and miss their target slot.
            if math.hypot(tx - p.x, ty - p.y) <= 1.2:
                p.x, p.y = tx, ty
                p.vx = p.vy = 0.0
            x, y = int(round(p.x)), int(round(p.y))
            if 0 <= x < W and 0 <= y < H:
                f.putpixel((x, y), 1)
        if step & 1:
            f.putpixel((0, 0), 1)
        frames.append(f)

    # SNAP: 1 frame with halo on all letters — the moment of triumph
    f = blank()
    for p in scaled:
        if p.target:
            tx, ty = p.target
            f.putpixel((tx, ty), 1)
            if tx + 1 < W:
                f.putpixel((tx + 1, ty), 1)
            if ty + 1 < H:
                f.putpixel((tx, ty + 1), 1)
    frames.append(f)

    # WHOLE-DISPLAY FLASH: 2 frames inverted (extended for emphasis —
    # the moment of triumph reads as a deliberate flash, not a glitch).
    last = frames[-1]
    inv = blank()
    for y in range(H):
        for x in range(W):
            if not last.getpixel((x, y)):
                inv.putpixel((x, y), 1)
    frames.append(inv)
    # Add a uniqueness toggle on the second copy so the encoder doesn't
    # dedupe and the cup gets two distinct frame slots. The corner is
    # already lit in the inverse, so flip it OFF to get a real diff.
    inv2 = inv.copy()
    inv2.putpixel((W - 1, 0), 0)
    frames.append(inv2)

    # ────────── CODA — OPERATIONAL ──────────
    # The system has formed. Now it gets to be alive on screen. Hold
    # → data flows L→R → settle → heartbeat → settle → data flows R→L
    # → settle. Each wave is bidirectional traffic across the cluster;
    # the heartbeat punctuates "still alive."

    letter_pixels = {p.target for p in scaled if p.target}
    xs = [x for (x, _) in letter_pixels]
    letters_x_min, letters_x_max = min(xs), max(xs)

    def render_tidb(toggle=None):
        f = blank()
        for (tx, ty) in letter_pixels:
            f.putpixel((tx, ty), 1)
        if toggle is not None:
            f.putpixel(toggle, 1)
        return f

    def invert_image(src):
        out = blank()
        for y in range(H):
            for x in range(W):
                if not src.getpixel((x, y)):
                    out.putpixel((x, y), 1)
        return out

    def render_sweep(sweep_x):
        f = render_tidb()
        for dx in (-1, 0, 1):
            x = sweep_x + dx
            if not (0 <= x < W):
                continue
            if dx == 0:
                for y in range(H):
                    f.putpixel((x, y), 1)
            else:
                for y in range(2, H - 2):
                    f.putpixel((x, y), 1)
        return f

    # Hold A: 3 frames — let the formed letters land before any motion.
    # Each frame uses a different corner toggle so the GIF encoder
    # doesn't dedupe consecutive "clean TIDB" frames.
    hold_a_toggles = [(0, 0), (W - 1, 0), (0, H - 1)]
    for toggle in hold_a_toggles:
        frames.append(render_tidb(toggle))

    # Scale out / scale in — TIDB grows Tiny → Medium → Large with
    # a halo punctuation at the apex, then shrinks back. Demonstrates
    # elastic scaling, TiDB's signature feature. The size sequence
    # forms a bell curve so growth and recall are symmetric.
    def add_halo(src):
        out = src.copy()
        for y in range(H):
            for x in range(W):
                if src.getpixel((x, y)):
                    if x + 1 < W:
                        out.putpixel((x + 1, y), 1)
                    if y + 1 < H:
                        out.putpixel((x, y + 1), 1)
        return out

    # Five-step bell curve, each size held long enough to register on
    # the eye. The progression Tiny→Small→Medium→Big→Large is gradual
    # (~1-2 rows per step) so growth reads as continuous expansion,
    # not a jump-cut between two extremes.
    scale_steps = [
        # Growing
        (GLYPHS_TINY,  False, (0, 0)),
        (GLYPHS_TINY,  False, (W - 1, 0)),         # hold tiny 2 frames
        (GLYPHS_SMALL, False, (0, H - 1)),
        (GLYPHS_SMALL, False, (W - 1, H - 1)),     # hold small 2 frames
        (GLYPHS_7,     False, (0, 0)),
        (GLYPHS_7,     False, (W - 1, 0)),         # hold medium 2 frames
        (GLYPHS_BIG,   False, (0, H - 1)),
        (GLYPHS_BIG,   False, (W - 1, H - 1)),     # hold big 2 frames
        (GLYPHS_LARGE, False, (0, 0)),
        (GLYPHS_LARGE, False, (W - 1, 0)),         # hold large 2 frames
        # Apex
        (GLYPHS_LARGE, True,  (0, H - 1)),
        (GLYPHS_LARGE, True,  (W - 1, H - 1)),     # halo apex 2 frames
        # Shrinking
        (GLYPHS_LARGE, False, (0, 0)),
        (GLYPHS_BIG,   False, (W - 1, 0)),
        (GLYPHS_BIG,   False, (0, H - 1)),         # hold big briefly
        (GLYPHS_7,     False, (W - 1, H - 1)),
        (GLYPHS_7,     False, (0, 0)),             # hold medium briefly
        (GLYPHS_SMALL, False, (W - 1, 0)),
        (GLYPHS_SMALL, False, (0, H - 1)),         # hold small briefly
        (GLYPHS_TINY,  False, (W - 1, H - 1)),
        (GLYPHS_TINY,  False, (0, 0)),             # land tiny 2 frames
    ]
    for glyphs, halo, toggle in scale_steps:
        f = render_tidb_at_size(glyphs)
        if halo:
            f = add_halo(f)
        # Toggle a corner to guarantee frame uniqueness for the GIF
        # encoder (consecutive same-size frames would otherwise dedupe).
        cur = f.getpixel(toggle)
        f.putpixel(toggle, 0 if cur else 1)
        frames.append(f)

    # Brief settle — let the cluster return to canonical size before
    # the data sweep starts.
    frames.append(render_tidb((W - 1, H - 1)))

    # Data sweep L→R through the cluster
    sweep_lo = letters_x_min - 4
    sweep_hi = letters_x_max + 4
    for sweep_x in range(sweep_lo, sweep_hi + 1, 2):
        frames.append(render_sweep(sweep_x))

    # Hold B: 3 frames — the wave passed, system is at rest again
    hold_b_toggles = [(W - 1, H - 1), (0, 0), (W - 1, 0)]
    for toggle in hold_b_toggles:
        frames.append(render_tidb(toggle))

    # Heartbeat 1 — 4 frames (2 pulses), invert/normal alternation.
    # Each frame is a fresh image with a unique toggle pixel so the
    # GIF encoder doesn't dedupe identical-looking systole/diastole
    # repetitions and the cup gets all four distinct frame slots.
    def heartbeat_frame(invert, toggle):
        f = render_tidb()
        if invert:
            f = invert_image(f)
        # Flip a corner pixel for uniqueness without disturbing letters
        cur = f.getpixel(toggle)
        f.putpixel(toggle, 0 if cur else 1)
        return f

    frames.append(heartbeat_frame(True,  (0, 0)))           # systole 1
    frames.append(heartbeat_frame(False, (W - 1, 0)))       # diastole 1
    frames.append(heartbeat_frame(True,  (0, H - 1)))       # systole 2
    frames.append(heartbeat_frame(False, (W - 1, H - 1)))   # diastole 2

    # Hold C: 3 frames
    hold_c_toggles = [(0, H - 1), (W - 1, H - 1), (0, 0)]
    for toggle in hold_c_toggles:
        frames.append(render_tidb(toggle))

    # Letter-by-letter announce — T, then I, then D, then B each pulse
    # in turn (halo around just that letter), then the whole word
    # halos at once. Reads as the system "spelling itself out": a
    # different kind of activity than the data sweep, not a mirror of
    # it. ~14 frames at speed=200 ≈ 2.2 s.
    #
    # Letter x-ranges in the canonical TIDB layout (5+1+1+1+5+1+5 → x0=14):
    #   T: 14..18, I: 20, D: 22..26, B: 28..32
    letter_ranges = [
        ('T', 14, 18),
        ('I', 20, 20),
        ('D', 22, 26),
        ('B', 28, 32),
    ]

    def render_with_letter_halo(x_lo, x_hi):
        f = render_tidb()
        for (tx, ty) in letter_pixels:
            if x_lo <= tx <= x_hi:
                if tx + 1 < W:
                    f.putpixel((tx + 1, ty), 1)
                if ty + 1 < H:
                    f.putpixel((tx, ty + 1), 1)
        return f

    # 3 frames per letter: halo, halo (held), clean release
    for name, x_lo, x_hi in letter_ranges:
        halo = render_with_letter_halo(x_lo, x_hi)
        frames.append(halo)
        # Held halo with a unique toggle so it doesn't dedupe
        halo2 = halo.copy()
        halo2.putpixel((0, 0), 1 if not halo.getpixel((0, 0)) else 0)
        frames.append(halo2)
        # Release: clean TIDB with a unique toggle per letter
        toggle_y = ord(name) % H
        frames.append(render_tidb((W - 1, toggle_y)))

    # Final beat — all four letters halo at once (the word "speaks").
    # 2 frames of full-word halo so the eye reads it as a deliberate
    # punctuation, not a flicker.
    full_halo = render_tidb()
    for (tx, ty) in letter_pixels:
        if tx + 1 < W:
            full_halo.putpixel((tx + 1, ty), 1)
        if ty + 1 < H:
            full_halo.putpixel((tx, ty + 1), 1)
    frames.append(full_halo)
    full_halo2 = full_halo.copy()
    full_halo2.putpixel((0, 0), 0 if full_halo.getpixel((0, 0)) else 1)
    frames.append(full_halo2)

    # Sonar ping — concentric diamond rings emanate from the cluster
    # center and expand outward until they reach the screen edges.
    # Reads as "TiDB broadcasting": the system has identity, now it
    # reaches out. ~6 frames, ~960 ms at speed=200.
    ping_cx = (letters_x_min + letters_x_max) // 2
    ping_cy = H // 2
    for r in (2, 4, 6, 8, 10, 12):
        f = render_tidb()
        # Draw diamond outline at this radius
        for dx in range(-r, r + 1):
            dy = r - abs(dx)
            for sign in (-1, 1):
                x = ping_cx + dx
                y = ping_cy + sign * dy
                if 0 <= x < W and 0 <= y < H:
                    f.putpixel((x, y), 1)
        frames.append(f)

    # Brief hold so the eye registers the ping reaching the edges
    # before the next motif starts.
    for toggle in [(0, 0), (W - 1, 0)]:
        frames.append(render_tidb(toggle))

    # Data packets — 1-pixel particles streaming across the screen in
    # BOTH directions simultaneously. Where a packet crosses a letter
    # pixel it visually merges (already lit); where it's in empty
    # space it shows. Reads as "concurrent distributed traffic" —
    # different from the wave packet (which was a single broad
    # wavefront) by being many independent streams. ~12 frames.
    pkt_rng = random.Random(42)
    packets = []
    # Pre-seed an active swarm so frame 0 already looks busy
    for _ in range(8):
        side = pkt_rng.choice([-1, 1])
        x = pkt_rng.randint(0, W - 1)
        y = pkt_rng.randint(0, H - 1)
        packets.append([x, y, 3 if side < 0 else -3])

    for _ in range(12):
        # Step
        for p in packets:
            p[0] += p[2]
        # Cull off-screen and respawn from opposite edge to keep flux
        packets = [p for p in packets if -1 <= p[0] <= W]
        while len(packets) < 8:
            side = pkt_rng.choice([-1, 1])
            if side < 0:
                x, vx = -1, 3
            else:
                x, vx = W, -3
            y = pkt_rng.randint(0, H - 1)
            packets.append([x, y, vx])
        # Render: TIDB underneath, packets on top (set-OR)
        f = render_tidb()
        for (x, y, _) in packets:
            if 0 <= x < W and 0 <= y < H:
                f.putpixel((x, y), 1)
        frames.append(f)

    # Brief hold so packets clear before the next motif
    frames.append(render_tidb((0, H - 1)))

    # Vertical scan — a 2-row bright bar sweeps top-to-bottom across
    # the screen. Adds the vertical axis (everything above is
    # horizontal sweep / radial / particles). Reads as "system
    # readout" — the cup is scanning itself. ~6 frames.
    for scan_y in range(0, H, 2):
        f = render_tidb()
        for x in range(W):
            for dy in (0, 1):
                yy = scan_y + dy
                if 0 <= yy < H:
                    f.putpixel((x, yy), 1)
        frames.append(f)

    # Brief hold after scan reaches bottom
    frames.append(render_tidb((W - 1, H - 1)))

    # Scatter & reform — every TIDB letter pixel detaches with an
    # outward velocity proportional to its distance from screen
    # center, drifts outward (4 frames), then is magnetically pulled
    # back to its target position (6 frames). High-energy explosion
    # + reformation — visually distinct from Act II crisis (which
    # was a small jostled cluster) and from heartbeat (full-screen
    # invert, no particle motion). ~10 frames.
    scatter_particles = []
    cx, cy = W / 2, H / 2
    for (tx, ty) in letter_pixels:
        dx, dy = tx - cx, ty - cy
        dist = max(0.5, math.hypot(dx, dy))
        # Outward unit vector × explosion speed
        vx = dx / dist * 1.6
        vy = dy / dist * 1.2
        scatter_particles.append({
            'x': float(tx), 'y': float(ty),
            'vx': vx, 'vy': vy,
            'tx': tx, 'ty': ty,
        })

    # Phase 1: scatter outward, with mild damping
    for _ in range(4):
        f = blank()
        for p in scatter_particles:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['vx'] *= 0.92
            p['vy'] *= 0.92
            xi, yi = int(round(p['x'])), int(round(p['y']))
            if 0 <= xi < W and 0 <= yi < H:
                f.putpixel((xi, yi), 1)
        # Uniqueness toggle in a position the explosion is unlikely
        # to land on (it's outward-only motion from letter region).
        f.putpixel((0, 0), 1 if not f.getpixel((0, 0)) else 0)
        frames.append(f)

    # Phase 2: magnetic recall to targets, ramping pull strength so
    # they accelerate home as they get closer. The snap radius
    # widens each frame, and the last frame hard-snaps every
    # particle to guarantee a clean TIDB at the end of the beat.
    REFORM_FRAMES = 6
    for k in range(REFORM_FRAMES):
        f = blank()
        pull = 0.22 + k * 0.06
        snap_r = 1.0 + k * 0.5
        is_last = (k == REFORM_FRAMES - 1)
        for p in scatter_particles:
            if is_last:
                p['x'], p['y'] = float(p['tx']), float(p['ty'])
            else:
                p['vx'] = p['vx'] * 0.7 + (p['tx'] - p['x']) * pull
                p['vy'] = p['vy'] * 0.7 + (p['ty'] - p['y']) * pull
                p['x'] += p['vx']
                p['y'] += p['vy']
                if math.hypot(p['tx'] - p['x'], p['ty'] - p['y']) < snap_r:
                    p['x'], p['y'] = float(p['tx']), float(p['ty'])
                    p['vx'] = p['vy'] = 0.0
            xi, yi = int(round(p['x'])), int(round(p['y']))
            if 0 <= xi < W and 0 <= yi < H:
                f.putpixel((xi, yi), 1)
        # Different uniqueness corner per frame
        corner = [(W - 1, 0), (0, H - 1), (W - 1, H - 1), (0, 0), (W - 1, 0), (0, H - 1)][k]
        f.putpixel(corner, 1 if not f.getpixel(corner) else 0)
        frames.append(f)

    # 3D rotation — simulates the TIDB letters spinning around a
    # vertical axis through screen center. We approximate the
    # projection with a horizontal squash factor s ∈ [-1, 1]:
    # s=1.0 is the canonical view, s=0 is the "edge-on" view (a
    # single vertical line where every letter pixel collapses to
    # the center column), s=-1.0 is the fully-mirrored back. As s
    # decreases, multiple letter columns collapse into the same
    # output column — the OR-merging produces the visual squashing
    # that reads as rotation. ~9 frames covering a full 360°.
    cx_axis = W // 2  # rotation axis = horizontal center

    def render_tidb_rotated(s):
        """Render TIDB squashed by horizontal factor s."""
        f = blank()
        for (tx, ty) in letter_pixels:
            offset = tx - cx_axis
            new_x = int(round(cx_axis + offset * s))
            if 0 <= new_x < W and 0 <= ty < H:
                f.putpixel((new_x, ty), 1)
        return f

    rotation_steps = [1.0, 0.6, 0.0, -0.6, -1.0, -0.6, 0.0, 0.6, 1.0]
    for i, s in enumerate(rotation_steps):
        f = render_tidb_rotated(s)
        # Uniqueness toggle in a corner that the squashed letters
        # don't reach (letters live near center column).
        toggle = [(0, 0), (W - 1, 0), (0, H - 1), (W - 1, H - 1)][i % 4]
        f.putpixel(toggle, 1 if not f.getpixel(toggle) else 0)
        frames.append(f)

    # Glitch / self-heal — random pixel corruption builds inside the
    # letter region, peaks, recedes, then a recovery halo flashes
    # before TIDB returns to clean. Says "Byzantine fault tolerance":
    # the brand survives noise. ~6 frames.
    #
    # Visual: each glitch frame XORs a set of random pixels in the
    # letter bounding box — some letter pixels go off (corruption),
    # some empty pixels go on (noise). Across the 4 corruption
    # frames intensity rises (10 → 18) then falls (12 → 5) so the
    # glitch reads as a transient disturbance, not a steady state.
    glitch_rng = random.Random(99)
    glitch_x_range = (letters_x_min - 2, letters_x_max + 2)
    glitch_y_range = (1, H - 2)
    intensities = [10, 18, 12, 5]
    for intensity in intensities:
        f = render_tidb()
        flipped = set()
        while len(flipped) < intensity:
            gx = glitch_rng.randint(*glitch_x_range)
            gy = glitch_rng.randint(*glitch_y_range)
            flipped.add((gx, gy))
        for (x, y) in flipped:
            if 0 <= x < W and 0 <= y < H:
                cur = f.getpixel((x, y))
                f.putpixel((x, y), 0 if cur else 1)
        frames.append(f)

    # Recovery halo — letters snap back with a halo flash, signaling
    # "we're whole again."
    recovery = render_tidb()
    for (tx, ty) in letter_pixels:
        if tx + 1 < W:
            recovery.putpixel((tx + 1, ty), 1)
        if ty + 1 < H:
            recovery.putpixel((tx, ty + 1), 1)
    frames.append(recovery)
    # Clean held TIDB so the eye registers full recovery
    frames.append(render_tidb((W - 1, H - 1)))

    # Constellation graph — TIDB letters as nodes in a ring topology.
    # Anchor points alternate top/bottom of the screen (above and below
    # the letters) so the connecting lines zigzag diagonally across,
    # passing *through* the letters where they intersect. Says
    # "distributed cluster topology" — the system reveals its
    # structure after reforming. ~8 frames.
    node_positions = [
        (16, 0),    # T anchor (above T center)
        (20, 11),   # I anchor (below I)
        (24, 0),    # D anchor (above D center)
        (30, 11),   # B anchor (below B center)
    ]
    edges = [(0, 1), (1, 2), (2, 3), (3, 0)]  # ring T→I→D→B→T

    def bresenham(x0, y0, x1, y1):
        """Yield (x, y) pixels along the line from (x0,y0) to (x1,y1)."""
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            yield (x0, y0)
            if x0 == x1 and y0 == y1:
                return
            e2 = err * 2
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def draw_line(img, a, b):
        for (x, y) in bresenham(a[0], a[1], b[0], b[1]):
            if 0 <= x < W and 0 <= y < H:
                img.putpixel((x, y), 1)

    def draw_nodes(img):
        for (nx, ny) in node_positions:
            if 0 <= nx < W and 0 <= ny < H:
                img.putpixel((nx, ny), 1)

    # Build 1 → 2 → 3 → 4 edges in sequence
    for n_edges in range(1, 5):
        f = render_tidb()
        draw_nodes(f)
        for ei in range(n_edges):
            a, b = edges[ei]
            draw_line(f, node_positions[a], node_positions[b])
        frames.append(f)

    # Hold the closed ring: 2 frames with corner toggle for uniqueness
    for h in range(2):
        f = render_tidb()
        draw_nodes(f)
        for a, b in edges:
            draw_line(f, node_positions[a], node_positions[b])
        toggle = (0, 0) if h == 0 else (W - 1, H - 1)
        f.putpixel(toggle, 1 if not f.getpixel(toggle) else 0)
        frames.append(f)

    # Fade — dotted edges (alternate pixels), 2 frames at offset 0/1
    for fade_step in range(2):
        f = render_tidb()
        draw_nodes(f)
        for a, b in edges:
            for i, (lx, ly) in enumerate(bresenham(
                node_positions[a][0], node_positions[a][1],
                node_positions[b][0], node_positions[b][1],
            )):
                if (i + fade_step) % 2 == 0 and 0 <= lx < W and 0 <= ly < H:
                    f.putpixel((lx, ly), 1)
        frames.append(f)

    # Hold D / settled: 3 frames before the collapse begins
    hold_d_toggles = [(W - 1, 0), (0, H - 1), (W - 1, H - 1)]
    for toggle in hold_d_toggles:
        frames.append(render_tidb(toggle))

    # Reset to small cluster: 3 frames that interpolate the TIDB letter
    # pixels toward the 6 starting cluster positions, so the loop wraps
    # cleanly back to Act I instead of fading to a single point.
    cluster_targets = []
    for i in range(6):
        ang = 2 * math.pi * i / 6
        cluster_targets.append((
            cluster_center[0] + math.cos(ang) * 2.5,
            cluster_center[1] + math.sin(ang) * 1.5,
        ))

    # Assign each TIDB pixel to a cluster slot (round-robin) so all 55
    # dots flow into the 6 final positions
    assignments = []
    for i, p in enumerate(scaled):
        if p.target is None:
            continue
        assignments.append((p.target, cluster_targets[i % 6]))

    for step in range(3):
        f = blank()
        # Easing: cubic ease-in so the collapse accelerates inward
        t = ((step + 1) / 3) ** 1.5
        seen = set()
        for (tx, ty), (cx, cy) in assignments:
            px = tx * (1 - t) + cx * t
            py = ty * (1 - t) + cy * t
            xi, yi = int(round(px)), int(round(py))
            if 0 <= xi < W and 0 <= yi < H:
                f.putpixel((xi, yi), 1)
                seen.add((xi, yi))
        # Frame uniqueness toggle in a corner where the collapse never
        # reaches, so it doesn't accidentally land on a real pixel
        if step & 1:
            f.putpixel((W - 1, H - 1), 1)
        frames.append(f)

    return frames


def main():
    frames = build_frames()
    if len(frames) > 255:
        raise RuntimeError(f"frame count {len(frames)} exceeds protocol limit")

    # SGUAI-C3 fw 1.7 only buffers 132 frames at upload — see
    # PROTOCOL_SPEC.md §4.6. The full storyboard above produces ~169
    # frames; we keep the first 132 (the beginning of the story:
    # Acts I-IV climax + early coda through the data-flow / heartbeat /
    # T-I-D-B announce / sonar). Beats that fit later in the loop
    # (vertical scan, scatter+reform, 3D rotation, glitch+heal,
    # constellation, collapse) are preserved in the storyboard but
    # not shipped in the on-cup animation. The loop-back boundary is
    # less polished without the explicit collapse-to-cluster frames,
    # but the eye still reads the abrupt return as a "reset".
    CUP_MAX_FRAMES = 132
    if len(frames) > CUP_MAX_FRAMES:
        full = len(frames)
        frames = frames[:CUP_MAX_FRAMES]
        print(f"! trimmed from {full} to {CUP_MAX_FRAMES} frames "
              f"(SGUAI-C3 fw 1.7 buffer limit)")

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
