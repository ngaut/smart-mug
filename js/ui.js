// ui.js - User interface components

function showConnectionPanel() {
  document.getElementById("connectionPanel").classList.remove("hidden");
  document.getElementById("mainContent").classList.add("hidden");
}

function hideConnectionPanel() {
  document.getElementById("connectionPanel").classList.add("hidden");
  document.getElementById("mainContent").classList.remove("hidden");
}

function updateDeviceStatus(status, isError = false) {
  const statusElement = document.getElementById("deviceStatus");
  const errorElement = document.getElementById("errorMessage");

  if (isError) {
    statusElement.textContent = "Error";
    statusElement.className = "text-red-500";
    errorElement.textContent = status;
    errorElement.classList.remove("hidden");
  } else {
    statusElement.textContent = status;
    statusElement.className =
      status === "Connected" ? "text-green-500" : "text-gray-600";
    errorElement.classList.add("hidden");
  }
}

function showWelcomeMessage() {
  document.getElementById("welcomeMessage").classList.remove("hidden");
  // Hide all function panels
  const panels = [
    "versionPanel",
    "temperaturePanel",
    "greetingPanel",
    "dynamicModePanel",
    "imageEditorPanel",
  ];
  panels.forEach((panel) => {
    const element = document.getElementById(panel);
    if (element) element.classList.add("hidden");
  });
}

function showVersionPanel(version) {
  hideAllFunctionPanels();
  const panel = document.getElementById("versionPanel");
  if (panel) {
    panel.innerHTML = `
      <h2 class="text-xl font-semibold mb-4">Version Information</h2>
      <div class="version-info">${version}</div>
      <button id="refreshVersionBtn" class="mt-4 bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
        Refresh
      </button>
    `;
    panel.classList.remove("hidden");

    // Add event listener for refresh button
    document
      .getElementById("refreshVersionBtn")
      .addEventListener("click", () => {
        window.refreshVersion();
      });
  }
}

function showTemperaturePanel(temperature) {
  hideAllFunctionPanels();
  const panel = document.getElementById("temperaturePanel");
  if (panel) {
    panel.innerHTML = `
      <h2 class="text-xl font-semibold mb-4">Temperature Reading</h2>
      <div class="temperature-display">${temperature}°C</div>
      <button id="refreshTempBtn" class="mt-4 bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
        Refresh
      </button>
    `;
    panel.classList.remove("hidden");

    // Add event listener for refresh button
    document.getElementById("refreshTempBtn").addEventListener("click", () => {
      window.refreshTemperature();
    });
  }
}

function showGreetingPanel() {
  hideAllFunctionPanels();
  const panel = document.getElementById("greetingPanel");
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
    panel.classList.remove("hidden");

    // Add event listener for set button
    document.getElementById("setGreetingBtn").addEventListener("click", () => {
      const message = document.getElementById("greetingInput").value;
      window.setGreetingMessage(message);
    });
  }
}

function showDynamicModePanel() {
  hideAllFunctionPanels();
  const panel = document.getElementById("dynamicModePanel");
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
    panel.classList.remove("hidden");

    // Add event listener for set button
    document.getElementById("setModeBtn").addEventListener("click", () => {
      const selectedMode = document.querySelector(
        'input[name="mode"]:checked'
      ).value;
      window.setDynamicMode(selectedMode);
    });
  }
}

