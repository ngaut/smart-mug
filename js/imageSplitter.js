// imageSplitter.js - Split large images into 4 cup-sized chunks

// Single cup dimensions
const CUP_WIDTH = 48;
const CUP_HEIGHT = 12;

class ImageSplitter {
  constructor() {
    this.currentLayout = 'grid_2x2'; // Default to Landscape Wide (user preference)
    this.splitResult = null;

    // Physical gap compensation (in pixels)
    this.gapHorizontal = 0; // Gap between left and right cups
    this.gapVertical = 0;   // Gap between top and bottom cups
  }

  /**
   * Set gap sizes for physical spacing between cups
   * @param {number} horizontal - Horizontal gap in pixels
   * @param {number} vertical - Vertical gap in pixels
   */
  setGaps(horizontal, vertical) {
    this.gapHorizontal = Math.max(0, Math.min(horizontal, 20)); // Max 20px
    this.gapVertical = Math.max(0, Math.min(vertical, 10));     // Max 10px
    console.log(`Gap compensation: ${this.gapHorizontal}px horizontal, ${this.gapVertical}px vertical`);
  }

  /**
   * Get target dimensions for current layout (including gaps)
   */
  getTargetDimensions(layout = this.currentLayout) {
    let base;
    switch (layout) {
      case 'grid_2x2':
        base = { width: 96, height: 24, rows: 2, cols: 2 };
        break;
      case 'vertical_4x1':
        base = { width: 48, height: 48, rows: 4, cols: 1 };
        break;
      default:
        base = { width: 48, height: 48, rows: 4, cols: 1 };
    }

    // Add gaps to dimensions
    // Gaps appear between cups: (cols-1) horizontal gaps, (rows-1) vertical gaps
    const totalWidth = base.width + (this.gapHorizontal * (base.cols - 1));
    const totalHeight = base.height + (this.gapVertical * (base.rows - 1));

    return {
      ...base,
      width: totalWidth,
      height: totalHeight
    };
  }

  /**
   * Set layout configuration
   */
  setLayout(layout) {
    if (['grid_2x2', 'vertical_4x1'].includes(layout)) {
      this.currentLayout = layout;
      return true;
    }
    return false;
  }

