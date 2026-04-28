package cache

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

// withTempCache redirects HOME so the cache file lands in a t.TempDir,
// keeping the developer's real ~/.smart_mug_cache.json untouched.
func withTempCache(t *testing.T) {
	t.Helper()
	dir := t.TempDir()
	t.Setenv("HOME", dir)
}

func TestLoadEmpty(t *testing.T) {
	withTempCache(t)
	c := Load()
	if c == nil {
		t.Fatal("Load returned nil")
	}
	if len(c.Aliases) != 0 {
		t.Errorf("expected empty aliases, got %v", c.Aliases)
	}
	if c.Address != "" || c.Name != "" {
		t.Errorf("expected empty address/name, got %q/%q", c.Address, c.Name)
	}
}

func TestSaveLoadRoundTrip(t *testing.T) {
	withTempCache(t)
	if err := SaveLastUsed("uuid-A", "SGUAI-C3"); err != nil {
		t.Fatalf("SaveLastUsed: %v", err)
	}
	if err := AddAlias("kitchen", "uuid-A", "SGUAI-C3"); err != nil {
		t.Fatalf("AddAlias: %v", err)
	}
	if err := AddAlias("office", "uuid-B", "SGUAI-C3"); err != nil {
		t.Fatalf("AddAlias: %v", err)
	}

	c := Load()
	if c.Address != "uuid-A" || c.Name != "SGUAI-C3" {
		t.Errorf("legacy fields lost: %v", c)
	}
	if c.Aliases["kitchen"].Address != "uuid-A" {
		t.Errorf("kitchen alias not stored: %v", c.Aliases)
	}
	if c.Aliases["office"].Address != "uuid-B" {
		t.Errorf("office alias not stored: %v", c.Aliases)
	}
}

func TestResolve(t *testing.T) {
	withTempCache(t)
	if err := AddAlias("kitchen", "uuid-A", "SGUAI-C3"); err != nil {
		t.Fatalf("AddAlias: %v", err)
	}

	if got := Resolve("kitchen"); got != "uuid-A" {
		t.Errorf("Resolve(kitchen) = %q, want uuid-A", got)
	}
	// Unknown alias passes through unchanged (caller's input may be a
	// raw UUID).
	if got := Resolve("not-an-alias"); got != "not-an-alias" {
		t.Errorf("Resolve(not-an-alias) = %q, want unchanged", got)
	}
	// Empty stays empty.
	if got := Resolve(""); got != "" {
		t.Errorf("Resolve(empty) = %q, want empty", got)
	}
}

func TestRemoveAndClear(t *testing.T) {
	withTempCache(t)
	_ = AddAlias("kitchen", "uuid-A", "SGUAI-C3")
	_ = AddAlias("office", "uuid-B", "SGUAI-C3")

	if err := RemoveAlias("kitchen"); err != nil {
		t.Fatalf("RemoveAlias: %v", err)
	}
	if _, ok := Load().Aliases["kitchen"]; ok {
		t.Error("kitchen still present after RemoveAlias")
	}
	if _, ok := Load().Aliases["office"]; !ok {
		t.Error("office removed unexpectedly")
	}

	if err := RemoveAlias("not-there"); err == nil {
		t.Error("expected error for unknown alias")
	}

	if err := ClearAliases(); err != nil {
		t.Fatalf("ClearAliases: %v", err)
	}
	if len(Load().Aliases) != 0 {
		t.Error("aliases not cleared")
	}
}

func TestAliasFor(t *testing.T) {
	withTempCache(t)
	_ = AddAlias("kitchen", "uuid-A", "SGUAI-C3")
	if got := AliasFor("uuid-A"); got != "kitchen" {
		t.Errorf("AliasFor(uuid-A) = %q, want kitchen", got)
	}
	if got := AliasFor("uuid-X"); got != "" {
		t.Errorf("AliasFor(unknown) = %q, want empty", got)
	}
}

// TestCrossToolFormat verifies the on-disk JSON shape matches Python's
// `_load_cache()` expectations exactly: top-level address/name plus an
// aliases dict whose values have `address` and `ble_name` keys.
func TestCrossToolFormat(t *testing.T) {
	withTempCache(t)
	_ = SaveLastUsed("uuid-X", "SGUAI-C3")
	_ = AddAlias("kitchen", "uuid-A", "SGUAI-C3")

	data, err := os.ReadFile(File())
	if err != nil {
		t.Fatalf("read cache: %v", err)
	}

	var raw map[string]any
	if err := json.Unmarshal(data, &raw); err != nil {
		t.Fatalf("not valid JSON: %v", err)
	}

	if raw["address"] != "uuid-X" {
		t.Errorf("top-level address: got %v, want uuid-X", raw["address"])
	}
	if raw["name"] != "SGUAI-C3" {
		t.Errorf("top-level name: got %v, want SGUAI-C3", raw["name"])
	}

	aliases, ok := raw["aliases"].(map[string]any)
	if !ok {
		t.Fatalf("aliases not a JSON object: %T", raw["aliases"])
	}
	kitchen, ok := aliases["kitchen"].(map[string]any)
	if !ok {
		t.Fatalf("kitchen alias not a nested object: %T", aliases["kitchen"])
	}
	if kitchen["address"] != "uuid-A" {
		t.Errorf("kitchen.address: got %v, want uuid-A", kitchen["address"])
	}
	if kitchen["ble_name"] != "SGUAI-C3" {
		t.Errorf("kitchen.ble_name: got %v, want SGUAI-C3", kitchen["ble_name"])
	}
}

// TestPythonCompatibilityShape ensures we can decode a hand-written
// cache file in Python's exact format.
func TestPythonCompatibilityShape(t *testing.T) {
	withTempCache(t)
	pythonCache := `{
		"address": "9C7C525C-E71D-CF72-6063-C1FC7A649889",
		"name": "SGUAI-C3",
		"aliases": {
			"cup-fw17": {
				"address": "9C7C525C-E71D-CF72-6063-C1FC7A649889",
				"ble_name": "SGUAI-C3"
			}
		}
	}`
	home, _ := os.UserHomeDir()
	if err := os.WriteFile(filepath.Join(home, ".smart_mug_cache.json"), []byte(pythonCache), 0o600); err != nil {
		t.Fatalf("seed cache: %v", err)
	}

	c := Load()
	if c.Address != "9C7C525C-E71D-CF72-6063-C1FC7A649889" {
		t.Errorf("address not loaded: %v", c.Address)
	}
	entry, ok := c.Aliases["cup-fw17"]
	if !ok {
		t.Fatal("cup-fw17 alias not loaded")
	}
	if entry.Address != "9C7C525C-E71D-CF72-6063-C1FC7A649889" {
		t.Errorf("alias address: got %v", entry.Address)
	}
	if entry.BLEName != "SGUAI-C3" {
		t.Errorf("alias ble_name: got %v", entry.BLEName)
	}
}