function showImageEditorPanel() {
  hideAllFunctionPanels();
  const panel = document.getElementById("imageEditorPanel");
  if (panel) {
    panel.innerHTML = `
      <h2 class="text-xl font-semibold mb-4">Monochrome Image Editor</h2>

      <!-- Image Upload Section -->
      <div class="bg-gray-50 p-4 rounded-lg mb-4 border-2 border-dashed border-gray-300">
        <h3 class="text-lg font-medium mb-3">Upload Image</h3>
        <div class="mb-3">
          <input type="file" id="imageFileInput" accept="image/*" class="block w-full text-sm text-gray-500
            file:mr-4 file:py-2 file:px-4
            file:rounded file:border-0
            file:text-sm file:font-semibold
            file:bg-blue-500 file:text-white
            hover:file:bg-blue-600
            file:cursor-pointer cursor-pointer">
        </div>

        <!-- Processing Options -->
        <div class="space-y-3 mb-3">
          <!-- Algorithm Selection -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Dithering Algorithm</label>
            <select id="algorithmSelect" class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm">
              <optgroup label="🎬 Temporal (Animated - Recommended!)">
                <option value="temporal">Temporal PWM (4 frames, smooth)</option>
                <option value="temporal-spatial">Temporal + Floyd-Steinberg (higher quality)</option>
              </optgroup>
              <optgroup label="📸 Spatial (Single Frame)">
                <option value="floyd-steinberg" selected>Floyd-Steinberg (Best for photos)</option>
                <option value="atkinson">Atkinson (Cleaner, less noise)</option>
                <option value="ordered">Ordered/Bayer (Pattern-based)</option>
                <option value="threshold">Simple Threshold (Fast)</option>
              </optgroup>
            </select>
          </div>

          <!-- Preprocessing Options -->
          <div class="border-t pt-3">
            <div class="flex items-center justify-between mb-2">
              <label class="text-sm font-medium text-gray-700">Enhancement</label>
              <input type="checkbox" id="autoContrastCheckbox" class="mr-1">
              <label for="autoContrastCheckbox" class="text-xs text-gray-600">Auto-Contrast</label>
            </div>

            <!-- Brightness -->
            <div class="mb-2">
              <label class="block text-xs text-gray-600 mb-1">Brightness: <span id="brightnessValue">0</span></label>
              <input type="range" id="brightnessSlider" min="-100" max="100" value="0" class="w-full h-2">
            </div>

            <!-- Contrast -->
            <div class="mb-2">
              <label class="block text-xs text-gray-600 mb-1">Contrast: <span id="contrastValue">0</span></label>
              <input type="range" id="contrastSlider" min="-100" max="100" value="0" class="w-full h-2">
            </div>

            <!-- Sharpening -->
            <div class="mb-2">
              <label class="block text-xs text-gray-600 mb-1">Sharpening: <span id="sharpenValue">0</span></label>
              <input type="range" id="sharpenSlider" min="0" max="2" step="0.1" value="0" class="w-full h-2">
            </div>

            <!-- Threshold -->
            <div>
              <label class="block text-xs text-gray-600 mb-1">Threshold: <span id="thresholdValue">128</span></label>
              <input type="range" id="thresholdSlider" min="0" max="255" value="128" class="w-full h-2">
            </div>
          </div>

          <div class="flex items-center">
            <input type="checkbox" id="maintainAspectCheckbox" checked class="mr-2">
            <label for="maintainAspectCheckbox" class="text-sm text-gray-700">Maintain aspect ratio</label>
          </div>
        </div>

        <button id="processImageBtn" disabled class="w-full bg-green-500 hover:bg-green-600 disabled:bg-gray-300 disabled:cursor-not-allowed text-white font-semibold py-2 px-4 rounded">
          Process & Preview
        </button>
      </div>

      <!-- Preview Section -->
      <div id="previewSection" class="bg-white p-4 rounded-lg mb-4 border border-gray-200 hidden">
        <h3 class="text-lg font-medium mb-3">Preview</h3>

        <!-- Image Analysis -->
        <div id="imageAnalysis" class="mb-3 p-3 bg-gray-50 rounded text-sm">
          <div class="font-medium mb-1">Image Quality</div>
          <div id="analysisStats" class="text-xs text-gray-600 mb-2"></div>
          <div id="analysisSuggestions" class="space-y-1"></div>
        </div>

        <div class="flex justify-center gap-4">
          <div>
            <p class="text-sm text-gray-600 mb-2 text-center">Original (resized)</p>
            <canvas id="originalPreview" class="border border-gray-300" width="192" height="48"></canvas>
          </div>
          <div>
            <p class="text-sm text-gray-600 mb-2 text-center">Processed (48×12)</p>
            <canvas id="processedPreview" class="border border-gray-300" width="384" height="96"></canvas>
          </div>
        </div>

        <!-- Temporal Animation Controls (shown only for temporal algorithms) -->
        <div id="temporalControls" class="hidden mt-4 p-3 bg-blue-50 rounded border border-blue-200">
          <div class="flex items-center justify-between mb-3">
            <h4 class="text-sm font-semibold text-gray-700">🎬 Temporal Animation</h4>
            <div class="text-xs text-gray-600">
              <span id="currentFrameDisplay">Frame 1/4</span>
            </div>
          </div>

          <!-- Warning Banner -->
          <div class="mb-3 p-2 bg-yellow-100 border border-yellow-300 rounded text-xs">
            <div class="font-semibold text-yellow-800 mb-1">⚠️ Device Speed Limitation</div>
            <div class="text-yellow-700">
              Each frame takes 15-30s to transfer via BLE. Device animation will be VERY slow (~1 frame per 20s).
              <strong>Browser preview shows ideal result.</strong> Consider sending your best single frame instead.
            </div>
          </div>

          <!-- Animation Control Buttons -->
          <div class="flex gap-2 mb-3">
            <button id="playAnimationBtn" class="flex-1 bg-green-500 hover:bg-green-600 text-white font-semibold py-2 px-3 rounded text-sm">
              ▶ Play Animation
            </button>
            <button id="pauseAnimationBtn" class="flex-1 bg-yellow-500 hover:bg-yellow-600 text-white font-semibold py-2 px-3 rounded text-sm hidden">
              ⏸ Pause
            </button>
          </div>

          <!-- Frame Rate Control -->
          <div class="mb-3">
            <label class="block text-xs text-gray-600 mb-1">Frame Rate: <span id="fpsValue">20</span> FPS</label>
            <input type="range" id="fpsSlider" min="5" max="60" value="20" class="w-full h-2">
          </div>

          <!-- Individual Frame Selection -->
          <div class="mb-3">
            <label class="block text-xs text-gray-600 mb-2">Select Individual Frame:</label>
            <div id="frameButtons" class="flex gap-2">
              <!-- Dynamically populated with frame buttons -->
            </div>
          </div>

          <!-- Send Frame Buttons -->
          <div class="border-t pt-3">
            <label class="block text-xs text-gray-600 mb-2">Send to Device:</label>

            <!-- Device Animation Speed Control -->
            <div class="mb-3">
              <label class="block text-xs text-gray-600 mb-1">Device Frame Delay: <span id="deviceDelayValue">50</span>ms</label>
              <input type="range" id="deviceDelaySlider" min="0" max="2000" step="50" value="50" class="w-full h-2">
              <div class="text-xs text-gray-500 mt-1">Lower = faster animation, higher = more visible frames</div>
            </div>

            <!-- Send Animation Button -->
            <button id="sendAnimationBtn" class="w-full mb-2 bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white font-semibold py-2 px-4 rounded">
              🎬 Send Animation to Device (Loop)
            </button>
            <button id="stopAnimationBtn" class="w-full mb-2 bg-red-500 hover:bg-red-600 text-white font-semibold py-2 px-4 rounded hidden">
              ⏹ Stop Animation
            </button>

            <!-- Progress Display -->
            <div id="deviceAnimationProgress" class="hidden mb-3 p-2 bg-purple-100 border border-purple-300 rounded text-xs">
              <div class="font-semibold text-purple-800 mb-1">Sending to Device...</div>
              <div id="deviceAnimationStatus" class="text-purple-700">
                Frame 1/4 (Elapsed: 0s)
              </div>
            </div>

            <!-- Individual Frame Buttons -->
            <label class="block text-xs text-gray-600 mb-2">Or Send Individual Frames:</label>
            <div id="sendFrameButtons" class="grid grid-cols-2 gap-2">
              <!-- Dynamically populated with send buttons -->
            </div>
          </div>
        </div>

        <button id="applyToEditorBtn" class="w-full mt-3 bg-purple-500 hover:bg-purple-600 text-white font-semibold py-2 px-4 rounded">
          Apply to Editor
        </button>
      </div>

      <!-- Manual Editor Section -->
      <div class="bg-white p-4 rounded-lg mb-4 border border-gray-200">
        <h3 class="text-lg font-medium mb-3">Manual Drawing Tools</h3>
        <div class="tool-buttons">
          <button id="drawTool" class="tool-button active" data-tool="draw">Draw</button>
          <button id="eraseTool" class="tool-button" data-tool="erase">Erase</button>
          <button id="clearTool" class="tool-button" data-tool="clear">Clear</button>
          <button id="fillTool" class="tool-button" data-tool="fill">Fill</button>
        </div>
        <div class="pixel-grid-container">
          <div id="pixelGrid" class="pixel-grid"></div>
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="flex gap-2">
        <button id="sendImageBtn" class="flex-1 bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
          Send to Cup
        </button>
        <button id="resetImageBtn" class="bg-gray-500 hover:bg-gray-700 text-white font-bold py-2 px-4 rounded">
          Reset
        </button>
      </div>
      <div id="imageStatus" class="mt-2 text-green-500 hidden"></div>
    `;
    panel.classList.remove("hidden");

    // Initialize the pixel grid
    initializePixelGrid();

    // Add event listeners for tools
    document.querySelectorAll(".tool-button").forEach((button) => {
      button.addEventListener("click", () => {
        // Remove active class from all buttons
        document.querySelectorAll(".tool-button").forEach((btn) => {
          btn.classList.remove("active");
        });
        // Add active class to clicked button
        button.classList.add("active");
        const tool = button.dataset.tool;
        window.currentTool = tool;
        // Sync with imageEditor
        if (window.imageEditor) {
          window.imageEditor.setTool(tool);
        }
      });
    });

    // Add event listeners for image upload
    const fileInput = document.getElementById("imageFileInput");
    const processBtn = document.getElementById("processImageBtn");

    // Slider elements
    const thresholdSlider = document.getElementById("thresholdSlider");
    const thresholdValue = document.getElementById("thresholdValue");
    const brightnessSlider = document.getElementById("brightnessSlider");
    const brightnessValue = document.getElementById("brightnessValue");
    const contrastSlider = document.getElementById("contrastSlider");
    const contrastValue = document.getElementById("contrastValue");
    const sharpenSlider = document.getElementById("sharpenSlider");
    const sharpenValue = document.getElementById("sharpenValue");

    fileInput.addEventListener("change", (e) => {
      processBtn.disabled = !e.target.files.length;
    });

    // Update slider value displays
    thresholdSlider.addEventListener("input", (e) => {
      thresholdValue.textContent = e.target.value;
    });

    brightnessSlider.addEventListener("input", (e) => {
      brightnessValue.textContent = e.target.value;
    });

    contrastSlider.addEventListener("input", (e) => {
      contrastValue.textContent = e.target.value;
    });

    sharpenSlider.addEventListener("input", (e) => {
      sharpenValue.textContent = parseFloat(e.target.value).toFixed(1);
    });

    processBtn.addEventListener("click", () => {
      window.processUploadedImage();
    });

    document.getElementById("applyToEditorBtn")?.addEventListener("click", () => {
      window.applyProcessedImageToEditor();
    });

    // Add event listeners for actions
    document.getElementById("sendImageBtn").addEventListener("click", () => {
      window.sendImageData();
    });

    document.getElementById("resetImageBtn").addEventListener("click", () => {
      window.resetImage();
    });
  }
}

