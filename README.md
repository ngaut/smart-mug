# SGUAI Smart Cup Control Application

Web-based control application for the SGUAI-C3 Smart Cup - a Bluetooth-enabled smart beverage container with a 48×12 pixel LED display.

## Features

- 🔗 **Bluetooth Connectivity** - Web Bluetooth API for device pairing
- 🌡️ **Temperature Monitoring** - Real-time sensor reading
- 📝 **Text Display** - Send greeting messages (UTF-8, 20 char limit)
- 🎬 **Display Modes** - Static, scrolling (both directions), flashing
- 🎨 **Visual Editor** - WYSIWYG pixel grid editor with draw/erase/clear/fill tools
- 📷 **Image Upload** - Upload photos with advanced dithering algorithms
- 🎞️ **Animated GIF Support** - Upload and play animated GIFs with on-screen preview
- ⚡ **Skip Connection Mode** - Test UI without a physical device

## Technology Stack

- **Frontend:** Vanilla JavaScript (ES6+), HTML5, Tailwind CSS (CDN)
- **Communication:** Web Bluetooth API
- **Image Processing:** Canvas API, Floyd-Steinberg dithering, omggif library
- **Display:** 48×12 pixel monochrome LED matrix

## Project Structure

```
├── index.html              # Main entry point
├── css/
│   └── styles.css         # Custom styling for pixel grid
├── js/
│   ├── ble.js            # Bluetooth communication layer
│   ├── ui.js             # UI components and panels
│   ├── imageProcessor.js # Image processing, dithering, and GIF parsing
│   ├── imageEditor.js    # Pixel grid state management
│   ├── omggif.js         # GIF parsing library
│   └── main.js           # Application orchestration
├── assets/
│   ├── icons/
│   │   └── favicon.svg
│   ├── cup_reference.jpeg
│   └── tidb-logo_preview.png
├── calibration.html       # Screen area calibration tool
├── generate_test_gif.py   # Test animation generator
├── examples/             # Reference animations (generators + pre-rendered GIFs)
│   ├── README.md
│   ├── tidb_scale_animation.py   # 4-phase "horizontal scale-out" narrative
│   ├── tidb_scale.gif
│   ├── tidb_nextgen_animation.py # 132-frame "Survive & Scale" story
│   └── tidb_nextgen.gif
├── python/               # Python BLE client (CLI + daemon + HTTP API)
│   ├── smart_mug.py      # Full implementation (~2000 LOC)
│   ├── test_protocol.py  # Wire-format tests (16 cases)
│   └── README.md
├── go/                   # Go reimplementation (single binary, no daemon needed)
│   ├── cmd/mug/          # CLI entry
│   ├── internal/sguai/   # Wire protocol + BLE client
│   ├── internal/anim/    # GIF loader
│   ├── internal/cache/   # Shared alias cache (same JSON file as Python)
│   └── README.md
├── PROTOCOL_SPEC.md      # Complete BLE protocol documentation
└── README.md             # This file
```

The Python and Go CLIs share a cache file at `~/.smart_mug_cache.json`,
so aliases registered by either are visible to the other. They do
**not** share the daemon-state directory; running the Python daemon
and using `mug ...` against the same cup at the same time will fight
over the BLE link.

## Try a worked example

```bash
# Render the "TiDB scalability" animation
uv run --with pillow python examples/tidb_scale_animation.py

# Send it to the cup at human-readable pacing (~9 s loop)
uv run python/smart_mug.py animate examples/tidb_scale.gif -s 200
```

See [`examples/README.md`](examples/README.md) for what's there and tips on
authoring your own animations.

## Quick Start

### 1. Start Local Server
```bash
cd smartmug
python3 -m http.server 8080
```

### 2. Open in Browser
- Open Chrome or Edge (Web Bluetooth required)
- Navigate to: http://localhost:8080
- Enable Web Bluetooth in browser settings if needed

### 3. Connect
1. Click "Connect to Device" and select "SGUAI-C3" from the pairing dialog, OR
2. Click "Skip Connection" to enter demo mode and explore the UI without a device.

### 4. Use Features
- Read version, temperature
- Send greeting text or set scrolling/flashing mode
- Upload an image or animated GIF
- Use the pixel editor to draw frames manually

## Animated GIF Playback

Upload an animated GIF and the cup will play it autonomously after upload —
no further BLE traffic is needed during playback. The on-screen preview
mirrors the cup's playback timing using the APK's
`ms_per_frame = 10 × (260 − speed)` formula (PROTOCOL_SPEC.md §4.6), so the
preview is honest about what you'll see on the device.

**Technical details:**
- Per-frame upload: ~150 ms (vs. ~3 s on the legacy streaming path)
- Cup-side playback: fully autonomous after upload — disconnect and the
  loop keeps running
- Speed byte: 1–255 (default 130 ≈ 1.3 s/frame, max 255 ≈ 50 ms/frame)
- Frame buffer cap: 132 frames on SGUAI-C3 fw 1.7 (the protocol byte
  allows 255 but the cup will drop the link beyond 132 —
  [`PROTOCOL_SPEC.md §4.6`](PROTOCOL_SPEC.md))
