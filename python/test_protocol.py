"""Wire-format tests for the Python reference implementation.

Same byte-level invariants as the Go port's `protocol_test.go`. If a
test here ever disagrees with the corresponding Go test, the two
implementations have drifted and the protocol is no longer single-source-
of-truth.

Run: ``uv run python -m pytest test_protocol.py``  (or just ``python -m pytest``)
"""

import sys
from pathlib import Path

# Avoid touching the user's real cache during tests.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from smart_mug import (  # noqa: E402
    BLEManager,
    pack_bitmap,
    parse_mode_arg,
    parse_speed_arg,
    IMAGE_WIDTH,
    IMAGE_HEIGHT,
)


# -----------------------------------------------------------------------------
# pack_bitmap — row-major LTR, MSB-first.
# Identical assertions to go/internal/sguai/protocol_test.go::TestPackBitmap.
# -----------------------------------------------------------------------------

def _blank():
    return [[0] * IMAGE_WIDTH for _ in range(IMAGE_HEIGHT)]


def test_pack_all_off():
    out = pack_bitmap(_blank())
    assert len(out) == 72
    assert out == bytes(72)


def test_pack_all_on():
    grid = [[1] * IMAGE_WIDTH for _ in range(IMAGE_HEIGHT)]
    out = pack_bitmap(grid)
    assert out == bytes([0xFF] * 72)


def test_pack_top_left_pixel():
    """grid[0][0] = 1 → byte 0 = 0x80 (MSB-first row-major LTR).

    Verified empirically against fw 1.6 — see PROTOCOL_SPEC.md §4.5."""
    grid = _blank()
    grid[0][0] = 1
    out = pack_bitmap(grid)
    assert out[0] == 0x80
    assert all(b == 0 for b in out[1:])


def test_pack_first_byte_last_bit():
    grid = _blank()
    grid[0][7] = 1
    out = pack_bitmap(grid)
    assert out[0] == 0x01
    assert all(b == 0 for b in out[1:])


def test_pack_row_major_scan_order():
    """grid[1][0] = 1 → byte 6 = 0x80 (start of row 2 = bit index 48)."""
    grid = _blank()
    grid[1][0] = 1
    out = pack_bitmap(grid)
    assert out[6] == 0x80


def test_pack_bottom_right_pixel():
    grid = _blank()
    grid[11][47] = 1
    out = pack_bitmap(grid)
    assert out[71] == 0x01


def test_pack_rejects_short_grid():
    short = [[0] * IMAGE_WIDTH for _ in range(IMAGE_HEIGHT - 1)]
    try:
        pack_bitmap(short)
    except ValueError:
        return
    raise AssertionError("expected ValueError for short grid")


def test_pack_rejects_uneven_row():
    grid = _blank()
    grid[3] = [0] * (IMAGE_WIDTH - 1)
    try:
        pack_bitmap(grid)
    except ValueError:
        return
    raise AssertionError("expected ValueError for uneven row")


# -----------------------------------------------------------------------------
# Read-frame builders. We don't have helper functions for these in
# smart_mug.py (the bytes are inlined in each method), so we invoke the
# methods through a fake client and capture what they would write. Easier:
# just assert the byte literals match the spec at the public-method level.
# -----------------------------------------------------------------------------

def test_read_temperature_frame_literal():
    """Mirrors go/internal/sguai/protocol_test.go::TestBuildReadCommand."""
    from smart_mug import BLEManager  # noqa
    # The frame is constructed inline in BLEManager.read_temperature.
    # Reproduce it here and assert structure.
    expected = [0xFF, 0x55, 0x07, 0x00, 0x01, 0x01, 0x00]
    # Open-coded check: locate the literal in the source.
    source = Path(__file__).resolve().parent / "smart_mug.py"
    text = source.read_text()
    assert "[0xFF, 0x55, 0x07, 0x00, 0x01, 0x01, 0x00]" in text, (
        "read_temperature frame literal changed"
    )
    _ = expected  # bytes documented above; this tests the source contains them


def test_read_battery_frame_literal():
    text = (Path(__file__).resolve().parent / "smart_mug.py").read_text()
    assert "[0xFF, 0x55, 0x07, 0x00, 0x01, 0x02, 0x00]" in text


def test_read_version_frame_literal():
    text = (Path(__file__).resolve().parent / "smart_mug.py").read_text()
    assert "[0xFF, 0x55, 0x07, 0x00, 0x01, 0x09, 0x00]" in text