function showMultiCupPanel() {
  hideAllFunctionPanels();
  const panel = document.getElementById("multiCupPanel");
  if (panel) {
    panel.innerHTML = `
      <h2 class="text-2xl font-semibold mb-4">🖼️ Multi-Cup Display System</h2>
      <p class="text-gray-600 mb-6">Connect 4 cups to create larger displays! (48×48 for portraits, 96×24 for landscapes)</p>

      <!-- Layout Configuration -->
      <div class="bg-blue-50 p-4 rounded-lg mb-6 border border-blue-200">
        <h3 class="text-lg font-medium mb-3">📐 Display Layout</h3>
        <p class="text-xs text-gray-600 mb-3">Choose based on your image type</p>
        <div class="space-y-2">
          <label class="flex items-start cursor-pointer hover:bg-blue-100 p-3 rounded border-2 border-blue-300">
            <input type="radio" name="layout" value="vertical_4x1" checked class="mr-3 mt-1">
            <div>
              <div class="text-sm font-semibold">⭐ Portrait Square (48×48)</div>
              <div class="text-xs text-gray-600">Best for faces, portraits, profile pictures</div>
            </div>
          </label>
          <label class="flex items-start cursor-pointer hover:bg-blue-100 p-3 rounded">
            <input type="radio" name="layout" value="grid_2x2" class="mr-3 mt-1">
            <div>
              <div class="text-sm font-semibold">📺 Landscape Wide (96×24)</div>
              <div class="text-xs text-gray-600">Panoramas, text banners, logos, wide images</div>
            </div>
          </label>
        </div>
      </div>

      <!-- Gap Compensation -->
      <div class="bg-yellow-50 p-4 rounded-lg mb-6 border border-yellow-200">
        <h3 class="text-lg font-medium mb-2">🔧 Physical Gap Compensation</h3>
        <p class="text-xs text-gray-600 mb-3">Adjust for physical spacing between your cups (bezels/frames)</p>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              Horizontal Gap: <span id="gapHValue" class="font-mono text-blue-600">0</span>px
            </label>
            <input type="range" id="gapHSlider" min="0" max="20" value="0"
              class="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer">
            <div class="flex justify-between text-xs text-gray-500 mt-1">
              <span>0px (seamless)</span>
              <span>20px</span>
            </div>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              Vertical Gap: <span id="gapVValue" class="font-mono text-blue-600">0</span>px
            </label>
            <input type="range" id="gapVSlider" min="0" max="10" value="0"
              class="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer">
            <div class="flex justify-between text-xs text-gray-500 mt-1">
              <span>0px (seamless)</span>
              <span>10px</span>
            </div>
          </div>
        </div>
        <p class="text-xs text-gray-500 mt-2">💡 Tip: Adjust these values until images line up across cup boundaries</p>
      </div>

      <!-- Cup Connection Grid -->
      <div class="bg-white p-4 rounded-lg mb-6 border border-gray-200">
        <h3 class="text-lg font-medium mb-4">Cup Connections</h3>
        <div id="cupGrid" class="grid grid-cols-2 gap-4 mb-4">
          <!-- Cup 0: Top-Left -->
          <div class="border-2 border-gray-300 rounded-lg p-4">
            <div class="flex items-center justify-between mb-2">
              <span class="font-semibold">Cup 0 (Top-Left)</span>
              <span id="cup0Status" class="text-xs px-2 py-1 rounded bg-gray-200 text-gray-600">Not Connected</span>
            </div>
            <div id="cup0DeviceInfo" class="hidden"></div>
            <button id="connectCup0Btn" class="w-full bg-blue-500 hover:bg-blue-600 text-white font-semibold py-2 px-3 rounded text-sm">
              Connect
            </button>
          </div>

          <!-- Cup 1: Top-Right -->
          <div class="border-2 border-gray-300 rounded-lg p-4">
            <div class="flex items-center justify-between mb-2">
              <span class="font-semibold">Cup 1 (Top-Right)</span>
              <span id="cup1Status" class="text-xs px-2 py-1 rounded bg-gray-200 text-gray-600">Not Connected</span>
            </div>
            <div id="cup1DeviceInfo" class="hidden"></div>
            <button id="connectCup1Btn" class="w-full bg-blue-500 hover:bg-blue-600 text-white font-semibold py-2 px-3 rounded text-sm">
              Connect
            </button>
          </div>

          <!-- Cup 2: Bottom-Left -->
          <div class="border-2 border-gray-300 rounded-lg p-4">
            <div class="flex items-center justify-between mb-2">
              <span class="font-semibold">Cup 2 (Bottom-Left)</span>
              <span id="cup2Status" class="text-xs px-2 py-1 rounded bg-gray-200 text-gray-600">Not Connected</span>
            </div>
            <div id="cup2DeviceInfo" class="hidden"></div>
            <button id="connectCup2Btn" class="w-full bg-blue-500 hover:bg-blue-600 text-white font-semibold py-2 px-3 rounded text-sm">
              Connect
            </button>
          </div>

          <!-- Cup 3: Bottom-Right -->
          <div class="border-2 border-gray-300 rounded-lg p-4">
            <div class="flex items-center justify-between mb-2">
              <span class="font-semibold">Cup 3 (Bottom-Right)</span>
              <span id="cup3Status" class="text-xs px-2 py-1 rounded bg-gray-200 text-gray-600">Not Connected</span>
            </div>
            <div id="cup3DeviceInfo" class="hidden"></div>
            <button id="connectCup3Btn" class="w-full bg-blue-500 hover:bg-blue-600 text-white font-semibold py-2 px-3 rounded text-sm">
              Connect
            </button>
          </div>
        </div>
        <div id="connectionSummary" class="text-sm text-gray-600">
          Connected: <span id="connectedCount" class="font-semibold">0</span>/4
        </div>
      </div>

      <!-- Image Upload Section -->
      <div class="bg-gray-50 p-4 rounded-lg mb-6 border-2 border-dashed border-gray-300">
        <h3 class="text-lg font-medium mb-3">Upload Large Image</h3>
        <div class="mb-3">
          <input type="file" id="multiCupImageInput" accept="image/*" class="block w-full text-sm text-gray-500
            file:mr-4 file:py-2 file:px-4
            file:rounded file:border-0
            file:text-sm file:font-semibold
            file:bg-blue-500 file:text-white
            hover:file:bg-blue-600
            file:cursor-pointer cursor-pointer">
        </div>

        <!-- Processing Options (simplified) -->
        <div class="space-y-3 mb-3">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Algorithm</label>
            <select id="multiCupAlgorithm" class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm">
              <option value="floyd-steinberg">Floyd-Steinberg (Best for photos)</option>
              <option value="atkinson">Atkinson (Cleaner)</option>
              <option value="ordered">Ordered/Bayer</option>
              <option value="threshold">Simple Threshold</option>
            </select>
          </div>
        </div>

        <button id="processMultiCupImageBtn" disabled class="w-full bg-green-500 hover:bg-green-600 disabled:bg-gray-300 disabled:cursor-not-allowed text-white font-semibold py-2 px-4 rounded">
          Process & Preview
        </button>
      </div>

      <!-- Split Preview Section -->
      <div id="multiCupPreviewSection" class="bg-white p-4 rounded-lg mb-6 border border-gray-200 hidden">
        <h3 class="text-lg font-medium mb-3">Split Preview</h3>
        <p class="text-sm text-gray-600 mb-3">Image divided into 4 chunks (one per cup):</p>

        <div class="mb-4">
          <p class="text-xs text-gray-500 mb-2">Composite View:</p>
          <div class="flex justify-center mb-4">
            <canvas id="compositePreview" class="border-2 border-gray-400"></canvas>
          </div>
        </div>

        <div class="mb-4">
          <p class="text-xs text-gray-500 mb-2">Individual Cup Views:</p>
          <div class="grid grid-cols-2 gap-3">
            <div class="border border-gray-300 rounded p-2">
              <p class="text-xs text-center mb-1">Cup 0 (Top-Left)</p>
              <canvas id="cup0Preview" class="border border-gray-200 mx-auto"></canvas>
            </div>
            <div class="border border-gray-300 rounded p-2">
              <p class="text-xs text-center mb-1">Cup 1 (Top-Right)</p>
              <canvas id="cup1Preview" class="border border-gray-200 mx-auto"></canvas>
            </div>
            <div class="border border-gray-300 rounded p-2">
              <p class="text-xs text-center mb-1">Cup 2 (Bottom-Left)</p>
              <canvas id="cup2Preview" class="border border-gray-200 mx-auto"></canvas>
            </div>
            <div class="border border-gray-300 rounded p-2">
              <p class="text-xs text-center mb-1">Cup 3 (Bottom-Right)</p>
              <canvas id="cup3Preview" class="border border-gray-200 mx-auto"></canvas>
            </div>
          </div>
        </div>
      </div>

      <!-- Send Section -->
      <div id="multiCupSendSection" class="hidden">
        <button id="sendToAllCupsBtn" class="w-full bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white font-bold py-3 px-6 rounded-lg text-lg mb-3">
          🚀 Send to All Connected Cups
        </button>
        <div id="multiCupSendStatus" class="text-center text-sm text-gray-600 hidden"></div>
      </div>
    `;
    panel.classList.remove("hidden");

    // Set up event listeners
    setupMultiCupEventListeners();
  }
}

