// main.js - Main application logic

// Global variables
let isConnected = false;
let isDemoMode = false;
let currentTool = 'draw';
let isBluetoothSupported = navigator.bluetooth !== undefined;

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
  // Check if Web Bluetooth is supported
  if (!isBluetoothSupported) {
    // Update UI to inform user about limited functionality
    document.getElementById('connectButton').disabled = true;
    updateDeviceStatus('Web Bluetooth is not supported in this browser. Please use Chrome or Edge.', true);
  }

  // Check if user was previously on Multi-Cup Display (auto-restore)
  const lastPanel = localStorage.getItem('smartmug_last_panel');
  if (lastPanel === 'multiCup') {
    // Auto-skip connection and go directly to Multi-Cup Display
    console.log("Restoring Multi-Cup Display panel...");
    document.getElementById('connectionPanel').classList.add('hidden');
    document.getElementById('mainContent').classList.remove('hidden');

    // Restore Multi-Cup panel
    setTimeout(() => {
      showMultiCupFunction();
    }, 100);
  }


  // Set up event listeners
  document.getElementById('connectButton').addEventListener('click', connectToDevice);
  document.getElementById('skipButton').addEventListener('click', skipConnection);
  document.getElementById('sidebarConnectBtn').addEventListener('click', () => {
    if (isConnected) {
      // If connected, disconnect
      connectToDevice();
    } else {
      // If not connected, show the connection panel
      showConnectionPanel();
      // Also reset the auto-restore flag so we don't just jump back
      localStorage.removeItem('smartmug_last_panel');
    }
  });

  // Set up function navigation
  document.getElementById('versionBtn').addEventListener('click', showVersionFunction);
  document.getElementById('temperatureBtn').addEventListener('click', showTemperatureFunction);
  document.getElementById('greetingBtn').addEventListener('click', showGreetingFunction);
  document.getElementById('dynamicModeBtn').addEventListener('click', showDynamicModeFunction);
  document.getElementById('imageEditorBtn').addEventListener('click', showImageEditorFunction);
  document.getElementById('multiCupBtn').addEventListener('click', showMultiCupFunction);

  // Initialize image editor
  window.imageEditor.initializeGrid();

  // Set up global functions for UI callbacks
  window.refreshVersion = refreshVersion;
  window.refreshTemperature = refreshTemperature;
  window.setGreetingMessage = setGreetingMessage;
  window.setDynamicMode = setDynamicMode;
  window.currentTool = currentTool;
  window.sendImageData = sendImageData;
  window.resetImage = () => {
    window.imageEditor.reset();
    updateImageStatus('Image reset');
  };

  // Set up drawing functions that delegate to imageEditor
  window.startDrawing = (row, col) => {
    window.imageEditor.startDrawing(row, col);
  };
  window.continueDrawing = (row, col) => {
    window.imageEditor.continueDrawing(row, col);
  };
  window.stopDrawing = () => {
    window.imageEditor.stopDrawing();
  };
});

async function connectToDevice() {
  // Check if Web Bluetooth is supported
  if (!isBluetoothSupported) {
    updateDeviceStatus('Web Bluetooth is not supported in this browser. Please use Chrome or Edge.', true);
    return;
  }

  const connectButton = document.getElementById('connectButton');

  if (isConnected) {
    // Disconnect
    bleManager.disconnect();
    isConnected = false;
    connectButton.textContent = 'Connect to Device';
    updateDeviceStatus('Not connected');
    showConnectionPanel();
    return;
  }

  try {
    connectButton.disabled = true;
    connectButton.textContent = 'Connecting...';
    updateDeviceStatus('Connecting...');

    // Request device
    const device = await bleManager.requestDevice();

    // Connect to device (device name verification happens inside connect method)
    await bleManager.connect();

    // Set up disconnection handler
    if (bleManager.device) {
      bleManager.device.addEventListener('gattserverdisconnected', handleDisconnection);
    }

    // Update UI
    isConnected = true;
    connectButton.textContent = 'Disconnect';
    connectButton.disabled = false;
    updateDeviceStatus('Connected');
    updateDeviceStatus('Connected');
    updateSidebarConnectButton(true);
    hideConnectionPanel();
    showWelcomeMessage();

  } catch (error) {
    console.error('Connection failed:', error);
    connectButton.disabled = false;
    connectButton.textContent = 'Connect to Device';
    updateDeviceStatus(error.message, true);
  }
}

function handleDisconnection() {
  console.warn('Device disconnected unexpectedly');
  isConnected = false;
  const connectButton = document.getElementById('connectButton');
  if (connectButton) {
    connectButton.textContent = 'Connect to Device';
    connectButton.disabled = false;
  }
  updateDeviceStatus('Disconnected', true);
  updateSidebarConnectButton(false);
  showToast('Device disconnected. Please reconnect.', 'warning');
}

// Function panel handlers
function showVersionFunction() {
  if (!isConnected && !isDemoMode) {
    showToast('Please connect to a device first', 'warning');
    return;
  }
  showVersionPanel();
}

function showTemperatureFunction() {
  if (!isConnected && !isDemoMode) {
    showToast('Please connect to a device first', 'warning');
    return;
  }
  showTemperaturePanel();
}

function showGreetingFunction() {
  if (!isConnected && !isDemoMode) {
    showToast('Please connect to a device first', 'warning');
    return;
  }
  showGreetingPanel();
}

function showDynamicModeFunction() {
  if (!isConnected && !isDemoMode) {
    showToast('Please connect to a device first', 'warning');
    return;
  }
  showDynamicModePanel();
}

function showImageEditorFunction() {
  if (!isConnected && !isDemoMode) {
    showToast('Please connect to a device first', 'warning');
    return;
  }
  window.ui.showImageEditorPanel();
}

function showMultiCupFunction() {
  // Multi-cup manages its own connections, so don't check isConnected
  localStorage.setItem('smartmug_last_panel', 'multiCup');
  window.ui.showMultiCupPanel();

  // Attempt to auto-reconnect to previously paired devices
  if (window.multiCupBLE) {
    window.multiCupBLE.autoReconnectAll().catch(err => {
      console.error("Auto-reconnect failed:", err);
    });
  }
}

// UI callback functions
async function refreshVersion() {
  if (!isConnected && !isDemoMode) return;

  if (isDemoMode) {
    showVersionPanel('v1.0.0 (Demo Mode)');
    return;
  }

  try {
    const version = await bleManager.readVersion();
    showVersionPanel(version);
  } catch (error) {
    console.error('Failed to read version:', error);
    showVersionPanel('Error reading version');
  }
}

async function refreshTemperature() {
  if (!isConnected && !isDemoMode) return;

  if (isDemoMode) {
    showTemperaturePanel(25 + Math.floor(Math.random() * 5)); // Random temp for demo
    return;
  }

  try {
    const temperature = await bleManager.readTemperature();
    showTemperaturePanel(temperature);
  } catch (error) {
    console.error('Failed to read temperature:', error);
    showTemperaturePanel('Error');
  }
}