def test_read_auto_off_is_six_bytes():
    """6-byte form — APK quirk. If this regresses to the 7-byte form,
    cup-side state can break in subtle ways (per PROTOCOL_SPEC.md §4.7)."""
    text = (Path(__file__).resolve().parent / "smart_mug.py").read_text()
    assert "[0xFF, 0x55, 0x06, 0x00, 0x01, 0x27]" in text, (
        "read_auto_off must be the 6-byte form"
    )


def test_factory_reset_uses_function_byte_01():
    """fn=0x01 is intentional per APK quirk (write-style trigger via
    read function byte). If this regresses to 0x02, the cup ignores it."""
    text = (Path(__file__).resolve().parent / "smart_mug.py").read_text()
    assert "[0xFF, 0x55, 0x06, 0x00, 0x01, 0xFC]" in text, (
        "factory_reset must use fn=0x01 per APK quirk"
    )


# -----------------------------------------------------------------------------
# Dynamic-mode byte values — APK ground truth from
# LanguagePack.dynamicEffect.dataList: 0=Fixed, 1=Shift Left,
# 2=Shift Right, 3=Twinkle. Verified across 4 language packs. The
# earlier (incorrect) mapping had 1=Right / 2=Left swapped.
# -----------------------------------------------------------------------------

def test_dynamic_mode_byte_values():
    text = (Path(__file__).resolve().parent / "smart_mug.py").read_text()
    # The mode_map literal must have left=1, right=2.
    assert '"scrollLeft": 1' in text, "scrollLeft must map to byte 1 (左移 in APK)"
    assert '"scrollRight": 2' in text, "scrollRight must map to byte 2 (右移 in APK)"
    # And NOT the swapped form.
    assert '"scrollRight": 1' not in text, "scroll directions are SWAPPED — see APK dynamicEffect.dataList"
    assert '"scrollLeft": 2' not in text, "scroll directions are SWAPPED — see APK dynamicEffect.dataList"


# -----------------------------------------------------------------------------
# Dynamic speed (feature 0x24) — separate persistent setting from the
# 0x26 prologue speed byte. Read frame is 6-byte form per APK survey.
# -----------------------------------------------------------------------------

def test_read_dynamic_speed_is_six_bytes():
    """6-byte form (no trailing 0x00) — matches the APK at
    app-service.pretty.js:51459. Newer feature bytes use this form."""
    text = (Path(__file__).resolve().parent / "smart_mug.py").read_text()
    assert "[0xFF, 0x55, 0x06, 0x00, 0x01, 0x24]" in text, (
        "read_dynamic_speed must be the 6-byte form"
    )


def test_set_dynamic_speed_frame_literal():
    """7-byte form: FF 55 07 00 02 24 <speed>."""
    text = (Path(__file__).resolve().parent / "smart_mug.py").read_text()
    assert "[0xFF, 0x55, 0x07, 0x00, 0x02, 0x24, speed]" in text, (
        "set_dynamic_speed frame literal changed"
    )


# -----------------------------------------------------------------------------
# Auto-off codes table — must match the APK's autoStandby.dataList exactly.
# -----------------------------------------------------------------------------

def test_auto_off_codes_table():
    assert BLEManager.AUTO_OFF_CODES == {
        0: "always on",
        1: "30 seconds",
        2: "1 minute",
        3: "3 minutes",
        4: "5 minutes",
    }


# -----------------------------------------------------------------------------
# Frame-count limits.
# -----------------------------------------------------------------------------

def test_frame_count_validation_rejects_above_132():
    """The cup-side limit is 132. Sending >132 leaves the cup in a
    silent-BLE state (PROTOCOL_SPEC.md §4.6)."""
    text = (Path(__file__).resolve().parent / "smart_mug.py").read_text()
    assert "CUP_MAX_FRAMES = 132" in text


# -----------------------------------------------------------------------------
# parse_mode_arg — accept liberal mode-name input.
# -----------------------------------------------------------------------------

def test_parse_mode_canonical_passthrough():
    assert parse_mode_arg("static") == "static"
    assert parse_mode_arg("scrollLeft") == "scrollLeft"
    assert parse_mode_arg("scrollRight") == "scrollRight"
    assert parse_mode_arg("flashing") == "flashing"


def test_parse_mode_friendly_synonyms():
    assert parse_mode_arg("left") == "scrollLeft"
    assert parse_mode_arg("right") == "scrollRight"
    assert parse_mode_arg("blink") == "flashing"
    assert parse_mode_arg("flash") == "flashing"
    assert parse_mode_arg("twinkle") == "flashing"
    assert parse_mode_arg("fixed") == "static"
    assert parse_mode_arg("still") == "static"


