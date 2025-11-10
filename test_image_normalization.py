#!/usr/bin/env python3
"""
Test Image Normalization

Shows the normalized image output that's used for search.
This helps debug why search results might not be accurate.
"""

import os
import sys
import argparse
from PIL import Image
from image_processor import normalize_search_image

def test_normalization(image_path: str, output_path: str = None):
    """Test image normalization and show the result"""
    print(f"Reading image: {image_path}")
    
    # Load original image
    original_image = Image.open(image_path)
    print(f"  Original size: {original_image.size}")
    print(f"  Original mode: {original_image.mode}")
    
    # Normalize the image
    print("\nNormalizing image...")
    normalized_image = normalize_search_image(original_image, target_size=224)
    
    print(f"  Normalized size: {normalized_image.size}")
    print(f"  Normalized mode: {normalized_image.mode}")
    
    # Get image statistics
    import numpy as np
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
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        output_path = f"{base_name}_normalized.png"
        normalized_image.save(output_path)
        print(f"\n✓ Normalized image saved to: {output_path}")
    
    # Also save a side-by-side comparison
    comparison = Image.new('RGB', (original_image.width + 224, max(original_image.height, 224)))
    comparison.paste(original_image.resize((original_image.width, original_image.height)), (0, 0))
    comparison.paste(normalized_image, (original_image.width, 0))
    
    comparison_path = f"{os.path.splitext(output_path)[0]}_comparison.png"
    comparison.save(comparison_path)
    print(f"✓ Comparison image saved to: {comparison_path}")
    
    return normalized_image

def main():
    parser = argparse.ArgumentParser(
        description="Test image normalization and show the result",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "image_file",
        help="Path to image file to normalize"
    )
    
    parser.add_argument(
        "--output",
        "-o",
        help="Output path for normalized image (default: <original>_normalized.png)"
    )
    
    args = parser.parse_args()
    
    # Resolve path
    image_path = args.image_file
    if not os.path.isabs(image_path):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        image_path = os.path.join(script_dir, image_path)
        image_path = os.path.normpath(image_path)
    
    if not os.path.isfile(image_path):
        print(f"✗ Error: Image file not found: {image_path}")
        sys.exit(1)
    
    test_normalization(image_path, args.output)

if __name__ == "__main__":
    main()

