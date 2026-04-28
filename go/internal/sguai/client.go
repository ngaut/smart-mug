package sguai

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"sync"
	"time"

	"tinygo.org/x/bluetooth"

	"github.com/ngaut/smart-mug/go/internal/cache"
)

// writeThrottle matches Python's WRITE_THROTTLE_S (rt(20) in the official
// APK's GET_BLE_WRITE action). Applied before every command except
// per-frame animation writes.
const writeThrottle = 20 * time.Millisecond

// Adapter wraps tinygo's DefaultAdapter so callers don't need to know
// the bluetooth package directly. Enable() must be called once before
// any Find/Connect.
type Adapter struct {
	a *bluetooth.Adapter
}

// NewAdapter returns the default platform adapter (CoreBluetooth on
// macOS, BlueZ on Linux). The adapter is enabled lazily.
func NewAdapter() *Adapter {
	return &Adapter{a: bluetooth.DefaultAdapter}
}

// Enable initializes the OS adapter. Idempotent in practice (tinygo
// bluetooth tolerates repeated calls).
func (a *Adapter) Enable() error {
	return a.a.Enable()
}

// FindDevice locates the cup. Behavior:
//
//   - If forceAddr is set: parse and return it without scanning. Caller
//     can connect by address even when the cup isn't advertising
//     (useful in §4.7 silent-BLE windows on a previously-bonded
//     peripheral, if the OS still has it cached).
//   - Else if useCache and the cache has a stored address: scan
//     briefly (5 s); if the cached address shows up, return it.
//   - Else: full scan (12 s), match by name. If multiple SGUAI-C3
//     devices appear, refuse to auto-pick — caller must disambiguate
//     via forceAddr.
//
// Returns the resolved BLE address as a string. The cache is updated
// with the auto-selected device's address on a fresh scan.
func (a *Adapter) FindDevice(ctx context.Context, useCache bool, forceAddr string) (string, error) {
	if forceAddr != "" {
		return forceAddr, nil
	}

	c := cache.Load()
	cachedAddr := c.Address

	// Fast path: cached address present, brief scan to confirm.
	if useCache && cachedAddr != "" {
		fmt.Printf("Cached device: %s (%s)\n", c.Name, cachedAddr)
		if found, err := a.scanFor(ctx, 5*time.Second, func(r bluetooth.ScanResult) bool {
			return strings.EqualFold(r.Address.String(), cachedAddr)
		}); err == nil && found != "" {
			fmt.Println("✓ Cached device available")
			return found, nil
		}
		fmt.Println("⚠ Cached device not advertising; trying direct connect by address...")
		return cachedAddr, nil
	}

	// Slow path: full scan.
	fmt.Println("Scanning for BLE devices...")
	candidates, err := a.scanAll(ctx, 12*time.Second)
	if err != nil {
		return "", err
	}
	if len(candidates) == 0 {
		return "", errors.New("no BLE devices found in scan")
	}

	fmt.Printf("\nFound %d named devices:\n", len(candidates))
	for i, r := range candidates {
		fmt.Printf("  %d. %s (%s)\n", i+1, r.LocalName(), r.Address.String())
	}

	var matches []bluetooth.ScanResult
	for _, r := range candidates {
		name := r.LocalName()
		if name == DeviceName || strings.HasPrefix(name, DeviceName) {
			matches = append(matches, r)
		}
	}
	if len(matches) == 1 {
		r := matches[0]
		addr := r.Address.String()
		fmt.Printf("\nAuto-selected: %s (%s)\n", r.LocalName(), addr)
		_ = cache.SaveLastUsed(addr, r.LocalName())
		return addr, nil
	}
	if len(matches) > 1 {
		var lines []string
		for _, r := range matches {
			lines = append(lines, fmt.Sprintf("  %s (%s)", r.LocalName(), r.Address.String()))
		}
		return "", fmt.Errorf("multiple %s devices found — refusing to auto-pick:\n%s\nPass --addr to select one explicitly", DeviceName, strings.Join(lines, "\n"))
	}
	return "", fmt.Errorf("no %s device in scan results", DeviceName)
}

