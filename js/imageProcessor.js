// imageProcessor.js - Image processing and dithering algorithms

class ImageProcessor {
  constructor() {
    this.IMAGE_WIDTH = 48;
    this.IMAGE_HEIGHT = 12;
  }

  /**
   * Load an image file and return an Image object
   * @param {File} file - Image file from input element
   * @returns {Promise<HTMLImageElement>}
   */
  async loadImageFromFile(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();

      reader.onload = (e) => {
        const img = new Image();
        img.onload = () => resolve(img);
        img.onerror = () => reject(new Error('Failed to load image'));
        img.src = e.target.result;
      };

      reader.onerror = () => reject(new Error('Failed to read file'));
      reader.readAsDataURL(file);
    });
  }

  /**
   * Resize image to target dimensions using canvas
   * @param {HTMLImageElement} img - Source image
   * @param {number} width - Target width
   * @param {number} height - Target height
   * @param {boolean} maintainAspect - Whether to maintain aspect ratio
   * @returns {ImageData}
   */
  resizeImage(img, width, height, maintainAspect = true) {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');

    let drawWidth = width;
    let drawHeight = height;
    let offsetX = 0;
    let offsetY = 0;

    if (maintainAspect) {
      const imgAspect = img.width / img.height;
      const targetAspect = width / height;

      if (imgAspect > targetAspect) {
        // Image is wider - fit to width
        drawWidth = width;
        drawHeight = width / imgAspect;
        offsetY = (height - drawHeight) / 2;
      } else {
        // Image is taller - fit to height
        drawHeight = height;
        drawWidth = height * imgAspect;
        offsetX = (width - drawWidth) / 2;
      }
    }

    canvas.width = width;
    canvas.height = height;

    // Fill with white background
    ctx.fillStyle = 'white';
    ctx.fillRect(0, 0, width, height);

    // Draw image
    ctx.drawImage(img, offsetX, offsetY, drawWidth, drawHeight);

    return ctx.getImageData(0, 0, width, height);
  }

  /**
   * Convert image data to grayscale
   * @param {ImageData} imageData
   * @returns {Uint8ClampedArray} - Grayscale values (0-255)
   */
  toGrayscale(imageData) {
    const data = imageData.data;
    const grayscale = new Uint8ClampedArray(imageData.width * imageData.height);

    for (let i = 0; i < data.length; i += 4) {
      // Standard luminance conversion (ITU-R BT.601)
      const r = data[i];
      const g = data[i + 1];
      const b = data[i + 2];
      const gray = Math.round(r * 0.299 + g * 0.587 + b * 0.114);
      grayscale[i / 4] = gray;
    }

    return grayscale;
  }

  /**
   * Apply Floyd-Steinberg dithering algorithm
   * @param {Uint8ClampedArray} grayscale - Grayscale pixel values
   * @param {number} width - Image width
   * @param {number} height - Image height
   * @param {number} threshold - Threshold value (0-255, default 128)
   * @returns {Uint8Array} - Binary image (0 or 1)
   */
  floydSteinbergDither(grayscale, width, height, threshold = 128) {
    // Create a working copy to accumulate errors
    const pixels = new Float32Array(grayscale);
    const output = new Uint8Array(width * height);

    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        const idx = y * width + x;
        const oldPixel = pixels[idx];

        // Quantize: decide if pixel should be black (1) or white (0)
        const newPixel = oldPixel > threshold ? 255 : 0;
        output[idx] = newPixel === 0 ? 1 : 0; // Invert: 0 = white, 1 = black

        // Calculate quantization error
        const error = oldPixel - newPixel;

        // Distribute error to neighboring pixels (Floyd-Steinberg coefficients)
        // Right pixel (x+1, y): 7/16 of error
        if (x + 1 < width) {
          pixels[idx + 1] += error * 7 / 16;
        }

        // Bottom-left pixel (x-1, y+1): 3/16 of error
        if (x > 0 && y + 1 < height) {
          pixels[idx + width - 1] += error * 3 / 16;
        }

        // Bottom pixel (x, y+1): 5/16 of error
        if (y + 1 < height) {
          pixels[idx + width] += error * 5 / 16;
        }

        // Bottom-right pixel (x+1, y+1): 1/16 of error
        if (x + 1 < width && y + 1 < height) {
          pixels[idx + width + 1] += error * 1 / 16;
        }
      }
    }

    return output;
  }

  /**
   * Simple threshold-based conversion (no dithering)
   * @param {Uint8ClampedArray} grayscale
   * @param {number} threshold
   * @returns {Uint8Array}
   */
  simpleThreshold(grayscale, threshold = 128) {
    const output = new Uint8Array(grayscale.length);

    for (let i = 0; i < grayscale.length; i++) {
      output[i] = grayscale[i] > threshold ? 0 : 1; // 0 = white, 1 = black
    }

    return output;
  }

  /**
   * Convert flat binary array to 2D grid for imageEditor
   * @param {Uint8Array} binaryData
   * @param {number} width
   * @param {number} height
   * @returns {Array<Array<number>>}
   */
  toGridArray(binaryData, width, height) {
    const grid = [];

    for (let row = 0; row < height; row++) {
      const rowData = [];
      for (let col = 0; col < width; col++) {
        rowData.push(binaryData[row * width + col]);
      }
      grid.push(rowData);
    }

    return grid;
  }

  /**
   * Create a preview canvas from binary data
   * @param {Uint8Array} binaryData
   * @param {number} width
   * @param {number} height
   * @param {number} scale - Scale factor for preview (default 8)
   * @returns {HTMLCanvasElement}
   */
  createPreviewCanvas(binaryData, width, height, scale = 8) {
    const canvas = document.createElement('canvas');
    canvas.width = width * scale;
    canvas.height = height * scale;
    const ctx = canvas.getContext('2d');

    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        const idx = y * width + x;
        const color = binaryData[idx] === 1 ? '#000000' : '#FFFFFF';
        ctx.fillStyle = color;
        ctx.fillRect(x * scale, y * scale, scale, scale);
      }
    }

    return canvas;
  }

  /**
   * Process image file and return grid data ready for display
   * @param {File} file - Image file
   * @param {Object} options - Processing options
   * @returns {Promise<Object>} - {grid, preview, originalImage}
   */
  async processImage(file, options = {}) {
    const {
      threshold = 128,
      useDithering = true,
      maintainAspect = true
    } = options;

    try {
      // Load image
      const img = await this.loadImageFromFile(file);

      // Resize to display dimensions
      const imageData = this.resizeImage(
        img,
        this.IMAGE_WIDTH,
        this.IMAGE_HEIGHT,
        maintainAspect
      );

      // Convert to grayscale
      const grayscale = this.toGrayscale(imageData);

      // Apply dithering or threshold
      const binaryData = useDithering
        ? this.floydSteinbergDither(grayscale, this.IMAGE_WIDTH, this.IMAGE_HEIGHT, threshold)
        : this.simpleThreshold(grayscale, threshold);

      // Convert to grid format
      const grid = this.toGridArray(binaryData, this.IMAGE_WIDTH, this.IMAGE_HEIGHT);

      // Create preview
      const preview = this.createPreviewCanvas(binaryData, this.IMAGE_WIDTH, this.IMAGE_HEIGHT);

      return {
        grid,
        preview,
        originalImage: img,
        binaryData
      };
    } catch (error) {
      throw new Error(`Image processing failed: ${error.message}`);
    }
  }

  /**
   * Adjust brightness of grayscale data
   * @param {Uint8ClampedArray} grayscale
   * @param {number} brightness - Adjustment value (-255 to 255)
   * @returns {Uint8ClampedArray}
   */
  adjustBrightness(grayscale, brightness) {
    const adjusted = new Uint8ClampedArray(grayscale.length);

    for (let i = 0; i < grayscale.length; i++) {
      adjusted[i] = Math.max(0, Math.min(255, grayscale[i] + brightness));
    }

    return adjusted;
  }

  /**
   * Adjust contrast of grayscale data
   * @param {Uint8ClampedArray} grayscale
   * @param {number} contrast - Contrast factor (0.5 to 2.0, 1.0 = no change)
   * @returns {Uint8ClampedArray}
   */
  adjustContrast(grayscale, contrast) {
    const adjusted = new Uint8ClampedArray(grayscale.length);
    const factor = (259 * (contrast * 255 + 255)) / (255 * (259 - contrast * 255));

    for (let i = 0; i < grayscale.length; i++) {
      adjusted[i] = Math.max(0, Math.min(255, factor * (grayscale[i] - 128) + 128));
    }

    return adjusted;
  }
}

// Export as singleton
window.imageProcessor = new ImageProcessor();
