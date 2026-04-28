package sguai

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"time"

	"tinygo.org/x/bluetooth"
)

// Default timeouts. The 10s execute timeout matches Python's
// set_dynamic_mode / set_auto_off; the 5s read timeout matches reads.
const (
	readTimeout    = 5 * time.Second
	executeTimeout = 10 * time.Second

	// Animation upload pacing — matches the official APK and Python.
	animPrologueDelay = 100 * time.Millisecond
	animFrameDelay    = 150 * time.Millisecond
	animRetryBackoff  = 100 * time.Millisecond
	animMaxRetries    = 10
)

// ErrResponseTimeout is returned when ExecuteCommand doesn't receive a
// notification within the deadline. Use ``errors.Is(err, ErrResponseTimeout)``
// rather than string matching.
var ErrResponseTimeout = errors.New("device response timeout")

// ReadVersion returns the cup's firmware version as "X.Y" (e.g. "1.7").
func (c *Client) ReadVersion(ctx context.Context) (string, error) {
	resp, err := c.ExecuteCommand(ctx, BuildReadCommand(FeatureVersion), readTimeout)
	if err != nil {
		return "", err
	}
	if len(resp) >= 2 {
		return fmt.Sprintf("%d.%d", resp[len(resp)-2], resp[len(resp)-1]), nil
	}
	return "", fmt.Errorf("short version response: % x", resp)
}

// ReadBattery returns the battery percent (0..100).
func (c *Client) ReadBattery(ctx context.Context) (int, error) {
	resp, err := c.ExecuteCommand(ctx, BuildReadCommand(FeatureBattery), readTimeout)
	if err != nil {
		return 0, err
	}
	if len(resp) == 0 {
		return 0, errors.New("empty battery response")
	}
	return int(resp[len(resp)-1]), nil
}

// ReadTemperature returns the cup's liquid temperature (°C, unsigned).
func (c *Client) ReadTemperature(ctx context.Context) (int, error) {
	resp, err := c.ExecuteCommand(ctx, BuildReadCommand(FeatureTemperature), readTimeout)
	if err != nil {
		return 0, err
	}
	if len(resp) == 0 {
		return 0, errors.New("empty temperature response")
	}
	return int(resp[len(resp)-1]), nil
}

// ReadAutoOff returns the auto-screen-off duration code (0..4). See
// AutoOffCodes for the human label of each code.
func (c *Client) ReadAutoOff(ctx context.Context) (byte, error) {
	resp, err := c.ExecuteCommand(ctx, BuildReadAutoOff(), readTimeout)
	if err != nil {
		return 0, err
	}
	if len(resp) == 0 {
		return 0, errors.New("empty auto-off response")
	}
	return resp[len(resp)-1], nil
}

// SetAutoOff writes the auto-screen-off duration code (0..4).
// See PROTOCOL_SPEC.md §4.7. Codes outside 0..4 are silently rejected
// by firmware so we validate client-side.
func (c *Client) SetAutoOff(ctx context.Context, code byte) error {
	cmd, err := BuildSetAutoOff(code)
	if err != nil {
		return err
	}
	// Like setDynamicMode, the cup occasionally drops the echo
	// notification on a config write — we treat the timeout as success
	// because the BLE-layer ACK is already sufficient.
	if _, err := c.ExecuteCommand(ctx, cmd, executeTimeout); err != nil {
		if errors.Is(err, ErrResponseTimeout) {
			return nil
		}
		return err
	}
	return nil
}

// ReadDynamicSpeed returns the persistent dynamic-speed setting
// (feature 0x24). See SetDynamicSpeed for the semantic relationship
// to the per-animation speed byte in the 0x26 prologue.
func (c *Client) ReadDynamicSpeed(ctx context.Context) (byte, error) {
	resp, err := c.ExecuteCommand(ctx, BuildReadDynamicSpeed(), readTimeout)
	if err != nil {
		return 0, err
	}
	if len(resp) == 0 {
		return 0, errors.New("empty dynamic-speed response")
	}
	return resp[len(resp)-1], nil
}

// SetDynamicSpeed writes the persistent dynamic-speed setting
// (feature 0x24). speed range 1..255, larger = faster. This is a
// SEPARATE firmware variable from the per-animation speed byte in
// the 0x26 prologue; the APK's UI slider drives both at once but
// they're independent on the cup.
func (c *Client) SetDynamicSpeed(ctx context.Context, speed byte) error {
	cmd, err := BuildSetDynamicSpeed(speed)
	if err != nil {
		return err
	}
	if _, err := c.ExecuteCommand(ctx, cmd, executeTimeout); err != nil {
		// Cup occasionally drops the echo notification on a config
		// write — same pattern as SetDynamicMode and SetAutoOff.
		if errors.Is(err, ErrResponseTimeout) {
			return nil
		}
		return err
	}
	return nil
}

// SetDynamicMode writes the display motion mode (static / scrollRight /
// scrollLeft / flashing).
func (c *Client) SetDynamicMode(ctx context.Context, mode string) error {
	cmd, err := BuildSetMode(mode)
	if err != nil {
		return err
	}
	if _, err := c.ExecuteCommand(ctx, cmd, executeTimeout); err != nil {
		if errors.Is(err, ErrResponseTimeout) {
			return nil
		}
		return err
	}
	return nil
}

