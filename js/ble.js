// ble.js - BLE connection and communication stubs

// Service and characteristic UUIDs
const SERVICE_UUID = "0000ff00-0000-1000-8000-00805f9b34fb"; // Custom service UUID
const COMMAND_CHAR_UUID = "0000ff01-0000-1000-8000-00805f9b34fb"; // Command characteristic
const RESPONSE_CHAR_UUID = "0000ff02-0000-1000-8000-00805f9b34fb"; // Response characteristic (notifications)

// Image dimensions
const IMAGE_WIDTH = 48;
const IMAGE_HEIGHT = 12;

class BLEManager {
  constructor() {
    this.device = null;
    this.server = null;
    this.service = null;
    this.commandCharacteristic = null;
    this.responseCharacteristic = null;
    this.pendingResponse = null;
    this.responseTimeout = null;
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

  // Execute a command and return the response
  async executeCommand(commandData, timeout = 5000) {
    if (!this.server) {
      throw new Error("Not connected to device");
    }

    let command = new ArrayBuffer(commandData.length);
    let view = new DataView(command);
    for (let i in commandData) {
        view.setUint8(i, commandData[i]);
    }

    console.log('execute command: ', commandData);

    let value = await new Promise((resolve, reject) => {
      // Set up pending response
      this.pendingResponse = { resolve, reject };

      // Set timeout
      this.responseTimeout = setTimeout(() => {
        this.responseTimeout = null;
        this.pendingResponse = null;
        reject(new Error("Device response timeout"));
      }, timeout);

      // Send command
      this.sendCommandInternal(command).catch((error) => {
        if (this.responseTimeout) {
          clearTimeout(this.responseTimeout);
          this.responseTimeout = null;
        }
        this.pendingResponse = null;
        reject(error);
      });
    });

    let arr = new Uint8Array(value.buffer);
    console.log('response: ', arr);
    if ((arr.length >= 3) && (arr[0] == 0xff)
        && (arr[arr.length - 2] == 0x0d) && (arr[arr.length - 1] == 0x0A)) {
        let part = arr.slice(2, arr.length - 2);
        return part;
    } else {
        return arr;
    }
  }

  // Internal method to send command to the device
  async sendCommandInternal(commandData) {
    if (!this.server) {
      throw new Error("Not connected to device");
    }

    if (!this.commandCharacteristic) {
      throw new Error("Command characteristic not available");
    }

    try {
      console.log("Sending command:", commandData);
      await this.commandCharacteristic.writeValue(commandData);
      return true;
    } catch (error) {
      throw new Error(`Failed to send command: ${error.message}`);
    }
  }

  // Read version information
  async readVersion() {
    if (!this.server) {
      throw new Error("Not connected to device");
    }

    try {
      const ver_info = await this.executeCommand([
        0xff, 0x55, 0x07, 0x00, 0x01, 0x09, 0x00,
      ]);
      const version = [...ver_info];
      return `${version}`;
    } catch (error) {
      throw new Error(`Failed to read version: ${error.message}`);
    }
  }

  // Read temperature
  async readTemperature() {
    if (!this.server) {
      throw new Error("Not connected to device");
    }

    try {
      // Create temperature request command (this would depend on your protocol)
      const response = await this.executeCommand(["0xFF", "0x55", "0x07", "0x0", "0x1", "0x1", "0x0"]);
      console.log("temperature: ", [...response]);
      const temperature = response[response.length - 1];
      return temperature;
    } catch (error) {
      throw new Error(`Failed to read temperature: ${error.message}`);
    }
  }

  // Set greeting message
  async setGreetingMessage(message) {
    if (!this.server) {
      throw new Error("Not connected to device");
    }

    let command = [0xFF, 0x55, 0x00, 0x00, 0x02, 0x17, 0x01];
    for (let i in message) {
        let cp = message.codePointAt(i);
        command.push(cp >> 8);
        command.push(cp & 0xff);
    }

    command[2] = command.length;

    try {
      let rsp = await this.executeCommand(command);
      console.log("setGreetingMessage: ", rsp);
      return true;
    } catch (error) {
      throw new Error(`Failed to set greeting message: ${error.message}`);
    }
  }

  // Set dynamic mode
  async setDynamicMode(mode) {
    if (!this.server) {
      throw new Error("Not connected to device");
    }

    // Map mode strings to numeric values
    const modeMap = {
      static: 0,
      scrollRight: 1,
      scrollLeft: 2,
      flashing: 3,
    };

    const modeValue = modeMap[mode];
    if (modeValue === undefined) {
      throw new Error(`Invalid mode: ${mode}`);
    }

    try {
      let rsp = await this.executeCommand(["0xFF", "0x55", "0x7", "0x0", "0x2", "0x23", modeValue]);
      console.log("setDynamicMode: ", rsp);
      return true;
    } catch (error) {
      throw new Error(`Failed to set dynamic mode: ${error.message}`);
    }
  }

  // Set image data
  async setImageData(imageData) {
    if (!this.server) {
      throw new Error("Not connected to device");
    }

    try {
      // Convert 2D array to bit-packed Uint8Array
      // imageData is a 12x48 array where 0 = white, 1 = black
      // Each bit represents 1 pixel, so 576 pixels = 72 bytes
      // Within each byte: highest bit (bit 7) = leftmost pixel, lowest bit (bit 0) = rightmost pixel
      const totalPixels = IMAGE_HEIGHT * IMAGE_WIDTH;
      const totalBytes = Math.ceil(totalPixels / 8);
      const flatData = new Uint8Array(120);

      let bitIndex = 0;
      for (let row = 0; row < IMAGE_HEIGHT; row++) {
        for (let col = 0; col < IMAGE_WIDTH; col++) {
          const byteIndex = Math.floor(bitIndex / 8);
          const bitPosition = 7 - (bitIndex % 8); // Reverse: bit 7 = leftmost, bit 0 = rightmost

          if (imageData[row][col] === 1) {
            // Set the bit at the current position
            flatData[byteIndex] |= (1 << bitPosition);
          }

          bitIndex++;
        }
      }

      const command = [0xFF, 0x55, 0x00, 0x00, 0x02, 0x25, ...flatData];
      command[2] = command.length; // Update length byte
      await this.executeCommand(command);
      return true;
    } catch (error) {
      throw new Error(`Failed to set image data: ${error.message}`);
    }
  }

  async verifyDeviceName() {
    try {
      console.log("Verifying device name...");

      // Get Generic Access service
      const genericAccessService = await this.server.getPrimaryService(
        "generic_access"
      );

      // Get Device Name characteristic
      const deviceNameCharacteristic =
        await genericAccessService.getCharacteristic("gap.device_name");

      // Read the device name
      const deviceNameValue = await deviceNameCharacteristic.readValue();

      // Convert DataView to string
      const decoder = new TextDecoder("utf-8");
      const deviceName = decoder.decode(deviceNameValue).trim();

      console.log(`Device name: "${deviceName}"`);

      // Verify the device name
      if (deviceName !== "SGUAI-C3") {
        // Disconnect and clean up before throwing error
        this.disconnect();
        throw new Error(
          `Invalid device name: "${deviceName}". Expected: "SGUAI-C3". Device disconnected.`
        );
      }

      console.log("Device name verified successfully");
      return true;
    } catch (error) {
      // If the error is about device name, re-throw it
      if (error.message.includes("Invalid device name")) {
        throw error;
      }

      // If we can't read the device name, warn but continue
      console.warn(
        `Could not verify device name via Generic Access service: ${error.message}`
      );
      console.warn(
        "Proceeding with connection - please ensure this is an SGUAI-C3 device"
      );
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
}

// Export as singleton
window.bleManager = new BLEManager();
