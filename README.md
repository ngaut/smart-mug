# SGUAI Smart Cup Control Application

Web-based control application for the SGUAI-C3 Smart Cup - a Bluetooth-enabled smart beverage container with a 48×12 pixel LED display.

## Features

### Single Cup Mode
- 🔗 **Bluetooth Connectivity** - Web Bluetooth API for device pairing
- 🌡️ **Temperature Monitoring** - Real-time sensor reading
- 📝 **Text Display** - Send greeting messages (UTF-8, 20 char limit)
- 🎬 **Display Modes** - Static, scrolling (both directions), flashing
- 🎨 **Visual Editor** - WYSIWYG pixel grid editor with draw/erase/clear/fill tools
- 📷 **Image Upload** - Upload photos with advanced dithering algorithms

### Multi-Cup Display (NEW!)
- 🖼️ **4-Cup Grid Layout** - Combine 4 cups into a 96×24 pixel display
- 🎞️ **Animated GIF Support** - Upload and play animated GIFs across all cups
- 🔄 **Motion Overlay** - Combine GIF animation with scrolling effects
- 📺 **Live Preview** - Real-time animated preview of all 4 cups
- ⚡ **Skip Connection Mode** - Test UI without physical devices

## Technology Stack

- **Frontend:** Vanilla JavaScript (ES6+), HTML5, Tailwind CSS (CDN)
- **Communication:** Web Bluetooth API
- **Image Processing:** Canvas API, Floyd-Steinberg dithering, omggif library
- **Display:** 48×12 pixel monochrome LED matrix (single cup) or 96×24 (4-cup grid)

## Project Structure

```
├── index.html              # Main entry point
├── css/
│   └── styles.css         # Custom styling for pixel grid
├── js/
│   ├── ble.js            # Bluetooth communication layer (single cup)
│   ├── multiCupBLE.js    # Multi-cup BLE manager
│   ├── ui.js             # UI components and panels
│   ├── imageProcessor.js # Image processing, dithering, and GIF parsing
│   ├── imageSplitter.js  # Multi-cup image splitting
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
├── PROTOCOL_SPEC.md      # Complete BLE protocol documentation
└── README.md             # This file
```

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

### 3. Connect to Device(s)
**Single Cup Mode:**
1. Click "Connect to Device"
2. Select "SGUAI-C3" from pairing dialog
3. Wait for connection confirmation

**Multi-Cup Mode:**
1. Click "Multi-Cup Display" tab
2. Click "Connect 4 Cups"
3. Select each cup one by one (Cup 0-3)
4. Or click "Skip Connection" to test UI without devices

### 4. Use Features
- **Single Cup:** Send text, images, or use the pixel editor
- **Multi-Cup:** Upload images/GIFs, select layout, and play animations

## Multi-Cup Display System

### Layouts
- **Grid 2×2:** 4 cups in a 2×2 grid (96×24 pixels total)
- **Landscape Wide:** 4 cups in a row (192×12 pixels total)

### Dynamic GIF Player

Upload animated GIFs and play them across all 4 cups with optional motion effects!

**Features:**
- **Automatic GIF Detection:** System detects multi-frame GIFs automatically
- **Frame Extraction:** Parses GIF frames using omggif library
- **Motion Overlay:** Combine frame animation with scrolling effects
  - Static: Frame-by-frame animation only
  - Scroll Right: Frames + rightward scrolling
  - Scroll Left: Frames + leftward scrolling
  - Flashing: Frames + flashing effect
- **Live Preview:** See exactly what's playing on each cup
- **Playback Controls:** Play, Stop, and Sync buttons
- **Preview Mode:** Works without physical devices (Skip Connection)

**Workflow:**
1. Upload an animated GIF (or generate one with `generate_test_gif.py`)
2. System automatically detects frames and shows animation controls
3. Select a motion overlay mode (optional)
4. Click "Play GIF on Cups"
5. Watch the animated preview update in real-time
6. Animation loops automatically every ~3 seconds per frame

**Technical Details:**
- Frame delay: ~3 seconds (allows time for BLE transmission)
- Supports GIFs with any number of frames
- Each frame is dithered and split across 4 cups
- Preview updates synchronously with device updates
- Graceful fallback when no cups connected (preview-only mode)

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

**Note:** Image sending takes 15-30 seconds per frame. Be patient and wait for confirmation.

## BLE Protocol

See [PROTOCOL_SPEC.md](PROTOCOL_SPEC.md) for complete protocol documentation.

### Quick Reference
- **Service UUID:** `0000ff00-0000-1000-8000-00805f9b34fb`
- **Command Characteristic:** `0000ff01-...` (write)
- **Response Characteristic:** `0000ff02-...` (notify, read)
- **Command Format:** `[0xFF, 0x55, LENGTH, 0x00, FUNCTION, COMMAND, ...DATA]`
- **Image Data:** 126 bytes (6 headers + 120 data bytes)

## Browser Requirements

- Chrome 56+ or Edge 79+
- Web Bluetooth API enabled
- HTTPS (or localhost for development)

## Known Limitations

1. **Device Response Time:** Image commands take 15-30 seconds to process
2. **Multi-Cup Animation Speed:** ~3 seconds per frame (BLE transmission limit)
3. **No Generic Access Service:** Device doesn't expose standard Generic Access service (handled gracefully)
4. **BLE Timeout:** Devices may auto-disconnect after inactivity (manual reconnect required)
5. **Production Build:** Tailwind CDN should be replaced with npm installation for production

## Troubleshooting

### Connection Issues
- Ensure device is powered on and in pairing mode
- Check Web Bluetooth is enabled in browser
- Try refreshing browser and reconnecting

### Image Sending Timeout
- Wait full 30 seconds before retrying
- Check device display - image may appear despite timeout warning
- Simpler images process faster

### Display Not Updating
- Verify device is still connected
- Try sending a simpler command (e.g., read temperature)
- Reconnect if device disconnected

### Multi-Cup Issues
- Ensure all 4 cups are connected before processing images
- Use "Skip Connection" to test UI without devices
- Check that cups are in correct positions (Cup 0-3)

## Development Notes

### Script Load Order (Critical)
```html
<script src="js/ble.js"></script>           <!-- 1. Single-cup BLE manager -->
<script src="js/multiCupBLE.js"></script>   <!-- 2. Multi-cup BLE manager -->
<script src="js/imageSplitter.js"></script> <!-- 3. Image splitting -->
<script src="js/ui.js"></script>            <!-- 4. UI components -->
<script src="js/omggif.js"></script>        <!-- 5. GIF parsing -->
<script src="js/imageProcessor.js"></script><!-- 6. Image processing -->
<script src="js/imageEditor.js"></script>   <!-- 7. Grid state -->
<script src="js/main.js"></script>          <!-- 8. Application logic -->
```

### Global Architecture
- **BLEManager** (`window.bleManager`) - Singleton for single-cup BLE operations
- **MultiCupBLEManager** (`window.multiCupBLE`) - Singleton for multi-cup operations
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
- [x] Multi-cup display system
- [x] Animated GIF support
- [x] Live preview with animation
- [x] Motion overlay effects
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
