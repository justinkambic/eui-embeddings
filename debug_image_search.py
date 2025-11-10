#!/usr/bin/env python3
"""
Debug Image Search

Check what's in the index and verify image search is working
"""

import os
import sys
from elasticsearch import Elasticsearch

INDEX_NAME = "icons"

def get_elasticsearch_client():
    """Initialize Elasticsearch client"""
    endpoint = os.getenv("ELASTICSEARCH_ENDPOINT")
    api_key = os.getenv("ELASTICSEARCH_API_KEY")
    if not endpoint or not api_key:
        print("Error: ELASTICSEARCH_ENDPOINT and ELASTICSEARCH_API_KEY must be set")
        sys.exit(1)
    return Elasticsearch([endpoint], api_key=api_key, request_timeout=30)

def check_index_contents(client: Elasticsearch):
    """Check what's in the index"""
    print("=" * 60)
    print("Checking Index Contents")
    print("=" * 60)
    print()
    
    # Get total count
    try:
        count_response = client.count(index=INDEX_NAME)
        total = count_response["count"]
        print(f"Total documents in index: {total}")
    except Exception as e:
        print(f"✗ Error getting count: {e}")
        return
    
    if total == 0:
        print("\n⚠️  Index is empty! You need to index some icons first.")
        print("   Run: python batch_embed_svgs.py --index")
        return
    
    # Get a sample of documents
    print(f"\nFetching sample documents...")
    try:
        response = client.search(
            index=INDEX_NAME,
            body={
                "size": 10,
                "_source": ["icon_name", "svg_embedding", "image_embedding", "text_embedding"]
            }
        )
        
        hits = response.get("hits", {}).get("hits", [])
        print(f"Found {len(hits)} documents\n")
        
        # Check what fields each document has
        fields_found = {
            "svg_embedding": 0,
            "image_embedding": 0,
            "text_embedding": 0
        }
        
        for hit in hits:
            icon_name = hit.get("_id") or hit.get("_source", {}).get("icon_name", "unknown")
            source = hit.get("_source", {})
            
            print(f"  {icon_name}:")
            if "svg_embedding" in source:
                svg_emb = source["svg_embedding"]
                print(f"    ✓ svg_embedding: {len(svg_emb)} dimensions")
                fields_found["svg_embedding"] += 1
            else:
                print(f"    ✗ svg_embedding: missing")
            
            if "image_embedding" in source:
                img_emb = source["image_embedding"]
                print(f"    ✓ image_embedding: {len(img_emb)} dimensions")
                fields_found["image_embedding"] += 1
            else:
                print(f"    ✗ image_embedding: missing")
            
            if "text_embedding" in source:
                txt_emb = source["text_embedding"]
                print(f"    ✓ text_embedding: {len(txt_emb)} dimensions")
                fields_found["text_embedding"] += 1
            else:
                print(f"    ✗ text_embedding: missing")
            print()
        
        # Summary
        print("=" * 60)
        print("Summary")
        print("=" * 60)
        print(f"Documents with svg_embedding: {fields_found['svg_embedding']}/{len(hits)}")
        print(f"Documents with image_embedding: {fields_found['image_embedding']}/{len(hits)}")
        print(f"Documents with text_embedding: {fields_found['text_embedding']}/{len(hits)}")
        print()
        
        if fields_found["svg_embedding"] == 0:
            print("⚠️  No documents have svg_embedding field!")
            print("   Image searches look for svg_embedding field.")
            print("   You need to index SVGs first:")
            print("   python batch_embed_svgs.py --index")
        elif fields_found["svg_embedding"] < len(hits):
            print(f"⚠️  Only {fields_found['svg_embedding']}/{len(hits)} documents have svg_embedding")
            print("   Some documents are missing svg_embedding field.")
        
    except Exception as e:
        print(f"✗ Error fetching documents: {e}")
        import traceback
        traceback.print_exc()

def test_knn_search(client: Elasticsearch):
    """Test KNN search with a dummy vector"""
    print("=" * 60)
    print("Testing KNN Search")
    print("=" * 60)
    print()
    
    # Create a dummy 512-dimension vector (for svg_embedding)
    dummy_vector = [0.1] * 512
    
    try:
        response = client.search(
            index=INDEX_NAME,
            body={
                "knn": {
                    "field": "svg_embedding",
                    "query_vector": dummy_vector,
                    "k": 10,
                    "num_candidates": 100
                },
                "size": 10
            }
        )
        
        hits = response.get("hits", {}).get("hits", [])
        total = response.get("hits", {}).get("total", {})
        
        print(f"KNN search results:")
        print(f"  Total matches: {total}")
        print(f"  Results returned: {len(hits)}")
        
        if len(hits) > 0:
            print(f"\n  ✓ KNN search is working!")
            print(f"  Top result: {hits[0].get('_id', 'unknown')}")
        else:
            print(f"\n  ⚠️  KNN search returned no results")
            print(f"  This might mean:")
            print(f"    - No documents have svg_embedding field")
            print(f"    - The field mapping is incorrect")
            print(f"    - The index is empty")
        
    except Exception as e:
        print(f"✗ Error testing KNN search: {e}")
        import traceback
        traceback.print_exc()

def main():
    client = get_elasticsearch_client()
    
    check_index_contents(client)
    print()
    test_knn_search(client)

if __name__ == "__main__":
    main()

