// ble.js - BLE communication for the SGUAI-C3 cup. Wire format and timings
// match the official `net.sguai.app` Android app; see PROTOCOL_SPEC.md and
// python/smart_mug.py for the cross-language reference implementation.

// Service and characteristic UUIDs
const SERVICE_UUID = "0000ff00-0000-1000-8000-00805f9b34fb";
const COMMAND_CHAR_UUID = "0000ff01-0000-1000-8000-00805f9b34fb";
const RESPONSE_CHAR_UUID = "0000ff02-0000-1000-8000-00805f9b34fb";

// Image dimensions
const IMAGE_WIDTH = 48;
const IMAGE_HEIGHT = 12;

// Timings copied from the official app:
//   - rt(20) before every GET_BLE_WRITE             -> WRITE_THROTTLE_MS
//   - setTimeout(..., 100) after the prologue       -> ANIM_PROLOGUE_DELAY_MS
//   - setTimeout(..., 150) between successful frames-> ANIM_FRAME_DELAY_MS
//   - setTimeout(..., 100) on per-frame retry       -> ANIM_RETRY_BACKOFF_MS
//   - failNum >= 10 caps retries                    -> ANIM_MAX_RETRIES
const WRITE_THROTTLE_MS = 20;
const ANIM_PROLOGUE_DELAY_MS = 100;
const ANIM_FRAME_DELAY_MS = 150;
const ANIM_RETRY_BACKOFF_MS = 100;
const ANIM_MAX_RETRIES = 10;

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

/**
 * Pack a 12x48 grid into 72 bytes for the cup's framebuffer.
 *
 * Encoding: **row-major left-to-right, top-to-bottom, MSB-first within
 * each byte**. Verified empirically on SGUAI-C3 firmware 1.6 (2026-04):
 * grid[0][0] = 1 lights the physical top-left LED; an asymmetric "F"
 * shape renders right-side-up.
 *
 * Note: the official `net.sguai.app` Android APK ships a *column-major
 * right-to-left* encoder at `app-sub-service.pretty.js:10113-10135`.
 * That encoder is byte-incompatible with this firmware — its output
 * produces a scrambled display (bit index N lands at row N÷48, col N mod
 * 48). The APK's encoder presumably targets newer firmware (likely C3
 * fw ≥ 2.x or the C5 family). See PROTOCOL_SPEC.md §4.5.
 */
function packBitmap(grid) {
  if (!Array.isArray(grid) || grid.length !== IMAGE_HEIGHT) {
    throw new Error(
      `grid must be a ${IMAGE_HEIGHT}-row array, got ${Array.isArray(grid) ? `length ${grid.length}` : typeof grid}`
    );
  }
  for (let r = 0; r < IMAGE_HEIGHT; r++) {
    if (!Array.isArray(grid[r]) || grid[r].length !== IMAGE_WIDTH) {
      throw new Error(`grid row ${r} must be ${IMAGE_WIDTH} elements, got ${grid[r]?.length ?? typeof grid[r]}`);
    }
  }
  const out = new Uint8Array(72);
  let i = 0;
  for (let row = 0; row < IMAGE_HEIGHT; row++) {
    for (let col = 0; col < IMAGE_WIDTH; col++) {
      if (grid[row][col]) out[i >> 3] |= 1 << (7 - (i & 7));
      i++;
    }
  }
  return out;
}

/**
 * Encode a string as UTF-16 big-endian bytes — 2 bytes per BMP code unit,
 * 4 bytes per non-BMP character (surrogate pair). Matches the official's
 * `charCodeAt` iteration exactly.
 */
function utf16beBytes(str) {
  const bytes = [];
  for (let i = 0; i < str.length; i++) {
    const cu = str.charCodeAt(i);  // 16-bit code unit (surrogate halves for non-BMP)
    bytes.push((cu >> 8) & 0xFF, cu & 0xFF);
  }
  return bytes;
}

/**
 * Promise-based async mutex. Acquire returns an `unlock()` function that
 * must be called (in finally) to release. Pending acquirers form a chain
 * so writes are serialized strictly in arrival order.
 */
class Mutex {
  constructor() { this._chain = Promise.resolve(); }
  async acquire() {
    let unlock;
    const next = new Promise(r => unlock = r);
    const previous = this._chain;
    this._chain = next;
    await previous;
    return unlock;
  }
}