function hideAllFunctionPanels() {
  document.getElementById("welcomeMessage").classList.add("hidden");
  const panels = [
    "versionPanel",
    "temperaturePanel",
    "greetingPanel",
    "dynamicModePanel",
    "imageEditorPanel",
    "multiCupPanel",
  ];
  panels.forEach((panel) => {
    const element = document.getElementById(panel);
    if (element) element.classList.add("hidden");
  });
}

function initializePixelGrid() {
  const grid = document.getElementById("pixelGrid");
  grid.innerHTML = "";

  // Create 48x12 grid (576 pixels)
  for (let row = 0; row < 12; row++) {
    for (let col = 0; col < 48; col++) {
      const pixel = document.createElement("div");
      pixel.className = "pixel";
      pixel.dataset.row = row;
      pixel.dataset.col = col;
      pixel.style.cursor = "pointer";
      
      // Add event listeners for drawing
      pixel.addEventListener("mousedown", (e) => {
        e.preventDefault();
        window.startDrawing(row, col);
      });
      pixel.addEventListener("mouseenter", () => {
        window.continueDrawing(row, col);
      });
      pixel.addEventListener("click", () => {
        window.startDrawing(row, col);
        window.stopDrawing();
      });
      
      grid.appendChild(pixel);
    }
  }

  // Add mouseup event to the grid to stop drawing
  grid.addEventListener("mouseup", () => window.stopDrawing());
  grid.addEventListener("mouseleave", () => window.stopDrawing());
}

