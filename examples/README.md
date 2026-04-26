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

A **labeled architecture diagram with animated data flow**, conveying
TiDB Next-Gen's compute/storage-separated design.

Layout (read left to right):

```
┌─────────────┬──────────────────────────┬───────────┐
│   TIDB      │     N compute nodes      │    S3     │
│   ×N        │     (dots scaling)       │           │
│             ▶─── data flow arrows ───▶ │ [cylinder]│
└─────────────┴──────────────────────────┴───────────┘
   cols 0-14         cols 16-31            cols 33-47
```

The "TIDB" and "S3" labels (in a 7-row bold hand-pixel font) anchor
what each part is — the architecture reads at a glance even without
prior context. The "×N" counter below TIDB and the visible node
count both grow (×1 → ×2 → ×4 → ×8) so the viewer sees the *number*
and the *visual* agreeing. The S3 cylinder on the right doesn't
change. **That side-by-side IS the architectural punchline of
compute/storage separation.**

Three phases (~7 s loop at speed=200):

1. **Reveal** — TIDB label types in, S3 types in, storage cylinder
   fills. Architecture establishes itself.
2. **Scale-out** — ×1 → ×2 → ×4 → ×8 with halo flashes on new
   nodes. Counter increments. Data-flow arrows pulse left → right
   between phases.
3. **Sustained throughput** — at full ×8 scale, dots continuously
   stream from compute nodes to the storage cylinder.

42 frames; well within the 255-frame protocol limit.

Design history note: earlier drafts oscillated between *too busy*
(drifting wavy storage line, flicker patterns, packet trails all
competing for attention) and *too thin* (pure scrolling text with
no architectural content). The labeled-diagram-with-flow approach
turned out to be the middle path that conveys the architecture
*and* stays legible.

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