class BLEManager {
  constructor() {
    this.device = null;
    this.server = null;
    this.service = null;
    this.commandCharacteristic = null;
    this.responseCharacteristic = null;
    this.pendingResponse = null;
    this.responseTimeout = null;
    // Serialize all writes — concurrent callers (e.g. parallel multi-cup
    // sends) cannot interleave GATT writes on the same characteristic.
    this._mutex = new Mutex();
  }

  async requestDevice() {
    // Check if Web Bluetooth is supported
    if (!navigator.bluetooth) {
      throw new Error(
        "Web Bluetooth is not supported in this browser. Please use Chrome or Edge."
      );
    }

    try {
      console.log("Requesting BLE devices...");
      // Request device with name filter and required services
      this.device = await navigator.bluetooth.requestDevice({
        filters: [{ name: "SGUAI-C3" }],
        optionalServices: [
          "device_information",
          "generic_access",
          SERVICE_UUID,
        ],
      });

      return this.device;
    } catch (error) {
      // Handle user cancellation
      if (error.name === "NotFoundError") {
        throw new Error(
          "No SGUAI-C3 device found. Please make sure your device is powered on and in pairing mode."
        );
      }
      throw new Error(`Failed to request device: ${error.message}`);
    }
  }

  static async getPreviouslyPairedDevices() {
    try {
      if (!navigator.bluetooth?.getDevices) {
        if (!window.isSecureContext) {
          console.warn("Web Bluetooth requires a secure context (HTTPS or localhost). It is not supported on file:// protocol.");
        } else {
          console.warn("getDevices() not supported in this browser");
        }
        return [];
      }

      const devices = await navigator.bluetooth.getDevices();
      console.log(`Found ${devices.length} previously paired device(s)`);
      return devices;
    } catch (error) {
      console.error("Failed to get previously paired devices:", error);
      return [];
    }
  }


  async connect() {
    if (!this.device) {
      throw new Error("No device selected. Please request a device first.");
    }

    try {
      console.log("Connecting to device...");

      // Connect to the GATT server
      this.server = await this.device.gatt.connect();
      console.log("Connected to GATT server");

      // Verify device name using Generic Access service
      await this.verifyDeviceName();

      // Get the service
      this.service = await this.server.getPrimaryService(SERVICE_UUID);

      // Get the command characteristic
      this.commandCharacteristic = await this.service.getCharacteristic(
        COMMAND_CHAR_UUID
      );

      // Get the response characteristic for notifications
      this.responseCharacteristic = await this.service.getCharacteristic(
        RESPONSE_CHAR_UUID
      );

      // Start notifications for response characteristic
      await this.responseCharacteristic.startNotifications();
      this.responseCharacteristic.addEventListener(
        "characteristicvaluechanged",
        this.handleResponse.bind(this)
      );

      return true;
    } catch (error) {
      this.server = null;
      this.service = null;
      this.commandCharacteristic = null;
      this.responseCharacteristic = null;
      throw new Error(`Failed to connect to device: ${error.message}`);
    }
  }

  disconnect() {
    console.log("Disconnecting from device...");
    if (this.responseCharacteristic) {
      this.responseCharacteristic.stopNotifications();
    }
    if (this.device && this.device.gatt.connected) {
      this.device.gatt.disconnect();
    }
    this.device = null;
    this.server = null;
    this.service = null;
    this.commandCharacteristic = null;
    this.responseCharacteristic = null;
    this.pendingResponse = null;
    if (this.responseTimeout) {
      clearTimeout(this.responseTimeout);
      this.responseTimeout = null;
    }
  }

  isConnected() {
    return this.device !== null && this.device.gatt.connected;
  }

  // Handle incoming responses from the device
  handleResponse(event) {
    const value = event.target.value;
    console.log("Received response:", value);

    // Resolve pending response if exists
    if (this.pendingResponse) {
      // Clear timeout
      if (this.responseTimeout) {
        clearTimeout(this.responseTimeout);
        this.responseTimeout = null;
      }

      // Resolve the promise
      this.pendingResponse.resolve(value);
      this.pendingResponse = null;
    } else {
      // No pending response, show the received value in a toast
      let arr = new Uint8Array(value.buffer);
      showToast(`Received unsolicited data: ${[...arr]}...`, "info");
    }
  }