function updateGreetingStatus(message, isError = false) {
  const statusElement = document.getElementById("greetingStatus");
  if (statusElement) {
    statusElement.textContent = message;
    statusElement.className = isError
      ? "mt-2 text-red-500"
      : "mt-2 text-green-500";
    statusElement.classList.remove("hidden");
  }
}

function updateModeStatus(message, isError = false) {
  const statusElement = document.getElementById("modeStatus");
  if (statusElement) {
    statusElement.textContent = message;
    statusElement.className = isError
      ? "mt-2 text-red-500"
      : "mt-2 text-green-500";
    statusElement.classList.remove("hidden");
  }
}

function updateImageStatus(message, isError = false) {
  const statusElement = document.getElementById("imageStatus");
  if (statusElement) {
    statusElement.textContent = message;
    statusElement.className = isError
      ? "mt-2 text-red-500"
      : "mt-2 text-green-500";
    statusElement.classList.remove("hidden");
  }
}

function showToast(message, type = "info") {
  // Create toast container if it doesn't exist
  let toastContainer = document.getElementById("toastContainer");
  if (!toastContainer) {
    toastContainer = document.createElement("div");
    toastContainer.id = "toastContainer";
    toastContainer.className = "fixed top-4 right-4 z-50 space-y-2";
    document.body.appendChild(toastContainer);
  }

  // Create toast element
  const toast = document.createElement("div");

  // Set toast classes based on type
  const baseClasses =
    "px-4 py-3 rounded-lg shadow-lg text-white font-medium transition-all duration-300 transform translate-x-full";
  const typeClasses = {
    info: "bg-blue-500",
    success: "bg-green-500",
    warning: "bg-yellow-500",
    error: "bg-red-500",
  };

  toast.className = `${baseClasses} ${
    typeClasses[type] || typeClasses["info"]
  }`;
  toast.textContent = message;

  // Add toast to container
  toastContainer.appendChild(toast);

  // Animate in
  setTimeout(() => {
    toast.classList.remove("translate-x-full");
    toast.classList.add("translate-x-0");
  }, 10);

  // Remove toast after 3 seconds
  setTimeout(() => {
    toast.classList.remove("translate-x-0");
    toast.classList.add("translate-x-full");
    setTimeout(() => {
      if (toast.parentNode) {
        toast.parentNode.removeChild(toast);
      }
    }, 300);
  }, 3000);
}

