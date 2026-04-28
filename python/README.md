# SGUAI Smart Cup — Python BLE Interface

Python implementation of the SGUAI-C3 BLE protocol, reverse-engineered from
the official `net.sguai.app` Android APK. Wire format and timings match the
official app; see `../PROTOCOL_SPEC.md` for the full protocol reference.

## Install

```bash
cd python
uv sync                    # uses pyproject.toml
# or: uv pip install bleak pillow aiohttp
```

## CLI

All commands are run via `uv run smart_mug.py <command>`. The device address
is cached after first connect; pass `--rescan` to force a fresh scan.

| Command | Description |
|---|---|
| `greeting "<text>"` | Set greeting text. Empty string clears the display. UTF-16BE encoded — full Unicode including CJK and emoji (surrogate pairs). |
| `mode <name>` | Set motion: `static`, `scrollRight`, `scrollLeft`, `flashing`. |
| `image <file>` | Upload a static image. Resized to 48×12 monochrome. |
| `image --test` / `image --border` | Upload a test pattern. |
| `animate <gif>` | Upload an animated GIF (cup-side limit: 132 frames on fw 1.7). The cup stores the frames and plays them autonomously. |
| `read [field ...]` | Read `version` / `temperature` / `battery` (default: all). |
| `info` | Full snapshot — BLE address, Device Information service, all protocol reads. |
| `auto-off [<preset>]` | Get/set screen auto-off. Presets: `always`, `30s`, `1m`, `3m`, `5m`. |
| `reset [-y]` | Factory reset (DESTRUCTIVE — wipes saved animations / settings / pairing). |
| `alias [<name> <UUID>]` | Manage local cup aliases (shared with the Go binary at `~/.smart_mug_cache.json`). `--remove <name>` / `--clear` also supported. |
| `daemon [--addr X] [--port N]` | Persistent BLE-connection daemon with HTTP API. `--status` / `--stop` / `--stop --all` to manage. |
| `repl` | Interactive REPL + HTTP API on a single persistent connection. |
| `clear-cache` | Forget the cached device + aliases. |

### Common image / animation options

- `-t N` — threshold (0–255, default 128)
- `-i` — invert
- `-d` — Floyd-Steinberg dither

### Animation-specific

- `-s N` / `--speed N` — speed byte sent to the cup (default 130, see `PROTOCOL_SPEC.md` §4.6)

### Examples

```bash
uv run smart_mug.py greeting "Hello"
uv run smart_mug.py greeting "你好 🍵" --mode scrollRight
uv run smart_mug.py greeting ""                    # clear
uv run smart_mug.py mode flashing
uv run smart_mug.py image photo.png -d
uv run smart_mug.py animate fire.gif -d -s 100
uv run smart_mug.py repl --host 0.0.0.0 --port 8888
```

## REPL

`uv run smart_mug.py repl` keeps the BLE connection open across commands and
also exposes an HTTP API on the same process.

```
smart-mug> msg Hello
smart-mug> mode scrollRight
smart-mug> image photo.png -d
smart-mug> animate fire.gif -s 100
smart-mug> exit
```

## HTTP API (REPL only)

| Endpoint | Body |
|---|---|
| `GET /api/status` | — |
| `POST /api/greeting` | `{"message": "...", "mode": "scrollRight"}` (mode optional, empty message clears) |
| `POST /api/mode` | `{"mode": "static\|scrollRight\|scrollLeft\|flashing"}` |
| `POST /api/image` | `{"image": "<base64>", "threshold": 128, "invert": false, "dither": false}` |
| `POST /api/test?pattern=checkerboard\|border` | — |

Animations are CLI-only.

## Performance notes

The implementation matches the official app's wire format and timings, so
upload speeds are comparable:

- **Static image** — single 78-byte BLE write, sub-second once connected.
- **Animation** — 8-byte prologue + N × 80-byte frames at 150 ms intervals.
  A 5-frame GIF uploads in ~0.9 s; the cup then plays it autonomously
  with no further BLE traffic. (The previous implementation took ~30 s
  per frame because it waited for a notification the cup never sends.)

## Requirements

- Python 3.8+
- `bleak` (BLE), `pillow` (image processing), `aiohttp` (HTTP API in REPL)

## Troubleshooting

- **Device not found.** Power cycle the cup, close any Web Bluetooth tabs holding the connection, then `--rescan`.
- **Permission denied on Linux.** Add your user to the `bluetooth` group, or `sudo setcap 'cap_net_raw,cap_net_admin+eip' $(which python3)`.
- **macOS BLE permission prompt missed.** System Settings → Privacy & Security → Bluetooth → enable for Terminal/iTerm.
- **Animation looks scrambled on display.** This client encodes bitmaps row-major LTR for SGUAI-C3 firmware 1.6 (verified on hardware). The official APK uses column-major RTL — likely for newer firmware. If you have a newer cup and the display is scrambled, the encoder in `pack_bitmap` may need to switch to column-major RTL. See `PROTOCOL_SPEC.md` §4.5.
