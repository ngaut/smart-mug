#!/usr/bin/env python3
"""TiDB Next-Gen architecture animation for the SGUAI-C3 cup (48×12).

The brief: convey TiDB Next-Gen's headline architectural ideas
(stateless compute layer, shared storage on object store, elastic
scaling) on 576 pixels, 1 bit deep. The display is vertical-narrow,
which we use to our advantage: vertical position IS the architectural
tier, horizontal position is parallelism.

Layout (4 lanes × 3 rows = 12 rows total):

    rows 0-2:  APP        — clients (small markers) issuing queries
    rows 3-5:  TiDB SQL   — stateless compute pillars (elastically scalable)
    rows 6-8:  TiKV/Flash — transactional + analytical engine clusters
    rows 9-11: S3         — shared object storage (wavy line, "ocean")

Narrative (4 acts, ~9.5 s loop at speed=200):

    Act 1 — Idle. Architecture at rest. Each lane shows its identity
            glyph; subtle flicker on the storage layer. (~1.3 s)
    Act 2 — Single query. A bright packet leaves a client, descends
            APP → SQL → KV → S3, then a result packet returns up.
            Tells the basic data path. (~2.5 s)
    Act 3 — Elastic scale-out. The SQL lane's compute pillars double
            in count (4 → 8), with halo flashes — the stateless tier
            scales while storage at the bottom is unchanged. The whole
            point of compute/storage separation. (~2 s)
    Act 4 — Burst. Multiple queries simultaneously descend across the
            full width, fan out at the SQL tier, all converge on the
            shared storage tier and fan back up. (~3.6 s)

Tuning notes
------------
Recommended speed=200 (cup period ≈ 160 ms/frame). At 255 the burst
phase becomes hard to read; at 130 the idle phase feels sluggish.

Usage
-----
    uv run --with pillow python examples/tidb_nextgen_animation.py
    cd python && uv run smart_mug.py animate ../examples/tidb_nextgen.gif -s 200
"""

from pathlib import Path
import random

from PIL import Image

W, H = 48, 12

# Lane layout — each lane is 3 rows tall.
LANE_APP    = (0, 2)   # rows 0..2
LANE_SQL    = (3, 5)
LANE_ENG    = (6, 8)   # TiKV / TiFlash
LANE_S3     = (9, 11)

# Static topology (positions chosen so motion lanes don't collide with glyphs).
APP_CLIENTS = [6, 18, 30, 42]                       # x positions of 4 clients
SQL_PILLARS_BASE = [4, 12, 20, 28, 36, 44]          # 6 pillars at scale 1
ENG_TIKV_X    = (8, 16)                             # TiKV cluster: 3 px wide block
ENG_TIFLASH_X = (28, 36)                            # TiFlash cluster
ENG_TIKV_LBL  = 24                                  # divider between left/right
S3_ROW = 10                                         # wavy line on this row

random.seed(42)


def blank():
    return Image.new('1', (W, H), 0)


def draw_app_lane(img, active_clients=()):
    """Each client is a small 2-pixel-tall triangle pointer.
    `active_clients` is an iterable of client indices to render brighter
    (with a halo) — used when a client is currently emitting a query."""
    for i, x in enumerate(APP_CLIENTS):
        # Base glyph: a small downward chevron at rows 0-1.
        # Row 0: ·X·   Row 1: XXX  → looks like a downward arrow head
        img.putpixel((x, 0), 1)
        for dx in (-1, 0, 1):
            xx = x + dx
            if 0 <= xx < W:
                img.putpixel((xx, 1), 1)
        if i in active_clients:
            # Halo: extend the X at row 0 slightly + add row 2 marker
            for dx in (-1, 0, 1):
                xx = x + dx
                if 0 <= xx < W:
                    img.putpixel((xx, 0), 1)
            img.putpixel((x, 2), 1)


def draw_sql_lane(img, pillars, glow_indices=()):
    """SQL lane: vertical pillars at the given x positions, rows 3-5.
    A pillar is a 1-pixel-wide column 3 rows tall.
    `glow_indices` are pillar indices that get a halo (extra row above)."""
    for i, x in enumerate(pillars):
        if not (0 <= x < W):
            continue
        for y in range(3, 6):
            img.putpixel((x, y), 1)
        if i in glow_indices:
            # Add horizontal halo dots to either side at row 4 (middle)
            for dx in (-1, 1):
                xx = x + dx
                if 0 <= xx < W:
                    img.putpixel((xx, 4), 1)


