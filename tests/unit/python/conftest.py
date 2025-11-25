"""
Shared pytest fixtures for unit tests
"""
import os
import pytest
from unittest.mock import Mock, MagicMock, patch
from fastapi.testclient import TestClient
from typing import Generator
import numpy as np
from PIL import Image
import base64
import io

# Import the app after setting up mocks
# We'll import it conditionally to avoid loading models during test discovery


@pytest.fixture(scope="session")
def mock_environment_variables():
    """Set up mock environment variables for testing"""
    env_vars = {
        "ELASTICSEARCH_ENDPOINT": "https://test-es.example.com",
        "ELASTICSEARCH_API_KEY": "test-api-key",
        "API_KEYS": "test-key-1,test-key-2",
        "CORS_ORIGINS": "http://localhost:3000",
        "RATE_LIMIT_PER_MINUTE": "60",
        "RATE_LIMIT_PER_HOUR": "1000",
        "OTEL_SERVICE_NAME": "eui-python-api-test",
        "OTEL_SERVICE_VERSION": "test-version",
        "OTEL_EXPORTER_OTLP_ENDPOINT": "https://test-otel.example.com",
        "OTEL_EXPORTER_OTLP_HEADERS": "Authorization=Bearer test-token",
    }
    
    # Save original values
    original_env = {}
    for key, value in env_vars.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    yield env_vars
    
    # Restore original values
    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


@pytest.fixture
def mock_elasticsearch_client():
    """Create a mock Elasticsearch client"""
    mock_client = Mock()
    
    # Mock common Elasticsearch methods
    mock_client.search = Mock(return_value={
        "hits": {
            "total": {"value": 2},
            "hits": [
                {
                    "_id": "icon1",
                    "_score": 0.95,
                    "_source": {
                        "icon_name": "icon1",
                        "descriptions": ["test icon 1"],
                        "icon_type": "icon"
                    }
                },
                {
                    "_id": "icon2",
                    "_score": 0.85,
                    "_source": {
                        "icon_name": "icon2",
                        "descriptions": ["test icon 2"],
                        "icon_type": "icon"
                    }
                }
            ]
        }
    })
    
    mock_client.exists = Mock(return_value=False)
    mock_client.get = Mock(return_value={
        "_id": "icon1",
        "_source": {
            "icon_name": "icon1",
            "text_embedding": [0.1] * 384,
            "image_embedding": [0.2] * 512
        }
    })
    mock_client.index = Mock(return_value={"_id": "icon1", "result": "created"})
    mock_client.update = Mock(return_value={"_id": "icon1", "result": "updated"})
    mock_client.ml = Mock()
    mock_client.ml.infer_trained_model = Mock(return_value={
        "inference_results": [{
            "predicted_value": {
                "text_embedding_sparse": {
                    "test": 0.5,
                    "icon": 0.3
                }
            }
        }]
    })
    
    return mock_client


@pytest.fixture
def mock_text_model():
    """Create a mock SentenceTransformer model for text embeddings"""
    mock_model = Mock()
    mock_model.encode = Mock(return_value=np.array([0.1] * 384))
    mock_model.get_sentence_embedding_dimension = Mock(return_value=384)
    return mock_model


@pytest.fixture
def mock_image_model():
    """Create a mock SentenceTransformer model for image embeddings"""
    mock_model = Mock()
    mock_model.encode = Mock(return_value=np.array([0.2] * 512))
    mock_model.get_sentence_embedding_dimension = Mock(return_value=512)
    return mock_model


@pytest.fixture
def sample_svg_content():
    """Sample SVG content for testing"""
    return """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 2L2 7v10l10 5 10-5V7L12 2z"/>
    </svg>"""


@pytest.fixture
def sample_base64_image():
    """Sample base64-encoded image for testing"""
    # Create a simple 224x224 RGB image
    img = Image.new('RGB', (224, 224), color='white')
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_bytes = buffer.getvalue()
    return base64.b64encode(img_bytes).decode('utf-8')


@pytest.fixture
def sample_pil_image():
    """Sample PIL Image for testing"""
    return Image.new('RGB', (224, 224), color='white')


@pytest.fixture
def sample_embeddings():
    """Sample embedding vectors for testing"""
    return {
        "text": [0.1] * 384,
        "image": [0.2] * 512,
        "svg": [0.3] * 512
    }


@pytest.fixture
def sample_search_results():
    """Sample Elasticsearch search results"""
    return {
        "hits": {
            "total": {"value": 2},
            "hits": [
                {
                    "_id": "icon1",
                    "_score": 0.95,
                    "_source": {
                        "icon_name": "icon1",
                        "descriptions": ["test icon 1"],
                        "icon_type": "icon",
                        "text_embedding": [0.1] * 384,
                        "image_embedding": [0.2] * 512
                    }
                },
                {
                    "_id": "icon2",
                    "_score": 0.85,
                    "_source": {
                        "icon_name": "icon2",
                        "descriptions": ["test icon 2"],
                        "icon_type": "icon",
                        "text_embedding": [0.1] * 384,
                        "image_embedding": [0.2] * 512
                    }
                }
            ]
        }
    }


@pytest.fixture
def fastapi_app(mock_environment_variables, mock_elasticsearch_client, mock_text_model, mock_image_model):
    """Create FastAPI app instance with mocked dependencies"""
    # Patch dependencies before importing embed
    with patch('embed.Elasticsearch') as mock_es_class, \
         patch('embed.SentenceTransformer') as mock_st_class, \
         patch('embed.es_client', mock_elasticsearch_client):
        
        # Configure mocks
        mock_es_class.return_value = mock_elasticsearch_client
        mock_st_class.side_effect = [mock_text_model, mock_image_model]
        
        # Import app after patching
        from embed import app
        return app


@pytest.fixture
def client(fastapi_app):
    """Create FastAPI test client"""
    return TestClient(fastapi_app)


@pytest.fixture
def authenticated_client(client):
    """Create authenticated test client with API key"""
    client.headers = {"X-API-Key": "test-key-1"}
    return client


@pytest.fixture
def mock_requests():
    """Mock requests library for external API calls"""
    with patch('requests.get') as mock_get, \
         patch('requests.post') as mock_post:
        yield {
            'get': mock_get,
            'post': mock_post
        }


@pytest.fixture
def mock_cairosvg():
    """Mock cairosvg for SVG to PNG conversion"""
    with patch('cairosvg.svg2png') as mock_svg2png:
        # Return a valid PNG byte string
        img = Image.new('RGB', (224, 224), color='white')
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        mock_svg2png.return_value = buffer.getvalue()
        yield mock_svg2png


@pytest.fixture
def mock_pil_image():
    """Mock PIL Image operations"""
    with patch('PIL.Image.open') as mock_open, \
         patch('PIL.Image.new') as mock_new:
        # Create a mock image
        mock_img = Mock(spec=Image.Image)
        mock_img.size = (224, 224)
        mock_img.mode = 'RGB'
        mock_img.convert = Mock(return_value=mock_img)
        
        mock_open.return_value = mock_img
        mock_new.return_value = mock_img
        
        yield {
            'open': mock_open,
            'new': mock_new,
            'image': mock_img
        }