- Demo mode (Skip Connection): preview-only, no BLE writes

## Image Upload Feature

### Supported Formats
- JPG, PNG, GIF (including animated GIFs)
- Any size (automatically resized to target dimensions)

### Dithering Algorithms

**Spatial (Single Frame):**
- **Floyd-Steinberg** - Error diffusion, best for photos
- **Atkinson** - Cleaner, less noise than Floyd-Steinberg
- **Ordered/Bayer** - Pattern-based, good for textures
- **Simple Threshold** - Fast, best for logos/text

### Image Enhancement
- **Fit Mode:** Contain (letterbox) or Cover (crop)
- **Gamma Correction:** Adjust for LED display characteristics
- **Brightness:** Adjust -100 to +100
- **Contrast:** Adjust -100 to +100
- **Sharpening:** Enhance edges (0 to 2.0)
- **Threshold:** Binary cutoff (0-255)
- **Auto-Contrast:** Automatic histogram equalization

### Standard Workflow
1. Click "Choose File" and select image
2. Choose algorithm and adjust enhancement settings
3. Click "Process & Preview"
4. Review processed result and image quality analysis
5. Click "Apply to Editor" to load into pixel grid (optional)
6. Optionally edit manually with drawing tools
7. Click "Send to Cup" to transfer to device

**Note:** With the corrected protocol (matching the official `net.sguai.app` Android app), static image upload completes in well under a second.

## BLE Protocol

See [PROTOCOL_SPEC.md](PROTOCOL_SPEC.md) for complete protocol documentation.

### Quick Reference
- **Service UUID:** `0000ff00-0000-1000-8000-00805f9b34fb`
- **Command Characteristic:** `0000ff01-...` (write)
- **Response Characteristic:** `0000ff02-...` (notify, read)
- **Command Format:** `[0xFF, 0x55, LEN, 0x00, FUNCTION, FEATURE, ...DATA]` — `LEN` = total written length, no terminator on writes
- **Static Image:** 78 bytes (`LEN=0x4E`, 6-byte header + 72-byte bitmap)
- **Animation Frame:** 80 bytes (`LEN=0x50`, 8-byte header `+ <idx><speed>` + 72-byte bitmap)
- **Bitmap encoding:** row-major left-to-right, rows top-to-bottom, MSB-first (verified on SGUAI-C3 firmware 1.6 hardware; see PROTOCOL_SPEC.md §4.5 for the firmware-dependent caveat)

## Browser Requirements

- Chrome 56+ or Edge 79+
- Web Bluetooth API enabled
- HTTPS (or localhost for development)

## Known Limitations

1. **No Generic Access Service:** Device doesn't expose standard Generic Access service (handled gracefully)
2. **BLE Timeout:** Device may auto-disconnect after inactivity (manual reconnect required)
3. **Production Build:** Tailwind CDN should be replaced with npm installation for production

## Troubleshooting

### Connection Issues
- Ensure device is powered on and in pairing mode
- Check Web Bluetooth is enabled in browser
- Try refreshing browser and reconnecting

### Display Not Updating
- Verify device is still connected
- Try sending a simpler command (e.g., read temperature)
- Reconnect if device disconnected

## Development Notes

### Script Load Order
```html
<script src="js/ble.js"></script>           <!-- 1. BLE manager -->
<script src="js/ui.js"></script>            <!-- 2. UI components -->
<script src="js/omggif.js"></script>        <!-- 3. GIF parsing -->
<script src="js/imageProcessor.js"></script><!-- 4. Image processing -->
<script src="js/imageEditor.js"></script>   <!-- 5. Grid state -->
<script src="js/main.js"></script>          <!-- 6. Application logic -->
```

### Global Architecture
- **BLEManager** (`window.bleManager`) - Singleton for BLE operations
- **ImageEditor** (`window.imageEditor`) - Singleton for grid state
- **ImageProcessor** (`window.imageProcessor`) - Singleton for image processing
- **UI Functions** (`window.ui`) - Namespace for UI components

### Key Design Patterns
- Singleton pattern for managers
- Promise-based async for BLE operations
- Event-driven UI updates
- Observer pattern for disconnection handling

## Future Improvements

### Completed ✅
- [x] Multiple dithering algorithms
- [x] Brightness/contrast/sharpening adjustments
- [x] Image quality analysis with suggestions
- [x] Animated GIF support
- [x] Live preview with animation
- [x] Skip connection mode for testing

### Planned
- [ ] Connection keepalive to prevent auto-disconnect
- [ ] Auto-reconnect on disconnection
- [ ] Built-in icon library
- [ ] Image history/favorites
- [ ] Installation as PWA
- [ ] Faster frame transmission (compression/pipelining)
- [ ] Device-side animation buffering
- [ ] Delta encoding for frame differences

## License

[Add your license here]

## Acknowledgments

- Floyd-Steinberg dithering algorithm
- omggif library for GIF parsing
- Web Bluetooth Community Group
- Tailwind CSS team
