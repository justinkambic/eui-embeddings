#!/usr/bin/env python3
"""
Test SVG Search Script

Tests the SVG search functionality by searching for an SVG against indexed embeddings.

Usage:
    python test_svg_search.py <svg_file_path>
    python test_svg_search.py --svg-content "<svg>...</svg>"
    python test_svg_search.py --icon-name illustration
"""

import os
import sys
import json
import argparse
import requests
from pathlib import Path

# Configuration
SEARCH_API_URL = "http://localhost:3001/api/search"
EMBEDDING_SERVICE_URL = "http://localhost:8000/embed-svg"

def read_svg_file(file_path: str) -> str:
    """Read SVG file content"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def search_by_svg(svg_content: str, api_url: str = None) -> dict:
    """Search for icons using SVG content"""
    if api_url is None:
        api_url = SEARCH_API_URL
    try:
        response = requests.post(
            api_url,
            json={
                "type": "svg",
                "query": svg_content
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

def search_by_icon_name(icon_name: str, api_url: str = None, svg_paths_file: str = ".svgpaths") -> dict:
    """Search using an icon name by finding its SVG in .svgpaths"""
    # Read .svgpaths file
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
                svg_content = read_svg_file(path)
                return search_by_svg(svg_content, api_url)
    
    print(f"✗ Error: Could not find SVG file for icon '{icon_name}'")
    return None

def main():
    parser = argparse.ArgumentParser(
        description="Test SVG search functionality",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "svg_file",
        nargs="?",
        help="Path to SVG file to search with"
    )
    
    parser.add_argument(
        "--svg-content",
        help="SVG content as string (use quotes)"
    )
    
    parser.add_argument(
        "--icon-name",
        help="Icon name to search for (finds SVG in .svgpaths)"
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
    
    # Use port to construct API URL if not explicitly provided
    if args.api_url == SEARCH_API_URL:
        api_url = f"http://localhost:{args.port}/api/search"
    else:
        api_url = args.api_url
    
    # Determine SVG content
    svg_content = None
    
    if args.svg_content:
        svg_content = args.svg_content
    elif args.icon_name:
        result = search_by_icon_name(args.icon_name, api_url)
        if result:
            print_results(result)
        return
    elif args.svg_file:
        if not os.path.exists(args.svg_file):
            print(f"✗ Error: File not found: {args.svg_file}")
            sys.exit(1)
        svg_content = read_svg_file(args.svg_file)
    else:
        parser.print_help()
        sys.exit(1)
    
    # Perform search
    print(f"Searching with SVG content ({len(svg_content)} chars)...")
    print(f"API URL: {api_url}")
    print()
    
    result = search_by_svg(svg_content, api_url)
    
    if result:
        print_results(result)
    else:
        print("✗ Search failed")
        sys.exit(1)

def print_results(result: dict):
    """Print search results in a readable format"""
    results = result.get("results", [])
    total = result.get("total", 0)
    
    print("=" * 60)
    print("Search Results")
    print("=" * 60)
    print(f"Total matches: {total}")
    print(f"Results returned: {len(results)}")
    print()
    
    if not results:
        print("No results found.")
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

if __name__ == "__main__":
    main()

