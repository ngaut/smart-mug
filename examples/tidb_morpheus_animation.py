#!/usr/bin/env python3
"""TiDB Morpheus — continuous metamorphosis on a 48×12 monochrome
panel. ~85 frames at `-s 8fps` (≈11 s/loop). Six phases that flow
through one another so the panel never goes static and never
repeats an effect:

  1. GLITCH BOOT     scan-line corruption tears across the brand,
                     letters appear half-corrupted, then a vertical
                     wipe self-repairs them top→bottom
  2. CARD FLIP       each letter independently rotates around its
                     own vertical axis (like a flipping playing
                     card); cascade is staggered L→R so the brand
                     reads as a wave of rotation
  3. 3D EXTRUSION    flat letters extrude backward into 3D solids;
                     a rotation around Y reveals depth via silhouette
                     lines connecting front face to offset back face
  4. PIXEL SHATTER   the 3D form explodes — every on-pixel becomes a
                     particle with random velocity; gravity-free
                     ballistic trajectories spread outward
  5. SPIRAL REFORM   particles slow, get captured into 3 concentric
                     rotating rings around the screen center; rings
                     gradually contract and merge
  6. BRAND SNAP      rings collapse onto the letter pixels, halo
                     bursts outward in 4 expanding diamond rings,
                     then settles to brand + 8-node cluster

Visual coherence: the brand is the protagonist. It's typed,
glitched, repaired, flipped, extruded, shattered, scattered,
gathered, and reborn — all on the same 48×12 surface. By the time
it settles you've seen "TiDB" transformed seven times without ever
losing track of the brand identity.

Usage
-----
    uv run --with pillow python examples/tidb_morpheus_animation.py
    /tmp/mug animate examples/tidb_morpheus.gif -s 8fps
"""

from pathlib import Path
import math
import random

from PIL import Image

W, H = 48, 12

GLYPHS = {
    'T': ["█████", "··█··", "··█··", "··█··", "··█··"],
    'i': ["█",     "·",     "█",     "█",     "█"],
    'D': ["████·", "█···█", "█···█", "█···█", "████·"],
    'B': ["████·", "█···█", "████·", "█···█", "████·"],
}

BRAND_X = 14
BRAND_Y = 4


def blank():
    return Image.new('1', (W, H), 0)


def stamp(img, text, x0, y0):
    x = x0
    for ch in text:
        if ch == ' ':
            x += 2
            continue
        g = GLYPHS.get(ch, [])
        gw = max((len(r) for r in g), default=0)
        for ry, row in enumerate(g):
            for rx in range(gw):
                if rx < len(row) and row[rx] == "█":
                    px, py = x + rx, y0 + ry
                    if 0 <= px < W and 0 <= py < H:
                        img.putpixel((px, py), 1)
        x += gw + 1


def brand_pixels():
    canvas = blank()
    stamp(canvas, "TiDB", BRAND_X, BRAND_Y)
    return [(x, y) for y in range(H) for x in range(W) if canvas.getpixel((x, y))]


def line(img, x0, y0, x1, y1):
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx - dy
    x, y = x0, y0
    while True:
        if 0 <= x < W and 0 <= y < H:
            img.putpixel((x, y), 1)
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy


# ─────────────────────────────────────────────────────────────────────
# Phase 1 — GLITCH BOOT
# Scan-line tearing applied to the brand, then a vertical wipe
# top→bottom that "repairs" each row to the clean version.
# ─────────────────────────────────────────────────────────────────────

def phase_glitch(num_frames=12):
    rng = random.Random(3)
    base = brand_pixels()
    base_set = set(base)

    frames = []
    # Corrupt phase: rows are randomly shifted, some rows show noise
    for t in range(6):
        f = blank()
        for x, y in base_set:
            shift = rng.randint(-3, 3) if rng.random() < 0.6 else 0
            nx = x + shift
            if 0 <= nx < W:
                f.putpixel((nx, y), 1)
        # add scan-line noise on a random row
        for _ in range(8):
            nx = rng.randint(0, W - 1)
            ny = rng.randint(BRAND_Y - 1, BRAND_Y + 5)
            if 0 <= ny < H:
                f.putpixel((nx, ny), 1)
        # full corrupt scan-line (1-px tear) at a random row
        tear_y = rng.randint(0, H - 1)
        for tx in range(W):
            f.putpixel((tx, tear_y), tx % 2 == 0)
        frames.append(f)
    # Repair phase: a horizontal wipe top→bottom; above wipe = clean,
    # below wipe = still corrupted
    for t in range(6):
        f = blank()
        wipe_y = (t / 5) * H + BRAND_Y
        for x, y in base_set:
            if y < wipe_y:
                f.putpixel((x, y), 1)
            else:
                shift = rng.randint(-2, 2) if rng.random() < 0.5 else 0
                nx = x + shift
                if 0 <= nx < W:
                    f.putpixel((nx, y), 1)
        # bright scan-line at the wipe boundary
        wy = int(wipe_y)
        if 0 <= wy < H:
            for tx in range(W):
                f.putpixel((tx, wy), 1)
        frames.append(f)
    return frames


# ─────────────────────────────────────────────────────────────────────
# Phase 2 — CARD FLIP
# Each letter rotates around its own vertical center-axis. Visible
# width = full_width × |cos(θ)|. Staggered phase across letters so
# the rotation reads as a wave traveling L→R.
# ─────────────────────────────────────────────────────────────────────

