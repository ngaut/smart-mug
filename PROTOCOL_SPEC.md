# SGUAI-C3 Smart Cup BLE Protocol Specification

## Document Version
Version 2.1 — Reverse-engineered from the official `net.sguai.app` Android APK
(uni-app bundle: `assets/apps/__UNI__7FD700B/www/app-service.js` and
`pages/water/children/app-sub-service.js`), with bitmap encoding corrected
against SGUAI-C3 firmware 1.6 hardware testing.

> **Corrections vs v1.0** (the original implementation analysis):
> 1. Writes have **no `0x0D 0x0A` terminator**; only responses carry a 2-byte
>    trailer.
> 2. The static-image payload is **72 bytes (LEN=0x4E)**, not 120.
> 3. The `0x26` animation command (autonomous on-cup playback) and several
>    other feature bytes (`0x0B`, `0x24`, `0x27`) were not documented.
>
> **Firmware-dependent bitmap encoding** — see §4.5 for details. The APK
> ships a column-major RTL encoder; SGUAI-C3 firmware 1.6 hardware uses
> **row-major LTR, MSB-first**, which is what this client implements.
> The protocol path (frame structure, command bytes, timings) is the same
> in both cases — only the bit ordering inside the 72-byte payload differs.

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

All commands sent to the device follow this structure (no terminators):

```
┌─────────┬─────────┬────────┬──────────┬──────────┬─────────┬──────────┐
│ Header1 │ Header2 │ Length │ Reserved │ Function │ Command │   Data   │
│  (0xFF) │  (0x55) │ (byte) │  (0x00)  │  (byte)  │ (byte)  │ (N bytes)│
└─────────┴─────────┴────────┴──────────┴──────────┴─────────┴──────────┘
    [0]       [1]       [2]       [3]        [4]       [5]     [6..N-1]
```

**Field Definitions:**

| Field | Offset | Size | Value | Description |
|-------|--------|------|-------|-------------|
| Header 1 | 0 | 1 byte | `0xFF` | Fixed command start marker |
| Header 2 | 1 | 1 byte | `0x55` | Fixed command start marker |
| Length | 2 | 1 byte | Variable | **Total length of the written buffer** (i.e. equals N) |
| Reserved | 3 | 1 byte | `0x00` | Reserved (always `0x00`) |
| Function | 4 | 1 byte | `0x01` / `0x02` | `0x01` = read/get, `0x02` = write/set |
| Command | 5 | 1 byte | Variable | Feature byte (see §4) |
| Data | 6 to N-1 | Variable | Variable | Command payload (can be empty) |

**Key correction vs v1.0:** The `LEN` byte equals the byte count actually
written to the GATT characteristic. The official client (`hexToBu` at
`app-service.js:15096`) writes the array verbatim with no trailer, and every
command builder in the APK stops at the last data byte. Verified across all
read/write commands.

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

## 3. Function Codes and Feature Bytes

### 3.1 Function byte (offset 4)

| Function | Code | Description |
|----------|------|-------------|
| Read / Get | `0x01` | Query device state |
| Write / Set | `0x02` | Configure device / send display data |

The original v1.0 spec called these "Device Information" and "Display
Control"; reverse-engineering shows they are simply read vs. write — the
*feature byte* at offset 5 is what selects what to read or write.

### 3.2 Known feature bytes (C3 / C5 family)

| Feature | Read | Write | Purpose |
|---------|------|-------|---------|
| `0x01` | ✔ | — | Temperature (°C / °F per `0x0B` setting) |
| `0x02` | ✔ | — | Battery percent |
| `0x09` | ✔ | — | Firmware version (`X.Y`) |
| `0x0B` | ✔ | ✔ | Temperature unit (0=°C, 1=°F) |
| `0x17` | — | ✔ | Greeting text (UTF-16BE codepoints, sub-cmd `0x01`) |
| `0x23` | ✔ | ✔ | Display motion mode (0=static, 1=scroll→, 2=scroll←, 3=flash) |
| `0x25` | — | ✔ | **Static** bitmap upload (72-byte payload) |
| `0x26` | — | ✔ | **Animation** upload (prologue + per-frame, see §4.6) |
| `0x27` | ✔ | ✔ | Auto-screen-off flag (boolean — see §4.7) |

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

