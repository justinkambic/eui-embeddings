#!/usr/bin/env python3
"""
Test the fill fix for SVG conversion
"""

import os
import sys
import re
from cairosvg import svg2png
from PIL import Image
import io
import numpy as np

def add_fill_to_svg(svg_content: str) -> str:
    """Add fill="black" to paths that don't have fill"""
    # Add fill="black" to all path elements that don't already have a fill attribute
    def add_fill_to_path(match):
        path_content = match.group(1)
        # Check if fill already exists
        if 'fill=' not in path_content:
            # Add fill="black" at the start of the attributes
            return f'<path fill="black" {path_content}>'
        return match.group(0)
    
    # Replace all <path> tags that don't have fill
    svg_content = re.sub(r'<path\s+([^>]*?)>', add_fill_to_path, svg_content)
    
    # Also handle paths without attributes
    svg_content = re.sub(r'<path\s*>', '<path fill="black">', svg_content)
    
    return svg_content

def test_conversion(svg_content: str, icon_name: str):
    """Test SVG conversion with fill fix"""
    print(f"\n{'='*60}")
    print(f"Testing: {icon_name}")
    print(f"{'='*60}")
    
    # Original SVG
    print(f"Original SVG (first 200 chars): {svg_content[:200]}...")
    print(f"Has fill: {'fill=' in svg_content}")
    
    # Add fill
    svg_with_fill = add_fill_to_svg(svg_content)
    print(f"\nAfter adding fill (first 200 chars): {svg_with_fill[:200]}...")
    print(f"Has fill now: {'fill=' in svg_with_fill}")
    
    # Convert to PNG
    try:
        png_data = svg2png(bytestring=svg_with_fill.encode('utf-8'), output_width=224, output_height=224)
        image = Image.open(io.BytesIO(png_data))
        
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        print(f"\nImage size: {image.size}")
        print(f"Image mode: {image.mode}")
        
        # Check image content
        image_array = np.array(image)
        unique_colors = len(np.unique(image_array.reshape(-1, image_array.shape[-1]), axis=0))
        min_val = np.min(image_array)
        max_val = np.max(image_array)
        mean_val = np.mean(image_array)
        
        print(f"Unique colors: {unique_colors}")
        print(f"Pixel value range: [{min_val}, {max_val}]")
        print(f"Mean pixel value: {mean_val:.2f}")
        
        if unique_colors == 1:
            print(f"  ⚠️  WARNING: Image has only one color!")
            if np.all(image_array == 0):
                print(f"  ⚠️  ERROR: Image is all black!")
            else:
                print(f"  Color: {image_array[0, 0]}")
        else:
            print(f"  ✓ Image has multiple colors - conversion successful!")
        
        return image
        
    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    svgpaths_file = os.path.join(script_dir, ".svgpaths")
    
    # Test with problematic icons
    problematic_icons = ["grid", "search"]
    
    svg_files = {}
    with open(svgpaths_file, 'r', encoding='utf-8') as f:
        for line in f:
            path = line.strip()
            if not path or path.startswith('#'):
                continue
            
            if not os.path.isabs(path):
                path = os.path.join(script_dir, path)
                path = os.path.normpath(path)
            
            filename = os.path.splitext(os.path.basename(path))[0]
            if filename in problematic_icons and os.path.isfile(path):
                svg_files[filename] = path
    
    print(f"Found {len(svg_files)} SVG files to test\n")
    
    for icon_name, file_path in svg_files.items():
        with open(file_path, 'r', encoding='utf-8') as f:
            svg_content = f.read()
        
        image = test_conversion(svg_content, icon_name)

if __name__ == "__main__":
    main()

