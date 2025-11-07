// imageSplitter.js - Split large images into 4 cup-sized chunks

// Single cup dimensions
const CUP_WIDTH = 48;
const CUP_HEIGHT = 12;

class ImageSplitter {
  constructor() {
    this.currentLayout = 'grid_2x2';
    this.splitResult = null;
  }

  /**
   * Get target dimensions for current layout
   */
  getTargetDimensions(layout = this.currentLayout) {
    switch (layout) {
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
   * Set layout configuration
   */
  setLayout(layout) {
    if (['grid_2x2', 'horizontal_1x4', 'vertical_4x1'].includes(layout)) {
      this.currentLayout = layout;
      return true;
    }
    return false;
  }

  /**
   * Calculate cup position boundaries for given layout
   * @returns Array of 4 boundary objects: { startRow, endRow, startCol, endCol }
   */
  getCupBoundaries(layout = this.currentLayout) {
    const boundaries = [];

    switch (layout) {
      case 'grid_2x2':
        // 96×24 grid: 2 rows, 2 cols
        // Cup 0: top-left
        boundaries.push({ startRow: 0, endRow: 12, startCol: 0, endCol: 48 });
        // Cup 1: top-right
        boundaries.push({ startRow: 0, endRow: 12, startCol: 48, endCol: 96 });
        // Cup 2: bottom-left
        boundaries.push({ startRow: 12, endRow: 24, startCol: 0, endCol: 48 });
        // Cup 3: bottom-right
        boundaries.push({ startRow: 12, endRow: 24, startCol: 48, endCol: 96 });
        break;

      case 'horizontal_1x4':
        // 192×12 strip: 1 row, 4 cols
        for (let i = 0; i < 4; i++) {
          boundaries.push({
            startRow: 0,
            endRow: 12,
            startCol: i * 48,
            endCol: (i + 1) * 48
          });
        }
        break;

      case 'vertical_4x1':
        // 48×48 column: 4 rows, 1 col
        for (let i = 0; i < 4; i++) {
          boundaries.push({
            startRow: i * 12,
            endRow: (i + 1) * 12,
            startCol: 0,
            endCol: 48
          });
        }
        break;
    }

    return boundaries;
  }

  /**
   * Split a large grid into 4 cup-sized chunks
   * @param {Array<Array<number>>} grid - Large grid (e.g., 24 rows × 96 cols)
   * @param {string} layout - Layout type
   * @returns {Array<Array<Array<number>>>} - Array of 4 grids (12×48 each)
   */
  splitGrid(grid, layout = this.currentLayout) {
    const boundaries = this.getCupBoundaries(layout);
    const chunks = [];

    // Debug: Check input grid dimensions
    const gridHeight = grid.length;
    const gridWidth = grid[0] ? grid[0].length : 0;
    console.log(`🔍 splitGrid: Input grid is ${gridHeight}×${gridWidth}, layout=${layout}`);

    for (let cupIndex = 0; cupIndex < 4; cupIndex++) {
      const { startRow, endRow, startCol, endCol } = boundaries[cupIndex];
      const chunk = [];

      console.log(`  Cup ${cupIndex}: rows ${startRow}-${endRow}, cols ${startCol}-${endCol}`);

      // Extract the sub-grid for this cup
      for (let row = startRow; row < endRow; row++) {
        const chunkRow = [];
        for (let col = startCol; col < endCol; col++) {
          // Handle out-of-bounds (fill with white)
          if (grid[row] && grid[row][col] !== undefined) {
            chunkRow.push(grid[row][col]);
          } else {
            chunkRow.push(0); // White pixel
          }
        }
        chunk.push(chunkRow);
      }

      chunks.push(chunk);
      console.log(`  Cup ${cupIndex}: chunk is ${chunk.length}×${chunk[0].length}`);
    }

    return chunks;
  }

  /**
   * Process uploaded image for multi-cup display
   * @param {File} file - Image file
   * @param {Object} options - Processing options (same as single-cup)
   * @param {string} layout - Layout type
   * @returns {Object} - Split result with chunks and previews
   */
  async processImageForMultiCup(file, options = {}, layout = this.currentLayout) {
    const dimensions = this.getTargetDimensions(layout);

    console.log(`🔍 processImageForMultiCup: layout=${layout}, target dimensions=${dimensions.width}×${dimensions.height}`);

    // Use existing imageProcessor but with multi-cup dimensions
    const processingOptions = {
      ...options,
      targetWidth: dimensions.width,
      targetHeight: dimensions.height
    };

    console.log(`🔍 Calling imageProcessor.processImage with targetWidth=${processingOptions.targetWidth}, targetHeight=${processingOptions.targetHeight}`);

    // Process image using existing processor
    const result = await window.imageProcessor.processImage(file, processingOptions);

    console.log(`🔍 imageProcessor returned grid: ${result.grid.length}×${result.grid[0]?.length}`);

    // Split the processed grid into 4 chunks
    const chunks = this.splitGrid(result.grid, layout);

    // Generate preview canvases for each chunk
    const chunkPreviews = this.generateChunkPreviews(chunks);

    // Store result
    this.splitResult = {
      layout,
      dimensions,
      chunks,
      chunkPreviews,
      originalResult: result, // Keep original for reference
      isTemporal: result.isTemporal,
      frames: result.isTemporal ? this.splitTemporalFrames(result.frames, layout) : null
    };

    return this.splitResult;
  }

  /**
   * Split temporal dithering frames into chunks
   */
  splitTemporalFrames(frames, layout = this.currentLayout) {
    if (!frames || !Array.isArray(frames)) return null;

    const splitFrames = [];

    for (const frame of frames) {
      const chunks = this.splitGrid(frame.grid, layout);
      const chunkPreviews = this.generateChunkPreviews(chunks);

      splitFrames.push({
        chunks,
        chunkPreviews,
        originalFrame: frame
      });
    }

    return splitFrames;
  }

  /**
   * Generate preview canvases for each chunk
   * @param {Array<Array<Array<number>>>} chunks - Array of 4 grids
   * @returns {Array<HTMLCanvasElement>} - Array of 4 canvas elements
   */
  generateChunkPreviews(chunks) {
    const previews = [];

    console.log('🔍 generateChunkPreviews: Creating previews for', chunks.length, 'chunks');

    for (let i = 0; i < 4; i++) {
      const canvas = document.createElement('canvas');
      canvas.width = CUP_WIDTH * 4; // 4x scale for visibility
      canvas.height = CUP_HEIGHT * 4;
      const ctx = canvas.getContext('2d');

      // Draw the chunk
      const grid = chunks[i];

      // Count black pixels for this chunk
      let blackPixels = 0;
      for (let row = 0; row < CUP_HEIGHT; row++) {
        for (let col = 0; col < CUP_WIDTH; col++) {
          const pixel = grid[row][col];
          if (pixel === 1) blackPixels++;
          ctx.fillStyle = pixel === 1 ? '#000000' : '#FFFFFF';
          ctx.fillRect(col * 4, row * 4, 4, 4);
        }
      }

      console.log(`  Preview ${i}: ${canvas.width}×${canvas.height}, ${blackPixels} black pixels`);
      previews.push(canvas);
    }

    return previews;
  }

  /**
   * Generate a composite preview showing all 4 cups in layout
   * @param {Array<Array<Array<number>>>} chunks - Array of 4 grids
   * @param {string} layout - Layout type
   * @returns {HTMLCanvasElement} - Composite preview canvas
   */
  generateCompositePreview(chunks, layout = this.currentLayout) {
    const dimensions = this.getTargetDimensions(layout);
    const scale = 4; // Display scale

    const canvas = document.createElement('canvas');
    canvas.width = dimensions.width * scale;
    canvas.height = dimensions.height * scale;
    const ctx = canvas.getContext('2d');

    // Fill background
    ctx.fillStyle = '#FFFFFF';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw each chunk at correct position
    const boundaries = this.getCupBoundaries(layout);

    for (let cupIndex = 0; cupIndex < 4; cupIndex++) {
      const { startRow, startCol } = boundaries[cupIndex];
      const grid = chunks[cupIndex];

      for (let row = 0; row < CUP_HEIGHT; row++) {
        for (let col = 0; col < CUP_WIDTH; col++) {
          const pixel = grid[row][col];
          if (pixel === 1) {
            ctx.fillStyle = '#000000';
            const x = (startCol + col) * scale;
            const y = (startRow + row) * scale;
            ctx.fillRect(x, y, scale, scale);
          }
        }
      }

      // Draw cup boundaries (optional, for debugging)
      ctx.strokeStyle = '#FF0000';
      ctx.lineWidth = 2;
      ctx.strokeRect(
        startCol * scale,
        startRow * scale,
        CUP_WIDTH * scale,
        CUP_HEIGHT * scale
      );
    }

    return canvas;
  }

  /**
   * Get the last split result
   */
  getLastSplitResult() {
    return this.splitResult;
  }

  /**
   * Clear stored result
   */
  clear() {
    this.splitResult = null;
  }
}

// Export as singleton
window.imageSplitter = new ImageSplitter();
