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

### `tidb_envelope_animation.py` → `tidb_envelope.gif`

**TiDB Envelope of Scale** — a stats-reel animation that tells the
TiDB scalability story across six dimensions, one big number per
card. Inspired by the *Redefining Dimensions of Scalability* and
*One Year Later: Push the Envelope of Scale* slides.

74 frames at `-s 5fps` (≈15 s/loop). Each card stamps a small 5-row
label across the top and a BIG 5-col×7-row number across the bottom,
with a wipe-in / hold / wipe-out beat:

```
   intro       "TIDB SCALE" wipes in left-to-right
   DATA  PB+   petabyte+ data volume
   QPS   1M+   millions of queries / transactions per second
   TBLS  3M    three million tables in a single cluster
   FAST  50x   50× faster on table creation
   IDX/s 1M    one million rows/sec when adding index
   XREG  10x   10× throughput improvement on cross-region replication
   outro       "PUSH THE / ENVELOPE" + brand reveal "TIDB" centered
```

Every card has the same disciplined layout: rows 0-4 = small label,
rows 5-11 = big number. Counter-bit anti-dedup at row 11 cols 1-7.
No accent overlays competing with the digits; the wipe transitions
do all the motion.

```bash
uv run --with pillow python examples/tidb_envelope_animation.py
/tmp/mug animate examples/tidb_envelope.gif -s 5fps
```

### `tidb_morph.gif` (frozen snapshot)

Frozen snapshot of `tidb_morpheus.gif` at the in-place-morph coda
revision (102 frames, 88 KB).  Identical content to the live
`tidb_morpheus.gif` at this point in time, but kept as a sibling
file so the visual is preserved even if the generator script
evolves further.  Recommended pacing: `-s 5fps` for ~20 s/loop —
each beat of the in-place morph dwells long enough to read.

```bash
/tmp/mug animate examples/tidb_morph.gif -s 5fps
mug auto-off 5m   # so the cup keeps the display lit between loops
```

### `tidb_morpheus_animation.py` → `tidb_morpheus.gif`

**TiDB Morpheus** — brand metamorphosis (acts 1–7) + in-place icon
morph (acts 8–11). 102 frames at `-s 8fps` (~12 s/loop). The coda's
core idea: the brand letters *literally become* the use-case icons
in their own letter slots — T → database barrel, D → document, B →
data-node diamond — then morph back. The brand is the system.

```
   1  GLITCH BOOT     scan-line corruption tears across the brand,
                      then a vertical wipe self-repairs top→bottom
   2  CARD FLIP       each letter independently rotates around its
                      own vertical center-axis (like flipping
                      cards); cascade staggered L→R
   3  3D EXTRUSION    flat letters extrude into a wireframe 3D
                      shape — silhouette of front face + offset
                      back face + Bresenham connecting lines —
                      then rotate to reveal depth
   4  PIXEL SHATTER   every brand pixel becomes a particle with a
                      randomized outward velocity; ballistic
                      trajectories with 1-frame trails
   5  SPIRAL REFORM   particles get captured into 3 concentric
                      counter-rotating rings around the screen
                      center; rings contract over time
   6  BRAND SNAP      rings collapse into the letter pixels;
                      4-ring halo bursts outward (radii 8 → 21)
   7  BRAND HOLD      clean brand + 8-node cluster (transitional)
   8  MORPH TO ICONS  each TiDB letter dissolves IN ITS OWN POSITION
                      into a use-case icon: T → database barrel,
                      i → i (unchanged — too narrow to morph), D →
                      document with internal line, B → outlined
                      diamond.  Stochastic pixel dissolve at fixed
                      seed so every render reads as a coherent
                      transition.  10 frames.
   9  ICONS ALIVE     all 4 icons settled in the brand slots.
                      One icon pings per beat with a 1-pixel halo.
                      A single dot heartbeat walks across the
                      bottom row keeping the panel never-static.
                      8 frames.
  10  MORPH BACK      same dissolve, reversed (icons → letters,
                      same seed so the transition retraces its
                      own path).  10 frames.
  11  FINAL SETTLE    canonical brand + 8-node cluster row, the
                      loop's neutral state for the next glitch
                      boot.  3 frames.
```

**The conceptual move that finally landed**: the brand literally
*becomes* the use cases. No separate icon zone, no beam routing,
no "system over here, identity over there" duality.  Each letter
slot in the canonical "TiDB" stamp dissolves through a stochastic
pixel mix into its corresponding use-case icon, in place, at the
same x,y the letter occupied.  The viewer reads it as "TiDB *is*
the system; the letters and the use cases are the same thing
looked at differently."  Then the same dissolve reverses with the
identical RNG seed, so the morph retraces its own path on the way
back — the brand re-emerges from the same chaos that produced the
icons.  ~30 frames of coda, every frame distinguishable from the
adjacent one, every frame readable.

The protagonist of the animation is the brand itself: typed,
glitched, repaired, flipped, extruded, shattered, scattered,
gathered, and reborn — all on the same 48×12 surface, all in 9
seconds. Seven different transforms of the same identity.

```bash
uv run --with pillow python examples/tidb_morpheus_animation.py
/tmp/mug animate examples/tidb_morpheus.gif -s 8fps
```

### `tidb_hyperspace_animation.py` → `tidb_hyperspace.gif`

**TiDB Hyperspace** — a math-driven 1-bit demoscene piece. 61 frames,
~7 s/loop at `-s 8fps`. Eight overlapping effects, each transitioning
straight into the next so the panel never goes static:

