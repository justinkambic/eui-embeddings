#!/usr/bin/env python3
"""
Batch SVG Embedding Script

Processes SVG files listed in .svgpaths file and generates embeddings for each.
Optionally indexes the embeddings in Elasticsearch.

Usage:
    python batch_embed_svgs.py [--svgpaths-file FILE] [--index] [--output-dir OUTPUT_DIR]

Examples:
    # Generate embeddings only (reads from .svgpaths)
    python batch_embed_svgs.py

    # Generate embeddings and index in Elasticsearch
    python batch_embed_svgs.py --index

    # Generate embeddings and save to specific directory
    python batch_embed_svgs.py --output-dir ./embeddings

    # Use a different paths file
    python batch_embed_svgs.py --svgpaths-file my_svgs.txt --index

    # Process only first 10 files (useful for testing)
    python batch_embed_svgs.py --limit 10 --index
"""

import os
import sys
import json
import argparse
from typing import List, Dict, Optional
import requests
from elasticsearch import Elasticsearch

# Configuration
EMBEDDING_SERVICE_URL = "http://localhost:8000/embed-svg"
INDEX_NAME = "icons"

def get_elasticsearch_client() -> Optional[Elasticsearch]:
    """Initialize Elasticsearch client if environment variables are set"""
    endpoint = os.getenv("ELASTICSEARCH_ENDPOINT")
    api_key = os.getenv("ELASTICSEARCH_API_KEY")
    
    if endpoint and api_key:
        return Elasticsearch(
            [endpoint],
            api_key=api_key,
            request_timeout=30
        )
    return None

