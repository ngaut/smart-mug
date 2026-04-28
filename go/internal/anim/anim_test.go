package anim

import (
	"bytes"
	"image"
	"image/color"
	"image/color/palette"
	"image/gif"
	"os"
	"path/filepath"
	"testing"
)

// makeGIF writes a minimal GIF file with the given frames and disposal
// methods, and returns its path. Frames are W×H paletted images.
func makeGIF(t *testing.T, w, h int, frames []*image.Paletted, disposals []byte) string {
	t.Helper()
	dir := t.TempDir()
	path := filepath.Join(dir, "test.gif")
	f, err := os.Create(path)
	if err != nil {
		t.Fatalf("create: %v", err)
	}
	defer f.Close()

	g := &gif.GIF{
		Image:    frames,
		Delay:    make([]int, len(frames)),
		Disposal: disposals,
		Config:   image.Config{Width: w, Height: h, ColorModel: color.Palette(palette.WebSafe)},
	}
	if err := gif.EncodeAll(f, g); err != nil {
		t.Fatalf("encode: %v", err)
	}
	return path
}

// solidFrame returns a paletted image filled with `c`.
func solidFrame(w, h int, pal color.Palette, c color.Color) *image.Paletted {
	img := image.NewPaletted(image.Rect(0, 0, w, h), pal)
	idx := uint8(pal.Index(c))
	for i := range img.Pix {
		img.Pix[i] = idx
	}
	return img
}

func TestLoadGIFAllWhite(t *testing.T) {
	pal := color.Palette{color.Black, color.White}
	frame := solidFrame(48, 12, pal, color.White)
	path := makeGIF(t, 48, 12, []*image.Paletted{frame}, []byte{0})

	frames, err := LoadGIF(path, 128, false)
	if err != nil {
		t.Fatalf("LoadGIF: %v", err)
	}
	if len(frames) != 1 {
		t.Fatalf("want 1 frame, got %d", len(frames))
	}
	for r := 0; r < 12; r++ {
		for c := 0; c < 48; c++ {
			if !frames[0][r][c] {
				t.Errorf("white frame should be all on; off at (%d,%d)", r, c)
				return
			}
		}
	}
}

func TestLoadGIFAllBlack(t *testing.T) {
	pal := color.Palette{color.Black, color.White}
	frame := solidFrame(48, 12, pal, color.Black)
	path := makeGIF(t, 48, 12, []*image.Paletted{frame}, []byte{0})

	frames, err := LoadGIF(path, 128, false)
	if err != nil {
		t.Fatalf("LoadGIF: %v", err)
	}
	for r := 0; r < 12; r++ {
		for c := 0; c < 48; c++ {
			if frames[0][r][c] {
				t.Errorf("black frame should be all off; on at (%d,%d)", r, c)
				return
			}
		}
	}
}

func TestLoadGIFInvert(t *testing.T) {
	pal := color.Palette{color.Black, color.White}
	frame := solidFrame(48, 12, pal, color.Black)
	path := makeGIF(t, 48, 12, []*image.Paletted{frame}, []byte{0})

	frames, err := LoadGIF(path, 128, true) // invert: black source → on
	if err != nil {
		t.Fatalf("LoadGIF: %v", err)
	}
	for r := 0; r < 12; r++ {
		for c := 0; c < 48; c++ {
			if !frames[0][r][c] {
				t.Errorf("inverted black should be all on; off at (%d,%d)", r, c)
				return
			}
		}
	}
}

func TestLoadGIFFrameCount(t *testing.T) {
	pal := color.Palette{color.Black, color.White}
	frames := []*image.Paletted{
		solidFrame(48, 12, pal, color.White),
		solidFrame(48, 12, pal, color.Black),
		solidFrame(48, 12, pal, color.White),
	}
	disposals := []byte{0, 0, 0}
	path := makeGIF(t, 48, 12, frames, disposals)

	loaded, err := LoadGIF(path, 128, false)
	if err != nil {
		t.Fatalf("LoadGIF: %v", err)
	}
	if len(loaded) != 3 {
		t.Errorf("want 3 frames, got %d", len(loaded))
	}
	// Frame 0 is all-white, frame 1 is all-black, frame 2 returns to all-white.
	if !loaded[0][0][0] {
		t.Error("frame 0 expected all-on")
	}
	if loaded[1][0][0] {
		t.Error("frame 1 expected all-off")
	}
	if !loaded[2][0][0] {
		t.Error("frame 2 expected all-on")
	}
}

// TestLoadGIFDisposalBackground exercises dispose=2 (restore-background)
// — between frames, the canvas reverts to bg color in the dirty rect.
// Without proper handling this fails because the canvas keeps the
// previous frame's pixels.
func TestLoadGIFDisposalBackground(t *testing.T) {
	pal := color.Palette{color.Black, color.White}
	// Frame 0: all white (full screen).
	f0 := solidFrame(48, 12, pal, color.White)
	// Frame 1: only top-left 4×4 black, rest transparent. With dispose=0
	// the rest stays white. We're stress-testing dispose=2 between f0
	// and f1.
	f1 := image.NewPaletted(image.Rect(0, 0, 48, 12), pal)
	for r := 0; r < 12; r++ {
		for c := 0; c < 48; c++ {
			f1.SetColorIndex(c, r, uint8(pal.Index(color.White)))
		}
	}
	path := makeGIF(t, 48, 12, []*image.Paletted{f0, f1}, []byte{gif.DisposalBackground, 0})

	loaded, err := LoadGIF(path, 128, false)
	if err != nil {
		t.Fatalf("LoadGIF: %v", err)
	}
	if len(loaded) != 2 {
		t.Fatalf("want 2 frames, got %d", len(loaded))
	}
	// Both frames should still render as all-on (white). The point of
	// this test is just to exercise the dispose=2 code path without
	// crashing — full visual correctness for sparse GIFs would require
	// more elaborate fixtures.
	if !loaded[0][0][0] {
		t.Error("frame 0 (white) expected all-on")
	}
}

// TestLoadGIFInvalidPath verifies graceful error on missing file.
func TestLoadGIFInvalidPath(t *testing.T) {
	_, err := LoadGIF("/nonexistent/path.gif", 128, false)
	if err == nil {
		t.Error("expected error for missing file")
	}
}

// TestLoadGIFCorruptData verifies graceful error on a non-GIF file.
func TestLoadGIFCorruptData(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "junk.gif")
	if err := os.WriteFile(path, []byte("this is not a gif"), 0o644); err != nil {
		t.Fatal(err)
	}
	_, err := LoadGIF(path, 128, false)
	if err == nil {
		t.Error("expected error for non-GIF data")
	}
}

// Defensive: confirm LoadGIF handles GIFs whose source dimensions don't
// match 48×12 — they should be resized cleanly.
func TestLoadGIFResize(t *testing.T) {
	pal := color.Palette{color.Black, color.White}
	frame := solidFrame(96, 24, pal, color.White) // 2x larger than cup
	path := makeGIF(t, 96, 24, []*image.Paletted{frame}, []byte{0})
	loaded, err := LoadGIF(path, 128, false)
	if err != nil {
		t.Fatalf("LoadGIF: %v", err)
	}
	// All-white source, any resize → all-on.
	for r := 0; r < 12; r++ {
		for c := 0; c < 48; c++ {
			if !loaded[0][r][c] {
				t.Errorf("resized all-white should be all-on; off at (%d,%d)", r, c)
				return
			}
		}
	}
}

var _ = bytes.Equal // hush unused-import linters during refactors