  /**
   * Calculate cup position boundaries for given layout (accounting for gaps)
   * @returns Array of 4 boundary objects: { startRow, endRow, startCol, endCol }
   */
  getCupBoundaries(layout = this.currentLayout) {
    const boundaries = [];
    const gapH = this.gapHorizontal;
    const gapV = this.gapVertical;

    switch (layout) {
      case 'grid_2x2':
        // 96×24 grid + gaps: 2 rows, 2 cols
        // Cup 0: top-left (no offset)
        boundaries.push({ startRow: 0, endRow: 12, startCol: 0, endCol: 48 });
        // Cup 1: top-right (skip horizontal gap)
        boundaries.push({ startRow: 0, endRow: 12, startCol: 48 + gapH, endCol: 96 + gapH });
        // Cup 2: bottom-left (skip vertical gap)
        boundaries.push({ startRow: 12 + gapV, endRow: 24 + gapV, startCol: 0, endCol: 48 });
        // Cup 3: bottom-right (skip both gaps)
        boundaries.push({ startRow: 12 + gapV, endRow: 24 + gapV, startCol: 48 + gapH, endCol: 96 + gapH });
        break;

      case 'vertical_4x1':
        // 48×48 column + gaps: 4 rows, 1 col
        for (let i = 0; i < 4; i++) {
          const rowOffset = i * gapV; // Accumulate gaps
          boundaries.push({
            startRow: i * 12 + rowOffset,
            endRow: (i + 1) * 12 + rowOffset,
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
    const dimensions = this.getTargetDimensions(layout);
    const chunks = [];

    // Debug: Check input grid dimensions
    const gridHeight = grid.length;
    const gridWidth = grid[0] ? grid[0].length : 0;
    console.log(`🔍 splitGrid: Input grid is ${gridHeight}×${gridWidth}, layout=${layout}`);

    for (let cupIndex = 0; cupIndex < 4; cupIndex++) {
      const { startRow, endRow, startCol, endCol } = boundaries[cupIndex];
      let chunk = [];

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
      console.log(`  Cup ${cupIndex}: final chunk is ${chunk.length}×${chunk[0].length}`);
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
      const grid = chunks[i];

      // Get actual chunk dimensions
      const chunkHeight = grid.length;
      const chunkWidth = grid[0] ? grid[0].length : 0;

      const canvas = document.createElement('canvas');
      const scale = 4; // 4x scale for visibility
      canvas.width = chunkWidth * scale;
      canvas.height = chunkHeight * scale;
      const ctx = canvas.getContext('2d');

      // Count black pixels for this chunk
      let blackPixels = 0;
      for (let row = 0; row < chunkHeight; row++) {
        for (let col = 0; col < chunkWidth; col++) {
          const pixel = grid[row][col];
          if (pixel === 1) blackPixels++;
          ctx.fillStyle = pixel === 1 ? '#000000' : '#FFFFFF';
          ctx.fillRect(col * scale, row * scale, scale, scale);
        }
      }

      console.log(`  Preview ${i}: ${canvas.width}×${canvas.height} (${chunkWidth}×${chunkHeight}), ${blackPixels} black pixels`);
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

    // Fill background (white)
    ctx.fillStyle = '#FFFFFF';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Fill gap areas with light gray to visualize gaps
    if (this.gapHorizontal > 0 || this.gapVertical > 0) {
      ctx.fillStyle = '#E0E0E0';

      // Draw horizontal gaps
      const boundaries = this.getCupBoundaries(layout);
      for (let i = 0; i < 4; i++) {
        const { startRow, endRow, startCol, endCol } = boundaries[i];

        // Check if there's a cup to the right (horizontal gap)
        for (let j = 0; j < 4; j++) {
          if (i !== j) {
            const other = boundaries[j];
            // If other cup starts where this ends (with a gap)
            if (Math.abs(other.startCol - endCol) > 0 && Math.abs(other.startCol - endCol) <= this.gapHorizontal &&
              startRow === other.startRow) {
              // Draw horizontal gap
              ctx.fillRect(endCol * scale, startRow * scale,
                (other.startCol - endCol) * scale, (endRow - startRow) * scale);
            }
            // If other cup starts below this (with a gap)
            if (Math.abs(other.startRow - endRow) > 0 && Math.abs(other.startRow - endRow) <= this.gapVertical &&
              startCol === other.startCol) {
              // Draw vertical gap
              ctx.fillRect(startCol * scale, endRow * scale,
                (endCol - startCol) * scale, (other.startRow - endRow) * scale);
            }
          }
        }
      }
    }

    // Draw each chunk at correct position
    const boundaries = this.getCupBoundaries(layout);

    for (let cupIndex = 0; cupIndex < 4; cupIndex++) {
      const { startRow, startCol } = boundaries[cupIndex];
      const grid = chunks[cupIndex];

      // Get actual chunk dimensions
      const chunkHeight = grid.length;
      const chunkWidth = grid[0] ? grid[0].length : 0;

      for (let row = 0; row < chunkHeight; row++) {
        for (let col = 0; col < chunkWidth; col++) {
          const pixel = grid[row][col];
          if (pixel === 1) {
            ctx.fillStyle = '#000000';
            const x = (startCol + col) * scale;
            const y = (startRow + row) * scale;
            ctx.fillRect(x, y, scale, scale);
          }
        }
      }

      // Draw cup boundaries (red borders)
      ctx.strokeStyle = '#FF0000';
      ctx.lineWidth = 2;
      ctx.strokeRect(
        startCol * scale,
        startRow * scale,
        chunkWidth * scale,
        chunkHeight * scale
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
