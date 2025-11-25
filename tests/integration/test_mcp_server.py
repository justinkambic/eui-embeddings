#!/usr/bin/env python3
"""
Test script for MCP Server

This script tests the MCP server functions directly without requiring an MCP client.
It verifies that SVG and image search tools work correctly.

Usage:
    python test_mcp_server.py
    python test_mcp_server.py --svg-file test.svg
    python test_mcp_server.py --svg-string "<svg>...</svg>"
    python test_mcp_server.py --image-file test.png
    python test_mcp_server.py --icon-type token
    python test_mcp_server.py --icon-svg --token-svg --svg-string "<svg>...</svg>"
    python test_mcp_server.py --icon-image --icon-svg --token-image --token-svg --image-file test.png
"""

import asyncio
import argparse
import base64
import os
import sys
from pathlib import Path

# Import the search functions from mcp_server
try:
    from mcp_server import search_by_svg, search_by_image
except ImportError:
    print("Error: Could not import from mcp_server.py")
    print("Make sure you're running from the project root directory")
    sys.exit(1)


def read_file_content(file_path: str) -> str:
    """Read file content"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def image_to_base64(image_path: str) -> str:
    """Convert image file to base64 string"""
    with open(image_path, 'rb') as f:
        image_data = f.read()
    return base64.b64encode(image_data).decode('utf-8')


async def test_svg_search(svg_content: str = None, icon_type: str = None, fields: list = None):
    """Test SVG search functionality"""
    print("=" * 60)
    print("Testing SVG Search")
    print("=" * 60)
    
    if svg_content is None:
        # Use a simple test SVG
        svg_content = '''<svg viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg">
  <circle cx="8" cy="8" r="6" fill="none" stroke="currentColor" stroke-width="2"/>
  <circle cx="8" cy="8" r="3" fill="currentColor"/>
</svg>'''
    
    print(f"SVG Content: {svg_content[:100]}...")
    if icon_type:
        print(f"Icon Type: {icon_type}")
    if fields:
        print(f"Fields: {fields}")
    print()
    
    try:
        result = await search_by_svg(svg_content, icon_type=icon_type, fields=fields, max_results=5)
        print(result)
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_image_search(image_path: str = None, icon_type: str = None, fields: list = None):
    """Test image search functionality"""
    print("=" * 60)
    print("Testing Image Search")
    print("=" * 60)
    
    if image_path is None:
        print("⚠️  No image file provided. Skipping image search test.")
        print("   Use --image-file <path> to test image search")
        return None
    
    if not os.path.exists(image_path):
        print(f"❌ Error: Image file not found: {image_path}")
        return False
    
    print(f"Image file: {image_path}")
    if icon_type:
        print(f"Icon Type: {icon_type}")
    if fields:
        print(f"Fields: {fields}")
    
    try:
        # Convert image to base64
        base64_data = image_to_base64(image_path)
        print(f"Base64 length: {len(base64_data)} characters")
        print()
        
        result = await search_by_image(base64_data, icon_type=icon_type, fields=fields, max_results=5)
        print(result)
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests(svg_file: str = None, svg_string: str = None, 
                        image_file: str = None, icon_type: str = None, fields: list = None):
    """Run all tests"""
    print("\n" + "=" * 60)
    print("MCP Server Test Suite")
    print("=" * 60)
    print()
    
    # Check prerequisites
    print("Checking prerequisites...")
    search_api_url = os.getenv("SEARCH_API_URL", "http://localhost:3001/api/search")
    embedding_url = os.getenv("EMBEDDING_SERVICE_URL", "http://localhost:8000")
    
    print(f"  Search API URL: {search_api_url}")
    print(f"  Embedding Service URL: {embedding_url}")
    if icon_type:
        print(f"  Icon Type: {icon_type}")
    if fields:
        print(f"  Fields: {fields}")
    print()
    
    results = {}
    
    # Test SVG search
    if svg_file:
        if os.path.exists(svg_file):
            svg_content = read_file_content(svg_file)
            results['svg'] = await test_svg_search(svg_content, icon_type=icon_type, fields=fields)
        else:
            print(f"❌ SVG file not found: {svg_file}")
            results['svg'] = False
    elif svg_string:
        results['svg'] = await test_svg_search(svg_string, icon_type=icon_type, fields=fields)
    else:
        results['svg'] = await test_svg_search(icon_type=icon_type, fields=fields)
    print()
    
    # Test image search
    if image_file:
        results['image'] = await test_image_search(image_file, icon_type=icon_type, fields=fields)
    else:
        results['image'] = await test_image_search(icon_type=icon_type, fields=fields)
    print()
    
    # Summary
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, result in results.items():
        if result is None:
            status = "⏭️  SKIPPED"
        elif result:
            status = "✅ PASSED"
        else:
            status = "❌ FAILED"
        print(f"  {test_name.upper():10} {status}")
    
    print()
    
    # Overall result
    passed = sum(1 for r in results.values() if r is True)
    total = sum(1 for r in results.values() if r is not None)
    
    if passed == total:
        print("✅ All tests passed!")
        return 0
    else:
        print(f"⚠️  {passed}/{total} tests passed")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="Test the MCP server functionality",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Create mutually exclusive group for SVG options
    svg_group = parser.add_mutually_exclusive_group()
    svg_group.add_argument(
        "--svg-file",
        help="SVG file to test with"
    )
    svg_group.add_argument(
        "--svg-string",
        help="SVG content as a string to test with (alternative to --svg-file)"
    )
    
    parser.add_argument(
        "--image-file",
        help="Image file to test with (PNG, JPG, etc.)"
    )
    
    parser.add_argument(
        "--icon-type",
        choices=["icon", "token"],
        help="Specify icon type: 'icon' or 'token' (affects default field selection)"
    )
    
    # Field override flags
    parser.add_argument(
        "--icon-image",
        action="store_true",
        help="Include icon_image_embedding field in search"
    )
    parser.add_argument(
        "--icon-svg",
        action="store_true",
        help="Include icon_svg_embedding field in search"
    )
    parser.add_argument(
        "--token-image",
        action="store_true",
        help="Include token_image_embedding field in search"
    )
    parser.add_argument(
        "--token-svg",
        action="store_true",
        help="Include token_svg_embedding field in search"
    )
    
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all tests (default behavior)"
    )
    
    args = parser.parse_args()
    
    # Build fields list from override flags
    fields = []
    if args.icon_image:
        fields.append("icon_image_embedding")
    if args.icon_svg:
        fields.append("icon_svg_embedding")
    if args.token_image:
        fields.append("token_image_embedding")
    if args.token_svg:
        fields.append("token_svg_embedding")
    
    # Use None if no fields specified (so defaults apply), otherwise use the list
    fields_list = fields if fields else None
    
    # Run tests
    exit_code = asyncio.run(run_all_tests(
        svg_file=args.svg_file,
        svg_string=args.svg_string,
        image_file=args.image_file,
        icon_type=args.icon_type,
        fields=fields_list
    ))
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

