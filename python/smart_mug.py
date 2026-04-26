#!/usr/bin/env python3
"""
SGUAI Smart Cup - Python BLE Interface

Complete BLE communication library for SGUAI-C3 smart cup.
"""

import asyncio
import base64
import io
import json
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from bleak import BleakClient, BleakScanner

try:
    from aiohttp import web
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

try:
    from PIL import Image, ImageOps, ImageSequence
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Set SMART_MUG_DEBUG=1 to print every BLE notification.
DEBUG = os.environ.get("SMART_MUG_DEBUG") == "1"


def _warn(msg):
    """Print a warning to stderr so stdout pipelines (e.g. `... | jq`) are
    not polluted."""
    print(f"Warning: {msg}", file=sys.stderr)

# BLE Configuration
SERVICE_UUID = "0000ff00-0000-1000-8000-00805f9b34fb"
COMMAND_CHAR_UUID = "0000ff01-0000-1000-8000-00805f9b34fb"
RESPONSE_CHAR_UUID = "0000ff02-0000-1000-8000-00805f9b34fb"
DEVICE_NAME = "SGUAI-C3"
IMAGE_WIDTH = 48
IMAGE_HEIGHT = 12

# Timings copied from the official app (net.sguai.app):
#   - rt(20) before every GET_BLE_WRITE             -> WRITE_THROTTLE_S
#   - setTimeout(..., 100) after the prologue       -> ANIM_PROLOGUE_DELAY_S
#   - setTimeout(..., 150) between successful frames-> ANIM_FRAME_DELAY_S
#   - setTimeout(..., 100) on per-frame retry       -> ANIM_RETRY_BACKOFF_S
#   - failNum >= 10 caps retries                    -> ANIM_MAX_RETRIES
#   - setBLEMTU({mtu: 500}) on Android post-connect -> REQUESTED_MTU
WRITE_THROTTLE_S = 0.02
ANIM_PROLOGUE_DELAY_S = 0.10
ANIM_FRAME_DELAY_S = 0.15
ANIM_RETRY_BACKOFF_S = 0.10
ANIM_MAX_RETRIES = 10
REQUESTED_MTU = 500

# Cache file path
CACHE_FILE = Path.home() / ".smart_mug_cache.json"


def _load_cache():
    try:
        return json.loads(CACHE_FILE.read_text())
    except (OSError, ValueError):
        return {}


def _save_cache(address, name):
    try:
        CACHE_FILE.write_text(json.dumps({"address": address, "name": name}))
    except OSError as e:
        _warn(f"could not save cache: {e}")


