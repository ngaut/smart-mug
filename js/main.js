// main.js - Main application logic

// Global variables
let isConnected = false;
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
  
  // Set up event listeners
  document.getElementById('connectButton').addEventListener('click', connectToDevice);
  
  // Set up function navigation
  document.getElementById('versionBtn').addEventListener('click', showVersionFunction);
  document.getElementById('temperatureBtn').addEventListener('click', showTemperatureFunction);
  document.getElementById('greetingBtn').addEventListener('click', showGreetingFunction);
  document.getElementById('dynamicModeBtn').addEventListener('click', showDynamicModeFunction);
  document.getElementById('imageEditorBtn').addEventListener('click', showImageEditorFunction);
  
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
  showToast('Device disconnected. Please reconnect.', 'warning');
}

// Function panel handlers
function showVersionFunction() {
  if (!isConnected) return;
  showVersionPanel();
}

function showTemperatureFunction() {
  if (!isConnected) return;
  showTemperaturePanel();
}

function showGreetingFunction() {
  if (!isConnected) return;
  showGreetingPanel();
}

function showDynamicModeFunction() {
  if (!isConnected) return;
  showDynamicModePanel();
}

function showImageEditorFunction() {
  if (!isConnected) return;
  window.ui.showImageEditorPanel();
}

// UI callback functions
async function refreshVersion() {
  if (!isConnected) return;
  
  try {
    const version = await bleManager.readVersion();
    showVersionPanel(version);
  } catch (error) {
    console.error('Failed to read version:', error);
    showVersionPanel('Error reading version');
  }
}

async function refreshTemperature() {
  if (!isConnected) return;
  
  try {
    const temperature = await bleManager.readTemperature();
    showTemperaturePanel(temperature);
  } catch (error) {
    console.error('Failed to read temperature:', error);
    showTemperaturePanel('Error');
  }
}

async function setGreetingMessage(message) {
  if (!isConnected) return;
  
  if (!message || message.trim() === '') {
    updateGreetingStatus('Please enter a message', true);
    return;
  }
  
  try {
    await bleManager.setGreetingMessage(message);
    updateGreetingStatus('Message set successfully');
  } catch (error) {
    console.error('Failed to set greeting message:', error);
    updateGreetingStatus('Error setting message', true);
  }
}

async function setDynamicMode(mode) {
  if (!isConnected) return;
  
  try {
    await bleManager.setDynamicMode(mode);
    updateModeStatus('Mode set successfully');
  } catch (error) {
    console.error('Failed to set dynamic mode:', error);
    updateModeStatus('Error setting mode', true);
  }
}