### 4.5 Set Static Image (Function: 0x02, Command: 0x25)

**Purpose:** Upload one monochrome bitmap as a static frame.

**Command Frame:**
```
Offset: 0    1    2    3    4    5    6 ... 77
Bytes:  FF   55   4E   00   02   25   [72 bytes of bit-packed bitmap]
```

- `LEN = 0x4E` (78), the actual GATT write length.
- Display: **48 × 12 pixels = 576 bits = 72 bytes**.
- The C5 family uses a 12 × 36 layout that packs to 60 bytes (`LEN = 0x42`).
  The official builder selects 0x42 only when the supplied hex string is 120
  characters (60 bytes); otherwise it sends 0x4E (72 bytes) — the C3 case.

**Bit Packing — firmware-dependent.** Two encodings exist; this client
implements the second (verified on hardware):

> ⚠️ **Firmware mismatch warning.** The official `net.sguai.app` Android
> APK ships a **column-major right-to-left** encoder
> (`app-sub-service.pretty.js:10113-10135`):
>
> ```js
> for (col = WIDTH - 1; col >= 0; col--)
>     for (row = 0; row < HEIGHT; row++)
>         accumulate_bit(grid[row][col]);
> ```
>
> That encoding is **byte-incompatible with SGUAI-C3 firmware 1.6** —
> sending its output produces a scrambled display where bit index N
> lands at row `N÷48`, col `N mod 48`. The APK presumably targets newer
> firmware (likely C3 fw ≥ 2.x or C5).

**Empirically verified encoding for SGUAI-C3 fw 1.6 — row-major LTR,
rows TTB, MSB-first:**

```js
for (row = 0; row < HEIGHT; row++)            // rows TOP-TO-BOTTOM
    for (col = 0; col < WIDTH; col++)         // cols LEFT-TO-RIGHT
        accumulate_bit(grid[row][col]);       // 1 = LED on
        if (8 bits accumulated) emit_byte_MSB_first();
```

Verified by single-pixel and "F"-shape tests on the user's cup
(2026-04-25): `grid[0][0] = 1` lights the physical top-left LED; an
asymmetric F renders right-side-up. Switching to the APK's column-major
RTL encoder produced a scrambled display whose pixel positions matched
exactly the row-major-LTR-interpretation of the *APK's bytes*, confirming
the cup's framebuffer scan is row-major LTR.

So for the 48×12 C3 display:
- byte 0 bit 7 = pixel `(row=0, col=47)`
- byte 0 bit 0 = pixel `(row=7, col=47)`
- byte 1 bits 7..4 = pixels `(row=8..11, col=47)`
- byte 1 bits 3..0 = pixels `(row=0..3, col=46)`
- … bytes straddle column boundaries because 12 rows ≠ multiple of 8.

**Pixel values:** `0` = LED off, `1` = LED on.

**Encoding (Python reference, matches the official app):**
```python
def pack_bitmap(grid):  # grid is grid[row][col], 12 rows × 48 cols
    bits = []
    for col in range(47, -1, -1):
        for row in range(12):
            bits.append(1 if grid[row][col] else 0)
    out = bytearray(72)
    for i, b in enumerate(bits):
        if b: out[i // 8] |= 1 << (7 - (i % 8))
    return bytes(out)
```

**Response:** Cup ACKs at the BLE-write level; no application response.

---

### 4.6 Set Animation (Function: 0x02, Command: 0x26)

**Purpose:** Store an animation in the cup's flash so it plays autonomously
afterwards — no further BLE traffic during playback. This is how the official
app achieves smooth animations.

**Wire flow (two phases):**

**Phase 1 — Prologue (8 bytes):**
```
Offset: 0    1    2    3    4    5    6        7
Bytes:  FF   55   08   00   02   26   <count>  <speed>
```
Tells the cup to expect `count` frames at the given speed (1 byte; default
`0x82` = 130 in the official UI).

