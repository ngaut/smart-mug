#!/usr/bin/env python3
"""TiDB Envelope of Scale — a stats-reel animation telling the
scalability story across 6 dimensions, one big number per card.

Inspired by the "Redefining Dimensions of Scalability" / "One Year
Later: Push the Envelope of Scale" slides.  Each card shows ONE
metric as a giant 5×7 number with a 5-row label above it; cards
transition with a wipe-in / pulse / wipe-out beat so the reel
reads as a punchy data ticker.

Cards (in order):
    1. PB+        DATA volume  (petabyte+)
    2. 1M+        QPS / TPS   (queries per second, millions)
    3. 3M         TBLS        (3 million tables)
    4. 50x        FAST        (50× faster table creation)
    5. 1M/s       IDX         (1 million rows/sec adding index)
    6. 10x        XREG        (10× cross-region throughput)
    + Outro: SaaS-ready tagline + brand reveal

48×12 monochrome panel, ~85 frames.  Pairs naturally with -s 5fps
(≈17 s/loop) so each card breathes for 1.5 s before transitioning.

Usage
-----
    uv run --with pillow python examples/tidb_envelope_animation.py
    /tmp/mug animate examples/tidb_envelope.gif -s 5fps
"""

from pathlib import Path

from PIL import Image

W, H = 48, 12

# ─── Small 5×5 glyphs for labels ─────────────────────────────────────
GLYPHS = {
    'A': ["·███·", "█···█", "█████", "█···█", "█···█"],
    'B': ["████·", "█···█", "████·", "█···█", "████·"],
    'C': ["·████", "█····", "█····", "█····", "·████"],
    'D': ["████·", "█···█", "█···█", "█···█", "████·"],
    'E': ["█████", "█····", "███··", "█····", "█████"],
    'F': ["█████", "█····", "███··", "█····", "█····"],
    'G': ["·████", "█····", "█·███", "█···█", "·████"],
    'H': ["█···█", "█···█", "█████", "█···█", "█···█"],
    'I': ["█████", "··█··", "··█··", "··█··", "█████"],
    'J': ["·████", "···█·", "···█·", "█··█·", "·██··"],
    'K': ["█···█", "█··█·", "███··", "█··█·", "█···█"],
    'L': ["█····", "█····", "█····", "█····", "█████"],
    'M': ["█···█", "██·██", "█·█·█", "█···█", "█···█"],
    'N': ["█···█", "██··█", "█·█·█", "█··██", "█···█"],
    'O': ["·███·", "█···█", "█···█", "█···█", "·███·"],
    'P': ["████·", "█···█", "████·", "█····", "█····"],
    'Q': ["·███·", "█···█", "█···█", "█··██", "·████"],
    'R': ["████·", "█···█", "████·", "█··█·", "█···█"],
    'S': ["·████", "█····", "·███·", "····█", "████·"],
    'T': ["█████", "··█··", "··█··", "··█··", "··█··"],
    'U': ["█···█", "█···█", "█···█", "█···█", "·███·"],
    'V': ["█···█", "█···█", "█···█", "·█·█·", "··█··"],
    'W': ["█···█", "█···█", "█·█·█", "██·██", "█···█"],
    'X': ["█···█", "·█·█·", "··█··", "·█·█·", "█···█"],
    'Y': ["█···█", "·█·█·", "··█··", "··█··", "··█··"],
    'Z': ["█████", "···█·", "··█··", "·█···", "█████"],
    '/': ["····█", "···█·", "··█··", "·█···", "█····"],
    '+': ["·····", "··█··", "█████", "··█··", "·····"],
    'i': ["█", "·", "█", "█", "█"],
}

