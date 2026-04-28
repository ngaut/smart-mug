package sguai

import (
	"bytes"
	"errors"
	"strings"
	"testing"
)

// All expected byte sequences in this file are manually transcribed
// from PROTOCOL_SPEC.md or the Python reference implementation. If a
// value here differs from python/smart_mug.py, the Go side is wrong —
// not the test.

func TestBuildReadCommand(t *testing.T) {
	cases := []struct {
		name    string
		feature byte
		want    []byte
	}{
		{"version (0x09)", FeatureVersion, []byte{0xFF, 0x55, 0x07, 0x00, 0x01, 0x09, 0x00}},
		{"battery (0x02)", FeatureBattery, []byte{0xFF, 0x55, 0x07, 0x00, 0x01, 0x02, 0x00}},
		{"temperature (0x01)", FeatureTemperature, []byte{0xFF, 0x55, 0x07, 0x00, 0x01, 0x01, 0x00}},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got := BuildReadCommand(tc.feature)
			if !bytes.Equal(got, tc.want) {
				t.Errorf("got % X, want % X", got, tc.want)
			}
		})
	}
}

func TestBuildReadAutoOff(t *testing.T) {
	// Critical: 6 bytes, no trailing 0x00. APK does this differently
	// from other reads; if Go regresses, it's a bug.
	want := []byte{0xFF, 0x55, 0x06, 0x00, 0x01, 0x27}
	got := BuildReadAutoOff()
	if !bytes.Equal(got, want) {
		t.Errorf("got % X, want % X", got, want)
	}
	if len(got) != 6 {
		t.Errorf("must be exactly 6 bytes, got %d", len(got))
	}
}

func TestBuildSetMode(t *testing.T) {
	// Byte values from APK LanguagePack.dynamicEffect.dataList:
	// 0=Fixed, 1=Shift Left, 2=Shift Right, 3=Twinkle. Verified across
	// zh-Hant / en / zh-Hans / ja language packs. Don't accept patches
	// that swap 1 and 2 — text-scroll direction will reverse.
	cases := []struct {
		mode string
		want []byte
	}{
		{"static", []byte{0xFF, 0x55, 0x07, 0x00, 0x02, 0x23, 0x00}},
		{"scrollLeft", []byte{0xFF, 0x55, 0x07, 0x00, 0x02, 0x23, 0x01}},
		{"scrollRight", []byte{0xFF, 0x55, 0x07, 0x00, 0x02, 0x23, 0x02}},
		{"flashing", []byte{0xFF, 0x55, 0x07, 0x00, 0x02, 0x23, 0x03}},
		// Case insensitivity / normalization
		{"SCROLLLEFT", []byte{0xFF, 0x55, 0x07, 0x00, 0x02, 0x23, 0x01}},
		{"scroll-left", []byte{0xFF, 0x55, 0x07, 0x00, 0x02, 0x23, 0x01}},
	}
	for _, tc := range cases {
		t.Run(tc.mode, func(t *testing.T) {
			got, err := BuildSetMode(tc.mode)
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if !bytes.Equal(got, tc.want) {
				t.Errorf("got % X, want % X", got, tc.want)
			}
		})
	}

	if _, err := BuildSetMode("nonsense"); err == nil {
		t.Error("expected error for invalid mode")
	}
}

func TestBuildSetAutoOff(t *testing.T) {
	// All 5 valid codes
	for code := byte(0); code <= 4; code++ {
		got, err := BuildSetAutoOff(code)
		if err != nil {
			t.Fatalf("code %d: unexpected error: %v", code, err)
		}
		want := []byte{0xFF, 0x55, 0x07, 0x00, 0x02, 0x27, code}
		if !bytes.Equal(got, want) {
			t.Errorf("code %d: got % X, want % X", code, got, want)
		}
	}
	// Out-of-range rejected
	if _, err := BuildSetAutoOff(5); err == nil {
		t.Error("expected error for code 5")
	}
	if _, err := BuildSetAutoOff(255); err == nil {
		t.Error("expected error for code 255")
	}
}