// Setup event listeners for multi-cup panel
function setupMultiCupEventListeners() {
  // Layout change handlers
  const layoutRadios = document.querySelectorAll('input[name="layout"]');
  layoutRadios.forEach(radio => {
    radio.addEventListener('change', (e) => {
      const layout = e.target.value;
      window.multiCupBLE.setLayout(layout);
      window.imageSplitter.setLayout(layout);
      showToast(`Layout changed to: ${layout}`, 'info');
    });
  });

  // Gap compensation handlers
  const gapHSlider = document.getElementById('gapHSlider');
  const gapVSlider = document.getElementById('gapVSlider');
  const gapHValue = document.getElementById('gapHValue');
  const gapVValue = document.getElementById('gapVValue');

  if (gapHSlider && gapVSlider) {
    gapHSlider.addEventListener('input', (e) => {
      const value = parseInt(e.target.value);
      gapHValue.textContent = value;
      window.imageSplitter.setGaps(value, parseInt(gapVSlider.value));
    });

    gapVSlider.addEventListener('input', (e) => {
      const value = parseInt(e.target.value);
      gapVValue.textContent = value;
      window.imageSplitter.setGaps(parseInt(gapHSlider.value), value);
    });
  }

  // Cup connection handlers
  for (let i = 0; i < 4; i++) {
    const btn = document.getElementById(`connectCup${i}Btn`);
    if (btn) {
      btn.addEventListener('click', () => window.connectMultiCup(i));
    }
  }

  // Image upload handler
  const fileInput = document.getElementById('multiCupImageInput');
  const processBtn = document.getElementById('processMultiCupImageBtn');

  if (fileInput) {
    fileInput.addEventListener('change', (e) => {
      processBtn.disabled = !e.target.files.length;
    });
  }

  if (processBtn) {
    processBtn.addEventListener('click', () => window.processMultiCupImage());
  }

  // Send to all cups handler
  const sendBtn = document.getElementById('sendToAllCupsBtn');
  if (sendBtn) {
    sendBtn.addEventListener('click', () => window.sendToAllCups());
  }
}