# ─── BIG 5-wide × 6-tall digits & symbols ────────────────────────────
# Compressed from 7 rows to 6 so we can fit a blank-row gap between
# the top label (5 rows) and the bottom number (6 rows): 5+1+6 = 12.
BIG = {
    '0': ["·███·", "█···█", "█···█", "█···█", "█···█", "·███·"],
    '1': ["··█··", "·██··", "··█··", "··█··", "··█··", "·███·"],
    '2': ["·███·", "█···█", "···█·", "··█··", "·█···", "█████"],
    '3': ["████·", "····█", "··██·", "····█", "····█", "████·"],
    '4': ["█···█", "█···█", "█████", "····█", "····█", "····█"],
    '5': ["█████", "█····", "████·", "····█", "····█", "████·"],
    '6': ["·███·", "█····", "████·", "█···█", "█···█", "·███·"],
    '7': ["█████", "····█", "···█·", "··█··", "·█···", "█····"],
    '8': ["·███·", "█···█", "·███·", "█···█", "█···█", "·███·"],
    '9': ["·███·", "█···█", "·████", "····█", "····█", "·███·"],
    'M': ["█···█", "██·██", "█·█·█", "█·█·█", "█···█", "█···█"],
    'K': ["█···█", "█··█·", "██···", "█·█··", "█··█·", "█···█"],
    'P': ["████·", "█···█", "████·", "█····", "█····", "█····"],
    'B': ["████·", "█···█", "████·", "█···█", "█···█", "████·"],
    'T': ["█████", "··█··", "··█··", "··█··", "··█··", "··█··"],
    'X': ["█···█", "·█·█·", "··█··", "··█··", "·█·█·", "█···█"],
    'x': ["·····", "█···█", "·█·█·", "··█··", "·█·█·", "█···█"],
    '+': ["·····", "··█··", "█████", "··█··", "·····", "·····"],
    '/': ["····█", "···█·", "··█··", "·█···", "█····", "·····"],
    's': ["·····", "·███·", "█····", "·███·", "····█", "███··"],
}


def blank():
    return Image.new('1', (W, H), 0)


def stamp_small(img, text, x0, y0, mask_x_max=None):
    """Render with the 5×5 small font.  Returns x past the last glyph."""
    x = x0
    for ch in text:
        if ch == ' ':
            x += 2
            continue
        g = GLYPHS.get(ch.upper(), GLYPHS.get(ch, []))
        if not g:
            x += 2
            continue
        gw = max((len(r) for r in g), default=0)
        for ry, row in enumerate(g):
            for rx in range(gw):
                if rx < len(row) and row[rx] == "█":
                    px, py = x + rx, y0 + ry
                    if mask_x_max is not None and px >= mask_x_max:
                        continue
                    if 0 <= px < W and 0 <= py < H:
                        img.putpixel((px, py), 1)
        x += gw + 1
    return x - 1


def stamp_big(img, text, x0, y0, mask_x_max=None):
    """Render with the 5×7 BIG font."""
    x = x0
    for ch in text:
        if ch == ' ':
            x += 2
            continue
        g = BIG.get(ch, [])
        if not g:
            x += 2
            continue
        gw = max((len(r) for r in g), default=0)
        for ry, row in enumerate(g):
            for rx in range(gw):
                if rx < len(row) and row[rx] == "█":
                    px, py = x + rx, y0 + ry
                    if mask_x_max is not None and px >= mask_x_max:
                        continue
                    if 0 <= px < W and 0 <= py < H:
                        img.putpixel((px, py), 1)
        x += gw + 1
    return x - 1


def text_width_big(text):
    w = 0
    for i, ch in enumerate(text):
        if ch == ' ':
            w += 2
        else:
            g = BIG.get(ch, [])
            if g:
                w += max(len(r) for r in g)
        if i < len(text) - 1:
            w += 1
    return w


def text_width_small(text):
    w = 0
    for i, ch in enumerate(text):
        if ch == ' ':
            w += 2
        else:
            g = GLYPHS.get(ch.upper(), GLYPHS.get(ch, []))
            if g:
                w += max(len(r) for r in g)
        if i < len(text) - 1:
            w += 1
    return w


