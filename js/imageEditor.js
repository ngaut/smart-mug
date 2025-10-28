// imageEditor.js - Image editor functionality

class ImageEditor {
  constructor() {
    // Image dimensions
    this.IMAGE_WIDTH = 48;
    this.IMAGE_HEIGHT = 12;

    this.grid = Array(this.IMAGE_HEIGHT)
      .fill()
      .map(() => Array(this.IMAGE_WIDTH).fill(0)); // 0 = white, 1 = black
    this.isDrawing = false;
    this.currentTool = "draw"; // draw, erase, clear, fill
  }

  initializeGrid() {
    this.grid = Array(this.IMAGE_HEIGHT)
      .fill()
      .map(() => Array(this.IMAGE_WIDTH).fill(0));
    this.updateDisplay();
  }

  setTool(tool) {
    this.currentTool = tool;
  }

  startDrawing(row, col) {
    this.isDrawing = true;
    this.processPixel(row, col);
  }

  continueDrawing(row, col) {
    if (this.isDrawing) {
      this.processPixel(row, col);
    }
  }

  stopDrawing() {
    this.isDrawing = false;
  }

  processPixel(row, col) {
    switch (this.currentTool) {
      case "draw":
        this.grid[row][col] = 1;
        break;
      case "erase":
        this.grid[row][col] = 0;
        break;
      case "clear":
        this.initializeGrid();
        return;
      case "fill":
        this.fillGrid();
        return;
    }
    this.updatePixel(row, col);
  }

  fillGrid() {
    // Always fill with black pixels (1) when fillGrid is called
    console.log('fillGrid called - filling with black pixels');
    const fillValue = 1;
    this.grid = Array(this.IMAGE_HEIGHT)
      .fill()
      .map(() => Array(this.IMAGE_WIDTH).fill(fillValue));
    console.log('Grid filled, updating display');
    this.updateDisplay();
    console.log('fillGrid completed');
  }

  updatePixel(row, col) {
    const pixel = document.querySelector(
      `.pixel[data-row="${row}"][data-col="${col}"]`
    );
    if (pixel) {
      pixel.className = this.grid[row][col] === 1 ? "pixel black" : "pixel";
    }
  }

  updateDisplay() {
    for (let row = 0; row < this.IMAGE_HEIGHT; row++) {
      for (let col = 0; col < this.IMAGE_WIDTH; col++) {
        this.updatePixel(row, col);
      }
    }
  }

  getGridData() {
    return this.grid;
  }

  reset() {
    this.initializeGrid();
  }
}

// Export as singleton
window.imageEditor = new ImageEditor();
