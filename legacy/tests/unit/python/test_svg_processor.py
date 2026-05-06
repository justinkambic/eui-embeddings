"""
Unit tests for svg_processor.py
"""
import pytest
from unittest.mock import patch, Mock
from PIL import Image
import io
from svg_processor import normalize_svg, svg_to_image, extract_svg_layers


class TestNormalizeSVG:
    """Tests for normalize_svg function"""
    
    def test_normalize_svg_with_viewbox(self):
        """Test normalization of SVG with viewBox"""
        svg = '<svg viewBox="0 0 24 24"><path d="M0 0 L24 24"/></svg>'
        normalized = normalize_svg(svg, target_size=224)
        assert 'viewBox="0 0 24 24"' in normalized
        assert 'width="224"' in normalized
        assert 'height="224"' in normalized
    
    def test_normalize_svg_with_width_height(self):
        """Test normalization of SVG with width and height"""
        svg = '<svg width="48" height="48"><path d="M0 0 L48 48"/></svg>'
        normalized = normalize_svg(svg, target_size=224)
        assert 'width="224"' in normalized
        assert 'height="224"' in normalized
    
    def test_normalize_svg_without_dimensions(self):
        """Test normalization of SVG without dimensions"""
        svg = '<svg><path d="M0 0 L24 24"/></svg>'
        normalized = normalize_svg(svg, target_size=224)
        assert 'viewBox="0 0 24 24"' in normalized  # Default viewBox
        assert 'width="224"' in normalized
    
    def test_normalize_svg_empty_content(self):
        """Test normalization of empty SVG"""
        svg = ""
        normalized = normalize_svg(svg)
        assert normalized is None
    
    def test_normalize_svg_different_target_size(self):
        """Test normalization with different target size"""
        svg = '<svg viewBox="0 0 24 24"><path d="M0 0 L24 24"/></svg>'
        normalized = normalize_svg(svg, target_size=128)
        assert 'width="128"' in normalized
        assert 'height="128"' in normalized
    
    def test_normalize_svg_preserves_content(self):
        """Test that normalization preserves SVG content"""
        svg = '<svg viewBox="0 0 24 24"><path d="M0 0 L24 24"/><circle cx="12" cy="12" r="5"/></svg>'
        normalized = normalize_svg(svg)
        assert '<path d="M0 0 L24 24"/>' in normalized
        assert '<circle cx="12" cy="12" r="5"/>' in normalized


class TestSVGToImage:
    """Tests for svg_to_image function"""
    
    @patch('svg_processor.svg2png')
    @patch('svg_processor.Image')
    def test_svg_to_image_success(self, mock_image_module, mock_svg2png):
        """Test successful SVG to image conversion"""
        # Setup mocks
        mock_img = Image.new('RGB', (224, 224), color='white')
        buffer = io.BytesIO()
        mock_img.save(buffer, format='PNG')
        mock_svg2png.return_value = buffer.getvalue()
        mock_image_module.open.return_value = mock_img
        
        svg = '<svg viewBox="0 0 24 24"><path d="M0 0 L24 24"/></svg>'
        result = svg_to_image(svg, target_size=224)
        
        assert isinstance(result, Image.Image)
        assert result.size == (224, 224)
        assert result.mode == 'RGB'
        mock_svg2png.assert_called_once()
    
    @patch('svg_processor.svg2png')
    def test_svg_to_image_conversion_error(self, mock_svg2png):
        """Test SVG to image conversion with error"""
        mock_svg2png.side_effect = Exception("Conversion failed")
        
        svg = '<svg viewBox="0 0 24 24"><path d="M0 0 L24 24"/></svg>'
        with pytest.raises(ValueError, match="Error converting SVG to PNG"):
            svg_to_image(svg)
    
    @patch('svg_processor.svg2png')
    @patch('svg_processor.Image')
    def test_svg_to_image_non_rgb(self, mock_image_module, mock_svg2png):
        """Test SVG to image conversion with non-RGB result"""
        # Create RGBA image
        mock_img = Image.new('RGBA', (224, 224), color=(255, 255, 255, 255))
        buffer = io.BytesIO()
        mock_img.save(buffer, format='PNG')
        mock_svg2png.return_value = buffer.getvalue()
        
        # Mock convert method
        rgb_img = Image.new('RGB', (224, 224), color='white')
        mock_img.convert = Mock(return_value=rgb_img)
        mock_image_module.open.return_value = mock_img
        
        svg = '<svg viewBox="0 0 24 24"><path d="M0 0 L24 24"/></svg>'
        result = svg_to_image(svg)
        
        assert result.mode == 'RGB'
        mock_img.convert.assert_called_once_with('RGB')


class TestExtractSVGLayers:
    """Tests for extract_svg_layers function"""
    
    def test_extract_paths(self):
        """Test extraction of path elements"""
        svg = '<svg><path d="M0 0 L10 10"/><path d="M5 5 L15 15"/></svg>'
        layers = extract_svg_layers(svg)
        assert len(layers) == 2
        assert all('<path' in layer for layer in layers)
    
    def test_extract_circles(self):
        """Test extraction of circle elements"""
        svg = '<svg><circle cx="10" cy="10" r="5"/><circle cx="20" cy="20" r="3"/></svg>'
        layers = extract_svg_layers(svg)
        assert len(layers) == 2
        assert all('<circle' in layer for layer in layers)
    
    def test_extract_rects(self):
        """Test extraction of rect elements"""
        svg = '<svg><rect x="0" y="0" width="10" height="10"/><rect x="5" y="5" width="5" height="5"/></svg>'
        layers = extract_svg_layers(svg)
        assert len(layers) == 2
        assert all('<rect' in layer for layer in layers)
    
    def test_extract_mixed_elements(self):
        """Test extraction of mixed element types"""
        svg = '<svg><path d="M0 0"/><circle cx="10" cy="10" r="5"/><rect x="0" y="0" width="10" height="10"/></svg>'
        layers = extract_svg_layers(svg)
        assert len(layers) == 3
    
    def test_extract_no_elements(self):
        """Test extraction from SVG with no extractable elements"""
        svg = '<svg><text>Hello</text></svg>'
        layers = extract_svg_layers(svg)
        assert len(layers) == 0
    
    def test_extract_case_insensitive(self):
        """Test extraction is case insensitive"""
        svg = '<svg><PATH d="M0 0"/><CIRCLE cx="10" cy="10" r="5"/></svg>'
        layers = extract_svg_layers(svg)
        assert len(layers) == 2


