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
  showImageEditorPanel();
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
  if (!isConnected) return;
  
  try {
    const imageData = window.imageEditor.getGridData();
    await bleManager.setImageData(imageData);
    updateImageStatus('Image sent successfully');
  } catch (error) {
    console.error('Failed to send image data:', error);
    updateImageStatus('Error sending image', true);
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

function showImageEditorPanel() {
  hideAllFunctionPanels();
  const panel = document.getElementById('imageEditorPanel');
  if (panel) {
    panel.innerHTML = `
      <h2 class="text-xl font-semibold mb-4">Monochrome Image Editor</h2>
      <div class="tool-buttons">
        <button id="drawTool" class="tool-button active" data-tool="draw">Draw</button>
        <button id="eraseTool" class="tool-button" data-tool="erase">Erase</button>
        <button id="clearTool" class="tool-button" data-tool="clear">Clear</button>
        <button id="fillTool" class="tool-button" data-tool="fill">Fill</button>
      </div>
      <div class="pixel-grid-container" style="width: 100%; height: 400px; max-height: 60vh; border: 1px solid #ccc; margin: 15px 0;">
        <div id="pixelGrid" class="pixel-grid"></div>
      </div>
      <div class="mt-4">
        <button id="sendImageBtn" class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
          Send to Cup
        </button>
      </div>
      <div id="imageStatus" class="mt-2 text-green-500 hidden"></div>
    `;
    panel.classList.remove('hidden');
    
    // Initialize the pixel grid
    initializePixelGrid();
    
    // Add event listeners for tools
    document.querySelectorAll('.tool-button').forEach(button => {
      button.addEventListener('click', () => {
        // Remove active class from all buttons
        document.querySelectorAll('.tool-button').forEach(btn => {
          btn.classList.remove('active');
        });
        // Add active class to clicked button
        button.classList.add('active');
        const selectedTool = button.dataset.tool;
        window.currentTool = selectedTool;
        
        // Handle immediate action tools
        if (selectedTool === 'clear') {
          window.imageEditor.initializeGrid();
          // Set back to draw tool after clearing
          button.classList.remove('active'); // Remove from clear button
          document.querySelector('[data-tool="draw"]').classList.add('active');
          window.currentTool = 'draw';
          window.imageEditor.setTool('draw');
        } else if (selectedTool === 'fill') {
          // Store current tool, perform fill, then switch to erase
          console.log('Fill button clicked - calling fillGrid');
          const previousTool = window.imageEditor.currentTool;
          window.imageEditor.fillGrid();
          // Set to erase tool after filling
          button.classList.remove('active'); // Remove from fill button
          document.querySelector('[data-tool="erase"]').classList.add('active');
          window.currentTool = 'erase';
          window.imageEditor.setTool('erase');
          console.log('Fill action completed, switched to erase tool');
        } else {
          // For draw and erase tools, update the imageEditor's tool
          window.imageEditor.setTool(selectedTool);
        }
      });
    });
    
    // Add event listeners for actions
    document.getElementById('sendImageBtn').addEventListener('click', () => {
      window.sendImageData();
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