```
   1  PLASMA          two-axis sin() field with rising threshold —
                      chaos resolves into a sparse pattern
   2  CUBE LIFT-OFF   the field becomes a wireframe cube
   3  CUBE SPIN       full 3D rotation around Y with perspective
                      projection (vertices closer to camera draw
                      larger), 12 Bresenham edges connect 8 corners
   4  WARP            cube vertices scatter as a parallax starfield
                      streaming outward (closer stars move faster)
   5  HYPERSPACE      stars reverse — each one targeted at a
                      specific brand-letter pixel, ease-in trajectory
                      with a 1-pixel trail behind
   6  BRAND LOCK      "TiDB" resolved; triple-ring halo expands
                      outward (radii 8, 10, 13, 17 — never cuts
                      through the letterforms)
   7  HEARTBEAT       ECG-style trace sweeps L→R below the brand;
                      8 cluster nodes pulse from dots into filled
                      diamonds on each beat
   8  SETTLE          clean brand + cluster, two hold frames
```

What makes it cool is the math: real 3D rotation matrices, real
perspective division, real parametric radial motion, real linear-
interpolated convergence — not just hand-tuned timings. The cube
is genuinely a cube in 3D space, scaled to the panel's 4:1 aspect
during projection.

```bash
uv run --with pillow python examples/tidb_hyperspace_animation.py
/tmp/mug animate examples/tidb_hyperspace.gif -s 8fps
```

### `tidb_strike_animation.py` → `tidb_strike.gif`

**TiDB Strike Force** — a 1-bit demoscene-style piece that earns the
brand reveal at its climax. 64 frames, ~8 s/loop at `-s 8fps`. Six
acts, all motion all the time:

```
   Act 1  BOOT          horizontal scanline sweeps top→bottom with
                        a phosphor afterglow trail (CRT power-on)
   Act 2  BRAND-IN      "TiDB" types in left-to-right behind a block
                        cursor; one full-screen flicker on lock
   Act 3  BOSS DESCENT  wide irregular "Legacy DB" boss looms from
                        the top, pixels boiling within (Matrix
                        data-rain), descends toward a tiny lone
                        TiDB node at the bottom
   Act 4  COUNTER FIRE  the lone node splits 1 → 2 → 4 → 8; each
                        spawn flashes a halo and fires a vertical
                        bullet trail; boss visibly shrinks
   Act 5  HTAP BARRAGE  top OLTP bullet stream + bottom OLAP laser
                        sweep crossfire pulverize what remains;
                        wireframe links pulse between nodes; final
                        hit detonates a full-screen flash
   Act 6  REFORM        explosion particles fly outward then
                        converge (linear-interpolated trajectories)
                        into the pixels of "TiDB"; halo expands;
                        cluster settles below the brand and loops
```

The "cool" comes from layered simultaneous motion: while bullets
fly, the boss internals roil; while nodes spawn, halos pulse;
during reform, particles still trace inward as the brand settles.
Nothing is static.

```bash
uv run --with pillow python examples/tidb_strike_animation.py
/tmp/mug animate examples/tidb_strike.gif -s 8fps
```

### `tidb_arcade_animation.py` → `tidb_arcade.gif`

**TiDB Arcade** — a 6-stage game-style animation that explains TiDB's
value proposition through 8-bit arcade tropes. 72 frames, ≤100 so it
fits both fw 1.6 and fw 1.7 buffers.

```
   Stage 1  TITLE        "TiDB" with arcade-corner sparkles
   Stage 2  OVERLOAD     a lone node takes fire from both sides,
                         flashes on each hit, then breaks under load
                         (the sharded-MySQL fall-over moment)
   Stage 3  POWER-UP     a "↑" descends from the top, impact halo,
                         scale-out unlocked
   Stage 4  CLUSTER      nodes spawn 1 → 2 → 4 → 8 with halo flashes
                         (horizontal scalability beat)
   Stage 5  HTAP         top row OLTP dots stream L→R while bottom
                         row OLAP sweeps cross slower; cluster nodes
                         flash when traffic crosses them
   Stage 6  VICTORY      whole-display invert sting, expanding
                         starburst, "TiDB" reveal, settles back to
                         the steady cluster and loops
```

Each visual element is a TiDB use-case in disguise: the lone node
breaking is *why sharded MySQL falls over*; the doubling cascade is
*horizontal scalability*; the top/bottom split is *HTAP — OLTP and
OLAP on the same cluster*; the boss-cleared sting is *the brand
promise: distributed SQL that makes the boss fight winnable*.

A 7-bit binary counter ticks across cols 1–7 of the bottom row to
guarantee per-frame uniqueness — without it PIL's GIF encoder merges
consecutive identical frames (e.g. settle holds, sting beats) and
the cup plays a shortened sequence at the wrong pace. Reads as a
small arcade scoreboard ticker.

Pacing: at `-s 8fps` (≈125 ms/frame) the loop runs ~9 s, brisk
arcade tempo. At `-s medium` (≈250 ms/frame) it stretches to ~18 s
and each stage's beats land deliberately. Up to you.

```bash
# Generate (overwrites tidb_arcade.gif next to this script):
uv run --with pillow python examples/tidb_arcade_animation.py

# Send to cup at brisk arcade pace:
/tmp/mug animate examples/tidb_arcade.gif -s 8fps
# ...or slower so each stage breathes:
/tmp/mug animate examples/tidb_arcade.gif -s medium
```

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
