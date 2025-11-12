#!/usr/bin/env python3
"""
Test SVG Search Script

Tests the SVG search functionality by searching for an SVG against indexed embeddings.

Usage:
    python test_svg_search.py <svg_file_path>
    python test_svg_search.py --svg-content "<svg>...</svg>"
    python test_svg_search.py --icon-name logoElasticsearch
"""

import os
import sys
import json
import re
import argparse
import requests
from pathlib import Path

# Configuration
SEARCH_API_URL = "http://localhost:8000/search"
EMBEDDING_SERVICE_URL = "http://localhost:8000/embed-svg"
EUI_LOCATION = os.getenv("EUI_LOCATION", "./data/eui")
ICON_MAP_PATH = "packages/eui/src/components/icon/icon_map.ts"

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

def extract_type_to_path_map(icon_map_path: str) -> dict:
    """
    Extract typeToPathMap from TypeScript file.
    
    Handles TypeScript syntax like:
    export const typeToPathMap = {
      iconName: 'filename',
      ...
    };
    """
    if not os.path.exists(icon_map_path):
        print(f"✗ Icon map file not found: {icon_map_path}")
        return {}
    
    try:
        with open(icon_map_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the typeToPathMap object
        # Match: export const typeToPathMap = { ... };
        pattern = r'export\s+const\s+typeToPathMap\s*=\s*\{([^}]+)\}'
        match = re.search(pattern, content, re.DOTALL)
        
        if not match:
            print("✗ Could not find typeToPathMap in file")
            return {}
        
        object_content = match.group(1)
        
        # Extract key-value pairs
        # Match: key: 'value', or key: "value",
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
    
    # Exclude common directories that shouldn't be searched
    exclude_dirs = {'.git', 'node_modules', 'dist', 'build', '__pycache__', '.next'}
    
    for root, dirs, files in os.walk(repo_dir):
        # Filter out excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            if file.endswith('.svg'):
                # Check if filename (without extension) matches
                file_base = os.path.splitext(file)[0]
                if file_base == filename:
                    return os.path.join(root, file)
    
    return None

def search_by_icon_name(icon_name: str, api_url: str = None) -> dict:
    """Search using an icon name by finding its SVG in the EUI repository"""
    # Get EUI location
    eui_location = os.path.abspath(EUI_LOCATION)
    
    if not os.path.exists(eui_location):
        print(f"✗ Error: EUI repository not found at {eui_location}")
        print(f"  Set EUI_LOCATION environment variable or ensure repository is cloned")
        return None
    
    # Extract icon mapping
    icon_map_path = os.path.join(eui_location, ICON_MAP_PATH)
    type_to_path_map = extract_type_to_path_map(icon_map_path)
    
    if not type_to_path_map:
        print(f"✗ Error: Could not extract icon mappings from {icon_map_path}")
        return None
    
    # Get filename from icon name (reverse mapping)
    filename = type_to_path_map.get(icon_name)
    if not filename:
        print(f"✗ Error: Icon name '{icon_name}' not found in typeToPathMap")
        print(f"  Available icon names: {', '.join(list(type_to_path_map.keys())[:10])}...")
        return None
    
    print(f"Found icon mapping: {icon_name} -> {filename}")
    
    # Find SVG file in repository
    svg_file = find_svg_file_in_repo(eui_location, filename)
    
    if not svg_file:
        print(f"✗ Error: Could not find SVG file '{filename}.svg' in repository")
        return None
    
    print(f"Found SVG file: {svg_file}")
    svg_content = read_svg_file(svg_file)
    return search_by_svg(svg_content, api_url)

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