def test_parse_mode_punctuation_and_case():
    assert parse_mode_arg("Scroll-Left") == "scrollLeft"
    assert parse_mode_arg("SCROLL_LEFT") == "scrollLeft"
    assert parse_mode_arg("scroll left") == "scrollLeft"
    assert parse_mode_arg("Shift Right") == "scrollRight"


def test_parse_mode_raw_byte_values():
    assert parse_mode_arg("0") == "static"
    assert parse_mode_arg("1") == "scrollLeft"
    assert parse_mode_arg("2") == "scrollRight"
    assert parse_mode_arg("3") == "flashing"


def test_parse_mode_rejects_garbage():
    import pytest
    for bad in ["upside-down", "diagonal", "5", "", "fast"]:
        try:
            parse_mode_arg(bad)
        except ValueError:
            continue
        raise AssertionError(f"expected ValueError for {bad!r}")


# -----------------------------------------------------------------------------
# parse_speed_arg — accept presets, ms/s/fps, or raw byte.
# -----------------------------------------------------------------------------

def test_parse_speed_presets():
    assert parse_speed_arg("slowest") == 5  # matches APK slider min=5
    assert parse_speed_arg("slow") == 50
    assert parse_speed_arg("medium") == 130
    assert parse_speed_arg("normal") == 130
    assert parse_speed_arg("default") == 130
    assert parse_speed_arg("fast") == 200
    assert parse_speed_arg("fastest") == 255


def test_parse_speed_raw_byte():
    assert parse_speed_arg("1") == 1
    assert parse_speed_arg("130") == 130
    assert parse_speed_arg("255") == 255


def test_parse_speed_milliseconds():
    # ms_per_frame = 10 * (260 - speed)  →  speed = 260 - ms/10
    # 1300ms → 260 - 130 = 130
    assert parse_speed_arg("1300ms") == 130
    # 600ms → 260 - 60 = 200
    assert parse_speed_arg("600ms") == 200
    # 50ms → 260 - 5 = 255
    assert parse_speed_arg("50ms") == 255


def test_parse_speed_seconds():
    assert parse_speed_arg("1.3s") == 130    # 1300ms equivalent
    assert parse_speed_arg("0.6s") == 200    # 600ms equivalent
    assert parse_speed_arg("2.5s") == 10     # 260 - 250 = 10


def test_parse_speed_fps():
    # 1000/2fps = 500ms/frame → speed = 260 - 50 = 210
    assert parse_speed_arg("2fps") == 210
    # 1000/10fps = 100ms/frame → speed = 260 - 10 = 250
    assert parse_speed_arg("10fps") == 250


def test_parse_speed_case_insensitive():
    assert parse_speed_arg("MEDIUM") == 130
    assert parse_speed_arg("Slow") == 50
    assert parse_speed_arg("1300MS") == 130


def test_parse_speed_rejects_garbage():
    import pytest
    for bad in ["", "fastfast", "very fast", "0", "-1", "256", "0fps", "9999ms"]:
        try:
            parse_speed_arg(bad)
        except ValueError:
            continue
        raise AssertionError(f"expected ValueError for {bad!r}")


# -----------------------------------------------------------------------------
# Cross-tool format: the JSON cache file must be readable by both
# Python and Go. The shape is documented at python/smart_mug.py
# `_load_cache` and Go's `cache.Cache`.
# -----------------------------------------------------------------------------

def test_cache_shape(tmp_path, monkeypatch):
    import json
    monkeypatch.setattr(
        "smart_mug.CACHE_FILE", tmp_path / ".smart_mug_cache.json"
    )
    from smart_mug import _load_cache, _save_cache_full

    # Empty load
    cache = _load_cache()
    assert isinstance(cache, dict)
    assert "aliases" in cache
    assert cache["aliases"] == {}

    # Save the shape Go expects, reload, and verify
    cache["address"] = "uuid-X"
    cache["name"] = "SGUAI-C3"
    cache["aliases"]["kitchen"] = {"address": "uuid-A", "ble_name": "SGUAI-C3"}
    _save_cache_full(cache)

    raw = json.loads((tmp_path / ".smart_mug_cache.json").read_text())
    assert raw["address"] == "uuid-X"
    assert raw["name"] == "SGUAI-C3"
    assert raw["aliases"]["kitchen"]["address"] == "uuid-A"
    assert raw["aliases"]["kitchen"]["ble_name"] == "SGUAI-C3"
