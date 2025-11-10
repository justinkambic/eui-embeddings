#!/usr/bin/env python3
"""
Elasticsearch Index Setup Script

Creates the 'icons' index with proper mappings for:
- Text embeddings (dense_vector, 384 dims)
- ELSER sparse embeddings (sparse_vector)
- Image embeddings (dense_vector, 512 dims)
- SVG embeddings (dense_vector, 512 dims)
"""

import os
import sys
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import RequestError

INDEX_NAME = "icons"

# Index mapping configuration
INDEX_MAPPING = {
    "mappings": {
        "properties": {
            "icon_name": {
                "type": "keyword"
            },
            "descriptions": {
                "type": "text",
                "fields": {
                    "keyword": {
                        "type": "keyword"
                    }
                }
            },
            "text_embedding": {
                "type": "dense_vector",
                "dims": 384,
                "index": True,
                "similarity": "cosine"
            },
            "text_embedding_sparse": {
                "type": "sparse_vector"
            },
            "image_embedding": {
                "type": "dense_vector",
                "dims": 512,
                "index": True,
                "similarity": "cosine"
            },
            "svg_embedding": {
                "type": "dense_vector",
                "dims": 512,
                "index": True,
                "similarity": "cosine"
            }
        }
    },
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0
    }
}


def setup_index(client: Elasticsearch, recreate: bool = False):
    """Create or recreate the Elasticsearch index"""
    
    # Check if index exists
    exists = client.indices.exists(index=INDEX_NAME)
    
    if exists:
        if recreate:
            print(f"Deleting existing index '{INDEX_NAME}'...")
            client.indices.delete(index=INDEX_NAME)
        else:
            print(f"Index '{INDEX_NAME}' already exists.")
            response = input("Do you want to recreate it? (y/n): ")
            if response.lower() == 'y':
                print(f"Deleting existing index '{INDEX_NAME}'...")
                client.indices.delete(index=INDEX_NAME)
            else:
                print("Keeping existing index.")
                return
    
    # Create index
    print(f"Creating index '{INDEX_NAME}' with mapping...")
    try:
        # For Elasticsearch 8.x, pass mappings and settings directly
        client.indices.create(
            index=INDEX_NAME,
            mappings=INDEX_MAPPING["mappings"],
            settings=INDEX_MAPPING["settings"]
        )
        print(f"✓ Successfully created index '{INDEX_NAME}'")
        return True
    except RequestError as e:
        print(f"✗ Error creating index: {e}")
        # Try with 'body' parameter for older ES versions or different client API
        try:
            client.indices.create(index=INDEX_NAME, body=INDEX_MAPPING)
            print(f"✓ Successfully created index '{INDEX_NAME}' (using body parameter)")
            return True
        except RequestError as e2:
            print(f"✗ Error creating index (retry): {e2}")
            return False


def check_elser_model(client: Elasticsearch):
    """Check if ELSER model is deployed"""
    try:
        models = client.ml.get_trained_models(model_id=".elser_model_2")
        print("✓ ELSER model (.elser_model_2) is available")
        return True
    except Exception:
        print("⚠ ELSER model (.elser_model_2) is not deployed")
        print("  To deploy ELSER, run:")
        print("  PUT _ml/trained_models/.elser_model_2/_deploy")
        return False


def main():
    """Main setup function"""
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
    
    # Test connection
    try:
        info = client.info()
        print(f"Connected to Elasticsearch cluster: {info.get('cluster_name')}")
    except Exception as e:
        print(f"Error connecting to Elasticsearch: {e}")
        sys.exit(1)
    
    # Setup index
    recreate = "--recreate" in sys.argv
    if setup_index(client, recreate):
        print("\nIndex setup complete!")
    
    # Check ELSER
    print("\nChecking ELSER model...")
    check_elser_model(client)
    
    print("\nSetup complete!")


if __name__ == "__main__":
    main()

