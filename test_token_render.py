#!/usr/bin/env python3
"""
Test Token Renderer Script

Tests the token renderer service by rendering a token and saving it as an image.

Usage:
    python test_token_render.py <icon_name> [--output output.png]
    python test_token_render.py tokenSymbol --output tokenSymbol_token.png
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
TOKEN_RENDERER_URL = os.getenv("TOKEN_RENDERER_URL", "http://localhost:3002/render-token")
EUI_LOCATION = os.getenv("EUI_LOCATION", "./data/eui")
ICON_MAP_PATH = "packages/eui/src/components/icon/icon_map.ts"


def extract_type_to_path_map(icon_map_path: str) -> dict:
    """Extract typeToPathMap from TypeScript file"""
    if not os.path.exists(icon_map_path):
        print(f"✗ Icon map file not found: {icon_map_path}")
        return {}
    
    try:
        import re
        with open(icon_map_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the typeToPathMap object
        pattern = r'export\s+const\s+typeToPathMap\s*=\s*\{([^}]+)\}'
        match = re.search(pattern, content, re.DOTALL)
        
        if not match:
            print("✗ Could not find typeToPathMap in file")
            return {}
        
        object_content = match.group(1)
        
        # Extract key-value pairs
        mapping = {}
        pattern = r'(\w+):\s*["\']([^"\']+)["\']'
        for match in re.finditer(pattern, object_content):
            key = match.group(1)
            value = match.group(2)
            mapping[key] = value
        
        return mapping
    except Exception as e:
        print(f"✗ Error extracting typeToPathMap: {e}")
        return {}


def find_svg_file_in_repo(repo_dir: str, filename: str) -> str:
    """Find SVG file in repository by filename"""
    if not os.path.exists(repo_dir):
        return None
    
    exclude_dirs = {'.git', 'node_modules', 'dist', 'build', '__pycache__', '.next'}
    
    for root, dirs, files in os.walk(repo_dir):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            if file.endswith('.svg'):
                file_base = os.path.splitext(file)[0]
                if file_base == filename:
                    return os.path.join(root, file)
    
    return None


def read_svg_file(file_path: str) -> str:
    """Read SVG file content"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def render_token(icon_name: str, size: str = 'm') -> str:
    """Render token using token renderer service
    Returns base64-encoded PNG image string
    """
    try:
        response = requests.post(
            TOKEN_RENDERER_URL,
            json={"iconName": icon_name, "size": size},
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
        print(f"✗ Error rendering token: {e}")
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
        description="Test token renderer and save output as image",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument("icon_name", help="Icon name to render as token")
    parser.add_argument("--output", "-o", default=None, help="Output PNG file path (default: <icon_name>_token.png)")
    parser.add_argument("--size", type=int, default=224, help="Output image size in pixels (default: 224)")
    parser.add_argument("--token-size", default="m", choices=["xs", "s", "m", "l", "xl"], help="Token size (default: m)")
    parser.add_argument("--eui-location", default=None, help=f"EUI repository location (default: from EUI_LOCATION env var or {EUI_LOCATION})")
    parser.add_argument("--svg-file", default=None, help="Direct path to SVG file (skips EUI repo lookup)")
    
    args = parser.parse_args()
    
    icon_name = args.icon_name
    output_path = args.output or f"{icon_name}_token.png"
    
    print(f"Testing token renderer for icon: {icon_name}")
    print(f"Token size: {args.token_size}")
    print()
    
    # Render token - API returns base64 PNG image
    print(f"Rendering token via {TOKEN_RENDERER_URL}...")
    image_base64 = render_token(icon_name, args.token_size)
    
    if not image_base64:
        print("✗ Failed to render token")
        sys.exit(1)
    
    print(f"✓ Token rendered (base64 image, {len(image_base64)} chars)")
    
    # Save PNG (optionally resize)
    print(f"Saving PNG ({args.size}x{args.size} if resizing)...")
    if save_base64_image(image_base64, output_path, args.size if args.size != 224 else None):
        print(f"✓ Saved to: {output_path}")
        
        # Display image info
        try:
            img = Image.open(output_path)
            print(f"\nImage info:")
            print(f"  Size: {img.size[0]}x{img.size[1]} pixels")
            print(f"  Mode: {img.mode}")
        except Exception as e:
            print(f"  Could not read image info: {e}")
    else:
        print("✗ Failed to save image")
        sys.exit(1)
    
    print(f"\n✓ Success! Token image saved to: {output_path}")


if __name__ == "__main__":
    main()

