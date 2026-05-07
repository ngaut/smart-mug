// ui.js - User interface components


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
      <h2 class="text-xl font-semibold mb-4">Set Display</h2>

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

            <!-- Gamma -->
            <div class="mb-2">
              <label class="block text-xs text-gray-600 mb-1">Gamma: <span id="gammaValue">1.0</span></label>
              <input type="range" id="gammaSlider" min="0.1" max="3.0" step="0.1" value="1.0" class="w-full h-2">
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

          <div class="flex items-center justify-between mb-2">
            <div class="flex items-center">
              <label class="text-sm font-medium text-gray-700 mr-2">Fit Mode:</label>
              <select id="fitModeSelect" class="text-sm border border-gray-300 rounded px-2 py-1">
                <option value="contain">Contain (Letterbox)</option>
                <option value="cover" selected>Cover (Fill)</option>
              </select>
            </div>
            <div class="flex items-center">
              <input type="checkbox" id="maintainAspectCheckbox" checked class="mr-2">
              <label for="maintainAspectCheckbox" class="text-sm text-gray-700">Maintain aspect</label>
            </div>
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

        <div class="flex justify-center items-center gap-6 flex-wrap">
          <div>
            <p class="text-sm text-gray-600 mb-2 text-center">Original (resized)</p>
            <canvas id="originalPreview" class="border border-gray-300" width="192" height="48"></canvas>
          </div>
          <div>
            <p class="text-sm text-gray-600 mb-2 text-center">On the cup</p>
            <div class="cup-container">
              <div class="cup-screen-overlay">
                <canvas id="processedPreview" width="384" height="96"></canvas>
              </div>
            </div>
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

          <!-- Info Banner -->
          <div class="mb-3 p-2 bg-blue-50 border border-blue-200 rounded text-xs">
            <div class="font-semibold text-blue-800 mb-1">ℹ️ Animation playback</div>
            <div class="text-blue-700">
              Frames are uploaded to the cup in one batch (~150 ms each), then the cup plays them
              autonomously from internal storage. Browser preview cycles independently.
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

          <!-- Speed Control — drives both the on-screen preview and the byte sent to the cup. -->
          <div class="mb-3">
            <label class="block text-xs text-gray-600 mb-1">Speed: <span id="deviceDelayValue">130</span> <span class="text-gray-400">(<span id="speedMsValue">1300</span> ms/frame)</span></label>
            <input type="range" id="deviceDelaySlider" min="1" max="255" step="1" value="130" class="w-full h-2">
            <div class="text-xs text-gray-500 mt-1">Range 1–255, larger = faster. 130 is the cup's official default (1300 ms/frame). Preview and cup playback share this speed.</div>
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
        window.imageEditor.setTool(button.dataset.tool);
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
    const gammaSlider = document.getElementById("gammaSlider");
    const gammaValue = document.getElementById("gammaValue");

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

    gammaSlider.addEventListener("input", (e) => {
      gammaValue.textContent = parseFloat(e.target.value).toFixed(1);
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



function showToast(message, type = "info") {
  let toastContainer = document.getElementById("toastContainer");
  if (!toastContainer) {
    toastContainer = document.createElement("div");
    toastContainer.id = "toastContainer";
    toastContainer.className = "fixed top-4 right-4 z-50 space-y-2";
    document.body.appendChild(toastContainer);
  }

  const baseClasses =
    "px-4 py-3 rounded-lg shadow-lg text-white font-medium transition-all duration-300 transform translate-x-full max-w-md";
  const typeClasses = {
    info: "bg-blue-500",
    success: "bg-green-500",
    warning: "bg-yellow-500",
    error: "bg-red-500",
  };

  // Stickier for messages the user actually needs to read.
  const lifetimeMs = { error: 6000, warning: 4500, success: 3000, info: 3000 }[type] || 3000;

  const toast = document.createElement("div");
  toast.className = `${baseClasses} ${typeClasses[type] || typeClasses.info}`;

  // Allow click-to-dismiss for stickier messages.
  toast.style.cursor = "pointer";
  toast.title = "Click to dismiss";
  const dismiss = () => {
    toast.classList.remove("translate-x-0");
    toast.classList.add("translate-x-full");
    setTimeout(() => toast.parentNode?.removeChild(toast), 300);
  };
  toast.addEventListener("click", dismiss);

  toast.textContent = message;
  toastContainer.appendChild(toast);

  // Animate in
  setTimeout(() => {
    toast.classList.remove("translate-x-full");
    toast.classList.add("translate-x-0");
  }, 10);

  setTimeout(dismiss, lifetimeMs);
}