def draw_engine_lane(img, kv_active=False, flash_active=False, frame_phase=0):
    """Engine lane: two cluster blocks (TiKV left, TiFlash right). Each
    is a 3×3 block with a faint inner pattern. Active state lights more
    pixels inside the block."""
    # TiKV: 3×3 block at rows 6-8, cols ENG_TIKV_X[0]..ENG_TIKV_X[1]
    def stamp_cluster(x_start, active):
        for y_off, row_pat in enumerate([
            "█·█·█·█·█",   # interleaved
            "·█·█·█·█·",
            "█·█·█·█·█",
        ]):
            y = 6 + y_off
            for dx, ch in enumerate(row_pat):
                if dx > (ENG_TIKV_X[1] - ENG_TIKV_X[0]):
                    break
                if ch == '█':
                    if active or ((dx + y_off + frame_phase) % 4 == 0):
                        img.putpixel((x_start + dx, y), 1)
    stamp_cluster(ENG_TIKV_X[0], kv_active)
    stamp_cluster(ENG_TIFLASH_X[0], flash_active)
    # Subtle separator between the two clusters: single pixel at row 7
    img.putpixel((ENG_TIKV_LBL, 7), 1)


def draw_s3_lane(img, wave_phase=0):
    """S3 lane: a moving wavy line at row 10 with sparse "deposit"
    pixels on rows 9 and 11, suggesting an ocean of storage."""
    for x in range(W):
        # Sine-ish wave: y oscillates between 9, 10, 11
        offset = (x + wave_phase) % 6
        if offset == 0:
            img.putpixel((x, 9), 1)
        elif offset == 3:
            img.putpixel((x, 11), 1)
        # Always draw the baseline at row 10 except where the deposit took over
        if offset != 0 and offset != 3:
            img.putpixel((x, 10), 1)


def draw_packet(img, x, y):
    """A single bright pixel + faint trailing pixel above (1 row of motion blur)."""
    if 0 <= x < W and 0 <= y < H:
        img.putpixel((x, y), 1)


def draw_packet_with_trail(img, x, y, direction='down'):
    """Bright packet at (x,y) + 1-pixel trail in the opposite direction
    of motion to suggest velocity."""
    if 0 <= x < W and 0 <= y < H:
        img.putpixel((x, y), 1)
    trail_y = y - 1 if direction == 'down' else y + 1
    if 0 <= x < W and 0 <= trail_y < H:
        img.putpixel((x, trail_y), 1)


