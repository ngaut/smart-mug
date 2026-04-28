// Package sguai contains the SGUAI-C3 BLE protocol — frame builders,
// command bytes, bitmap encoding. All wire-format constants live here so
// they're easy to audit against PROTOCOL_SPEC.md and the Python
// reference implementation in python/smart_mug.py.
package sguai

import (
	"errors"
	"fmt"
)

// BLE service / characteristic UUIDs.
const (
	ServiceUUID     = "0000ff00-0000-1000-8000-00805f9b34fb"
	CommandCharUUID = "0000ff01-0000-1000-8000-00805f9b34fb"
	ResponseUUID    = "0000ff02-0000-1000-8000-00805f9b34fb"
	DeviceName      = "SGUAI-C3"
)

// Display dimensions (1-bit panel).
const (
	ImageWidth  = 48
	ImageHeight = 12
	BitmapBytes = 72 // 48 * 12 / 8
)

// Empirical cup-side limits (verified against fw 1.7, 2026-04-26).
const (
	// CupMaxFrames is the cup's animation buffer limit. Sending more
	// frames crashes the BLE link mid-upload at frame index 132.
	// Protocol byte allows 255; this is firmware, not protocol.
	CupMaxFrames = 132
)

// Function bytes (offset 4 in command frames).
const (
	FuncRead  = 0x01
	FuncWrite = 0x02
)

// Feature bytes (offset 5). See PROTOCOL_SPEC.md §3.2.
const (
	FeatureTemperature  = 0x01
	FeatureBattery      = 0x02
	FeatureVersion      = 0x09
	FeatureTempUnit     = 0x0B
	FeatureGreeting     = 0x17
	FeatureMode         = 0x23 // 设置/获取动态效果 — Set/Get Dynamic Effect
	FeatureDynamicSpeed = 0x24 // 设置/获取动态速度 — Set/Get Dynamic Speed
	FeatureStaticImage  = 0x25
	FeatureAnimation    = 0x26
	FeatureAutoOff      = 0x27
	FeatureFactoryReset = 0xFC
)

// AutoOffCodes maps the 5 firmware presets to human labels (matches
// the official APK's auto-standby picker exactly).
var AutoOffCodes = map[byte]string{
	0: "always on",
	1: "30 seconds",
	2: "1 minute",
	3: "3 minutes",
	4: "5 minutes",
}

// DynamicModes maps user-facing mode names to the byte the firmware
// expects. Byte values verified against the APK's
// `LanguagePack.dynamicEffect.dataList` across 4 language packs:
//   0 = 固定 / Fixed       (static)
//   1 = 左移 / Shift Left  (scroll left)
//   2 = 右移 / Shift Right (scroll right)
//   3 = 閃爍 / Twinkle     (flashing)
//
// Earlier impls had scrollRight=1 / scrollLeft=2 (swapped) and
// produced text scrolling the opposite direction from what users
// asked for — fixed.
var DynamicModes = map[string]byte{
	"static":      0,
	"scrollleft":  1,
	"scrollright": 2,
	"flashing":    3,
}

// PackBitmap encodes a 12×48 boolean grid into 72 bytes for the cup's
// framebuffer. Encoding is **row-major LTR, top-to-bottom, MSB-first**.
//
// Verified empirically on SGUAI-C3 firmware 1.6 hardware: grid[0][0]=true
// lights the physical top-left LED. The official Android APK ships a
// column-major RTL encoder that's incompatible with this firmware — see
// PROTOCOL_SPEC.md §4.5.
func PackBitmap(grid [][]bool) ([]byte, error) {
	if len(grid) != ImageHeight {
		return nil, fmt.Errorf("grid must have %d rows, got %d", ImageHeight, len(grid))
	}
	for r, row := range grid {
		if len(row) != ImageWidth {
			return nil, fmt.Errorf("row %d must have %d cols, got %d", r, ImageWidth, len(row))
		}
	}
	out := make([]byte, BitmapBytes)
	i := 0
	for r := 0; r < ImageHeight; r++ {
		for c := 0; c < ImageWidth; c++ {
			if grid[r][c] {
				out[i>>3] |= 1 << (7 - (i & 7))
			}
			i++
		}
	}
	return out, nil
}

