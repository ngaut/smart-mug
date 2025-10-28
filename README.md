# SGUAI Smart Cup Control Application

Web-based control application for the SGUAI-C3 Smart Cup - a Bluetooth-enabled smart beverage container with a 48×12 pixel LED display.

## Features

- 🔗 **Bluetooth Connectivity** - Web Bluetooth API for device pairing
- 🌡️ **Temperature Monitoring** - Real-time sensor reading
- 📝 **Text Display** - Send greeting messages (UTF-8, 20 char limit)
- 🎬 **Display Modes** - Static, scrolling (both directions), flashing
- 🎨 **Visual Editor** - WYSIWYG pixel grid editor with draw/erase/clear/fill tools
- 📷 **Image Upload** - Upload photos with Floyd-Steinberg dithering for monochrome conversion

## Technology Stack

- **Frontend:** Vanilla JavaScript (ES6+), HTML5, Tailwind CSS (CDN)
- **Communication:** Web Bluetooth API
- **Image Processing:** Canvas API, Floyd-Steinberg dithering algorithm
- **Display:** 48×12 pixel monochrome LED matrix

## Project Structure

```
├── index.html              # Main entry point
├── css/
│   └── styles.css         # Custom styling for pixel grid
├── js/
│   ├── ble.js            # Bluetooth communication layer
│   ├── ui.js             # UI components and panels
│   ├── imageProcessor.js # Image processing and dithering
│   ├── imageEditor.js    # Pixel grid state management
│   └── main.js           # Application orchestration
├── assets/
│   └── icons/
│       └── favicon.svg
└── PROTOCOL_SPEC.md      # Complete BLE protocol documentation
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

### 3. Connect to Device
1. Click "Connect to Device"
2. Select "SGUAI-C3" from pairing dialog
3. Wait for connection confirmation

### 4. Use Features
- **Read Version/Temperature** - Query device information
- **Set Greeting Message** - Send text (max 20 characters)
- **Set Dynamic Mode** - Choose animation style
- **Set Static Image** - Draw manually or upload photos

## Image Upload Feature

### Supported Formats
- JPG, PNG, GIF
- Any size (automatically resized to 48×12)

### Dithering Algorithms

**🎬 Temporal (Animated - Recommended for best quality!):**
- **Temporal PWM** - Creates perceived grayscale through frame animation (4 frames)
- **Temporal + Floyd-Steinberg** - Hybrid approach for highest quality

**📸 Spatial (Single Frame):**
- **Floyd-Steinberg** - Error diffusion, best for photos
- **Atkinson** - Cleaner, less noise than Floyd-Steinberg
- **Ordered/Bayer** - Pattern-based, good for textures
- **Simple Threshold** - Fast, best for logos/text

### Image Enhancement
- **Auto-Contrast** - Automatic histogram equalization
- **Brightness** - Adjust -100 to +100
- **Contrast** - Adjust -100 to +100
- **Sharpening** - Enhance edges (0 to 2.0)
- **Threshold** - Binary cutoff (0-255)
- **Aspect Ratio** - Maintain or stretch

### Temporal Dithering Workflow (NEW!)

**Creates perceived grayscale from 1-bit display using animation:**

1. Select "Temporal PWM" or "Temporal + Floyd-Steinberg" algorithm
2. Upload and process image
3. **Watch animated preview** - Shows perceived grayscale at 20 FPS
4. Adjust FPS slider (5-60 FPS) to see different speeds
5. **Choose workflow:**

   **Option A: Best Single Frame (Recommended)**
   - Watch animation to identify best-looking frame
   - Click "Send Frame X" button for that specific frame
   - Get best static image on device

   **Option B: Device Animation (Experimental)**
   - Click "🎬 Send Animation to Device (Loop)"
   - Frames cycle on device (~35 second cycle)
   - ⚠️ Too slow for perceived grayscale (BLE limitation)
   - But demonstrates frame cycling capability

**How Temporal Dithering Works:**
- Generates 4 frames with different brightness thresholds
- Bright pixels ON in all frames (100% duty cycle → appears bright)
- Medium pixels ON in half frames (50% duty cycle → appears medium gray)
- Dark pixels ON in few frames (25% duty cycle → appears dark)
- When cycled rapidly, eye perceives smooth grayscale!

**Browser vs Device:**
- **Browser Preview**: 20 FPS → Beautiful perceived grayscale ✨
- **Device**: 0.15 FPS → Individual frames visible, not grayscale ⚠️
- **Limitation**: BLE too slow (needs 15+ FPS for temporal effect)

See [TEMPORAL_DITHERING_REVIEW.md](TEMPORAL_DITHERING_REVIEW.md) for technical details.

### Standard Workflow
1. Click "Choose File" and select image
2. Choose algorithm and adjust enhancement settings
3. Click "Process & Preview"
4. Review processed result and image quality analysis
5. For temporal: Watch animation, select best frame
6. Click "Apply to Editor" to load into pixel grid (optional)
7. Optionally edit manually with drawing tools
8. Click "Send Frame X" or "Send to Cup" to transfer to device

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
2. **Temporal Dithering Speed:** Device animation too slow (~0.15 FPS) for perceived grayscale (needs 15+ FPS). Browser preview demonstrates ideal result.
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

## Development Notes

### Script Load Order (Critical)
```html
<script src="js/ble.js"></script>           <!-- 1. BLE manager -->
<script src="js/ui.js"></script>            <!-- 2. UI components -->
<script src="js/imageProcessor.js"></script> <!-- 3. Image processing -->
<script src="js/imageEditor.js"></script>   <!-- 4. Grid state -->
<script src="js/main.js"></script>          <!-- 5. Application logic -->
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
- [x] Multiple dithering algorithms (Floyd-Steinberg, Atkinson, Ordered, Threshold, Temporal)
- [x] Brightness/contrast/sharpening adjustments
- [x] Temporal dithering with animated preview
- [x] Progress indicator for frame sending
- [x] Image quality analysis with suggestions

### Planned for Device Animation
- [ ] **Faster BLE Protocol** - Compress/pipeline frame data
- [ ] **Device Firmware Update** - Buffer multiple frames internally
- [ ] **Device-Side Animation** - Send all frames once, device cycles autonomously
- [ ] **Delta Encoding** - Only send pixel differences between frames
- [ ] **Smart Frame Selection** - Auto-identify best single frame

### General Improvements
- [ ] Connection keepalive to prevent auto-disconnect
- [ ] Auto-reconnect on disconnection
- [ ] Built-in icon library
- [ ] Image history/favorites
- [ ] Installation as PWA
- [ ] Perceptual dithering (more detail where eye looks)
- [ ] Edge-aware dithering (preserve edges, dither smooth areas)

## License

[Add your license here]

## Acknowledgments

- Floyd-Steinberg dithering algorithm
- Web Bluetooth Community Group
- Tailwind CSS team