class BLEManager:
    """BLE Manager for SGUAI-C3 Smart Cup. Serializes all writes via an
    asyncio.Lock so concurrent callers (e.g. HTTP handlers) can't interleave
    GATT writes."""

    def __init__(self, device_name=DEVICE_NAME):
        self.client = None
        self.device_name = device_name
        self.response_data = None
        self.response_event = None
        self._lock = asyncio.Lock()

    def response_handler(self, sender, data):
        if DEBUG:
            print(f"[debug] notify: {list(data)}")
        self.response_data = data
        if self.response_event:
            self.response_event.set()

    @staticmethod
    def clear_cached_device():
        try:
            CACHE_FILE.unlink()
            print("Device cache cleared")
        except FileNotFoundError:
            pass
        except OSError as e:
            _warn(f"could not clear cache: {e}")

    async def find_device(self, use_cache=True):
        """Locate the cup. Tries the cached address first (5 s scan), then
        falls back to a 15 s scan with auto-select on name match."""
        if use_cache:
            cache = _load_cache()
            cached_addr = cache.get("address")
            if cached_addr:
                print(f"Cached device: {cache.get('name')} ({cached_addr})")
                try:
                    for d in await BleakScanner.discover(timeout=5.0):
                        if d.address == cached_addr:
                            print("✓ Cached device available")
                            return d
                except Exception as e:
                    print(f"⚠ Cache scan failed ({type(e).__name__}); rescanning...")
                else:
                    print("⚠ Cached device not found; rescanning...")

        print("Scanning for BLE devices...")
        devices = [d for d in await BleakScanner.discover(timeout=15.0) if d.name]
        if not devices:
            raise Exception("No named BLE devices found")

        print(f"\nFound {len(devices)} named devices:")
        for i, d in enumerate(devices):
            print(f"  {i+1}. {d.name} ({d.address})")

        for d in devices:
            if d.name == self.device_name or d.name.startswith(self.device_name):
                print(f"\nAuto-selected: {d.name}")
                _save_cache(d.address, d.name)
                return d

        try:
            choice = int(input(f"\nEnter device number (1-{len(devices)}): ").strip())
        except ValueError:
            raise Exception("Invalid device selection")
        if not 1 <= choice <= len(devices):
            raise Exception("Selection out of range")
        selected = devices[choice - 1]
        _save_cache(selected.address, selected.name)
        return selected

    async def connect(self, device):
        """Connect to device"""
        print(f"Connecting to {device.address}...")
        self.client = BleakClient(device)
        await self.client.connect()
        await asyncio.sleep(1)

        # Verify service exists
        service_found = False
        for service in self.client.services:
            if service.uuid.lower() == SERVICE_UUID.lower():
                service_found = True
                print("✓ Found target service")
                break

        if not service_found:
            raise Exception(f"Service {SERVICE_UUID} not found")

        # Official Android app calls setBLEMTU(500) post-connect. bleak's
        # only equivalent is BlueZ-internal (`_acquire_mtu`); macOS / WinRT
        # auto-negotiate during service discovery and expose no override.
        try:
            backend = getattr(self.client, "_backend", None)
            if backend is not None and hasattr(backend, "_acquire_mtu"):
                await backend._acquire_mtu()
        except Exception:
            pass
        mtu = getattr(self.client, "mtu_size", None)
        if mtu:
            print(f"✓ MTU: {mtu} (official app requests {REQUESTED_MTU})")

        # Enable notifications
        await self.client.start_notify(RESPONSE_CHAR_UUID, self.response_handler)
        print("✓ Connected successfully")
        return True

    async def disconnect(self):
        """Disconnect from device. The BlueZ backend occasionally raises
        EOFError on disconnect when the device is already gone; harmless."""
        if not self.client:
            return
        try:
            if self.client.is_connected:
                try:
                    await self.client.stop_notify(RESPONSE_CHAR_UUID)
                except Exception:
                    pass
                await self.client.disconnect()
            print("Disconnected")
        except Exception as e:
            print(f"Disconnected (with warning: {type(e).__name__})")

    def _ensure_connected(self):
        if not self.client or not self.client.is_connected:
            raise Exception("Not connected")

    async def _write(self, command_data, *, throttle=True):
        """Write-with-response. With `throttle=True` (default) applies the
        20 ms pre-guard that the official `GET_BLE_WRITE` action uses;
        per-frame animation writes pass `throttle=False`."""
        self._ensure_connected()
        if throttle:
            await asyncio.sleep(WRITE_THROTTLE_S)
        await self.client.write_gatt_char(
            COMMAND_CHAR_UUID, bytes(command_data), response=True
        )

    async def _write_frame_with_retry(self, command_data):
        """Animation per-frame write. Mirrors the official's recursive
        `writeBLECharacteristicValue`: up to ANIM_MAX_RETRIES attempts,
        ANIM_RETRY_BACKOFF_S between failures, no pre-guard."""
        for attempt in range(ANIM_MAX_RETRIES):
            try:
                await self._write(command_data, throttle=False)
                return
            except Exception:
                if attempt == ANIM_MAX_RETRIES - 1:
                    raise
                await asyncio.sleep(ANIM_RETRY_BACKOFF_S)

    async def _execute_locked(self, command_data, timeout):
        """Body of execute_command. Caller must hold self._lock."""
        self._ensure_connected()
        self.response_data = None
        self.response_event = asyncio.Event()
        await self._write(command_data)
        await asyncio.wait_for(self.response_event.wait(), timeout=timeout)
        arr = bytearray(self.response_data)
        if len(arr) >= 3 and arr[0] == 0xFF and arr[-2] == 0x0D and arr[-1] == 0x0A:
            return arr[2:-2]
        return arr

    async def execute_command(self, command_data, timeout=5.0):
        """Write a command and wait up to `timeout` s for a notification.
        Used for commands the official's receive parser handles (mode echo,
        reads, etc.). Applies the 20 ms pre-guard and acquires the lock."""
        async with self._lock:
            return await self._execute_locked(command_data, timeout)

    @staticmethod
    def _bitmap_payload(grid_or_bytes, label="bitmap"):
        if isinstance(grid_or_bytes, list) and grid_or_bytes and isinstance(grid_or_bytes[0], list):
            return pack_bitmap(grid_or_bytes)
        payload = bytes(grid_or_bytes)
        if len(payload) != 72:
            raise ValueError(f"{label} must be 72 bytes, got {len(payload)}")
        return payload

    async def set_greeting_message(self, message):
        """Set greeting text. Empty string clears the display.

        Matches the official page-level path (sub-service.pretty.js:4083-88):
        direct write — no 20 ms guard, no notification wait (the receive
        parser has no 0x17 handler). Encoding is UTF-16 big-endian, matching
        the official's `charCodeAt` iteration including surrogate pairs."""
        message = message or ""
        subcmd = 0x01 if message else 0x00
        command = [0xFF, 0x55, 0x00, 0x00, 0x02, 0x17, subcmd]
        command.extend(message.encode("utf-16-be"))
        command[2] = len(command)
        async with self._lock:
            await self._write(command, throttle=False)
        return True

    async def set_dynamic_mode(self, mode):
        """Set display motion: static / scrollRight / scrollLeft / flashing."""
        mode_map = {"static": 0, "scrollRight": 1, "scrollLeft": 2, "flashing": 3}
        if mode not in mode_map:
            raise ValueError(f"Invalid mode. Use: {list(mode_map)}")
        command = [0xFF, 0x55, 0x07, 0x00, 0x02, 0x23, mode_map[mode]]
        async with self._lock:
            try:
                await self._execute_locked(command, timeout=10.0)
            except asyncio.TimeoutError:
                # Cup occasionally drops the echo notification; the write
                # itself was ACKed at the BLE layer so the mode is set.
                pass
        return True

    async def set_image_data(self, image_data):
        """Upload a static image. Sends FF 55 4E 00 02 25 + 72-byte bitmap.
        Fire-and-forget — the receive parser has no 0x25 handler."""
        payload = self._bitmap_payload(image_data, "image payload")
        command = [0xFF, 0x55, 0x00, 0x00, 0x02, 0x25] + list(payload)
        command[2] = len(command)  # 0x4E (78)
        async with self._lock:
            await self._write(command)
        return True

    async def set_animation(self, frames, speed=130):
        """Upload an animation. The cup stores the frames and plays them
        autonomously after upload completes — no BLE traffic during playback.

        Wire protocol (matches official app):
          Prologue: FF 55 08 00 02 26 <count> <speed>
          Frame N : FF 55 50 00 02 26 <idx>   <speed> <72-byte bitmap>

        Timing matches the official app: 20 ms pre-guard on the prologue,
        100 ms post-prologue, 150 ms between successful frames, 10× retry
        with 100 ms backoff on per-frame failure.

        :param frames: list of 12×48 grids (0/1 ints) or list of 72-byte
            bytes objects. Each frame is pre-validated *before* the prologue
            is sent so a bad frame can't leave the cup half-loaded.
        :param speed: 1..255, larger = faster. 0 produces unspecified
            behavior on the cup. Default 130 matches the official app's
            `speedValue` and produces ~1 second per 4-frame cycle (exact
            unit not yet quantified — see PROTOCOL_SPEC.md §4.6).
        """
        if not frames:
            raise ValueError("At least one frame required")
        if len(frames) > 255:
            raise ValueError("Max 255 frames")
        if not 1 <= speed <= 255:
            raise ValueError("speed must be 1..255 (0 is unspecified by firmware)")

        # Pre-pack all payloads BEFORE acquiring the mutex / sending the
        # prologue. A bad frame mid-upload would leave the cup expecting
        # more frames than it gets — corrupted animation state.
        payloads = []
        for idx, frame in enumerate(frames):
            try:
                payloads.append(self._bitmap_payload(frame, f"frame {idx}"))
            except ValueError as e:
                raise ValueError(f"frame {idx}: {e}") from e

        async with self._lock:
            n = len(frames)
            await self._write([0xFF, 0x55, 0x08, 0x00, 0x02, 0x26, n, speed])
            await asyncio.sleep(ANIM_PROLOGUE_DELAY_S)

            for idx, payload in enumerate(payloads):
                cmd = [0xFF, 0x55, 0x00, 0x00, 0x02, 0x26, idx, speed] + list(payload)
                cmd[2] = len(cmd)  # 0x50 (80)
                await self._write_frame_with_retry(cmd)
                if idx < n - 1:
                    await asyncio.sleep(ANIM_FRAME_DELAY_S)
        return True

    # ------------------------------------------------------------------
    # Read commands — convenience wrappers around execute_command for
    # the read paths the cup's receive parser handles.
    # ------------------------------------------------------------------

    def is_connected(self):
        """True when the underlying BleakClient is connected."""
        return self.client is not None and self.client.is_connected

    async def read_temperature(self):
        """Read the cup's current liquid temperature (°C, unsigned byte)."""
        resp = await self.execute_command([0xFF, 0x55, 0x07, 0x00, 0x01, 0x01, 0x00])
        return resp[-1]

    async def read_battery(self):
        """Read the cup's battery level (percent, 0..100)."""
        resp = await self.execute_command([0xFF, 0x55, 0x07, 0x00, 0x01, 0x02, 0x00])
        return resp[-1]

    async def read_version(self):
        """Read the cup's firmware version as 'major.minor' (e.g. '1.6').

        The cup returns 4 payload bytes after the feature byte; the official
        parser at app-service.pretty.js:53402 reads the last two for the
        major.minor pair (with the trailer already stripped)."""
        resp = await self.execute_command([0xFF, 0x55, 0x07, 0x00, 0x01, 0x09, 0x00])
        if len(resp) >= 2:
            return f"{resp[-2]}.{resp[-1]}"
        return ".".join(str(b) for b in resp)


