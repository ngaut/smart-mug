# SGUAI-C3 Smart Cup BLE Protocol Specification

## Document Version
Version 1.0 - Complete Protocol Specification

---

## 1. BLE Service Overview

### 1.1 Service UUID
```
Service UUID: 0000ff00-0000-1000-8000-00805f9b34fb
```

### 1.2 Characteristics

| Characteristic | UUID | Properties | Description |
|---------------|------|------------|-------------|
| Command | `0000ff01-0000-1000-8000-00805f9b34fb` | Write | Send commands to device |
| Response | `0000ff02-0000-1000-8000-00805f9b34fb` | Notify, Read | Receive responses from device |

### 1.3 Additional Services Used

| Service | UUID | Purpose |
|---------|------|---------|
| Generic Access | `generic_access` | Device name verification |
| Device Information | `device_information` | Model number, firmware version (optional) |

---

## 2. Protocol Frame Structure

### 2.1 Command Frame Format

All commands sent to the device follow this structure:

```
┌─────────┬─────────┬────────┬──────────┬──────────┬─────────┬──────────┬─────────────┬──────────┐
│ Header1 │ Header2 │ Length │ Reserved │ Function │ Command │   Data   │ Terminator1 │ Term2    │
│  (0xFF) │  (0x55) │ (byte) │  (0x00)  │  (byte)  │ (byte)  │ (N bytes)│   (0x0D)    │ (0x0A)   │
└─────────┴─────────┴────────┴──────────┴──────────┴─────────┴──────────┴─────────────┴──────────┘
    [0]       [1]       [2]       [3]        [4]       [5]     [6..N-3]     [N-2]        [N-1]
```

**Field Definitions:**

| Field | Offset | Size | Value | Description |
|-------|--------|------|-------|-------------|
| Header 1 | 0 | 1 byte | `0xFF` | Fixed command start marker |
| Header 2 | 1 | 1 byte | `0x55` | Fixed command start marker |
| Length | 2 | 1 byte | Variable | **Total length of entire command including headers and terminators** |
| Reserved | 3 | 1 byte | `0x00` | Reserved field (always 0x00) |
| Function | 4 | 1 byte | Variable | Function category identifier |
| Command | 5 | 1 byte | Variable | Specific command within function category |
| Data | 6 to N-3 | Variable | Variable | Command payload (can be empty) |
| Terminator 1 | N-2 | 1 byte | `0x0D` | Fixed command end marker (CR) |
| Terminator 2 | N-1 | 1 byte | `0x0A` | Fixed command end marker (LF) |

**CRITICAL NOTE:** The Length field (byte[2]) contains the **total length of the entire command**, including:
- Headers (0xFF, 0x55)
- Length byte itself
- All data bytes
- Terminators (0x0D, 0x0A)

### 2.2 Response Frame Format

Responses from the device follow the same structure:

```
┌─────────┬─────────┬────────┬──────────────┬─────────────┬──────────┐
│ Header1 │ Header2 │ Length │     Data     │ Terminator1 │ Term2    │
│  (0xFF) │  (0x55) │ (byte) │   (N bytes)  │   (0x0D)    │ (0x0A)   │
└─────────┴─────────┴────────┴──────────────┴─────────────┴──────────┘
```

**Response Parsing:**
- Client validates: `response[0] == 0xFF && response[N-2] == 0x0D && response[N-1] == 0x0A`
- If valid, extracts payload: `payload = response[2..N-3]` (excludes 0xFF, length byte, and terminators)
- If invalid structure, entire response array is returned as-is

---

## 3. Function Categories and Commands

### 3.1 Function Category Codes

| Function | Code | Description |
|----------|------|-------------|
| Device Information | `0x01` | Query device status and information |
| Display Control | `0x02` | Control display content and modes |

---

## 4. Command Specifications

### 4.1 Read Version (Function: 0x01, Command: 0x09)

**Purpose:** Query device version information

**Command Frame:**
```
Offset: 0    1    2    3    4    5    6
Bytes:  FF   55   07   00   01   09   00
```

