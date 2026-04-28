// Command mug is a Go reimplementation of the Python smart_mug.py CLI.
// Single binary, no daemon — Goroutines hold one BLE connection alive
// across all in-process operations, and the connection lifecycle is
// short enough per command that the cup-side §4.7 silent-BLE windows
// simply aren't visible to single-shot users.
package main

import (
	"context"
	"errors"
	"fmt"
	"os"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/ngaut/smart-mug/go/internal/anim"
	"github.com/ngaut/smart-mug/go/internal/cache"
	"github.com/ngaut/smart-mug/go/internal/sguai"
)

func main() {
	if len(os.Args) < 2 {
		printHelp()
		os.Exit(0)
	}

	cmd := os.Args[1]
	args := os.Args[2:]

	switch cmd {
	case "-h", "--help", "help":
		printHelp()
		return
	case "alias":
		os.Exit(cmdAlias(args))
	case "clear-cache":
		os.Exit(cmdClearCache())
	case "info":
		os.Exit(runWithClient(args, cmdInfo))
	case "read":
		os.Exit(runWithClient(args, cmdRead))
	case "auto-off":
		os.Exit(runWithClient(args, cmdAutoOff))
	case "speed", "dynamic-speed":
		os.Exit(runWithClient(args, cmdSpeed))
	case "greeting":
		os.Exit(runWithClient(args, cmdGreeting))
	case "mode":
		os.Exit(runWithClient(args, cmdMode))
	case "image":
		os.Exit(runWithClient(args, cmdImage))
	case "animate", "anim", "gif":
		os.Exit(runWithClient(args, cmdAnimate))
	case "reset", "factory-reset":
		os.Exit(runWithClient(args, cmdReset))
	default:
		fmt.Fprintf(os.Stderr, "Unknown command: %s\n\n", cmd)
		printHelp()
		os.Exit(1)
	}
}

// runWithClient handles the connect → run → disconnect lifecycle for
// commands that need an active BLE link. Resolves --addr/aliases and
// honors --rescan.
func runWithClient(args []string, fn func(context.Context, *sguai.Client, []string) error) int {
	useCache := !hasFlag(args, "--rescan")
	forceAddr := cache.Resolve(flagValue(args, "--addr"))

	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()

	a := sguai.NewAdapter()
	if err := a.Enable(); err != nil {
		fmt.Fprintf(os.Stderr, "Error: enable adapter: %v\n", err)
		return 1
	}

	addr, err := a.FindDevice(ctx, useCache, forceAddr)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		return 1
	}

	client, err := a.Connect(ctx, addr)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		return 1
	}
	defer client.Disconnect()

	if err := fn(ctx, client, args); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		return 1
	}
	return 0
}

// =============================================================================
// Subcommands
// =============================================================================

func cmdInfo(ctx context.Context, c *sguai.Client, _ []string) error {
	fmt.Println("\n=== BLE address ===")
	fmt.Printf("  address: %s\n", c.Address())

	fmt.Println("\n=== Device Information service (0x180A) ===")
	dis, _ := c.ReadDeviceInfo(ctx)
	if len(dis) == 0 {
		fmt.Println("  (no DIS characteristics populated)")
	} else {
		keys := make([]string, 0, len(dis))
		for k := range dis {
			keys = append(keys, k)
		}
		sort.Strings(keys)
		for _, k := range keys {
			fmt.Printf("  %s: %s\n", k, dis[k])
		}
	}

	fmt.Println("\n=== SGUAI protocol reads ===")
	if v, err := c.ReadVersion(ctx); err != nil {
		fmt.Printf("  firmware:    error (%v)\n", err)
	} else {
		fmt.Printf("  firmware:    %s\n", v)
	}
	if code, err := c.ReadAutoOff(ctx); err != nil {
		fmt.Printf("  auto-off:    error (%v)\n", err)
	} else {
		fmt.Printf("  auto-off:    code %d (%s)\n", code, sguai.AutoOffCodes[code])
	}
	if b, err := c.ReadBattery(ctx); err != nil {
		fmt.Printf("  battery:     error (%v)\n", err)
	} else {
		fmt.Printf("  battery:     %d%%\n", b)
	}
	if t, err := c.ReadTemperature(ctx); err != nil {
		fmt.Printf("  temperature: error (%v)\n", err)
	} else {
		fmt.Printf("  temperature: %d °C\n", t)
	}
	return nil
}

