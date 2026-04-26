# Animation Examples

Pre-rendered animations for the SGUAI-C3 cup, plus the Python scripts
that generate them. Each script is self-contained — `pillow` is the
only dependency.

## Running an example

Generate (or re-generate) the GIF:

```bash
uv run --with pillow python examples/tidb_scale_animation.py
```

Send it to the cup. The cup will then play the animation autonomously —
no further BLE traffic.

```bash
# Recommended: human-readable pacing (~9 s loop, beats are countable):
uv run python/smart_mug.py animate examples/tidb_scale.gif -s 200

# Faster for "vibes" but the scale-out beats become hard to count:
uv run python/smart_mug.py animate examples/tidb_scale.gif -s 255
```

**Speed tuning.** The cup's speed byte is monotonic (larger = faster)
but the unit isn't strictly milliseconds — see `PROTOCOL_SPEC.md` §4.6.
Empirically, period ≈ 32500 / speed, so `speed=200` ≈ 160 ms/frame
(comfortable read), `speed=130` (default) ≈ 250 ms/frame (slow and
deliberate), `speed=255` ≈ 127 ms/frame (motion-heavy but the scale
beats fly by).

(The pre-rendered `.gif` files are committed alongside the scripts so
you can upload without re-rendering.)

## What's here

### `tidb_nextgen_animation.py` → `tidb_nextgen.gif`

A flowing architectural diagram of TiDB Next-Gen's compute/storage
separation. Animation carries the "upstream → downstream"
directionality so no brand label is needed on the left.

Layout (read left to right):

```
┌───────────────────────┬──────────────────┬───────────┐
│   incoming workload   │   compute nodes  │    S3     │
│   (4 dot tracks       │   (scaling 1→8)  │           │
│    flowing rightward) │                  │ [cylinder]│
└───────────────────────┴──────────────────┴───────────┘
   cols 0-14                cols 16-31      cols 33-47
```

**Three coordinated motions, ONE narrative.** Earlier "busy" drafts
combined unrelated motions (drifting waves, flicker patterns, halos);
this version makes everything serve the same story:

- **Left third** — 4 horizontal client tracks with dots flowing
  rightward at staggered timing. The active-track count grows with
  the scale level, so visible load matches cluster capacity.
- **Middle third** — N compute nodes scaling 1 → 2 → 4 → 8 with a
  halo flash on each scale-up.
- **Right third** — "S3" label and a static cylinder outline. The
  *only* part of the canvas that doesn't change. That stillness is
  the architectural point.

The eye reads motion direction (left-to-right) automatically as
data flow, so the layout's directionality is conveyed without a
text label. The "S3" label remains because the rightmost rectangle
needs to be unambiguous.

40 frames at speed=200 ≈ 6.4 s per loop. No reveal phase — the
architecture establishes itself through the flowing motion from
frame 0.

Design history (so future-you doesn't repeat the iterations):
v1 (busy diagrams), v2 (abstract slabs), v3 (pure text marquee),
v4 (labeled diagram with counter and arrows), v5 (decluttered
labeled diagram), v6 (this version: labels removed where animation
can do the same job).

### `tidb_scale_animation.py` → `tidb_scale.gif`

A four-phase "horizontal scale-out" narrative for the TiDB brand:

1. **Boot** — "TiDB" wipes in left-to-right like a progress bar, with
   sparse Matrix-rain dots falling in the right region.
2. **Scale out** — the cluster grows 1 → 2 → 4 → 8 → 16 nodes, each
   beat spawning a diamond shape with a 1-pixel halo flash, then
   holding for ~800 ms so the count is countable. Diamonds shrink as
   the count climbs; at n = 16 they're single pixels distributed
   across the full width.
3. **Wave** — a 3-pixel-wide bright wave packet sweeps L→R across the
   16-node steady state, reading as data flowing through the cluster.
4. **Sting** — the entire display inverts for two beats at the climax,
   then returns to steady state and loops.

~55 frames at speed=200 → ~9 s per loop, paced for human reading.
Demonstrates that a 1-bit 48×12 LED matrix can carry a complete
narrative when multiple effects layer (rain background + scaling
foreground + sweeping highlight + identity anchor + surprise beat),
*as long as each beat dwells long enough for the eye to register it*.

## Designing your own

If you're authoring an animation for this cup, keep the constraints in
mind:

- **48 wide × 12 tall**, 1-bit monochrome
- **Up to 255 frames** per animation (uploaded once, played autonomously)
- **Speed byte 1..255**, larger = faster. Default 130 ≈ 250 ms/frame;
  255 ≈ 127 ms/frame. The unit isn't strictly milliseconds (see
  `PROTOCOL_SPEC.md` §4.6) but the relationship is monotonic.
- **Bitmap encoding** is row-major LTR, MSB-first — but you don't need
  to think about that; PIL `Image` mode `'1'` plus `python/smart_mug.py
  animate` handles the encoding.

The simplest authoring path is to build a list of `PIL.Image` frames
in `'1'` mode (each 48×12), save them as a GIF with `save_all=True`,
and upload via `smart_mug.py animate`. See `tidb_scale_animation.py`
for a worked example of layered effects.