func TestBuildFactoryReset(t *testing.T) {
	// Critical: function byte is 0x01 (read), even though it's a
	// write-style trigger. Matches APK exactly. If Go "fixes" it to
	// 0x02, the cup ignores the command.
	want := []byte{0xFF, 0x55, 0x06, 0x00, 0x01, 0xFC}
	got := BuildFactoryReset()
	if !bytes.Equal(got, want) {
		t.Errorf("got % X, want % X", got, want)
	}
	if got[4] != 0x01 {
		t.Errorf("function byte must be 0x01 (read) per APK quirk, got 0x%02X", got[4])
	}
}

func TestBuildSetStaticImage(t *testing.T) {
	bm := make([]byte, BitmapBytes)
	for i := range bm {
		bm[i] = byte(i)
	}
	got, err := BuildSetStaticImage(bm)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(got) != 78 {
		t.Errorf("frame must be 78 bytes (header 6 + bitmap 72), got %d", len(got))
	}
	header := got[:6]
	want := []byte{0xFF, 0x55, 0x4E, 0x00, 0x02, 0x25}
	if !bytes.Equal(header, want) {
		t.Errorf("header got % X, want % X", header, want)
	}
	if !bytes.Equal(got[6:], bm) {
		t.Error("payload not preserved verbatim")
	}

	// Wrong-size bitmap rejected
	if _, err := BuildSetStaticImage(make([]byte, 71)); err == nil {
		t.Error("expected error for short bitmap")
	}
	if _, err := BuildSetStaticImage(make([]byte, 73)); err == nil {
		t.Error("expected error for long bitmap")
	}
}

func TestBuildAnimationPrologue(t *testing.T) {
	got := BuildAnimationPrologue(3, 130)
	want := []byte{0xFF, 0x55, 0x08, 0x00, 0x02, 0x26, 0x03, 0x82}
	if !bytes.Equal(got, want) {
		t.Errorf("got % X, want % X", got, want)
	}
	if len(got) != 8 {
		t.Errorf("prologue must be 8 bytes, got %d", len(got))
	}
}

func TestBuildAnimationFrame(t *testing.T) {
	bm := make([]byte, BitmapBytes)
	for i := range bm {
		bm[i] = byte(i ^ 0x55)
	}
	got, err := BuildAnimationFrame(7, 200, bm)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(got) != 80 {
		t.Errorf("frame command must be 80 bytes, got %d", len(got))
	}
	want := []byte{0xFF, 0x55, 0x50, 0x00, 0x02, 0x26, 0x07, 0xC8}
	if !bytes.Equal(got[:8], want) {
		t.Errorf("header got % X, want % X", got[:8], want)
	}
	if !bytes.Equal(got[8:], bm) {
		t.Error("bitmap payload not preserved verbatim")
	}

	if _, err := BuildAnimationFrame(0, 100, make([]byte, 71)); err == nil {
		t.Error("expected error for short bitmap")
	}
}

func TestBuildSetGreeting(t *testing.T) {
	// Empty string → subcmd 0x00, no payload. Length = 7.
	t.Run("empty clears", func(t *testing.T) {
		got := BuildSetGreeting("")
		want := []byte{0xFF, 0x55, 0x07, 0x00, 0x02, 0x17, 0x00}
		if !bytes.Equal(got, want) {
			t.Errorf("got % X, want % X", got, want)
		}
	})

	// "Hi" → subcmd 0x01, then UTF-16BE bytes 0x00 0x48 0x00 0x69.
	// Total length = 6 + 1 + 4 = 11 = 0x0B.
	t.Run("simple ASCII", func(t *testing.T) {
		got := BuildSetGreeting("Hi")
		want := []byte{0xFF, 0x55, 0x0B, 0x00, 0x02, 0x17, 0x01, 0x00, 0x48, 0x00, 0x69}
		if !bytes.Equal(got, want) {
			t.Errorf("got % X, want % X", got, want)
		}
	})

	// CJK character: 你 = U+4F60 → 0x4F 0x60.
	t.Run("CJK", func(t *testing.T) {
		got := BuildSetGreeting("你")
		want := []byte{0xFF, 0x55, 0x09, 0x00, 0x02, 0x17, 0x01, 0x4F, 0x60}
		if !bytes.Equal(got, want) {
			t.Errorf("got % X, want % X", got, want)
		}
	})

	// Length byte equals total frame length.
	t.Run("length byte correct", func(t *testing.T) {
		got := BuildSetGreeting("Hello, world!")
		if int(got[2]) != len(got) {
			t.Errorf("length byte 0x%02X != actual length %d", got[2], len(got))
		}
	})
}