def read_svg_file(file_path: str) -> str:
    """Read SVG file content"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def generate_embedding(svg_content: str, service_url: str = None) -> Optional[List[float]]:
    """Generate embedding for SVG content"""
    if service_url is None:
        service_url = EMBEDDING_SERVICE_URL
    try:
        response = requests.post(
            service_url,
            json={"svg_content": svg_content},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        return data.get("embeddings")
    except requests.exceptions.RequestException as e:
        print(f"  ✗ Error generating embedding: {e}")
        return None

def index_embedding(
    client: Elasticsearch,
    icon_name: str,
    svg_content: str,
    embeddings: List[float]
) -> bool:
    """Index embedding in Elasticsearch"""
    try:
        document = {
            "icon_name": icon_name,
            "svg_embedding": embeddings,
        }
        
        # Check if document exists
        exists = client.exists(index=INDEX_NAME, id=icon_name)
        
        if exists:
            client.update(
                index=INDEX_NAME,
                id=icon_name,
                doc=document,
                doc_as_upsert=True
            )
        else:
            client.index(
                index=INDEX_NAME,
                id=icon_name,
                document=document
            )
        
        return True
    except Exception as e:
        print(f"  ✗ Error indexing in Elasticsearch: {e}")
        return False

def save_embedding_to_file(
    icon_name: str,
    svg_content: str,
    embeddings: List[float],
    output_dir: str
):
    """Save embedding to JSON file"""
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, f"{icon_name}.json")
    data = {
        "icon_name": icon_name,
        "svg_content": svg_content,
        "embeddings": embeddings,
        "embedding_dimension": len(embeddings)
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def check_already_indexed(
    es_client: Optional[Elasticsearch],
    icon_name: str
) -> bool:
    """Check if icon is already indexed in Elasticsearch"""
    if not es_client:
        return False
    
    try:
        exists = es_client.exists(index=INDEX_NAME, id=icon_name)
        if exists:
            # Also check if it has SVG embedding
            doc = es_client.get(index=INDEX_NAME, id=icon_name)
            source = doc.get("_source", {})
            return "svg_embedding" in source
        return False
    except Exception:
        # If check fails, assume not indexed
        return False

def process_svg_file(
    file_path: str,
    icon_name: str,
    es_client: Optional[Elasticsearch],
    output_dir: Optional[str],
    index: bool,
    service_url: str = None,
    skip_if_exists: bool = True
) -> Dict:
    """Process a single SVG file"""
    result = {
        "file": file_path,
        "icon_name": icon_name,
        "success": False,
        "skipped": False,
        "error": None
    }
    
    # Check if already indexed
    if index and skip_if_exists and es_client:
        if check_already_indexed(es_client, icon_name):
            result["success"] = True
            result["skipped"] = True
            return result
    
    try:
        # Read SVG file
        svg_content = read_svg_file(file_path)
        
        # Generate embedding
        print(f"  Generating embedding...")
        embeddings = generate_embedding(svg_content, service_url)
        
        if not embeddings:
            result["error"] = "Failed to generate embedding"
            return result
        
        print(f"  ✓ Embedding generated ({len(embeddings)} dimensions)")
        
        # Index in Elasticsearch if requested
        if index and es_client:
            print(f"  Indexing in Elasticsearch...")
            if index_embedding(es_client, icon_name, svg_content, embeddings):
                print(f"  ✓ Indexed in Elasticsearch")
            else:
                result["error"] = "Failed to index in Elasticsearch"
                return result
        
        # Save to file if output directory specified
        if output_dir:
            print(f"  Saving to {output_dir}...")
            save_embedding_to_file(icon_name, svg_content, embeddings, output_dir)
            print(f"  ✓ Saved to file")
        
        result["success"] = True
        return result
        
    except Exception as e:
        result["error"] = str(e)
        print(f"  ✗ Error: {e}")
        return result

def read_svg_paths_from_file(file_path: str) -> List[str]:
    """Read SVG file paths from a text file (one path per line)"""
    svg_files = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                # Strip whitespace and skip empty lines
                path = line.strip()
                if path and not path.startswith('#'):  # Skip comments
                    # Resolve relative paths
                    if not os.path.isabs(path):
                        # Make path relative to script directory
                        script_dir = os.path.dirname(os.path.abspath(__file__))
                        path = os.path.join(script_dir, path)
                        path = os.path.normpath(path)
                    
                    # Check if file exists
                    if os.path.isfile(path):
                        svg_files.append(path)
                    else:
                        print(f"  ⚠ Warning: File not found: {path}")
    except FileNotFoundError:
        print(f"✗ Error: File not found: {file_path}")
        return []
    except Exception as e:
        print(f"✗ Error reading file {file_path}: {e}")
        return []
    
    return svg_files

def get_icon_name_from_path(file_path: str) -> str:
    """Extract icon name from file path"""
    # Get filename without extension
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    return base_name

def main():
    parser = argparse.ArgumentParser(
        description="Batch process SVG files and generate embeddings",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--svgpaths-file",
        default=".svgpaths",
        help="File containing SVG paths (one per line) (default: .svgpaths)"
    )
    
    parser.add_argument(
        "--index",
        action="store_true",
        help="Index embeddings in Elasticsearch (requires ELASTICSEARCH_ENDPOINT and ELASTICSEARCH_API_KEY)"
    )
    
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory to save embedding JSON files (default: don't save to files)"
    )
    
    parser.add_argument(
        "--service-url",
        default=EMBEDDING_SERVICE_URL,
        help=f"Embedding service URL (default: {EMBEDDING_SERVICE_URL})"
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit processing to first N SVG files (useful for testing)"
    )
    
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-process files even if they're already indexed (default: skip existing)"
    )
    
    args = parser.parse_args()
    
    # Update service URL if provided (use local variable, not global)
    service_url = args.service_url
    
    # Read SVG file paths from file
    svgpaths_file = args.svgpaths_file
    if not os.path.isabs(svgpaths_file):
        # Make path relative to script directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        svgpaths_file = os.path.join(script_dir, svgpaths_file)
        svgpaths_file = os.path.normpath(svgpaths_file)
    
    print(f"Reading SVG paths from: {svgpaths_file}")
    svg_files = read_svg_paths_from_file(svgpaths_file)
    
    if not svg_files:
        print(f"✗ No valid SVG files found in: {svgpaths_file}")
        sys.exit(1)
    
    # Apply limit if specified
    total_files = len(svg_files)
    if args.limit and args.limit > 0:
        svg_files = svg_files[:args.limit]
        print(f"✓ Found {total_files} SVG file(s), limiting to first {len(svg_files)}")
    else:
        print(f"✓ Found {len(svg_files)} SVG file(s)")
    print()
    
    # Initialize Elasticsearch client if indexing requested
    es_client = None
    if args.index:
        es_client = get_elasticsearch_client()
        if not es_client:
            print("✗ Error: --index specified but Elasticsearch environment variables not set")
            print("  Set ELASTICSEARCH_ENDPOINT and ELASTICSEARCH_API_KEY")
            sys.exit(1)
        
        # Test connection
        try:
            es_client.info()
            print("✓ Connected to Elasticsearch")
        except Exception as e:
            print(f"✗ Error connecting to Elasticsearch: {e}")
            sys.exit(1)
    
    # Process each SVG file
    results = []
    for i, svg_file in enumerate(svg_files, 1):
        icon_name = get_icon_name_from_path(svg_file)
        print(f"[{i}/{len(svg_files)}] Processing: {icon_name} ({svg_file})")
        
        result = process_svg_file(
            svg_file,
            icon_name,
            es_client,
            args.output_dir,
            args.index,
            service_url,
            skip_if_exists=not args.force
        )
        
        if result.get("skipped"):
            print(f"  ⏭ Skipped: Already indexed")
        
        results.append(result)
        print()
    
    # Summary
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    
    successful = sum(1 for r in results if r["success"])
    skipped = sum(1 for r in results if r.get("skipped", False))
    failed = len(results) - successful
    
    print(f"Total files: {len(results)}")
    print(f"Successful: {successful}")
    if skipped > 0:
        print(f"Skipped (already indexed): {skipped}")
    print(f"Failed: {failed}")
    
    if failed > 0:
        print("\nFailed files:")
        for result in results:
            if not result["success"] and not result.get("skipped", False):
                print(f"  - {result['icon_name']}: {result['error']}")
    
    # Exit with error code if any failed
    sys.exit(1 if failed > 0 else 0)

if __name__ == "__main__":
    main()