func cmdRead(ctx context.Context, c *sguai.Client, args []string) error {
	fields := positional(args)
	if len(fields) == 0 {
		fields = []string{"version", "temperature", "battery"}
	}
	for _, f := range fields {
		switch strings.ToLower(f) {
		case "version":
			v, err := c.ReadVersion(ctx)
			if err != nil {
				return err
			}
			fmt.Printf("version:     %s\n", v)
		case "temperature", "temp":
			t, err := c.ReadTemperature(ctx)
			if err != nil {
				return err
			}
			fmt.Printf("temperature: %d °C\n", t)
		case "battery":
			b, err := c.ReadBattery(ctx)
			if err != nil {
				return err
			}
			fmt.Printf("battery:     %d%%\n", b)
		case "all":
			// recurse without "all"
			return cmdRead(ctx, c, []string{"version", "temperature", "battery"})
		default:
			return fmt.Errorf("unknown field %q (use version|temperature|battery|all)", f)
		}
	}
	return nil
}

func cmdAutoOff(ctx context.Context, c *sguai.Client, args []string) error {
	pos := positional(args)
	if len(pos) == 0 {
		code, err := c.ReadAutoOff(ctx)
		if err != nil {
			return err
		}
		fmt.Printf("Auto-off: code %d — %s\n", code, sguai.AutoOffCodes[code])
		return nil
	}
	code, err := parseAutoOffArg(pos[0])
	if err != nil {
		return err
	}
	if err := c.SetAutoOff(ctx, code); err != nil {
		return err
	}
	fmt.Printf("✓ Auto-off → code %d (%s)\n", code, sguai.AutoOffCodes[code])
	return nil
}

// cmdSpeed gets/sets the persistent dynamic-speed feature byte (0x24).
// Distinct from `animate -s`, which sets the per-animation speed byte
// in the 0x26 prologue. Argument forms accepted by parseSpeedArg:
// presets (slow/medium/fast/...), raw byte (130), duration per frame
// (1300ms / 1.3s), or frame rate (2fps).
func cmdSpeed(ctx context.Context, c *sguai.Client, args []string) error {
	pos := positional(args)
	if len(pos) == 0 {
		speed, err := c.ReadDynamicSpeed(ctx)
		if err != nil {
			return err
		}
		var ms int
		if speed >= 1 {
			ms = 10 * (260 - int(speed))
		}
		fmt.Printf("Dynamic speed: %d (~%d ms/frame per APK formula)\n", speed, ms)
		return nil
	}
	n, err := parseSpeedArg(pos[0])
	if err != nil {
		return err
	}
	if err := c.SetDynamicSpeed(ctx, byte(n)); err != nil {
		return err
	}
	ms := 10 * (260 - int(n))
	fmt.Printf("✓ Dynamic speed → %d (~%d ms/frame)\n", n, ms)
	return nil
}

