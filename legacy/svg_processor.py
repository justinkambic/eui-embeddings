"""
SVG Processing Utilities

Functions for normalizing SVG code and converting to images for embedding.
"""

import re
from typing import Optional
from cairosvg import svg2png
from PIL import Image
import io

def normalize_svg(svg_content: str, target_size: int = 224) -> str:
    """
    Normalize SVG: standardize size, remove metadata, ensure consistent format.
    
    Args:
        svg_content: Raw SVG string
        target_size: Target size in pixels (default: 224)
    
    Returns:
        Normalized SVG string
    """
    if not svg_content:
        return None
    
    # Extract viewBox or create one
    viewbox_match = re.search(r'viewBox=["\']([^"\']+)["\']', svg_content)
    width_match = re.search(r'width=["\']([^"\']+)["\']', svg_content)
    height_match = re.search(r'height=["\']([^"\']+)["\']', svg_content)
    
    viewbox = '0 0 24 24'  # Default EUI icon viewBox
    if viewbox_match:
        viewbox = viewbox_match.group(1)
    elif width_match and height_match:
        width = float(re.sub(r'[^\d.]', '', width_match.group(1)) or 24)
        height = float(re.sub(r'[^\d.]', '', height_match.group(1)) or 24)
        viewbox = f'0 0 {width} {height}'
    
    # Create normalized SVG with consistent size
    # Replace opening svg tag
    normalized = re.sub(
        r'<svg[^>]*>',
        f'<svg viewBox="{viewbox}" width="{target_size}" height="{target_size}" xmlns="http://www.w3.org/2000/svg">',
        svg_content,
        count=1
    )
    
    # Remove fill and stroke attributes for consistency (optional)
    # normalized = re.sub(r'fill=["\'][^"\']*["\']', '', normalized)
    # normalized = re.sub(r'stroke=["\'][^"\']*["\']', '', normalized)
    
    return normalized

def svg_to_image(svg_content: str, target_size: int = 224) -> Image.Image:
    """
    Convert SVG string to PIL Image.
    
    Args:
        svg_content: SVG string
        target_size: Target size in pixels (default: 224)
    
    Returns:
        PIL Image (RGB, target_size x target_size)
    """
    # Normalize SVG first
    normalized_svg = normalize_svg(svg_content, target_size)
    
    # Convert SVG to PNG
    try:
        png_data = svg2png(
            bytestring=normalized_svg.encode('utf-8'),
            output_width=target_size,
            output_height=target_size
        )
    except Exception as e:
        raise ValueError(f"Error converting SVG to PNG: {str(e)}")
    
    # Load PNG as PIL Image
    image = Image.open(io.BytesIO(png_data))
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    return image

def extract_svg_layers(svg_content: str) -> list:
    """
    Extract individual layers/paths from SVG.
    This is a simplified version - for complex SVGs, you might want to use
    a proper SVG parser like svgpathtools.
    
    Args:
        svg_content: SVG string
    
    Returns:
        List of layer/path strings
    """
    # Extract all path elements
    paths = re.findall(r'<path[^>]*>', svg_content, re.IGNORECASE)
    
    # Extract all circle elements
    circles = re.findall(r'<circle[^>]*>', svg_content, re.IGNORECASE)
    
    # Extract all rect elements
    rects = re.findall(r'<rect[^>]*>', svg_content, re.IGNORECASE)
    
    # Combine all elements
    layers = paths + circles + rects
    
    return layers