// SetGreeting uploads a greeting string. Empty string clears.
func (c *Client) SetGreeting(_ context.Context, msg string) error {
	return c.Write(BuildSetGreeting(msg))
}

// SetImageData uploads a static image. The cup persists this in the
// static-image slot; it's displayed when no animation is playing.
func (c *Client) SetImageData(_ context.Context, grid [][]bool) error {
	bm, err := PackBitmap(grid)
	if err != nil {
		return err
	}
	cmd, err := BuildSetStaticImage(bm)
	if err != nil {
		return err
	}
	return c.Write(cmd)
}

// SetAnimation uploads an animation: 8-byte prologue followed by N
// per-frame commands. Pre-validates frame count against both the
// protocol limit (255) and the empirical fw 1.7 buffer limit (132).
func (c *Client) SetAnimation(ctx context.Context, frames [][][]bool, speed int) error {
	if err := IsValidSpeed(speed); err != nil {
		return err
	}
	if err := ValidateFrameCount(len(frames)); err != nil {
		return err
	}

	// Pre-pack ALL frames before sending the prologue. A bad frame
	// mid-upload would leave the cup expecting more data than will
	// arrive — corrupted animation slot.
	bitmaps := make([][]byte, len(frames))
	for i, f := range frames {
		bm, err := PackBitmap(f)
		if err != nil {
			return fmt.Errorf("frame %d: %w", i, err)
		}
		bitmaps[i] = bm
	}

	c.mu.Lock()
	defer c.mu.Unlock()

	if err := c.writeLocked(BuildAnimationPrologue(byte(len(frames)), byte(speed))); err != nil {
		return fmt.Errorf("prologue write failed: %w", err)
	}
	time.Sleep(animPrologueDelay)

	startTime := time.Now()
	for idx, bm := range bitmaps {
		cmd, err := BuildAnimationFrame(byte(idx), byte(speed), bm)
		if err != nil {
			return err
		}
		if err := c.writeFrameWithRetry(cmd); err != nil {
			return fmt.Errorf("animation upload failed at frame %d/%d (after %d successful frames, ~%.1fs elapsed): %w",
				idx, len(frames), idx, time.Since(startTime).Seconds(), err)
		}
		if idx < len(frames)-1 {
			time.Sleep(animFrameDelay)
		}
		if err := ctx.Err(); err != nil {
			return err
		}
	}
	return nil
}

// writeFrameWithRetry mirrors the official's recursive
// writeBLECharacteristicValue: up to ANIM_MAX_RETRIES with backoff.
// Caller must hold c.mu.
func (c *Client) writeFrameWithRetry(cmd []byte) error {
	var lastErr error
	for attempt := 0; attempt < animMaxRetries; attempt++ {
		if err := c.writeLocked(cmd); err == nil {
			return nil
		} else {
			lastErr = err
		}
		time.Sleep(animRetryBackoff)
	}
	return lastErr
}

// FactoryReset sends 0xFC. The cup typically drops the GATT link as
// part of processing this, so we treat write-side errors as expected.
// See PROTOCOL_SPEC.md §4.8.
func (c *Client) FactoryReset(_ context.Context) error {
	c.mu.Lock()
	defer c.mu.Unlock()
	_ = c.writeLocked(BuildFactoryReset())
	return nil
}

// ReadDeviceInfo probes the standard BLE Device Information service
// (0x180A). Returns whatever characteristics the cup populates; on
// SGUAI-C3 fw 1.7 this comes back empty (verified 2026-04-26).
func (c *Client) ReadDeviceInfo(_ context.Context) (map[string]string, error) {
	out := map[string]string{}
	disUUID, _ := bluetooth.ParseUUID("0000180a-0000-1000-8000-00805f9b34fb")
	svcs, err := c.dev.DiscoverServices([]bluetooth.UUID{disUUID})
	if err != nil || len(svcs) == 0 {
		return out, nil // service not present — return empty, not error
	}

	type charSpec struct {
		uuid string
		key  string
		hex  bool
	}
	specs := []charSpec{
		{"00002a29-0000-1000-8000-00805f9b34fb", "manufacturer", false},
		{"00002a24-0000-1000-8000-00805f9b34fb", "model_number", false},
		{"00002a25-0000-1000-8000-00805f9b34fb", "serial_number", false},
		{"00002a26-0000-1000-8000-00805f9b34fb", "firmware_rev", false},
		{"00002a27-0000-1000-8000-00805f9b34fb", "hardware_rev", false},
		{"00002a28-0000-1000-8000-00805f9b34fb", "software_rev", false},
		{"00002a23-0000-1000-8000-00805f9b34fb", "system_id", true},
	}
	for _, s := range specs {
		uuid, _ := bluetooth.ParseUUID(s.uuid)
		chars, err := svcs[0].DiscoverCharacteristics([]bluetooth.UUID{uuid})
		if err != nil || len(chars) == 0 {
			continue
		}
		buf := make([]byte, 64)
		n, err := chars[0].Read(buf)
		if err != nil || n == 0 {
			continue
		}
		if s.hex {
			out[s.key] = fmt.Sprintf("%x", buf[:n])
		} else {
			out[s.key] = strings.TrimRight(string(buf[:n]), "\x00")
		}
	}
	return out, nil
}