// parseSpeedArg accepts user-friendly speed values:
//   - preset names: slowest, slow, medium (=normal/default), fast, fastest
//   - raw byte: 1..255
//   - duration per frame: "1300ms" / "1.3s"
//   - frame rate: "2fps"
//
// Duration ↔ byte uses the APK formula ms_per_frame = 10 * (260 - speed).
func parseSpeedArg(s string) (byte, error) {
	raw := strings.TrimSpace(strings.ToLower(s))
	if raw == "" {
		return 0, fmt.Errorf("speed value cannot be empty")
	}

	// Preset boundaries match the official APK's slider (min=5, max=255,
	// default=130). See PROTOCOL_SPEC.md §4.6.
	presets := map[string]byte{
		"slowest": 5, "slow": 50,
		"medium": 130, "normal": 130, "default": 130,
		"fast": 200, "fastest": 255,
	}
	if v, ok := presets[raw]; ok {
		return v, nil
	}

	// Frames per second: <N>fps
	if rest := strings.TrimSuffix(raw, "fps"); rest != raw {
		fps, err := strconv.ParseFloat(strings.TrimSpace(rest), 64)
		if err != nil || fps <= 0 {
			return 0, fmt.Errorf("invalid fps %q", s)
		}
		ms := 1000.0 / fps
		speed := int(260 - ms/10 + 0.5)
		if speed < 1 || speed > 255 {
			return 0, fmt.Errorf("%g fps maps to speed %d (range 1..255)", fps, speed)
		}
		return byte(speed), nil
	}

	// Duration per frame: <N>ms or <N>s
	if rest := strings.TrimSuffix(raw, "ms"); rest != raw {
		n, err := strconv.ParseFloat(strings.TrimSpace(rest), 64)
		if err != nil || n < 0 {
			return 0, fmt.Errorf("invalid ms duration %q", s)
		}
		speed := int(260 - n/10 + 0.5)
		if speed < 1 || speed > 255 {
			return 0, fmt.Errorf("%g ms maps to speed %d (range 1..255; valid 50..2590ms)", n, speed)
		}
		return byte(speed), nil
	}
	if rest := strings.TrimSuffix(raw, "s"); rest != raw && rest != "" {
		n, err := strconv.ParseFloat(strings.TrimSpace(rest), 64)
		if err != nil || n < 0 {
			return 0, fmt.Errorf("invalid s duration %q", s)
		}
		ms := n * 1000
		speed := int(260 - ms/10 + 0.5)
		if speed < 1 || speed > 255 {
			return 0, fmt.Errorf("%g s maps to speed %d (range 1..255)", n, speed)
		}
		return byte(speed), nil
	}

	// Raw byte
	n, err := strconv.Atoi(raw)
	if err != nil {
		return 0, fmt.Errorf("speed %q: expected raw 1..255, preset (slowest|slow|medium|fast|fastest), <N>ms, <N>s, or <N>fps", s)
	}
	if n < 1 || n > 255 {
		return 0, fmt.Errorf("speed %d out of range 1..255 (0 is unspecified by firmware)", n)
	}
	return byte(n), nil
}

// parseModeArg maps any user-typed mode synonym to the canonical name
// expected by sguai.BuildSetMode.
func parseModeArg(s string) (string, error) {
	key := strings.ToLower(s)
	for _, ch := range []string{" ", "-", "_"} {
		key = strings.ReplaceAll(key, ch, "")
	}
	aliases := map[string]string{
		"static": "static", "fixed": "static", "still": "static", "off": "static", "none": "static", "0": "static",
		"left": "scrollLeft", "scrollleft": "scrollLeft", "shiftleft": "scrollLeft", "scrolltoleft": "scrollLeft", "1": "scrollLeft",
		"right": "scrollRight", "scrollright": "scrollRight", "shiftright": "scrollRight", "scrolltoright": "scrollRight", "2": "scrollRight",
		"flash": "flashing", "flashing": "flashing", "blink": "flashing", "blinking": "flashing", "twinkle": "flashing", "3": "flashing",
	}
	if v, ok := aliases[key]; ok {
		return v, nil
	}
	return "", fmt.Errorf("unknown mode %q. Try: static | left | right | flash", s)
}

func parseAutoOffArg(s string) (byte, error) {
	key := strings.ReplaceAll(strings.ReplaceAll(strings.ToLower(s), " ", ""), "_", "")
	presets := map[string]byte{
		"always": 0, "on": 0, "alwayson": 0,
		"30s": 1, "30sec": 1, "30seconds": 1,
		"1m": 2, "1min": 2, "1minute": 2,
		"3m": 3, "3min": 3, "3minutes": 3,
		"5m": 4, "5min": 4, "5minutes": 4,
	}
	if c, ok := presets[key]; ok {
		return c, nil
	}
	if n, err := strconv.Atoi(s); err == nil {
		if n < 0 || n > 4 {
			return 0, fmt.Errorf("auto-off code must be 0..4 (got %d)", n)
		}
		return byte(n), nil
	}
	return 0, fmt.Errorf("expected always|30s|1m|3m|5m or 0..4 (got %q)", s)
}

func cmdGreeting(ctx context.Context, c *sguai.Client, args []string) error {
	pos := positional(args)
	if len(pos) == 0 {
		return errors.New("usage: greeting <message>")
	}
	msg := strings.Join(pos, " ")
	if err := c.SetGreeting(ctx, msg); err != nil {
		return err
	}
	if raw := flagValue(args, "--mode"); raw != "" {
		mode, err := parseModeArg(raw)
		if err != nil {
			return err
		}
		if err := c.SetDynamicMode(ctx, mode); err != nil {
			return err
		}
	}
	fmt.Println("✓ Greeting set")
	return nil
}

