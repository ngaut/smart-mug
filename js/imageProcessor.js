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
   * @returns {Promise<Object>} - {grid, preview, originalImage, analysis}
   */
  async processImage(file, options = {}) {
    const {
      threshold = 128,
      algorithm = 'floyd-steinberg', // 'floyd-steinberg', 'atkinson', 'ordered', 'threshold'
      maintainAspect = true,
      brightness = 0,      // -100 to 100
      contrast = 0,        // -100 to 100
      sharpen = 0,         // 0 to 2
      autoContrast = false // Histogram equalization
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
      let grayscale = this.toGrayscale(imageData);

      // Analyze original grayscale
      const analysis = this.analyzeImage(grayscale);

      // Apply preprocessing in order

      // 1. Auto contrast (histogram equalization)
      if (autoContrast) {
        grayscale = this.histogramEqualize(grayscale);
      }

      // 2. Brightness adjustment
      if (brightness !== 0) {
        grayscale = this.adjustBrightness(grayscale, brightness);
      }

      // 3. Contrast adjustment
      if (contrast !== 0) {
        grayscale = this.adjustContrast(grayscale, contrast);
      }

      // 4. Sharpening
      if (sharpen > 0) {
        grayscale = this.sharpen(grayscale, this.IMAGE_WIDTH, this.IMAGE_HEIGHT, sharpen);
      }

      // Apply dithering algorithm
      let binaryData;
      let frames = null; // For temporal dithering
      let isTemporal = false;

      switch (algorithm) {
        case 'temporal':
          isTemporal = true;
          frames = this.temporalDither(grayscale, this.IMAGE_WIDTH, this.IMAGE_HEIGHT, 4);
          binaryData = frames[0]; // Use first frame as default
          break;
        case 'temporal-spatial':
          isTemporal = true;
          frames = this.temporalSpatialDither(grayscale, this.IMAGE_WIDTH, this.IMAGE_HEIGHT, 4);
          binaryData = frames[0]; // Use first frame as default
          break;
        case 'atkinson':
          binaryData = this.atkinsonDither(grayscale, this.IMAGE_WIDTH, this.IMAGE_HEIGHT, threshold);
          break;
        case 'ordered':
          binaryData = this.orderedDither(grayscale, this.IMAGE_WIDTH, this.IMAGE_HEIGHT);
          break;
        case 'threshold':
          binaryData = this.simpleThreshold(grayscale, threshold);
          break;
        case 'floyd-steinberg':
        default:
          binaryData = this.floydSteinbergDither(grayscale, this.IMAGE_WIDTH, this.IMAGE_HEIGHT, threshold);
          break;
      }

      // For temporal algorithms, process all frames
      if (isTemporal && frames) {
        const frameData = frames.map((frameBinary, index) => ({
          index,
          binaryData: frameBinary,
          grid: this.toGridArray(frameBinary, this.IMAGE_WIDTH, this.IMAGE_HEIGHT),
          preview: this.createPreviewCanvas(frameBinary, this.IMAGE_WIDTH, this.IMAGE_HEIGHT)
        }));

        return {
          isTemporal: true,
          frames: frameData,
          numFrames: frames.length,
          originalImage: img,
          analysis,
          // Keep single-frame compatibility
          grid: frameData[0].grid,
          preview: frameData[0].preview,
          binaryData: frameData[0].binaryData
        };
      }

      // Convert to grid format (single frame)
      const grid = this.toGridArray(binaryData, this.IMAGE_WIDTH, this.IMAGE_HEIGHT);

      // Create preview
      const preview = this.createPreviewCanvas(binaryData, this.IMAGE_WIDTH, this.IMAGE_HEIGHT);

      return {
        isTemporal: false,
        grid,
        preview,
        originalImage: img,
        binaryData,
        analysis // Include analysis for UI feedback
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
   * @param {number} contrast - Contrast factor (-100 to 100, 0 = no change)
   * @returns {Uint8ClampedArray}
   */
  adjustContrast(grayscale, contrast) {
    const adjusted = new Uint8ClampedArray(grayscale.length);
    const factor = (259 * (contrast + 255)) / (255 * (259 - contrast));

    for (let i = 0; i < grayscale.length; i++) {
      adjusted[i] = Math.max(0, Math.min(255, factor * (grayscale[i] - 128) + 128));
    }

    return adjusted;
  }

  /**
   * Sharpen image using unsharp mask
   * @param {Uint8ClampedArray} grayscale
   * @param {number} width
   * @param {number} height
   * @param {number} amount - Sharpening amount (0-2, default 1)
   * @returns {Uint8ClampedArray}
   */
  sharpen(grayscale, width, height, amount = 1) {
    const sharpened = new Uint8ClampedArray(grayscale.length);

    // Simple 3x3 sharpening kernel
    const kernel = [
      0, -1, 0,
      -1, 5, -1,
      0, -1, 0
    ];

    for (let y = 1; y < height - 1; y++) {
      for (let x = 1; x < width - 1; x++) {
        let sum = 0;

        // Apply kernel
        for (let ky = -1; ky <= 1; ky++) {
          for (let kx = -1; kx <= 1; kx++) {
            const idx = (y + ky) * width + (x + kx);
            const kidx = (ky + 1) * 3 + (kx + 1);
            sum += grayscale[idx] * kernel[kidx];
          }
        }

        const idx = y * width + x;
        const original = grayscale[idx];
        const sharp = original + (sum - original) * amount;
        sharpened[idx] = Math.max(0, Math.min(255, sharp));
      }
    }

    // Copy edges
    for (let x = 0; x < width; x++) {
      sharpened[x] = grayscale[x]; // Top
      sharpened[(height - 1) * width + x] = grayscale[(height - 1) * width + x]; // Bottom
    }
    for (let y = 0; y < height; y++) {
      sharpened[y * width] = grayscale[y * width]; // Left
      sharpened[y * width + width - 1] = grayscale[y * width + width - 1]; // Right
    }

    return sharpened;
  }

  /**
   * Histogram equalization for automatic contrast enhancement
   * @param {Uint8ClampedArray} grayscale
   * @returns {Uint8ClampedArray}
   */
  histogramEqualize(grayscale) {
    const histogram = new Array(256).fill(0);
    const cdf = new Array(256).fill(0);

    // Build histogram
    for (let i = 0; i < grayscale.length; i++) {
      histogram[grayscale[i]]++;
    }

    // Build cumulative distribution function
    cdf[0] = histogram[0];
    for (let i = 1; i < 256; i++) {
      cdf[i] = cdf[i - 1] + histogram[i];
    }

    // Normalize CDF
    const cdfMin = cdf.find(v => v > 0);
    const totalPixels = grayscale.length;
    const equalized = new Uint8ClampedArray(grayscale.length);

    for (let i = 0; i < grayscale.length; i++) {
      const value = grayscale[i];
      equalized[i] = Math.round(((cdf[value] - cdfMin) / (totalPixels - cdfMin)) * 255);
    }

    return equalized;
  }

  /**
   * Atkinson dithering algorithm (cleaner, less noise than Floyd-Steinberg)
   * @param {Uint8ClampedArray} grayscale
   * @param {number} width
   * @param {number} height
   * @param {number} threshold
   * @returns {Uint8Array}
   */
  atkinsonDither(grayscale, width, height, threshold = 128) {
    const pixels = new Float32Array(grayscale);
    const output = new Uint8Array(width * height);

    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        const idx = y * width + x;
        const oldPixel = pixels[idx];
        const newPixel = oldPixel > threshold ? 255 : 0;
        output[idx] = newPixel === 0 ? 1 : 0; // Invert: 0 = white, 1 = black

        const error = (oldPixel - newPixel) / 8; // Atkinson divides by 8, not 16

        // Distribute error (Atkinson pattern)
        if (x + 1 < width) pixels[idx + 1] += error;
        if (x + 2 < width) pixels[idx + 2] += error;
        if (y + 1 < height) {
          if (x - 1 >= 0) pixels[idx + width - 1] += error;
          pixels[idx + width] += error;
          if (x + 1 < width) pixels[idx + width + 1] += error;
        }
        if (y + 2 < height) {
          pixels[idx + width * 2] += error;
        }
      }
    }

    return output;
  }

  /**
   * Ordered (Bayer) dithering - creates regular pattern
   * @param {Uint8ClampedArray} grayscale
   * @param {number} width
   * @param {number} height
   * @returns {Uint8Array}
   */
  orderedDither(grayscale, width, height) {
    const output = new Uint8Array(width * height);

    // 4x4 Bayer matrix
    const bayerMatrix = [
      [ 0, 8, 2, 10],
      [12, 4, 14, 6],
      [ 3, 11, 1, 9],
      [15, 7, 13, 5]
    ];

    const matrixSize = 4;
    const scale = 255 / 16; // Bayer matrix values are 0-15

    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        const idx = y * width + x;
        const bayerValue = bayerMatrix[y % matrixSize][x % matrixSize];
        const threshold = bayerValue * scale;
        output[idx] = grayscale[idx] > threshold ? 0 : 1; // 0 = white, 1 = black
      }
    }

    return output;
  }

  /**
   * Analyze image histogram and suggest improvements
   * @param {Uint8ClampedArray} grayscale
   * @returns {Object} Analysis results with suggestions
   */
  analyzeImage(grayscale) {
    const histogram = new Array(256).fill(0);
    let min = 255, max = 0, sum = 0;

    // Build histogram and calculate stats
    for (let i = 0; i < grayscale.length; i++) {
      const value = grayscale[i];
      histogram[value]++;
      min = Math.min(min, value);
      max = Math.max(max, value);
      sum += value;
    }

    const mean = sum / grayscale.length;
    const range = max - min;
    const contrast = range / 255;

    // Calculate standard deviation
    let variance = 0;
    for (let i = 0; i < grayscale.length; i++) {
      variance += Math.pow(grayscale[i] - mean, 2);
    }
    const stdDev = Math.sqrt(variance / grayscale.length);

    // Determine image characteristics
    const isLowContrast = contrast < 0.4;
    const isDark = mean < 85;
    const isBright = mean > 170;
    const hasGoodDistribution = stdDev > 50;

    // Generate suggestions
    const suggestions = [];
    if (isLowContrast) {
      suggestions.push('⚠️ Low contrast - increase contrast slider');
    }
    if (isDark) {
      suggestions.push('🔆 Image is dark - increase brightness');
    }
    if (isBright) {
      suggestions.push('🔅 Image is bright - decrease brightness');
    }
    if (!hasGoodDistribution) {
      suggestions.push('📊 Limited tonal range - try histogram equalization');
    }
    if (range < 100) {
      suggestions.push('💡 Try sharpening to enhance details');
    }

    return {
      min,
      max,
      mean: Math.round(mean),
      stdDev: Math.round(stdDev),
      contrast: Math.round(contrast * 100),
      histogram,
      isLowContrast,
      isDark,
      isBright,
      hasGoodDistribution,
      suggestions,
      quality: hasGoodDistribution && !isLowContrast ? 'good' : 'poor'
    };
  }

  /**
   * Temporal dithering - generates multiple frames for animation
   * Creates perceived grayscale through temporal averaging (PWM for displays)
   * @param {Uint8ClampedArray} grayscale
   * @param {number} width
   * @param {number} height
   * @param {number} numFrames - Number of frames (2-8, default 4)
   * @returns {Array<Uint8Array>} Array of binary frame data
   */
  temporalDither(grayscale, width, height, numFrames = 4) {
    const frames = [];

    // Generate brightness thresholds for each frame
    // Frame 0: Only brightest pixels (creates ~25% duty cycle for dark pixels)
    // Frame 1: Brighter pixels (creates ~50% duty cycle)
    // Frame 2: Medium pixels (creates ~75% duty cycle)
    // Frame 3: Most pixels (creates ~100% duty cycle for bright pixels)

    for (let frameIndex = 0; frameIndex < numFrames; frameIndex++) {
      const output = new Uint8Array(width * height);

      // Calculate threshold for this frame
      // Frame 0 (first): highest threshold - only brightest pixels
      // Frame N-1 (last): lowest threshold - most pixels visible
      const threshold = 255 - ((frameIndex + 1) * 255 / numFrames);

      // For each pixel, determine if it should be ON in this frame
      for (let i = 0; i < grayscale.length; i++) {
        const brightness = grayscale[i];

        // Pixel is ON if its brightness exceeds this frame's threshold
        // This creates temporal PWM effect:
        // - Bright pixels (255): ON in all frames (100% duty cycle)
        // - Medium pixels (128): ON in half the frames (50% duty cycle)
        // - Dark pixels (64): ON in quarter frames (25% duty cycle)
        output[i] = brightness > threshold ? 1 : 0;
      }

      frames.push(output);
    }

    return frames;
  }

  /**
   * Hybrid temporal + spatial dithering for best quality
   * Applies error diffusion dithering to each temporal frame
   * @param {Uint8ClampedArray} grayscale
   * @param {number} width
   * @param {number} height
   * @param {number} numFrames
   * @returns {Array<Uint8Array>} Array of binary frame data
   */
  temporalSpatialDither(grayscale, width, height, numFrames = 4) {
    const frames = [];

    for (let frameIndex = 0; frameIndex < numFrames; frameIndex++) {
      // Calculate threshold for this frame
      const baseThreshold = 255 - ((frameIndex + 1) * 255 / numFrames);

      // Apply Floyd-Steinberg with this threshold
      const frame = this.floydSteinbergDither(
        grayscale,
        width,
        height,
        baseThreshold
      );

      frames.push(frame);
    }

    return frames;
  }
}

// Export as singleton
window.imageProcessor = new ImageProcessor();