  // Internal: write-with-response. With `throttle=true` (default) applies the
  // 20 ms pre-guard that the official `GET_BLE_WRITE` action uses; per-frame
  // animation writes pass `throttle=false`.
  async _write(commandData, { throttle = true } = {}) {
    if (!this.commandCharacteristic) throw new Error("Not connected to device");
    if (throttle) await sleep(WRITE_THROTTLE_MS);
    const buf = new Uint8Array(commandData.length);
    for (let i = 0; i < commandData.length; i++) buf[i] = commandData[i] & 0xFF;
    await this.commandCharacteristic.writeValue(buf);
  }

  // Animation per-frame write. Mirrors the official's recursive
  // writeBLECharacteristicValue: up to ANIM_MAX_RETRIES, ANIM_RETRY_BACKOFF_MS
  // between failures, no pre-guard.
  async _writeFrameWithRetry(commandData) {
    for (let attempt = 0; attempt < ANIM_MAX_RETRIES; attempt++) {
      try {
        await this._write(commandData, { throttle: false });
        return;
      } catch (err) {
        if (attempt === ANIM_MAX_RETRIES - 1) throw err;
        await sleep(ANIM_RETRY_BACKOFF_MS);
      }
    }
  }

  // Public: write a command and wait up to `timeout` ms for a notification.
  // Used for commands the official's receive parser handles (mode echo,
  // reads, etc.). Acquires the mutex.
  async executeCommand(commandData, timeout = 5000) {
    if (!this.server) throw new Error("Not connected to device");
    const unlock = await this._mutex.acquire();
    try {
      return await this._executeLocked(commandData, timeout);
    } finally {
      unlock();
    }
  }

  async _executeLocked(commandData, timeout) {
    const value = await new Promise((resolve, reject) => {
      this.pendingResponse = { resolve, reject };
      this.responseTimeout = setTimeout(() => {
        this.responseTimeout = null;
        this.pendingResponse = null;
        reject(new Error("Device response timeout"));
      }, timeout);
      this._write(commandData).catch((error) => {
        if (this.responseTimeout) {
          clearTimeout(this.responseTimeout);
          this.responseTimeout = null;
        }
        this.pendingResponse = null;
        reject(error);
      });
    });

    const arr = new Uint8Array(value.buffer);
    if (arr.length >= 3 && arr[0] === 0xFF && arr[arr.length - 2] === 0x0D && arr[arr.length - 1] === 0x0A) {
      return arr.slice(2, arr.length - 2);
    }
    return arr;
  }

  // Read firmware version. Returns a string "major.minor" (e.g. "1.6") —
  // the cup returns 4 payload bytes after the feature byte; the official
  // parser at app-service.pretty.js:53402 uses the last two for major.minor.
  async readVersion() {
    const resp = await this.executeCommand([0xFF, 0x55, 0x07, 0x00, 0x01, 0x09, 0x00]);
    if (resp.length >= 2) {
      return `${resp[resp.length - 2]}.${resp[resp.length - 1]}`;
    }
    return Array.from(resp).join('.');
  }

  // Read current liquid temperature in °C (last payload byte, unsigned).
  async readTemperature() {
    const resp = await this.executeCommand([0xFF, 0x55, 0x07, 0x00, 0x01, 0x01, 0x00]);
    return resp[resp.length - 1];
  }

  // Read battery level (percent, 0..100).
  async readBattery() {
    const resp = await this.executeCommand([0xFF, 0x55, 0x07, 0x00, 0x01, 0x02, 0x00]);
    return resp[resp.length - 1];
  }

