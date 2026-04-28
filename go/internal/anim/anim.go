// Package anim loads animation frames from GIF files into the boolean
// 12×48 grids the SGUAI cup expects. Uses Go's standard library
// image/gif decoder.
package anim

import (
	"fmt"
	"image"
	"image/color"
	"image/gif"
	"os"

	"github.com/ngaut/smart-mug/go/internal/sguai"

	"golang.org/x/image/draw"
)

// LoadGIF reads a GIF file and returns its frames as []bool grids
// (Height × Width). Frames are resized to 48×12, converted to grayscale,
// and thresholded. The threshold convention matches the Python
// implementation: source-bright pixels (≥ threshold) → grid value true
// (LED on); source-dark → false. Use invert=true to flip polarity for
// black-on-white logos.
//
// GIF disposal modes are honored: dispose=0/1 keeps the previous frame
// as background, dispose=2 restores the canvas to the GIF's background
// color in the dirty rect, and dispose=3 restores the previous frame.
// Without this, optimized GIFs (the typical case) render with stale
// pixel ghosts.
func LoadGIF(path string, threshold uint8, invert bool) ([][][]bool, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	g, err := gif.DecodeAll(f)
	if err != nil {
		return nil, fmt.Errorf("decode %s: %w", path, err)
	}
	if len(g.Image) == 0 {
		return nil, fmt.Errorf("%s: no frames", path)
	}

	W, H := sguai.ImageWidth, sguai.ImageHeight
	canvas := image.NewNRGBA(image.Rect(0, 0, g.Config.Width, g.Config.Height))
	// Snapshot of the canvas BEFORE the current frame is drawn — used
	// to support dispose=3 (restore-previous).
	previous := image.NewNRGBA(canvas.Bounds())
	resized := image.NewNRGBA(image.Rect(0, 0, W, H))

	bg := color.NRGBA{0, 0, 0, 0}
	if g.BackgroundIndex < uint8(len(g.Image[0].Palette)) {
		if c, ok := g.Image[0].Palette[g.BackgroundIndex].(color.RGBA); ok {
			bg = color.NRGBA{c.R, c.G, c.B, c.A}
		}
	}

	out := make([][][]bool, 0, len(g.Image))
	for i, frame := range g.Image {
		// Save snapshot for possible dispose=3 next iteration.
		copy(previous.Pix, canvas.Pix)

		dirty := frame.Bounds()
		// Composite this delta onto the canvas. Use draw.Over to honor
		// transparency in the GIF frame.
		draw.Draw(canvas, dirty, frame, dirty.Min, draw.Over)

		// Render canvas → 48×12 with nearest-neighbor + draw.Src so the
		// resized buffer is fully replaced (no leftover pixels from
		// the previous iteration ghosting through).
		draw.NearestNeighbor.Scale(resized, resized.Bounds(), canvas, canvas.Bounds(), draw.Src, nil)

		grid := make([][]bool, H)
		for y := 0; y < H; y++ {
			row := make([]bool, W)
			for x := 0; x < W; x++ {
				gray := luminance(resized.At(x, y))
				on := gray >= threshold
				if invert {
					on = !on
				}
				row[x] = on
			}
			grid[y] = row
		}
		out = append(out, grid)

		// Apply this frame's disposal so the NEXT frame composites
		// onto the right starting state.
		if i < len(g.Disposal) {
			switch g.Disposal[i] {
			case gif.DisposalBackground:
				// Restore the dirty rect to background color.
				fillRect(canvas, dirty, bg)
			case gif.DisposalPrevious:
				// Restore the dirty rect from the pre-frame snapshot.
				draw.Draw(canvas, dirty, previous, dirty.Min, draw.Src)
			default:
				// gif.DisposalNone or DisposalKeep — leave canvas as-is.
			}
		}
	}
	return out, nil
}

// fillRect fills `r` (clipped to dst.Bounds()) with c.
func fillRect(dst *image.NRGBA, r image.Rectangle, c color.NRGBA) {
	r = r.Intersect(dst.Bounds())
	for y := r.Min.Y; y < r.Max.Y; y++ {
		for x := r.Min.X; x < r.Max.X; x++ {
			dst.SetNRGBA(x, y, c)
		}
	}
}

// luminance maps a color to an 8-bit grayscale value using the standard
// 0.299/0.587/0.114 luma weights.
func luminance(c color.Color) uint8 {
	r, g, b, _ := c.RGBA()
	r8, g8, b8 := r>>8, g>>8, b>>8
	y := (299*r8 + 587*g8 + 114*b8 + 500) / 1000
	if y > 255 {
		y = 255
	}
	return uint8(y)
}