def hline(img, y, x_lo=0, x_hi=W - 1, period=2):
    for x in range(x_lo, x_hi + 1):
        if x % period == 0:
            if 0 <= y < H:
                img.putpixel((x, y), 1)


def diamond_outline(img, cx, cy, r):
    for dx in range(-r, r + 1):
        dy = r - abs(dx)
        for sign in (-1, 1):
            x, y = cx + dx, cy + sign * dy
            if 0 <= x < W and 0 <= y < H:
                img.putpixel((x, y), 1)


# ─── Card builder ────────────────────────────────────────────────────

def card(label, big_value, num_frames=10, accent=None):
    """Build a card showing `label` (small, top) and `big_value`
    (large, bottom) with a wipe-in then pulse-then-hold sequence.

    `accent` is an optional callable(frame, frame_idx_in_card) that
    decorates the frame with a metric-specific visual flourish.
    """
    frames = []
    big_w = text_width_big(big_value)
    bx = (W - big_w) // 2
    by = 6  # rows 6-11 for the big number (6 tall); row 5 is the blank gap
    small_w = text_width_small(label)
    sx = (W - small_w) // 2
    sy = 0  # rows 0-4 for the small label (5 tall)

    for t in range(num_frames):
        f = blank()
        if t == 0:
            stamp_small(f, label, sx, sy)
            stamp_big(f, big_value, bx, by, mask_x_max=bx + big_w // 3)
        elif t == 1:
            stamp_small(f, label, sx, sy)
            stamp_big(f, big_value, bx, by, mask_x_max=bx + 2 * big_w // 3)
        elif t < num_frames - 2:
            stamp_small(f, label, sx, sy)
            stamp_big(f, big_value, bx, by)
        elif t == num_frames - 2:
            # wipe-out start: right-side reveal
            stamp_small(f, label, sx, sy)
            stamp_big(f, big_value, bx, by, mask_x_max=bx + 2 * big_w // 3)
        else:
            # wipe-out finish
            stamp_small(f, label, sx, sy, mask_x_max=sx + small_w // 2)
            stamp_big(f, big_value, bx, by, mask_x_max=bx + big_w // 4)
        frames.append(f)
    return frames


# ─── Per-metric accents (a small visual flourish during hold) ────────

def accent_bars(frame_idx):
    """Returns an accent callable that draws growing bars (data volume)."""
    def fn(img, t):
        # 5 bars rising from row 11
        rng_offset = (t - 4) % 4
        for i in range(5):
            x = 4 + i * 9
            h = 1 + (i + rng_offset) % 4
            for k in range(h):
                if 0 <= x < W and 0 <= 11 - k < H:
                    img.putpixel((x, 11 - k), 1)
    return fn


def accent_flow(frame_idx):
    """Streaming dots — for QPS (queries flowing)."""
    def fn(img, t):
        # 3 dots traveling across row 11, staggered
        for stream in range(3):
            x = (t * 7 + stream * 14) % W
            if 0 <= x < W:
                img.putpixel((x, 11), 1)
    return fn


def accent_grid(frame_idx):
    """A grid filling cell-by-cell (table count growing)."""
    def fn(img, t):
        # Mini grid at bottom-left: 8x2
        for i in range(min(t * 2, 16)):
            gx, gy = 1 + (i % 8) * 2, 11 - i // 8
            if 0 <= gx < W and 0 <= gy < H:
                img.putpixel((gx, gy), 1)
    return fn


def accent_speed(frame_idx):
    """Speedometer-style sweep (table-create speed)."""
    def fn(img, t):
        # arc of dots at row 11 progressively filling
        n_dots = min(t, 9)
        for i in range(n_dots):
            x = 5 + i * 5
            if 0 <= x < W:
                img.putpixel((x, 11), 1)
    return fn


def accent_rows(frame_idx):
    """Scrolling row indicator (index rows/sec)."""
    def fn(img, t):
        # 4-pixel-wide bar zooming across row 11
        x = (t * 5) % W
        for k in range(4):
            xk = x + k
            if 0 <= xk < W:
                img.putpixel((xk, 11), 1)
    return fn


def accent_xregion(frame_idx):
    """Two clusters connected (cross-region replication)."""
    def fn(img, t):
        # 2 cluster-dots at the corners + dotted connector at row 11
        img.putpixel((2, 11), 1)
        img.putpixel((1, 11), 1)
        img.putpixel((W - 2, 11), 1)
        img.putpixel((W - 3, 11), 1)
        # animated dot traveling between them
        x = 4 + (t * 4) % (W - 8)
        if 0 <= x < W:
            img.putpixel((x, 11), 1)
    return fn


# ─── Intro / outro ───────────────────────────────────────────────────

def intro(num_frames=4):
    """Fast 'TIDB SCALE' wipe-in (pure text, no chrome)."""
    frames = []
    text = "TIDB SCALE"
    tw = text_width_small(text)
    tx = (W - tw) // 2
    ty = (H - 5) // 2
    for t in range(num_frames):
        f = blank()
        progress = (t + 1) / num_frames
        stamp_small(f, text, tx, ty, mask_x_max=tx + int(tw * progress))
        frames.append(f)
    return frames


def outro(num_frames=10):
    """Final reveal: 'SAAS READY' with TiDB anchor."""
    frames = []
    line1 = "PUSH THE"
    line2 = "ENVELOPE"
    w1 = text_width_small(line1)
    w2 = text_width_small(line2)
    x1 = (W - w1) // 2
    x2 = (W - w2) // 2
    for t in range(num_frames):
        f = blank()
        if t == 0:
            stamp_small(f, line1, x1, 0)
        elif t == 1:
            stamp_small(f, line1, x1, 0)
            stamp_small(f, line2, x2, 6)
        elif t < num_frames - 3:
            stamp_small(f, line1, x1, 0)
            stamp_small(f, line2, x2, 6)
            # halo bursts on alternating frames
            if t % 2 == 0:
                cx, cy = W // 2, H // 2
                diamond_outline(f, cx, cy, 12 + (t - 2))
        else:
            # Final frames: brand "TiDB" + cluster row
            tdb_w = text_width_small("TIDB")
            stamp_small(f, "TIDB", (W - tdb_w) // 2, (H - 5) // 2)
            for i in range(8):
                cx = int(4 + (W - 8) * i / 7)
                if 0 <= cx < W:
                    f.putpixel((cx, H - 1), 1)
        frames.append(f)
    return frames


# ─── Anti-dedup ──────────────────────────────────────────────────────

def add_frame_tick(frames):
    """7-bit binary anti-dedup at row H-1, cols 1..7.  PIL's GIF
    encoder merges identical adjacent frames; this counter ensures
    every frame is unique so the cup plays the intended timing."""
    for i, f in enumerate(frames):
        for bit in range(7):
            f.putpixel((1 + bit, H - 1), 0)
        for bit in range(7):
            if (i >> bit) & 1:
                f.putpixel((1 + bit, H - 1), 1)
    return frames


# ─── Build ───────────────────────────────────────────────────────────

def build_frames():
    return (intro(4)
            + card("DATA",  "PB+",  10)
            + card("QPS",   "1M+",  10)
            + card("TBLS",  "3M",   10)
            + card("FAST",  "50x",  10)
            + card("IDX/s", "1M",   10)
            + card("XREG",  "10x",  10)
            + outro(10))


def main():
    frames = add_frame_tick(build_frames())
    out = Path(__file__).resolve().parent / "tidb_envelope.gif"
    frames[0].save(
        out,
        save_all=True,
        append_images=frames[1:],
        duration=200,    # GIF preview pace; cup uses its own speed byte
        loop=0,
        optimize=False,
        disposal=2,
    )
    print(f"✓ wrote {out} ({len(frames)} frames)")


if __name__ == "__main__":
    main()