// UTF16BEBytes encodes a string as 2-byte-per-code-unit UTF-16 big-endian,
// matching the official's `charCodeAt` iteration. Non-BMP characters use
// surrogate pairs (4 bytes), like the official.
func UTF16BEBytes(s string) []byte {
	out := make([]byte, 0, len(s)*2)
	for _, r := range s {
		if r < 0x10000 {
			out = append(out, byte(r>>8), byte(r&0xFF))
		} else {
			// Encode as surrogate pair
			r -= 0x10000
			hi := 0xD800 + (r >> 10)
			lo := 0xDC00 + (r & 0x3FF)
			out = append(out, byte(hi>>8), byte(hi&0xFF), byte(lo>>8), byte(lo&0xFF))
		}
	}
	return out
}

// BuildReadCommand returns a 7-byte read frame for the given feature byte.
// Format: ``FF 55 07 00 01 <feature> 00``. Most reads use this form.
func BuildReadCommand(feature byte) []byte {
	return []byte{0xFF, 0x55, 0x07, 0x00, FuncRead, feature, 0x00}
}

// BuildReadAutoOff returns the 6-byte read frame for 0x27. Unlike most
// reads this one omits the trailing 0x00 — matches the APK exactly.
// See PROTOCOL_SPEC.md §4.7.
func BuildReadAutoOff() []byte {
	return []byte{0xFF, 0x55, 0x06, 0x00, FuncRead, FeatureAutoOff}
}

// BuildReadDynamicSpeed returns the 6-byte read frame for 0x24
// (matches the APK at app-service.pretty.js:51459). The newer feature
// bytes (0x16+) all use the 6-byte read form rather than the 7-byte
// form with a trailing 0x00 used by 0x01/0x02/0x09.
func BuildReadDynamicSpeed() []byte {
	return []byte{0xFF, 0x55, 0x06, 0x00, FuncRead, FeatureDynamicSpeed}
}

// BuildSetDynamicSpeed returns the frame for `set persistent dynamic
// speed`. speed must be 1..255 (0 is unspecified by firmware). See
// PROTOCOL_SPEC.md §4.6 for the speed-byte interpretation.
func BuildSetDynamicSpeed(speed byte) ([]byte, error) {
	if speed == 0 {
		return nil, errors.New("speed must be 1..255 (0 is unspecified by firmware)")
	}
	return []byte{0xFF, 0x55, 0x07, 0x00, FuncWrite, FeatureDynamicSpeed, speed}, nil
}

// BuildSetMode returns the frame for `set dynamic mode`. Mode is one of
// "static" / "scrollRight" / "scrollLeft" / "flashing" (case-insensitive).
func BuildSetMode(mode string) ([]byte, error) {
	b, ok := DynamicModes[normalizeMode(mode)]
	if !ok {
		return nil, fmt.Errorf("invalid mode %q (use static|scrollRight|scrollLeft|flashing)", mode)
	}
	return []byte{0xFF, 0x55, 0x07, 0x00, FuncWrite, FeatureMode, b}, nil
}

// BuildSetAutoOff returns the frame for `set auto-off duration code`.
// code must be 0..4. See PROTOCOL_SPEC.md §4.7 for label mapping.
func BuildSetAutoOff(code byte) ([]byte, error) {
	if _, ok := AutoOffCodes[code]; !ok {
		return nil, fmt.Errorf("auto-off code %d invalid (must be 0..4)", code)
	}
	return []byte{0xFF, 0x55, 0x07, 0x00, FuncWrite, FeatureAutoOff, code}, nil
}

// BuildFactoryReset returns the destructive 0xFC frame. Note function
// byte is 0x01 (read), even though it's a write trigger — matches the
// APK exactly. See PROTOCOL_SPEC.md §4.8.
func BuildFactoryReset() []byte {
	return []byte{0xFF, 0x55, 0x06, 0x00, FuncRead, FeatureFactoryReset}
}

