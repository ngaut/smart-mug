package main

import "testing"

func TestParseModeCanonical(t *testing.T) {
	cases := map[string]string{
		"static":      "static",
		"scrollLeft":  "scrollLeft",
		"scrollRight": "scrollRight",
		"flashing":    "flashing",
	}
	for in, want := range cases {
		got, err := parseModeArg(in)
		if err != nil {
			t.Errorf("%s: unexpected error: %v", in, err)
		}
		if got != want {
			t.Errorf("%s: got %q, want %q", in, got, want)
		}
	}
}

func TestParseModeFriendlySynonyms(t *testing.T) {
	cases := map[string]string{
		"left":    "scrollLeft",
		"right":   "scrollRight",
		"blink":   "flashing",
		"flash":   "flashing",
		"twinkle": "flashing",
		"fixed":   "static",
		"still":   "static",
	}
	for in, want := range cases {
		got, err := parseModeArg(in)
		if err != nil {
			t.Errorf("%s: unexpected error: %v", in, err)
		}
		if got != want {
			t.Errorf("%s: got %q, want %q", in, got, want)
		}
	}
}

func TestParseModePunctuationAndCase(t *testing.T) {
	cases := map[string]string{
		"Scroll-Left":  "scrollLeft",
		"SCROLL_LEFT":  "scrollLeft",
		"scroll left":  "scrollLeft",
		"Shift Right":  "scrollRight",
	}
	for in, want := range cases {
		got, err := parseModeArg(in)
		if err != nil {
			t.Errorf("%s: unexpected error: %v", in, err)
		}
		if got != want {
			t.Errorf("%s: got %q, want %q", in, got, want)
		}
	}
}

func TestParseModeRawBytes(t *testing.T) {
	cases := map[string]string{
		"0": "static", "1": "scrollLeft", "2": "scrollRight", "3": "flashing",
	}
	for in, want := range cases {
		got, _ := parseModeArg(in)
		if got != want {
			t.Errorf("%s: got %q, want %q", in, got, want)
		}
	}
}

func TestParseModeRejectsGarbage(t *testing.T) {
	for _, bad := range []string{"upside-down", "diagonal", "5", "", "fast"} {
		if _, err := parseModeArg(bad); err == nil {
			t.Errorf("expected error for %q", bad)
		}
	}
}

func TestParseSpeedPresets(t *testing.T) {
	cases := map[string]byte{
		"slowest": 5, "slow": 50,
		"medium": 130, "normal": 130, "default": 130,
		"fast": 200, "fastest": 255,
	}
	for in, want := range cases {
		got, err := parseSpeedArg(in)
		if err != nil {
			t.Errorf("%s: unexpected error: %v", in, err)
		}
		if got != want {
			t.Errorf("%s: got %d, want %d", in, got, want)
		}
	}
}

func TestParseSpeedRawByte(t *testing.T) {
	cases := map[string]byte{"1": 1, "130": 130, "255": 255}
	for in, want := range cases {
		got, err := parseSpeedArg(in)
		if err != nil {
			t.Errorf("%s: unexpected error: %v", in, err)
		}
		if got != want {
			t.Errorf("%s: got %d, want %d", in, got, want)
		}
	}
}

func TestParseSpeedMilliseconds(t *testing.T) {
	// ms_per_frame = 10 * (260 - speed)  →  speed = 260 - ms/10
	cases := map[string]byte{
		"1300ms": 130, // 260 - 130 = 130
		"600ms":  200, // 260 - 60 = 200
		"50ms":   255, // 260 - 5 = 255
	}
	for in, want := range cases {
		got, err := parseSpeedArg(in)
		if err != nil {
			t.Errorf("%s: unexpected error: %v", in, err)
		}
		if got != want {
			t.Errorf("%s: got %d, want %d", in, got, want)
		}
	}
}

func TestParseSpeedSeconds(t *testing.T) {
	cases := map[string]byte{
		"1.3s": 130, "0.6s": 200, "2.5s": 10,
	}
	for in, want := range cases {
		got, err := parseSpeedArg(in)
		if err != nil {
			t.Errorf("%s: unexpected error: %v", in, err)
		}
		if got != want {
			t.Errorf("%s: got %d, want %d", in, got, want)
		}
	}
}

func TestParseSpeedFPS(t *testing.T) {
	cases := map[string]byte{
		"2fps":  210, // 1000/2 = 500ms → 260 - 50 = 210
		"10fps": 250, // 1000/10 = 100ms → 260 - 10 = 250
	}
	for in, want := range cases {
		got, err := parseSpeedArg(in)
		if err != nil {
			t.Errorf("%s: unexpected error: %v", in, err)
		}
		if got != want {
			t.Errorf("%s: got %d, want %d", in, got, want)
		}
	}
}

func TestParseSpeedCaseInsensitive(t *testing.T) {
	cases := map[string]byte{
		"MEDIUM": 130, "Slow": 50, "1300MS": 130,
	}
	for in, want := range cases {
		got, err := parseSpeedArg(in)
		if err != nil {
			t.Errorf("%s: unexpected error: %v", in, err)
		}
		if got != want {
			t.Errorf("%s: got %d, want %d", in, got, want)
		}
	}
}

func TestParseSpeedRejectsGarbage(t *testing.T) {
	for _, bad := range []string{"", "fastfast", "0", "-1", "256", "0fps", "9999ms"} {
		if _, err := parseSpeedArg(bad); err == nil {
			t.Errorf("expected error for %q", bad)
		}
	}
}