**Field Breakdown:**
- `0xFF 0x55`: Headers
- `0x07`: Total length (7 bytes)
- `0x00`: Reserved
- `0x01`: Function = Device Information
- `0x09`: Command = Read Version
- `0x00`: Data (placeholder, likely unused)

**Response:**
- After frame parsing, returns version information bytes
- Format: Implementation-specific (displayed as comma-separated decimal values)
- Example response payload: `[1, 0, 3]` representing version "1,0,3"

---

### 4.2 Read Temperature (Function: 0x01, Command: 0x01)

**Purpose:** Read current temperature from device sensor

**Command Frame:**
```
Offset: 0    1    2    3    4    5    6
Bytes:  FF   55   07   00   01   01   00
```

**Field Breakdown:**
- `0xFF 0x55`: Headers
- `0x07`: Total length (7 bytes)
- `0x00`: Reserved
- `0x01`: Function = Device Information
- `0x01`: Command = Read Temperature
- `0x00`: Data (placeholder, likely unused)

**Response:**
- After frame parsing, returns temperature data bytes
- Temperature value: **Last byte of payload** (1-byte unsigned integer)
- Unit: Celsius (°C)
- Range: 0-255°C (typical operational range likely 0-100°C)

**Example:**
- Response payload: `[0x05, 0x01, 0x1F]` → Temperature = `0x1F` = 31°C

---

### 4.3 Set Greeting Message (Function: 0x02, Command: 0x17, Subcommand: 0x01)

**Purpose:** Send text message to display on device

**Command Frame:**
```
Offset: 0    1    2    3    4    5    6    7    8    9    ...
Bytes:  FF   55   LEN  00   02   17   01   CP0H CP0L CP1H CP1L ...
```

**Field Breakdown:**
- `0xFF 0x55`: Headers
- `LEN`: Total length (calculated dynamically: `6 + 1 + message.length * 2`)
- `0x00`: Reserved
- `0x02`: Function = Display Control
- `0x17`: Command = Set Text
- `0x01`: Subcommand = Greeting Message
- Followed by character codepoints (2 bytes per character, big-endian)

**Text Encoding:**
- Each character encoded as **Unicode codepoint** (2 bytes, big-endian)
- Format: `[high_byte, low_byte]` for each character
- Maximum message length: **20 characters** (enforced by application)
- Encoding process:
  1. For each character in message string
  2. Get Unicode codepoint: `cp = char.codePointAt(index)`
  3. Split into bytes: `high = (cp >> 8) & 0xFF`, `low = cp & 0xFF`
  4. Append `[high, low]` to command data

**Example:**
Message: "Hi" (2 characters)
- 'H' = U+0048: `[0x00, 0x48]`
- 'i' = U+0069: `[0x00, 0x69]`
- Command: `[0xFF, 0x55, 0x0B, 0x00, 0x02, 0x17, 0x01, 0x00, 0x48, 0x00, 0x69]`
  - Length = 11 bytes (0x0B)

**Response:**
- Returns acknowledgment (format not specified in implementation)

---

### 4.4 Set Dynamic Mode (Function: 0x02, Command: 0x23)

**Purpose:** Configure display animation mode

**Command Frame:**
```
Offset: 0    1    2    3    4    5    6
Bytes:  FF   55   07   00   02   23   MODE
```

**Field Breakdown:**
- `0xFF 0x55`: Headers
- `0x07`: Total length (7 bytes)
- `0x00`: Reserved
- `0x02`: Function = Display Control
- `0x23`: Command = Set Dynamic Mode
- `MODE`: Animation mode value (1 byte)

**Mode Values:**

| Mode | Value | Description |
|------|-------|-------------|
| Static | `0x00` | No animation, static display |
| Scroll Right | `0x01` | Content scrolls from left to right |
| Scroll Left | `0x02` | Content scrolls from right to left |
| Flashing | `0x03` | Display flashes on/off |

**Example:**
Set to "Scroll Left" mode:
```
[0xFF, 0x55, 0x07, 0x00, 0x02, 0x23, 0x02]
```

