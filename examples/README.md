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

**"Murmuration"** — a flock of pixel-birds streams in chaotic from
the right edge, gradually converges, **assembles into the letters
TIDB** for one beat, then bursts outward and flies off. Then a fresh
flock streams in. Loop forever.

```
   ←── chaos: flock drifting leftward, scattered ───────

         . .   . .              .  .   .
            .         .   .   .       .       .
       .       .   .             .       .  .

   ─── converging ─────────────────────────────────────

                ▮▮▮▮▮  ▮  ▮▮▮▮·  ▮▮▮▮·
                  ▮       ▮   ▮  ▮   ▮
                  ▮     ▮ ▮   ▮  ▮▮▮▮·     ← *click!*  TIDB
                  ▮     ▮ ▮   ▮  ▮   ▮       holds for
                  ▮     ▮ ▮   ▮  ▮   ▮       one breath
                  ▮     ▮ ▮   ▮  ▮   ▮
                  ▮     ▮ ▮▮▮▮·  ▮▮▮▮·

   ─── dispersing: flock bursts outward and flies off ──

       .                                   .
              .         .                .
                  .            .

       (empty for a beat) ...
   ←── new flock streams in (loop) ──────────────────
```

A 55-bird flocking simulation with hand-rolled physics, not a generic
effect. Each bird is a pixel with position + velocity; targets are
assigned by left-to-right distance during the converge phase so the
flock settles cleanly into the letters; dispersal velocity is
outward-from-center so birds fly off the edges naturally.

**Why this works on a coffee cup**:

- Visually arresting. Flocks captivate at any scale.
- Has an actual *surprise* — the moment of assembly is a real
  punchline, not just a transition.
- Captures the *cultural* shape of TiDB (many distributed pieces
  resolving into a single coherent product) without being a
  literal architectural diagram.
- Loops cleanly. The moment of formation is something you'd want
  to wait for again.

62 frames at speed=200 ≈ 9.9 s per loop.

Design history — nine iterations:
v1 4-tier diagram (busy) → v2 abstract slab → v3 scrolling text →
v4 labeled diagram with counter (cluttered) → v5 decluttered diagram
→ v6 animated workload tracks → v7 telemetry dashboard → v8 ambient
breathing → **v9 (this version): pixel-bird murmuration with
brand-assembly punchline**. The lesson the iterations teach: when
"explain the architecture" doesn't fit the medium, do something
*genuinely creative* whose punchline IS the brand identity. The
cup's job is to be a surprise on a coffee table, not a slide.

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
