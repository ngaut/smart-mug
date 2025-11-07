// multiCupBLE.js - Multi-cup BLE connection manager

// Cup positions in display grid
// Default 2x2 layout:
// [0] [1]
// [2] [3]

class MultiCupBLEManager {
  constructor() {
    // Store individual BLE managers for each cup
    this.cups = {
      0: { manager: null, connected: false, position: 'top-left', deviceId: null, deviceName: null, reconnectAttempts: 0, autoReconnect: false },
      1: { manager: null, connected: false, position: 'top-right', deviceId: null, deviceName: null, reconnectAttempts: 0, autoReconnect: false },
      2: { manager: null, connected: false, position: 'bottom-left', deviceId: null, deviceName: null, reconnectAttempts: 0, autoReconnect: false },
      3: { manager: null, connected: false, position: 'bottom-right', deviceId: null, deviceName: null, reconnectAttempts: 0, autoReconnect: false }
    };

    // Display layout configuration
    this.layout = 'grid_2x2'; // Options: 'grid_2x2', 'horizontal_1x4', 'vertical_4x1'

    // Statistics
    this.stats = {
      lastSendTime: null,
      totalFramesSent: 0,
      averageSendTime: 0
    };

    // Connection monitoring
    this.monitoringInterval = null;
    this.monitoringEnabled = false;
    this.MONITOR_INTERVAL_MS = 30000; // Check every 30 seconds
    this.MAX_RECONNECT_ATTEMPTS = 3;
  }

  /**
   * Get layout dimensions
   */
  getLayoutDimensions() {
    switch (this.layout) {
      case 'grid_2x2':
        return { width: 96, height: 24, rows: 2, cols: 2 };
      case 'horizontal_1x4':
        return { width: 192, height: 12, rows: 1, cols: 4 };
      case 'vertical_4x1':
        return { width: 48, height: 48, rows: 4, cols: 1 };
      default:
        return { width: 96, height: 24, rows: 2, cols: 2 };
    }
  }

  /**
   * Set display layout
   */
  setLayout(layout) {
    if (['grid_2x2', 'horizontal_1x4', 'vertical_4x1'].includes(layout)) {
      this.layout = layout;
      console.log(`Layout changed to: ${layout}`);
      return true;
    }
    return false;
  }

  /**
   * Connect to a specific cup at position
   */
  async connectCup(position) {
    if (position < 0 || position > 3) {
      throw new Error(`Invalid position: ${position}. Must be 0-3.`);
    }

    // Check if already connected
    if (this.cups[position].connected) {
      throw new Error(`Cup at position ${position} is already connected`);
    }

    try {
      console.log(`Connecting cup at position ${position}...`);

      // Create new BLEManager instance for this cup
      const manager = new BLEManager();

      // Request and connect to device
      await manager.requestDevice();
      await manager.connect();

      // Check for duplicate device IDs
      const newDeviceId = manager.device.id;
      for (let i = 0; i < 4; i++) {
        if (i !== position && this.cups[i].connected && this.cups[i].deviceId === newDeviceId) {
          // Duplicate detected! Disconnect and throw error
          manager.disconnect();
          throw new Error(`This device is already connected to Cup ${i}! Each cup position needs a different physical device.`);
        }
      }

      // Store the manager and device info
      this.cups[position].manager = manager;
      this.cups[position].connected = true;
      this.cups[position].deviceId = newDeviceId;
      this.cups[position].deviceName = manager.device.name;
      this.cups[position].reconnectAttempts = 0;
      this.cups[position].autoReconnect = true; // Enable auto-reconnect for this cup

      // Set up disconnection handler
      if (manager.device) {
        manager.device.addEventListener('gattserverdisconnected', () => {
          this.handleCupDisconnection(position);
        });
      }

      // Start connection monitoring if not already running
      this.startConnectionMonitoring();

      // Convert device ID to hex for display
      let deviceIdHex = newDeviceId;
      try {
        const binaryString = atob(newDeviceId);
        const hexArray = [];
        for (let i = 0; i < binaryString.length; i++) {
          hexArray.push(binaryString.charCodeAt(i).toString(16).padStart(2, '0'));
        }
        deviceIdHex = hexArray.join(':').toUpperCase();
      } catch (e) {
        deviceIdHex = newDeviceId;
      }

      console.log(`✅ Cup ${position} connected successfully: ${manager.device.name} (${deviceIdHex})`);
      return true;
    } catch (error) {
      console.error(`Failed to connect cup ${position}:`, error);
      this.cups[position].manager = null;
      this.cups[position].connected = false;
      throw error;
    }
  }

  /**
   * Disconnect a specific cup
   */
  disconnectCup(position) {
    if (position < 0 || position > 3) {
      return;
    }

    const cup = this.cups[position];
    if (cup.connected && cup.manager) {
      console.log(`Disconnecting cup ${position}...`);
      cup.manager.disconnect();
    }

    // Clear cup state
    cup.manager = null;
    cup.connected = false;
    cup.deviceId = null;
    cup.deviceName = null;
    cup.autoReconnect = false; // Disable auto-reconnect for manual disconnects
    cup.reconnectAttempts = 0;

    // Stop monitoring if no cups are connected
    if (!this.hasAnyConnected()) {
      this.stopConnectionMonitoring();
    }
  }

