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
      <div class="tool-buttons">
        <button id="drawTool" class="tool-button active" data-tool="draw">Draw</button>
        <button id="eraseTool" class="tool-button" data-tool="erase">Erase</button>
        <button id="clearTool" class="tool-button" data-tool="clear">Clear</button>
        <button id="fillTool" class="tool-button" data-tool="fill">Fill</button>
      </div>
      <div class="pixel-grid-container">
        <div id="pixelGrid" class="pixel-grid"></div>
      </div>
      <div class="mt-4">
        <button id="sendImageBtn" class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
          Send to Cup
        </button>
        <button id="resetImageBtn" class="ml-2 bg-gray-500 hover:bg-gray-700 text-white font-bold py-2 px-4 rounded">
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
        window.currentTool = button.dataset.tool;
      });
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

function hideAllFunctionPanels() {
  document.getElementById("welcomeMessage").classList.add("hidden");
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
  updateGreetingStatus,
  updateModeStatus,
  updateImageStatus,
};
