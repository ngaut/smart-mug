#!/usr/bin/env python3
"""TiDB Strike Force — a 1-bit demoscene-style animation that earns
the brand reveal at its climax.

A 48×12 monochrome panel running ~85 frames, paced for `-s 8fps`
(≈11 s/loop) or `-s medium` (≈21 s/loop). Six acts:

  Act 1  BOOT          horizontal scanline sweeps top→bottom with a
                       phosphor afterglow trail (CRT power-on)
  Act 2  BRAND-IN      "TiDB" types in left-to-right behind a block
                       cursor; one full-screen flicker on lock
  Act 3  BOSS DESCENT  wide irregular "Legacy DB" boss looms from
                       the top, pixels boiling inside it (Matrix
                       data-rain), descends row by row toward a tiny
                       lone TiDB node at the bottom
  Act 4  COUNTER FIRE  the lone node splits 1 → 2 → 4 → 8, each
                       spawn flashes a halo and immediately fires a
                       vertical bullet trail upward; boss takes hits
                       and visibly shrinks
  Act 5  HTAP BARRAGE  top-half OLTP bullet stream + bottom-half
                       OLAP laser sweep crossfire pulverize what's
                       left; final hit detonates an explosion
  Act 6  REFORM        explosion particles fly outward then converge
                       (linearly interpolated trajectories) into the
                       pixels of "TiDB", a halo expands, cluster
                       settles below the brand and the loop closes

The "coolness" comes from layered simultaneous motion: while bullets
fly, the boss internals roil; while nodes spawn, halos pulse; while
the brand reveals, particles still fly into it. Nothing is static.
A 7-bit anti-dedup counter at the bottom-row corner doubles as an
arcade scoreboard ticker.

Usage
-----
    uv run --with pillow python examples/tidb_strike_animation.py
    /tmp/mug animate examples/tidb_strike.gif -s 8fps
"""

from pathlib import Path
import random

from PIL import Image

W, H = 48, 12

# Same micro-font as the other examples for brand consistency.
GLYPHS = {
    'T': ["█████", "··█··", "··█··", "··█··", "··█··"],
    'i': ["█",     "·",     "█",     "█",     "█"],
    'D': ["████·", "█···█", "█···█", "█···█", "████·"],
    'B': ["████·", "█···█", "████·", "█···█", "████·"],
}

# Pre-compute the brand-stamped target image so we can drive particle
# trajectories toward those pixel positions during Act 6.
BRAND_X = 14
BRAND_Y = 4


def blank():
    return Image.new('1', (W, H), 0)


def stamp(img, text, x0, y0, mask_x_max=None):
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
                        if mask_x_max is None or px < mask_x_max:
                            img.putpixel((px, py), 1)
        x += gw + 1
    return x - 1


def brand_pixels():
    """All (x,y) pixels that 'TiDB' will occupy in the final reveal —
    used as targets for the converge-into-letters effect."""
    canvas = blank()
    stamp(canvas, "TiDB", BRAND_X, BRAND_Y)
    return [(x, y) for y in range(H) for x in range(W) if canvas.getpixel((x, y))]


def line(img, x0, y0, x1, y1):
    """Bresenham line — for wireframe cluster connections."""
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


def filled_rect(img, x0, y0, x1, y1):
    for y in range(max(0, y0), min(H, y1 + 1)):
        for x in range(max(0, x0), min(W, x1 + 1)):
            img.putpixel((x, y), 1)


def diamond(img, cx, cy, r, filled=True):
    if filled:
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
    else:
        for dx in range(-r, r + 1):
            dy = r - abs(dx)
            for sign in (-1, 1):
                x, y = cx + dx, cy + sign * dy
                if 0 <= x < W and 0 <= y < H:
                    img.putpixel((x, y), 1)


def invert(img):
    out = blank()
    for y in range(H):
        for x in range(W):
            if not img.getpixel((x, y)):
                out.putpixel((x, y), 1)
    return out


# ─────────────────────────────────────────────────────────────────────
# ACT BUILDERS
# ─────────────────────────────────────────────────────────────────────

def act1_boot():
    """CRT scan-line sweep top→bottom with a 3-row trail."""
    frames = []
    for y in range(H + 2):
        f = blank()
        # bright current row
        if 0 <= y < H:
            for x in range(W):
                f.putpixel((x, y), 1)
        # 1-row afterglow trail (sparse)
        if 1 <= y - 1 < H:
            for x in range(0, W, 2):
                f.putpixel((x, y - 1), 1)
        if 2 <= y - 2 < H:
            for x in range(0, W, 4):
                f.putpixel((x, y - 2), 1)
        frames.append(f)
    return frames


