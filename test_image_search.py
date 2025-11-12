#!/usr/bin/env python3
"""
Test Image Search Script

Tests image search functionality by searching with an image file (e.g., screenshot).

Usage:
    python test_image_search.py <image_file_path>
    python test_image_search.py --image screenshot.png
"""

import os
import sys
import base64
import argparse
import requests
from pathlib import Path
from PIL import Image
import io

# Configuration
SEARCH_API_URL = "http://localhost:8000/search"

def image_to_base64(image_path: str) -> str:
    """Convert image file to base64 string"""
    try:
        with open(image_path, 'rb') as f:
            image_data = f.read()
        base64_data = base64.b64encode(image_data).decode('utf-8')
        return base64_data
    except Exception as e:
        print(f"✗ Error reading image file: {e}")
        return None

def search_by_image(image_path: str, api_url: str = None) -> dict:
    """Search for icons using an image file"""
    if api_url is None:
        api_url = SEARCH_API_URL
    
    # Convert image to base64
    print(f"Reading image: {image_path}")
    base64_image = image_to_base64(image_path)
    
    if not base64_image:
        return None
    
    # Get image info
    try:
        img = Image.open(image_path)
        print(f"  Image size: {img.size}")
        print(f"  Image mode: {img.mode}")
        print(f"  Base64 length: {len(base64_image)} chars")
    except Exception as e:
        print(f"  ⚠️  Warning: Could not read image info: {e}")
    
    # Search
    try:
        print(f"\nSearching with image...")
        print(f"API URL: {api_url}")
        
        response = requests.post(
            api_url,
            json={
                "type": "image",
                "query": base64_image
            },
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"✗ Error searching: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"  Response: {e.response.text}")
        return None

def print_results(result: dict):
    """Print search results in a readable format"""
    if not result:
        print("✗ No results returned")
        return
    
    results = result.get("results", [])
    total = result.get("total", {})
    
    print("\n" + "=" * 60)
    print("Search Results")
    print("=" * 60)
    print(f"Total matches: {total}")
    print(f"Results returned: {len(results)}")
    print()
    
    if not results:
        print("No results found")
        return
    
    for i, item in enumerate(results, 1):
        icon_name = item.get("icon_name", "unknown")
        score = item.get("score", 0)
        descriptions = item.get("descriptions", [])
        
        print(f"[{i}] {icon_name}")
        print(f"    Score: {score:.4f}")
        if descriptions:
            print(f"    Descriptions: {', '.join(descriptions[:3])}")
        print()

def main():
    parser = argparse.ArgumentParser(
        description="Test image search functionality",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "image_file",
        nargs="?",
        help="Path to image file (PNG, JPG, etc.)"
    )
    
    parser.add_argument(
        "--image",
        help="Path to image file (alternative to positional argument)"
    )
    
    parser.add_argument(
        "--api-url",
        default=SEARCH_API_URL,
        help=f"Search API URL (default: {SEARCH_API_URL})"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=3001,
        help="Frontend port number (default: 3001)"
    )
    
    args = parser.parse_args()
    
    # Determine image file path
    image_path = args.image or args.image_file
    
    if not image_path:
        print("✗ Error: No image file specified")
        print("Usage: python test_image_search.py <image_file_path>")
        print("   or: python test_image_search.py --image <image_file_path>")
        sys.exit(1)
    
    # Resolve path
    if not os.path.isabs(image_path):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        image_path = os.path.join(script_dir, image_path)
        image_path = os.path.normpath(image_path)
    
    if not os.path.isfile(image_path):
        print(f"✗ Error: Image file not found: {image_path}")
        sys.exit(1)
    
    # Use port to construct API URL if not explicitly provided
    if args.api_url == SEARCH_API_URL:
        api_url = f"http://localhost:{args.port}/api/search"
    else:
        api_url = args.api_url
    
    # Perform search
    result = search_by_image(image_path, api_url)
    
    if result:
        print_results(result)
    else:
        print("✗ Search failed")
        sys.exit(1)

if __name__ == "__main__":
    main()