async function sendImageData() {
  if (!isConnected) {
    updateImageStatus('Not connected to device', true);
    showToast('Please connect to device first', 'warning');
    return;
  }

  // Check actual connection status
  if (!bleManager.isConnected()) {
    updateImageStatus('Device disconnected. Please reconnect.', true);
    showToast('Device disconnected. Please reconnect.', 'error');
    isConnected = false;
    handleDisconnection();
    return;
  }

  try {
    showToast('Sending image to device... This may take up to 30 seconds.', 'info');
    const imageData = window.imageEditor.getGridData();
    await bleManager.setImageData(imageData);
    updateImageStatus('Image sent successfully');
    showToast('Image sent successfully!', 'success');
  } catch (error) {
    console.error('Failed to send image data:', error);

    // Check if it's a timeout error but device might still have received it
    if (error.message.includes('timeout')) {
      updateImageStatus('Image sent (response timeout, but likely displayed on device)');
      showToast('Image sent to device (no confirmation received)', 'warning');
    } else {
      updateImageStatus(`Error: ${error.message}`, true);
      showToast(`Failed to send image: ${error.message}`, 'error');
    }

    // If disconnected, update UI
    if (!bleManager.isConnected()) {
      isConnected = false;
      handleDisconnection();
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
  const panels = ['versionPanel', 'temperaturePanel', 'greetingPanel', 'dynamicModePanel', 'imageEditorPanel'];
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
  const panels = ['versionPanel', 'temperaturePanel', 'greetingPanel', 'dynamicModePanel', 'imageEditorPanel'];
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
    { id: 'imageEditorPanel', class: 'hidden' }
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
    const autoContrast = document.getElementById('autoContrastCheckbox').checked;
    const maintainAspect = document.getElementById('maintainAspectCheckbox').checked;

    // Process image
    const result = await window.imageProcessor.processImage(file, {
      algorithm: algorithm,
      threshold: threshold,
      brightness: brightness,
      contrast: contrast,
      sharpen: sharpen,
      autoContrast: autoContrast,
      maintainAspect: maintainAspect
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

  if (!isConnected) {
    showToast('Device not connected', 'warning');
    return;
  }

  try {
    showToast(`Sending frame ${frameIndex + 1}...`, 'info');

    const frame = temporalAnimationState.frameData[frameIndex];
    const success = await window.bleManager.setImageData(frame.grid);

    if (success) {
      showToast(`Frame ${frameIndex + 1} sent successfully!`, 'success');
    } else {
      throw new Error('Failed to send frame');
    }
  } catch (error) {
    console.error('Frame send error:', error);
    showToast(`Failed to send frame ${frameIndex + 1}: ${error.message}`, 'error');
  }
}

// Device Animation State
let deviceAnimationState = {
  isRunning: false,
  currentFrame: 0,
  intervalId: null,
  startTime: null,
  frameStartTime: null
};

async function sendAnimationToDevice() {
  if (!temporalAnimationState.frameData) {
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

  // Show stop button, hide send button
  document.getElementById('sendAnimationBtn').classList.add('hidden');
  document.getElementById('stopAnimationBtn').classList.remove('hidden');

  // Show progress display
  document.getElementById('deviceAnimationProgress').classList.remove('hidden');

  deviceAnimationState.isRunning = true;
  deviceAnimationState.currentFrame = 0;
  deviceAnimationState.startTime = Date.now();

  showToast('Starting animation on device... (this may take time)', 'info');

  // Function to send next frame in sequence
  const sendNextFrame = async () => {
    if (!deviceAnimationState.isRunning) return;

    try {
      const frame = temporalAnimationState.frameData[deviceAnimationState.currentFrame];

      console.log(`Sending frame ${deviceAnimationState.currentFrame + 1}/${temporalAnimationState.frameData.length} to device...`);

      // Update progress display
      deviceAnimationState.frameStartTime = Date.now();
      const totalElapsed = Math.floor((deviceAnimationState.frameStartTime - deviceAnimationState.startTime) / 1000);
      document.getElementById('deviceAnimationStatus').textContent =
        `Sending Frame ${deviceAnimationState.currentFrame + 1}/${temporalAnimationState.frameData.length} (Total elapsed: ${totalElapsed}s)`;

      // Send frame to device
      const success = await window.bleManager.setImageData(frame.grid);

      if (!success) {
        throw new Error('Failed to send frame');
      }

      // Show completion for this frame
      const frameElapsed = Math.floor((Date.now() - deviceAnimationState.frameStartTime) / 1000);
      console.log(`Frame ${deviceAnimationState.currentFrame + 1} sent successfully in ${frameElapsed}s`);

      // Move to next frame
      deviceAnimationState.currentFrame =
        (deviceAnimationState.currentFrame + 1) % temporalAnimationState.frameData.length;

      // Schedule next frame
      if (deviceAnimationState.isRunning) {
        // Add delay to let device actually display the frame
        // Device needs time to process and show the image before receiving next frame
        // Using 2-3 second delay to ensure visible frame changes
        const displayDelay = 2000; // 2 seconds display time per frame
        console.log(`Waiting ${displayDelay}ms before sending next frame...`);
        document.getElementById('deviceAnimationStatus').textContent =
          `Frame ${deviceAnimationState.currentFrame}/${temporalAnimationState.frameData.length} displayed (waiting ${displayDelay/1000}s before next)`;
        deviceAnimationState.intervalId = setTimeout(sendNextFrame, displayDelay);
      }
    } catch (error) {
      console.error('Animation send error:', error);
      showToast(`Animation error: ${error.message}`, 'error');
      stopAnimationToDevice();
    }
  };

  // Start the animation loop
  sendNextFrame();

  showToast('Animation loop started! Cycling frames on device...', 'success');
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

// Make functions globally accessible
window.processUploadedImage = processUploadedImage;
window.applyProcessedImageToEditor = applyProcessedImageToEditor;