**Speed-byte semantics (partially characterized on SGUAI-C3 fw 1.6,
2026-04-25):** larger byte = faster playback (monotonic). The exact
unit / relationship is not yet pinned down quantitatively. Observed:

| Speed | Behavior |
|------:|---|
| 20    | Slow — several seconds per 4-frame cycle |
| 130 (official default) | Comfortable mid-speed, roughly 1 second per 4-frame cycle |
| 200   | Faster than default |
| 255   | Very fast, near-blur |

The relationship is *not* `ms_per_frame = speed` (under that hypothesis
small values would be fast, but they're slow). It is consistent with an
inverse model (`period ∝ 1/speed`) or with the cup using `speed` as an
internal accumulator increment with frame advance on overflow, but two
data points isn't enough to discriminate. Stick with the official
default of 130 for general use; iterate empirically for specific
cycle rates.

Range: 1–255 in the official app. 0 produces unspecified behavior.

**Phase 2 — Per-frame upload, repeated `count` times:**
```
Offset: 0    1    2    3    4    5    6      7        8 .. 79
Bytes:  FF   55   50   00   02   26   <idx>  <speed>  [72-byte bitmap]
```
- `idx` is the 0-based frame index (1 byte → max 256 frames).
- `speed` is repeated in every frame for redundancy.
- `LEN = 0x50` (80) — 8-byte header (`FF 55 LEN 00 02 26 idx speed`) plus
  a 72-byte bitmap. The official builder computes
  `LEN = ceil((bitmap_hex_len + 16) / 2)` (`sub-service.pretty.js:9682`),
  where the constant 16 accounts for the 16 hex chars of header.
  Note: this is **different** from the `0x25` static command's `LEN = 0x4E`,
  because the static frame omits the idx/speed bytes.
- The official app paces frames **~150 ms apart**, response-acked, retrying
  up to 10 times on write failure.

After the last frame is acknowledged, the cup begins playback from internal
storage and continues until power-off or another `0x25`/`0x26` write replaces
it. Frame transmission for a 5-frame animation completes in roughly 1 second
at MTU 247+, vs. ~30 s × 5 with the old `0x25`-streaming approach.

**Static-from-animation slice trick:**
The official app stores every saved frame in unified
`FF55 LEN 0002 26 idx speed bitmap` form. To send a single frame as a static
display, it strips the first 16 hex chars (= 8 bytes of header) and ships
the bare bitmap with `0x25`. This pattern confirms the 8-byte per-frame
header above.

**Example — 3-frame animation at 130 ms/frame:**
```
Prologue: FF 55 08 00 02 26 03 82
Frame 0:  FF 55 50 00 02 26 00 82 <72 B>
Frame 1:  FF 55 50 00 02 26 01 82 <72 B>
Frame 2:  FF 55 50 00 02 26 02 82 <72 B>
```

---

### 4.7 Auto-Screen-Off Flag (Function: 0x02 / 0x01, Command: 0x27)

**Purpose:** Enable or disable the firmware's automatic screen-off
behavior. When enabled (the firmware default), the LED matrix powers
down after a brief idle period; when disabled, the display stays
alive indefinitely.

**Empirical note:** the original v2.0 reverse-engineering inferred a
`seconds` duration for this byte. Probing on SGUAI-C3 fw 1.6 (2026-04)
showed it is actually a **boolean**: any non-zero value reads back as
`1`, only `0` reads back as `0`. The duration when enabled is fixed
in firmware and cannot be tuned through this command.

**Set Frame:**
```
Offset: 0    1    2    3    4    5    6
Bytes:  FF   55   07   00   02   27   <flag>
```
- `<flag>`: `0x00` to disable auto-off, any non-zero to enable.

**Read Frame:**
```
Offset: 0    1    2    3    4    5    6
Bytes:  FF   55   07   00   01   27   00
```
- Response payload final byte: `0x00` (disabled) or `0x01` (enabled).

**Use case:** for animation playback or always-on dashboard scenarios,
send `set 0` once after connecting. Persistence across power cycles
not verified — re-send after reconnects to be safe.

---

## 5. Communication Protocol Details

### 5.1 Connection sequence (mirrors the official Android app)

1. Scan and match by advertised service UUID `0000ff00-...`; the device
   advertises its name (`SGUAI-C3`) too.
2. GATT connect.
3. **Android only:** `setBLEMTU({mtu: 500})` then sleep 2 s.
4. Get service `0000ff00-...` and its characteristics:
   - `0000ff01-...` — write (command)
   - `0000ff02-...` — notify, read (response)
5. Enable notifications on `0xff02`.

### 5.2 Write paths — two flavors

| Path | Used by | Pre-write timing | State reset |
|------|---------|------------------|-------------|
| **`GET_BLE_WRITE` action** | reads, mode `0x23`, static image `0x25`, animation prologue `0x26`, every other state-changing command | 20 ms `Sleep(20)` after clearing the response-state buffer | Yes |
| **Direct `writeValue`** (page-level) | greeting `0x17`, animation per-frame `0x26 (80 B)` | none | No |

The 20 ms guard exists to give the in-app state reset time to propagate
before the write — it is not a firmware requirement, but the official app
applies it consistently to commands that expect a response. The animation
per-frame loop bypasses the guard to maximize throughput; the greeting
bypasses it because greetings have no response handler at all.

### 5.3 Response handling

Responses are notifications on `0xff02`. The receive parser strips a
2-byte trailer (`0x0D 0x0A`) and then dispatches on the feature byte
(byte 4 of the un-stripped frame, byte 2 of the payload). Feature bytes
**without** a parser entry — including `0x17` (greeting), `0x25` (static
image), and `0x26` (animation) — are treated as fire-and-forget; the cup
ACKs them at the BLE-write layer but emits no application-level response.

### 5.4 Animation retry policy

The per-frame loop retries on BLE-write failure up to **10 attempts** with
**100 ms** backoff between retries (`sub-service.pretty.js:9719-24`). On
exhaustion it surfaces an error to the user. Successful writes are paced
**150 ms** apart (`:9716-18`).

### 5.5 Data types

| Data Type | Size | Endianness | Notes |
|-----------|------|------------|-------|
| Frame header | 2 B | Fixed | Always `0xFF 0x55` |
| Length field | 1 B | — | Equals total written buffer length |
| Function | 1 B | — | `0x01` read, `0x02` write |
| Feature | 1 B | — | See §3.2 |
| Greeting text | 2 B/code unit | UTF-16 BE | Surrogate pairs for non-BMP |
| Bitmap | 72 B | MSB-first per byte | **Row-major LTR, rows TTB** (verified on fw 1.6); the APK uses column-major RTL — see §4.5 for the firmware-dependent caveat |
| Response trailer | 2 B | Fixed | `0x0D 0x0A` (responses only — writes have no trailer) |

---

## 7. Command Reference Summary

| Command | Function | Feature | Data | LEN | Purpose |
|---------|----------|---------|------|-----|---------|
| Read Version | `0x01` | `0x09` | 1 B `0x00` | 7 | Firmware version `X.Y` |
| Read Temperature | `0x01` | `0x01` | 1 B `0x00` | 7 | Temperature (last data byte) |
| Read Battery | `0x01` | `0x02` | 1 B `0x00` | 7 | Battery percent |
| Read Temp Unit | `0x01` | `0x0B` | 1 B `0x00` | 7 | 0=°C, 1=°F |
| Set Greeting | `0x02` | `0x17` | `<sub>` + UTF-16BE | 7 + 2K | `sub=0x01` + K UTF-16 code units, or `sub=0x00` (no data) to clear |
| Set Motion | `0x02` | `0x23` | 1 B mode | 7 | 0=static, 1=→, 2=←, 3=flash |
| Set Static Image | `0x02` | `0x25` | 72 B bitmap | 78 (`0x4E`) | One frame |
| Animation Prologue | `0x02` | `0x26` | `<count><speed>` | 8 | Begin N-frame animation |
| Animation Frame | `0x02` | `0x26` | `<idx><speed>` + 72 B | 80 (`0x50`) | Store frame (×N) |
| Set Auto-off | `0x02` | `0x27` | 1 B flag | 7 | 0=disabled (always on), nonzero=enabled |

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

### Example 3: Set greeting "OK"
```
'O' = U+004F → 00 4F
'K' = U+004B → 00 4B

Command:  FF 55 0B 00 02 17 01  00 4F 00 4B
Length:   0x0B (11)
```

### Example 4: Clear greeting (empty)
```
Command:  FF 55 07 00 02 17 00
```

### Example 5: Set greeting with emoji "🍵"
```
🍵 = U+1F375 → UTF-16 surrogate pair: D83C DF75

Command:  FF 55 0F 00 02 17 01  D8 3C DF 75 ...
```

### Example 6: Set mode to flashing
```
Command:  FF 55 07 00 02 23 03      (0x03 = flashing)
```

### Example 7: Set static image (all on)
```
Command:  FF 55 4E 00 02 25  FF FF ... (72 × 0xFF)
Length:   0x4E (78)          all 576 pixels lit
```

### Example 8: Upload a 2-frame animation
```
Prologue: FF 55 08 00 02 26 02 82
Frame 0:  FF 55 50 00 02 26 00 82  <72 B bitmap>
Frame 1:  FF 55 50 00 02 26 01 82  <72 B bitmap>
```

---

## 9. Protocol Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-10-28 | Initial specification based on implementation analysis |
| 2.0 | 2026-04-24 | Reverse-engineered from `net.sguai.app` APK. Removed bogus 0x0D/0x0A terminators on writes, corrected static-image size to 72 B, added `0x26` animation command and `0x0B`/`0x27` feature bytes. Bitmap encoder was set to column-major RTL MSB-first to match the APK; this turned out to be wrong for fw 1.6 — see v2.1. |
| 2.1 | 2026-04-25 | **Bitmap encoding corrected to row-major LTR (firmware-dependent).** Hardware testing on SGUAI-C3 firmware 1.6 showed the APK's column-major RTL encoder produces a scrambled display: a single pixel at `grid[0][0]` lit row 11 col 36 (= bit index 564 ÷ 48 / mod 48), proving the cup's framebuffer is row-major LTR. Reverted both Python and JS encoders to row-major LTR MSB-first. The 0x26 animation protocol path itself was correct; only the bit ordering inside each frame's 72-byte payload changed. The APK presumably targets newer firmware (≥ 2.x or C5 family). End-to-end verified: scrolling text reads correctly, a 4-digit cycling animation plays in order (1→2→3→4→1...). **Speed-byte semantics partially characterized**: larger byte = faster playback (monotonic), unit not yet quantified — see §4.6. Default 130 cycles a 4-frame animation in ~1 second. |

---

## 10. Source citations

All findings in this spec are traceable to specific lines in the
beautified APK bundle (`assets/apps/__UNI__7FD700B/www/`):

| Topic | File | Line |
|-------|------|------|
| Receive parser dispatch | `app-service.js` | 53159+ |
| Hex-to-buffer (no terminator on writes) | `app-service.js` | 15096 |
| `GET_BLE_WRITE` action with 20 ms guard | `app-service.js` | 49825 / 49854 |
| `setBLEMTU(500)` on Android | `app-service.js` | 49500 |
| Static image builder (`0x25`) | `app-service.js` | 51592 |
| Animation prologue builder (`0x26`) | `app-service.js` | 51624 |
| Per-frame animation loop with retry | `app-sub-service.js` | 9678–9724 |
| APK's bitmap encoder (column-major RTL — *not* used here, see §4.5) | `app-sub-service.js` | 10113–10135 |
| Greeting builder (page-level) | `app-sub-service.js` | 4083–4088 |

---

**END OF SPECIFICATION**
