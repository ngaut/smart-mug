#!/usr/bin/env python3
"""TiDB Arcade — a game-style animation that explains TiDB in 6 stages.

Tells a small arcade story on a 48×12 monochrome panel:

    Stage 1  TITLE      "TiDB" with arcade blink + corner stars
    Stage 2  OVERLOAD   single MySQL node takes fire, breaks under load
    Stage 3  POWER-UP   "+" descends, scale-out unlocked
    Stage 4  CLUSTER    nodes 1 → 2 → 4 → 8 spawn with halos
    Stage 5  HTAP       top OLTP dots + bottom OLAP sweeps run together
    Stage 6  VICTORY    boss-cleared invert sting, starburst, settle

Each visual element is a TiDB use-case in disguise:
  - the lone node breaking   → why sharded MySQL falls over
  - the scale-out beats      → horizontal scalability
  - top vs bottom traffic    → HTAP (OLTP + OLAP, same cluster)
  - the starburst clear      → the brand promise: distributed SQL
                                that makes the boss fight winnable

Designed for the SGUAI-C3 fw 1.6/1.7 cup (≤100 frames safe). Pairs
naturally with the Go CLI's speed forms — try `-s 8fps` (~12 s/loop)
or `-s medium` (~24 s/loop) so each stage's beats land deliberately.

Usage
-----
    # Generate (overwrites tidb_arcade.gif next to this script):
    uv run --with pillow examples/tidb_arcade_animation.py

    # Send to cup:
    /tmp/mug animate examples/tidb_arcade.gif -s 8fps
"""

from pathlib import Path

from PIL import Image

W, H = 48, 12

# Tiny pixel font — same metrics as tidb_scale_animation.py so the brand
# letters render consistently across both clips.
GLYPHS = {
    'T': ["█████", "··█··", "··█··", "··█··", "··█··"],
    'i': ["█",     "·",     "█",     "█",     "█"],
    'D': ["████·", "█···█", "█···█", "█···█", "████·"],
    'B': ["████·", "█···█", "████·", "█···█", "████·"],
    'H': ["█···█", "█···█", "█████", "█···█", "█···█"],
    'A': ["·███·", "█···█", "█████", "█···█", "█···█"],
    'P': ["████·", "█···█", "████·", "█····", "█····"],
    'S': ["·████", "█····", "·███·", "····█", "████·"],
    '1': ["··█··", "·██··", "··█··", "··█··", "·███·"],
    '2': ["████·", "····█", "·███·", "█····", "█████"],
    '3': ["████·", "····█", "·███·", "····█", "████·"],
}


def blank():
    return Image.new('1', (W, H), 0)


def stamp(img, text, x0, y0, scale=1):
    """Draw `text` starting at (x0, y0). Glyph height = 5×scale, width
    varies per char. Returns x past the last glyph."""
    x = x0
    for ch in text:
        if ch == ' ':
            x += 2 * scale
            continue
        g = GLYPHS.get(ch, [])
        gw = max((len(r) for r in g), default=0)
        for ry, row in enumerate(g):
            for rx in range(gw):
                if rx < len(row) and row[rx] == "█":
                    for sy in range(scale):
                        for sx in range(scale):
                            px, py = x + rx * scale + sx, y0 + ry * scale + sy
                            if 0 <= px < W and 0 <= py < H:
                                img.putpixel((px, py), 1)
        x += gw * scale + scale
    return x - scale


def filled_diamond(img, cx, cy, r):
    """Manhattan-distance disc."""
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
    """Outline-only diamond at radius r+1 (the halo flash)."""
    rr = r + 1
    for dx in range(-rr, rr + 1):
        dy = rr - abs(dx)
        for sign in (-1, 1):
            x, y = cx + dx, cy + sign * dy
            if 0 <= x < W and 0 <= y < H:
                img.putpixel((x, y), 1)


def square(img, cx, cy, r):
    """Filled square outline (the lone-node node)."""
    for dx in range(-r, r + 1):
        for dy in range(-r, r + 1):
            x, y = cx + dx, cy + dy
            if 0 <= x < W and 0 <= y < H:
                img.putpixel((x, y), 1)


def hcross(img, cx, cy, r):
    """X mark for the explosion beat."""
    for d in range(-r, r + 1):
        for x, y in [(cx + d, cy + d), (cx + d, cy - d)]:
            if 0 <= x < W and 0 <= y < H:
                img.putpixel((x, y), 1)


def invert(img):
    out = blank()
    for y in range(H):
        for x in range(W):
            if not img.getpixel((x, y)):
                out.putpixel((x, y), 1)
    return out


def corner_stars(img, on=True):
    """Arcade-marquee 4-corner sparkle."""
    if not on:
        return
    for x, y in [(0, 0), (W - 1, 0), (0, H - 1), (W - 1, H - 1)]:
        img.putpixel((x, y), 1)