def act2_brand_in():
    """'TiDB' types in left-to-right behind a block cursor."""
    frames = []
    text = "TiDB"
    # 4 typing frames + 1 full + 1 blink-off + 1 blink-on + 1 flicker
    for n_chars in range(1, len(text) + 1):
        f = blank()
        partial = text[:n_chars]
        end_x = stamp(f, partial, BRAND_X, BRAND_Y) + 1
        # block cursor right after the last typed glyph
        for cy in range(BRAND_Y, BRAND_Y + 5):
            if 0 <= end_x < W:
                f.putpixel((end_x, cy), 1)
        frames.append(f)
    # full text, cursor on
    f = blank()
    end_x = stamp(f, text, BRAND_X, BRAND_Y) + 1
    for cy in range(BRAND_Y, BRAND_Y + 5):
        if 0 <= end_x < W:
            f.putpixel((end_x, cy), 1)
    frames.append(f)
    # full text, cursor off (blink)
    f = blank()
    stamp(f, text, BRAND_X, BRAND_Y)
    frames.append(f)
    # full screen flicker (signal acquired)
    f = blank()
    for y in range(H):
        for x in range(W):
            f.putpixel((x, y), 1)
    frames.append(f)
    # back to brand
    f = blank()
    stamp(f, text, BRAND_X, BRAND_Y)
    frames.append(f)
    return frames


def boss_shape(t):
    """Wide irregular boss silhouette. Top-row width grows toward
    middle, edges noisy. Returns set of (x,y) pixels at this t step."""
    rng = random.Random(7 + t)
    pixels = set()
    # boss occupies rows 0..3 + descends per t
    descent = t // 2
    for ry in range(4):
        # width gets wider in middle rows, plus per-row jitter
        base_w = 24 + ry * 4
        cx = W // 2
        x_left = cx - base_w // 2 + rng.randint(-1, 1)
        x_right = cx + base_w // 2 + rng.randint(-1, 1)
        for x in range(x_left, x_right + 1):
            if rng.random() < 0.85:  # 15% holes — looks "alive"
                px, py = x, ry + descent
                if 0 <= px < W and 0 <= py < H:
                    pixels.add((px, py))
    return pixels