func cmdMode(ctx context.Context, c *sguai.Client, args []string) error {
	pos := positional(args)
	if len(pos) == 0 {
		return errors.New("usage: mode <static|left|right|flash> (or any synonym)")
	}
	mode, err := parseModeArg(pos[0])
	if err != nil {
		return err
	}
	if err := c.SetDynamicMode(ctx, mode); err != nil {
		return err
	}
	fmt.Printf("✓ Mode set: %s\n", mode)
	return nil
}

func cmdImage(_ context.Context, _ *sguai.Client, _ []string) error {
	// Static image upload via single-frame GIF input is doable but
	// requires the same dithering toolbox as Python (Floyd-Steinberg
	// etc). For now this is a stub — single-frame uploads can use
	// `animate <single-frame.gif>` with a 1-frame animation.
	return errors.New("image upload not yet implemented in Go port — use `animate` with a single-frame GIF, or use python/smart_mug.py image")
}

func cmdAnimate(ctx context.Context, c *sguai.Client, args []string) error {
	pos := positional(args)
	if len(pos) == 0 {
		return errors.New("usage: animate <gif> [--speed N]")
	}
	path := pos[0]
	speed := 130 // matches Python and the APK's default (`speedValue`)
	for _, flag := range []string{"-s", "--speed"} {
		if s := flagValue(args, flag); s != "" {
			n, err := parseSpeedArg(s)
			if err != nil {
				return fmt.Errorf("%s: %w", flag, err)
			}
			speed = int(n)
		}
	}
	threshold := uint8(128)
	invert := hasFlag(args, "-i") || hasFlag(args, "--invert")

	fmt.Printf("Loading frames from %s...\n", path)
	frames, err := anim.LoadGIF(path, threshold, invert)
	if err != nil {
		return err
	}
	fmt.Printf("✓ %d frame(s) loaded\n", len(frames))

	// Match the official APK: do NOT touch auto-off before sending an
	// animation. The cup retains its existing screen-off preference.
	// To keep the display lit, run `mug auto-off always` separately —
	// the same way the APK exposes it.

	fmt.Printf("\nUploading %d frame(s) at speed=%d...\n", len(frames), speed)
	if err := c.SetAnimation(ctx, frames, speed); err != nil {
		return err
	}
	fmt.Println("✓ Animation uploaded — cup is now playing autonomously")
	return nil
}

func cmdReset(ctx context.Context, c *sguai.Client, args []string) error {
	if !(hasFlag(args, "--yes") || hasFlag(args, "-y")) {
		fmt.Print("⚠ Factory reset will ERASE ALL CUP DATA (animations, settings, pairing). Continue? [y/N] ")
		var answer string
		fmt.Scanln(&answer)
		if !strings.HasPrefix(strings.ToLower(strings.TrimSpace(answer)), "y") {
			fmt.Println("Aborted.")
			return errors.New("user aborted")
		}
	}
	if err := c.FactoryReset(ctx); err != nil {
		return err
	}
	fmt.Println("✓ Factory-reset command sent. The cup will reboot; BLE may drop momentarily.")
	return nil
}

// =============================================================================
// alias / clear-cache (no BLE)
// =============================================================================

func cmdAlias(args []string) int {
	if hasFlag(args, "--clear") {
		if err := cache.ClearAliases(); err != nil {
			fmt.Fprintf(os.Stderr, "Error: %v\n", err)
			return 1
		}
		fmt.Println("✓ All aliases cleared")
		return 0
	}
	if hasFlag(args, "--remove") {
		name := flagValue(args, "--remove")
		if name == "" {
			fmt.Fprintln(os.Stderr, "Error: --remove requires a name")
			return 1
		}
		if err := cache.RemoveAlias(name); err != nil {
			fmt.Fprintf(os.Stderr, "Error: %v\n", err)
			return 1
		}
		fmt.Printf("✓ Removed alias %q\n", name)
		return 0
	}
	pos := positional(args)
	if len(pos) == 0 {
		// list
		c := cache.Load()
		if c.Address != "" {
			name := c.Name
			if name == "" {
				name = sguai.DeviceName
			}
			fmt.Printf("Last used: %s (%s)\n", name, c.Address)
		}
		if len(c.Aliases) == 0 {
			fmt.Println("\nNo aliases registered. Add one with:")
			fmt.Println("  mug alias <name> <UUID>")
			return 0
		}
		fmt.Println("\nAliases:")
		names := make([]string, 0, len(c.Aliases))
		for k := range c.Aliases {
			names = append(names, k)
		}
		sort.Strings(names)
		for _, n := range names {
			e := c.Aliases[n]
			fmt.Printf("  %-16s  %s  (%s)\n", n, e.Address, e.BLEName)
		}
		return 0
	}
	if len(pos) != 2 {
		fmt.Fprintln(os.Stderr, "Error: usage: alias <name> <UUID>  (or --remove NAME / --clear)")
		return 1
	}
	name, addr := pos[0], pos[1]
	if err := cache.AddAlias(name, addr, sguai.DeviceName); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		return 1
	}
	fmt.Printf("✓ Aliased %q → %s\n", name, addr)
	fmt.Printf("  Use it: mug info --addr %s\n", name)
	return 0
}