**Response:**
- Returns acknowledgment (format not specified in implementation)

---

### 4.5 Set Image Data (Function: 0x02, Command: 0x25)

**Purpose:** Upload monochrome bitmap image to device display

**Command Frame:**
```
Offset: 0    1    2    3    4    5    6 ... 125
Bytes:  FF   55   LEN  00   02   25   [120 bytes of image data]
```

**Field Breakdown:**
- `0xFF 0x55`: Headers
- `LEN`: Total length = 126 bytes (0x7E)
- `0x00`: Reserved
- `0x02`: Function = Display Control
- `0x25`: Command = Set Image
- Followed by 120 bytes of bit-packed image data

**Image Format Specification:**

**Display Hardware:**
- Resolution: **48 pixels (width) × 12 pixels (height)**
- Total pixels: 576
- Color depth: 1-bit monochrome (black/white)
- Packed size: 72 bytes (576 bits / 8)

**CRITICAL: Actual Implementation Uses 120 Bytes**
```javascript
const flatData = new Uint8Array(120);  // Not 72!
```
This suggests the device expects 120 bytes even though only 72 bytes (576 bits) are needed for the visible 48×12 display. The extra 48 bytes may be:
- Buffer padding
- Extended display memory
- Reserved space for future use
- Internal device requirement

**Bit Packing Format:**

1. **Pixel Order:** Row-major order (scan left-to-right, top-to-bottom)
   ```
   Row 0: Pixel[0,0] to Pixel[0,47]
   Row 1: Pixel[1,0] to Pixel[1,47]
   ...
   Row 11: Pixel[11,0] to Pixel[11,47]
   ```

2. **Bit Layout Within Each Byte:**
   - **MSB-first** (big-endian bit order)
   - Bit 7 (leftmost) = first pixel
   - Bit 0 (rightmost) = eighth pixel

   ```
   Byte N:
   ┌─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┐
   │ Bit7│ Bit6│ Bit5│ Bit4│ Bit3│ Bit2│ Bit1│ Bit0│
   │Pix N│Pix+1│Pix+2│Pix+3│Pix+4│Pix+5│Pix+6│Pix+7│
   └─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┘
   ```

3. **Pixel Values:**
   - `0` = White (LED off)
   - `1` = Black (LED on)

**Encoding Algorithm:**
```javascript
const IMAGE_WIDTH = 48;
const IMAGE_HEIGHT = 12;
const flatData = new Uint8Array(120);  // Device expects 120 bytes

let bitIndex = 0;
for (let row = 0; row < IMAGE_HEIGHT; row++) {
    for (let col = 0; col < IMAGE_WIDTH; col++) {
        const byteIndex = Math.floor(bitIndex / 8);
        const bitPosition = 7 - (bitIndex % 8);  // MSB first

        if (imageData[row][col] === 1) {  // If pixel is black
            flatData[byteIndex] |= (1 << bitPosition);
        }

        bitIndex++;
    }
}
// Bytes 0-71 contain the 576 pixel bits
// Bytes 72-119 remain 0x00 (padding)
```

**Byte Mapping Example:**
```
Byte 0:  Pixels [0,0] to [0,7]   (Row 0, columns 0-7)
Byte 1:  Pixels [0,8] to [0,15]  (Row 0, columns 8-15)
Byte 2:  Pixels [0,16] to [0,23] (Row 0, columns 16-23)
...
Byte 5:  Pixels [0,40] to [0,47] (Row 0, columns 40-47)
Byte 6:  Pixels [1,0] to [1,7]   (Row 1, columns 0-7)
...
Byte 71: Pixels [11,40] to [11,47] (Row 11, columns 40-47)
Bytes 72-119: Padding (all 0x00)
```

