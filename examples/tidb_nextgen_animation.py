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
                        • data wave L→R (data flowing through)
                        • heartbeat × 2 (the system is alive)
                        • T-I-D-B announce + full-word halo (identity)
                        • sonar ping (concentric rings, broadcasting)
                        • data packets (concurrent multi-stream traffic)
                        • hold + collapse back to the Act-I cluster
                      Each beat says something different — no
                      mirror duplications, no padding.

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

# 7-row font for the TIDB target
GLYPHS_7 = {
    'T': ["█████", "··█··", "··█··", "··█··", "··█··", "··█··", "··█··"],
    'I': ["█",     "·",     "█",     "█",     "█",     "█",     "█"],
    'D': ["████·", "█···█", "█···█", "█···█", "█···█", "█···█", "████·"],
    'B': ["████·", "█···█", "████·", "█···█", "█···█", "█···█", "████·"],
}


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
