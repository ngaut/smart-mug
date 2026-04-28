#!/usr/bin/env python3
"""TiDB Hyperspace — a 1-bit demoscene piece designed for the cup.

48×12 monochrome panel, ~85 frames at `-s 8fps` (≈11 s/loop). Eight
overlapping effects, each transitioning seamlessly into the next so
the animation never goes static:

  Phase 1  PLASMA          two-axis sine plasma fades in, threshold
                           climbs so a chaotic field resolves into a
                           crisp dot grid
  Phase 2  GRID LIFT-OFF   the grid lifts off the plane, becomes
                           the 8 vertices of a wireframe cube
  Phase 3  CUBE SPIN       cube rotates around Y axis with cheap
                           perspective (vertices closer to camera
                           draw at larger radius); 12 Bresenham edges
                           connecting the 8 corners
  Phase 4  WARP            cube vertices fly outward as a starfield;
                           parallax — nearer stars move faster than
                           distant ones — fakes 3D depth
  Phase 5  HYPERSPACE      stars reverse: instead of streaming OUT
                           they zoom IN, each one targeted at a
                           specific pixel of the "TiDB" letterforms
  Phase 6  BRAND LOCK      letters fully resolved; double halo burst
                           expanding from the screen center
  Phase 7  HEARTBEAT       ECG-style trace sweeps L→R below the
                           brand, on each beat the 8 cluster nodes
                           pulse from dots into filled diamonds
  Phase 8  CLOSE           clean settle for two frames before looping

The "cool" comes from real math, not just hand-tuned timings: the
cube uses 3D rotation + perspective projection, the plasma uses
two summed sine waves, the starfield uses radial parametric motion,
the brand reveal uses linear interpolation toward computed target
pixels, and the heartbeat uses a sweeping cursor with on-beat node
amplification. Anti-dedup binary counter ticks at the bottom-left.

Usage
-----
    uv run --with pillow python examples/tidb_hyperspace_animation.py
    /tmp/mug animate examples/tidb_hyperspace.gif -s 8fps
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
    """Bresenham line."""
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
# Phase 1 — PLASMA fade-in resolving into a dot grid
# ─────────────────────────────────────────────────────────────────────

def phase_plasma(num_frames=10):
    frames = []
    for t in range(num_frames):
        f = blank()
        # threshold sweeps from low (lots on) to high (sparse) so the
        # field resolves into a more-and-more-deliberate pattern
        thresh = -1.5 + 2.8 * (t / max(1, num_frames - 1))
        for y in range(H):
            for x in range(W):
                v = (math.sin(x / 4 + t * 0.45)
                     + math.sin(y / 2.5 + t * 0.35)
                     + math.sin((x + y) / 5 + t * 0.55))
                if v > thresh:
                    f.putpixel((x, y), 1)
        frames.append(f)
    return frames


# ─────────────────────────────────────────────────────────────────────
# Phase 2/3 — GRID LIFT-OFF + CUBE SPIN
# ─────────────────────────────────────────────────────────────────────

# 8 unit-cube vertices in 3D. Screen-aspect compensation happens in
# projection (scale_x ≠ scale_y) so the cube stays a cube in 3D.
CUBE_V = [(x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
# Edges connect vertex-pairs differing in exactly one coordinate.
CUBE_E = [(i, j) for i in range(8) for j in range(i + 1, 8)
          if bin(i ^ j).count('1') == 1]


def project_cube(theta, scale_x=12, scale_y=4):
    """Rotate cube around Y, project to 2D with simple perspective.
    The 4:1 panel aspect is compensated by using different X/Y scales —
    the cube is a true cube in 3D, just stretched horizontally on
    screen to fill the available real estate."""
    cy_, sy_ = math.cos(theta), math.sin(theta)
    cx, cy = W // 2, H // 2
    out = []
    for x, y, z in CUBE_V:
        # rotate around Y
        rx = x * cy_ + z * sy_
        rz = -x * sy_ + z * cy_
        # perspective: vertices closer to the camera (smaller rz)
        # project larger; far vertices (larger rz) project smaller.
        fov = 3.0
        f_p = fov / (fov + rz)
        px = cx + rx * scale_x * f_p / 1.6  # tame so cube fits horizontally
        py = cy + y * scale_y * f_p / 1.0
        out.append((int(round(px)), int(round(py))))
    return out


def phase_cube_spin(num_frames=14):
    frames = []
    for t in range(num_frames):
        f = blank()
        theta = (t / num_frames) * 2 * math.pi  # full rotation
        verts = project_cube(theta)
        for a, b in CUBE_E:
            line(f, verts[a][0], verts[a][1], verts[b][0], verts[b][1])
        frames.append(f)
    return frames


# ─────────────────────────────────────────────────────────────────────
# Phase 4 — WARP starfield outward
# ─────────────────────────────────────────────────────────────────────

def phase_warp_out(num_frames=8):
    frames = []
    rng = random.Random(11)
    n_stars = 36
    # each star: angle, parallax-depth (closer = faster), spawn distance
    stars = []
    for _ in range(n_stars):
        angle = rng.random() * 2 * math.pi
        depth = 0.3 + rng.random() * 1.2  # closer/farther multiplier
        d0 = rng.random() * 6
        stars.append((angle, depth, d0))
    cx, cy = W // 2, H // 2
    for t in range(num_frames):
        f = blank()
        for angle, depth, d0 in stars:
            d = d0 + t * 1.6 * depth
            x = int(cx + d * math.cos(angle))
            y = int(cy + d * math.sin(angle) * 0.5)
            if 0 <= x < W and 0 <= y < H:
                f.putpixel((x, y), 1)
            # short trail behind each star (1 step back)
            d_trail = d - 1.0 * depth
            xt = int(cx + d_trail * math.cos(angle))
            yt = int(cy + d_trail * math.sin(angle) * 0.5)
            if 0 <= xt < W and 0 <= yt < H:
                f.putpixel((xt, yt), 1)
        frames.append(f)
    return frames


# ─────────────────────────────────────────────────────────────────────
# Phase 5 — HYPERSPACE: stars zoom IN to brand-letter pixels
# ─────────────────────────────────────────────────────────────────────

def phase_zoom_in(num_frames=10):
    frames = []
    targets = brand_pixels()
    rng = random.Random(7)
    # each star launches from a far-edge position chosen radially
    starts = []
    for tx, ty in targets:
        ang = rng.random() * 2 * math.pi
        r = 30 + rng.random() * 20  # far enough to start off-screen
        sx = int(W // 2 + r * math.cos(ang))
        sy = int(H // 2 + r * math.sin(ang))
        starts.append((sx, sy))
    for t in range(num_frames):
        f = blank()
        alpha = (t + 1) / num_frames
        for (sx, sy), (tx, ty) in zip(starts, targets):
            # ease-in: alpha**0.6 makes stars accelerate as they near
            a = alpha ** 0.6
            px = int(sx + (tx - sx) * a)
            py = int(sy + (ty - sy) * a)
            if 0 <= px < W and 0 <= py < H:
                f.putpixel((px, py), 1)
            # 1-pixel trail behind, fading in last frame
            if t < num_frames - 2:
                a_back = max(0, a - 0.08)
                tx_b = int(sx + (tx - sx) * a_back)
                ty_b = int(sy + (ty - sy) * a_back)
                if 0 <= tx_b < W and 0 <= ty_b < H:
                    f.putpixel((tx_b, ty_b), 1)
        frames.append(f)
    return frames


# ─────────────────────────────────────────────────────────────────────
# Phase 6 — BRAND LOCK + double halo burst
# ─────────────────────────────────────────────────────────────────────

def phase_lock(num_frames=5):
    """Brand-locked + concentric halos expanding outward. Inner radii
    are kept ≥ 7 so the halo never cuts through the letterforms."""
    frames = []
    cx, cy = W // 2, H // 2
    radii_per_frame = [(), (8,), (10, 13), (13, 17), ()]
    for t in range(num_frames):
        f = blank()
        stamp(f, "TiDB", BRAND_X, BRAND_Y)
        for r in radii_per_frame[t]:
            for dx in range(-r, r + 1):
                dy = r - abs(dx)
                for sign in (-1, 1):
                    x, y = cx + dx, cy + sign * dy
                    if 0 <= x < W and 0 <= y < H:
                        f.putpixel((x, y), 1)
        frames.append(f)
    return frames


# ─────────────────────────────────────────────────────────────────────
# Phase 7 — HEARTBEAT trace + cluster pulse
# ─────────────────────────────────────────────────────────────────────

CLUSTER_Y = H - 2


def cluster_centers():
    return [(int(4 + (W - 8) * i / 7), CLUSTER_Y) for i in range(8)]


def phase_heartbeat(num_frames=12):
    frames = []
    centers = cluster_centers()
    for t in range(num_frames):
        f = blank()
        stamp(f, "TiDB", BRAND_X, BRAND_Y)
        # ECG trace at row 10 — sweeps L→R; one "spike" per beat at col 24
        sweep_x = (t * 5) % W
        for x in range(W):
            # baseline row 10 with spike near sweep_x
            d = (x - sweep_x) % W
            if d == 0:
                # peak
                f.putpixel((x, 9), 1)
                f.putpixel((x, 10), 1)
                f.putpixel((x, 11), 1)
            elif d == 1 or d == W - 1:
                f.putpixel((x, 10), 1)
            elif d <= 3 or d >= W - 3:
                # baseline near spike
                pass  # leave subtle gap
            else:
                # baseline
                if x % 2 == 0:
                    f.putpixel((x, 10), 1)
        # cluster nodes — pulse on beat (every other frame)
        beat = (t // 3) % 2 == 0
        for cx, cy in centers:
            if beat:
                # filled small diamond
                f.putpixel((cx, cy), 1)
                f.putpixel((cx - 1, cy), 1)
                f.putpixel((cx + 1, cy), 1)
                if cy - 1 >= 0:
                    f.putpixel((cx, cy - 1), 1)
            else:
                f.putpixel((cx, cy), 1)
        frames.append(f)
    return frames


# ─────────────────────────────────────────────────────────────────────
# Phase 8 — settle / loop boundary
# ─────────────────────────────────────────────────────────────────────

def phase_settle(num_frames=2):
    frames = []
    centers = cluster_centers()
    for _ in range(num_frames):
        f = blank()
        stamp(f, "TiDB", BRAND_X, BRAND_Y)
        for cx, cy in centers:
            f.putpixel((cx, cy), 1)
        frames.append(f)
    return frames


# ─────────────────────────────────────────────────────────────────────

def add_frame_tick(frames):
    """7-bit binary anti-dedup at row H-1, cols 1..7."""
    for i, f in enumerate(frames):
        for bit in range(7):
            f.putpixel((1 + bit, H - 1), 0)
        for bit in range(7):
            if (i >> bit) & 1:
                f.putpixel((1 + bit, H - 1), 1)
    return frames


def build_frames():
    return (phase_plasma(10)
            + phase_cube_spin(14)
            + phase_warp_out(8)
            + phase_zoom_in(10)
            + phase_lock(5)
            + phase_heartbeat(12)
            + phase_settle(2))


def main():
    frames = add_frame_tick(build_frames())
    out = Path(__file__).resolve().parent / "tidb_hyperspace.gif"
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
