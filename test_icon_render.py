#!/usr/bin/env python3
"""
Test Icon Renderer Script

Tests the icon renderer service by rendering both an icon and token version
of the same icon and saving them as images.

Usage:
    python test_icon_render.py <icon_name> [--output-dir output_dir]
    python test_icon_render.py search --output-dir ./test_output
"""

import os
import sys
import argparse
import requests
import base64
from pathlib import Path
from PIL import Image
import io

# Configuration
ICON_RENDERER_URL = os.getenv("ICON_RENDERER_URL", "http://localhost:3002/render-icon")


def render_icon(icon_name: str, component_type: str = 'icon', size: str = 'm') -> str:
    """Render icon or token using icon renderer service
    Returns base64-encoded PNG image string
    """
    try:
        response = requests.post(
            ICON_RENDERER_URL,
            json={"iconName": icon_name, "componentType": component_type, "size": size},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        # Debug: check what we got
        if "image" not in data:
            print(f"  ✗ Response missing 'image' field. Keys: {list(data.keys())}")
            if "error" in data:
                print(f"  Error: {data['error']}")
            return None
        
        image_data = data.get("image")
        
        # Check if it's actually a string
        if not isinstance(image_data, str):
            print(f"  ✗ 'image' is not a string, got type: {type(image_data)}")
            print(f"  Value: {image_data}")
            return None
        
        return image_data
    except requests.exceptions.RequestException as e:
        print(f"✗ Error rendering {component_type}: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"  Response: {e.response.text}")
        return None


def save_base64_image(image_base64: str, output_path: str, size: int = None):
    """Save base64-encoded PNG image to file
    Optionally resize the image if size is provided
    """
    try:
        # Decode base64 image
        image_data = base64.b64decode(image_base64)
        
        if not image_data or len(image_data) == 0:
            raise ValueError("Base64 image data is empty")
        
        # Load image with PIL
        img = Image.open(io.BytesIO(image_data))
        
        # Resize if requested
        if size:
            img = img.resize((size, size), Image.Resampling.LANCZOS)
        
        # Save PNG
        img.save(output_path, 'PNG')
        
        return True
    except Exception as e:
        print(f"✗ Error saving image: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Test icon renderer and save both icon and token versions as images",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument("icon_name", help="Icon name to render (both icon and token)")
    parser.add_argument("--output-dir", "-o", default=".", help="Output directory for images (default: current directory)")
    parser.add_argument("--size", type=int, default=224, help="Output image size in pixels (default: 224)")
    parser.add_argument("--icon-size", default="m", choices=["xs", "s", "m", "l", "xl"], help="Icon/token size (default: m)")
    
    args = parser.parse_args()
    
    icon_name = args.icon_name
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    icon_output = output_dir / f"{icon_name}_icon.png"
    token_output = output_dir / f"{icon_name}_token.png"
    
    print(f"Testing icon renderer for: {icon_name}")
    print(f"Icon/token size: {args.icon_size}")
    print(f"Output directory: {output_dir}")
    print()
    
    # Render icon version
    print(f"Rendering icon version via {ICON_RENDERER_URL}...")
    icon_base64 = render_icon(icon_name, component_type='icon', size=args.icon_size)
    
    if not icon_base64:
        print("✗ Failed to render icon")
        sys.exit(1)
    
    print(f"✓ Icon rendered (base64 image, {len(icon_base64)} chars)")
    
    # Save icon PNG
    print(f"Saving icon PNG ({args.size}x{args.size} if resizing)...")
    if save_base64_image(icon_base64, str(icon_output), args.size if args.size != 224 else None):
        print(f"✓ Icon saved to: {icon_output}")
    else:
        print("✗ Failed to save icon")
        sys.exit(1)
    
    print()
    
    # Render token version
    print(f"Rendering token version via {ICON_RENDERER_URL}...")
    token_base64 = render_icon(icon_name, component_type='token', size=args.icon_size)
    
    if not token_base64:
        print("✗ Failed to render token")
        sys.exit(1)
    
    print(f"✓ Token rendered (base64 image, {len(token_base64)} chars)")
    
    # Save token PNG
    print(f"Saving token PNG ({args.size}x{args.size} if resizing)...")
    if save_base64_image(token_base64, str(token_output), args.size if args.size != 224 else None):
        print(f"✓ Token saved to: {token_output}")
    else:
        print("✗ Failed to save token")
        sys.exit(1)
    
    # Display image info
    try:
        icon_img = Image.open(icon_output)
        token_img = Image.open(token_output)
        print(f"\nIcon image info:")
        print(f"  Size: {icon_img.size[0]}x{icon_img.size[1]} pixels")
        print(f"  Mode: {icon_img.mode}")
        print(f"\nToken image info:")
        print(f"  Size: {token_img.size[0]}x{token_img.size[1]} pixels")
        print(f"  Mode: {token_img.mode}")
    except Exception as e:
        print(f"  Could not read image info: {e}")
    
    print(f"\n✓ Success! Both images saved:")
    print(f"  Icon: {icon_output}")
    print(f"  Token: {token_output}")


if __name__ == "__main__":
    main()