def letter_layout():
    """Return list of (glyph, base_x, char_width) for "TiDB"."""
    layout = []
    x = BRAND_X
    for ch in "TiDB":
        g = GLYPHS[ch]
        gw = max(len(r) for r in g)
        layout.append((g, x, gw))
        x += gw + 1
    return layout


def flip_letter(img, glyph, base_x, gw, theta):
    """Render a 'card-flipped' letter: rotated around its vertical
    center-axis. cos(θ) compresses the horizontal extent."""
    cx = base_x + gw / 2
    c = math.cos(theta)
    for ry, row in enumerate(glyph):
        for rx in range(len(row)):
            if row[rx] != "█":
                continue
            offset = rx - (gw - 1) / 2
            sx = int(round(cx + offset * c))
            sy = BRAND_Y + ry
            if 0 <= sx < W and 0 <= sy < H:
                img.putpixel((sx, sy), 1)


def phase_cardflip(num_frames=16):
    layout = letter_layout()
    frames = []
    for t in range(num_frames):
        f = blank()
        # Each letter's rotation is offset so the wave runs L→R
        base_theta = (t / num_frames) * 2 * math.pi
        for i, (g, bx, gw) in enumerate(layout):
            theta = base_theta - i * 0.6  # staggered phase
            flip_letter(f, g, bx, gw, theta)
        frames.append(f)
    return frames


# ─────────────────────────────────────────────────────────────────────
# Phase 3 — 3D EXTRUSION
# Brand pixels become front face of a 3D shape; same pixels offset
# to back face; silhouette edges connect them. Y-rotation animates
# the depth offset (dx, dy) so the extrusion reads as 3D.
# ─────────────────────────────────────────────────────────────────────

def phase_extrude(num_frames=10):
    """Brand extrudes into 3D wireframe. Pure outline rendering:
    silhouette of the front face + same silhouette offset to the
    back face + Bresenham lines connecting corresponding points.
    Keeps the letterforms readable as 3D solids without filling."""
    base = brand_pixels()
    base_set = set(base)
    # silhouette pixels: brand pixels with at least one off neighbor
    silhouette = []
    for x, y in base:
        for ddx, ddy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            if (x + ddx, y + ddy) not in base_set:
                silhouette.append((x, y))
                break

    frames = []
    for t in range(num_frames):
        f = blank()
        depth_progress = min(1.0, t / (num_frames / 2))
        max_depth = 7 * depth_progress
        theta = (t / num_frames) * math.pi * 1.4
        dx = max_depth * math.sin(theta)
        dy = -max_depth * 0.18 * math.cos(theta)
        # connecting lines from front silhouette to back silhouette,
        # at every 3rd silhouette pixel so the rendering is sparse
        for i, (x, y) in enumerate(silhouette):
            if i % 3 != 0:
                continue
            bx = int(round(x + dx))
            by = int(round(y + dy))
            line(f, x, y, bx, by)
        # back-face silhouette
        for x, y in silhouette:
            bx = int(round(x + dx))
            by = int(round(y + dy))
            if 0 <= bx < W and 0 <= by < H:
                f.putpixel((bx, by), 1)
        # front-face: render the full glyph (the readable brand)
        for x, y in base:
            f.putpixel((x, y), 1)
        frames.append(f)
    return frames


# ─────────────────────────────────────────────────────────────────────
# Phase 4 — PIXEL SHATTER
# Every brand pixel becomes a particle with a random velocity. They
# fly outward, no gravity, leaving short trails.
# ─────────────────────────────────────────────────────────────────────

def phase_shatter(num_frames=10):
    base = brand_pixels()
    rng = random.Random(19)
    # assign each pixel a velocity vector
    particles = []
    for x, y in base:
        # outward bias from brand center
        dx0 = x - W // 2
        dy0 = y - H // 2
        ang = math.atan2(dy0, dx0) + rng.uniform(-0.5, 0.5)
        speed = 0.6 + rng.uniform(0, 1.0)
        particles.append((x, y, math.cos(ang) * speed, math.sin(ang) * speed * 0.5))

    frames = []
    for t in range(num_frames):
        f = blank()
        for x0, y0, vx, vy in particles:
            x = int(round(x0 + vx * t))
            y = int(round(y0 + vy * t))
            if 0 <= x < W and 0 <= y < H:
                f.putpixel((x, y), 1)
            # trail: 1 step behind
            if t >= 1:
                xt = int(round(x0 + vx * (t - 1)))
                yt = int(round(y0 + vy * (t - 1)))
                if 0 <= xt < W and 0 <= yt < H:
                    f.putpixel((xt, yt), 1)
        frames.append(f)
    return frames


# ─────────────────────────────────────────────────────────────────────
# Phase 5 — SPIRAL REFORM
# Particles get captured into 3 concentric rotating rings. Rings
# contract over time, merging toward the brand position.
# ─────────────────────────────────────────────────────────────────────

def phase_spiral(num_frames=12):
    rng = random.Random(31)
    cx, cy = W // 2, H // 2 + 1  # slightly below to leave room for brand
    # 3 rings, each with N particles at evenly-spaced angles
    rings = [
        {"radius": 14, "n": 16, "phase": 0.0,  "speed": 0.45},
        {"radius": 10, "n": 12, "phase": 1.0,  "speed": -0.55},
        {"radius": 6,  "n": 8,  "phase": 2.0,  "speed": 0.7},
    ]
    frames = []
    for t in range(num_frames):
        f = blank()
        contract = (t / max(1, num_frames - 1))
        for ring in rings:
            r = ring["radius"] * (1 - contract * 0.55)
            ang_offset = ring["phase"] + ring["speed"] * t
            for i in range(ring["n"]):
                a = ang_offset + (2 * math.pi * i / ring["n"])
                x = int(round(cx + r * math.cos(a)))
                y = int(round(cy + r * math.sin(a) * 0.4))
                if 0 <= x < W and 0 <= y < H:
                    f.putpixel((x, y), 1)
        frames.append(f)
    return frames


