#!/usr/bin/env python3
"""
Test SVG Normalization

Shows the normalized image output that's used for SVG embedding.
This helps compare how SVGs are normalized when indexed vs how search images are normalized.
"""

import os
import sys
import argparse
import re
from PIL import Image
import io
import numpy as np
from cairosvg import svg2png

def normalize_svg_for_embedding(svg_content: str, target_size: int = 224) -> Image.Image:
    """
    Normalize SVG the same way embed.py does for embedding.
    
    This matches the exact process used in embed.py for SVG embedding.
    """
    # Preprocess SVG: ensure it has proper fill and background for cairosvg
    # This matches the logic in embed.py
    
    # Add white background rectangle first
    viewbox_match = re.search(r'viewBox=["\']([^"\']+)["\']', svg_content)
    if viewbox_match:
        viewbox = viewbox_match[1]
        coords = viewbox.split()
        if len(coords) == 4:
            x, y, width, height = map(float, coords)
            # Insert white background rectangle after opening <svg> tag
            bg_rect = f'<rect x="{x}" y="{y}" width="{width}" height="{height}" fill="white"/>'
            svg_content = re.sub(r'(<svg[^>]*>)', r'\1' + bg_rect, svg_content, count=1)
    
    # Add fill="black" to all path elements that don't already have a fill attribute
    def add_fill_to_path(match):
        full_match = match.group(0)
        # Check if fill already exists
        if 'fill=' not in full_match:
            # Add fill="black" - insert after <path and before any existing attributes
            if ' ' in full_match:
                # Has attributes: <path attr1="val1" attr2="val2">
                return full_match.replace('<path ', '<path fill="black" ', 1)
            else:
                # No attributes: <path>
                return full_match.replace('<path>', '<path fill="black">', 1)
        return full_match
    
    # Replace all <path> tags that don't have fill
    svg_content = re.sub(r'<path\s*[^>]*>', add_fill_to_path, svg_content)
    
    # Convert SVG to PNG with background color
    png_data = svg2png(
        bytestring=svg_content.encode('utf-8'),
        output_width=target_size,
        output_height=target_size,
        background_color='white'
    )
    
    # Load PNG as PIL Image
    image = Image.open(io.BytesIO(png_data))
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    return image

def test_svg_normalization(svg_path: str, output_path: str = None):
    """Test SVG normalization and show the result"""
    print(f"Reading SVG: {svg_path}")
    
    # Read SVG content
    with open(svg_path, 'r', encoding='utf-8') as f:
        svg_content = f.read()
    
    print(f"  SVG size: {len(svg_content)} chars")
    
    # Normalize the SVG (same process as embed.py)
    print("\nNormalizing SVG (same as embed.py)...")
    normalized_image = normalize_svg_for_embedding(svg_content, target_size=224)
    
    print(f"  Normalized size: {normalized_image.size}")
    print(f"  Normalized mode: {normalized_image.mode}")
    
    # Get image statistics
    img_array = np.array(normalized_image)
    
    # Convert to grayscale for statistics if RGB
    if len(img_array.shape) == 3:
        gray_array = np.dot(img_array[...,:3], [0.299, 0.587, 0.114])
    else:
        gray_array = img_array
    
    min_val = np.min(gray_array)
    max_val = np.max(gray_array)
    mean_val = np.mean(gray_array)
    std_val = np.std(gray_array)
    
    print(f"\nNormalized image statistics:")
    print(f"  Min value: {min_val:.2f}")
    print(f"  Max value: {max_val:.2f}")
    print(f"  Mean value: {mean_val:.2f}")
    print(f"  Std deviation: {std_val:.2f}")
    
    # Check unique colors
    unique_colors = len(np.unique(gray_array))
    print(f"  Unique color values: {unique_colors}")
    
    # Check if it's mostly white/black
    white_pixels = np.sum(gray_array > 200)  # Pixels close to white
    black_pixels = np.sum(gray_array < 55)   # Pixels close to black
    total_pixels = gray_array.size
    
    print(f"\nColor distribution:")
    print(f"  White pixels (>200): {white_pixels} ({100*white_pixels/total_pixels:.1f}%)")
    print(f"  Black pixels (<55): {black_pixels} ({100*black_pixels/total_pixels:.1f}%)")
    print(f"  Gray pixels: {total_pixels - white_pixels - black_pixels} ({100*(total_pixels - white_pixels - black_pixels)/total_pixels:.1f}%)")
    
    # Save normalized image
    if output_path:
        normalized_image.save(output_path)
        print(f"\n✓ Normalized image saved to: {output_path}")
    else:
        # Save to default location
        base_name = os.path.splitext(os.path.basename(svg_path))[0]
        output_path = f"{base_name}_normalized.png"
        normalized_image.save(output_path)
        print(f"\n✓ Normalized image saved to: {output_path}")
    
    return normalized_image

def test_svg_by_icon_name(icon_name: str, svg_paths_file: str = ".svgpaths", output_path: str = None):
    """Test SVG normalization by icon name"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    svgpaths_file = os.path.join(script_dir, svg_paths_file)
    
    if not os.path.exists(svgpaths_file):
        print(f"✗ Error: {svgpaths_file} not found")
        return None
    
    # Find SVG file for this icon name
    with open(svgpaths_file, 'r', encoding='utf-8') as f:
        for line in f:
            path = line.strip()
            if not path or path.startswith('#'):
                continue
            
            # Resolve relative path
            if not os.path.isabs(path):
                path = os.path.join(script_dir, path)
                path = os.path.normpath(path)
            
            # Check if filename matches icon name
            filename = os.path.splitext(os.path.basename(path))[0]
            if filename == icon_name and os.path.isfile(path):
                print(f"Found SVG file: {path}")
                return test_svg_normalization(path, output_path)
    
    print(f"✗ Error: Could not find SVG file for icon '{icon_name}'")
    return None

def main():
    parser = argparse.ArgumentParser(
        description="Test SVG normalization and show the result",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "svg_file_or_icon",
        nargs="?",
        help="Path to SVG file or icon name"
    )
    
    parser.add_argument(
        "--icon-name",
        help="Icon name to look up in .svgpaths file"
    )
    
    parser.add_argument(
        "--svgpaths-file",
        default=".svgpaths",
        help="File containing SVG paths (default: .svgpaths)"
    )
    
    parser.add_argument(
        "--output",
        "-o",
        help="Output path for normalized image"
    )
    
    args = parser.parse_args()
    
    if args.icon_name:
        # Test by icon name
        test_svg_by_icon_name(args.icon_name, args.svgpaths_file, args.output)
    elif args.svg_file_or_icon:
        # Test by file path or icon name
        svg_path = args.svg_file_or_icon
        
        # Check if it's a file path
        if os.path.isfile(svg_path):
            test_svg_normalization(svg_path, args.output)
        else:
            # Try as icon name
            test_svg_by_icon_name(svg_path, args.svgpaths_file, args.output)
    else:
        print("✗ Error: No SVG file or icon name specified")
        print("Usage: python test_svg_normalization.py <svg_file>")
        print("   or: python test_svg_normalization.py --icon-name <icon_name>")
        sys.exit(1)

if __name__ == "__main__":
    main()