// Update multi-cup connection status display
function updateMultiCupConnectionStatus(position, connected) {
  const statusElement = document.getElementById(`cup${position}Status`);
  const deviceInfoElement = document.getElementById(`cup${position}DeviceInfo`);
  const btnElement = document.getElementById(`connectCup${position}Btn`);

  if (statusElement) {
    if (connected) {
      statusElement.textContent = 'Connected';
      statusElement.className = 'text-xs px-2 py-1 rounded bg-green-100 text-green-700';
    } else {
      statusElement.textContent = 'Not Connected';
      statusElement.className = 'text-xs px-2 py-1 rounded bg-gray-200 text-gray-600';
    }
  }

  // Update device info
  if (deviceInfoElement) {
    if (connected) {
      const cup = window.multiCupBLE.cups[position];
      const deviceName = cup.deviceName || 'Unknown';
      const deviceIdBase64 = cup.deviceId || 'Unknown';

      // Decode base64 device ID to hex for readability
      let deviceIdHex = deviceIdBase64;
      try {
        // Decode base64 to binary
        const binaryString = atob(deviceIdBase64);
        // Convert to hex
        const hexArray = [];
        for (let i = 0; i < binaryString.length; i++) {
          const hex = binaryString.charCodeAt(i).toString(16).padStart(2, '0');
          hexArray.push(hex);
        }
        deviceIdHex = hexArray.join(':').toUpperCase();
      } catch (e) {
        // If decoding fails, use original
        deviceIdHex = deviceIdBase64;
      }

      // Escape HTML to prevent XSS
      const escapeHtml = (str) => {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
      };

      deviceInfoElement.innerHTML = `
        <div class="text-xs text-gray-600 mt-1 mb-2">
          <div><strong>Name:</strong> ${escapeHtml(deviceName)}</div>
          <div class="break-all"><strong>ID:</strong> <code class="text-xs bg-gray-100 px-1 rounded font-mono">${escapeHtml(deviceIdHex)}</code></div>
        </div>
      `;
      deviceInfoElement.classList.remove('hidden');
    } else {
      deviceInfoElement.innerHTML = '';
      deviceInfoElement.classList.add('hidden');
    }
  }

  if (btnElement) {
    if (connected) {
      btnElement.textContent = 'Disconnect';
      btnElement.className = 'w-full bg-red-500 hover:bg-red-600 text-white font-semibold py-2 px-3 rounded text-sm';
    } else {
      btnElement.textContent = 'Connect';
      btnElement.className = 'w-full bg-blue-500 hover:bg-blue-600 text-white font-semibold py-2 px-3 rounded text-sm';
    }
  }

  // Update connection count
  const status = window.multiCupBLE.getConnectionStatus();
  const countElement = document.getElementById('connectedCount');
  if (countElement) {
    countElement.textContent = status.connected;
  }
}

// Make functions available globally
window.ui = {
  showConnectionPanel,
  hideConnectionPanel,
  updateDeviceStatus,
  showWelcomeMessage,
  showVersionPanel,
  showTemperaturePanel,
  showGreetingPanel,
  showDynamicModePanel,
  showImageEditorPanel,
  showMultiCupPanel,
  updateMultiCupConnectionStatus,
  updateGreetingStatus,
  updateModeStatus,
  updateImageStatus,
};
