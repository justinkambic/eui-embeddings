#!/usr/bin/env python3
"""
Debug SVG to PNG conversion

Check what's happening during SVG-to-PNG conversion
"""

import os
import sys
from cairosvg import svg2png
from PIL import Image
import io
import numpy as np

def test_svg_conversion(svg_content: str, icon_name: str):
    """Test SVG to PNG conversion for a single SVG"""
    print(f"\n{'='*60}")
    print(f"Testing: {icon_name}")
    print(f"{'='*60}")
    print(f"SVG size: {len(svg_content)} chars")
    print(f"SVG preview (first 200 chars): {svg_content[:200]}...")
    
    try:
        # Convert SVG to PNG
        print("\nConverting SVG to PNG...")
        png_data = svg2png(bytestring=svg_content.encode('utf-8'), output_width=224, output_height=224)
        
        print(f"  PNG data size: {len(png_data)} bytes")
        
        if not png_data or len(png_data) == 0:
            print("  ⚠️  ERROR: PNG data is empty!")
            return None
        
        # Load PNG as PIL Image
        print("Loading PNG as PIL Image...")
        image = Image.open(io.BytesIO(png_data))
        print(f"  Image mode: {image.mode}")
        print(f"  Image size: {image.size}")
        
        if image.mode != 'RGB':
            print(f"  Converting to RGB...")
            image = image.convert('RGB')
        
        # Check image content
        print("Analyzing image content...")
        image_array = np.array(image)
        print(f"  Image array shape: {image_array.shape}")
        print(f"  Image array dtype: {image_array.dtype}")
        
        # Check for empty/solid color images
        unique_colors = len(np.unique(image_array.reshape(-1, image_array.shape[-1]), axis=0))
        print(f"  Unique colors: {unique_colors}")
        
        if unique_colors == 1:
            color = image_array[0, 0]
            print(f"  ⚠️  WARNING: Image has only one color: {color}")
            print(f"  This might indicate a conversion failure!")
        
        # Check pixel value ranges
        min_val = np.min(image_array)
        max_val = np.max(image_array)
        mean_val = np.mean(image_array)
        print(f"  Pixel value range: [{min_val}, {max_val}]")
        print(f"  Mean pixel value: {mean_val:.2f}")
        
        # Check if image is all zeros or all same value
        if np.all(image_array == 0):
            print(f"  ⚠️  ERROR: Image is all zeros (black)!")
        elif np.all(image_array == image_array[0, 0]):
            print(f"  ⚠️  ERROR: Image is solid color!")
        
        return image
        
    except Exception as e:
        print(f"  ✗ ERROR during conversion: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    svgpaths_file = os.path.join(script_dir, ".svgpaths")
    
    # Test with problematic icons
    problematic_icons = ["grid", "index_mapping", "search"]
    
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
        
        image = test_svg_conversion(svg_content, icon_name)
        
        if image:
            print(f"  ✓ Conversion successful")
        else:
            print(f"  ✗ Conversion failed")

if __name__ == "__main__":
    main()