**Example - 3×3 Black Square at Top-Left:**
```
Image Grid (3×3 black pixels):
■ ■ ■ □ □ □ ... (48 pixels wide)
■ ■ ■ □ □ □ ...
■ ■ ■ □ □ □ ...
□ □ □ □ □ □ ... (12 pixels tall)
...

Byte 0: 11100000 = 0xE0  (Row 0, pixels 0-7)
Byte 1: 00000000 = 0x00  (Row 0, pixels 8-15)
...
Byte 6: 11100000 = 0xE0  (Row 1, pixels 0-7)
...
Byte 12: 11100000 = 0xE0 (Row 2, pixels 0-7)
...
All other bytes: 0x00
```

**Complete Command Example:**
```
Command: [0xFF, 0x55, 0x7E, 0x00, 0x02, 0x25, <120 image bytes>]
Total length: 126 bytes (0x7E)
```

**Response:**
- Returns acknowledgment (format not specified in implementation)

---

## 5. Communication Protocol Details

### 5.1 Connection Sequence

1. **Device Discovery:**
   - Filter: Device name = "SGUAI-C3"
   - Optional services: `generic_access`, `device_information`, `0000ff00-...`

2. **GATT Connection:**
   - Connect to GATT server
   - Verify device name via Generic Access service (`gap.device_name`)
   - Expected value: "SGUAI-C3" (strict match required)

3. **Service/Characteristic Setup:**
   - Get primary service: `0000ff00-0000-1000-8000-00805f9b34fb`
   - Get command characteristic: `0000ff01-...` (write)
   - Get response characteristic: `0000ff02-...` (notify, read)
   - Enable notifications on response characteristic

4. **Ready State:**
   - Connection established
   - Notifications active
   - Ready to send commands

### 5.2 Request-Response Pattern

**Timing:**
- Command timeout: **5000ms (5 seconds)**
- Each command waits for response before returning
- Unsolicited responses logged but not matched to pending commands

**Flow:**
```
Client                          Device
  |                               |
  |---(1) Write Command---------->|
  |                               |
  |   [Wait up to 5s for response]
  |                               |
  |<--(2) Notification Response---|
  |                               |
  |   [Parse and return payload]  |
  |                               |
```

**Error Handling:**
- Timeout after 5 seconds → `Error("Device response timeout")`
- Invalid response format → Return raw response array
- Connection lost → All pending requests rejected

### 5.3 Data Types and Endianness

| Data Type | Size | Endianness | Usage |
|-----------|------|------------|-------|
| Command header | 2 bytes | Fixed | Always `0xFF 0x55` |
| Length field | 1 byte | N/A | Unsigned integer (0-255) |
| Function/Command codes | 1 byte | N/A | Unsigned integer |
| Unicode codepoint | 2 bytes | Big-endian | High byte first |
| Temperature | 1 byte | N/A | Unsigned integer (Celsius) |
| Mode value | 1 byte | N/A | Unsigned integer |
| Bitmap data | 120 bytes | MSB-first per byte | Bit 7 = leftmost pixel |
| Terminator | 2 bytes | Fixed | Always `0x0D 0x0A` |

---

## 6. Implementation Notes

### 6.1 Known Issues and Inconsistencies

**Issue 1: Temperature Command Uses String Literals**
```javascript
// INCORRECT: Uses string literals instead of numeric values
await this.executeCommand(["0xFF", "0x55", "0x07", "0x0", "0x1", "0x1", "0x0"]);

// Should be (like other commands):
await this.executeCommand([0xFF, 0x55, 0x07, 0x00, 0x01, 0x01, 0x00]);
```
**Impact:** JavaScript coerces strings to numbers in `setUint8()`, so it works, but is inconsistent.

**Issue 2: Dynamic Mode Command Uses Mixed Types**
```javascript
// INCORRECT: Mixes string literals and numeric variable
await this.executeCommand(["0xFF", "0x55", "0x7", "0x0", "0x2", "0x23", modeValue]);

// Should be:
await this.executeCommand([0xFF, 0x55, 0x07, 0x00, 0x02, 0x23, modeValue]);
```

**Issue 3: Image Data Buffer Size Mismatch**
- Display is 48×12 = 576 pixels = 72 bytes needed
- Implementation allocates 120 bytes
- Reason unclear (device firmware requirement, buffer padding, or future expansion)

### 6.2 Security Considerations