def act3_boss_descent():
    """Boss appears, descends; lone TiDB node visible at bottom."""
    frames = []
    for t in range(8):
        f = blank()
        # boss
        for x, y in boss_shape(t):
            f.putpixel((x, y), 1)
        # falling data-rain inside the boss zone
        rng = random.Random(31 + t)
        for _ in range(4):
            rx = rng.randint(8, W - 9)
            ry = rng.randint(0, 3) + t // 2
            if 0 <= ry < H:
                f.putpixel((rx, ry), 1)
        # lone TiDB node at bottom-center, blinking
        if t % 2 == 0:
            diamond(f, W // 2, H - 2, 1)
        else:
            f.putpixel((W // 2, H - 2), 1)
        frames.append(f)
    return frames


def cluster_centers(n, y=H - 2):
    if n <= 0:
        return []
    if n == 1:
        return [(W // 2, y)]
    spacing = (W - 8) / (n - 1)
    return [(int(4 + spacing * i), y) for i in range(n)]


def act4_counterfire():
    """Nodes spawn 2 → 4 → 8, each spawn fires a vertical bullet
    upward; boss takes damage (shrinks) on each hit."""
    frames = []
    boss_t = 8  # continue boss descent index

    def boss_pixels(damage_pct):
        """Boss with `damage_pct` fraction of its pixels removed."""
        full = list(boss_shape(boss_t))
        rng = random.Random(99)
        rng.shuffle(full)
        keep = full[: int(len(full) * (1 - damage_pct))]
        return keep

    schedule = [
        (2, 0.20),  # 2 nodes, 20% boss damage
        (4, 0.45),  # 4 nodes, 45% damage
        (8, 0.75),  # 8 nodes, 75% damage
    ]
    for n, damage in schedule:
        centers = cluster_centers(n)
        # Spawn flash — halo around each new node
        f = blank()
        for x, y in boss_pixels(damage / 2):
            f.putpixel((x, y), 1)
        for cx, cy in centers:
            diamond(f, cx, cy, 1, filled=True)
            diamond(f, cx, cy, 2, filled=False)
        frames.append(f)
        # Bullet rise — 3 frames of bullet trails climbing
        for step in range(3):
            f = blank()
            damage_now = damage * ((step + 1) / 3)
            for x, y in boss_pixels(damage_now):
                f.putpixel((x, y), 1)
            for cx, cy in centers:
                diamond(f, cx, cy, 1)
            # bullets: 3-pixel vertical streak per node, rising
            for cx, _ in centers:
                bullet_y = cy - 2 - step * 2
                for k in range(3):
                    by = bullet_y - k
                    if 0 <= by < H:
                        f.putpixel((cx, by), 1)
            frames.append(f)
    # Hold a beat with 8-node steady + ~75% boss
    f = blank()
    for x, y in boss_pixels(0.75):
        f.putpixel((x, y), 1)
    for cx, cy in cluster_centers(8):
        diamond(f, cx, cy, 1)
    frames.append(f)
    return frames


def act5_htap_barrage():
    """Top OLTP bullets + bottom OLAP laser bars; final hit pulverizes
    what's left of the boss."""
    frames = []
    centers = cluster_centers(8)

    def remaining_boss(damage):
        full = list(boss_shape(8))
        rng = random.Random(99)
        rng.shuffle(full)
        return full[: int(len(full) * (1 - damage))]

    OLTP_ROW = 1
    OLAP_ROW = 7
    NUM_FRAMES = 10
    for t in range(NUM_FRAMES):
        f = blank()
        # boss decaying
        damage = 0.75 + (t / NUM_FRAMES) * 0.25
        for x, y in remaining_boss(min(0.99, damage)):
            f.putpixel((x, y), 1)
        # cluster nodes — pulse-on every other frame
        for cx, cy in centers:
            if t % 2 == 0:
                diamond(f, cx, cy, 1)
            else:
                f.putpixel((cx, cy), 1)
        # wireframe links connecting first/last + every other
        if t % 3 == 0:
            for i in range(len(centers) - 1):
                x0, y0 = centers[i]
                x1, y1 = centers[i + 1]
                line(f, x0, y0, x1, y1)
        # OLTP rapid dots (top), 3 staggered streams
        for stream in range(3):
            x = (t * 5 + stream * 14) % W
            f.putpixel((x, OLTP_ROW), 1)
            if 0 <= x - 1 < W:
                f.putpixel((x - 1, OLTP_ROW), 1)
        # OLAP wide sweep (mid), 5-px wide bar
        sweep_x = (t * 3) % W
        for k in range(5):
            x = (sweep_x + k) % W
            f.putpixel((x, OLAP_ROW), 1)
        frames.append(f)
    # Final detonation — full screen flash
    f = blank()
    for y in range(H):
        for x in range(W):
            f.putpixel((x, y), 1)
    frames.append(f)
    return frames


def act6_reform():
    """Particles fly outward from explosion center, then converge
    (linearly) into the pixels of 'TiDB'. Halo expands, settle."""
    frames = []
    targets = brand_pixels()  # final positions of 'TiDB'
    # Spawn particles around the explosion center
    rng = random.Random(13)
    cx, cy = W // 2, H // 2
    # one particle per target pixel (so they all land)
    starts = []
    for _ in targets:
        sx = cx + rng.randint(-W // 2, W // 2)
        sy = cy + rng.randint(-H // 2, H // 2)
        starts.append((sx, sy))

    NUM_STEPS = 5
    for step in range(1, NUM_STEPS + 1):
        f = blank()
        alpha = step / NUM_STEPS
        for (sx, sy), (tx, ty) in zip(starts, targets):
            px = int(sx + (tx - sx) * alpha)
            py = int(sy + (ty - sy) * alpha)
            if 0 <= px < W and 0 <= py < H:
                f.putpixel((px, py), 1)
        # cluster nodes start to reappear at the bottom for the final
        # frames as the brand consolidates
        if step >= NUM_STEPS - 1:
            for ccx, ccy in cluster_centers(8):
                f.putpixel((ccx, ccy), 1)
        frames.append(f)

    # Halo bursting outward from screen center, on top of brand
    for r in (3, 5, 7):
        f = blank()
        stamp(f, "TiDB", BRAND_X, BRAND_Y)
        for ccx, ccy in cluster_centers(8):
            f.putpixel((ccx, ccy), 1)
        # outline diamond at radius r
        for dx in range(-r, r + 1):
            dy = r - abs(dx)
            for sign in (-1, 1):
                x, y = W // 2 + dx, H // 2 + sign * dy
                if 0 <= x < W and 0 <= y < H:
                    f.putpixel((x, y), 1)
        frames.append(f)

    # Final settle: brand + cluster, no halo, two hold frames so the
    # loop boundary feels deliberate.
    for _ in range(2):
        f = blank()
        stamp(f, "TiDB", BRAND_X, BRAND_Y)
        for ccx, ccy in cluster_centers(8):
            f.putpixel((ccx, ccy), 1)
        frames.append(f)
    return frames


def add_frame_tick(frames):
    """7-bit binary anti-dedup at row H-1, cols 1..7. Without this PIL's
    GIF encoder merges consecutive identical frames and the cup plays
    the wrong sequence."""
    for i, f in enumerate(frames):
        for bit in range(7):
            f.putpixel((1 + bit, H - 1), 0)
        for bit in range(7):
            if (i >> bit) & 1:
                f.putpixel((1 + bit, H - 1), 1)
    return frames


def build_frames():
    return (act1_boot()
            + act2_brand_in()
            + act3_boss_descent()
            + act4_counterfire()
            + act5_htap_barrage()
            + act6_reform())


def main():
    frames = add_frame_tick(build_frames())
    out = Path(__file__).resolve().parent / "tidb_strike.gif"
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