async function setGreetingMessage(message) {
  if (!isConnected && !isDemoMode) return;

  if (!message || message.trim() === '') {
    updateGreetingStatus('Please enter a message', true);
    return;
  }

  try {
    if (isDemoMode) {
      await new Promise(resolve => setTimeout(resolve, 500)); // Simulate delay
      updateGreetingStatus('Message set successfully (Demo)');
    } else {
      await bleManager.setGreetingMessage(message);
      updateGreetingStatus('Message set successfully');
    }
  } catch (error) {
    console.error('Failed to set greeting message:', error);
    updateGreetingStatus('Error setting message', true);
  }
}

async function setDynamicMode(mode) {
  if (!isConnected && !isDemoMode) return;

  try {
    if (isDemoMode) {
      await new Promise(resolve => setTimeout(resolve, 500)); // Simulate delay
      updateModeStatus('Mode set successfully (Demo)');
    } else {
      await bleManager.setDynamicMode(mode);
      updateModeStatus('Mode set successfully');
    }
  } catch (error) {
    console.error('Failed to set dynamic mode:', error);
    updateModeStatus('Error setting mode', true);
  }
}

async function sendImageData(imageData = null, options = {}) {
  if (!isConnected && !isDemoMode) {
    updateImageStatus('Not connected to device', true);
    showToast('Please connect to device first', 'warning');
    return false;
  }

  // Check actual connection status (skip for demo mode)
  if (!isDemoMode && !bleManager.isConnected()) {
    updateImageStatus('Device disconnected. Please reconnect.', true);
    showToast('Device disconnected. Please reconnect.', 'error');
    isConnected = false;
    handleDisconnection();
    return false;
  }

  try {
    const startTime = Date.now();
    const { silent = false, label = 'Image' } = options;

    if (!silent) {
      showToast('Sending image to device...', 'info');
    }

    // Use provided imageData or get from editor
    const dataToSend = imageData || window.imageEditor.getGridData();

    if (isDemoMode) {
      await new Promise(resolve => setTimeout(resolve, 200));
    } else {
      await bleManager.setImageData(dataToSend);
    }

    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
    console.log(`⚡ ${label} sent in ${elapsed}s`);

    if (!silent) {
      updateImageStatus(`Image sent successfully (${elapsed}s)`);
      showToast(`Image sent successfully in ${elapsed}s!`, 'success');
    }

    return { success: true, elapsed: parseFloat(elapsed) };
  } catch (error) {
    console.error('Failed to send image data:', error);
    updateImageStatus(`Error: ${error.message}`, true);
    if (!options.silent) {
      showToast(`Failed to send image: ${error.message}`, 'error');
    }
    return { success: false, error: error.message };
  }
}

function updateSidebarConnectButton(connected) {
  const btn = document.getElementById('sidebarConnectBtn');
  if (btn) {
    if (connected) {
      btn.innerHTML = '<span>❌</span> Disconnect';
      btn.className = 'w-full bg-red-500 hover:bg-red-700 text-white font-bold py-2 px-4 rounded flex items-center justify-center gap-2';
    } else {
      btn.innerHTML = '<span>🔗</span> Connect Device';
      btn.className = 'w-full bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded flex items-center justify-center gap-2';
    }
  }
}

// UI helper functions
function showConnectionPanel() {
  document.getElementById('connectionPanel').classList.remove('hidden');
  document.getElementById('mainContent').classList.add('hidden');
}

function hideConnectionPanel() {
  document.getElementById('connectionPanel').classList.add('hidden');
  document.getElementById('mainContent').classList.remove('hidden');
}

function updateDeviceStatus(status, isError = false) {
  const statusElement = document.getElementById('deviceStatus');
  const errorElement = document.getElementById('errorMessage');

  if (isError) {
    statusElement.textContent = 'Error';
    statusElement.className = 'text-red-500';
    errorElement.textContent = status;
    errorElement.classList.remove('hidden');
  } else {
    statusElement.textContent = status;
    statusElement.className = status === 'Connected' ? 'text-green-500' : 'text-gray-600';
    errorElement.classList.add('hidden');
  }
}

function showWelcomeMessage() {
  document.getElementById('welcomeMessage').classList.remove('hidden');
  // Hide all function panels
  const panels = ['versionPanel', 'temperaturePanel', 'greetingPanel', 'dynamicModePanel', 'imageEditorPanel', 'multiCupPanel'];
  panels.forEach(panel => {
    const element = document.getElementById(panel);
    if (element) element.classList.add('hidden');
  });
}

function showVersionPanel(version = null) {
  hideAllFunctionPanels();
  const panel = document.getElementById('versionPanel');
  if (panel) {
    if (version !== null) {
      panel.innerHTML = `
        <h2 class="text-xl font-semibold mb-4">Version Information</h2>
        <div class="version-info">${version}</div>
        <button id="refreshVersionBtn" class="mt-4 bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
          Refresh
        </button>
      `;
    } else {
      panel.innerHTML = `
        <h2 class="text-xl font-semibold mb-4">Version Information</h2>
        <div class="version-info">Not loaded</div>
        <button id="refreshVersionBtn" class="mt-4 bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
          Read Version
        </button>
      `;
    }
    panel.classList.remove('hidden');

    // Add event listener for refresh button
    document.getElementById('refreshVersionBtn').addEventListener('click', () => {
      window.refreshVersion();
    });
  }
}

function showTemperaturePanel(temperature = null) {
  hideAllFunctionPanels();
  const panel = document.getElementById('temperaturePanel');
  if (panel) {
    if (temperature !== null) {
      panel.innerHTML = `
        <h2 class="text-xl font-semibold mb-4">Temperature Reading</h2>
        <div class="temperature-display">${temperature}°C</div>
        <button id="refreshTempBtn" class="mt-4 bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
          Refresh
        </button>
      `;
    } else {
      panel.innerHTML = `
        <h2 class="text-xl font-semibold mb-4">Temperature Reading</h2>
        <div class="temperature-display">--°C</div>
        <button id="refreshTempBtn" class="mt-4 bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
          Read Temperature
        </button>
      `;
    }
    panel.classList.remove('hidden');

    // Add event listener for refresh button
    document.getElementById('refreshTempBtn').addEventListener('click', () => {
      window.refreshTemperature();
    });
  }
}

function showGreetingPanel() {
  hideAllFunctionPanels();
  const panel = document.getElementById('greetingPanel');
  if (panel) {
    panel.innerHTML = `
      <h2 class="text-xl font-semibold mb-4">Set Greeting Message</h2>
      <div class="mb-4">
        <label for="greetingInput" class="block text-gray-700 text-sm font-bold mb-2">Message:</label>
        <input type="text" id="greetingInput" class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline" maxlength="20" placeholder="Enter greeting message">
      </div>
      <button id="setGreetingBtn" class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
        Set Message
      </button>
      <div id="greetingStatus" class="mt-2 text-green-500 hidden"></div>
    `;
    panel.classList.remove('hidden');

    // Add event listener for set button
    document.getElementById('setGreetingBtn').addEventListener('click', () => {
      const message = document.getElementById('greetingInput').value;
      window.setGreetingMessage(message);
    });
  }
}