1. **Device Name Verification:**
   - Always verify device name matches "SGUAI-C3"
   - Prevents connection to incorrect devices
   - Uses Generic Access service for verification

2. **Input Validation:**
   - Greeting message: Maximum 20 characters (not enforced by protocol, only application)
   - Mode values: Must be 0-3 (validated before sending)
   - Image data: Must be 120 bytes (enforced by buffer allocation)

3. **Error Handling:**
   - All commands wrapped in try-catch blocks
   - Timeout protection prevents hanging
   - Response validation checks frame markers

### 6.3 Best Practices

1. **Command Construction:**
   - Always use numeric literals (not strings)
   - Calculate length field dynamically for variable-length commands
   - Verify length field = actual command length

2. **Response Handling:**
   - Always validate frame markers (`0xFF`, `0x0D`, `0x0A`)
   - Extract payload by removing headers and terminators
   - Handle timeout gracefully

3. **Connection Management:**
   - Check connection status before sending commands
   - Clean up on disconnect (stop notifications, clear pending requests)
   - Handle unexpected disconnections

---

## 7. Command Reference Summary

| Command | Function | Command | Data Length | Total Length | Purpose |
|---------|----------|---------|-------------|--------------|---------|
| Read Version | `0x01` | `0x09` | 1 byte | 7 bytes | Query firmware version |
| Read Temperature | `0x01` | `0x01` | 1 byte | 7 bytes | Read temperature sensor |
| Set Greeting | `0x02` | `0x17` | Variable | 7 + N*2 bytes | Send text message (N ≤ 20) |
| Set Mode | `0x02` | `0x23` | 1 byte | 7 bytes | Set animation mode (0-3) |
| Set Image | `0x02` | `0x25` | 120 bytes | 126 bytes | Upload bitmap image |

---

## 8. Appendix: Example Commands

### Example 1: Read Version
```
Command:  [0xFF, 0x55, 0x07, 0x00, 0x01, 0x09, 0x00]
Response: [0xFF, 0x55, 0x05, 0x01, 0x00, 0x03, 0x0D, 0x0A]
Payload:  [0x01, 0x00, 0x03]  → Version "1,0,3"
```

### Example 2: Read Temperature (31°C)
```
Command:  [0xFF, 0x55, 0x07, 0x00, 0x01, 0x01, 0x00]
Response: [0xFF, 0x55, 0x05, 0x05, 0x01, 0x1F, 0x0D, 0x0A]
Payload:  [0x05, 0x01, 0x1F]
Temp:     0x1F = 31°C (last byte)
```

### Example 3: Set Greeting "OK"
```
Message: "OK"
- 'O' = U+004F: [0x00, 0x4F]
- 'K' = U+004B: [0x00, 0x4B]

Command:  [0xFF, 0x55, 0x0B, 0x00, 0x02, 0x17, 0x01,
           0x00, 0x4F, 0x00, 0x4B]
Length:   11 bytes (0x0B)
```

### Example 4: Set Mode to Flashing
```
Command:  [0xFF, 0x55, 0x07, 0x00, 0x02, 0x23, 0x03]
Mode:     0x03 = Flashing
```

### Example 5: Set Image (All Black)
```
Command:  [0xFF, 0x55, 0x7E, 0x00, 0x02, 0x25,
           0xFF, 0xFF, ... (118 more 0xFF bytes)]
Length:   126 bytes (0x7E)
Result:   All 576 pixels lit (first 72 bytes = 0xFF)
```

---

## 9. Protocol Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-10-28 | Initial specification based on implementation analysis |

---

## 10. Additional Information

### 10.1 Web Bluetooth API Requirements
- Chrome 56+ or Edge 79+ (with Web Bluetooth enabled)
- HTTPS required (or localhost for development)
- User gesture required to initiate pairing

### 10.2 Device Requirements
- BLE 4.0+ support
- Device name must be exactly "SGUAI-C3"
- Must implement custom service UUID `0000ff00-...`
- Must support GATT notifications on response characteristic

---

**END OF SPECIFICATION**
