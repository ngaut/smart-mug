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

A telemetry dashboard for TiDB Next-Gen. **Stops trying to be an
architecture diagram** (which doesn't fit 48×12) and instead shows
what the architecture delivers: enormous, climbing scale.

```
   ┌─────────────────────────────┐
   │           1M                │     ← climbing magnitude (8 rows tall)
   │                             │
   │                             │
   ├─────────────────────────────┤
   │ ▓▓▓▓▓▓▓▓▓░░░░░░░ 65%        │     ← load bar (fills as N climbs)
   └─────────────────────────────┘
```

The counter ticks **1K → 10K → 100K → 1M → 10M → ∞**, each value
held for ~1 second. The load bar fills proportionally on each step
(5% → 20% → 45% → 65% → 85% → 100%). On the ∞ frame the whole
display flashes inverse, then the loop resets.

40 frames at speed=200 ≈ 6.4 s per loop. Loop reads instantly as
"system handling massive load and keeping up".

Design history (long version):

- **v1**: 4-tier diagram with drifting wave + flicker + trails. Too
  busy.
- **v2**: Static 2-tier slab. Too abstract without prior context.
- **v3**: Pure scrolling text. Too thin, no architectural content.
- **v4**: Labeled diagram with `×N` counter and animated arrows.
  Cluttered.
- **v5**: Decluttered diagram (TIDB + nodes + S3 + cylinder). Better,
  but the static labels were doing a lot of work.
- **v6**: Removed TIDB label, used animated incoming-workload tracks
  in its place. Better directionality but still a diagram.
- **v7 (this version)**: Backed up two levels and reframed entirely.
  A 48×12 LED matrix can't render multi-tier architecture, but it
  can render a *climbing magnitude with a load bar*. That's the
  shape of the medium. Numbers and bars need no decoding; the
  dashboard reads at a glance.

The lesson: **match the visualization to the canvas's geometry, not
to the prose description of the system**.

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