# Image Processing

def pack_bitmap(image_data):
    """Pack a 48x12 grid into 72 bytes for the cup's framebuffer.

    Encoding: **row-major left-to-right, top-to-bottom, MSB-first within
    each byte**. Verified empirically on SGUAI-C3 firmware 1.6 (2026-04):
    a single pixel at grid[0][0] lights the physical top-left LED, and an
    asymmetric "F" shape renders right-side-up.

    Note: the official `net.sguai.app` Android APK ships a *column-major
    right-to-left* encoder at `app-sub-service.pretty.js:10113-10135`.
    That encoder is byte-incompatible with this firmware — sending its
    output produces a scrambled display (bit index N lands at row N÷48,
    col N mod 48). The APK's encoder presumably targets newer firmware
    (likely C3 fw ≥ 2.x or the C5 family). See PROTOCOL_SPEC.md §4.5."""
    if len(image_data) != IMAGE_HEIGHT or any(len(r) != IMAGE_WIDTH for r in image_data):
        raise ValueError(
            f"grid must be {IMAGE_HEIGHT}×{IMAGE_WIDTH}, got "
            f"{len(image_data)}×{len(image_data[0]) if image_data else 0}"
        )

    out = bytearray(72)
    i = 0
    for row in range(IMAGE_HEIGHT):
        for col in range(IMAGE_WIDTH):
            if image_data[row][col]:
                out[i // 8] |= 1 << (7 - (i % 8))
            i += 1
    return bytes(out)


def _pil_frame_to_grid(frame, threshold, invert, dither):
    img = frame.convert('L').resize((IMAGE_WIDTH, IMAGE_HEIGHT), Image.Resampling.LANCZOS)
    if dither:
        img = img.convert('1', dither=Image.Dither.FLOYDSTEINBERG)
    else:
        img = img.point(lambda x: 0 if x < threshold else 255, '1')
    if invert:
        img = ImageOps.invert(img.convert('L')).convert('1')
    pixels = list(img.getdata())
    return [[0 if pixels[r * IMAGE_WIDTH + c] == 255 else 1
             for c in range(IMAGE_WIDTH)]
            for r in range(IMAGE_HEIGHT)]


def load_and_convert_image(path, threshold=128, invert=False, dither=False):
    """Convert image to 48x12 monochrome (single frame)"""
    if not PIL_AVAILABLE:
        raise Exception("Pillow not installed: uv pip install pillow")
    img = Image.open(path)
    return _pil_frame_to_grid(img, threshold, invert, dither)


def load_animation_frames(path, threshold=128, invert=False, dither=False, max_frames=255):
    """Load animation frames from a GIF (or any multi-frame image).

    Uses `ImageSequence.Iterator` so GIF disposal methods are applied
    correctly — optimized GIFs that store each frame as a delta of the
    previous compose properly. The simpler `seek` / `EOFError` pattern
    captures only the dirty-rectangle pixels and produces garbage on
    most real-world GIFs."""
    if not PIL_AVAILABLE:
        raise Exception("Pillow not installed: uv pip install pillow")
    img = Image.open(path)
    frames = []
    for frame in ImageSequence.Iterator(img):
        frames.append(_pil_frame_to_grid(frame, threshold, invert, dither))
        if len(frames) >= max_frames:
            break
    if not frames:
        raise ValueError("No frames found")
    return frames


def create_test_pattern():
    """Checkerboard pattern"""
    return [[1 if (r+c)%2==0 else 0 for c in range(IMAGE_WIDTH)]
            for r in range(IMAGE_HEIGHT)]


def create_border_pattern():
    """Border pattern"""
    return [[1 if r==0 or r==IMAGE_HEIGHT-1 or c==0 or c==IMAGE_WIDTH-1 else 0
             for c in range(IMAGE_WIDTH)]
            for r in range(IMAGE_HEIGHT)]


def print_preview(image_data):
    """ASCII preview"""
    print("\n┌" + "─"*IMAGE_WIDTH + "┐")
    for row in image_data:
        print("│" + "".join("█" if p else " " for p in row) + "│")
    print("└" + "─"*IMAGE_WIDTH + "┘")


# HTTP API Server

def _json_endpoint(handler):
    """Wrap a handler so any exception becomes a 500 JSON error response.
    Handlers may raise web.HTTPException directly for non-500 errors."""
    async def wrapped(self, request):
        try:
            return await handler(self, request)
        except web.HTTPException:
            raise
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    return wrapped


class APIServer:
    """Small REST shim around BLEManager (used by the REPL)."""

    def __init__(self, manager, host='0.0.0.0', port=8080):
        self.manager = manager
        self.host = host
        self.port = port
        self.app = None
        self.runner = None

    @_json_endpoint
    async def handle_greeting(self, request):
        """POST /api/greeting — set greeting (empty string clears)."""
        data = await request.json()
        if 'message' not in data:
            return web.json_response({'error': 'message field required'}, status=400)
        message = data['message']
        mode = data.get('mode')
        await self.manager.set_greeting_message(message)
        if mode:
            await self.manager.set_dynamic_mode(mode)
        return web.json_response({'status': 'success', 'message': message, 'mode': mode})

    @_json_endpoint
    async def handle_mode(self, request):
        """POST /api/mode — static | scrollRight | scrollLeft | flashing."""
        data = await request.json()
        mode = data.get('mode')
        if not mode:
            return web.json_response({'error': 'mode required'}, status=400)
        await self.manager.set_dynamic_mode(mode)
        return web.json_response({'status': 'success', 'mode': mode})

    @_json_endpoint
    async def handle_image(self, request):
        """POST /api/image — upload a base64 image as a static frame."""
        data = await request.json()
        image_b64 = data.get('image')
        if not image_b64:
            return web.json_response({'error': 'image (base64) required'}, status=400)
        img = Image.open(io.BytesIO(base64.b64decode(image_b64)))
        grid = _pil_frame_to_grid(
            img,
            threshold=data.get('threshold', 128),
            invert=data.get('invert', False),
            dither=data.get('dither', False),
        )
        await self.manager.set_image_data(grid)
        return web.json_response({'status': 'success'})

    @_json_endpoint
    async def handle_test(self, request):
        """POST /api/test?pattern=checkerboard|border."""
        pattern = request.query.get('pattern', 'checkerboard')
        grid = create_border_pattern() if pattern == 'border' else create_test_pattern()
        await self.manager.set_image_data(grid)
        return web.json_response({'status': 'success', 'pattern': pattern})

    async def handle_status(self, request):
        """GET /api/status - Get connection status"""
        is_connected = self.manager.client and self.manager.client.is_connected
        return web.json_response({
            'connected': is_connected,
            'device': self.manager.device_name
        })

    async def handle_index(self, request):
        html = """<!DOCTYPE html>
<html><head><title>Smart Mug API</title></head><body>
<h1>Smart Mug REST API</h1>
<h2>Endpoints</h2>
<ul>
  <li><b>GET /api/status</b> — connection status</li>
  <li><b>POST /api/greeting</b> — set greeting text (empty string clears).
      Body: <code>{"message": "text", "mode": "scrollRight"}</code> (mode optional)</li>
  <li><b>POST /api/mode</b> — set display motion mode.
      Body: <code>{"mode": "static|scrollRight|scrollLeft|flashing"}</code></li>
  <li><b>POST /api/image</b> — upload a static image.
      Body: <code>{"image": "base64...", "threshold": 128, "invert": false, "dither": false}</code></li>
  <li><b>POST /api/test</b> — upload a test pattern.
      Query: <code>?pattern=checkerboard|border</code></li>
</ul>
<h2>Examples</h2>
<pre>
curl -X POST http://localhost:8080/api/greeting \\
     -H 'Content-Type: application/json' \\
     -d '{"message": "Hello"}'

curl -X POST http://localhost:8080/api/mode \\
     -H 'Content-Type: application/json' \\
     -d '{"mode": "scrollRight"}'

curl -X POST 'http://localhost:8080/api/test?pattern=border'
</pre>
<p>Animations are CLI-only: <code>uv run smart_mug.py animate file.gif</code></p>
</body></html>"""
        return web.Response(text=html, content_type='text/html')

    async def start(self):
        if not AIOHTTP_AVAILABLE:
            print("⚠️  aiohttp not installed (run: uv pip install aiohttp)")
            return False
        self.app = web.Application()
        self.app.router.add_get('/', self.handle_index)
        self.app.router.add_get('/api/status', self.handle_status)
        self.app.router.add_post('/api/greeting', self.handle_greeting)
        self.app.router.add_post('/api/mode', self.handle_mode)
        self.app.router.add_post('/api/image', self.handle_image)
        self.app.router.add_post('/api/test', self.handle_test)
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        await web.TCPSite(self.runner, self.host, self.port).start()

        display_host = 'localhost' if self.host == '0.0.0.0' else self.host
        suffix = " (network-accessible)" if self.host == '0.0.0.0' else ""
        print(f"🌐 HTTP API: http://{display_host}:{self.port}{suffix}")
        return True

    async def stop(self):
        if self.runner:
            await self.runner.cleanup()
            print("🌐 HTTP API stopped")


# CLI Commands

@asynccontextmanager
async def connected_manager(args):
    """Open a connected BLEManager, yield it, then disconnect cleanly.
    Honors `--rescan` in args. Use as: `async with connected_manager(args) as m:`."""
    manager = BLEManager()
    try:
        device = await manager.find_device(use_cache="--rescan" not in args)
        await manager.connect(device)
        yield manager
    finally:
        await manager.disconnect()


# Flags that don't belong to any cmd-specific parser but appear in CLI args.
# Listed here so _parse_image_opts knows to consume them silently rather than
# warning, and `_first_positional` knows how many args to skip past.
_KNOWN_GLOBAL_FLAGS = {"--rescan", "--host", "--port", "--mode"}
_GLOBAL_FLAGS_WITH_VALUE = {"--mode", "--host", "--port"}

VALID_MODES = ("static", "scrollRight", "scrollLeft", "flashing")


def _flag(args, name, default, cast=str):
    """Return the value following `--name` in args, or default."""
    if name in args:
        i = args.index(name)
        if i + 1 < len(args):
            try:
                return cast(args[i + 1])
            except ValueError:
                pass
    return default


def _first_positional(args):
    """Return the first non-flag arg in `args`, skipping flags and any value
    that follows a known value-taking flag. Returns None if no positional."""
    i = 0
    while i < len(args):
        a = args[i]
        if not a.startswith("-"):
            return a
        if a in _GLOBAL_FLAGS_WITH_VALUE:
            i += 2
        else:
            i += 1
    return None


def _parse_int_arg(args, i, name):
    """Parse args[i+1] as int with a clear error message. Returns (value, new_i)."""
    if i + 1 >= len(args):
        _warn(f"ignoring {name} (missing integer value)")
        return None, i + 1
    raw = args[i + 1]
    try:
        return int(raw), i + 2
    except ValueError:
        _warn(f"ignoring {name} {raw!r} (expected integer)")
        return None, i + 2


def _parse_image_opts(args):
    """Parse the shared image options (-t N, -i, -d, -s/--speed N, --test,
    --border) plus a positional file path. Returns
    (path, threshold, invert, dither, speed, test_pattern). Unknown flags
    print a warning so typos like `--diter` don't get silently dropped."""
    threshold, invert, dither, speed = 128, False, False, 130
    path, test_pattern = None, None
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("-t", "--threshold"):
            v, i = _parse_int_arg(args, i, a)
            if v is not None:
                threshold = v
        elif a in ("-i", "--invert"):
            invert = True; i += 1
        elif a in ("-d", "--dither"):
            dither = True; i += 1
        elif a in ("-s", "--speed"):
            v, i = _parse_int_arg(args, i, a)
            if v is not None:
                speed = v
        elif a == "--test":
            test_pattern = "checkerboard"; i += 1
        elif a == "--border":
            test_pattern = "border"; i += 1
        elif not a.startswith("-"):
            path = a; i += 1
        else:
            if a not in _KNOWN_GLOBAL_FLAGS:
                _warn(f"ignoring unknown flag {a!r}")
            i += 2 if a in _GLOBAL_FLAGS_WITH_VALUE and i + 1 < len(args) else 1
    return path, threshold, invert, dither, speed, test_pattern


async def cmd_greeting(args):
    message = _first_positional(args)
    if message is None:
        print("Error: message required (use \"\" to clear)")
        return 1
    mode = _flag(args, "--mode", None)
    if mode is not None and mode not in VALID_MODES:
        print(f"Error: invalid mode {mode!r}. Use: {list(VALID_MODES)}")
        return 1
    try:
        async with connected_manager(args) as m:
            print(f"\nSending: {message!r}")
            await m.set_greeting_message(message)
            print("✓ Message sent")
            if mode:
                print(f"Setting mode: {mode}")
                await m.set_dynamic_mode(mode)
                print("✓ Mode set")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


async def cmd_mode(args):
    mode = _first_positional(args)
    if mode is None:
        print(f"Error: mode required ({'/'.join(VALID_MODES)})")
        return 1
    if mode not in VALID_MODES:
        print(f"Error: invalid mode {mode!r}. Use: {list(VALID_MODES)}")
        return 1
    try:
        async with connected_manager(args) as m:
            await m.set_dynamic_mode(mode)
            print("✓ Mode set")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


async def cmd_image(args):
    path, threshold, invert, dither, _, test_pattern = _parse_image_opts(args)
    if test_pattern == "checkerboard":
        image_data = create_test_pattern()
    elif test_pattern == "border":
        image_data = create_border_pattern()
    elif path:
        image_data = load_and_convert_image(path, threshold, invert, dither)
    else:
        print("Error: specify image file or --test/--border")
        return 1

    print_preview(image_data)
    if input("\nUpload? (y/n): ").strip().lower() != "y":
        return 0

    try:
        async with connected_manager(args) as m:
            print("\nUploading...")
            await m.set_image_data(image_data)
            print("✓ Upload complete")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


async def cmd_animate(args):
    path, threshold, invert, dither, speed, _ = _parse_image_opts(args)
    if not path:
        print("Error: specify a GIF (or other multi-frame image) file")
        return 1
    if not 1 <= speed <= 255:
        print(f"Error: speed must be 1..255, got {speed}")
        return 1

    print(f"Loading frames from {path}...")
    frames = load_animation_frames(path, threshold, invert, dither)
    print(f"✓ {len(frames)} frame(s) loaded")
    for idx, frame in enumerate(frames[:3]):
        print(f"\nFrame {idx}:")
        print_preview(frame)
    if len(frames) > 3:
        print(f"... ({len(frames) - 3} more)")

    try:
        async with connected_manager(args) as m:
            print(f"\nUploading {len(frames)} frame(s) at speed={speed}...")
            await m.set_animation(frames, speed=speed)
            print("✓ Animation uploaded — cup is now playing autonomously")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


async def cmd_read(args):
    """Read one or more device fields. Useful for diagnostics."""
    fields = [a for a in args if not a.startswith("-")]
    if not fields:
        fields = ["version", "temperature", "battery"]  # default: read all
    valid = {"version", "temperature", "temp", "battery", "all"}
    if "all" in fields:
        fields = ["version", "temperature", "battery"]
    bad = [f for f in fields if f not in valid]
    if bad:
        print(f"Error: unknown field(s) {bad}. Valid: version, temperature, battery, all")
        return 1
    try:
        async with connected_manager(args) as m:
            for f in fields:
                if f == "version":
                    print(f"version:     {await m.read_version()}")
                elif f in ("temperature", "temp"):
                    print(f"temperature: {await m.read_temperature()} °C")
                elif f == "battery":
                    print(f"battery:     {await m.read_battery()} %")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


REPL_HELP = """
REPL commands:
  msg <text>           Send greeting (empty after `msg ` clears)
  mode <name>          static | scrollRight | scrollLeft | flashing
  image <file> [opts]  Upload image (-t N, -i, -d)
  animate <gif> [opts] Upload animation (-t N, -i, -d, -s SPEED)
  test                 Upload checkerboard test pattern
  read [field ...]     Read version / temperature / battery (default: all)
  status               Alias for `read all`
  help                 Show this help
  exit | quit          Leave the REPL
"""


async def _repl_dispatch(manager, cmd, cmd_args):
    """Run one REPL command. Raises on caller errors; logs handler errors."""
    if cmd in ("msg", "message", "greeting"):
        message = " ".join(cmd_args)
        print(f"📤 Sending: {message!r}")
        await manager.set_greeting_message(message)
        print("✓ Sent")
    elif cmd == "mode":
        if not cmd_args:
            print("❌ mode required"); return
        print(f"🔄 Setting mode: {cmd_args[0]}")
        await manager.set_dynamic_mode(cmd_args[0])
        print("✓ Mode set")
    elif cmd == "test":
        grid = create_test_pattern()
        print_preview(grid)
        await manager.set_image_data(grid)
        print("✓ Uploaded")
    elif cmd == "image":
        path, threshold, invert, dither, _, test_pattern = _parse_image_opts(cmd_args)
        if test_pattern == "checkerboard":
            grid = create_test_pattern()
        elif test_pattern == "border":
            grid = create_border_pattern()
        elif path:
            grid = load_and_convert_image(path, threshold, invert, dither)
        else:
            print("❌ image file or --test/--border required"); return
        print_preview(grid)
        print("Uploading...")
        await manager.set_image_data(grid)
        print("✓ Uploaded")
    elif cmd in ("animate", "anim", "gif"):
        path, threshold, invert, dither, speed, _ = _parse_image_opts(cmd_args)
        if not path:
            print("❌ GIF file required"); return
        frames = load_animation_frames(path, threshold, invert, dither)
        print(f"✓ {len(frames)} frame(s)")
        if frames:
            print_preview(frames[0])
        print(f"Uploading at speed={speed}...")
        await manager.set_animation(frames, speed=speed)
        print("✓ Animation uploaded — playing autonomously")
    elif cmd in ("read", "status"):
        fields = [a for a in cmd_args if not a.startswith("-")]
        if not fields or "all" in fields or cmd == "status":
            fields = ["version", "temperature", "battery"]
        for f in fields:
            try:
                if f == "version":
                    print(f"  version:     {await manager.read_version()}")
                elif f in ("temperature", "temp"):
                    print(f"  temperature: {await manager.read_temperature()} °C")
                elif f == "battery":
                    print(f"  battery:     {await manager.read_battery()} %")
                else:
                    print(f"  ❌ unknown field {f!r} (version/temperature/battery)")
            except Exception as e:
                print(f"  ❌ {f}: {type(e).__name__}: {e}")
    elif cmd == "help":
        print(REPL_HELP)
    else:
        print(f"❌ Unknown command: {cmd!r} (try 'help')")


async def cmd_repl(args):
    """Interactive REPL with a persistent BLE connection and HTTP API."""
    host = _flag(args, "--host", "0.0.0.0")
    port = _flag(args, "--port", 8080, int)
    api_server = None

    try:
        async with connected_manager(args) as manager:
            print("✓ Connected! Entering REPL mode.\n")

            api_server = APIServer(manager, host=host, port=port)
            if await api_server.start():
                print("💡 Device is now also reachable via HTTP API")

            print(REPL_HELP)

            while True:
                try:
                    line = input("smart-mug> ").strip()
                except KeyboardInterrupt:
                    print("\n(use 'exit' or 'quit' to leave)")
                    continue
                except EOFError:
                    print("\n👋 Goodbye!")
                    break
                if not line:
                    continue

                parts = line.split()
                cmd = parts[0].lower()
                if cmd in ("exit", "quit", "q"):
                    print("👋 Goodbye!")
                    break

                try:
                    await _repl_dispatch(manager, cmd, parts[1:])
                except Exception as e:
                    print(f"❌ {type(e).__name__}: {e}")
        return 0
    except Exception as e:
        print(f"❌ {type(e).__name__}: {e}")
        return 1
    finally:
        if api_server:
            await api_server.stop()


def print_help():
    print("""
SGUAI Smart Cup - Python BLE Interface

Commands:
  greeting <msg> [--mode MODE] [--rescan]     Set greeting (empty msg clears)
  mode <mode> [--rescan]                      Set display mode
  image <file> [opts] [--rescan]              Upload static image
  image --test [--rescan]                     Upload test pattern
  animate <gif> [opts] [-s SPEED] [--rescan]  Upload animation (cup plays it)
  read [field ...] [--rescan]                 Read version / temperature / battery
  repl [--rescan] [--host HOST] [--port PORT] Interactive REPL + HTTP API
  clear-cache                                 Forget cached device

Examples:
  uv run smart_mug.py greeting "Hello"
  uv run smart_mug.py greeting "你好 🍵" --mode scrollRight
  uv run smart_mug.py mode flashing
  uv run smart_mug.py image photo.png -d
  uv run smart_mug.py animate fire.gif -d -s 100
  uv run smart_mug.py read temperature battery
  uv run smart_mug.py read                    (= all three fields)
  uv run smart_mug.py repl --host 0.0.0.0 --port 8888

Modes:        static | scrollRight | scrollLeft | flashing
Read fields:  version | temperature | battery | all (default: all)
Image opts:   -t N (threshold 0-255), -i (invert), -d (Floyd-Steinberg dither)
Animate opts: image opts + -s/--speed N (1-255, larger = faster, default 130)

Global flags:
  --rescan       Force a fresh BLE scan (ignore cached device)
  --host HOST    HTTP API host (REPL only, default 0.0.0.0)
  --port PORT    HTTP API port (REPL only, default 8080)

The device address is cached on first connect; REPL keeps the connection
open across commands.
""")


async def main():
    if len(sys.argv) < 2 or sys.argv[1] in ['-h', '--help']:
        print_help()
        return 0

    cmd = sys.argv[1]
    if cmd == 'greeting':
        return await cmd_greeting(sys.argv[2:])
    elif cmd == 'mode':
        return await cmd_mode(sys.argv[2:])
    elif cmd == 'image':
        return await cmd_image(sys.argv[2:])
    elif cmd in ('animate', 'anim', 'gif'):
        return await cmd_animate(sys.argv[2:])
    elif cmd == 'read':
        return await cmd_read(sys.argv[2:])
    elif cmd == 'repl':
        return await cmd_repl(sys.argv[2:])
    elif cmd == 'clear-cache':
        BLEManager.clear_cached_device()
        return 0
    else:
        print(f"Unknown command: {cmd}")
        print_help()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