function showDynamicModePanel() {
  hideAllFunctionPanels();
  const panel = document.getElementById('dynamicModePanel');
  if (panel) {
    panel.innerHTML = `
      <h2 class="text-xl font-semibold mb-4">Set Dynamic Mode</h2>
      <div class="mb-4">
        <label class="block text-gray-700 text-sm font-bold mb-2">Select Mode:</label>
        <div class="space-y-2">
          <div>
            <input type="radio" id="static" name="mode" value="static" checked>
            <label for="static" class="ml-2">Static</label>
          </div>
          <div>
            <input type="radio" id="scrollRight" name="mode" value="scrollRight">
            <label for="scrollRight" class="ml-2">Scroll Right to Left</label>
          </div>
          <div>
            <input type="radio" id="scrollLeft" name="mode" value="scrollLeft">
            <label for="scrollLeft" class="ml-2">Scroll Left to Right</label>
          </div>
          <div>
            <input type="radio" id="flashing" name="mode" value="flashing">
            <label for="flashing" class="ml-2">Flashing</label>
          </div>
        </div>
      </div>
      <button id="setModeBtn" class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
        Set Mode
      </button>
      <div id="modeStatus" class="mt-2 text-green-500 hidden"></div>
    `;
    panel.classList.remove('hidden');

    // Add event listener for set button
    document.getElementById('setModeBtn').addEventListener('click', () => {
      const selectedMode = document.querySelector('input[name="mode"]:checked').value;
      window.setDynamicMode(selectedMode);
    });
  }
}

function hideAllFunctionPanels() {
  document.getElementById('welcomeMessage').classList.add('hidden');
  const panels = ['versionPanel', 'temperaturePanel', 'greetingPanel', 'dynamicModePanel', 'imageEditorPanel', 'multiCupPanel'];
  panels.forEach(panel => {
    const element = document.getElementById(panel);
    if (element) element.classList.add('hidden');
  });
}

function initializePixelGrid() {
  const grid = document.getElementById('pixelGrid');
  grid.innerHTML = '';

  // Create 48x12 grid (576 pixels)
  for (let row = 0; row < 12; row++) {
    for (let col = 0; col < 48; col++) {
      const pixel = document.createElement('div');
      pixel.className = 'pixel';
      pixel.dataset.row = row;
      pixel.dataset.col = col;
      pixel.addEventListener('mousedown', () => {
        if (window.imageEditor && window.imageEditor.startDrawing) {
          window.imageEditor.startDrawing(row, col);
        }
      });
      pixel.addEventListener('mouseenter', () => {
        if (window.imageEditor && window.imageEditor.continueDrawing) {
          window.imageEditor.continueDrawing(row, col);
        }
      });
      grid.appendChild(pixel);
    }
  }

  // Add mouseup event to the grid to stop drawing
  grid.addEventListener('mouseup', () => {
    if (window.imageEditor && window.imageEditor.stopDrawing) {
      window.imageEditor.stopDrawing();
    }
  });
  grid.addEventListener('mouseleave', () => {
    if (window.imageEditor && window.imageEditor.stopDrawing) {
      window.imageEditor.stopDrawing();
    }
  });
}

function updateGreetingStatus(message, isError = false) {
  const statusElement = document.getElementById('greetingStatus');
  if (statusElement) {
    statusElement.textContent = message;
    statusElement.className = isError ? 'mt-2 text-red-500' : 'mt-2 text-green-500';
    statusElement.classList.remove('hidden');
  }
}

function updateModeStatus(message, isError = false) {
  const statusElement = document.getElementById('modeStatus');
  if (statusElement) {
    statusElement.textContent = message;
    statusElement.className = isError ? 'mt-2 text-red-500' : 'mt-2 text-green-500';
    statusElement.classList.remove('hidden');
  }
}

function updateImageStatus(message, isError = false) {
  const statusElement = document.getElementById('imageStatus');
  if (statusElement) {
    statusElement.textContent = message;
    statusElement.className = isError ? 'mt-2 text-red-500' : 'mt-2 text-green-500';
    statusElement.classList.remove('hidden');
  }
}

// Add function content panels to the HTML dynamically
function initializeFunctionPanels() {
  const functionContent = document.getElementById('functionContent');

  // Create panels if they don't exist
  const panels = [
    { id: 'versionPanel', class: 'hidden' },
    { id: 'temperaturePanel', class: 'hidden' },
    { id: 'greetingPanel', class: 'hidden' },
    { id: 'dynamicModePanel', class: 'hidden' },
    { id: 'imageEditorPanel', class: 'hidden' },
    { id: 'multiCupPanel', class: 'hidden' }
  ];

  panels.forEach(panel => {
    if (!document.getElementById(panel.id)) {
      const panelElement = document.createElement('div');
      panelElement.id = panel.id;
      panelElement.className = panel.class;
      functionContent.appendChild(panelElement);
    }
  });
}

// Initialize panels when DOM is loaded
document.addEventListener('DOMContentLoaded', initializeFunctionPanels);

// Image upload and processing functions
let processedImageData = null; // Store processed image data for preview

