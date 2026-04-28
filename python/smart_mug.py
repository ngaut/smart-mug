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
import signal
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
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
    """Load the local cache. Returns a dict with shape::

        {
          "address": "<UUID>",       # last-used address (legacy, kept for
          "name":    "<ble-name>",   # backward compat with single-cup users)
          "aliases": {               # NEW: user-assigned per-cup aliases
            "<alias-name>": {
              "address": "<UUID>",
              "ble_name": "SGUAI-C3",
            },
            ...
          }
        }

    Missing keys are tolerated; old single-cup caches still work."""
    try:
        cache = json.loads(CACHE_FILE.read_text())
        if not isinstance(cache, dict):
            return {}
        cache.setdefault("aliases", {})
        return cache
    except (OSError, ValueError):
        return {"aliases": {}}


def _save_cache_full(cache):
    try:
        CACHE_FILE.write_text(json.dumps(cache, indent=2))
    except OSError as e:
        _warn(f"could not save cache: {e}")


def _save_cache(address, name):
    """Update the legacy 'last used' fields without touching aliases."""
    cache = _load_cache()
    cache["address"] = address
    cache["name"] = name
    _save_cache_full(cache)


def _resolve_addr_or_alias(value):
    """Translate a user-supplied --addr value: if it matches an alias,
    return that alias's address; otherwise return the value unchanged.
    Lets users say `--addr kitchen` once they've registered the alias."""
    if not value:
        return value
    cache = _load_cache()
    aliases = cache.get("aliases", {})
    entry = aliases.get(value)
    if entry and "address" in entry:
        print(f"Resolved alias {value!r} → {entry['address']}")
        return entry["address"]
    return value


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

    async def find_device(self, use_cache=True, force_addr=None):
        """Locate the cup. Tries (in order): explicit ``force_addr`` →
        cached address → BLE scan with name match.

        ``force_addr``: if given, returned as-is so ``connect()`` will
        attempt a direct connect-by-address. Use this when the user has
        multiple SGUAI-C3 cups paired and needs to pin tests to one.

        Direct connect-by-address bypasses the scan entirely — useful
        when the cup is in §4.7's silent-BLE animation-playback state
        and may not appear in scans even though it's reachable.

        When ``≥2`` SGUAI-C3 devices appear in a scan, this method
        refuses to auto-select silently — it raises with the list of
        candidate addresses, so the caller can disambiguate via
        ``force_addr``. Picking randomly between identically-named
        cups produced confusing test results in the past.
        """
        if force_addr:
            print(f"Using explicit address: {force_addr}")
            return force_addr

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
                    print(f"⚠ Cache scan failed ({type(e).__name__}); trying direct connect...")
                else:
                    print(f"⚠ Cached device not advertising; trying direct connect by address...")
                return cached_addr

        print("Scanning for BLE devices...")
        devices = [d for d in await BleakScanner.discover(timeout=15.0) if d.name]
        if not devices:
            raise Exception("No named BLE devices found")

        print(f"\nFound {len(devices)} named devices:")
        for i, d in enumerate(devices):
            print(f"  {i+1}. {d.name} ({d.address})")

        # Collect ALL name-matches before deciding what to do — picking
        # the first match silently was the source of two-cup test
        # confusion (different cups won the coin flip on different runs).
        matches = [
            d for d in devices
            if d.name == self.device_name or d.name.startswith(self.device_name)
        ]
        if len(matches) == 1:
            d = matches[0]
            print(f"\nAuto-selected: {d.name} ({d.address})")
            _save_cache(d.address, d.name)
            return d
        if len(matches) > 1:
            addrs = "\n  ".join(f"{d.name} ({d.address})" for d in matches)
            raise Exception(
                f"Multiple {self.device_name} devices found — refusing to "
                f"auto-pick:\n  {addrs}\n"
                f"Re-run with --addr <UUID> to select one explicitly."
            )

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
        """Connect to device. Accepts a BLEDevice or a raw address string
        (the latter from the direct-connect path in find_device).

        Mirrors the official APK's post-connect sequence
        (app-service.pretty.js:49445-49582):

          1. createBLEConnection
          2. wait 2000 ms (link stabilization)
          3. setBLEMTU(500) on Android (best-effort here)
          4. wait 2000 ms (post-MTU stabilization)
          5. discover services + characteristics
          6. subscribe to response characteristic
          7. wait 500 ms
          8. **handshake**: read firmware version (0x09).
             The cup's firmware appears to require this read before it
             treats the GATT session as fully initialized — without it,
             persistent-config writes (0x27 auto-off in particular) can
             leave the BLE module in a state that breaks reconnection
             after disconnect.
          9. wait up to 5000 ms for the firmware response.
        """
        addr = device if isinstance(device, str) else device.address
        print(f"Connecting to {addr}...")
        self.client = BleakClient(device)
        await self.client.connect()

        # Step 2: post-connect stabilization (official: 2000 ms)
        await asyncio.sleep(2.0)

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

        # Step 6: subscribe to notifications
        await self.client.start_notify(RESPONSE_CHAR_UUID, self.response_handler)

        # Step 7: brief settle before handshake (official: 500 ms)
        await asyncio.sleep(0.5)

        # Step 8: firmware-version handshake. The official app treats
        # this read as the "session ready" gate; if it doesn't come back
        # within 5 s, it disconnects. We log on failure but still surface
        # a connected session — older cups may not respond to 0x09.
        try:
            version = await self.read_version()
            print(f"✓ Handshake: firmware {version}")
        except Exception as e:
            print(f"⚠ Firmware handshake failed ({type(e).__name__}: {e}); "
                  "subsequent persistent-config writes (e.g. auto-off) "
                  "may leave the cup in a state that prevents reconnect.")

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
        """Set display motion: static / scrollLeft / scrollRight / flashing.

        Byte values match the official APK (verified via the
        `LanguagePack.dynamicEffect.dataList` across 4 language packs):
        0=固定 (Fixed), 1=左移 (Shift Left), 2=右移 (Shift Right),
        3=閃爍 (Flashing). The earlier impl had scroll directions
        swapped — sending `scrollRight` actually scrolled left.
        """
        mode_map = {"static": 0, "scrollLeft": 1, "scrollRight": 2, "flashing": 3}
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
            raise ValueError("Max 255 frames per the protocol spec")
        # Empirical cup-side limit on SGUAI-C3 fw 1.7 (verified by
        # bisection 2026-04-26): the cup's animation buffer holds at
        # most 132 frames. Any animation with more frames causes the
        # cup to drop the BLE link at frame index 132 and leaves the
        # cup BLE-unreachable until physical wake. Hard-fail before
        # sending so we don't brick the cup. The protocol spec allows
        # up to 255 — this is a firmware constraint that may be
        # raised in later cup firmware.
        CUP_MAX_FRAMES = 132
        if len(frames) > CUP_MAX_FRAMES:
            raise ValueError(
                f"Animation has {len(frames)} frames; cup fw 1.7 buffer "
                f"holds at most {CUP_MAX_FRAMES}. Trim to {CUP_MAX_FRAMES} "
                f"or fewer frames before uploading."
            )
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
                try:
                    await self._write_frame_with_retry(cmd)
                except Exception as e:
                    # Surface the exact frame that failed so we can
                    # diagnose mid-stream disconnects empirically.
                    raise RuntimeError(
                        f"animation upload failed at frame {idx}/{n} "
                        f"(after {idx} successful frames, ~{idx * ANIM_FRAME_DELAY_S:.1f}s "
                        f"elapsed): {type(e).__name__}: {e}"
                    ) from e
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

    # Auto-screen-off duration codes — match the official APK's picker.
    # Codes outside 0..4 are silently rejected by firmware fw 1.6.
    AUTO_OFF_CODES = {
        0: "always on",
        1: "30 seconds",
        2: "1 minute",
        3: "3 minutes",
        4: "5 minutes",
    }

    async def set_auto_off(self, code):
        """Set the cup's auto-screen-off duration preset.

        Frame: ``FF 55 07 00 02 27 <code>``, where ``<code>`` is one of
        the five firmware presets (0=always on, 1=30 s, 2=1 m, 3=3 m,
        4=5 m). The earlier "boolean" interpretation was wrong: the
        firmware accepts five discrete codes and silently rejects
        anything else. See PROTOCOL_SPEC.md §4.7 for the full table.

        :param code: integer 0..4 — see :py:attr:`AUTO_OFF_CODES`.
        """
        if not isinstance(code, int) or code not in self.AUTO_OFF_CODES:
            raise ValueError(
                f"code must be one of {sorted(self.AUTO_OFF_CODES)} "
                f"(got {code!r})"
            )
        command = [0xFF, 0x55, 0x07, 0x00, 0x02, 0x27, code]
        async with self._lock:
            try:
                await self._execute_locked(command, timeout=10.0)
            except asyncio.TimeoutError:
                # Like set_dynamic_mode, the cup occasionally drops the
                # echo for a config write. The BLE-layer ACK is enough.
                pass
        return True

    async def read_auto_off(self):
        """Read the current auto-screen-off duration code (0..4).

        Frame: ``FF 55 06 00 01 27`` (6 bytes, no trailing data byte).
        This matches the official APK at ``app-service.pretty.js:51525``.
        Most other read commands use the 7-byte form with a trailing
        ``0x00``, but the official explicitly uses 6 bytes for this
        specific feature byte. See PROTOCOL_SPEC.md §4.7.
        """
        resp = await self.execute_command([0xFF, 0x55, 0x06, 0x00, 0x01, 0x27])
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

    async def factory_reset(self):
        """Send the factory-reset command (0xFC). DESTRUCTIVE — wipes
        all cup data: saved animations, custom settings, and pairing.

        Frame: ``FF 55 06 00 01 FC`` (6 bytes, no data). Note the
        function byte is ``0x01`` (read), even though it's a write
        trigger — matches the APK exactly at
        ``app-service.pretty.js:52564``. See PROTOCOL_SPEC.md §4.8.

        The cup typically closes the GATT link as part of processing
        this, so we don't wait for a response and treat write-side
        errors as expected (the connection drop IS the success signal)."""
        command = [0xFF, 0x55, 0x06, 0x00, 0x01, 0xFC]
        async with self._lock:
            try:
                await self._write(command)
            except Exception:
                # Cup may drop the GATT link as part of resetting.
                pass
        return True

    async def read_device_info(self):
        """Probe the standard BLE Device Information service (UUID 0x180A)
        and return whatever characteristics the cup populates.

        These are platform-stable per-cup identifiers (unlike macOS's
        rotating peripheral UUIDs). If the cup populates the Serial Number
        characteristic (0x2A25), that's the cleanest cross-session identity.

        Returns a dict mapping characteristic short-name to its decoded
        value. Missing characteristics are simply absent from the dict.
        Network errors propagate (the caller's already inside a connect
        block).
        """
        # Standard 16-bit GATT characteristic UUIDs (in DIS 0x180A)
        DIS_CHARS = [
            ("manufacturer", "00002a29-0000-1000-8000-00805f9b34fb"),
            ("model_number", "00002a24-0000-1000-8000-00805f9b34fb"),
            ("serial_number", "00002a25-0000-1000-8000-00805f9b34fb"),
            ("firmware_rev", "00002a26-0000-1000-8000-00805f9b34fb"),
            ("hardware_rev", "00002a27-0000-1000-8000-00805f9b34fb"),
            ("software_rev", "00002a28-0000-1000-8000-00805f9b34fb"),
            ("system_id",    "00002a23-0000-1000-8000-00805f9b34fb"),
        ]
        info = {}
        for label, uuid in DIS_CHARS:
            try:
                raw = await self.client.read_gatt_char(uuid)
                # Most are UTF-8 strings; system_id is 8 bytes binary.
                if label == "system_id":
                    info[label] = raw.hex()
                else:
                    info[label] = raw.decode("utf-8", errors="replace").rstrip("\x00")
            except Exception:
                # Characteristic not present on this device — skip.
                pass
        return info


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
    return [[1 if pixels[r * IMAGE_WIDTH + c] == 255 else 0
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

    @_json_endpoint
    async def handle_animate(self, request):
        """POST /api/animate — upload an animation.

        Body: ``{"path": "/path/to.gif", "speed": 130, "keep_alive": false,
                 "threshold": 128, "invert": false, "dither": false}``

        Either ``path`` (server-side file path) or ``frames_b64`` (a list of
        base64-encoded GIF bytes) is required. Cup-side max 132 frames.
        """
        data = await request.json()
        speed = int(data.get('speed', 130))
        keep_alive = bool(data.get('keep_alive', False))

        path = data.get('path')
        if path:
            frames = load_animation_frames(
                path,
                threshold=int(data.get('threshold', 128)),
                invert=bool(data.get('invert', False)),
                dither=bool(data.get('dither', False)),
            )
        else:
            return web.json_response(
                {'error': "either 'path' (server-side file) is required"},
                status=400,
            )

        if keep_alive:
            try:
                await self.manager.set_auto_off(0)
            except Exception:
                pass
        await self.manager.set_animation(frames, speed=speed)
        return web.json_response({
            'status': 'success',
            'frames': len(frames),
            'speed': speed,
            'keep_alive': keep_alive,
        })

    @_json_endpoint
    async def handle_auto_off(self, request):
        """GET/POST /api/auto-off

        GET returns the current code + label.
        POST body: ``{"code": <0..4>}`` or ``{"preset": "always|30s|1m|3m|5m"}``.
        """
        if request.method == 'GET':
            code = await self.manager.read_auto_off()
            return web.json_response({
                'code': int(code),
                'label': BLEManager.AUTO_OFF_CODES.get(int(code), 'unknown'),
            })
        data = await request.json()
        if 'code' in data:
            code = int(data['code'])
        else:
            preset = (data.get('preset') or '').lower().replace(' ', '').replace('_', '')
            preset_map = {
                'always': 0, 'on': 0, '0': 0,
                '30s': 1, '30sec': 1, '1': 1,
                '1m': 2, '1min': 2, '2': 2,
                '3m': 3, '3min': 3, '3': 3,
                '5m': 4, '5min': 4, '4': 4,
            }
            if preset not in preset_map:
                return web.json_response({'error': 'code 0..4 or preset name required'}, status=400)
            code = preset_map[preset]
        await self.manager.set_auto_off(code)
        return web.json_response({
            'status': 'success',
            'code': code,
            'label': BLEManager.AUTO_OFF_CODES.get(code, 'unknown'),
        })

    @_json_endpoint
    async def handle_info(self, request):
        """GET /api/info — full cup snapshot (DIS + protocol reads)."""
        addr = None
        try:
            addr = self.manager.client.address
        except Exception:
            pass
        dis = await self.manager.read_device_info()
        out = {'address': addr, 'device_information_service': dis}
        for label, fn in [
            ('firmware', self.manager.read_version),
            ('battery', self.manager.read_battery),
            ('temperature_c', self.manager.read_temperature),
            ('auto_off_code', self.manager.read_auto_off),
        ]:
            try:
                out[label] = await fn()
            except Exception as e:
                out[label] = f"error: {type(e).__name__}: {e}"
        if isinstance(out.get('auto_off_code'), int):
            out['auto_off_label'] = BLEManager.AUTO_OFF_CODES.get(
                out['auto_off_code'], 'unknown'
            )
        return web.json_response(out)

    @_json_endpoint
    async def handle_reset(self, request):
        """POST /api/reset?confirm=YES — factory-reset (DESTRUCTIVE).

        Refuses unless ``?confirm=YES`` query param is present, to avoid
        accidental wipes via mis-typed curl commands.
        """
        if request.query.get('confirm') != 'YES':
            return web.json_response(
                {'error': "factory reset requires ?confirm=YES query param"},
                status=400,
            )
        await self.manager.factory_reset()
        return web.json_response({'status': 'success'})

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
        self.app.router.add_get('/api/info', self.handle_info)
        self.app.router.add_get('/api/auto-off', self.handle_auto_off)
        self.app.router.add_post('/api/auto-off', self.handle_auto_off)
        self.app.router.add_post('/api/greeting', self.handle_greeting)
        self.app.router.add_post('/api/mode', self.handle_mode)
        self.app.router.add_post('/api/image', self.handle_image)
        self.app.router.add_post('/api/test', self.handle_test)
        self.app.router.add_post('/api/animate', self.handle_animate)
        self.app.router.add_post('/api/reset', self.handle_reset)
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

async def _find_daemon(args):
    """Decide whether the current command should route through a running
    daemon. Returns the daemon's status dict (containing host/port) or
    None if the command should open its own direct BLE connection.

    Routing rules:
      • --no-daemon in args → never route (forces direct BLE).
      • --addr <X> in args → route only if a daemon serves that address
        (after alias resolution). Otherwise None.
      • No --addr → route if exactly one daemon is running. If multiple
        daemons are running, return None — caller should fall through
        to direct BLE (which will then refuse to auto-pick anyway).
    """
    if "--no-daemon" in args:
        return None
    daemons = _read_all_daemons()
    if not daemons:
        return None
    target = _flag_value(args, "--addr")
    target_addr = _resolve_addr_or_alias(target) if target else None
    if target_addr:
        for d in daemons:
            if d.get("address") == target_addr:
                return d
        return None
    if len(daemons) == 1:
        return daemons[0]
    return None


def _daemon_url(d, path):
    return f"http://{d.get('host')}:{d.get('port')}{path}"


async def _daemon_request(d, method, path, json_body=None, params=None):
    """Helper: make an HTTP request to a running daemon and return parsed
    JSON. Raises on transport failures (caller should fall back to direct
    BLE on connection errors)."""
    if not AIOHTTP_AVAILABLE:
        raise RuntimeError("aiohttp not installed; cannot reach daemon")
    import aiohttp
    timeout = aiohttp.ClientTimeout(total=120)
    url = _daemon_url(d, path)
    async with aiohttp.ClientSession(timeout=timeout) as s:
        async with s.request(method, url, json=json_body, params=params) as r:
            text = await r.text()
            try:
                data = json.loads(text)
            except ValueError:
                data = {"_raw": text}
            if r.status >= 400:
                raise RuntimeError(f"daemon {r.status}: {data.get('error', text)}")
            return data


def _flag_value(args, name):
    """Return the value following `--flag` in args, or None."""
    if name in args:
        i = args.index(name)
        if i + 1 < len(args):
            return args[i + 1]
    return None


@asynccontextmanager
async def connected_manager(args):
    """Open a connected BLEManager, yield it, then disconnect cleanly.
    Honors `--rescan` and `--addr <UUID>` in args. Use as:
    ``async with connected_manager(args) as m:``"""
    manager = BLEManager()
    try:
        device = await manager.find_device(
            use_cache="--rescan" not in args,
            force_addr=_resolve_addr_or_alias(_flag_value(args, "--addr")),
        )
        await manager.connect(device)
        yield manager
    finally:
        await manager.disconnect()


# Flags that don't belong to any cmd-specific parser but appear in CLI args.
# Listed here so _parse_image_opts knows to consume them silently rather than
# warning, and `_first_positional` knows how many args to skip past.
_KNOWN_GLOBAL_FLAGS = {"--rescan", "--host", "--port", "--mode", "--no-keep-alive", "--addr", "--no-daemon", "--yes", "-y"}
_GLOBAL_FLAGS_WITH_VALUE = {"--mode", "--host", "--port", "--addr"}

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


async def cmd_auto_off(args):
    """Set or read the auto-screen-off duration preset.

    The cup supports five firmware presets matching the official app's
    "自动熄屏" picker. Friendly names accepted alongside numeric codes:

      auto-off                     → read current preset
      auto-off always | on | 0     → 常亮 (display always on)
      auto-off 30s    | 1          → 30 seconds
      auto-off 1m     | 2          → 1 minute
      auto-off 3m     | 3          → 3 minutes
      auto-off 5m     | 4          → 5 minutes
    """
    name_to_code = {
        "always": 0, "on": 0, "alwayson": 0, "always-on": 0,
        "30s": 1, "30sec": 1, "30seconds": 1,
        "1m": 2, "1min": 2, "1minute": 2,
        "3m": 3, "3min": 3, "3minutes": 3,
        "5m": 4, "5min": 4, "5minutes": 4,
    }
    arg = _first_positional(args)

    # Resolve the user's input to a code (or None for read).
    code = None
    if arg is not None:
        key = arg.lower().replace(" ", "").replace("_", "")
        if key in name_to_code:
            code = name_to_code[key]
        else:
            try:
                code = int(arg)
            except ValueError:
                print(f"Error: expected one of {sorted(set(name_to_code))} "
                      f"or a code 0..4 (got {arg!r})")
                return 1
            if code not in BLEManager.AUTO_OFF_CODES:
                print(f"Error: code must be 0..4 (got {code})")
                return 1

    daemon = await _find_daemon(args)
    if daemon:
        target = daemon.get("alias") or daemon.get("address")
        print(f"Routing via daemon at port {daemon.get('port')} → {target}")
        try:
            if code is None:
                data = await _daemon_request(daemon, "GET", "/api/auto-off")
                print(f"Auto-off: code {data.get('code')} — {data.get('label')}")
            else:
                data = await _daemon_request(daemon, "POST", "/api/auto-off",
                                             json_body={"code": code})
                print(f"✓ Auto-off → code {data.get('code')} ({data.get('label')})")
            return 0
        except Exception as e:
            print(f"⚠ Daemon route failed ({e}); falling through to direct BLE")

    try:
        async with connected_manager(args) as m:
            if code is None:
                code = await m.read_auto_off()
                label = BLEManager.AUTO_OFF_CODES.get(code, f"unknown code {code}")
                print(f"Auto-off: code {code} — {label}")
            else:
                await m.set_auto_off(code)
                label = BLEManager.AUTO_OFF_CODES[code]
                print(f"✓ Auto-off → code {code} ({label})")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


async def cmd_info(args):
    """Dump everything we can read about the connected cup.

    Useful for distinguishing physical cups when you have ≥ 2 paired.
    Reads the standard BLE Device Information service (0x180A) plus
    our protocol-level reads (firmware version, auto-off code, etc).
    """
    daemon = await _find_daemon(args)
    if daemon:
        target = daemon.get("alias") or daemon.get("address")
        print(f"Routing via daemon at port {daemon.get('port')} → {target}\n")
        try:
            data = await _daemon_request(daemon, "GET", "/api/info")
            print("=== BLE address ===")
            print(f"  address: {data.get('address')}")
            print("\n=== Device Information service (0x180A) ===")
            dis = data.get("device_information_service") or {}
            if dis:
                for k, v in dis.items():
                    print(f"  {k}: {v}")
            else:
                print("  (no DIS characteristics populated)")
            print("\n=== SGUAI protocol reads ===")
            print(f"  firmware (0x09):      {data.get('firmware')}")
            print(f"  auto-off (0x27):      code {data.get('auto_off_code')} ({data.get('auto_off_label')})")
            print(f"  battery (0x02):       {data.get('battery')}%")
            print(f"  temperature (0x01):   {data.get('temperature_c')} °C")
            return 0
        except Exception as e:
            print(f"⚠ Daemon route failed ({e}); falling through to direct BLE\n")

    try:
        async with connected_manager(args) as m:
            print("\n=== BLE address ===")
            try:
                addr = m.client.address
                print(f"  address: {addr}")
            except Exception:
                pass

            print("\n=== Device Information service (0x180A) ===")
            dis = await m.read_device_info()
            if dis:
                for k, v in dis.items():
                    print(f"  {k}: {v}")
            else:
                print("  (no DIS characteristics populated)")

            print("\n=== SGUAI protocol reads ===")
            try:
                print(f"  firmware (0x09):      {await m.read_version()}")
            except Exception as e:
                print(f"  firmware: error ({e})")
            try:
                code = await m.read_auto_off()
                label = BLEManager.AUTO_OFF_CODES.get(code, f"unknown {code}")
                print(f"  auto-off (0x27):      code {code} ({label})")
            except Exception as e:
                print(f"  auto-off: error ({e})")
            try:
                print(f"  battery (0x02):       {await m.read_battery()}%")
            except Exception as e:
                print(f"  battery: error ({e})")
            try:
                print(f"  temperature (0x01):   {await m.read_temperature()} °C")
            except Exception as e:
                print(f"  temperature: error ({e})")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_alias(args):
    """Manage friendly per-cup names.

    Usage:
      alias                          List all aliases (and the "last used" cup)
      alias <name> <UUID>            Register or update an alias
      alias --remove <name>          Forget an alias
      alias --clear                  Forget all aliases (cache file stays)

    Once aliased, `--addr <name>` resolves to the stored UUID. The cup
    BLE-name (always "SGUAI-C3" on this firmware) is recorded for
    bookkeeping; only the UUID is used at connect time.

    This is a local-only mapping — nothing is written to the cup. The
    file lives at ``~/.smart_mug_cache.json``.
    """
    cache = _load_cache()
    aliases = cache.setdefault("aliases", {})

    if not args:
        # List
        if cache.get("address"):
            print(f"Last used: {cache.get('name', 'SGUAI-C3')} ({cache['address']})")
        if not aliases:
            print("\nNo aliases registered. Add one with:")
            print("  smart_mug.py alias <name> <UUID>")
            return 0
        print("\nAliases:")
        for name in sorted(aliases):
            entry = aliases[name]
            print(f"  {name:<16}  {entry.get('address', '?')}  ({entry.get('ble_name', '?')})")
        return 0

    if "--clear" in args:
        cache["aliases"] = {}
        _save_cache_full(cache)
        print("✓ All aliases cleared")
        return 0

    if "--remove" in args:
        idx = args.index("--remove")
        if idx + 1 >= len(args):
            print("Error: --remove requires a name")
            return 1
        name = args[idx + 1]
        if name in aliases:
            del aliases[name]
            _save_cache_full(cache)
            print(f"✓ Removed alias {name!r}")
            return 0
        print(f"Error: no alias named {name!r}")
        return 1

    # Positional: <name> <UUID>
    pos = [a for a in args if not a.startswith("-")]
    if len(pos) != 2:
        print("Error: usage: alias <name> <UUID>  (or --remove / --clear)")
        return 1
    name, uuid = pos
    if name in {"-", "--", "list", "default"} or name.startswith("--"):
        print(f"Error: reserved alias name {name!r}")
        return 1
    aliases[name] = {"address": uuid, "ble_name": DEVICE_NAME}
    _save_cache_full(cache)
    print(f"✓ Aliased {name!r} → {uuid}")
    print(f"  Use it: smart_mug.py info --addr {name}")
    return 0


async def cmd_reset(args):
    """Factory-reset the cup. ALL DATA WILL BE ERASED.

    Sends 0xFC matching the official APK's "重置设备" action. Wipes
    saved animations, custom settings, and pairing state.

    By default prompts for confirmation. Pass ``--yes`` / ``-y`` to skip.
    """
    skip_confirm = "--yes" in args or "-y" in args
    if not skip_confirm:
        try:
            answer = input(
                "⚠ Factory reset will ERASE ALL CUP DATA "
                "(animations, settings, pairing). Continue? [y/N] "
            ).strip().lower()
        except EOFError:
            answer = ""
        if answer not in ("y", "yes"):
            print("Aborted.")
            return 1
    try:
        async with connected_manager(args) as m:
            await m.factory_reset()
            print("✓ Factory-reset command sent. The cup will reboot; "
                  "BLE may drop momentarily.")
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

    keep_alive = "--no-keep-alive" not in args

    # Daemon route — no fresh BLE connection needed.
    daemon = await _find_daemon(args)
    if daemon:
        target = daemon.get("alias") or daemon.get("address")
        print(f"Routing via daemon at port {daemon.get('port')} → {target}")
        try:
            abs_path = str(Path(path).resolve())
            data = await _daemon_request(daemon, "POST", "/api/animate", json_body={
                "path": abs_path,
                "speed": speed,
                "keep_alive": keep_alive,
                "threshold": threshold,
                "invert": invert,
                "dither": dither,
            })
            print(f"✓ Animation uploaded via daemon — {data.get('frames')} frame(s) at speed={data.get('speed')}")
            return 0
        except Exception as e:
            print(f"⚠ Daemon route failed ({e}); falling through to direct BLE")

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
            if keep_alive:
                try:
                    await m.set_auto_off(0)
                    print("✓ Auto-off disabled (display will stay alive)")
                except Exception as e:
                    print(f"⚠ Could not disable auto-off ({e}); proceeding anyway")
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


DAEMON_DIR = Path.home() / ".smart_mug_daemons"
# Legacy single-file location from the previous daemon implementation.
# Cleaned up on first new-daemon run if present and stale.
_LEGACY_DAEMON_STATUS_FILE = Path.home() / ".smart_mug_daemon.json"


def _daemon_status_file(port):
    return DAEMON_DIR / f"port-{port}.json"


def _read_one_daemon(path):
    """Load + alive-check one daemon status file. Returns the dict on
    success; cleans up + returns None if the recorded PID is gone."""
    try:
        status = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    pid = status.get("pid")
    if not isinstance(pid, int):
        return None
    try:
        os.kill(pid, 0)
    except OSError:
        try:
            path.unlink()
        except OSError:
            pass
        return None
    return status


def _read_all_daemons():
    """Return a list of running daemon status dicts. Stale entries are
    cleaned up. Includes a one-time migration of the legacy
    `~/.smart_mug_daemon.json` location."""
    # Legacy file: if its PID is still alive, migrate; otherwise drop.
    if _LEGACY_DAEMON_STATUS_FILE.exists():
        legacy = _read_one_daemon(_LEGACY_DAEMON_STATUS_FILE)
        if legacy:
            DAEMON_DIR.mkdir(parents=True, exist_ok=True)
            target = _daemon_status_file(legacy.get("port", 0))
            try:
                target.write_text(json.dumps(legacy, indent=2))
                _LEGACY_DAEMON_STATUS_FILE.unlink()
            except OSError:
                pass
        else:
            try:
                _LEGACY_DAEMON_STATUS_FILE.unlink()
            except OSError:
                pass

    if not DAEMON_DIR.exists():
        return []
    out = []
    for path in sorted(DAEMON_DIR.glob("port-*.json")):
        s = _read_one_daemon(path)
        if s:
            out.append(s)
    return out


def _read_daemon_status(port=None):
    """Convenience: return one daemon (matching ``port`` if given, else
    the unique daemon if exactly one is running) or None."""
    daemons = _read_all_daemons()
    if not daemons:
        return None
    if port is not None:
        for d in daemons:
            if d.get("port") == port:
                return d
        return None
    if len(daemons) == 1:
        return daemons[0]
    return None  # multiple — caller must disambiguate


def _format_daemon(d):
    """One-line summary of a daemon status dict."""
    addr = d.get("address", "?")
    alias = d.get("alias")
    target = f"{alias} ({addr})" if alias else addr
    return (f"  port {d.get('port')}: PID {d.get('pid')} → {target} "
            f"@ http://{d.get('host')}:{d.get('port')}/")


async def cmd_daemon(args):
    """Persistent BLE-connection daemon with HTTP API.

    Holds a GATT connection alive until the process is signaled
    (SIGINT/SIGTERM). Exposes the cup over a local HTTP API so
    short-lived clients can drive the cup without each paying the
    connect+disconnect cost — and without triggering the cup's
    silent-BLE side effects after autonomous animation playback
    (PROTOCOL_SPEC.md §4.6 / §4.7).

    Multiple daemons may run simultaneously, one per port, e.g. one
    per physical cup. Status files live at
    ``~/.smart_mug_daemons/port-<N>.json``.

    Usage:
      smart_mug.py daemon [--addr UUID|alias] [--host 127.0.0.1] [--port N]
      smart_mug.py daemon --status                  List all running daemons
      smart_mug.py daemon --stop [--port N | --all] Stop one or all daemons
    """
    if "--status" in args:
        daemons = _read_all_daemons()
        if not daemons:
            print("No daemons running.")
            return 0
        print(f"{len(daemons)} daemon(s) running:")
        for d in daemons:
            print(_format_daemon(d))
            print(f"    started:  {d.get('started_at')}")
        return 0

    if "--stop" in args:
        daemons = _read_all_daemons()
        if not daemons:
            print("No daemons running.")
            return 0
        if "--all" in args:
            stopped = 0
            for d in daemons:
                try:
                    os.kill(d["pid"], signal.SIGTERM)
                    print(f"✓ Sent SIGTERM to PID {d['pid']} (port {d.get('port')})")
                    stopped += 1
                except OSError as e:
                    print(f"⚠ Could not signal PID {d['pid']}: {e}")
            return 0 if stopped else 1
        target_port = _flag(args, "--port", None, int)
        if target_port is None and len(daemons) == 1:
            d = daemons[0]
        elif target_port is None:
            print("Multiple daemons running — pass --port <N> or --all:")
            for d in daemons:
                print(_format_daemon(d))
            return 1
        else:
            d = next((x for x in daemons if x.get("port") == target_port), None)
            if d is None:
                print(f"No daemon on port {target_port}.")
                return 1
        try:
            os.kill(d["pid"], signal.SIGTERM)
            print(f"✓ Sent SIGTERM to PID {d['pid']} (port {d.get('port')})")
        except OSError as e:
            print(f"Error: could not signal PID {d['pid']}: {e}")
            return 1
        return 0

    host = _flag(args, "--host", "127.0.0.1")
    port = _flag(args, "--port", 8080, int)

    # Refuse if a daemon is already on the requested port. Other ports
    # are fine; multi-cup support is the whole point.
    existing = _read_daemon_status(port=port)
    if existing:
        print(f"Error: a daemon is already on port {port} "
              f"(PID {existing['pid']}). Pick a different --port or stop "
              f"with `smart_mug.py daemon --stop --port {port}`.")
        return 1

    if not AIOHTTP_AVAILABLE:
        print("Error: aiohttp not available. Install with: uv pip install aiohttp")
        return 1

    api_server = None
    stop_event = asyncio.Event()

    def _on_signal():
        if not stop_event.is_set():
            print("\n✓ Received signal, shutting down daemon...")
            stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _on_signal)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler on the proactor loop;
            # SIGINT will still raise KeyboardInterrupt.
            pass

    try:
        async with connected_manager(args) as manager:
            # Identify which physical cup (alias if known) we ended up on.
            try:
                addr = manager.client.address
            except Exception:
                addr = "unknown"
            alias = None
            for name, entry in _load_cache().get("aliases", {}).items():
                if entry.get("address") == addr:
                    alias = name
                    break

            api_server = APIServer(manager, host=host, port=port)
            if not await api_server.start():
                return 1

            status = {
                "pid": os.getpid(),
                "host": host,
                "port": port,
                "alias": alias,
                "address": addr,
                "started_at": datetime.now(timezone.utc).isoformat(),
            }
            try:
                DAEMON_DIR.mkdir(parents=True, exist_ok=True)
                _daemon_status_file(port).write_text(json.dumps(status, indent=2))
            except OSError as e:
                print(f"⚠ could not write status file: {e}")

            target = f"{alias} ({addr})" if alias else addr
            print(f"\n✓ Daemon ready. Persistent connection to {target}.")
            print(f"  HTTP API: http://{host}:{port}/")
            print(f"  Stop with: smart_mug.py daemon --stop  (or Ctrl-C)\n")

            await stop_event.wait()
        return 0
    except KeyboardInterrupt:
        print("\n✓ Interrupted, shutting down daemon...")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1
    finally:
        if api_server:
            try:
                await api_server.stop()
            except Exception:
                pass
        try:
            f = _daemon_status_file(port)
            if f.exists():
                f.unlink()
        except OSError:
            pass


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
  animate <gif> [opts] [-s SPEED] [--rescan] [--no-keep-alive]
                                              Upload animation (cup plays it).
                                              Auto-disables screen sleep by default
                                              so the loop plays continuously.
  read [field ...] [--rescan]                 Read version / temperature / battery
  info [--rescan] [--addr UUID|alias]         Dump everything: BLE address + standard
                                              Device Information service + protocol reads
                                              (useful for distinguishing two cups)
  alias [<name> <UUID> | --list | --remove <name> | --clear]
                                              Manage friendly per-cup names. Once
                                              aliased, --addr <name> resolves locally.
  daemon [--addr UUID|alias] [--host H] [--port P]
                                              Persistent BLE-connection daemon with
                                              HTTP API. Multiple daemons may run, one
                                              per port — e.g. one per cup. Avoids
                                              §4.7 silent-BLE windows by never
                                              disconnecting.
  daemon --status                             List all running daemons.
  daemon --stop [--port N | --all]            Stop one (--port required when ≥2)
                                              or all running daemons.
  auto-off [<preset>] [--rescan]              Set or read screen auto-off duration
                                              presets: always | 30s | 1m | 3m | 5m
  reset [-y] [--rescan]                       Factory reset (DESTRUCTIVE — wipes
                                              all cup data; -y to skip prompt)
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
  --addr UUID    Connect to a specific cup by address (skips scan).
                 Required when ≥ 2 SGUAI-C3 devices are paired —
                 the scanner refuses to silently auto-pick. Also
                 selects a daemon by address when one is running.
  --no-daemon    Bypass any running daemon; open a direct BLE
                 connection. Useful for debugging or when you want
                 to bypass a stale daemon.
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
    elif cmd in ('reset', 'factory-reset'):
        return await cmd_reset(sys.argv[2:])
    elif cmd in ('animate', 'anim', 'gif'):
        return await cmd_animate(sys.argv[2:])
    elif cmd == 'read':
        return await cmd_read(sys.argv[2:])
    elif cmd == 'info':
        return await cmd_info(sys.argv[2:])
    elif cmd == 'alias':
        return cmd_alias(sys.argv[2:])
    elif cmd in ('auto-off', 'autooff', 'screen-off'):
        return await cmd_auto_off(sys.argv[2:])
    elif cmd == 'repl':
        return await cmd_repl(sys.argv[2:])
    elif cmd == 'daemon':
        return await cmd_daemon(sys.argv[2:])
    elif cmd == 'clear-cache':
        BLEManager.clear_cached_device()
        return 0
    else:
        print(f"Unknown command: {cmd}")
        print_help()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