  /**
   * Set the cup's auto-screen-off feature flag.
   *
   * Frame: FF 55 07 00 02 27 <byte>. Empirically (probed against
   * SGUAI-C3 fw 1.6) this byte is a *boolean*, not a seconds counter
   * as the protocol spec originally implied: any non-zero value reads
   * back as 1, only 0 reads back as 0.
   *
   *   setAutoOff(0)  → auto-off disabled (display stays alive)
   *   setAutoOff(1)  → auto-off enabled (firmware default)
   *
   * Side effect: with the flag disabled, the cup may stop appearing
   * in fresh BLE scans while it's actively driving the panel
   * (PROTOCOL_SPEC.md §4.7).
   */
  async setAutoOff(value) {
    if (!this.server) throw new Error("Not connected to device");
    if (!Number.isInteger(value) || value < 0 || value > 255) {
      throw new Error("value must fit in one byte (0..255)");
    }
    const command = [0xFF, 0x55, 0x07, 0x00, 0x02, 0x27, value];
    const unlock = await this._mutex.acquire();
    try {
      try {
        await this._executeLocked(command, 10000);
      } catch (err) {
        // Like setDynamicMode, the cup occasionally drops the echo for
        // a config write. The BLE-layer ACK is enough.
        if (err.message !== "Device response timeout") throw err;
      }
      return true;
    } finally {
      unlock();
    }
  }

  // Read the auto-screen-off flag (0 = disabled, 1 = enabled).
  async readAutoOff() {
    const resp = await this.executeCommand([0xFF, 0x55, 0x07, 0x00, 0x01, 0x27, 0x00]);
    return resp[resp.length - 1];
  }

  /**
   * Set greeting text. Empty string clears the display.
   *
   * Matches the official page-level path (sub-service.pretty.js:4083-88):
   * direct write — no 20 ms guard, no notification wait (the receive parser
   * has no 0x17 handler). Encoding is UTF-16 big-endian, matching the
   * official's `charCodeAt` iteration including surrogate pairs.
   */
  async setGreetingMessage(message) {
    if (!this.server) throw new Error("Not connected to device");
    // Coerce explicitly so falsy non-strings like 0 / false are rendered
    // as their string form rather than silently clearing the display.
    const text = message == null ? "" : String(message);
    const subcmd = text.length ? 0x01 : 0x00;
    const command = [0xFF, 0x55, 0x00, 0x00, 0x02, 0x17, subcmd, ...utf16beBytes(text)];
    command[2] = command.length;
    const unlock = await this._mutex.acquire();
    try {
      await this._write(command, { throttle: false });
      return true;
    } finally {
      unlock();
    }
  }

  // Set display motion: static / scrollRight / scrollLeft / flashing.
  async setDynamicMode(mode) {
    if (!this.server) throw new Error("Not connected to device");
    const modeMap = { static: 0, scrollRight: 1, scrollLeft: 2, flashing: 3 };
    const modeValue = modeMap[mode];
    if (modeValue === undefined) throw new Error(`Invalid mode: ${mode}`);
    const command = [0xFF, 0x55, 0x07, 0x00, 0x02, 0x23, modeValue];
    const unlock = await this._mutex.acquire();
    try {
      try {
        await this._executeLocked(command, 10000);
      } catch (err) {
        // Cup occasionally drops the echo notification; the write itself
        // was ACKed at the BLE layer so the mode is set. Match exactly the
        // message we throw ourselves inside _executeLocked, not any error
        // that happens to contain the word "timeout".
        if (err.message !== "Device response timeout") throw err;
      }
      return true;
    } finally {
      unlock();
    }
  }

  /**
   * Upload a static image. Sends FF 55 4E 00 02 25 + 72-byte bitmap.
   * Fire-and-forget — the receive parser has no 0x25 handler. Goes through
   * the same GET_BLE_WRITE path as every other state-changing command, so
   * we apply the 20 ms pre-guard.
   */
  async setImageData(imageData) {
    if (!this.server) throw new Error("Not connected to device");
    const payload = packBitmap(imageData);
    const command = [0xFF, 0x55, 0x00, 0x00, 0x02, 0x25, ...payload];
    command[2] = command.length;  // 0x4E (78)
    const unlock = await this._mutex.acquire();
    try {
      await this._write(command);
      return true;
    } finally {
      unlock();
    }
  }

