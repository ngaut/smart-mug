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

**"Survive & Scale"** — a four-act story told in pixels, not a single
visual moment. The TIDB letters at the end are *earned* by the
narrative, not a logo bolted on:

```
   Act I — ORDER
       . .          a small cluster bobs on a heartbeat. The
      .   .         system at rest. Establishing baseline.
       . .

   Act II — CRISIS
   .  →  . .  ←  .  load streams in from both edges, jostling
        .         the cluster. 3 dots wink out — the system
   .  →     ←  .   nearly loses. Then they revive. Survival.

   Act III — SCALE
        . . . .    cell-division waves: 6 → 12 → 24 → 48
     . . . . . .   the cluster grows outward in pulses,
    . . . . . . .  absorbing the load.

   Act IV — TRIUMPH
   ▮▮▮▮▮ ▮ ▮▮▮▮ ▮▮▮▮      the dots organize into TIDB
     ▮     ▮  ▮ ▮  ▮      *snap* (halo flash)
     ▮  ▮  ▮  ▮ ▮▮▮▮      *flash* (whole-display invert)
     ▮  ▮  ▮  ▮ ▮  ▮      hold the brand for a breath...
     ▮  ▮ ▮▮▮▮  ▮▮▮▮      then collapse back to the cluster
                          and the story restarts.
```

**Why this works on a coffee cup**: a story with stakes survives the
constraints of a 48×12 monochrome panel better than a single arresting
image. The viewer reads four beats — *establish, threaten, adapt,
prevail* — and the brand-assembly is the *punchline of the story*, not
the whole content. Loops cleanly because the collapse-back lands
exactly on the Act I cluster geometry.

132 frames at speed=200 ≈ 21 s per loop. The full storyboard runs ~169
frames but the cup's fw 1.7 animation buffer caps at 132 frames
(see `PROTOCOL_SPEC.md §4.6`); the generator trims to 132 so the
upload doesn't crash mid-stream. The shipped `tidb_nextgen.gif`
focuses on the early acts; later beats (vertical scan, scatter+reform,
3D rotation, glitch+heal, constellation) are kept in the source for
future cup firmware that lifts the limit.

### `tidb_nextgen_100.gif`

A 100-frame trim of `tidb_nextgen.gif` for cups with a smaller frame
buffer than fw 1.7 — empirically **fw 1.6 caps at 131 frames** (a 132-
frame upload fails mid-stream at frame 131 and leaves the cup BLE-
unreachable until power-cycle). Trimming to 100 sits well inside
both buffer limits and is safe to upload regardless of firmware.

Pacing-wise this variant pairs well with `-s 8fps` (≈12 s loop) or
`-s 5fps` (≈20 s loop) on the Go CLI's user-friendly speed forms;
both let each act of the narrative dwell long enough to register.

Reproduce with:

```bash
uv run --with pillow python -c "
from PIL import Image
src = Image.open('examples/tidb_nextgen.gif')
frames = []
for i in range(min(100, src.n_frames)):
    src.seek(i)
    frames.append(src.copy())
frames[0].save('examples/tidb_nextgen_100.gif',
               save_all=True, append_images=frames[1:],
               duration=100, loop=0)
"
```

Design history — ten iterations:
v1 4-tier diagram (busy) → v2 abstract slab → v3 scrolling text →
v4 labeled diagram with counter (cluttered) → v5 decluttered diagram
→ v6 animated workload tracks → v7 telemetry dashboard → v8 ambient
breathing → v9 pixel-bird murmuration → **v10 (this version):
four-act narrative, "Survive & Scale"**. The lesson the iterations
teach: when "explain the architecture" doesn't fit the medium,
*tell a story whose climax is the brand*. The cup's job is to be a
surprise on a coffee table, not a slide.

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
- **Up to 132 frames** per animation on SGUAI-C3 fw 1.7. The protocol
  byte allows 255 but the cup's animation buffer caps at 132; uploads
  larger than that drop the GATT link mid-stream and leave the cup
  BLE-unreachable until physical wake (see `PROTOCOL_SPEC.md §4.6`).
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
