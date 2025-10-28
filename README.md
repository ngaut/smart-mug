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

### Processing Options
- **Algorithm:**
  - Floyd-Steinberg Dithering (best for photos)
  - Simple Threshold (best for logos/text)
- **Threshold:** Adjustable 0-255 (default 128)
- **Aspect Ratio:** Maintain or stretch

### Workflow
1. Click "Choose File" and select image
2. Adjust algorithm and threshold
3. Click "Process & Preview"
4. Review processed result
5. Click "Apply to Editor" to load into pixel grid
6. Optionally edit manually with drawing tools
7. Click "Send to Cup" to transfer to device

**Note:** Image sending takes 15-30 seconds. Be patient and wait for confirmation.

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
2. **No Generic Access Service:** Device doesn't expose standard Generic Access service (handled gracefully)
3. **BLE Timeout:** Devices may auto-disconnect after inactivity (manual reconnect required)
4. **Production Build:** Tailwind CDN should be replaced with npm installation for production

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

- [ ] Connection keepalive to prevent auto-disconnect
- [ ] Auto-reconnect on disconnection
- [ ] Progress indicator for image sending
- [ ] Built-in icon library
- [ ] Image history/favorites
- [ ] Multiple dithering algorithms
- [ ] Brightness/contrast adjustments
- [ ] Installation as PWA

## License

[Add your license here]

## Acknowledgments

- Floyd-Steinberg dithering algorithm
- Web Bluetooth Community Group
- Tailwind CSS team