func TestUTF16BEBytes(t *testing.T) {
	cases := []struct {
		s    string
		want []byte
	}{
		{"", []byte{}},
		{"H", []byte{0x00, 0x48}},
		{"Hi", []byte{0x00, 0x48, 0x00, 0x69}},
		{"你", []byte{0x4F, 0x60}},
		// Non-BMP: 🍵 (TEAPOT) = U+1F375 → surrogate pair
		// U+1F375 - 0x10000 = 0xF375; high = 0xD800+0x3C = 0xD83C; low = 0xDC00+0x375 = 0xDF75.
		{"🍵", []byte{0xD8, 0x3C, 0xDF, 0x75}},
	}
	for _, tc := range cases {
		got := UTF16BEBytes(tc.s)
		if !bytes.Equal(got, tc.want) {
			t.Errorf("UTF16BEBytes(%q): got % X, want % X", tc.s, got, tc.want)
		}
	}
}

func TestPackBitmap(t *testing.T) {
	// All-off → 72 zero bytes.
	t.Run("all off", func(t *testing.T) {
		grid := blankGrid()
		got, err := PackBitmap(grid)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if len(got) != BitmapBytes {
			t.Errorf("must be %d bytes, got %d", BitmapBytes, len(got))
		}
		for i, b := range got {
			if b != 0 {
				t.Errorf("byte %d: got 0x%02X, want 0x00", i, b)
				break
			}
		}
	})

	// All-on → 72 0xFF bytes.
	t.Run("all on", func(t *testing.T) {
		grid := blankGrid()
		for r := range grid {
			for c := range grid[r] {
				grid[r][c] = true
			}
		}
		got, err := PackBitmap(grid)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		for i, b := range got {
			if b != 0xFF {
				t.Errorf("byte %d: got 0x%02X, want 0xFF", i, b)
				break
			}
		}
	})

	// Single pixel at (0,0) — top-left LED. MSB-first → first byte = 0x80.
	// Verified empirically against fw 1.6 hardware (PROTOCOL_SPEC.md §4.5).
	t.Run("top-left pixel", func(t *testing.T) {
		grid := blankGrid()
		grid[0][0] = true
		got, err := PackBitmap(grid)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if got[0] != 0x80 {
			t.Errorf("byte 0: got 0x%02X, want 0x80", got[0])
		}
		for i := 1; i < len(got); i++ {
			if got[i] != 0 {
				t.Errorf("byte %d unexpectedly set: 0x%02X", i, got[i])
				break
			}
		}
	})

	// Single pixel at (0,7) — last bit of first byte. MSB-first → 0x01.
	t.Run("first-byte last bit", func(t *testing.T) {
		grid := blankGrid()
		grid[0][7] = true
		got, err := PackBitmap(grid)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if got[0] != 0x01 {
			t.Errorf("byte 0: got 0x%02X, want 0x01", got[0])
		}
	})

	// Single pixel at (1,0) — start of row 2 = bit index 48 = byte 6 bit 7.
	t.Run("row-major scan order", func(t *testing.T) {
		grid := blankGrid()
		grid[1][0] = true
		got, err := PackBitmap(grid)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if got[6] != 0x80 {
			t.Errorf("byte 6: got 0x%02X, want 0x80 (row 2 col 0 should land here)", got[6])
		}
	})

	// Single pixel at (11,47) — bottom-right LED = bit 575 = byte 71 bit 0 = 0x01.
	t.Run("bottom-right pixel", func(t *testing.T) {
		grid := blankGrid()
		grid[11][47] = true
		got, err := PackBitmap(grid)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if got[71] != 0x01 {
			t.Errorf("byte 71: got 0x%02X, want 0x01", got[71])
		}
	})

	// Wrong dimensions rejected.
	t.Run("rejects wrong-shape grid", func(t *testing.T) {
		short := make([][]bool, ImageHeight-1)
		for i := range short {
			short[i] = make([]bool, ImageWidth)
		}
		if _, err := PackBitmap(short); err == nil {
			t.Error("expected error for short grid")
		}

		uneven := blankGrid()
		uneven[3] = make([]bool, ImageWidth-1)
		if _, err := PackBitmap(uneven); err == nil {
			t.Error("expected error for uneven row")
		}
	})
}