// scanAll runs a scan for `timeout` and returns every named device
// encountered.
func (a *Adapter) scanAll(ctx context.Context, timeout time.Duration) ([]bluetooth.ScanResult, error) {
	var (
		mu      sync.Mutex
		results = map[string]bluetooth.ScanResult{}
	)
	scanCtx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	done := make(chan struct{})
	go func() {
		<-scanCtx.Done()
		_ = a.a.StopScan()
		close(done)
	}()

	err := a.a.Scan(func(_ *bluetooth.Adapter, r bluetooth.ScanResult) {
		if r.LocalName() == "" {
			return
		}
		mu.Lock()
		results[r.Address.String()] = r
		mu.Unlock()
	})
	<-done
	if err != nil && !errors.Is(err, context.Canceled) {
		// scan returns nil on graceful StopScan; only surface real errors
		if !strings.Contains(err.Error(), "scan stopped") {
			return nil, err
		}
	}

	mu.Lock()
	defer mu.Unlock()
	out := make([]bluetooth.ScanResult, 0, len(results))
	for _, r := range results {
		out = append(out, r)
	}
	return out, nil
}

// scanFor stops as soon as `match` returns true. Returns the matched
// address or "" on timeout.
func (a *Adapter) scanFor(ctx context.Context, timeout time.Duration, match func(bluetooth.ScanResult) bool) (string, error) {
	scanCtx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	var (
		mu       sync.Mutex
		matched  string
	)
	done := make(chan struct{})
	go func() {
		<-scanCtx.Done()
		_ = a.a.StopScan()
		close(done)
	}()

	err := a.a.Scan(func(_ *bluetooth.Adapter, r bluetooth.ScanResult) {
		if !match(r) {
			return
		}
		mu.Lock()
		if matched == "" {
			matched = r.Address.String()
			cancel()
		}
		mu.Unlock()
	})
	<-done
	mu.Lock()
	defer mu.Unlock()
	if matched != "" {
		return matched, nil
	}
	if err != nil && !strings.Contains(err.Error(), "scan stopped") {
		return "", err
	}
	return "", nil
}

// Client is a connected SGUAI-C3 cup. All write operations are
// serialized through a per-client mutex so concurrent goroutines
// can't interleave GATT writes on the same characteristic.
type Client struct {
	dev     bluetooth.Device
	cmdChar bluetooth.DeviceCharacteristic
	rspChar bluetooth.DeviceCharacteristic

	mu sync.Mutex // serializes Write / ExecuteCommand

	rspMu sync.Mutex
	rsp   chan []byte
}

// Connect resolves the address into a tinygo address, opens the GATT
// link, runs the firmware-version handshake, and returns a Client
// ready for use. On failure the underlying connection is rolled back.
//
// Mirrors the official APK's post-connect sequence:
//
//	connect → wait 2s → discover service+chars → subscribe → wait 500 ms
//	→ read firmware version (handshake gate)
func (a *Adapter) Connect(ctx context.Context, addrStr string) (*Client, error) {
	uuid, err := bluetooth.ParseUUID(addrStr)
	if err != nil {
		return nil, fmt.Errorf("invalid BLE address %q: %w", addrStr, err)
	}
	addr := bluetooth.Address{UUID: uuid}

	fmt.Printf("Connecting to %s...\n", addrStr)
	// 8s connection timeout matches the official APK
	// (app-service.pretty.js:49449 — `createBLEConnection({timeout: 8e3})`).
	dev, err := a.a.Connect(addr, bluetooth.ConnectionParams{
		ConnectionTimeout: bluetooth.NewDuration(8 * time.Second),
	})
	if err != nil {
		return nil, fmt.Errorf("connect failed: %w", err)
	}

	// Step 2: stabilize 2s post-connect (matches APK rt(2e3))
	select {
	case <-time.After(2 * time.Second):
	case <-ctx.Done():
		_ = dev.Disconnect()
		return nil, ctx.Err()
	}

	svcUUID, _ := bluetooth.ParseUUID(ServiceUUID)
	svcs, err := dev.DiscoverServices([]bluetooth.UUID{svcUUID})
	if err != nil || len(svcs) == 0 {
		_ = dev.Disconnect()
		return nil, fmt.Errorf("service %s not found: %w", ServiceUUID, err)
	}
	fmt.Println("✓ Found target service")

	cmdUUID, _ := bluetooth.ParseUUID(CommandCharUUID)
	rspUUID, _ := bluetooth.ParseUUID(ResponseUUID)
	chars, err := svcs[0].DiscoverCharacteristics([]bluetooth.UUID{cmdUUID, rspUUID})
	if err != nil {
		_ = dev.Disconnect()
		return nil, fmt.Errorf("characteristic discovery failed: %w", err)
	}
	var cmdChar, rspChar bluetooth.DeviceCharacteristic
	for _, c := range chars {
		switch c.UUID().String() {
		case cmdUUID.String():
			cmdChar = c
		case rspUUID.String():
			rspChar = c
		}
	}
	if cmdChar.UUID().String() == "" || rspChar.UUID().String() == "" {
		_ = dev.Disconnect()
		return nil, errors.New("required characteristics not present")
	}

	cli := &Client{
		dev:     dev,
		cmdChar: cmdChar,
		rspChar: rspChar,
	}

	if err := rspChar.EnableNotifications(cli.handleNotify); err != nil {
		_ = dev.Disconnect()
		return nil, fmt.Errorf("subscribe failed: %w", err)
	}

	// Step 7: brief settle (matches APK rt(500))
	time.Sleep(500 * time.Millisecond)

	// Step 8: firmware-version handshake. Cup's firmware appears to
	// require this before treating the GATT session as fully
	// initialized — without it, persistent-config writes (notably
	// 0x27 auto-off) can leave BLE state that prevents reconnect.
	if v, err := cli.ReadVersion(ctx); err != nil {
		fmt.Printf("⚠ Firmware handshake failed (%v); persistent-config writes may misbehave\n", err)
	} else {
		fmt.Printf("✓ Handshake: firmware %s\n", v)
	}

	fmt.Println("✓ Connected successfully")
	return cli, nil
}