# ─────────────────────────────────────────────────────────────────────
# Phase 6 — BRAND SNAP + HALO + SETTLE
# ─────────────────────────────────────────────────────────────────────

def cluster_centers():
    return [(int(4 + (W - 8) * i / 7), H - 2) for i in range(8)]


def phase_snap(num_frames=8):
    frames = []
    cx, cy = W // 2, H // 2
    halos = [(), (), (8,), (10, 13), (13, 17), (17, 21), (), ()]
    for t in range(num_frames):
        f = blank()
        # brand fades in: start with sparse pixels, gradually full
        targets = brand_pixels()
        if t < 2:
            keep = len(targets) * (t + 1) // 3
            random.Random(0).shuffle(targets)
            for x, y in targets[:keep]:
                f.putpixel((x, y), 1)
        else:
            stamp(f, "TiDB", BRAND_X, BRAND_Y)
        for r in halos[t]:
            for dx in range(-r, r + 1):
                dy = r - abs(dx)
                for sign in (-1, 1):
                    x, y = cx + dx, cy + sign * dy
                    if 0 <= x < W and 0 <= y < H:
                        f.putpixel((x, y), 1)
        # cluster begins to materialize from frame 4
        if t >= 4:
            for ccx, ccy in cluster_centers():
                f.putpixel((ccx, ccy), 1)
        frames.append(f)
    return frames


def phase_settle(num_frames=3):
    frames = []
    for _ in range(num_frames):
        f = blank()
        stamp(f, "TiDB", BRAND_X, BRAND_Y)
        for ccx, ccy in cluster_centers():
            f.putpixel((ccx, ccy), 1)
        frames.append(f)
    return frames


# ─────────────────────────────────────────────────────────────────────
# Coda — TiDB-as-system, on a 48×12 1-bit panel.  Discipline:
#   • NO brand text (the prior 7 phases already burned the brand
#     into the viewer's eye; a 5-row 19-col text block here would
#     eat 40% of the panel and force beams to plow through it)
#   • Tiny "TiDB" anchor at the left = a 3-dot cluster at row 6
#   • 4 icons in a 2×2 grid on the right, each 4×4, with clean
#     gutters between them (negative space matters at 48×12)
#   • One beam at a time, sweeping; on arrival the icon at that
#     destination resolves
#   • Constellation phase shows everything together, but with
#     dotted (every-3rd-pixel) connector lines — sparse enough
#     that the icons stay readable
# ─────────────────────────────────────────────────────────────────────


# Anchor: where the TiDB cluster lives in the coda
ANCHOR_X = 4
ANCHOR_Y = 6


def stamp_anchor(img):
    """Tiny 3-dot cluster at the left, representing 'TiDB the system'."""
    pts = [(ANCHOR_X, ANCHOR_Y),
           (ANCHOR_X - 1, ANCHOR_Y - 1),
           (ANCHOR_X - 1, ANCHOR_Y + 1),
           (ANCHOR_X + 1, ANCHOR_Y),
           (ANCHOR_X - 2, ANCHOR_Y),
           (ANCHOR_X, ANCHOR_Y - 2),
           (ANCHOR_X, ANCHOR_Y + 2)]
    for x, y in pts:
        if 0 <= x < W and 0 <= y < H:
            img.putpixel((x, y), 1)


# 4 use-case icons, each 4 rows × 5 cols.  Distinguishable
# silhouettes that read cleanly at 1-bit even on a tiny display.
ICON_DB = [        # database barrel
    "·███·",
    "█···█",
    "█···█",
    "·███·",
]
ICON_CHART = [     # 3 ascending bars
    "····█",
    "···██",
    "··███",
    "·████",
]
ICON_DOC = [       # document with horizontal lines
    "█████",
    "█···█",
    "█···█",
    "█████",
]
ICON_NODE = [      # outlined diamond
    "··█··",
    "·█·█·",
    "█···█",
    "·███·",
]


def stamp_glyph(img, glyph, x0, y0):
    for ry, row in enumerate(glyph):
        for rx, ch in enumerate(row):
            if ch == "█":
                px, py = x0 + rx, y0 + ry
                if 0 <= px < W and 0 <= py < H:
                    img.putpixel((px, py), 1)

# Voxel cluster geometry: a 9×7 isometric-ish stack centered around
# (CX, CY). Hand-pixeled so it reads as a chunky 3D mass.
VOXEL_CX, VOXEL_CY = 18, 6
VOXEL_TOP_FACE = [    # the lit "front-top" face of the cluster
    (-3, -3), (-2, -3), (-1, -3), (0, -3),
    (-4, -2), (-3, -2), (-1, -2), (0, -2), (1, -2),
    (-4, -1), (-3, -1), (-2, -1), (-1, -1), (0, -1), (1, -1),
    (-4,  0), (-2,  0), (-1,  0), (1,  0),
    (-4,  1),           (-2,  1),         (1,  1),
    (-3,  2), (-2,  2), (-1,  2), (0,  2), (1,  2),
    (-2,  3), (-1,  3), (0,  3),
]
VOXEL_DEPTH_EDGES = [  # right-side depth dots to suggest 3D
    (2, -3), (2, -2), (2, -1), (3, -1), (2, 1), (2, 2), (2, 3),
]
SATELLITES = [           # floating outer cubes (2×2 each)
    (-8, -5), (5, -4), (-7, 4), (6, 3),
]