def node_positions(n, x0=8, x1=W - 9, y=5):
    if n <= 0:
        return []
    if n == 1:
        return [((x0 + x1) // 2, y)]
    spacing = (x1 - x0) / max(1, n - 1)
    return [(int(x0 + spacing * i), y) for i in range(n)]


def build_frames():
    frames = []

    # ─────────────────────────────────────────────────────────────
    # STAGE 1 — TITLE (10 frames). "TiDB" with arcade-corner blinks.
    # ─────────────────────────────────────────────────────────────
    title_x = (W - (5 + 1 + 1 + 1 + 5 + 1 + 5)) // 2  # rough center
    title_y = (H - 5) // 2
    for i in range(10):
        f = blank()
        stamp(f, "TiDB", title_x, title_y)
        # Sparkle on/off every 2 frames for a marquee feel
        if (i // 2) % 2 == 0:
            corner_stars(f, True)
        frames.append(f)

    # ─────────────────────────────────────────────────────────────
    # STAGE 2 — OVERLOAD (16 frames). Single node taking fire.
    # The center node holds at (24, 5). Projectiles come in from
    # both edges, frame by frame closing toward the node. Each
    # impact inverts the node briefly (a flash). Eventually the
    # node breaks: explosion X, then a "GAME OVER"-feeling blank.
    # ─────────────────────────────────────────────────────────────
    cx, cy = 24, 5
    # 3 waves of incoming fire
    for wave in range(3):
        for step in range(4):
            f = blank()
            # the node
            square(f, cx, cy, 1)
            # incoming projectiles
            left_x = step + wave * 2          # advances 0..3
            right_x = W - 1 - left_x
            if 0 <= left_x < W:
                f.putpixel((left_x, cy), 1)
            if 0 <= right_x < W:
                f.putpixel((right_x, cy), 1)
            frames.append(f)
        # impact flash — invert the central node + halo on hit
        f = blank()
        # impact halo
        for d in range(-2, 3):
            if 0 <= cx + d < W:
                f.putpixel((cx + d, cy), 1)
            if 0 <= cy + d < H:
                f.putpixel((cx, cy + d), 1)
        frames.append(f)

    # Explosion beat — X mark + scatter
    f = blank()
    hcross(f, cx, cy, 3)
    frames.append(f)
    # Scatter
    f = blank()
    for px, py in [(cx - 4, cy - 1), (cx + 4, cy + 1),
                   (cx - 2, cy - 3), (cx + 2, cy + 3)]:
        if 0 <= px < W and 0 <= py < H:
            f.putpixel((px, py), 1)
    frames.append(f)
    # Aftermath blank
    frames.append(blank())

    # ─────────────────────────────────────────────────────────────
    # STAGE 3 — POWER-UP (6 frames). "↑" arrow descends from top,
    # impact flash spawns the cluster.
    # ─────────────────────────────────────────────────────────────
    for y in (0, 2, 4):
        f = blank()
        # Up-arrow glyph (3 wide, falling from top toward node spot)
        for dx, dy in [(0, 0), (-1, 1), (1, 1), (0, 1), (0, 2)]:
            px, py = cx + dx, y + dy
            if 0 <= px < W and 0 <= py < H:
                f.putpixel((px, py), 1)
        frames.append(f)
    # Impact halo (huge ring)
    f = blank()
    for r in (3, 4):
        for dx in range(-r, r + 1):
            dy = r - abs(dx)
            for sign in (-1, 1):
                x, y = cx + dx, cy + sign * dy
                if 0 <= x < W and 0 <= y < H:
                    f.putpixel((x, y), 1)
    frames.append(f)
    # Spawn beat — single seed node, halo flash
    f = blank()
    filled_diamond(f, cx, cy, 1)
    diamond_halo(f, cx, cy, 1)
    frames.append(f)
    # Settle
    f = blank()
    filled_diamond(f, cx, cy, 1)
    frames.append(f)

    # ─────────────────────────────────────────────────────────────
    # STAGE 4 — CLUSTER (12 frames). Doubling cascade 2 → 4 → 8.
    # Each beat: 1 spawn frame (filled + halo) + 2 settle frames.
    # ─────────────────────────────────────────────────────────────
    radii = {1: 1, 2: 1, 4: 1, 8: 0}
    for n in (2, 4, 8):
        centers = node_positions(n)
        r = radii[n]
        # Spawn flash
        f = blank()
        for ccx, ccy in centers:
            filled_diamond(f, ccx, ccy, r)
            diamond_halo(f, ccx, ccy, r)
        frames.append(f)
        # Settle (2 frames)
        for _ in range(2):
            f = blank()
            for ccx, ccy in centers:
                filled_diamond(f, ccx, ccy, r)
            frames.append(f)
    # Hold the 8-node steady
    final_centers = node_positions(8)
    f = blank()
    for ccx, ccy in final_centers:
        f.putpixel((ccx, ccy), 1)
    frames.append(f)
    f = blank()
    for ccx, ccy in final_centers:
        f.putpixel((ccx, ccy), 1)
    # tag with "HTAP" near the top to set up the next stage
    stamp(f, "HTAP", 13, 0)
    frames.append(f)
    f = blank()
    for ccx, ccy in final_centers:
        f.putpixel((ccx, ccy), 1)
    stamp(f, "HTAP", 13, 0)
    frames.append(f)

    # ─────────────────────────────────────────────────────────────
    # STAGE 5 — HTAP (16 frames). Top OLTP dots stream L→R; bottom
    # OLAP sweep spans 3-px wide and crawls L→R; 8 cluster nodes
    # mid-row flash as traffic crosses them. Two passes.
    # ─────────────────────────────────────────────────────────────
    OLTP_ROW = 1
    OLAP_ROW = 10
    for pass_idx in range(2):
        for t in range(8):
            f = blank()
            # cluster row (centers)
            for i, (ccx, ccy) in enumerate(final_centers):
                # node "lit" iff a query is near it this frame
                near_oltp = (t * 6 + pass_idx * 3) % W in range(ccx - 2, ccx + 3)
                near_olap = (t * 4 + pass_idx) % W in range(ccx - 3, ccx + 4)
                if near_oltp or near_olap:
                    filled_diamond(f, ccx, ccy, 1)
                else:
                    f.putpixel((ccx, ccy), 1)
            # OLTP burst — 3 small dots staggered
            for k in range(3):
                x = (t * 6 + k * 4 + pass_idx * 3) % W
                f.putpixel((x, OLTP_ROW), 1)
            # OLAP wide sweep — 4-px-wide bar moving slower
            sweep_x = (t * 4 + pass_idx) % W
            for k in range(4):
                x = (sweep_x + k) % W
                f.putpixel((x, OLAP_ROW), 1)
            frames.append(f)

    # ─────────────────────────────────────────────────────────────
    # STAGE 6 — VICTORY (10 frames). Boss-cleared sting + starburst
    # + brand reveal + loop-friendly settle.
    # ─────────────────────────────────────────────────────────────
    # Sting: full-display invert for two beats
    base = blank()
    for ccx, ccy in final_centers:
        filled_diamond(base, ccx, ccy, 1)
    sting = invert(base)
    frames.append(sting)
    frames.append(sting.copy())  # distinct Image so per-frame tick differs

    # Starburst — expanding halo from screen center on top of nodes
    sx, sy = W // 2, H // 2
    for r in (2, 4, 6):
        f = blank()
        for ccx, ccy in final_centers:
            f.putpixel((ccx, ccy), 1)
        # outline diamond at radius r
        for dx in range(-r, r + 1):
            dy = r - abs(dx)
            for sign in (-1, 1):
                x, y = sx + dx, sy + sign * dy
                if 0 <= x < W and 0 <= y < H:
                    f.putpixel((x, y), 1)
        frames.append(f)

    # Brand reveal — "TiDB" + cluster
    for _ in range(3):
        f = blank()
        for ccx, ccy in final_centers:
            f.putpixel((ccx, ccy), 1)
        stamp(f, "TiDB", title_x, 0)
        corner_stars(f, True)
        frames.append(f)

    # Settle — clean cluster (no text, no stars), 2 hold frames so the
    # loop boundary feels deliberate before the next title cycle.
    for _ in range(2):
        f = blank()
        for ccx, ccy in final_centers:
            f.putpixel((ccx, ccy), 1)
        frames.append(f)

    return frames


def add_frame_tick(frames):
    """Per-frame uniqueness marker: a 7-bit binary counter across the
    bottom row (cols 1..7), away from the corner-stars region. Each
    frame index gets a distinct bit pattern, so PIL's GIF encoder
    can't merge consecutive identical frames — without this the cup
    plays a shortened sequence at the wrong pace. Reads as an
    arcade-style scoreboard ticker at the bottom-left."""
    for i, f in enumerate(frames):
        # Clear the counter region first so an inverted frame doesn't
        # come in with the same all-ones pattern across the counter.
        for bit in range(7):
            f.putpixel((1 + bit, H - 1), 0)
        for bit in range(7):
            if (i >> bit) & 1:
                f.putpixel((1 + bit, H - 1), 1)
    return frames


def main():
    frames = add_frame_tick(build_frames())
    out = Path(__file__).resolve().parent / "tidb_arcade.gif"
    frames[0].save(
        out,
        save_all=True,
        append_images=frames[1:],
        duration=120,    # GIF-preview pace; cup uses its own speed byte
        loop=0,
        optimize=False,
        disposal=2,
    )
    print(f"✓ wrote {out} ({len(frames)} frames)")


if __name__ == "__main__":
    main()
