#!/usr/bin/env python3
"""
Test suite for Phase 4: API Key Authentication

Tests API key authentication, validation, and error handling.
"""

import pytest
import os
import sys
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Add parent directory to path to import embed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from embed import app, verify_api_key, load_api_keys, _valid_api_keys


class TestAPIKeyAuthentication:
    """Test API key authentication"""
    
    def test_health_endpoint_no_auth_required(self):
        """Test that health endpoint doesn't require authentication"""
        client = TestClient(app)
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
    
    @patch.dict(os.environ, {"API_KEYS": "test-key-123,test-key-456"})
    def test_endpoint_requires_api_key_when_configured(self):
        """Test that endpoints require API key when keys are configured"""
        # Reload module to pick up new env var
        import importlib
        import embed
        importlib.reload(embed)
        
        client = TestClient(embed.app)
        
        # Test without API key
        response = client.post(
            "/search",
            json={"type": "text", "query": "test"}
        )
        
        assert response.status_code == 401
        assert "API key" in response.json()["detail"].lower()
    
    @patch.dict(os.environ, {"API_KEYS": "test-key-123"})
    def test_endpoint_with_valid_api_key(self):
        """Test that endpoints work with valid API key"""
        import importlib
        import embed
        importlib.reload(embed)
        
        client = TestClient(embed.app)
        
        # Test with valid API key
        response = client.post(
            "/search",
            json={"type": "text", "query": "test"},
            headers={"X-API-Key": "test-key-123"}
        )
        
        # Should not be 401 (may be 500 if Elasticsearch not configured, but auth passed)
        assert response.status_code != 401
    
    @patch.dict(os.environ, {"API_KEYS": "test-key-123"})
    def test_endpoint_with_invalid_api_key(self):
        """Test that endpoints reject invalid API key"""
        import importlib
        import embed
        importlib.reload(embed)
        
        client = TestClient(embed.app)
        
        # Test with invalid API key
        response = client.post(
            "/search",
            json={"type": "text", "query": "test"},
            headers={"X-API-Key": "wrong-key"}
        )
        
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]
    
    def test_backward_compatibility_no_keys(self):
        """Test backward compatibility when no keys are configured"""
        with patch.dict(os.environ, {"API_KEYS": ""}, clear=False):
            import importlib
            import embed
            importlib.reload(embed)
            
            client = TestClient(embed.app)
            
            # Should work without API key when no keys configured
            response = client.post(
                "/search",
                json={"type": "text", "query": "test"}
            )
            
            # Should not be 401 (backward compatible)
            assert response.status_code != 401
    
    @patch.dict(os.environ, {"API_KEY_HEADER": "X-Custom-API-Key"})
    def test_custom_api_key_header(self):
        """Test custom API key header name"""
        import importlib
        import embed
        importlib.reload(embed)
        
        # Set API keys
        embed.API_KEYS_ENV = "test-key-123"
        embed.load_api_keys()
        
        client = TestClient(embed.app)
        
        # Test with custom header
        response = client.post(
            "/search",
            json={"type": "text", "query": "test"},
            headers={"X-Custom-API-Key": "test-key-123"}
        )
        
        # Should not be 401
        assert response.status_code != 401


class TestAPIKeyLoading:
    """Test API key loading from environment"""
    
    @patch.dict(os.environ, {"API_KEYS": "key1,key2,key3"})
    def test_load_keys_from_env(self):
        """Test loading keys from environment variable"""
        import importlib
        import embed
        importlib.reload(embed)
        
        assert len(embed._valid_api_keys) >= 3
        assert "key1" in embed._valid_api_keys
        assert "key2" in embed._valid_api_keys
        assert "key3" in embed._valid_api_keys
    
    @patch.dict(os.environ, {"API_KEYS": "key1, key2 , key3 "})
    def test_load_keys_with_whitespace(self):
        """Test loading keys with whitespace is trimmed"""
        import importlib
        import embed
        importlib.reload(embed)
        
        assert "key1" in embed._valid_api_keys
        assert "key2" in embed._valid_api_keys
        assert "key3" in embed._valid_api_keys


class TestVerifyAPIKeyFunction:
    """Test verify_api_key dependency function"""
    
    def test_verify_with_no_keys_configured(self):
        """Test verification when no keys are configured"""
        from fastapi import Request
        
        # Mock request
        request = MagicMock(spec=Request)
        
        # Set empty keys
        with patch('embed._valid_api_keys', set()):
            result = verify_api_key(request)
            assert result is True  # Should allow when no keys configured
    
    def test_verify_with_valid_key(self):
        """Test verification with valid key"""
        from fastapi import Request
        
        # Mock request with valid key
        request = MagicMock(spec=Request)
        request.headers.get.return_value = "test-key-123"
        
        with patch('embed._valid_api_keys', {"test-key-123"}):
            with patch('embed.API_KEY_HEADER', "X-API-Key"):
                result = verify_api_key(request)
                assert result is True
    
    def test_verify_with_missing_key(self):
        """Test verification with missing key"""
        from fastapi import Request
        from fastapi import HTTPException
        
        # Mock request without key
        request = MagicMock(spec=Request)
        request.headers.get.return_value = None
        
        with patch('embed._valid_api_keys', {"test-key-123"}):
            with patch('embed.API_KEY_HEADER', "X-API-Key"):
                with pytest.raises(HTTPException) as exc_info:
                    verify_api_key(request)
                
                assert exc_info.value.status_code == 401
                assert "required" in exc_info.value.detail.lower()
    
    def test_verify_with_invalid_key(self):
        """Test verification with invalid key"""
        from fastapi import Request
        from fastapi import HTTPException
        
        # Mock request with invalid key
        request = MagicMock(spec=Request)
        request.headers.get.return_value = "wrong-key"
        
        with patch('embed._valid_api_keys', {"test-key-123"}):
            with patch('embed.API_KEY_HEADER', "X-API-Key"):
                with pytest.raises(HTTPException) as exc_info:
                    verify_api_key(request)
                
                assert exc_info.value.status_code == 401
                assert "Invalid" in exc_info.value.detail


def test_manage_api_keys_script_exists():
    """Test that API key management script exists"""
    import os
    
    assert os.path.exists("scripts/manage/manage-api-keys.sh"), "manage-api-keys.sh not found"
    assert os.access("scripts/manage/manage-api-keys.sh", os.X_OK), "manage-api-keys.sh not executable"


def test_api_key_rotation_docs_exist():
    """Test that API key rotation documentation exists"""
    import os
    
    assert os.path.exists("docs/API_KEY_ROTATION.md"), "API_KEY_ROTATION.md not found"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])