async function processUploadedImage() {
  const fileInput = document.getElementById('imageFileInput');
  const file = fileInput.files[0];

  if (!file) {
    showToast('Please select an image file', 'warning');
    return;
  }

  try {
    showToast('Processing image...', 'info');

    // Get processing options
    const algorithm = document.getElementById('algorithmSelect').value;
    const threshold = parseInt(document.getElementById('thresholdSlider').value);
    const brightness = parseInt(document.getElementById('brightnessSlider').value);
    const contrast = parseInt(document.getElementById('contrastSlider').value);
    const sharpen = parseFloat(document.getElementById('sharpenSlider').value);
    const gamma = parseFloat(document.getElementById('gammaSlider').value);
    const fitMode = document.getElementById('fitModeSelect').value;
    const maintainAspect = document.getElementById('maintainAspectCheckbox').checked;

    // Process image
    const result = await window.imageProcessor.processImage(file, {
      algorithm,
      threshold,
      brightness,
      contrast,
      sharpen,
      gamma,
      fitMode,
      autoContrast: document.getElementById('autoContrastCheckbox').checked,
      maintainAspect: maintainAspect // Kept for backward compatibility if needed, but fitMode overrides
    });

    // Store processed data
    processedImageData = result;

    // Show preview section
    const previewSection = document.getElementById('previewSection');
    previewSection.classList.remove('hidden');

    // Draw original (resized) preview
    const originalCanvas = document.getElementById('originalPreview');
    const originalCtx = originalCanvas.getContext('2d');
    originalCtx.clearRect(0, 0, originalCanvas.width, originalCanvas.height);
    originalCtx.drawImage(result.originalImage, 0, 0, 192, 48);

    // Draw processed preview
    const processedCanvas = document.getElementById('processedPreview');
    const processedCtx = processedCanvas.getContext('2d');
    processedCtx.clearRect(0, 0, processedCanvas.width, processedCanvas.height);
    processedCtx.drawImage(result.preview, 0, 0, 384, 96);

    // Handle temporal animation if applicable
    if (result.isTemporal) {
      setupTemporalAnimation(result);
    } else {
      // Hide temporal controls for non-temporal algorithms
      document.getElementById('temporalControls').classList.add('hidden');
      stopTemporalAnimation();
    }

    // Display image analysis results
    if (result.analysis) {
      const analysisStats = document.getElementById('analysisStats');
      const analysisSuggestions = document.getElementById('analysisSuggestions');

      const contrastPercent = (result.analysis.contrast * 100).toFixed(0);
      const meanRounded = Math.round(result.analysis.mean);

      analysisStats.innerHTML = `
        <div class="text-xs space-y-1">
          <div>Range: ${result.analysis.min}-${result.analysis.max}</div>
          <div>Contrast: ${contrastPercent}%</div>
          <div>Brightness: ${meanRounded}/255</div>
          <div>Quality: <span class="${result.analysis.quality === 'poor' ? 'text-red-600' : 'text-green-600'}">${result.analysis.quality}</span></div>
        </div>
      `;

      if (result.analysis.suggestions.length > 0) {
        analysisSuggestions.innerHTML = result.analysis.suggestions
          .map(s => `<div class="text-xs mt-1">${s}</div>`)
          .join('');
      } else {
        analysisSuggestions.innerHTML = '<div class="text-xs mt-1 text-green-600">✓ Image looks good!</div>';
      }

      document.getElementById('imageAnalysis').classList.remove('hidden');
    }

    showToast('Image processed successfully!', 'success');
  } catch (error) {
    console.error('Image processing error:', error);
    showToast(`Failed to process image: ${error.message}`, 'error');
  }
}

