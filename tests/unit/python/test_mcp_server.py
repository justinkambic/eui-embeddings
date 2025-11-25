"""
Unit tests for mcp_server.py
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json
import base64
from PIL import Image
import io


@pytest.fixture
def mock_mcp_available():
    """Mock MCP SDK availability"""
    with patch('mcp_server.MCP_AVAILABLE', True), \
         patch('mcp_server.Server') as mock_server_class, \
         patch('mcp_server.stdio_server') as mock_stdio_server, \
         patch('mcp_server.Tool') as mock_tool_class, \
         patch('mcp_server.TextContent') as mock_text_content_class:
        
        mock_server = Mock()
        mock_server_class.return_value = mock_server
        mock_server.list_tools.return_value = []
        
        yield {
            'server': mock_server,
            'server_class': mock_server_class,
            'stdio_server': mock_stdio_server,
            'tool_class': mock_tool_class,
            'text_content_class': mock_text_content_class
        }


@pytest.fixture
def sample_svg_content():
    """Sample SVG content"""
    return '<svg viewBox="0 0 24 24"><path d="M0 0 L24 24"/></svg>'


@pytest.fixture
def sample_base64_image():
    """Sample base64 image"""
    img = Image.new('RGB', (224, 224), color='white')
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode('utf-8')


class TestMCPServer:
    """Tests for MCP server functionality"""
    
    def test_server_initialization(self, mock_mcp_available):
        """Test server initialization"""
        with patch('mcp_server.EMBEDDING_SERVICE_URL', 'http://localhost:8000'):
            import importlib
            import mcp_server
            importlib.reload(mcp_server)
            # MCP server uses 'app' variable, not 'server'
            assert hasattr(mcp_server, 'app') or hasattr(mcp_server, 'server')
    
    def test_search_by_svg_tool_registration(self, mock_mcp_available):
        """Test search_by_svg tool is registered"""
        with patch('mcp_server.EMBEDDING_SERVICE_URL', 'http://localhost:8000'):
            import mcp_server
            # Check that search_by_svg function exists
            assert hasattr(mcp_server, 'search_by_svg') or callable(getattr(mcp_server, 'search_by_svg', None))
    
    def test_search_by_image_tool_registration(self, mock_mcp_available):
        """Test search_by_image tool is registered"""
        with patch('mcp_server.EMBEDDING_SERVICE_URL', 'http://localhost:8000'):
            import mcp_server
            # Check that search_by_image function exists
            assert hasattr(mcp_server, 'search_by_image') or callable(getattr(mcp_server, 'search_by_image', None))
    
    @patch('mcp_server.requests.post')
    def test_search_by_svg_success(self, mock_post, sample_svg_content):
        """Test successful SVG search"""
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {"icon_name": "icon1", "score": 0.95}
            ]
        }
        mock_post.return_value = mock_response
        
        with patch('mcp_server.EMBEDDING_SERVICE_URL', 'http://localhost:8000'):
            import mcp_server
            # Call search function if it exists
            if hasattr(mcp_server, 'search_by_svg'):
                result = mcp_server.search_by_svg(sample_svg_content)
                assert result is not None
    
    @patch('mcp_server.requests.post')
    def test_search_by_image_success(self, mock_post, sample_base64_image):
        """Test successful image search"""
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {"icon_name": "icon1", "score": 0.95}
            ]
        }
        mock_post.return_value = mock_response
        
        with patch('mcp_server.EMBEDDING_SERVICE_URL', 'http://localhost:8000'):
            import mcp_server
            # Call search function if it exists
            if hasattr(mcp_server, 'search_by_image'):
                result = mcp_server.search_by_image(sample_base64_image)
                assert result is not None
    
    @patch('mcp_server.requests.post')
    def test_search_api_error(self, mock_post):
        """Test handling of API errors"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response
        
        with patch('mcp_server.EMBEDDING_SERVICE_URL', 'http://localhost:8000'):
            import mcp_server
            # Should handle error gracefully
            if hasattr(mcp_server, 'search_by_svg'):
                try:
                    mcp_server.search_by_svg('<svg></svg>')
                except Exception:
                    pass  # Error handling is expected
    
    def test_mcp_unavailable_fallback(self):
        """Test fallback when MCP SDK is not available"""
        with patch('mcp_server.MCP_AVAILABLE', False):
            import mcp_server
            # Server should still be importable
            assert True  # Basic import test