  /**
   * Upload an animation. The cup stores the frames and plays them
   * autonomously after upload completes — no BLE traffic during playback.
   *
   * Wire protocol (matches official app):
   *   Prologue: FF 55 08 00 02 26 <count> <speed>
   *   Frame N : FF 55 50 00 02 26 <idx>   <speed> <72-byte bitmap>
   *
   * Timing matches the official app: 20 ms pre-guard on the prologue,
   * 100 ms post-prologue, 150 ms between successful frames, 10× retry
   * with 100 ms backoff on per-frame failure.
   *
   * @param {Array<Array<Array<number>>>} frames  Array of 12×48 grids.
   *     Each frame is pre-validated *before* the prologue is sent so a
   *     bad frame can't leave the cup half-loaded.
   * @param {number} speed  1..255, larger = faster. 0 produces unspecified
   *     behavior on the cup. Default 130 matches the official app's
   *     `speedValue` and produces ~1 second per 4-frame cycle (exact unit
   *     not yet quantified — see PROTOCOL_SPEC.md §4.6).
   * @param {Object} [opts]
   * @param {boolean} [opts.keepAlive=true]  When true (default), disables
   *     the cup's auto-screen-off before uploading frames so the loop
   *     plays continuously after disconnect. Set false to preserve the
   *     existing auto-off setting (firmware default = enabled).
   */
  async setAnimation(frames, speed = 130, opts = {}) {
    if (!this.server) throw new Error("Not connected to device");
    if (!Array.isArray(frames) || frames.length === 0) {
      throw new Error("frames must be a non-empty array");
    }
    if (frames.length > 255) throw new Error("Max 255 frames");
    if (!Number.isInteger(speed)) throw new Error("speed must be an integer");
    if (speed < 1 || speed > 255) throw new Error("speed must be 1..255 (0 is unspecified by firmware)");

    const keepAlive = opts.keepAlive !== false;

    // Pre-pack every frame BEFORE acquiring the mutex / sending the prologue.
    // If any frame has the wrong shape, we throw upfront with frame-index
    // context, leaving the cup's state untouched. Without this, a bad frame
    // mid-upload would leave the cup expecting more data than will arrive.
    const payloads = frames.map((f, idx) => {
      try { return packBitmap(f); }
      catch (err) { throw new Error(`frame ${idx}: ${err.message}`); }
    });

    // Keep-alive runs OUTSIDE the per-upload mutex acquisition because
    // setAutoOff already takes the mutex itself; nesting would deadlock.
    // A failure here is non-fatal — the animation can still upload, it
    // just may sleep mid-playback.
    if (keepAlive) {
      try {
        await this.setAutoOff(0);
      } catch (err) {
        console.warn(`Could not disable auto-off (${err.message}); animation may sleep mid-loop`);
      }
    }

    const unlock = await this._mutex.acquire();
    try {
      const n = frames.length;
      await this._write([0xFF, 0x55, 0x08, 0x00, 0x02, 0x26, n, speed]);
      await sleep(ANIM_PROLOGUE_DELAY_MS);

      for (let idx = 0; idx < n; idx++) {
        const cmd = [0xFF, 0x55, 0x00, 0x00, 0x02, 0x26, idx, speed, ...payloads[idx]];
        cmd[2] = cmd.length;  // 0x50 (80)
        await this._writeFrameWithRetry(cmd);
        if (idx < n - 1) await sleep(ANIM_FRAME_DELAY_MS);
      }
      return true;
    } finally {
      unlock();
    }
  }

  async verifyDeviceName() {
    if (!this.server) {
      throw new Error("Not connected to device");
    }

    try {
      const genericAccessService = await this.server.getPrimaryService(
        "generic_access"
      );
      const deviceNameCharacteristic =
        await genericAccessService.getCharacteristic("gap.device_name");
      const deviceNameValue = await deviceNameCharacteristic.readValue();

      const decoder = new TextDecoder("utf-8");
      const deviceName = decoder.decode(deviceNameValue).trim();

      if (deviceName !== "SGUAI-C3") {
        this.disconnect();
        throw new Error(
          `Invalid device name: "${deviceName}". Expected: "SGUAI-C3". Device disconnected.`
        );
      }
      // If we reach here, the device name was verified successfully
      return true;
    } catch (error) {
      // If the error is about device name, re-throw it
      if (error.message.includes("Invalid device name")) {
        throw error;
      }
      // Generic Access service not available - that's OK
      // We'll rely on the user selecting the correct device
      return true;
    }
  }

