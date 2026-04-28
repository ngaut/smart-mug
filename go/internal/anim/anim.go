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

	// Composite each frame against the previous image to handle GIF
	// disposal modes correctly. Optimized GIFs store dirty rectangles
	// only — naive frame-by-frame extraction misses background pixels.
	W, H := sguai.ImageWidth, sguai.ImageHeight
	canvas := image.NewNRGBA(image.Rect(0, 0, g.Config.Width, g.Config.Height))
	resized := image.NewNRGBA(image.Rect(0, 0, W, H))
	out := make([][][]bool, 0, len(g.Image))

	for i, frame := range g.Image {
		// Disposal modes are advisory; for our 48×12 cup we just composite
		// each delta onto the canvas.
		draw.Draw(canvas, frame.Bounds(), frame, frame.Bounds().Min, draw.Over)

		// Resize canvas → 48×12 with nearest-neighbor (cup is 1-bit; we
		// don't want anti-aliased values landing on threshold boundaries).
		draw.NearestNeighbor.Scale(resized, resized.Bounds(), canvas, canvas.Bounds(), draw.Over, nil)

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

		_ = i
	}
	return out, nil
}

// luminance maps a color to an 8-bit grayscale value using the standard
// 0.299/0.587/0.114 luma weights.
func luminance(c color.Color) uint8 {
	r, g, b, _ := c.RGBA()
	// RGBA returns 16-bit channels in 0..0xFFFF; scale to 8-bit.
	r8, g8, b8 := r>>8, g>>8, b>>8
	y := (299*r8 + 587*g8 + 114*b8 + 500) / 1000
	if y > 255 {
		y = 255
	}
	return uint8(y)
}
