#!/usr/bin/env node
/**
 * Token Renderer Microservice
 * 
 * Standalone Node.js service for rendering EuiToken components to SVG.
 * Can be controlled by Python scripts for automated indexing.
 */

const express = require('express');
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const rateLimit = require('express-rate-limit');

const app = express();
const HOST = process.env.TOKEN_RENDERER_HOST || "0.0.0.0";
const PORT = process.env.TOKEN_RENDERER_PORT || process.env.PORT || 3002;
const BASE_URL = process.env.TOKEN_RENDERER_BASE_URL || `http://${HOST}:${PORT}`;

// Rate limiting configuration (stricter for resource-intensive rendering)
const RATE_LIMIT_PER_MINUTE = parseInt(process.env.TOKEN_RENDERER_RATE_LIMIT || "10", 10);
const renderRateLimit = rateLimit({
  windowMs: 60 * 1000, // 1 minute
  max: RATE_LIMIT_PER_MINUTE, // Limit each IP to 10 requests per windowMs
  message: 'Too many rendering requests from this IP, please try again later.',
  standardHeaders: true, // Return rate limit info in the `RateLimit-*` headers
  legacyHeaders: false, // Disable the `X-RateLimit-*` headers
});

// Middleware
app.use(express.json());

// Apply rate limiting to all routes (rendering is resource-intensive)
app.use(renderRateLimit);

// Serve static files from dist (webpack build output)
const distPath = path.join(__dirname, 'dist');
if (fs.existsSync(distPath)) {
  app.use(express.static(distPath));
}

// Initialize Playwright browser instance (reused across requests)
let browser = null;

async function getBrowser() {
  if (!browser) {
    browser = await chromium.launch({
      headless: true
    });
  }
  return browser;
}

// Cleanup browser on process exit
process.on('SIGINT', async () => {
  if (browser) {
    await browser.close();
  }
  process.exit(0);
});

process.on('SIGTERM', async () => {
  if (browser) {
    await browser.close();
  }
  process.exit(0);
});


/**
 * Render EuiIcon or EuiToken to base64 PNG screenshot using Playwright
 * Opens the webpack-built frontend page and captures the rendered element as an image
 * 
 * @param {string} iconType - The icon type name
 * @param {string} componentType - Component type: 'icon' or 'token' (required)
 * @param {string} size - Icon/token size (default: 'm')
 * @returns {Promise<string|null>} Base64 PNG string or null on error
 */
async function renderIconToImage(iconType, componentType, size = 'm') {
  if (!componentType || (componentType !== 'icon' && componentType !== 'token')) {
    throw new Error('componentType is required and must be "icon" or "token"');
  }
  let page = null;
  try {
    // Check if dist directory exists (webpack build output)
    if (!fs.existsSync(distPath)) {
      console.error('Frontend not built. Run "npm run build" first.');
      return null;
    }
    
    const browserInstance = await getBrowser();
    page = await browserInstance.newPage();
    
    // Navigate to the frontend page with query parameters
    const url = `${BASE_URL}/?iconType=${encodeURIComponent(iconType)}&componentType=${encodeURIComponent(componentType)}&size=${encodeURIComponent(size)}`;
    await page.goto(url, { waitUntil: 'networkidle' });
    
    // Wait for the SVG to load and have content
    await page.waitForFunction(() => {
      const svg = document.querySelector('svg');
      return svg && svg.innerHTML.trim().length > 0;
    }, { timeout: 10000 }).catch(() => {
      console.warn(`Timeout waiting for SVG to load for ${iconType}`);
    });
    
    // Debug: Log what component is actually rendered
    const renderedComponent = await page.evaluate(() => {
      const tokenSpan = document.querySelector('span.euiToken, [class*="euiToken"]');
      const iconSvg = document.querySelector('svg.euiIcon, svg[class*="euiIcon"]');
      return {
        hasToken: !!tokenSpan,
        hasIcon: !!iconSvg,
        componentType: tokenSpan ? 'token' : (iconSvg ? 'icon' : 'unknown')
      };
    });
    console.log(`Rendering ${componentType} for ${iconType}, detected:`, renderedComponent);
    
    // Find the element to screenshot based on component type
    let elementToScreenshot = null;
    
    if (componentType === 'token') {
      // For EuiToken: find the span wrapper that contains the SVG
      // EuiToken renders as: <span class="euiToken ..."><svg>...</svg></span>
      elementToScreenshot = await page.$('span.euiToken, [class*="euiToken"]');
      
      if (!elementToScreenshot) {
        // Fallback: look for any span containing an SVG with euiToken class
        elementToScreenshot = await page.$('span:has(svg)');
      }
    } else {
      // For EuiIcon: find the SVG element directly, but NOT inside a token
      // EuiIcon renders as: <svg class="euiIcon ...">...</svg>
      // We need to exclude SVGs that are inside token wrappers
      elementToScreenshot = await page.evaluateHandle(() => {
        // Find all SVGs
        const svgs = document.querySelectorAll('svg');
        for (const svg of svgs) {
          // Check if this SVG is NOT inside a token wrapper
          const parent = svg.closest('span.euiToken, [class*="euiToken"]');
          if (!parent) {
            // This SVG is not inside a token, so it's an icon
            return svg;
          }
        }
        // If no standalone SVG found, return the first SVG (shouldn't happen)
        return svgs[0] || null;
      });
      
      if (elementToScreenshot && elementToScreenshot.asElement) {
        elementToScreenshot = elementToScreenshot.asElement();
      } else {
        elementToScreenshot = null;
      }
      
      // Fallback: try to find SVG with euiIcon class
      if (!elementToScreenshot) {
        elementToScreenshot = await page.$('svg.euiIcon, svg[class*="euiIcon"]');
      }
    }
    
    if (!elementToScreenshot) {
      await page.close();
      console.warn(`No ${componentType} element found for ${iconType}`);
      return null;
    }
    
    // Take screenshot of the element (includes all styling)
    // Get screenshot as buffer and convert to base64 string
    const screenshotBuffer = await elementToScreenshot.screenshot();
    
    await page.close();
    
    // Convert Buffer to base64 string
    if (!screenshotBuffer || screenshotBuffer.length === 0) {
      console.warn(`Screenshot is empty for ${iconType}`);
      return null;
    }
    
    // Convert buffer to base64 string
    const screenshotBase64 = screenshotBuffer.toString('base64');
    
    return screenshotBase64;
  } catch (error) {
    console.error(`Error rendering ${componentType} ${iconType}:`, error.message);
    console.error(error.stack);
    if (page) {
      try {
        await page.close();
      } catch (e) {
        // Ignore close errors
      }
    }
    return null;
  }
}

