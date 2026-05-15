#!/usr/bin/env python3
"""
Elasticsearch Setup Validation Test Suite

This script validates that your Elasticsearch cluster is properly configured
to receive data from the EUI embeddings project. It checks:

1. Connection and authentication
2. Index existence and mapping
3. Dense vector field support
4. ELSER sparse embedding support (optional)
5. Search functionality (knn, text_expansion, hybrid)
6. Indexing capabilities

Usage:
    python test_elasticsearch_setup.py

Environment Variables Required:
    ELASTICSEARCH_ENDPOINT - Your ES cluster endpoint
    ELASTICSEARCH_API_KEY - Your ES API key
"""

import os
import sys
from typing import Dict, Any, List, Optional
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import (
    ConnectionError,
    AuthenticationException,
    NotFoundError,
    RequestError,
)

# Configuration
INDEX_NAME = "icons"
TEST_DOC_ID = "test_icon_validation"

# Expected field configurations
REQUIRED_FIELDS = {
    "icon_name": {"type": "keyword"},
    "descriptions": {"type": "text"},
    "text_embedding": {
        "type": "dense_vector",
        "dims": 384,
        "index": True,
        "similarity": "cosine"
    },
    "image_embedding": {
        "type": "dense_vector",
        "dims": 384,
        "index": True,
        "similarity": "cosine"
    },
    "svg_embedding": {
        "type": "dense_vector",
        "dims": 384,
        "index": True,
        "similarity": "cosine"
    },
}

# Optional ELSER field
ELSER_FIELD = "text_embedding_sparse"


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_test(name: str, status: str, details: str = ""):
    """Print test result with color coding"""
    if status == "PASS":
        symbol = f"{Colors.GREEN}✓{Colors.RESET}"
    elif status == "FAIL":
        symbol = f"{Colors.RED}✗{Colors.RESET}"
    else:
        symbol = f"{Colors.YELLOW}⚠{Colors.RESET}"
    
    print(f"{symbol} {name}")
    if details:
        print(f"   {details}")