function applyProcessedImageToEditor() {
  if (!processedImageData) {
    showToast('No processed image available', 'warning');
    return;
  }

  try {
    // Apply grid data to imageEditor
    window.imageEditor.grid = processedImageData.grid;
    window.imageEditor.updateDisplay();

    showToast('Image applied to editor!', 'success');

    // Scroll to pixel grid
    const pixelGrid = document.getElementById('pixelGrid');
    if (pixelGrid) {
      pixelGrid.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  } catch (error) {
    console.error('Failed to apply image:', error);
    showToast(`Failed to apply image: ${error.message}`, 'error');
  }
}

// Temporal Animation Management
let temporalAnimationState = {
  isPlaying: false,
  currentFrame: 0,
  intervalId: null,
  fps: 20,
  frameData: null
};

function setupTemporalAnimation(result) {
  // Store frame data
  temporalAnimationState.frameData = result.frames;
  temporalAnimationState.currentFrame = 0;

  // Show temporal controls
  const temporalControls = document.getElementById('temporalControls');
  temporalControls.classList.remove('hidden');

  // Update frame display
  updateFrameDisplay();

  // Create frame selection buttons
  const frameButtons = document.getElementById('frameButtons');
  frameButtons.innerHTML = '';
  result.frames.forEach((frame, index) => {
    const btn = document.createElement('button');
    btn.textContent = `Frame ${index + 1}`;
    btn.className = `px-3 py-1 rounded text-sm ${index === 0 ? 'bg-blue-500 text-white' : 'bg-gray-200 hover:bg-gray-300'}`;
    btn.onclick = () => selectFrame(index);
    frameButtons.appendChild(btn);
  });

  // Create send frame buttons
  const sendFrameButtons = document.getElementById('sendFrameButtons');
  sendFrameButtons.innerHTML = '';
  result.frames.forEach((frame, index) => {
    const btn = document.createElement('button');
    btn.textContent = `Send Frame ${index + 1}`;
    btn.className = 'bg-blue-500 hover:bg-blue-600 text-white font-semibold py-2 px-3 rounded text-xs';
    btn.onclick = () => sendTemporalFrame(index);
    sendFrameButtons.appendChild(btn);
  });

  // Set up animation controls
  document.getElementById('playAnimationBtn').onclick = startTemporalAnimation;
  document.getElementById('pauseAnimationBtn').onclick = pauseTemporalAnimation;
  document.getElementById('fpsSlider').oninput = (e) => {
    temporalAnimationState.fps = parseInt(e.target.value);
    document.getElementById('fpsValue').textContent = e.target.value;
    // Restart animation if playing to apply new FPS
    if (temporalAnimationState.isPlaying) {
      stopTemporalAnimation();
      startTemporalAnimation();
    }
  };

  // Set up device animation controls
  document.getElementById('sendAnimationBtn').onclick = sendAnimationToDevice;
  document.getElementById('stopAnimationBtn').onclick = stopAnimationToDevice;

  // Set up device animation-speed slider (sends raw speed byte 1..255).
  const deviceDelaySlider = document.getElementById('deviceDelaySlider');
  const deviceDelayValue = document.getElementById('deviceDelayValue');
  if (deviceDelaySlider && deviceDelayValue) {
    deviceDelaySlider.addEventListener('input', (e) => {
      deviceAnimationState.animationSpeed = parseInt(e.target.value);
      deviceDelayValue.textContent = e.target.value;
    });
  }

  // Auto-start animation
  setTimeout(() => startTemporalAnimation(), 500);
}

function selectFrame(frameIndex) {
  if (!temporalAnimationState.frameData) return;

  temporalAnimationState.currentFrame = frameIndex;
  updateFrameDisplay();
  renderCurrentFrame();

  // Update frame button styling
  const frameButtons = document.getElementById('frameButtons').children;
  Array.from(frameButtons).forEach((btn, idx) => {
    if (idx === frameIndex) {
      btn.className = 'px-3 py-1 rounded text-sm bg-blue-500 text-white';
    } else {
      btn.className = 'px-3 py-1 rounded text-sm bg-gray-200 hover:bg-gray-300';
    }
  });
}

function renderCurrentFrame() {
  if (!temporalAnimationState.frameData) return;

  const frame = temporalAnimationState.frameData[temporalAnimationState.currentFrame];
  const processedCanvas = document.getElementById('processedPreview');
  const ctx = processedCanvas.getContext('2d');

  // Draw the frame
  ctx.clearRect(0, 0, processedCanvas.width, processedCanvas.height);
  ctx.drawImage(frame.preview, 0, 0, 384, 96);
}

function startTemporalAnimation() {
  if (!temporalAnimationState.frameData || temporalAnimationState.isPlaying) return;

  temporalAnimationState.isPlaying = true;
  document.getElementById('playAnimationBtn').classList.add('hidden');
  document.getElementById('pauseAnimationBtn').classList.remove('hidden');

  // Calculate interval from FPS
  const interval = 1000 / temporalAnimationState.fps;

  temporalAnimationState.intervalId = setInterval(() => {
    // Advance to next frame
    temporalAnimationState.currentFrame =
      (temporalAnimationState.currentFrame + 1) % temporalAnimationState.frameData.length;

    updateFrameDisplay();
    renderCurrentFrame();
    selectFrame(temporalAnimationState.currentFrame); // Update button styling
  }, interval);
}

function pauseTemporalAnimation() {
  stopTemporalAnimation();
  document.getElementById('playAnimationBtn').classList.remove('hidden');
  document.getElementById('pauseAnimationBtn').classList.add('hidden');
}

function stopTemporalAnimation() {
  temporalAnimationState.isPlaying = false;
  if (temporalAnimationState.intervalId) {
    clearInterval(temporalAnimationState.intervalId);
    temporalAnimationState.intervalId = null;
  }
}

function updateFrameDisplay() {
  if (!temporalAnimationState.frameData) return;

  const display = document.getElementById('currentFrameDisplay');
  display.textContent = `Frame ${temporalAnimationState.currentFrame + 1}/${temporalAnimationState.frameData.length}`;
}

async function sendTemporalFrame(frameIndex) {
  if (!temporalAnimationState.frameData) {
    showToast('No frame data available', 'warning');
    return;
  }

  const frame = temporalAnimationState.frameData[frameIndex];
  const result = await sendImageData(frame.grid, {
    silent: false,
    label: `Frame ${frameIndex + 1}`
  });

  if (result && result.success) {
    showToast(`Frame ${frameIndex + 1} sent successfully in ${result.elapsed}s!`, 'success');
  } else if (result && !result.success) {
    showToast(`Failed to send frame ${frameIndex + 1}: ${result.error}`, 'error');
  }
}

// Device animation state. With the 0x26 protocol, the cup plays
// autonomously after a one-shot upload — `intervalId` here drives only the
// local browser preview loop, not BLE traffic.
let deviceAnimationState = {
  isRunning: false,
  currentFrame: 0,
  intervalId: null,
  startTime: null,
  // Cup's speed byte (1..255, larger = faster). Sent as-is in the 0x26
  // prologue + each frame. Default 130 matches the official app's
  // `speedValue: 130`. The exact unit isn't characterized — see
  // PROTOCOL_SPEC.md §4.6 for what we know empirically.
  animationSpeed: 130
};

async function sendAnimationToDevice() {
  if (!temporalAnimationState.frameData?.length) {
    showToast('No frame data available', 'warning');
    return;
  }
  if (!isConnected) {
    showToast('Device not connected', 'warning');
    return;
  }
  if (deviceAnimationState.isRunning) {
    showToast('Animation already running', 'warning');
    return;
  }

  // Clear any pending preview-loop timer so we don't double-schedule.
  if (deviceAnimationState.intervalId) {
    clearTimeout(deviceAnimationState.intervalId);
    deviceAnimationState.intervalId = null;
  }

  document.getElementById('sendAnimationBtn').classList.add('hidden');
  document.getElementById('stopAnimationBtn').classList.remove('hidden');
  document.getElementById('deviceAnimationProgress').classList.remove('hidden');

  deviceAnimationState.isRunning = true;
  deviceAnimationState.currentFrame = 0;
  deviceAnimationState.startTime = Date.now();

  const totalFrames = temporalAnimationState.frameData.length;
  const frames = temporalAnimationState.frameData.map(f => f.grid);

  // Speed byte: take the slider value, clamp to 1..255.
  const speed = Math.max(1, Math.min(255, Math.round(deviceAnimationState.animationSpeed)));

  console.log(`🎬 Uploading ${totalFrames}-frame animation at speed=${speed}ms...`);
  document.getElementById('deviceAnimationStatus').textContent =
    `Uploading ${totalFrames} frames...`;

  // Phase 1: one-shot upload via 0x26. Cup then plays autonomously.
  if (!isDemoMode) {
    try {
      const t0 = Date.now();
      await bleManager.setAnimation(frames, speed);
      const elapsed = ((Date.now() - t0) / 1000).toFixed(2);
      console.log(`✅ Animation uploaded in ${elapsed}s (cup playing autonomously)`);
      showToast(`Animation uploaded in ${elapsed}s — cup playing autonomously`, 'success');
    } catch (error) {
      console.error('Animation upload failed:', error);
      showToast(`Animation upload failed: ${error.message}`, 'error');
      stopAnimationToDevice();
      return;
    }
  } else {
    await new Promise(r => setTimeout(r, 200));
    showToast('Demo mode: simulating cup playback', 'info');
  }

  // Phase 2: local preview loop, independent of cup playback. The cup's
  // frame period as a function of `speed` is uncharacterized, but
  // empirically speed=130 → ~250 ms/frame (~1 s per 4-frame cycle). The
  // inverse approximation `period ≈ 32500 / speed` ms tracks the cup
  // roughly across the byte's range; floored at 50 ms (20 fps) for fast
  // speeds, and clamped to 2 s on the slow end so the preview still
  // visibly progresses. See PROTOCOL_SPEC.md §4.6.
  const previewIntervalMs = Math.min(2000, Math.max(50, Math.round(32500 / speed)));
  const previewLoop = () => {
    if (!deviceAnimationState.isRunning) return;
    const f = deviceAnimationState.currentFrame;
    document.getElementById('deviceAnimationStatus').textContent =
      `Cup playing autonomously — preview frame ${f + 1}/${totalFrames}`;
    deviceAnimationState.currentFrame = (f + 1) % totalFrames;
    deviceAnimationState.intervalId = setTimeout(previewLoop, previewIntervalMs);
  };
  previewLoop();
}

function stopAnimationToDevice() {
  deviceAnimationState.isRunning = false;

  if (deviceAnimationState.intervalId) {
    clearTimeout(deviceAnimationState.intervalId);
    deviceAnimationState.intervalId = null;
  }

  // Show send button, hide stop button
  document.getElementById('sendAnimationBtn').classList.remove('hidden');
  document.getElementById('stopAnimationBtn').classList.add('hidden');

  // Hide progress display
  document.getElementById('deviceAnimationProgress').classList.add('hidden');

  showToast('Animation stopped', 'info');
}

// ===== MULTI-CUP DISPLAY FUNCTIONS =====

// Multi-cup stored image data
let multiCupProcessedData = null;

/**
 * Connect to a specific cup at position
 */
async function connectMultiCup(position) {
  const btn = document.getElementById(`connectCup${position}Btn`);
  const cup = window.multiCupBLE.cups[position];

  // If already connected, disconnect
  if (cup.connected) {
    try {
      window.multiCupBLE.disconnectCup(position);
      window.ui.updateMultiCupConnectionStatus(position, false);
      showToast(`Cup ${position} disconnected`, 'info');
    } catch (error) {
      console.error(`Failed to disconnect cup ${position}:`, error);
      showToast(`Error disconnecting cup ${position}: ${error.message}`, 'error');
    }
    return;
  }

  // Otherwise, connect
  try {
    if (btn) {
      btn.disabled = true;
      btn.textContent = 'Connecting...';
    }

    if (isDemoMode) {
      await new Promise(resolve => setTimeout(resolve, 500)); // Simulate delay
      // Manually set connected state for demo
      window.multiCupBLE.cups[position].connected = true;
      // Simulate a Web Bluetooth ID (base64)
      window.multiCupBLE.cups[position].deviceId = "c2ltdWxhdGVkX2lk_" + position;
      window.multiCupBLE.cups[position].deviceName = "SGUAI-C3 (Demo)";
      window.ui.updateMultiCupConnectionStatus(position, true);
      showToast(`Cup ${position} connected successfully! (Demo)`, 'success');
    } else {
      await window.multiCupBLE.connectCup(position);
      window.ui.updateMultiCupConnectionStatus(position, true);
      showToast(`Cup ${position} connected successfully!`, 'success');
    }
  } catch (error) {
    console.error(`Failed to connect cup ${position}:`, error);
    showToast(`Error connecting cup ${position}: ${error.message}`, 'error');
    window.ui.updateMultiCupConnectionStatus(position, false);
  } finally {
    if (btn) {
      btn.disabled = false;
    }
  }
}

/**
 * Handle multi-cup disconnection
 */
function onMultiCupDisconnect(position) {
  window.ui.updateMultiCupConnectionStatus(position, false);
  showToast(`Cup ${position} disconnected unexpectedly!`, 'warning');
}

/**
 * Handle multi-cup reconnection
 */
function onMultiCupReconnect(position) {
  window.ui.updateMultiCupConnectionStatus(position, true);
  showToast(`✅ Cup ${position} reconnected successfully!`, 'success');
}

/**
 * Process uploaded image for multi-cup display
 */
async function processMultiCupImage() {
  const fileInput = document.getElementById('multiCupImageInput');
  const file = fileInput.files[0];

  if (!file) {
    showToast('Please select an image file', 'warning');
    return;
  }

  try {
    showToast('Processing image for multi-cup display...', 'info');

    // Load image to check dimensions
    const img = await window.imageProcessor.loadImageFromFile(file);
    const aspect = img.width / img.height;

    // Get current layout
    let layout = document.querySelector('input[name="layout"]:checked').value;
    let maintainAspect = true;

    // Logic: If image is square-ish (aspect ~1) but user wants 2x2 (aspect 4),
    // we must STRETCH it to fill the cups, otherwise it looks like "only two cups"
    if (Math.abs(aspect - 1) < 0.5 && layout === 'grid_2x2') {
      maintainAspect = false;
      showToast('Stretching square image to fill 2x2 layout', 'info');
    } else if (Math.abs(aspect - 1) < 0.5 && layout !== 'vertical_4x1' && layout !== 'grid_2x2') {
      // Default behavior for other cases (if any)
      // For now, if it's square and NOT 2x2, we might want to suggest vertical,
      // but let's stick to the user's selection or default if they haven't chosen.
      // If they chose vertical, it's fine.
    }

    // Update UI labels based on layout
    updateMultiCupLabels(layout);

    // Get algorithm
    const algorithm = document.getElementById('multiCupAlgorithm').value;
    const fitMode = document.getElementById('multiCupFitMode').value;
    const gamma = parseFloat(document.getElementById('multiCupGammaSlider').value);

    // Process and split image
    const result = await window.imageSplitter.processImageForMultiCup(file, {
      algorithm,
      fitMode,
      gamma,
      maintainAspect: true // Default for multi-cup, but fitMode handles it
    }, layout);

    // Store result
    multiCupProcessedData = result;

    // Show preview section
    document.getElementById('multiCupPreviewSection').classList.remove('hidden');
    document.getElementById('multiCupSendSection').classList.remove('hidden');

    // Render composite preview
    const compositeCanvas = document.getElementById('compositePreview');
    const compositePreview = window.imageSplitter.generateCompositePreview(result.chunks, layout);
    const ctx = compositeCanvas.getContext('2d');
    compositeCanvas.width = compositePreview.width;
    compositeCanvas.height = compositePreview.height;
    ctx.clearRect(0, 0, compositeCanvas.width, compositeCanvas.height);
    ctx.drawImage(compositePreview, 0, 0);

    // Check if result has frames (Animation)
    const animControls = document.getElementById('multiCupAnimationControls');
    const frameCountBadge = document.getElementById('multiCupFrameCount');

    if (result.frames && result.frames.length > 1) {
      animControls.classList.remove('hidden');
      frameCountBadge.textContent = `${result.frames.length} frames`;
      showToast(`Loaded animated GIF with ${result.frames.length} frames!`, 'success');
    } else {
      animControls.classList.add('hidden');
    }

    // Debug: Log chunk dimensions
    console.log('🔍 DEBUG: Rendering individual cup previews');
    for (let i = 0; i < 4; i++) {
      const chunk = result.chunks[i];
      console.log(`  Cup ${i} chunk: ${chunk.length} rows × ${chunk[0]?.length} cols`);

      // Count black pixels in each chunk
      let blackPixels = 0;
      for (let row = 0; row < chunk.length; row++) {
        for (let col = 0; col < chunk[row].length; col++) {
          if (chunk[row][col] === 1) blackPixels++;
        }
      }
      console.log(`  Cup ${i} has ${blackPixels} black pixels`);
    }

    // Render individual cup previews
    for (let i = 0; i < 4; i++) {
      const cupCanvas = document.getElementById(`cup${i}Preview`);
      const preview = result.chunkPreviews[i];
      console.log(`  Cup ${i} preview canvas: ${preview.width}×${preview.height}`);
      cupCanvas.width = preview.width;
      cupCanvas.height = preview.height;
      const cupCtx = cupCanvas.getContext('2d');
      cupCtx.clearRect(0, 0, cupCanvas.width, cupCanvas.height);
      cupCtx.drawImage(preview, 0, 0);
    }

    showToast('Image processed and split successfully!', 'success');
    console.log(`✅ Image split into ${result.chunks.length} chunks for layout: ${layout}`);
  } catch (error) {
    console.error('Multi-cup image processing error:', error);
    showToast(`Failed to process image: ${error.message}`, 'error');
  }
}



// Multi-Cup Animation State
let multiCupAnimationState = {
  isPlaying: false,
  currentFrame: 0,
  intervalId: null,
  mode: 'static' // 'static', 'scrollRight', 'scrollLeft', 'flashing'
};

/**
 * Play Multi-Cup Animation.
 *
 * Uploads the entire frame sequence to each cup once via the 0x26 command,
 * then returns — the cups play autonomously from internal storage with no
 * further BLE traffic. The local preview loop is independent of the cup's
 * playback (since we have no playback-progress feedback) and keeps spinning
 * until the user hits Stop.
 *
 * Speed is the cup's per-frame timer (1 byte sent in the prologue + each
 * frame). Default 130 matches the official app's `speedValue: 130`.
 */
async function playMultiCupAnimation() {
  if (!multiCupProcessedData?.frames?.length) {
    showToast('No animation frames available. Please process a GIF/animated image.', 'warning');
    return;
  }

  if (multiCupAnimationState.isPlaying) {
    showToast('Animation already playing', 'warning');
    return;
  }

  const modeSelect = document.getElementById('multiCupMotionMode');
  const modeMap = { 'static': 0x00, 'scrollRight': 0x01, 'scrollLeft': 0x02, 'flashing': 0x03 };
  const selectedModeStr = modeSelect ? modeSelect.value : 'static';
  const selectedMode = modeMap[selectedModeStr] || 0x00;

  multiCupAnimationState.isPlaying = true;
  multiCupAnimationState.mode = selectedModeStr;
  multiCupAnimationState.currentFrame = 0;

  // Update UI
  document.getElementById('playMultiCupAnimationBtn').classList.add('hidden');
  document.getElementById('stopMultiCupAnimationBtn').classList.remove('hidden');
  document.getElementById('multiCupAnimationStatus').classList.remove('hidden');

  const totalFrames = multiCupProcessedData.frames.length;
  console.log(`🎬 Starting Multi-Cup Animation: ${totalFrames} frames, Mode: ${selectedModeStr}`);

  // Transpose: frames[f].chunks[cup] -> cupFrames[cup][f]
  const cupFrames = [[], [], [], []];
  for (const frame of multiCupProcessedData.frames) {
    for (let cup = 0; cup < 4; cup++) {
      cupFrames[cup].push(frame.chunks[cup]);
    }
  }

  // Animation speed byte (1..255, larger = faster; default 130 matches the
  // official app's `speedValue`). We deliberately do NOT auto-derive from
  // the GIF's frame delays — those are in milliseconds, but the cup's speed
  // byte is not (see PROTOCOL_SPEC.md §4.6). Mapping ms → speed-byte
  // requires the inverse relationship we haven't fully characterized.
  const speed = 130;

  // Phase 1: upload to cups + set mode (single shot, ~1 s for short animations)
  if (!isDemoMode) {
    try {
      const statusDiv = document.getElementById('multiCupAnimationStatus');
      if (statusDiv) statusDiv.textContent = `Uploading ${totalFrames} frames...`;

      await window.multiCupBLE.setAnimationAll(cupFrames, speed, { silent: false });
      // Re-apply the user's chosen motion mode after the upload (the cup
      // resets to its default mode on each frame store). The user can pair
      // an animation with a scroll/flash overlay if they want — those layer
      // on top of the per-frame playback.
      await window.multiCupBLE.setDynamicModeAll(selectedMode);

      showToast(`✅ Animation uploaded — cups playing autonomously`, 'success');
    } catch (error) {
      if (error.message === 'No cups connected') {
        console.warn('Animation running in preview mode (no cups connected)');
        showToast('Preview mode (no cups connected)', 'info');
      } else {
        console.error('Animation upload failed:', error);
        showToast(`Animation upload failed: ${error.message}`, 'error');
        stopMultiCupAnimation();
        return;
      }
    }
  } else {
    showToast('Demo mode: simulating cup playback', 'info');
  }

  // Phase 2: local preview loop. Same approximation as the single-cup
  // case — `period ≈ 32500 / speed` ms, bounded [50 ms, 2 s].
  // See PROTOCOL_SPEC.md §4.6.
  const previewIntervalMs = Math.min(2000, Math.max(50, Math.round(32500 / speed)));
  const previewLoop = () => {
    if (!multiCupAnimationState.isPlaying) return;
    const f = multiCupAnimationState.currentFrame;
    updateMultiCupPreviews(f);
    const statusDiv = document.getElementById('multiCupAnimationStatus');
    if (statusDiv) {
      statusDiv.textContent = `Cup playing autonomously — preview frame ${f + 1}/${totalFrames}`;
    }
    multiCupAnimationState.currentFrame = (f + 1) % totalFrames;
    multiCupAnimationState.intervalId = setTimeout(previewLoop, previewIntervalMs);
  };
  previewLoop();
}

/**
 * Stop Multi-Cup Animation
 */
function stopMultiCupAnimation() {
  multiCupAnimationState.isPlaying = false;
  if (multiCupAnimationState.intervalId) {
    clearTimeout(multiCupAnimationState.intervalId);
    multiCupAnimationState.intervalId = null;
  }

  // Update UI
  document.getElementById('playMultiCupAnimationBtn').classList.remove('hidden');
  document.getElementById('stopMultiCupAnimationBtn').classList.add('hidden');
  document.getElementById('multiCupAnimationStatus').classList.add('hidden');

  showToast('Animation stopped', 'info');
}

/**
 * Sync all cups (Reset to Frame 1 + Mode)
 */
async function syncMultiCupAnimation() {
  // Stop any running animation first
  if (multiCupAnimationState.isPlaying) {
    stopMultiCupAnimation();
  }

  showToast('Syncing all cups...', 'info');

  try {
    // If we have frames, send the first one. If not, send the static image.
    let chunksToSend;
    if (multiCupProcessedData && multiCupProcessedData.frames) {
      chunksToSend = multiCupProcessedData.frames[0].chunks;
    } else if (multiCupProcessedData) {
      chunksToSend = multiCupProcessedData.chunks;
    } else {
      showToast('No image data to sync', 'warning');
      return;
    }

    // Get current mode
    const modeSelect = document.getElementById('multiCupMotionMode');
    const modeMap = {
      'static': 0x00,
      'scrollRight': 0x01,
      'scrollLeft': 0x02,
      'flashing': 0x03
    };
    const selectedMode = modeMap[modeSelect ? modeSelect.value : 'static'] || 0x00;

    if (isDemoMode) {
      await new Promise(r => setTimeout(r, 500));
    } else {
      await window.multiCupBLE.sendToAllWithMode(chunksToSend, selectedMode);
    }

    // Reset preview to frame 0 if the source has frames at all.
    if (multiCupProcessedData?.frames?.length) {
      updateMultiCupPreviews(0);
    }

    showToast('✅ Sync Complete: All cups reset to start', 'success');

  } catch (error) {
    console.error('Sync failed:', error);
    showToast('Sync failed', 'error');
  }
}

/**
 * Update Multi-Cup Previews for a specific frame
 * @param {number} frameIndex 
 */
function updateMultiCupPreviews(frameIndex) {
  if (!multiCupProcessedData || !multiCupProcessedData.frames || !multiCupProcessedData.frames[frameIndex]) {
    return;
  }

  const frameData = multiCupProcessedData.frames[frameIndex];

  for (let i = 0; i < 4; i++) {
    const cupCanvas = document.getElementById(`cup${i}Preview`);
    if (!cupCanvas) continue;

    const preview = frameData.chunkPreviews[i];
    if (!preview) continue;

    const cupCtx = cupCanvas.getContext('2d');
    cupCtx.clearRect(0, 0, cupCanvas.width, cupCanvas.height);
    cupCtx.drawImage(preview, 0, 0);
  }
}

/**
 * Send split image to all connected cups
 */
async function sendToAllCups() {
  if (!multiCupProcessedData) {
    showToast('No processed image available. Please process an image first.', 'warning');
    return;
  }

  const status = window.multiCupBLE.getConnectionStatus();

  // In demo mode, simulate all cups connected if none are "physically" connected but we want to test
  // Actually, we should rely on the simulated connection state from connectMultiCup
  // But for sendToAllCups, let's just check if we have any "connected" cups (simulated or real)

  let connectedCount = status.connected;
  if (isDemoMode) {
    // Count simulated connections
    connectedCount = Object.values(window.multiCupBLE.cups).filter(c => c.connected).length;
  }

  if (connectedCount === 0) {
    showToast('No cups connected. Please connect at least one cup.', 'warning');
    return;
  }

  const sendBtn = document.getElementById('sendToAllCupsBtn');
  const statusDiv = document.getElementById('multiCupSendStatus');

  try {
    if (sendBtn) {
      sendBtn.disabled = true;
      sendBtn.textContent = `Sending to ${connectedCount} cups...`;
    }

    if (statusDiv) {
      statusDiv.textContent = `Sending to ${connectedCount} connected cups...`;
      statusDiv.classList.remove('hidden');
    }

    showToast(`Sending to ${connectedCount} cups in parallel...`, 'info');

    // Send to all connected cups in parallel
    let result;
    if (isDemoMode) {
      await new Promise(resolve => setTimeout(resolve, 2000)); // Simulate sending
      result = {
        success: true,
        totalElapsed: 2000,
        successful: connectedCount,
        failed: 0,
        results: []
      };
    } else {
      result = await window.multiCupBLE.sendToAll(multiCupProcessedData.chunks, {
        silent: false
      });
    }

    if (result.success) {
      showToast(`✅ Successfully sent to all ${result.successful} cups in ${(result.totalElapsed / 1000).toFixed(1)}s!`, 'success');
      if (statusDiv) {
        statusDiv.textContent = `✅ Sent to ${result.successful} cups in ${(result.totalElapsed / 1000).toFixed(1)}s`;
        statusDiv.className = 'text-center text-sm text-green-600';
      }
    } else {
      showToast(`⚠️ Partial success: ${result.successful} succeeded, ${result.failed} failed`, 'warning');
      if (statusDiv) {
        statusDiv.textContent = `⚠️ ${result.successful} succeeded, ${result.failed} failed`;
        statusDiv.className = 'text-center text-sm text-yellow-600';
      }
    }
  } catch (error) {
    console.error('Failed to send to cups:', error);
    showToast(`Error sending to cups: ${error.message}`, 'error');
    if (statusDiv) {
      statusDiv.textContent = `❌ Error: ${error.message}`;
      statusDiv.className = 'text-center text-sm text-red-600';
    }
  } finally {
    if (sendBtn) {
      sendBtn.disabled = false;
      sendBtn.textContent = '🚀 Send to All Connected Cups';
    }
  }
}

// Global state
// let isConnected = false; // Removed duplicate
// let isDemoMode = false; // Removed duplicate

// ... (existing code)

/**
 * Skip connection and enter demo mode
 */
function skipConnection() {
  isDemoMode = true;
  isConnected = false; // Still technically not connected

  // Update UI
  const connectButton = document.getElementById('connectButton');
  if (connectButton) {
    connectButton.textContent = 'Connect to Device';
    connectButton.disabled = false;
  }

  updateDeviceStatus('Demo Mode (No Device)', false);
  hideConnectionPanel();
  showWelcomeMessage();

  showToast('Entered Demo Mode. You can test UI features without a device.', 'info');
}

/**
 * Rename a device at the specified position
 */
function renameDevice(position) {
  const cup = window.multiCupBLE.cups[position];
  if (!cup || !cup.connected) {
    showToast('No device connected at this position', 'warning');
    return;
  }

  const currentName = cup.deviceName || 'Unknown';

  // Populate and show modal
  const modal = document.getElementById('renameModal');
  const input = document.getElementById('renameInput');
  const posInput = document.getElementById('renamePosition');

  if (modal && input && posInput) {
    input.value = currentName;
    posInput.value = position;
    modal.classList.remove('hidden');
    input.focus();
  }
}

// Initialize modal listeners
document.addEventListener('DOMContentLoaded', () => {
  const modal = document.getElementById('renameModal');
  const saveBtn = document.getElementById('saveRenameBtn');
  const cancelBtn = document.getElementById('cancelRenameBtn');
  const input = document.getElementById('renameInput');
  const posInput = document.getElementById('renamePosition');

  if (saveBtn) {
    saveBtn.addEventListener('click', () => {
      const newName = input.value.trim();
      const position = parseInt(posInput.value);

      if (newName) {
        const cup = window.multiCupBLE.cups[position];
        if (cup) {
          window.multiCupBLE.updateFriendlyName(position, newName);
          cup.deviceName = newName;

          // Update UI
          window.ui.updateMultiCupConnectionStatus(position, true);
          showToast(`Device renamed to "${newName}"`, 'success');
        }
      }
      modal.classList.add('hidden');
    });
  }

  if (cancelBtn) {
    cancelBtn.addEventListener('click', () => {
      modal.classList.add('hidden');
    });
  }

  // Close on click outside
  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        modal.classList.add('hidden');
      }
    });
  }
});

