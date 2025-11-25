#!/usr/bin/env python3
"""
Diagnostic script to investigate embedding issues

Checks for:
- Duplicate embeddings
- Similarity scores between embeddings
- Embedding generation consistency
"""

import os
import sys
import json
import argparse
import numpy as np
from elasticsearch import Elasticsearch
from collections import defaultdict

INDEX_NAME = "icons"

def get_elasticsearch_client():
    """Initialize Elasticsearch client"""
    endpoint = os.getenv("ELASTICSEARCH_ENDPOINT")
    api_key = os.getenv("ELASTICSEARCH_API_KEY")
    if not endpoint or not api_key:
        print("Error: ELASTICSEARCH_ENDPOINT and ELASTICSEARCH_API_KEY must be set")
        sys.exit(1)
    return Elasticsearch([endpoint], api_key=api_key, request_timeout=30)

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

def check_duplicate_embeddings(client: Elasticsearch, field: str = "svg_embedding"):
    """Check for duplicate or very similar embeddings"""
    print(f"\n{'='*60}")
    print(f"Checking for duplicate {field} embeddings...")
    print(f"{'='*60}\n")
    
    # Get all documents
    response = client.search(
        index=INDEX_NAME,
        body={
            "size": 10000,  # Get all documents
            "_source": ["icon_name", field]
        }
    )
    
    hits = response.get("hits", {}).get("hits", [])
    print(f"Found {len(hits)} documents with {field}\n")
    
    if len(hits) < 2:
        print("Not enough documents to check for duplicates")
        return
    
    # Group embeddings by their string representation (for exact duplicates)
    embedding_map = defaultdict(list)
    embeddings_list = []
    
    for hit in hits:
        icon_name = hit.get("_id") or hit.get("_source", {}).get("icon_name", "unknown")
        embedding = hit.get("_source", {}).get(field)
        
        if embedding is None:
            continue
        
        # Convert to tuple for hashing
        embedding_tuple = tuple(embedding)
        embedding_map[embedding_tuple].append(icon_name)
        embeddings_list.append((icon_name, embedding))
    
    # Check for exact duplicates
    duplicates_found = False
    for emb_tuple, icon_names in embedding_map.items():
        if len(icon_names) > 1:
            duplicates_found = True
            print(f"⚠️  EXACT DUPLICATE EMBEDDINGS found for {len(icon_names)} icons:")
            for icon_name in icon_names:
                print(f"   - {icon_name}")
            print()
    
    if not duplicates_found:
        print("✓ No exact duplicate embeddings found\n")
    
    # Check for very similar embeddings (cosine similarity > 0.99)
    print("Checking for very similar embeddings (cosine similarity > 0.99)...\n")
    similar_pairs = []
    
    for i, (icon1, emb1) in enumerate(embeddings_list):
        for j, (icon2, emb2) in enumerate(embeddings_list[i+1:], i+1):
            similarity = cosine_similarity(emb1, emb2)
            if similarity > 0.99:
                similar_pairs.append((icon1, icon2, similarity))
    
    if similar_pairs:
        print(f"⚠️  Found {len(similar_pairs)} pairs with similarity > 0.99:\n")
        for icon1, icon2, sim in sorted(similar_pairs, key=lambda x: x[2], reverse=True)[:20]:
            print(f"   {icon1} <-> {icon2}: {sim:.6f}")
        if len(similar_pairs) > 20:
            print(f"   ... and {len(similar_pairs) - 20} more pairs")
    else:
        print("✓ No very similar embeddings found (all similarities < 0.99)\n")
    
    # Show similarity distribution
    print("Similarity distribution (sample of 100 random pairs):\n")
    similarities = []
    sample_size = min(100, len(embeddings_list) * (len(embeddings_list) - 1) // 2)
    
    import random
    pairs_checked = set()
    while len(similarities) < sample_size and len(pairs_checked) < len(embeddings_list) * (len(embeddings_list) - 1) // 2:
        i = random.randint(0, len(embeddings_list) - 1)
        j = random.randint(0, len(embeddings_list) - 1)
        if i != j and (i, j) not in pairs_checked:
            pairs_checked.add((i, j))
            sim = cosine_similarity(embeddings_list[i][1], embeddings_list[j][1])
            similarities.append(sim)
    
    if similarities:
        similarities.sort()
        print(f"   Min similarity: {similarities[0]:.6f}")
        print(f"   Max similarity: {similarities[-1]:.6f}")
        print(f"   Mean similarity: {np.mean(similarities):.6f}")
        print(f"   Median similarity: {np.median(similarities):.6f}")
        print(f"   95th percentile: {np.percentile(similarities, 95):.6f}")
        print(f"   99th percentile: {np.percentile(similarities, 99):.6f}")

def check_specific_icons(client: Elasticsearch, icon_names: list, field: str = "svg_embedding"):
    """Check embeddings for specific icons"""
    print(f"\n{'='*60}")
    print(f"Checking embeddings for specific icons...")
    print(f"{'='*60}\n")
    
    for icon_name in icon_names:
        try:
            doc = client.get(index=INDEX_NAME, id=icon_name)
            source = doc.get("_source", {})
            embedding = source.get(field)
            
            if embedding is None:
                print(f"⚠️  {icon_name}: No {field} found")
            else:
                print(f"✓ {icon_name}: {field} found ({len(embedding)} dimensions)")
                print(f"   First 5 values: {embedding[:5]}")
                print(f"   Norm: {np.linalg.norm(embedding):.6f}")
        except Exception as e:
            print(f"✗ {icon_name}: Error - {e}")
        print()

def compare_embeddings(client: Elasticsearch, icon1: str, icon2: str, field: str = "svg_embedding"):
    """Compare embeddings between two icons"""
    print(f"\n{'='*60}")
    print(f"Comparing {field} for '{icon1}' vs '{icon2}'...")
    print(f"{'='*60}\n")
    
    try:
        doc1 = client.get(index=INDEX_NAME, id=icon1)
        doc2 = client.get(index=INDEX_NAME, id=icon2)
        
        emb1 = doc1.get("_source", {}).get(field)
        emb2 = doc2.get("_source", {}).get(field)
        
        if emb1 is None or emb2 is None:
            print("✗ One or both embeddings not found")
            return
        
        similarity = cosine_similarity(emb1, emb2)
        print(f"Cosine similarity: {similarity:.6f}")
        print(f"Are identical: {np.array_equal(emb1, emb2)}")
        
        # Calculate difference
        diff = np.array(emb1) - np.array(emb2)
        print(f"Max difference: {np.max(np.abs(diff)):.6f}")
        print(f"Mean difference: {np.mean(np.abs(diff)):.6f}")
        
    except Exception as e:
        print(f"✗ Error comparing embeddings: {e}")

def main():
    parser = argparse.ArgumentParser(description="Diagnose embedding issues")
    parser.add_argument("--field", default="svg_embedding", 
                       choices=["svg_embedding", "image_embedding", "text_embedding"],
                       help="Embedding field to check (default: svg_embedding)")
    parser.add_argument("--icons", nargs="+", help="Specific icons to check")
    parser.add_argument("--compare", nargs=2, metavar=("ICON1", "ICON2"),
                       help="Compare two specific icons")
    
    args = parser.parse_args()
    
    client = get_elasticsearch_client()
    
    # Check for duplicates
    check_duplicate_embeddings(client, args.field)
    
    # Check specific icons if provided
    if args.icons:
        check_specific_icons(client, args.icons, args.field)
    
    # Compare two icons if provided
    if args.compare:
        compare_embeddings(client, args.compare[0], args.compare[1], args.field)

if __name__ == "__main__":
    main()