def print_section(title: str):
    """Print section header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{title}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")


def test_environment_variables() -> bool:
    """Test 1: Check required environment variables"""
    print_section("Test 1: Environment Variables")
    
    endpoint = os.getenv("ELASTICSEARCH_ENDPOINT")
    api_key = os.getenv("ELASTICSEARCH_API_KEY")
    
    if not endpoint:
        print_test("ELASTICSEARCH_ENDPOINT", "FAIL", "Environment variable not set")
        return False
    else:
        print_test("ELASTICSEARCH_ENDPOINT", "PASS", f"Set to: {endpoint}")
    
    if not api_key:
        print_test("ELASTICSEARCH_API_KEY", "FAIL", "Environment variable not set")
        return False
    else:
        # Mask API key for security
        masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
        print_test("ELASTICSEARCH_API_KEY", "PASS", f"Set (masked: {masked_key})")
    
    return True


def test_connection(client: Elasticsearch) -> bool:
    """Test 2: Verify connection and authentication"""
    print_section("Test 2: Connection & Authentication")
    
    try:
        info = client.info()
        cluster_name = info.get("cluster_name", "unknown")
        version = info.get("version", {}).get("number", "unknown")
        
        print_test("Connection", "PASS", f"Connected to cluster: {cluster_name}")
        print_test("Elasticsearch Version", "PASS", f"Version: {version}")
        
        # Check if version supports required features
        major_version = int(version.split(".")[0]) if version != "unknown" else 0
        if major_version < 8:
            print_test("Version Compatibility", "WARN", 
                       "Elasticsearch 8.0+ recommended for best dense vector support")
        else:
            print_test("Version Compatibility", "PASS")
        
        return True
        
    except ConnectionError as e:
        print_test("Connection", "FAIL", f"Cannot connect: {str(e)}")
        return False
    except AuthenticationException as e:
        print_test("Authentication", "FAIL", f"Authentication failed: {str(e)}")
        return False
    except Exception as e:
        print_test("Connection", "FAIL", f"Unexpected error: {str(e)}")
        return False


def test_index_exists(client: Elasticsearch) -> bool:
    """Test 3: Check if index exists"""
    print_section("Test 3: Index Existence")
    
    try:
        exists = client.indices.exists(index=INDEX_NAME)
        if exists:
            print_test(f"Index '{INDEX_NAME}' exists", "PASS")
            return True
        else:
            print_test(f"Index '{INDEX_NAME}' exists", "FAIL", 
                       "Index does not exist. You may need to create it.")
            return False
    except Exception as e:
        print_test("Index check", "FAIL", f"Error checking index: {str(e)}")
        return False


def test_index_mapping(client: Elasticsearch) -> bool:
    """Test 4: Validate index mapping"""
    print_section("Test 4: Index Mapping Validation")
    
    try:
        mapping = client.indices.get_mapping(index=INDEX_NAME)
        index_mapping = mapping[INDEX_NAME]["mappings"].get("properties", {})
        
        all_passed = True
        
        # Check each required field
        for field_name, expected_config in REQUIRED_FIELDS.items():
            if field_name not in index_mapping:
                print_test(f"Field '{field_name}'", "FAIL", "Field not found in mapping")
                all_passed = False
                continue
            
            field_mapping = index_mapping[field_name]
            field_type = field_mapping.get("type")
            expected_type = expected_config["type"]
            
            if field_type != expected_type:
                print_test(f"Field '{field_name}' type", "FAIL", 
                          f"Expected '{expected_type}', got '{field_type}'")
                all_passed = False
            else:
                print_test(f"Field '{field_name}' type", "PASS", f"Type: {field_type}")
            
            # For dense_vector fields, check dimensions
            if field_type == "dense_vector":
                expected_dims = expected_config.get("dims")
                actual_dims = field_mapping.get("dims")
                
                if actual_dims != expected_dims:
                    print_test(f"Field '{field_name}' dimensions", "FAIL",
                              f"Expected {expected_dims} dims, got {actual_dims}")
                    all_passed = False
                else:
                    print_test(f"Field '{field_name}' dimensions", "PASS", 
                              f"{actual_dims} dimensions")
                
                # Check if indexing is enabled
                index_enabled = field_mapping.get("index", True)
                if not index_enabled:
                    print_test(f"Field '{field_name}' indexing", "WARN",
                              "Indexing disabled - knn search may not work")
        
        # Check for ELSER field (optional)
        if ELSER_FIELD in index_mapping:
            field_type = index_mapping[ELSER_FIELD].get("type")
            if field_type == "sparse_vector":
                print_test(f"Field '{ELSER_FIELD}' (ELSER)", "PASS", 
                          "ELSER sparse vector field found")
            else:
                print_test(f"Field '{ELSER_FIELD}' (ELSER)", "WARN",
                          f"Found but type is '{field_type}', expected 'sparse_vector'")
        else:
            print_test(f"Field '{ELSER_FIELD}' (ELSER)", "WARN",
                      "ELSER field not found - sparse embeddings will not work")
        
        return all_passed
        
    except NotFoundError:
        print_test("Index mapping", "FAIL", "Index does not exist")
        return False
    except Exception as e:
        print_test("Index mapping", "FAIL", f"Error reading mapping: {str(e)}")
        return False


def test_elser_model(client: Elasticsearch) -> bool:
    """Test 5: Check ELSER model availability"""
    print_section("Test 5: ELSER Model Availability")
    
    try:
        # Check if ELSER model is deployed
        ml_models = client.ml.get_trained_models(model_id=".elser_model_2")
        print_test("ELSER model deployed", "PASS", "ELSER model is available")
        return True
    except NotFoundError:
        print_test("ELSER model deployed", "WARN",
                  "ELSER model not found. Sparse embeddings will not work.")
        print("   To deploy ELSER: PUT _ml/trained_models/.elser_model_2/_deploy")
        return False
    except Exception as e:
        print_test("ELSER model check", "WARN", f"Could not check ELSER: {str(e)}")
        return False


def test_indexing(client: Elasticsearch) -> bool:
    """Test 6: Test document indexing"""
    print_section("Test 6: Document Indexing")
    
    try:
        # Create a test document with all embedding types
        test_doc = {
            "icon_name": "test_icon",
            "descriptions": ["A test icon for validation"],
            "text_embedding": [0.1] * 384,  # Dummy 384-dim vector
            "image_embedding": [0.2] * 384,  # Dummy 384-dim vector
            "svg_embedding": [0.3] * 384,    # Dummy 384-dim vector
        }
        
        # Index the document
        response = client.index(
            index=INDEX_NAME,
            id=TEST_DOC_ID,
            document=test_doc
        )
        
        if response.get("result") in ["created", "updated"]:
            print_test("Index document", "PASS", 
                      f"Document indexed (result: {response.get('result')})")
            
            # Refresh index to make document searchable
            client.indices.refresh(index=INDEX_NAME)
            print_test("Index refresh", "PASS", "Index refreshed")
            
            return True
        else:
            print_test("Index document", "FAIL", 
                      f"Unexpected result: {response.get('result')}")
            return False
            
    except RequestError as e:
        error_info = e.info.get("error", {}) if hasattr(e, "info") else {}
        root_cause = error_info.get("root_cause", [{}])[0].get("reason", str(e))
        print_test("Index document", "FAIL", f"Error: {root_cause}")
        return False
    except Exception as e:
        print_test("Index document", "FAIL", f"Unexpected error: {str(e)}")
        return False


def test_dense_vector_search(client: Elasticsearch) -> bool:
    """Test 7: Test dense vector (knn) search"""
    print_section("Test 7: Dense Vector Search (knn)")
    
    try:
        # Test knn search on text_embedding
        query_vector = [0.1] * 384
        
        response = client.search(
            index=INDEX_NAME,
            body={
                "knn": {
                    "field": "text_embedding",
                    "query_vector": query_vector,
                    "k": 5,
                    "num_candidates": 10
                },
                "size": 5
            }
        )
        
        hits = response.get("hits", {}).get("hits", [])
        if hits:
            print_test("knn search (text_embedding)", "PASS", 
                      f"Found {len(hits)} results")
        else:
            print_test("knn search (text_embedding)", "WARN",
                      "No results found (may be expected if index is empty)")
        
        # Test knn search on image_embedding
        response = client.search(
            index=INDEX_NAME,
            body={
                "knn": {
                    "field": "image_embedding",
                    "query_vector": query_vector,
                    "k": 5,
                    "num_candidates": 10
                },
                "size": 5
            }
        )
        
        hits = response.get("hits", {}).get("hits", [])
        if hits:
            print_test("knn search (image_embedding)", "PASS", 
                      f"Found {len(hits)} results")
        else:
            print_test("knn search (image_embedding)", "WARN",
                      "No results found (may be expected if index is empty)")
        
        return True
        
    except RequestError as e:
        error_info = e.info.get("error", {}) if hasattr(e, "info") else {}
        root_cause = error_info.get("root_cause", [{}])[0].get("reason", str(e))
        print_test("knn search", "FAIL", f"Error: {root_cause}")
        return False
    except Exception as e:
        print_test("knn search", "FAIL", f"Unexpected error: {str(e)}")
        return False


def test_elser_search(client: Elasticsearch) -> bool:
    """Test 8: Test ELSER sparse vector search"""
    print_section("Test 8: ELSER Sparse Vector Search")
    
    try:
        # Check if ELSER field exists in mapping
        mapping = client.indices.get_mapping(index=INDEX_NAME)
        index_mapping = mapping[INDEX_NAME]["mappings"].get("properties", {})
        
        if ELSER_FIELD not in index_mapping:
            print_test("ELSER search", "SKIP", "ELSER field not in mapping")
            return True  # Not a failure, just optional
        
        # Test text_expansion query (ELSER)
        response = client.search(
            index=INDEX_NAME,
            body={
                "query": {
                    "text_expansion": {
                        ELSER_FIELD: {
                            "model_text": "test query",
                            "model_id": ".elser_model_2"
                        }
                    }
                },
                "size": 5
            }
        )
        
        hits = response.get("hits", {}).get("hits", [])
        print_test("ELSER text_expansion search", "PASS", 
                  f"Query executed successfully (found {len(hits)} results)")
        return True
        
    except NotFoundError:
        print_test("ELSER search", "WARN", "ELSER model not deployed")
        return False
    except RequestError as e:
        error_info = e.info.get("error", {}) if hasattr(e, "info") else {}
        root_cause = error_info.get("root_cause", [{}])[0].get("reason", str(e))
        print_test("ELSER search", "FAIL", f"Error: {root_cause}")
        return False
    except Exception as e:
        print_test("ELSER search", "WARN", f"Could not test ELSER: {str(e)}")
        return False


def test_hybrid_search(client: Elasticsearch) -> bool:
    """Test 9: Test hybrid search (dense + sparse)"""
    print_section("Test 9: Hybrid Search (Dense + Sparse)")
    
    try:
        query_vector = [0.1] * 384
        
        # Build hybrid query
        body = {
            "knn": {
                "field": "text_embedding",
                "query_vector": query_vector,
                "k": 5,
                "num_candidates": 10
            },
            "size": 5
        }
        
        # Add ELSER query if available
        mapping = client.indices.get_mapping(index=INDEX_NAME)
        index_mapping = mapping[INDEX_NAME]["mappings"].get("properties", {})
        
        if ELSER_FIELD in index_mapping:
            body["query"] = {
                "text_expansion": {
                    ELSER_FIELD: {
                        "model_text": "test query",
                        "model_id": ".elser_model_2"
                    }
                }
            }
        
        response = client.search(
            index=INDEX_NAME,
            body=body
        )
        
        hits = response.get("hits", {}).get("hits", [])
        print_test("Hybrid search", "PASS", 
                  f"Hybrid query executed (found {len(hits)} results)")
        return True
        
    except Exception as e:
        print_test("Hybrid search", "WARN", f"Could not test hybrid search: {str(e)}")
        return False


def cleanup_test_document(client: Elasticsearch):
    """Clean up test document"""
    try:
        client.delete(index=INDEX_NAME, id=TEST_DOC_ID, ignore=[404])
        print(f"\n{Colors.BLUE}Cleaned up test document{Colors.RESET}")
    except Exception:
        pass  # Ignore cleanup errors


def main():
    """Run all tests"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("=" * 60)
    print("Elasticsearch Setup Validation Test Suite")
    print("=" * 60)
    print(f"{Colors.RESET}\n")
    
    # Test 1: Environment variables
    if not test_environment_variables():
        print(f"\n{Colors.RED}Tests failed: Missing environment variables{Colors.RESET}")
        sys.exit(1)
    
    # Initialize Elasticsearch client
    try:
        client = Elasticsearch(
            [os.getenv("ELASTICSEARCH_ENDPOINT")],
            api_key=os.getenv("ELASTICSEARCH_API_KEY"),
            request_timeout=30
        )
    except Exception as e:
        print(f"\n{Colors.RED}Failed to create Elasticsearch client: {str(e)}{Colors.RESET}")
        sys.exit(1)
    
    # Run tests
    results = []
    
    results.append(("Connection", test_connection(client)))
    results.append(("Index Exists", test_index_exists(client)))
    results.append(("Index Mapping", test_index_mapping(client)))
    results.append(("ELSER Model", test_elser_model(client)))
    results.append(("Indexing", test_indexing(client)))
    results.append(("Dense Vector Search", test_dense_vector_search(client)))
    results.append(("ELSER Search", test_elser_search(client)))
    results.append(("Hybrid Search", test_hybrid_search(client)))
    
    # Cleanup
    cleanup_test_document(client)
    
    # Summary
    print_section("Test Summary")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print_test(test_name, status)
    
    print(f"\n{Colors.BOLD}Results: {passed}/{total} tests passed{Colors.RESET}\n")
    
    if passed == total:
        print(f"{Colors.GREEN}✓ All critical tests passed! Your Elasticsearch cluster is ready.{Colors.RESET}\n")
        sys.exit(0)
    else:
        print(f"{Colors.YELLOW}⚠ Some tests failed or were skipped. Review the output above.{Colors.RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()