/**
 * Forget a device at the specified position
 */
function forgetDevice(position) {
  const cup = window.multiCupBLE.cups[position];
  if (!cup || !cup.deviceId) {
    showToast('No device to forget at this position', 'warning');
    return;
  }

  const deviceName = cup.deviceName || 'this device';
  if (!confirm(`Are you sure you want to forget "${deviceName}"?\n\nYou will need to pair it again next time.`)) {
    return;
  }

  // Clear the device mapping
  window.multiCupBLE.clearDeviceMapping(position);

  // Disconnect if still connected
  if (cup.connected && cup.manager) {
    cup.manager.disconnect();
  }

  // Reset cup state
  cup.manager = null;
  cup.connected = false;
  cup.deviceId = null;
  cup.deviceName = null;
  cup.macAddress = null;
  cup.deviceIdentifier = null;

  // Update UI
  window.ui.updateMultiCupConnectionStatus(position, false);
  showToast(`Device "${deviceName}" forgotten`, 'success');
}


// Make functions globally accessible
window.processUploadedImage = processUploadedImage;
window.applyProcessedImageToEditor = applyProcessedImageToEditor;
window.connectMultiCup = connectMultiCup;
window.processMultiCupImage = processMultiCupImage;
window.sendToAllCups = sendToAllCups;
window.onMultiCupDisconnect = onMultiCupDisconnect;
window.onMultiCupReconnect = onMultiCupReconnect;
window.skipConnection = skipConnection;
window.playMultiCupAnimation = playMultiCupAnimation;
window.stopMultiCupAnimation = stopMultiCupAnimation;
window.syncMultiCupAnimation = syncMultiCupAnimation;
window.renameDevice = renameDevice;
window.forgetDevice = forgetDevice;


// Initialize panels when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  initializeFunctionPanels();

  // Add skip button listener
  const skipBtn = document.getElementById('skipButton');
  if (skipBtn) {
    skipBtn.addEventListener('click', skipConnection);
  }
});