// BuildSetStaticImage builds the 78-byte image upload frame.
// `bitmap` must be exactly 72 bytes (output of PackBitmap).
func BuildSetStaticImage(bitmap []byte) ([]byte, error) {
	if len(bitmap) != BitmapBytes {
		return nil, fmt.Errorf("bitmap must be %d bytes, got %d", BitmapBytes, len(bitmap))
	}
	out := make([]byte, 0, 6+BitmapBytes)
	out = append(out, 0xFF, 0x55, 0x4E, 0x00, FuncWrite, FeatureStaticImage)
	out = append(out, bitmap...)
	return out, nil
}

// BuildAnimationPrologue builds the 8-byte prologue that precedes
// per-frame uploads.  Tells the cup to expect <count> frames at <speed>.
func BuildAnimationPrologue(count, speed byte) []byte {
	return []byte{0xFF, 0x55, 0x08, 0x00, FuncWrite, FeatureAnimation, count, speed}
}

// BuildAnimationFrame builds an 80-byte per-frame upload command.
// `bitmap` must be exactly 72 bytes; idx is 0-based; speed should match
// the prologue.
func BuildAnimationFrame(idx, speed byte, bitmap []byte) ([]byte, error) {
	if len(bitmap) != BitmapBytes {
		return nil, fmt.Errorf("bitmap must be %d bytes, got %d", BitmapBytes, len(bitmap))
	}
	out := make([]byte, 0, 8+BitmapBytes)
	out = append(out, 0xFF, 0x55, 0x50, 0x00, FuncWrite, FeatureAnimation, idx, speed)
	out = append(out, bitmap...)
	return out, nil
}

// BuildSetGreeting builds a UTF-16BE greeting frame. Empty string clears
// the greeting (subcmd 0x00). Length byte is computed from total payload.
func BuildSetGreeting(msg string) []byte {
	subcmd := byte(0x00)
	var payload []byte
	if msg != "" {
		subcmd = 0x01
		payload = UTF16BEBytes(msg)
	}
	out := []byte{0xFF, 0x55, 0x00, 0x00, FuncWrite, FeatureGreeting, subcmd}
	out = append(out, payload...)
	out[2] = byte(len(out)) // total length
	return out
}

// ParseResponse strips the 0xFF/length/0x0D/0x0A frame envelope from a
// notification, returning just the payload bytes. If the envelope is
// missing or malformed, the raw bytes are returned unchanged so callers
// can introspect.
func ParseResponse(raw []byte) []byte {
	if len(raw) >= 3 && raw[0] == 0xFF && raw[len(raw)-2] == 0x0D && raw[len(raw)-1] == 0x0A {
		return raw[2 : len(raw)-2]
	}
	return raw
}

// IsValidSpeed enforces the 1..255 firmware constraint. 0 is documented
// as unspecified behavior.
func IsValidSpeed(speed int) error {
	if speed < 1 || speed > 255 {
		return errors.New("speed must be 1..255 (0 is unspecified by firmware)")
	}
	return nil
}

// ValidateFrameCount enforces both the protocol limit (255) and the
// empirical cup-side firmware buffer limit (CupMaxFrames). The latter
// is checked first because it's the more painful failure mode.
func ValidateFrameCount(n int) error {
	if n == 0 {
		return errors.New("at least one frame required")
	}
	if n > 255 {
		return errors.New("max 255 frames per the protocol spec")
	}
	if n > CupMaxFrames {
		return fmt.Errorf("animation has %d frames; cup fw 1.7 buffer holds at most %d. Trim before uploading", n, CupMaxFrames)
	}
	return nil
}

// normalizeMode lowercases and strips spaces/dashes so callers can pass
// "scrollRight" / "scroll-right" / "ScrollRight" interchangeably.
func normalizeMode(s string) string {
	out := make([]byte, 0, len(s))
	for i := 0; i < len(s); i++ {
		c := s[i]
		if c == ' ' || c == '-' || c == '_' {
			continue
		}
		if c >= 'A' && c <= 'Z' {
			c += 32
		}
		out = append(out, c)
	}
	return string(out)
}