  /**
   * Disconnect all cups
   */
  disconnectAll() {
    console.log('Disconnecting all cups...');
    for (let i = 0; i < 4; i++) {
      this.disconnectCup(i);
    }
  }

  /**
   * Handle cup disconnection
   */
  handleCupDisconnection(position) {
    console.warn(`⚠️ Cup ${position} disconnected unexpectedly`);

    const cup = this.cups[position];
    const shouldAutoReconnect = cup.autoReconnect;
    const deviceToReconnect = cup.manager?.device; // Keep reference to device

    // Update connection state
    cup.connected = false;
    // Note: Don't clear manager/deviceId yet - needed for reconnection

    // Notify UI of disconnection
    if (window.onMultiCupDisconnect) {
      window.onMultiCupDisconnect(position);
    }

    // Attempt automatic reconnection if enabled
    if (shouldAutoReconnect && deviceToReconnect) {
      this.attemptReconnection(position, deviceToReconnect);
    } else {
      // Clear state if not reconnecting
      cup.manager = null;
      cup.deviceId = null;
      cup.deviceName = null;
    }
  }

  /**
   * Get connection status
   */
  getConnectionStatus() {
    const status = {
      total: 4,
      connected: 0,
      disconnected: 0,
      positions: {}
    };

    for (let i = 0; i < 4; i++) {
      status.positions[i] = this.cups[i].connected;
      if (this.cups[i].connected) {
        status.connected++;
      } else {
        status.disconnected++;
      }
    }

    return status;
  }

  /**
   * Check if all cups are connected
   */
  areAllConnected() {
    return Object.values(this.cups).every(cup => cup.connected);
  }

  /**
   * Check if any cups are connected
   */
  hasAnyConnected() {
    return Object.values(this.cups).some(cup => cup.connected);
  }

  /**
   * Send image data to specific cup
   */
  async sendToCup(position, imageData) {
    if (position < 0 || position > 3) {
      throw new Error(`Invalid position: ${position}`);
    }

    const cup = this.cups[position];
    if (!cup.connected || !cup.manager) {
      throw new Error(`Cup ${position} is not connected`);
    }

    const startTime = Date.now();

    try {
      await cup.manager.setImageData(imageData);
      const elapsed = Date.now() - startTime;
      console.log(`✅ Cup ${position}: Sent in ${(elapsed / 1000).toFixed(1)}s`);
      return { success: true, elapsed, position };
    } catch (error) {
      console.error(`❌ Cup ${position}: Failed -`, error.message);
      throw error;
    }
  }

  /**
   * Send image chunks to all connected cups in parallel
   * @param {Array<Array<Array<number>>>} imageChunks - Array of 4 image grids (12x48 each)
   * @param {Object} options - Send options
   */
  async sendToAll(imageChunks, options = {}) {
    const { silent = false } = options;

    if (!Array.isArray(imageChunks) || imageChunks.length !== 4) {
      throw new Error('imageChunks must be an array of 4 image grids');
    }

    const status = this.getConnectionStatus();
    if (status.connected === 0) {
      throw new Error('No cups connected');
    }

    const startTime = Date.now();
    const promises = [];
    const results = [];

    if (!silent) {
      console.log(`\n🎬 Sending to ${status.connected} cups in parallel...`);
    }

    // Send to all connected cups in parallel
    for (let i = 0; i < 4; i++) {
      if (this.cups[i].connected) {
        const promise = this.sendToCup(i, imageChunks[i])
          .then(result => {
            results.push(result);
            return result;
          })
          .catch(error => {
            results.push({ success: false, position: i, error: error.message });
            return { success: false, position: i, error: error.message };
          });
        promises.push(promise);
      }
    }

    // Wait for all sends to complete
    await Promise.all(promises);

    const totalElapsed = Date.now() - startTime;
    const successful = results.filter(r => r.success).length;
    const failed = results.filter(r => !r.success).length;

    // Update statistics
    this.stats.lastSendTime = totalElapsed;
    this.stats.totalFramesSent += successful;

    if (!silent) {
      console.log(`\n📊 MULTI-CUP SEND COMPLETE:`);
      console.log(`   Total time: ${(totalElapsed / 1000).toFixed(1)}s`);
      console.log(`   Successful: ${successful}/${status.connected}`);
      if (failed > 0) {
        console.log(`   Failed: ${failed}`);
      }

      // Show individual cup times
      const successfulResults = results.filter(r => r.success);
      if (successfulResults.length > 0) {
        const times = successfulResults.map(r => r.elapsed);
        const avgTime = times.reduce((a, b) => a + b, 0) / times.length;
        const maxTime = Math.max(...times);
        const minTime = Math.min(...times);
        console.log(`   Average per cup: ${(avgTime / 1000).toFixed(1)}s`);
        console.log(`   Fastest: ${(minTime / 1000).toFixed(1)}s`);
        console.log(`   Slowest: ${(maxTime / 1000).toFixed(1)}s`);
      }
    }

    return {
      success: failed === 0,
      totalElapsed,
      results,
      successful,
      failed
    };
  }