/**
 * Health check endpoint
 */
app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: 'token-renderer' });
});

// Frontend route - serve the webpack-built frontend
app.get('/', (req, res) => {
  const indexPath = path.join(__dirname, 'dist', 'index.html');
  if (fs.existsSync(indexPath)) {
    res.sendFile(indexPath);
  } else {
    res.status(404).send('Frontend not built. Run "npm run build" first.');
  }
});

/**
 * Render icon or token endpoint
 * POST /render-icon
 * Body: { iconName: string, componentType: string ('icon' or 'token'), size?: string }
 * Returns: { image: string (base64 PNG), iconName: string, componentType: string, size: string }
 */
app.post('/render-icon', async (req, res) => {
  const { iconName, componentType, size = 'm' } = req.body;
  
  if (!iconName) {
    return res.status(400).json({ 
      error: 'Missing required field: iconName' 
    });
  }
  
  if (!componentType) {
    return res.status(400).json({ 
      error: 'Missing required field: componentType (must be "icon" or "token")' 
    });
  }
  
  if (componentType !== 'icon' && componentType !== 'token') {
    return res.status(400).json({ 
      error: 'componentType must be "icon" or "token"' 
    });
  }
  
  try {
    const imageBase64 = await renderIconToImage(iconName, componentType, size);
    
    if (!imageBase64) {
      return res.status(500).json({ 
        error: `Failed to render ${componentType} for icon: ${iconName}` 
      });
    }
    
    res.json({ 
      image: imageBase64,
      iconName: iconName,
      componentType: componentType,
      size: size
    });
  } catch (error) {
    console.error(`Error in render-icon endpoint (${componentType}):`, error);
    res.status(500).json({ 
      error: error.message || 'Internal server error' 
    });
  }
});

/**
 * Get SVG/HTML content for icon or token
 * POST /render-svg
 * Body: { iconName: string, componentType: string ('icon' or 'token'), size?: string }
 * Returns: { svgContent: string (HTML/SVG), iconName: string, componentType: string, size: string }
 */
async function renderIconToSVG(iconType, componentType, size = 'm') {
  if (!componentType || (componentType !== 'icon' && componentType !== 'token')) {
    throw new Error('componentType is required and must be "icon" or "token"');
  }
  let page = null;
  try {
    if (!fs.existsSync(distPath)) {
      console.error('Frontend not built. Run "npm run build" first.');
      return null;
    }
    
    const browserInstance = await getBrowser();
    page = await browserInstance.newPage();
    
    const url = `${BASE_URL}/?iconType=${encodeURIComponent(iconType)}&componentType=${encodeURIComponent(componentType)}&size=${encodeURIComponent(size)}`;
    await page.goto(url, { waitUntil: 'networkidle' });
    
    // Wait for the SVG to load
    await page.waitForFunction(() => {
      const svg = document.querySelector('svg');
      return svg && svg.innerHTML.trim().length > 0;
    }, { timeout: 10000 }).catch(() => {
      console.warn(`Timeout waiting for SVG to load for ${iconType}`);
    });
    
    // Extract the SVG/HTML content
    const svgContent = await page.evaluate((compType) => {
      if (compType === 'token') {
        // For token, get the outerHTML of the span wrapper
        const tokenSpan = document.querySelector('span.euiToken, [class*="euiToken"]');
        return tokenSpan ? tokenSpan.outerHTML : null;
      } else {
        // For icon, get the SVG element
        const svgs = document.querySelectorAll('svg');
        for (const svg of svgs) {
          const parent = svg.closest('span.euiToken, [class*="euiToken"]');
          if (!parent) {
            return svg.outerHTML;
          }
        }
        return svgs[0] ? svgs[0].outerHTML : null;
      }
    }, componentType);
    
    await page.close();
    
    return svgContent;
  } catch (error) {
    console.error(`Error rendering ${componentType} SVG ${iconType}:`, error.message);
    if (page) {
      try {
        await page.close();
      } catch (e) {
        // Ignore close errors
      }
    }
    return null;
  }
}