func TestParseResponse(t *testing.T) {
	cases := []struct {
		name string
		raw  []byte
		want []byte
	}{
		{
			"valid envelope",
			[]byte{0xFF, 0x55, 0x05, 0x01, 0x1F, 0x0D, 0x0A},
			[]byte{0x05, 0x01, 0x1F},
		},
		{
			"missing terminator → returned as-is",
			[]byte{0xFF, 0x55, 0x05, 0x01, 0x1F},
			[]byte{0xFF, 0x55, 0x05, 0x01, 0x1F},
		},
		{
			"empty",
			[]byte{},
			[]byte{},
		},
		{
			"too short for envelope check",
			[]byte{0xFF, 0x55},
			[]byte{0xFF, 0x55},
		},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got := ParseResponse(tc.raw)
			if !bytes.Equal(got, tc.want) {
				t.Errorf("got % X, want % X", got, tc.want)
			}
		})
	}
}

func TestValidateFrameCount(t *testing.T) {
	cases := []struct {
		n       int
		wantErr string // substring match; empty = expect no error
	}{
		{0, "at least one"},
		{1, ""},
		{132, ""},        // exactly the cup limit
		{133, "fw 1.7"},  // first invalid
		{255, "fw 1.7"},  // protocol max but cup-limited
		{256, "max 255"}, // protocol violation
	}
	for _, tc := range cases {
		err := ValidateFrameCount(tc.n)
		if tc.wantErr == "" {
			if err != nil {
				t.Errorf("n=%d: unexpected error %v", tc.n, err)
			}
			continue
		}
		if err == nil {
			t.Errorf("n=%d: expected error matching %q, got nil", tc.n, tc.wantErr)
			continue
		}
		if !strings.Contains(err.Error(), tc.wantErr) {
			t.Errorf("n=%d: error %q does not contain %q", tc.n, err.Error(), tc.wantErr)
		}
	}
}

func TestIsValidSpeed(t *testing.T) {
	for _, ok := range []int{1, 2, 130, 200, 255} {
		if err := IsValidSpeed(ok); err != nil {
			t.Errorf("speed %d should be valid, got %v", ok, err)
		}
	}
	for _, bad := range []int{-1, 0, 256, 1000} {
		if err := IsValidSpeed(bad); err == nil {
			t.Errorf("speed %d should be rejected", bad)
		}
	}
}

func TestErrResponseTimeoutSentinel(t *testing.T) {
	// Wrappers should be detectable via errors.Is, not string match.
	wrapped := errors.Join(errors.New("upstream"), ErrResponseTimeout)
	if !errors.Is(wrapped, ErrResponseTimeout) {
		t.Error("wrapped ErrResponseTimeout not detectable via errors.Is")
	}
}

// blankGrid returns a 12×48 boolean grid initialized to all-false.
func blankGrid() [][]bool {
	g := make([][]bool, ImageHeight)
	for i := range g {
		g[i] = make([]bool, ImageWidth)
	}
	return g
}