func cmdClearCache() int {
	if err := cache.Clear(); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		return 1
	}
	fmt.Println("Cache cleared")
	return 0
}

// =============================================================================
// Argument helpers
// =============================================================================

// positional returns args that are neither flags (start with -) nor flag
// values (consumed by --flag VALUE forms in flagValue).
func positional(args []string) []string {
	consumed := map[int]bool{}
	flagsWithValue := map[string]bool{
		"--addr":  true,
		"--mode":  true,
		"--speed": true,
		"-s":      true,
	}
	out := []string{}
	for i := 0; i < len(args); i++ {
		a := args[i]
		if consumed[i] {
			continue
		}
		if strings.HasPrefix(a, "-") {
			if flagsWithValue[a] && i+1 < len(args) {
				consumed[i+1] = true
			}
			continue
		}
		out = append(out, a)
	}
	return out
}

func hasFlag(args []string, name string) bool {
	for _, a := range args {
		if a == name {
			return true
		}
	}
	return false
}

func flagValue(args []string, name string) string {
	for i, a := range args {
		if a == name && i+1 < len(args) {
			return args[i+1]
		}
	}
	return ""
}

// =============================================================================
// Help
// =============================================================================

func printHelp() {
	fmt.Print(`mug — SGUAI-C3 Smart Cup CLI (Go)

Commands:
  info [--addr X] [--rescan]                 Connect, dump everything readable
  read [field ...] [--addr X] [--rescan]     Read version|temperature|battery|all
  auto-off [<preset>] [--addr X] [--rescan]  Get/set screen-off duration
                                             presets: always | 30s | 1m | 3m | 5m
  speed [<value>] [--addr X]                 Get/set persistent dynamic-speed
                                             (feature 0x24). Default 130; APK
                                             slider min=5, max=255.
                                             Forms: slowest|slow|medium|fast|fastest,
                                             1..255, <N>ms, <N>s, <N>fps.
                                             ms_per_frame = 10 * (260 - speed)
  greeting <msg> [--mode M] [--addr X]       Set greeting text (mode optional)
  mode <mode> [--addr X]                     static|left|right|flash (synonyms:
                                             scrollLeft/scrollRight/flashing/blink/
                                             twinkle/fixed/still, raw 0..3)
  image <file> [--addr X]                    STUB — not yet implemented in Go.
                                             Use python/smart_mug.py image, or
                                             pass a 1-frame GIF to "animate".
  animate <gif> [-s SPEED] [-i]              Upload animation (max 132 frames).
                  [--addr X]                 SPEED: same forms as "speed"
                                             (e.g. medium, 1300ms, 2fps).
                                             Cup's existing auto-off is left
                                             untouched (matches the official
                                             app). Run "mug auto-off always"
                                             beforehand if you want the loop
                                             to play indefinitely.
  reset [-y] [--addr X]                      Factory reset (DESTRUCTIVE)
  alias                                      List per-cup aliases
  alias <name> <UUID>                        Register an alias
  alias --remove <name>                      Forget an alias
  alias --clear                              Forget all aliases
  clear-cache                                Forget cached device + aliases

Global flags:
  --addr UUID|alias   Pin to a specific cup (skips scan auto-pick).
  --rescan            Force a fresh BLE scan; ignore cached address.

Notes:
  • The cup's animation buffer holds at most 132 frames on fw 1.7. The
    CLI hard-fails before sending if you exceed this.
  • After autonomous animation playback the cup goes silent on BLE for
    a window — see PROTOCOL_SPEC.md §4.7.
  • Aliases live at ~/.smart_mug_cache.json; the Python implementation
    shares this file so settings carry across.
`)
}
