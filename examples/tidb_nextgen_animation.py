#!/usr/bin/env python3
"""TiDB Next-Gen architecture animation for the SGUAI-C3 cup (48×12).

Design history (so future-you doesn't repeat the iterations):
  v1: 4-tier diagram with drifting wave + flicker + trails — too busy.
  v2: Static 2-tier slab — too abstract.
  v3: Pure scrolling text — too simplified.
  v4: Labeled diagram (TIDB + counter + arrows + S3) — still busy.
  v5: Decluttered labeled diagram — readable but TIDB label was static.
  v6 (this version): Drop TIDB label entirely; reclaim that space for
      animated incoming-workload tracks. The motion now carries the
      "compute is upstream of storage" narrative that the label used
      to. Right side keeps the "S3" label + cylinder as the
      architectural anchor.

Layout (read left to right):

    ┌───────────────────────┬──────────────────┬───────────┐
    │   incoming workload   │   compute nodes  │    S3     │
    │   (4 dot tracks       │   (scaling 1→8)  │           │
    │    flowing rightward) │                  │ [cylinder]│
    └───────────────────────┴──────────────────┴───────────┘
       cols 0-14                cols 16-31      cols 33-47

The left region is no longer a label — it's animated dots traveling
rightward on 4 staggered horizontal tracks (rows 1, 4, 7, 10). When
a dot reaches the compute layer it triggers a brief halo on the
nearest compute node. The dot then continues rightward, finally
"dropping" into the cylinder on the right.

Three things happening simultaneously, all part of ONE narrative
(load arriving → compute processes → storage receives), so the eye
reads it as a coherent flow rather than competing animations.

Animation (~6 s loop at speed=200)
----------------------------------
    Phase 1 — Steady traffic at ×1 compute. Dots flow continuously
              left → right. ~1.5 s.
    Phase 2 — Scale to ×2, then ×4, then ×8. Each scale-up is a
              halo flash on new nodes; traffic continues uninterrupted.
              ~3 s.
    Phase 3 — Brief peak: all 4 client tracks emit simultaneously,
              all 8 compute nodes light up, dots converge on storage.
              ~1.5 s.
"""

from pathlib import Path
from PIL import Image

W, H = 48, 12

# 7-row pixel font for the S3 label only (TIDB removed)
GLYPHS_7 = {
    'S': ["·███", "█···", "·██·", "···█", "···█", "···█", "███·"],
    '3': ["███·", "···█", "·██·", "···█", "···█", "···█", "███·"],
}


def stamp(img, text, x0, y0):
    x = x0
    for ch in text:
        g = GLYPHS_7.get(ch)
        if g is None:
            x += 4
            continue
        gw = max(len(row) for row in g)
        for ry, row in enumerate(g):
            for rx in range(gw):
                if rx < len(row) and row[rx] == '█':
                    px, py = x + rx, y0 + ry
                    if 0 <= px < W and 0 <= py < H:
                        img.putpixel((px, py), 1)
        x += gw + 1


def blank():
    return Image.new('1', (W, H), 0)


# Layout constants
WORKLOAD_REGION = (0, 14)        # incoming-traffic tracks live here
WORKLOAD_TRACK_ROWS = (1, 4, 7, 10)   # 4 horizontal client tracks

NODE_REGION = (16, 31)
NODE_Y_TOP, NODE_Y_BOT = 5, 6
NODE_LAYOUTS = {
    1: [24],
    2: [20, 28],
    4: [18, 22, 26, 30],
    8: [16, 18, 20, 23, 25, 27, 29, 31],
}

S3_X, S3_Y = 35, 1
CYL_TOP, CYL_BOT = 8, 11
CYL_LEFT, CYL_RIGHT = 33, 47

# How fast each track's dots advance per frame
TRACK_SPEED = 2  # pixels/frame
# Stagger between tracks (so they don't all pulse together)
TRACK_OFFSETS = (0, 5, 10, 15)


def draw_s3(img):
    stamp(img, "S3", S3_X, S3_Y)


