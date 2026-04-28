# mug — Go reimplementation of `smart_mug.py`

Single binary, no daemon, no HTTP shim. Goroutines + Go's stdlib
collapse the architecture the Python tree built up over the last 12
commits. Ships one executable that does everything the Python CLI did,
minus the now-unnecessary `repl` / `daemon` / API server layers.

## Build

```bash
cd go
go build -o mug ./cmd/mug
```

## Status

| Subcommand | Status |
|---|---|
| `info` / `read` | Done |
| `auto-off` (get/set, all 5 presets, alias names) | Done |
| `greeting` / `mode` | Done |
| `animate <gif>` (132-frame cap enforced, GIF disposal-aware) | Done |
| `reset` (with confirmation prompt) | Done |
| `alias` (full CRUD, shared `~/.smart_mug_cache.json` with Python) | Done |
| `image <file>` | Stub — use `animate` with a 1-frame GIF, or use Python's CLI for static dithering |
| `repl` / `daemon` / HTTP API | Intentionally not ported — single-process Go doesn't need them |

## Why this exists

The Python tree grew a daemon mode and a transparent CLI proxy to work
around two structural pain points:

1. **Per-command process lifecycle** — every CLI invocation forks a new
   Python process, which needs to scan and reconnect from scratch. The
   cup's silent-BLE window (`PROTOCOL_SPEC.md §4.7`) makes reconnect
   slow or impossible if the previous command was an animation.
2. **macOS BLE caching** — direct connect by address ages out faster
   than the cup's own silent-BLE window, so reconnect-by-cache fails
   too.

In Go, neither matters as much: a single short-lived `mug` process holds
the connection long enough to finish its operation and disconnect cleanly,
goroutines simplify the async/await + mutex bookkeeping that Python's
asyncio needed, and tinygo-org/bluetooth gives us the same address-based
connection API on macOS / Linux / Windows. Most users won't hit the
silent-BLE window because by the time they run the next command, the
cup has already cycled out of animation playback.

## Wire-protocol parity

All command bytes, frame builders, bitmap encoding (row-major LTR
MSB-first), and timings (rt(20) pre-throttle, rt(100) post-prologue,
rt(150) inter-frame, rt(100)/×10 retry) match the Python reference
implementation exactly. The 132-frame cup-side limit is enforced
client-side. The 6-byte `read_auto_off` form matches the APK exactly.

The firmware-version handshake fires on every connect, mirroring the
APK behavior at `app-service.pretty.js:49572-49582`.

## Behavioral differences vs Python

A few choices intentionally diverge from Python; output bitmaps for
the same source GIF will not be byte-identical between Python and Go.

- **GIF resize uses nearest-neighbor** (Python uses Lanczos). NN
  avoids anti-aliased pixels landing on the threshold boundary and
  flickering between frames; the trade-off is slightly blockier
  rescaling for small source GIFs.
- **Threshold is hardcoded to 128** for `animate`. Python's
  `--threshold` / `-t` flag is not yet ported. Use `--invert` / `-i`
  if your GIF has the wrong polarity.
- **`image` subcommand is a stub.** Use `animate` with a 1-frame GIF,
  or use Python's `smart_mug.py image` for static images that need
  Floyd-Steinberg / Atkinson dithering.

## Cross-tool compatibility

The cache file at `~/.smart_mug_cache.json` is the same on-disk format
as Python's. Aliases registered via Python's `smart_mug.py alias`
appear in Go's `mug alias` (and vice versa). Both implementations can
be in use side-by-side — no migration needed.

**Caveat: daemon state is NOT shared.** The Python implementation
writes per-port status files to `~/.smart_mug_daemons/`. The Go binary
doesn't read or write that directory, and doesn't avoid stepping on
a running Python daemon. If you have a Python daemon holding a BLE
link to cup-fw17 and run `mug animate --addr cup-fw17`, both will try
to connect to the same cup; behavior is undefined (typically: one
side wins, the other gets a connection error). Use one tool at a
time per physical cup.
