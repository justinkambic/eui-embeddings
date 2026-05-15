/**
 * Icon Renderer Utility
 * 
 * Renders EuiIcon components to standardized images (PNG) and extracts SVG code.
 * Uses React server-side rendering to generate icons.
 */

const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const fs = require('fs').promises;
const path = require('path');
const { createCanvas } = require('canvas');

// Note: This requires @elastic/eui to be installed
// You may need to configure the EuiIcon import based on your setup
let EuiIcon;
try {
  EuiIcon = require('@elastic/eui').EuiIcon;
} catch (e) {
  console.warn('Warning: Could not import EuiIcon. Make sure @elastic/eui is installed.');
}

/**
 * Render an EuiIcon to SVG string
 * @param {string} iconType - The icon type name
 * @param {string} size - Icon size (default: 'xl')
 * @returns {Promise<string|null>} SVG string or null on error
 */
async function renderIconToSVG(iconType, size = 'xl') {
  if (!EuiIcon) {
    throw new Error('EuiIcon is not available. Install @elastic/eui package.');
  }

  try {
    const iconElement = React.createElement(EuiIcon, {
      type: iconType,
      size: size
    });
    
    const htmlString = renderToStaticMarkup(iconElement);
    
    // Extract just the SVG part
    const svgMatch = htmlString.match(/<svg[^>]*>.*<\/svg>/s);
    if (svgMatch) {
      return svgMatch[0];
    }
    
    // If no SVG found, return the full HTML (might be wrapped)
    return htmlString;
  } catch (error) {
    console.error(`Error rendering icon ${iconType}:`, error.message);
    return null;
  }
}

/**
 * Normalize SVG: standardize size, remove metadata, ensure consistent format
 * @param {string} svgString - Raw SVG string
 * @param {number} targetSize - Target size in pixels (default: 224)
 * @returns {string} Normalized SVG string
 */
function normalizeSVG(svgString, targetSize = 224) {
  if (!svgString) return null;

  // Extract viewBox or create one
  const viewBoxMatch = svgString.match(/viewBox=["']([^"']+)["']/);
  const widthMatch = svgString.match(/width=["']([^"']+)["']/);
  const heightMatch = svgString.match(/height=["']([^"']+)["']/);

  let viewBox = '0 0 24 24'; // Default EUI icon viewBox
  if (viewBoxMatch) {
    viewBox = viewBoxMatch[1];
  } else if (widthMatch && heightMatch) {
    const width = parseFloat(widthMatch[1]) || 24;
    const height = parseFloat(heightMatch[1]) || 24;
    viewBox = `0 0 ${width} ${height}`;
  }

  // Create normalized SVG with consistent size
  const normalizedSVG = svgString
    .replace(/<svg[^>]*>/, `<svg viewBox="${viewBox}" width="${targetSize}" height="${targetSize}" xmlns="http://www.w3.org/2000/svg">`)
    .replace(/fill=["'][^"']*["']/g, '') // Remove fill attributes for consistency
    .replace(/stroke=["'][^"']*["']/g, ''); // Remove stroke attributes

  return normalizedSVG;
}

/**
 * Convert SVG string to image buffer (PNG)
 * Note: This requires the 'canvas' package and a headless browser or SVG renderer
 * For production, consider using puppeteer or a dedicated SVG-to-image service
 * 
 * @param {string} svgString - SVG string
 * @param {number} width - Image width (default: 224)
 * @param {number} height - Image height (default: 224)
 * @returns {Promise<Buffer|null>} PNG image buffer or null on error
 */
async function svgToImageBuffer(svgString, width = 224, height = 224) {
  try {
    // This is a simplified version - in production you might want to use:
    // - puppeteer with headless Chrome
    // - sharp with librsvg
    // - cairosvg (Python) called via subprocess
    
    // For now, we'll use canvas if available, otherwise return null
    // and let the Python side handle SVG-to-image conversion
    if (typeof createCanvas === 'function') {
      const canvas = createCanvas(width, height);
      const ctx = canvas.getContext('2d');
      
      // Note: Canvas doesn't natively support SVG rendering
      // This would require additional libraries like svg2img or sharp
      // For now, return null and handle conversion in Python
      return null;
    }
    
    return null;
  } catch (error) {
    console.error('Error converting SVG to image:', error.message);
    return null;
  }
}

/**
 * Save SVG to file
 * @param {string} iconType - Icon type name
 * @param {string} svgContent - SVG string
 * @param {string} outputDir - Output directory (default: './rendered-icons')
 * @returns {Promise<string>} Path to saved file
 */
async function saveSVG(iconType, svgContent, outputDir = './rendered-icons') {
  await fs.mkdir(outputDir, { recursive: true });
  const filename = path.join(outputDir, `${iconType}.svg`);
  await fs.writeFile(filename, svgContent, 'utf8');
  return filename;
}

/**
 * Render icon to image file (PNG)
 * This is a placeholder - actual implementation depends on available libraries
 * @param {string} iconType - Icon type name
 * @param {string} outputDir - Output directory
 * @param {number} size - Image size in pixels
 * @returns {Promise<string|null>} Path to saved image or null
 */
async function renderIconToImage(iconType, outputDir = './rendered-icons', size = 224) {
  // First get SVG
  const svgContent = await renderIconToSVG(iconType);
  if (!svgContent) {
    return null;
  }

  // Normalize SVG
  const normalizedSVG = normalizeSVG(svgContent, size);
  
  // Save SVG (we'll convert to image in Python using cairosvg or similar)
  const svgPath = await saveSVG(iconType, normalizedSVG, outputDir);
  
  // Return SVG path - actual PNG conversion will be done in Python
  return svgPath;
}

module.exports = {
  renderIconToSVG,
  normalizeSVG,
  svgToImageBuffer,
  saveSVG,
  renderIconToImage
};