def draw_cluster(img, scale=1.0, jitter_seed=None):
    """Render the voxel cluster + satellites at full presence (scale=1.0)
    or partial (scale<1.0 → keep first scale-fraction of pixels for
    assemble-in animation)."""
    rng = random.Random(jitter_seed) if jitter_seed is not None else None
    full = list(VOXEL_TOP_FACE) + list(VOXEL_DEPTH_EDGES)
    keep = full if scale >= 1.0 else full[: int(len(full) * scale)]
    for dx, dy in keep:
        x, y = VOXEL_CX + dx, VOXEL_CY + dy
        if rng and rng.random() < 0.05:
            continue  # subtle stipple jitter
        if 0 <= x < W and 0 <= y < H:
            img.putpixel((x, y), 1)
    # satellite cubes — 2×2 blocks
    for i, (sdx, sdy) in enumerate(SATELLITES):
        if i >= int(len(SATELLITES) * min(1.0, scale * 1.4)):
            break
        for ddx in (0, 1):
            for ddy in (0, 1):
                x, y = VOXEL_CX + sdx + ddx, VOXEL_CY + sdy + ddy
                if 0 <= x < W and 0 <= y < H:
                    img.putpixel((x, y), 1)


def draw_rain(img, t, density=8, seed=99):
    """Sparse vertical-drop data rain — 1-pixel drops scrolling down."""
    rng = random.Random(seed)
    drops = [(rng.randint(0, 12), rng.random() * 12, rng.uniform(0.5, 1.4))
             for _ in range(density)]
    drops += [(rng.randint(34, W - 1), rng.random() * 12, rng.uniform(0.5, 1.4))
              for _ in range(density)]
    for x, y0, speed in drops:
        y = (y0 + t * speed) % (H + 4)
        for k in range(2):
            py = int(y) - k
            if 0 <= py < H:
                if k == 0 or rng.random() < 0.4:
                    img.putpixel((x, py), 1)


def phase_rain_intro(num_frames=6):
    """Data rain fades in over an empty panel (transition from settle)."""
    frames = []
    for t in range(num_frames):
        f = blank()
        # rain density grows
        density = int(2 + 6 * (t / max(1, num_frames - 1)))
        draw_rain(f, t, density=density)
        frames.append(f)
    return frames


def phase_cluster_assemble(num_frames=8):
    """Voxel cluster materializes piece-by-piece while rain continues."""
    frames = []
    for t in range(num_frames):
        f = blank()
        draw_rain(f, t + 6, density=6)
        scale = (t + 1) / num_frames
        draw_cluster(f, scale=scale, jitter_seed=t)
        frames.append(f)
    return frames


