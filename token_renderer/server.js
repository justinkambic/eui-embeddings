#!/usr/bin/env node
/**
 * Token Renderer Microservice
 * 
 * Standalone Node.js service for rendering EuiToken components to SVG.
 * Can be controlled by Python scripts for automated indexing.
 */

const express = require('express');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const { EuiToken } = require('@elastic/eui');

const app = express();
const PORT = process.env.TOKEN_RENDERER_PORT || 3002;

// Middleware
app.use(express.json());

/**
 * Render EuiToken to SVG string
 * @param {string} iconType - The icon type name
 * @param {string} tokenType - Token type (default: 'string')
 * @param {string} size - Token size (default: 'm')
 * @returns {string|null} SVG string or null on error
 */
function renderTokenToSVG(iconType, tokenType = 'string', size = 'm') {
  try {
    // EuiToken props based on TOKEN_INDEXING_PLAN.md
    // iconType: required, the icon type name
    // tokenType: optional, token type (e.g., 'string', 'number', 'boolean')
    // size: optional, token size (default: 'm')
    const tokenElement = React.createElement(EuiToken, {
      iconType: iconType,
      tokenType: tokenType,
      size: size
    });
    
    const htmlString = renderToStaticMarkup(tokenElement);
    
    // Extract just the SVG part
    // EuiToken renders as an SVG element, so we need to extract it
    const svgMatch = htmlString.match(/<svg[^>]*>.*<\/svg>/s);
    if (svgMatch) {
      return svgMatch[0];
    }
    
    // If no SVG found, return the full HTML (might be wrapped in a span or div)
    // Try to find any SVG element
    const anySvgMatch = htmlString.match(/<svg[^>]*>.*?<\/svg>/s);
    if (anySvgMatch) {
      return anySvgMatch[0];
    }
    
    // Return the full HTML as fallback
    return htmlString;
  } catch (error) {
    console.error(`Error rendering token ${iconType}:`, error.message);
    return null;
  }
}

/**
 * Health check endpoint
 */
app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: 'token-renderer' });
});

/**
 * Render token endpoint
 * POST /render-token
 * Body: { iconName: string, tokenType?: string, size?: string }
 */
app.post('/render-token', (req, res) => {
  const { iconName, tokenType = 'string', size = 'm' } = req.body;
  
  if (!iconName) {
    return res.status(400).json({ 
      error: 'Missing required field: iconName' 
    });
  }
  
  try {
    const svg = renderTokenToSVG(iconName, tokenType, size);
    
    if (!svg) {
      return res.status(500).json({ 
        error: `Failed to render token for icon: ${iconName}` 
      });
    }
    
    res.json({ 
      svg: svg,
      iconName: iconName,
      tokenType: tokenType,
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
 * Batch render tokens endpoint
 * POST /render-tokens
 * Body: { tokens: Array<{ iconName: string, tokenType?: string, size?: string }> }
 */
app.post('/render-tokens', (req, res) => {
  const { tokens } = req.body;
  
  if (!tokens || !Array.isArray(tokens)) {
    return res.status(400).json({ 
      error: 'Missing or invalid field: tokens (must be an array)' 
    });
  }
  
  try {
    const results = tokens.map(({ iconName, tokenType = 'string', size = 'm' }) => {
      const svg = renderTokenToSVG(iconName, tokenType, size);
      return {
        iconName,
        tokenType,
        size,
        svg: svg || null,
        error: svg ? null : `Failed to render token for icon: ${iconName}`
      };
    });
    
    res.json({ results });
  } catch (error) {
    console.error('Error in render-tokens endpoint:', error);
    res.status(500).json({ 
      error: error.message || 'Internal server error' 
    });
  }
});

// Start server
app.listen(PORT, () => {
  console.log(`Token renderer service running on port ${PORT}`);
  console.log(`Health check: http://localhost:${PORT}/health`);
  console.log(`Render token: POST http://localhost:${PORT}/render-token`);
});