app.post('/render-svg', async (req, res) => {
  const { iconName, componentType, size = 'm' } = req.body;
  
  if (!iconName) {
    return res.status(400).json({ 
      error: 'Missing required field: iconName' 
    });
  }
  
  if (!componentType || (componentType !== 'icon' && componentType !== 'token')) {
    return res.status(400).json({ 
      error: 'componentType must be "icon" or "token"' 
    });
  }
  
  try {
    const svgContent = await renderIconToSVG(iconName, componentType, size);
    
    if (!svgContent) {
      return res.status(500).json({ 
        error: `Failed to render ${componentType} SVG for icon: ${iconName}` 
      });
    }
    
    res.json({ 
      svgContent: svgContent,
      iconName: iconName,
      componentType: componentType,
      size: size
    });
  } catch (error) {
    console.error(`Error in render-svg endpoint (${componentType}):`, error);
    res.status(500).json({ 
      error: error.message || 'Internal server error' 
    });
  }
});

/**
 * Render token endpoint (backward compatibility)
 * POST /render-token
 * Body: { iconName: string, size?: string }
 * Returns: { image: string (base64 PNG), iconName: string, size: string }
 */
app.post('/render-token', async (req, res) => {
  const { iconName, size = 'm' } = req.body;
  
  if (!iconName) {
    return res.status(400).json({ 
      error: 'Missing required field: iconName' 
    });
  }
  
  try {
    const imageBase64 = await renderIconToImage(iconName, 'token', size);
    
    if (!imageBase64) {
      return res.status(500).json({ 
        error: `Failed to render token for icon: ${iconName}` 
      });
    }
    
    res.json({ 
      image: imageBase64,
      iconName: iconName,
      size: size
    });
  } catch (error) {
    console.error('Error in render-token endpoint:', error);
    res.status(500).json({ 
      error: error.message || 'Internal server error' 
    });
  }
});

/**
 * Batch render icons/tokens endpoint
 * POST /render-icons
 * Body: { icons: Array<{ iconName: string, componentType?: string, size?: string }> }
 * Returns: { results: Array<{ iconName: string, componentType: string, size: string, image: string (base64 PNG) | null, error: string | null }> }
 */
app.post('/render-icons', async (req, res) => {
  const { icons } = req.body;
  
  if (!icons || !Array.isArray(icons)) {
    return res.status(400).json({ 
      error: 'Missing or invalid field: icons (must be an array)' 
    });
  }
  
  try {
    const results = await Promise.all(
      icons.map(async ({ iconName, componentType = 'token', size = 'm' }) => {
        const imageBase64 = await renderIconToImage(iconName, componentType, size);
        return {
          iconName,
          componentType,
          size,
          image: imageBase64 || null,
          error: imageBase64 ? null : `Failed to render ${componentType} for icon: ${iconName}`
        };
      })
    );
    
    res.json({ results });
  } catch (error) {
    console.error('Error in render-icons endpoint:', error);
    res.status(500).json({ 
      error: error.message || 'Internal server error' 
    });
  }
});

/**
 * Batch render tokens endpoint (backward compatibility)
 * POST /render-tokens
 * Body: { tokens: Array<{ iconName: string, size?: string }> }
 * Returns: { results: Array<{ iconName: string, size: string, image: string (base64 PNG) | null, error: string | null }> }
 */
app.post('/render-tokens', async (req, res) => {
  const { tokens } = req.body;
  
  if (!tokens || !Array.isArray(tokens)) {
    return res.status(400).json({ 
      error: 'Missing or invalid field: tokens (must be an array)' 
    });
  }
  
  try {
    const results = await Promise.all(
      tokens.map(async ({ iconName, size = 'm' }) => {
        const imageBase64 = await renderIconToImage(iconName, 'token', size);
        return {
          iconName,
          size,
          image: imageBase64 || null,
          error: imageBase64 ? null : `Failed to render token for icon: ${iconName}`
        };
      })
    );
    
    res.json({ results });
  } catch (error) {
    console.error('Error in render-tokens endpoint:', error);
    res.status(500).json({ 
      error: error.message || 'Internal server error' 
    });
  }
});

// Start server
app.listen(PORT, HOST, () => {
  console.log(`Icon renderer service running on ${HOST}:${PORT}`);
  console.log(`Health check: ${BASE_URL}/health`);
  console.log(`Render icon: POST ${BASE_URL}/render-icon`);
  console.log(`Render token: POST ${BASE_URL}/render-token (backward compat)`);
  console.log(`Frontend: ${BASE_URL}/`);
  console.log(`\nTo build frontend: npm run build`);
  console.log(`To run frontend dev server: npm run dev:frontend`);
});