  /**
   * Read version from specific cup
   */
  async readVersion(position) {
    const cup = this.cups[position];
    if (!cup.connected || !cup.manager) {
      throw new Error(`Cup ${position} is not connected`);
    }
    return await cup.manager.readVersion();
  }

  /**
   * Read temperature from specific cup
   */
  async readTemperature(position) {
    const cup = this.cups[position];
    if (!cup.connected || !cup.manager) {
      throw new Error(`Cup ${position} is not connected`);
    }
    return await cup.manager.readTemperature();
  }

  /**
   * Set greeting message on specific cup
   */
  async setGreetingMessage(position, message) {
    const cup = this.cups[position];
    if (!cup.connected || !cup.manager) {
      throw new Error(`Cup ${position} is not connected`);
    }
    return await cup.manager.setGreetingMessage(message);
  }

  /**
   * Set dynamic mode on specific cup
   */
  async setDynamicMode(position, mode) {
    const cup = this.cups[position];
    if (!cup.connected || !cup.manager) {
      throw new Error(`Cup ${position} is not connected`);
    }
    return await cup.manager.setDynamicMode(mode);
  }

  /**
   * Set dynamic mode on all connected cups
   */
  async setDynamicModeAll(mode) {
    const promises = [];
    for (let i = 0; i < 4; i++) {
      if (this.cups[i].connected) {
        promises.push(this.setDynamicMode(i, mode).catch(error => {
          console.error(`Failed to set mode on cup ${i}:`, error);
        }));
      }
    }
    await Promise.all(promises);
  }

  /**
   * Attempt to reconnect a disconnected cup
   */
  async attemptReconnection(position, device) {
    const cup = this.cups[position];

    // Check reconnection attempts
    if (cup.reconnectAttempts >= this.MAX_RECONNECT_ATTEMPTS) {
      console.warn(`❌ Cup ${position}: Max reconnection attempts (${this.MAX_RECONNECT_ATTEMPTS}) reached. Giving up.`);
      cup.autoReconnect = false;
      cup.manager = null;
      cup.deviceId = null;
      cup.deviceName = null;
      return;
    }

    cup.reconnectAttempts++;
    const delay = Math.min(2000 * cup.reconnectAttempts, 10000); // Exponential backoff, max 10s

    console.log(`🔄 Cup ${position}: Attempting reconnection (${cup.reconnectAttempts}/${this.MAX_RECONNECT_ATTEMPTS}) in ${delay}ms...`);

    // Wait before attempting reconnection
    await new Promise(resolve => setTimeout(resolve, delay));

    try {
      // Attempt to reconnect to the same device
      if (device.gatt) {
        console.log(`🔄 Cup ${position}: Connecting to GATT server...`);
        await device.gatt.connect();

        // Reconnect the manager
        await cup.manager.connect();

        // Success!
        cup.connected = true;
        cup.reconnectAttempts = 0;
        console.log(`✅ Cup ${position}: Reconnected successfully!`);

        // Notify UI of reconnection
        if (window.onMultiCupReconnect) {
          window.onMultiCupReconnect(position);
        }
      }
    } catch (error) {
      console.error(`❌ Cup ${position}: Reconnection failed:`, error.message);

      // Try again if we haven't hit max attempts
      if (cup.reconnectAttempts < this.MAX_RECONNECT_ATTEMPTS) {
        this.attemptReconnection(position, device);
      } else {
        console.warn(`❌ Cup ${position}: Max reconnection attempts reached. Please reconnect manually.`);
        cup.autoReconnect = false;
        cup.manager = null;
        cup.deviceId = null;
        cup.deviceName = null;
      }
    }
  }

  /**
   * Start connection monitoring
   */
  startConnectionMonitoring() {
    if (this.monitoringEnabled) {
      return; // Already monitoring
    }

    console.log('🔍 Starting connection monitoring...');
    this.monitoringEnabled = true;

    this.monitoringInterval = setInterval(() => {
      this.checkConnectionHealth();
    }, this.MONITOR_INTERVAL_MS);
  }

  /**
   * Stop connection monitoring
   */
  stopConnectionMonitoring() {
    if (!this.monitoringEnabled) {
      return;
    }

    console.log('🛑 Stopping connection monitoring');
    this.monitoringEnabled = false;

    if (this.monitoringInterval) {
      clearInterval(this.monitoringInterval);
      this.monitoringInterval = null;
    }
  }

  /**
   * Check connection health by reading version (keepalive)
   */
  async checkConnectionHealth() {
    for (let i = 0; i < 4; i++) {
      const cup = this.cups[i];

      if (cup.connected && cup.manager) {
        try {
          // Send a simple read command to keep connection alive
          await cup.manager.readVersion();
          // Success - connection is healthy
        } catch (error) {
          // Connection failed - it may have disconnected
          console.warn(`⚠️ Cup ${i}: Health check failed. Connection may be lost.`);
        }
      }
    }
  }
}

// Export as singleton
window.multiCupBLE = new MultiCupBLEManager();