// Disconnect tears down the GATT link.
func (c *Client) Disconnect() error {
	err := c.dev.Disconnect()
	fmt.Println("Disconnected")
	return err
}

// Address returns the cup's BLE address (rotating UUID on macOS).
func (c *Client) Address() string {
	return c.dev.Address.String()
}

// handleNotify is the response-characteristic notification callback.
// We only ever wait for one response at a time (under c.mu), so a
// length-1 channel is enough.
func (c *Client) handleNotify(buf []byte) {
	c.rspMu.Lock()
	ch := c.rsp
	c.rspMu.Unlock()
	if ch == nil {
		return
	}
	// Copy because the caller may reuse buf
	cp := make([]byte, len(buf))
	copy(cp, buf)
	select {
	case ch <- cp:
	default:
		// Caller's done with this response; drop subsequent late ones.
	}
}

// Write is fire-and-forget. Acquires the mutex so concurrent callers
// (e.g. animation upload + a status read) can't interleave. Applies
// the 20 ms pre-write throttle that matches the official APK's
// GET_BLE_WRITE action.
func (c *Client) Write(data []byte) error {
	c.mu.Lock()
	defer c.mu.Unlock()
	time.Sleep(writeThrottle)
	return c.writeLocked(data)
}

// writeLocked is the lock-free body of Write WITHOUT throttle.
// Used by per-frame animation writes (which apply their own pacing).
// Caller must hold c.mu.
func (c *Client) writeLocked(data []byte) error {
	_, err := c.cmdChar.Write(data)
	return err
}

// ExecuteCommand writes a request, waits for the next notification on
// the response characteristic, and returns the parsed payload. Applies
// the 20 ms pre-write throttle.
//
// Race-safety: the response-channel slot is set BEFORE the write goes
// out, so any notification arriving after the write (the one we want)
// will land in our channel. We also wrap with a brief drain-then-bind
// step in case the previous command's late echo is still in flight —
// the cup occasionally sends them up to a few hundred ms after the
// originating write.
func (c *Client) ExecuteCommand(ctx context.Context, data []byte, timeout time.Duration) ([]byte, error) {
	c.mu.Lock()
	defer c.mu.Unlock()

	ch := make(chan []byte, 1)
	c.rspMu.Lock()
	// Drain any stale buffered notification that may have been queued
	// against a previous (now-stopped) channel; the handler drops sends
	// when the active channel is full or absent, but we install a fresh
	// channel anyway for clarity.
	c.rsp = ch
	c.rspMu.Unlock()
	defer func() {
		c.rspMu.Lock()
		c.rsp = nil
		c.rspMu.Unlock()
	}()

	time.Sleep(writeThrottle)
	if err := c.writeLocked(data); err != nil {
		return nil, err
	}

	select {
	case raw := <-ch:
		return ParseResponse(raw), nil
	case <-time.After(timeout):
		return nil, ErrResponseTimeout
	case <-ctx.Done():
		return nil, ctx.Err()
	}
}
