#!/usr/bin/env python3
"""
Check Elasticsearch Index Contents

Quick script to see what's actually indexed in Elasticsearch.
"""

import os
import sys
from elasticsearch import Elasticsearch

INDEX_NAME = "icons"

def main():
    endpoint = os.getenv("ELASTICSEARCH_ENDPOINT")
    api_key = os.getenv("ELASTICSEARCH_API_KEY")
    
    if not endpoint or not api_key:
        print("Error: ELASTICSEARCH_ENDPOINT and ELASTICSEARCH_API_KEY must be set")
        sys.exit(1)
    
    client = Elasticsearch(
        [endpoint],
        api_key=api_key,
        request_timeout=30
    )
    
    try:
        # Get all documents
        response = client.search(
            index=INDEX_NAME,
            body={
                "query": {"match_all": {}},
                "size": 1000
            }
        )
        
        hits = response.get("hits", {}).get("hits", [])
        total = response.get("hits", {}).get("total", {})
        
        print("=" * 60)
        print("Elasticsearch Index Contents")
        print("=" * 60)
        print(f"Total documents: {total}")
        print(f"Documents returned: {len(hits)}")
        print()
        
        if not hits:
            print("No documents found in index.")
            return
        
        print("Indexed Icons:")
        print("-" * 60)
        for hit in hits:
            icon_name = hit.get("_id") or hit.get("_source", {}).get("icon_name", "unknown")
            source = hit.get("_source", {})
            
            # Check which embeddings are present
            has_text = "text_embedding" in source
            has_image = "image_embedding" in source
            has_svg = "svg_embedding" in source
            
            print(f"  {icon_name}")
            print(f"    - Text embedding: {'✓' if has_text else '✗'}")
            print(f"    - Image embedding: {'✓' if has_image else '✗'}")
            print(f"    - SVG embedding: {'✓' if has_svg else '✗'}")
            
            if has_svg:
                svg_dims = len(source.get("svg_embedding", []))
                print(f"    - SVG embedding dimensions: {svg_dims}")
            
            print()
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

