// Package cache stores the local cup cache: last-used address +
// user-assigned aliases. Lives at ~/.smart_mug_cache.json (shared
// format with the Python implementation, so users can switch between
// implementations without losing their aliases).
package cache

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
)

// File is the on-disk cache path. Shared with Python — keep the format
// stable.
func File() string {
	home, _ := os.UserHomeDir()
	return filepath.Join(home, ".smart_mug_cache.json")
}

// AliasEntry records one user-assigned cup name → BLE address mapping.
type AliasEntry struct {
	Address string `json:"address"`
	BLEName string `json:"ble_name,omitempty"`
}

// Cache mirrors Python's _load_cache() shape: legacy single-cup
// fields at the top level, plus an aliases map.
type Cache struct {
	Address string                `json:"address,omitempty"`
	Name    string                `json:"name,omitempty"`
	Aliases map[string]AliasEntry `json:"aliases"`
}

// Load returns the cache from disk. Missing or malformed file → empty
// cache (no error).
func Load() *Cache {
	c := &Cache{Aliases: map[string]AliasEntry{}}
	data, err := os.ReadFile(File())
	if err != nil {
		return c
	}
	_ = json.Unmarshal(data, c)
	if c.Aliases == nil {
		c.Aliases = map[string]AliasEntry{}
	}
	return c
}

// Save writes the cache atomically (temp file + rename).
func (c *Cache) Save() error {
	data, err := json.MarshalIndent(c, "", "  ")
	if err != nil {
		return err
	}
	path := File()
	tmp := path + ".tmp"
	if err := os.WriteFile(tmp, data, 0o600); err != nil {
		return err
	}
	return os.Rename(tmp, path)
}

// SaveLastUsed updates address/name without touching aliases.
func SaveLastUsed(address, name string) error {
	c := Load()
	c.Address = address
	c.Name = name
	return c.Save()
}

// Resolve translates a user-supplied address-or-alias. If the value
// matches an alias, returns the alias's stored address. Otherwise
// returns the value unchanged. Empty input returns empty.
func Resolve(value string) string {
	if value == "" {
		return ""
	}
	c := Load()
	if entry, ok := c.Aliases[value]; ok {
		return entry.Address
	}
	return value
}

// AliasFor returns the alias name registered for the given address, if
// any. Used to display friendly names in command output.
func AliasFor(address string) string {
	c := Load()
	for name, entry := range c.Aliases {
		if entry.Address == address {
			return name
		}
	}
	return ""
}

// AddAlias registers or updates an alias.
func AddAlias(name, address, bleName string) error {
	if name == "" {
		return fmt.Errorf("alias name cannot be empty")
	}
	if address == "" {
		return fmt.Errorf("address cannot be empty")
	}
	c := Load()
	c.Aliases[name] = AliasEntry{Address: address, BLEName: bleName}
	return c.Save()
}

// RemoveAlias deletes an alias. Returns ErrNoSuchAlias if missing.
func RemoveAlias(name string) error {
	c := Load()
	if _, ok := c.Aliases[name]; !ok {
		return fmt.Errorf("no alias named %q", name)
	}
	delete(c.Aliases, name)
	return c.Save()
}

// ClearAliases empties the alias map (legacy address/name kept).
func ClearAliases() error {
	c := Load()
	c.Aliases = map[string]AliasEntry{}
	return c.Save()
}

// Clear removes the entire cache file.
func Clear() error {
	err := os.Remove(File())
	if err != nil && !os.IsNotExist(err) {
		return err
	}
	return nil
}
