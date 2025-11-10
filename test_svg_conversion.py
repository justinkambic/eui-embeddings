#!/usr/bin/env python3
"""
Test SVG to PNG conversion and embedding generation

Checks if different SVGs produce different embeddings.
"""

import os
import sys
import requests
from pathlib import Path
import numpy as np

EMBEDDING_SERVICE_URL = "http://localhost:8000/embed-svg"

def read_svg_file(file_path: str) -> str:
    """Read SVG file content"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def generate_embedding(svg_content: str) -> list:
    """Generate embedding for SVG content"""
    try:
        response = requests.post(
            EMBEDDING_SERVICE_URL,
            json={"svg_content": svg_content},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        return data.get("embeddings")
    except Exception as e:
        print(f"  ✗ Error generating embedding: {e}")
        return None

def cosine_similarity(vec1, vec2):
    """Calculate cosine similarity between two vectors"""
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot_product / (norm1 * norm2)

def main():
    # Test with the problematic icons
    script_dir = os.path.dirname(os.path.abspath(__file__))
    svgpaths_file = os.path.join(script_dir, ".svgpaths")
    
    # Find SVG files for problematic icons
    problematic_icons = ["grid", "index_mapping", "checkInCircleFilled", "search", "app_devtools", "minus_in_circle_filled"]
    
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
    
    if len(svg_files) < 2:
        print("Not enough files found to test")
        return
    
    # Read SVGs and generate embeddings
    embeddings = {}
    svg_contents = {}
    
    for icon_name, file_path in svg_files.items():
        print(f"Processing {icon_name}...")
        svg_content = read_svg_file(file_path)
        svg_contents[icon_name] = svg_content
        print(f"  SVG size: {len(svg_content)} chars")
        
        embedding = generate_embedding(svg_content)
        if embedding:
            embeddings[icon_name] = embedding
            print(f"  ✓ Embedding generated ({len(embedding)} dimensions)")
            print(f"  First 5 values: {embedding[:5]}")
            print(f"  Norm: {np.linalg.norm(embedding):.6f}")
        else:
            print(f"  ✗ Failed to generate embedding")
        print()
    
    # Compare embeddings
    print("=" * 60)
    print("Comparing Embeddings")
    print("=" * 60)
    print()
    
    icon_names = list(embeddings.keys())
    if len(icon_names) < 2:
        print("Not enough embeddings to compare")
        return
    
    # Check for exact duplicates
    print("Checking for exact duplicates...")
    duplicates = []
    for i, icon1 in enumerate(icon_names):
        for icon2 in icon_names[i+1:]:
            if np.array_equal(embeddings[icon1], embeddings[icon2]):
                duplicates.append((icon1, icon2))
                print(f"  ⚠️  EXACT DUPLICATE: {icon1} == {icon2}")
    
    if not duplicates:
        print("  ✓ No exact duplicates found")
    print()
    
    # Check similarities
    print("Similarity scores:")
    for i, icon1 in enumerate(icon_names):
        for icon2 in icon_names[i+1:]:
            similarity = cosine_similarity(embeddings[icon1], embeddings[icon2])
            status = "⚠️" if similarity > 0.99 else "✓"
            print(f"  {status} {icon1} <-> {icon2}: {similarity:.6f}")
    
    # Check if SVGs are identical
    print()
    print("=" * 60)
    print("Comparing SVG Content")
    print("=" * 60)
    print()
    
    for i, icon1 in enumerate(icon_names):
        for icon2 in icon_names[i+1:]:
            svg1 = svg_contents[icon1]
            svg2 = svg_contents[icon2]
            
            if svg1 == svg2:
                print(f"  ⚠️  IDENTICAL SVG: {icon1} == {icon2}")
            else:
                # Normalize whitespace and compare
                svg1_norm = ' '.join(svg1.split())
                svg2_norm = ' '.join(svg2.split())
                if svg1_norm == svg2_norm:
                    print(f"  ⚠️  IDENTICAL SVG (normalized): {icon1} == {icon2}")
                else:
                    print(f"  ✓ Different SVG: {icon1} != {icon2}")

if __name__ == "__main__":
    main()