  async readDeviceName() {
    if (!this.server) {
      throw new Error("Not connected to device");
    }

    try {
      console.log("Reading device name...");
      const service = await this.server.getPrimaryService("device_information");
      const characteristic = await service.getCharacteristic(
        "00002A24-0000-1000-8000-00805F9B34FB"
      ); // Model Number String
      const value = await characteristic.readValue();

      // Convert DataView to string
      const decoder = new TextDecoder("utf-8");
      return decoder.decode(value);
    } catch (error) {
      throw new Error(`Failed to read device name: ${error.message}`);
    }
  }

  async readFirmwareVersion() {
    if (!this.server) {
      throw new Error("Not connected to device");
    }

    try {
      console.log("Reading firmware version...");
      const service = await this.server.getPrimaryService("device_information");
      const characteristic = await service.getCharacteristic(
        "00002A26-0000-1000-8000-00805F9B34FB"
      ); // Firmware Revision String
      const value = await characteristic.readValue();

      // Convert DataView to string
      const decoder = new TextDecoder("utf-8");
      return decoder.decode(value);
    } catch (error) {
      throw new Error(`Failed to read firmware version: ${error.message}`);
    }
  }

  async detectMacFromAdvertisement() {
    if (!this.device) return null;

    if (!this.device.watchAdvertisements) {
      console.warn("Web Bluetooth watchAdvertisements() API is not available in this browser.");
      return null;
    }

    console.log("Scanning for MAC address in advertisements...");
    const abortController = new AbortController();
    const { signal } = abortController;

    return new Promise((resolve) => {
      const handleAd = (event) => {
        if (event.manufacturerData) {
          event.manufacturerData.forEach((value, key) => {
            // Check if value is 6 bytes (MAC address length)
            if (value.byteLength === 6) {
              const arr = new Uint8Array(value.buffer);
              const mac = Array.from(arr)
                .map(b => b.toString(16).padStart(2, '0').toUpperCase())
                .join(':');
              console.log(`Found potential MAC in Manufacturer Data (Key: ${key}):`, mac);
              abortController.abort();
              resolve(mac);
            }
          });
        }
      };

      this.device.addEventListener('advertisementreceived', handleAd, { signal });

      this.device.watchAdvertisements()
        .catch(error => {
          console.warn("watchAdvertisements error:", error);
          resolve(null);
        });

      // Timeout after 2 seconds
      setTimeout(() => {
        abortController.abort();
        resolve(null);
      }, 2000);
    });
  }


  async readDeviceIdentifiers() {
    if (!this.server) return null;

    try {
      const service = await this.server.getPrimaryService("device_information");

      // Try Serial Number (0x2A25)
      try {
        const char = await service.getCharacteristic("00002A25-0000-1000-8000-00805F9B34FB");
        const value = await char.readValue();
        const decoder = new TextDecoder("utf-8");
        const serial = decoder.decode(value);
        console.log("Read Serial Number:", serial);
        return { type: 'Serial Number', value: serial };
      } catch (e) { /* Ignore */ }

      // Try System ID (0x2A23)
      try {
        const char = await service.getCharacteristic("00002A23-0000-1000-8000-00805F9B34FB");
        const value = await char.readValue();
        const arr = new Uint8Array(value.buffer);
        const hex = Array.from(arr).map(b => b.toString(16).padStart(2, '0').toUpperCase()).join(':');
        console.log("Read System ID:", hex);
        return { type: 'System ID', value: hex };
      } catch (e) { /* Ignore */ }

    } catch (e) {
      // Device Information service not available - that's OK
    }
    return null;
  }

  async scanAllCharacteristics() {
    if (!this.server) return null;

    try {
      const services = await this.server.getPrimaryServices();

      for (const service of services) {
        try {
          const characteristics = await service.getCharacteristics();

          for (const char of characteristics) {
            try {
              const value = await char.readValue();
              const arr = new Uint8Array(value.buffer);

              // Check if it's 6 bytes (MAC address length)
              if (arr.length === 6) {
                const mac = Array.from(arr)
                  .map(b => b.toString(16).padStart(2, '0').toUpperCase())
                  .join(':');
                console.log(`Found potential MAC address: ${mac}`);
                return { type: 'MAC Address', value: mac };
              }
            } catch (e) {
              // Can't read this characteristic
            }
          }
        } catch (e) {
          // Can't enumerate characteristics for this service
        }
      }
    } catch (e) {
      // Can't enumerate services
    }

    return null;
  }
}

// Export as singleton
window.bleManager = new BLEManager();
