"""
Pytest fixtures for integration tests
"""
import pytest
import os
from elasticsearch import Elasticsearch


@pytest.fixture(scope="session")
def client():
    """
    Create Elasticsearch client for integration tests.
    Skips tests if Elasticsearch is not configured.
    """
    endpoint = os.getenv("ELASTICSEARCH_ENDPOINT")
    api_key = os.getenv("ELASTICSEARCH_API_KEY")
    
    if not endpoint or not api_key:
        pytest.skip("ELASTICSEARCH_ENDPOINT and ELASTICSEARCH_API_KEY must be set for integration tests")
    
    try:
        es_client = Elasticsearch(
            [endpoint],
            api_key=api_key,
            request_timeout=30
        )
        # Test connection
        es_client.info()
        return es_client
    except Exception as e:
        pytest.skip(f"Could not connect to Elasticsearch: {e}")