def phase_rays_burst(num_frames=7):
    """Light rays burst from cluster center toward the right edge —
    3 rays at different angles, lengths grow per frame then fade.
    Cluster persists; data rain continues sparse."""
    frames = []
    ray_targets = [
        (W - 1, 1),      # upper-right
        (W - 1, H // 2), # straight right
        (W - 1, H - 2),  # lower-right
    ]
    for t in range(num_frames):
        f = blank()
        draw_rain(f, t + 14, density=5)
        draw_cluster(f, scale=1.0)
        # rays — animated reach
        reach = (t + 1) / num_frames
        for tx, ty in ray_targets:
            ex = int(VOXEL_CX + (tx - VOXEL_CX) * reach)
            ey = int(VOXEL_CY + (ty - VOXEL_CY) * reach)
            line(f, VOXEL_CX + 4, VOXEL_CY, ex, ey)
        # sparkle stars at random positions in right zone, alt. frames
        if t % 2 == 0:
            for sx, sy in [(35, 2), (42, 6), (38, 9)]:
                # 4-point sparkle: center + 4 cardinal one off
                f.putpixel((sx, sy), 1)
                if sx - 1 >= 0:
                    f.putpixel((sx - 1, sy), 1)
                if sx + 1 < W:
                    f.putpixel((sx + 1, sy), 1)
                if sy - 1 >= 0:
                    f.putpixel((sx, sy - 1), 1)
                if sy + 1 < H:
                    f.putpixel((sx, sy + 1), 1)
        frames.append(f)
    return frames


# Tiny use-case icons (3-wide × 2-tall each) — distinguishable
# silhouettes for: database, chart, document, design.
ICONS = [
    # database (cylinder hint: top + bottom horizontal bar)
    [(0, 0), (1, 0), (2, 0),
     (0, 1), (1, 1), (2, 1)],
    # chart (3 ascending bars)
    [(0, 1),
     (1, 0), (1, 1),
     (2, 0), (2, 1)],
    # document
    [(0, 0), (1, 0), (2, 0),
     (0, 1),         (2, 1)],
    # design (corner brackets)
    [(0, 0),                 (2, 0),
     (0, 1),         (1, 1), (2, 1)],
]
ICON_POSITIONS = [(36, 1), (36, 4), (36, 7), (36, 10)]


def phase_icons_pop(num_frames=10):
    """Use-case icons appear one by one on the right; sparkle on
    arrival. Cluster + rays persist. Background rain very sparse."""
    frames = []
    for t in range(num_frames):
        f = blank()
        draw_rain(f, t + 21, density=4)
        draw_cluster(f, scale=1.0)
        # rays at full reach, lighter touch
        for (tx, ty) in [(W - 1, 1), (W - 1, H // 2), (W - 1, H - 2)]:
            line(f, VOXEL_CX + 4, VOXEL_CY, tx, ty)
        # icons appear progressively: 1 every 2 frames, then all stay
        appeared = min(len(ICONS), 1 + t // 2)
        for i in range(appeared):
            ix0, iy0 = ICON_POSITIONS[i]
            for dx, dy in ICONS[i]:
                x, y = ix0 + dx, iy0 + dy
                if 0 <= x < W and 0 <= y < H:
                    f.putpixel((x, y), 1)
            # sparkle on the frame the icon first appeared
            if t == (i * 2):
                for sdx, sdy in [(-2, 0), (0, -1), (4, 0), (1, 2)]:
                    sx, sy = ix0 + sdx, iy0 + sdy
                    if 0 <= sx < W and 0 <= sy < H:
                        f.putpixel((sx, sy), 1)
        frames.append(f)
    return frames


def phase_vista_hold(num_frames=4):
    # legacy stub — superseded by the coda phases below.  Kept so
    # external callers don't break.  Returns an empty list.
    return []


# Beam emanates from the right edge of the anchor cluster.  All beam
# targets are in a 2×2 grid in the right half of the panel — clean
# horizontal/vertical separation between targets, no diagonals
# crossing the anchor.
BEAM_ORIGIN_X = ANCHOR_X + 2
BEAM_ORIGIN_Y = ANCHOR_Y

# Icon anchor positions (top-left corners) — 2×2 grid in cols 28-44,
# rows 1-9.  4 cols of horizontal gutter between left/right column.
# Icon size: 4×5.
ICON_POSITIONS_2X2 = [
    (29, 1, ICON_DB),     # top-left   (rows 1-4)
    (40, 1, ICON_CHART),  # top-right  (rows 1-4)
    (29, 7, ICON_DOC),    # bottom-left (rows 7-10)
    (40, 7, ICON_NODE),   # bottom-right (rows 7-10)
]

# Beam targets = approximate centers of each icon
BEAM_TARGETS = [(ix + 2, iy + 2, icon) for ix, iy, icon in ICON_POSITIONS_2X2]


def dotted_line(img, x0, y0, x1, y1, period=2):
    """Bresenham line, rendered as every-Nth pixel so it reads as
    'beam of light' instead of a solid wall."""
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    steps = max(dx, dy, 1)
    for k in range(steps + 1):
        if k % period == 0:
            px = int(round(x0 + (x1 - x0) * k / steps))
            py = int(round(y0 + (y1 - y0) * k / steps))
            if 0 <= px < W and 0 <= py < H:
                img.putpixel((px, py), 1)


def phase_beacon(num_frames=16):
    """Anchor cluster at left.  ONE beam at a time fires toward a
    target on the right; 3 beam-progress frames + 1 icon-arrival
    frame per beat × 4 beats = 16 frames.  Beams travel through
    rows that don't intersect the anchor (anchor at row 6, beams
    fan to rows 3 and 9)."""
    frames = []
    for beat in range(4):
        target_x, target_y, icon = BEAM_TARGETS[beat]
        # 3-frame beam progression
        for step in range(3):
            f = blank()
            stamp_anchor(f)
            progress = (step + 1) / 3
            ex = int(round(BEAM_ORIGIN_X + (target_x - BEAM_ORIGIN_X) * progress))
            ey = int(round(BEAM_ORIGIN_Y + (target_y - BEAM_ORIGIN_Y) * progress))
            dotted_line(f, BEAM_ORIGIN_X, BEAM_ORIGIN_Y, ex, ey, period=2)
            frames.append(f)
        # 1-frame icon-arrival (no beam, just anchor + icon resolved
        # at destination)
        f = blank()
        stamp_anchor(f)
        ix, iy, icon_g = ICON_POSITIONS_2X2[beat]
        stamp_glyph(f, icon_g, ix, iy)
        frames.append(f)
    return frames


def phase_constellation(num_frames=10):
    """All 4 icons stay visible.  One icon pings per frame, and
    ONLY the connector to the currently-pinging icon is drawn —
    so each frame has anchor + 4 icons + 1 dotted beam + 1 ping.
    The eye sees the anchor 'addressing' each downstream use case
    in turn, without the panel ever filling with overlapping fans."""
    frames = []
    for t in range(num_frames):
        f = blank()
        stamp_anchor(f)
        # 4 icons (static, in their final 2×2 grid)
        for ix, iy, icon in ICON_POSITIONS_2X2:
            stamp_glyph(f, icon, ix, iy)
        # active connector — only to the currently-addressed icon
        active = t % len(ICON_POSITIONS_2X2)
        atx, aty, _ = BEAM_TARGETS[active]
        dotted_line(f, BEAM_ORIGIN_X, BEAM_ORIGIN_Y, atx, aty, period=2)
        # ping: invert the addressed icon's bounding box
        pix, piy, picon = ICON_POSITIONS_2X2[active]
        for dy in range(len(picon)):
            row = picon[dy]
            for dx in range(len(row)):
                x, y = pix + dx, piy + dy
                if 0 <= x < W and 0 <= y < H:
                    cur = f.getpixel((x, y))
                    f.putpixel((x, y), 0 if cur else 1)
        frames.append(f)
    return frames


def phase_close(num_frames=5):
    """Wind down: icons fade row-by-row, anchor expands into the
    full 8-node cluster row for a clean loop boundary back to
    phase_glitch which corrupts the brand."""
    frames = []
    # 3 frames: icons fade row-by-row (4 → 2 → 0 rows kept)
    for keep in (3, 1, 0):
        f = blank()
        stamp_anchor(f)
        for ix, iy, icon in ICON_POSITIONS_2X2:
            partial = icon[:keep]
            stamp_glyph(f, partial, ix, iy)
        frames.append(f)
    # 2 frames: clean brand text + cluster at the original positions —
    # this is the loop's "neutral" frame, and phase_glitch(t=0) builds
    # off this by corrupting it visibly.
    for _ in range(num_frames - 3):
        f = blank()
        stamp(f, "TiDB", BRAND_X, BRAND_Y)
        for ccx, ccy in cluster_centers():
            f.putpixel((ccx, ccy), 1)
        frames.append(f)
    return frames


# ─────────────────────────────────────────────────────────────────────
# In-place morph coda — TiDB letters transform DIRECTLY into use-case
# icons in their letter positions, then back.  No separate icon zone,
# no beam routing.  The point: TiDB *is* the system; the letters and
# the use cases are the same thing, just looked at differently.
#
#   T  ↔  database barrel       (5×5 ↔ 5×5)
#   i  ↔  small bar chart       (1×5 ↔ scaled into letter slot)
#   D  ↔  document silhouette
#   B  ↔  data-node diamond
#
# Implementation: each letter has a "source" glyph (the letter) and
# a "destination" glyph (the icon), both rendered in the same 5-row
# slot.  Morph by stochastic-but-deterministic subset selection:
# at progress t∈[0,1], show source pixels with probability (1-t)
# AND destination pixels with probability t, using a fixed-seed RNG
# per pixel so the transition is reproducible and reads as a
# coherent dissolve.
# ─────────────────────────────────────────────────────────────────────


def diamond_outline(img, cx, cy, r):
    for dx in range(-r, r + 1):
        dy = r - abs(dx)
        for sign in (-1, 1):
            x, y = cx + dx, cy + sign * dy
            if 0 <= x < W and 0 <= y < H:
                img.putpixel((x, y), 1)


def fill_all(img):
    for y in range(H):
        for x in range(W):
            img.putpixel((x, y), 1)


# ─── Per-letter source/destination glyphs ────────────────────────────
# All 5 rows.  Source (letter) on the left of each pair, destination
# (icon glyph in the same slot) on the right.  Same width as the letter
# so the morph happens IN PLACE.

# T (5 wide) → database barrel
T_LETTER = ["█████", "··█··", "··█··", "··█··", "··█··"]
T_ICON   = ["·███·", "█···█", "█···█", "█···█", "·███·"]

# i (1 wide is too narrow for a useful icon; render it as a 3-wide
# mini bar-chart glyph that shares the i's column anchor).  We let
# the icon spill 1 col left and 1 col right for legibility and
# subtract that back when morphing so the overall brand width stays
# the same.
I_LETTER = ["█", "·", "█", "█", "█"]
I_ICON   = ["█", "·", "█", "█", "█"]  # i stays as i (the i in TiDB is iconic)

# D (5 wide) → document silhouette
D_LETTER = ["████·", "█···█", "█···█", "█···█", "████·"]
D_ICON   = ["█████", "█···█", "█·███", "█···█", "█████"]

# B (5 wide) → data-node diamond
B_LETTER = ["████·", "█···█", "████·", "█···█", "████·"]
B_ICON   = ["··█··", "·███·", "█···█", "·███·", "··█··"]


def glyph_pixels(glyph):
    """Return set of (rx, ry) offsets that are 'on' in the glyph."""
    pts = set()
    for ry, row in enumerate(glyph):
        for rx, ch in enumerate(row):
            if ch == "█":
                pts.add((rx, ry))
    return pts


def render_morph(img, glyphs, x0_list, y0, progress, rng_seed=0):
    """For each (src, dst, x0) tuple, render a stochastic dissolve at
    `progress` ∈ [0,1].  At progress=0 we show all source pixels; at
    progress=1 we show all destination pixels.  In between, each
    pixel from each glyph is shown with a probability tied to a
    fixed-seed RNG so the transition is smooth and deterministic."""
    rng = random.Random(rng_seed)
    for (src, dst), x0 in zip(glyphs, x0_list):
        src_pts = glyph_pixels(src)
        dst_pts = glyph_pixels(dst)
        # union of all pixels we'll consider
        all_pts = src_pts | dst_pts
        for rx, ry in all_pts:
            in_src = (rx, ry) in src_pts
            in_dst = (rx, ry) in dst_pts
            r = rng.random()
            if in_src and in_dst:
                # always-on (both letter and icon have this pixel)
                show = True
            elif in_src and not in_dst:
                # source-only: fades OUT as progress rises
                show = (r > progress)
            elif in_dst and not in_src:
                # destination-only: fades IN as progress rises
                show = (r < progress)
            else:
                show = False
            if show:
                px, py = x0 + rx, y0 + ry
                if 0 <= px < W and 0 <= py < H:
                    img.putpixel((px, py), 1)


def _brand_morph_layout():
    """Compute (glyphs_list, x_offsets, y_origin) so each letter morph
    targets the SAME (x,y) the canonical 'TiDB' stamp uses, keeping
    the visual position identical across the full animation."""
    glyphs = [(T_LETTER, T_ICON),
              (I_LETTER, I_ICON),
              (D_LETTER, D_ICON),
              (B_LETTER, B_ICON)]
    # Same letter spacing as stamp(): 1-px gap between glyphs
    x_offsets = []
    x = BRAND_X
    for src, _ in glyphs:
        x_offsets.append(x)
        gw = max(len(r) for r in src)
        x += gw + 1
    return glyphs, x_offsets, BRAND_Y


def phase_morph_to_icons(num_frames=10):
    """Brand → icons, in place.  Stochastic dissolve."""
    glyphs, x_offsets, y0 = _brand_morph_layout()
    frames = []
    for t in range(num_frames):
        f = blank()
        progress = t / max(1, num_frames - 1)
        render_morph(f, glyphs, x_offsets, y0, progress, rng_seed=42)
        # subtle "system pulse" beneath: a single dot wandering across
        # the bottom row (cluster heartbeat) so the panel doesn't go
        # static during the dissolve
        dot_x = (t * 5) % W
        if 0 <= dot_x < W:
            f.putpixel((dot_x, H - 2), 1)
        frames.append(f)
    return frames


def phase_icons_alive(num_frames=8):
    """All 4 icons settled in their letter slots.  They pulse together
    (every other frame: invert all icon pixels for a beat-on/beat-off
    rhythm).  This is the climax — 'TiDB has BECOME the use cases.'"""
    glyphs, x_offsets, y0 = _brand_morph_layout()
    icons_only = [(dst, dst) for _, dst in glyphs]  # both src & dst = icon
    frames = []
    for t in range(num_frames):
        f = blank()
        render_morph(f, icons_only, x_offsets, y0, progress=1.0)
        # heartbeat: one icon at a time gets a 1-pixel halo
        if t % 2 == 0:
            ping = t // 2 % 4
            x0 = x_offsets[ping]
            _, dst = glyphs[ping]
            gw = max(len(r) for r in dst)
            for dy in (-1, 5):
                for dx in range(-1, gw + 1):
                    px, py = x0 + dx, y0 + dy
                    if 0 <= px < W and 0 <= py < H:
                        f.putpixel((px, py), 1)
            for dy in range(-1, 6):
                for dx in (-1, gw):
                    px, py = x0 + dx, y0 + dy
                    if 0 <= px < W and 0 <= py < H:
                        f.putpixel((px, py), 1)
        # cluster heartbeat continues at the bottom
        dot_x = ((t + num_frames) * 5) % W
        if 0 <= dot_x < W:
            f.putpixel((dot_x, H - 2), 1)
        frames.append(f)
    return frames


def phase_morph_back(num_frames=10):
    """Icons → brand, in place.  Reverse dissolve, same RNG seed so
    the transition retraces its own path."""
    glyphs, x_offsets, y0 = _brand_morph_layout()
    # Swap source and destination
    swapped = [(dst, src) for src, dst in glyphs]
    frames = []
    for t in range(num_frames):
        f = blank()
        progress = t / max(1, num_frames - 1)
        render_morph(f, swapped, x_offsets, y0, progress, rng_seed=42)
        dot_x = ((t + num_frames * 2) * 5) % W
        if 0 <= dot_x < W:
            f.putpixel((dot_x, H - 2), 1)
        frames.append(f)
    return frames


def phase_final_settle(num_frames=3):
    """Brand fully restored, 8-node cluster row at the bottom.  Loop
    boundary back to phase_glitch."""
    frames = []
    for _ in range(num_frames):
        f = blank()
        stamp(f, "TiDB", BRAND_X, BRAND_Y)
        for ccx, ccy in cluster_centers():
            f.putpixel((ccx, ccy), 1)
        frames.append(f)
    return frames


def phase_charge(num_frames=8):
    """Cluster row PULSES with growing halos.  Each pulse beat: 1
    halo frame, 1 quiet frame.  4 beats, halo grows each beat,
    nodes get bigger each beat — anticipation building toward the
    drop."""
    frames = []
    cx, cy = W // 2, 5
    centers = [(int(4 + (W - 8) * i / 7), cy) for i in range(8)]
    pulse_radii = [2, 4, 6, 9]
    for beat in range(4):
        f = blank()
        for ccx, ccy in centers:
            f.putpixel((ccx, ccy), 1)
        diamond_outline(f, cx, cy, pulse_radii[beat])
        frames.append(f)
        f = blank()
        r = beat // 2
        for ccx, ccy in centers:
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    if abs(dx) + abs(dy) <= r:
                        x, y = ccx + dx, ccy + dy
                        if 0 <= x < W and 0 <= y < H:
                            f.putpixel((x, y), 1)
        frames.append(f)
    return frames


def phase_drop(num_frames=2):
    """The DROP — 2 frames: full panel inverted (all white), then
    full panel blank.  Whole-screen flash that visually breaks the
    rhythm that's been building.  Like a synth tear."""
    f1 = blank()
    fill_all(f1)
    f2 = blank()
    return [f1, f2]


def phase_radiate(num_frames=8):
    """After the drop, ONE wave expands outward from screen center,
    delivers energy, then dissipates.  Icons materialize AFTER the
    wave passes through their region — never co-existing with the
    expanding ring (which would create overlap noise).  Anchor
    arrives last for a clean lock-in."""
    frames = []
    cx, cy = W // 2, H // 2
    # Frame 0–3: ring expanding outward, NOTHING ELSE (clean wave)
    for t in range(4):
        f = blank()
        diamond_outline(f, cx, cy, t * 2 + 1)  # 1, 3, 5, 7
        frames.append(f)
    # Frame 4: ring is gone; all 4 icons SLAM into existence at once
    f = blank()
    for ix, iy, icon in ICON_POSITIONS_2X2:
        stamp_glyph(f, icon, ix, iy)
    # 1-pixel halo around each icon for the first frame (impact)
    for ix, iy, icon in ICON_POSITIONS_2X2:
        for dy in (-1, len(icon)):
            for dx in range(-1, len(icon[0]) + 1):
                x, y = ix + dx, iy + dy
                if 0 <= x < W and 0 <= y < H:
                    f.putpixel((x, y), 1)
        for dy in range(-1, len(icon) + 1):
            for dx in (-1, len(icon[0])):
                x, y = ix + dx, iy + dy
                if 0 <= x < W and 0 <= y < H:
                    f.putpixel((x, y), 1)
    frames.append(f)
    # Frame 5: halos drop, just icons clean
    f = blank()
    for ix, iy, icon in ICON_POSITIONS_2X2:
        stamp_glyph(f, icon, ix, iy)
    frames.append(f)
    # Frame 6: anchor materializes (small halo around it for arrival)
    f = blank()
    for ix, iy, icon in ICON_POSITIONS_2X2:
        stamp_glyph(f, icon, ix, iy)
    stamp_anchor(f)
    diamond_outline(f, ANCHOR_X, ANCHOR_Y, 3)
    frames.append(f)
    # Frame 7: anchor + icons clean
    f = blank()
    for ix, iy, icon in ICON_POSITIONS_2X2:
        stamp_glyph(f, icon, ix, iy)
    stamp_anchor(f)
    frames.append(f)
    return frames


def phase_lock_in(num_frames=8):
    """4 icons present + anchor.  A 3-pixel STREAM packet flies
    from the anchor to each icon in turn — 2 frames per beat
    (mid-flight + arrival).  Arrival inverts the icon AND draws
    a 1-pixel halo around it: bright impact."""
    frames = []
    targets = [(ix + 2, iy + 2) for ix, iy, _ in ICON_POSITIONS_2X2]
    for beat in range(4):
        tx, ty = targets[beat]
        # Mid-flight
        f = blank()
        stamp_anchor(f)
        for ix, iy, icon in ICON_POSITIONS_2X2:
            stamp_glyph(f, icon, ix, iy)
        mx = (BEAM_ORIGIN_X + tx) // 2
        my = (BEAM_ORIGIN_Y + ty) // 2
        for k in range(3):
            sx = mx - k
            sy = my
            if 0 <= sx < W and 0 <= sy < H:
                f.putpixel((sx, sy), 1)
        frames.append(f)
        # Arrival burst
        f = blank()
        stamp_anchor(f)
        for ix, iy, icon in ICON_POSITIONS_2X2:
            stamp_glyph(f, icon, ix, iy)
        ix, iy, icon = ICON_POSITIONS_2X2[beat]
        for dy in range(len(icon)):
            row = icon[dy]
            for dx in range(len(row)):
                x, y = ix + dx, iy + dy
                if 0 <= x < W and 0 <= y < H:
                    cur = f.getpixel((x, y))
                    f.putpixel((x, y), 0 if cur else 1)
        # 1-pixel halo around the impacted icon
        for dy in (-1, len(icon)):
            for dx in range(-1, len(icon[0]) + 1):
                x, y = ix + dx, iy + dy
                if 0 <= x < W and 0 <= y < H:
                    f.putpixel((x, y), 1)
        for dy in range(-1, len(icon) + 1):
            for dx in (-1, len(icon[0])):
                x, y = ix + dx, iy + dy
                if 0 <= x < W and 0 <= y < H:
                    f.putpixel((x, y), 1)
        frames.append(f)
    return frames


def phase_unified_pulse(num_frames=4):
    """Climax — anchor + 4 icons all present, halos pulse together
    in perfect sync.  Even frames: dual-radius halo rings.  Odd
    frames: clean.  Strong on/off rhythm."""
    frames = []
    cx, cy = W // 2, H // 2
    for t in range(num_frames):
        f = blank()
        stamp_anchor(f)
        for ix, iy, icon in ICON_POSITIONS_2X2:
            stamp_glyph(f, icon, ix, iy)
        if t % 2 == 0:
            diamond_outline(f, cx, cy, 6)
            diamond_outline(f, cx, cy, 9)
        frames.append(f)
    return frames


def phase_reset(num_frames=3):
    """Back to brand + 8-node cluster, the loop's neutral state."""
    frames = []
    for _ in range(num_frames):
        f = blank()
        stamp(f, "TiDB", BRAND_X, BRAND_Y)
        for ccx, ccy in cluster_centers():
            f.putpixel((ccx, ccy), 1)
        frames.append(f)
    return frames


# ─────────────────────────────────────────────────────────────────────

def add_frame_tick(frames):
    for i, f in enumerate(frames):
        for bit in range(7):
            f.putpixel((1 + bit, H - 1), 0)
        for bit in range(7):
            if (i >> bit) & 1:
                f.putpixel((1 + bit, H - 1), 1)
    return frames


def build_frames():
    return (phase_glitch(12)
            + phase_cardflip(16)
            + phase_extrude(10)
            + phase_shatter(10)
            + phase_spiral(12)
            + phase_snap(8)
            + phase_settle(3)
            # Coda — IN-PLACE MORPH.  Each TiDB letter morphs IN PLACE
            # into a use-case icon and back.  T = database barrel,
            # i = bar chart, D = document, B = data-node diamond.
            # No "icon zone" off to the side — the brand IS the system.
            + phase_morph_to_icons(10)
            + phase_icons_alive(8)
            + phase_morph_back(10)
            + phase_final_settle(3))


def main():
    frames = add_frame_tick(build_frames())
    out = Path(__file__).resolve().parent / "tidb_morpheus.gif"
    frames[0].save(
        out,
        save_all=True,
        append_images=frames[1:],
        duration=120,
        loop=0,
        optimize=False,
        disposal=2,
    )
    print(f"✓ wrote {out} ({len(frames)} frames)")


if __name__ == "__main__":
    main()