def build_frames():
    frames = []

    # ------------------------------------------------------------------
    # Act 1 — Idle steady state. Show the architecture at rest.
    # 8 frames at speed=200 ≈ 1.3 s. Wave moves slowly through S3.
    # ------------------------------------------------------------------
    for i in range(8):
        f = blank()
        draw_app_lane(f)
        draw_sql_lane(f, SQL_PILLARS_BASE[:4])  # start with 4 pillars
        draw_engine_lane(f, frame_phase=i)
        draw_s3_lane(f, wave_phase=i)
        frames.append(f)

    # ------------------------------------------------------------------
    # Act 2 — Single query: client 1 (x=18) emits, packet descends to
    # S3 (row 10), then a result packet ascends back. ~2.5 s.
    # The packet path is just the column at x=18, traveling
    # rows 2 → 10 (down) and 10 → 0 (up).
    # ------------------------------------------------------------------
    query_x = APP_CLIENTS[1]  # 18

    # Descent: rows 2 → 10 (9 frames)
    for step, y in enumerate(range(2, 11)):
        f = blank()
        draw_app_lane(f, active_clients=[1] if y < 4 else ())
        draw_sql_lane(f, SQL_PILLARS_BASE[:4],
                      glow_indices=[1] if 3 <= y <= 5 else ())
        draw_engine_lane(f, kv_active=(6 <= y <= 8),
                         frame_phase=(8 + step))
        draw_s3_lane(f, wave_phase=(8 + step))
        draw_packet_with_trail(f, query_x, y, direction='down')
        frames.append(f)

    # Brief "hit S3" beat: 1 frame with a bright cluster at the S3 lane
    # near where the packet landed
    f = blank()
    draw_app_lane(f)
    draw_sql_lane(f, SQL_PILLARS_BASE[:4])
    draw_engine_lane(f, frame_phase=17)
    draw_s3_lane(f, wave_phase=17)
    # Bright "splash" at the S3 lane where packet hit
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            xx, yy = query_x + dx, 10 + dy
            if 0 <= xx < W and 0 <= yy < H:
                f.putpixel((xx, yy), 1)
    frames.append(f)

    # Ascent: rows 10 → 0 (return path with the result)
    for step, y in enumerate(range(10, -1, -1)):
        f = blank()
        draw_app_lane(f, active_clients=[1] if y <= 1 else ())
        draw_sql_lane(f, SQL_PILLARS_BASE[:4],
                      glow_indices=[1] if 3 <= y <= 5 else ())
        draw_engine_lane(f, kv_active=(6 <= y <= 8),
                         frame_phase=(18 + step))
        draw_s3_lane(f, wave_phase=(18 + step))
        draw_packet_with_trail(f, query_x, y, direction='up')
        frames.append(f)

    # ------------------------------------------------------------------
    # Act 3 — Elastic scale-out at the SQL tier.
    # Pillars go from 4 → 6 → 8, each with a halo flash. ~2 s.
    # ------------------------------------------------------------------
    scale_steps = [
        (SQL_PILLARS_BASE[:4], []),                  # baseline
        (SQL_PILLARS_BASE[:4], list(range(4))),      # baseline + glow flash
        (SQL_PILLARS_BASE[:6], [4, 5]),              # 2 new pillars + glow
        (SQL_PILLARS_BASE[:6], []),                  # settle at 6
        # Now double again: 6 → 8 (using two interpolated positions)
        (SQL_PILLARS_BASE[:6] + [8, 40], [6, 7]),    # 2 new + glow
        (SQL_PILLARS_BASE[:6] + [8, 40], []),        # settle at 8
    ]
    for step_idx, (pillars, glow) in enumerate(scale_steps):
        for hold in range(2):  # each step holds 2 frames ≈ 320 ms
            f = blank()
            draw_app_lane(f)
            draw_sql_lane(f, pillars, glow_indices=glow if hold == 0 else ())
            draw_engine_lane(f, frame_phase=(30 + step_idx * 2 + hold))
            draw_s3_lane(f, wave_phase=(30 + step_idx * 2 + hold))
            frames.append(f)

    SQL_PILLARS_FULL = SQL_PILLARS_BASE[:6] + [8, 40]

    # ------------------------------------------------------------------
    # Act 4 — Burst load. 4 packets descend simultaneously from each
    # client, converge on shared S3, then ascend back as 4 results.
    # ~3.6 s.
    # ------------------------------------------------------------------

    # Descent phase: 4 packets at x = APP_CLIENTS, all moving y: 2→10
    for step, y in enumerate(range(2, 11)):
        f = blank()
        active_clients = [i for i in range(4)] if y < 4 else ()
        draw_app_lane(f, active_clients=active_clients)
        # Glow whichever pillars the packets are passing through
        # Each packet is at (APP_CLIENTS[i], y); a pillar at xp is "hit"
        # if there's a packet within 2 pixels horizontally and y is in
        # SQL lane (3..5). Match approximately.
        glow = []
        if 3 <= y <= 5:
            for px, x in enumerate(SQL_PILLARS_FULL):
                if any(abs(x - cx) <= 4 for cx in APP_CLIENTS):
                    glow.append(px)
        draw_sql_lane(f, SQL_PILLARS_FULL, glow_indices=glow)
        # Engine lane — both KV and Flash light up because packets traverse
        eng_active = (6 <= y <= 8)
        draw_engine_lane(f, kv_active=eng_active, flash_active=eng_active,
                         frame_phase=(50 + step))
        draw_s3_lane(f, wave_phase=(50 + step))
        for cx in APP_CLIENTS:
            draw_packet_with_trail(f, cx, y, direction='down')
        frames.append(f)

    # Convergence/splash beat: all 4 packets visible at S3 lane, big splash
    f = blank()
    draw_app_lane(f)
    draw_sql_lane(f, SQL_PILLARS_FULL)
    draw_engine_lane(f, frame_phase=60)
    draw_s3_lane(f, wave_phase=60)
    # Big splash across the whole S3 lane: light all of row 9-11 sparsely
    for x in range(W):
        if x % 2 == 0:
            f.putpixel((x, 9), 1)
        f.putpixel((x, 10), 1)
        if x % 2 == 1:
            f.putpixel((x, 11), 1)
    frames.append(f)
    frames.append(f)  # hold the splash for 2 frames

    # Ascent phase: 4 packets returning, y: 10→0
    for step, y in enumerate(range(10, -1, -1)):
        f = blank()
        active_clients = [i for i in range(4)] if y <= 1 else ()
        draw_app_lane(f, active_clients=active_clients)
        glow = []
        if 3 <= y <= 5:
            for px, x in enumerate(SQL_PILLARS_FULL):
                if any(abs(x - cx) <= 4 for cx in APP_CLIENTS):
                    glow.append(px)
        draw_sql_lane(f, SQL_PILLARS_FULL, glow_indices=glow)
        eng_active = (6 <= y <= 8)
        draw_engine_lane(f, kv_active=eng_active, flash_active=eng_active,
                         frame_phase=(62 + step))
        draw_s3_lane(f, wave_phase=(62 + step))
        for cx in APP_CLIENTS:
            draw_packet_with_trail(f, cx, y, direction='up')
        frames.append(f)

    # Final brief steady state at full scale before loop wraps.
    for i in range(3):
        f = blank()
        draw_app_lane(f)
        draw_sql_lane(f, SQL_PILLARS_FULL)
        draw_engine_lane(f, frame_phase=(75 + i))
        draw_s3_lane(f, wave_phase=(75 + i))
        frames.append(f)

    return frames


def main():
    frames = build_frames()
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
