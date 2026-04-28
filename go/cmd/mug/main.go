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
	if mode := flagValue(args, "--mode"); mode != "" {
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
		return errors.New("usage: mode <static|scrollRight|scrollLeft|flashing>")
	}
	if err := c.SetDynamicMode(ctx, pos[0]); err != nil {
		return err
	}
	fmt.Println("✓ Mode set")
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
	speed := 200
	if s := flagValue(args, "-s"); s != "" {
		if n, err := strconv.Atoi(s); err == nil {
			speed = n
		}
	}
	if s := flagValue(args, "--speed"); s != "" {
		if n, err := strconv.Atoi(s); err == nil {
			speed = n
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

	// Match Python's default behavior on origin/main: keep-alive is ON
	// by default, opt out via --no-keep-alive. Setting auto-off=0 makes
	// the cup display stay lit so the animation plays continuously after
	// disconnect — but it also triggers the §4.7 silent-BLE side effect
	// (cup may not appear in next scan until animation playback ends).
	keepAlive := !hasFlag(args, "--no-keep-alive")
	if keepAlive {
		if err := c.SetAutoOff(ctx, 0); err != nil {
			fmt.Fprintf(os.Stderr, "⚠ Could not disable auto-off (%v); proceeding anyway\n", err)
		} else {
			fmt.Println("✓ Auto-off disabled (display will stay alive — see PROTOCOL_SPEC.md §4.7)")
		}
	}

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
  greeting <msg> [--mode M] [--addr X]       Set greeting text (mode optional)
  mode <mode> [--addr X]                     static|scrollRight|scrollLeft|flashing
  image <file> [--addr X]                    (not yet implemented in Go port)
  animate <gif> [-s SPEED] [--addr X]        Upload animation (max 132 frames).
                  [--no-keep-alive] [-i]     Sets auto-off=0 by default (continuous
                                             playback); pass --no-keep-alive to
                                             preserve the cup's existing setting.
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