def draw_cylinder(img):
    """Static rectangular outline for the storage layer."""
    for x in range(CYL_LEFT, CYL_RIGHT + 1):
        img.putpixel((x, CYL_TOP), 1)
        img.putpixel((x, CYL_BOT), 1)
    for y in range(CYL_TOP, CYL_BOT + 1):
        img.putpixel((CYL_LEFT, y), 1)
        img.putpixel((CYL_RIGHT, y), 1)


def draw_nodes(img, n, halo_indices=()):
    if n not in NODE_LAYOUTS:
        return
    for i, x in enumerate(NODE_LAYOUTS[n]):
        if not (0 <= x < W):
            continue
        for y in (NODE_Y_TOP, NODE_Y_BOT):
            img.putpixel((x, y), 1)
        if i in halo_indices:
            if NODE_Y_TOP - 1 >= 0:
                img.putpixel((x, NODE_Y_TOP - 1), 1)
            if NODE_Y_BOT + 1 < H:
                img.putpixel((x, NODE_Y_BOT + 1), 1)


def draw_workload(img, frame_idx, n_active_tracks=4):
    """Render the 4 incoming-traffic tracks. Each track carries dots
    moving rightward across cols 0..14 with staggered timing.
    Returns a set of compute-node-x positions that should halo this
    frame (because a dot just arrived at the compute layer)."""
    halo_xs = set()
    for track_i, (row, off) in enumerate(zip(WORKLOAD_TRACK_ROWS, TRACK_OFFSETS)):
        if track_i >= n_active_tracks:
            continue
        # Dots are spaced every 6 px on the track. The position of each
        # dot on this track at this frame is (frame*TRACK_SPEED + off + 6k)
        # for integer k. We render whichever of these lie in [0, 15).
        base = (frame_idx * TRACK_SPEED + off) % 6
        for x in range(WORKLOAD_REGION[0] - base, WORKLOAD_REGION[1] + 1, 6):
            xx = x + base
            if WORKLOAD_REGION[0] <= xx <= WORKLOAD_REGION[1]:
                img.putpixel((xx, row), 1)
            # Did this dot just cross into the compute layer this frame?
            if xx == WORKLOAD_REGION[1] - 1:
                halo_xs.add(track_i)
    return halo_xs


def draw_compute_to_storage_dots(img, frame_idx):
    """A few dots between compute (col 32) and S3 (col 33) on the
    middle row, suggesting compute → storage flow. Sparse — one or two
    dots traveling, not a full stream."""
    # Two staggered dots cycling between cols 32-33 and converging on the
    # cylinder. Single row in the middle of the cylinder height.
    flow_y = (CYL_TOP + CYL_BOT) // 2  # row 9
    pos1 = (frame_idx * 2) % 4
    if pos1 < 2:
        x = NODE_REGION[1] + 1 + pos1  # 32 or 33
        if 0 <= x < W:
            img.putpixel((x, flow_y), 1)


def build_frames():
    """Continuous flow with periodic scale-ups. No reveal phase — the
    architecture establishes itself through the dots' motion."""
    frames = []

    # Define a schedule of scale levels per frame range.
    # Each level lasts ~10 frames (~1.6 s at speed=200).
    schedule = [
        (1, 8),   # 8 frames at ×1
        (2, 8),
        (4, 8),
        (8, 8),
        (8, 8),   # extra hold at peak
    ]

    frame_idx = 0
    last_n = None
    for n, count in schedule:
        for k in range(count):
            f = blank()

            # Workload tracks (always on)
            track_halos = draw_workload(f, frame_idx,
                                        n_active_tracks=min(n, 4))

            # Compute nodes — halo on first frame of new scale level
            if k == 0 and n != last_n:
                halos = list(range(n))   # all nodes flash on scale-up
            else:
                halos = []
            draw_nodes(f, n, halo_indices=halos)

            # Compute → storage flow
            draw_compute_to_storage_dots(f, frame_idx)

            # S3 anchor
            draw_s3(f)
            draw_cylinder(f)

            frames.append(f)
            frame_idx += 1
        last_n = n

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
