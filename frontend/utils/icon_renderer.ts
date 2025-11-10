/**
 * Icon Renderer Utility
 * 
 * Renders EuiIcon components to standardized images (PNG) and extracts SVG code.
 * Uses React server-side rendering to generate icons.
 */

import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { EuiIcon } from '@elastic/eui';
import fs from 'fs/promises';
import path from 'path';

/**
 * Render an EuiIcon to SVG string
 * @param iconType - The icon type name
 * @param size - Icon size (default: 'xl')
 * @returns SVG string or null on error
 */
export async function renderIconToSVG(iconType: string, size: string = 'xl'): Promise<string | null> {
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
  } catch (error: any) {
    console.error(`Error rendering icon ${iconType}:`, error.message);
    return null;
  }
}

/**
 * Normalize SVG: standardize size, remove metadata, ensure consistent format
 * @param svgString - Raw SVG string
 * @param targetSize - Target size in pixels (default: 224)
 * @returns Normalized SVG string
 */
export function normalizeSVG(svgString: string, targetSize: number = 224): string | null {
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
 * Save SVG to file
 * @param iconType - Icon type name
 * @param svgContent - SVG string
 * @param outputDir - Output directory (default: './rendered-icons')
 * @returns Path to saved file
 */
export async function saveSVG(iconType: string, svgContent: string, outputDir: string = './rendered-icons'): Promise<string> {
  await fs.mkdir(outputDir, { recursive: true });
  const filename = path.join(outputDir, `${iconType}.svg`);
  await fs.writeFile(filename, svgContent, 'utf8');
  return filename;
}

/**
 * Render icon to image file (SVG)
 * This returns the SVG path - actual PNG conversion will be done in Python
 * @param iconType - Icon type name
 * @param outputDir - Output directory
 * @param size - Image size in pixels
 * @returns Path to saved SVG file or null
 */
export async function renderIconToImage(iconType: string, outputDir: string = './rendered-icons', size: number = 224): Promise<string | null> {
  // First get SVG
  const svgContent = await renderIconToSVG(iconType);
  if (!svgContent) {
    return null;
  }

  // Normalize SVG
  const normalizedSVG = normalizeSVG(svgContent, size);
  if (!normalizedSVG) {
    return null;
  }
  
  // Save SVG (we'll convert to image in Python using cairosvg or similar)
  const svgPath = await saveSVG(iconType, normalizedSVG, outputDir);
  
  // Return SVG path - actual PNG conversion will be done in Python
  return svgPath;
}

