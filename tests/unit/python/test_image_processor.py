"""
Unit tests for image_processor.py
"""
import pytest
import numpy as np
import io
from PIL import Image
from image_processor import detect_background_color, normalize_search_image, normalize_image, image_to_bytes


class TestDetectBackgroundColor:
    """Tests for detect_background_color function"""
    
    def test_detect_light_background(self):
        """Test detection of light background"""
        # Create white image
        img = Image.new('RGB', (100, 100), color='white')
        result = detect_background_color(img)
        assert result is False  # Light background
    
    def test_detect_dark_background(self):
        """Test detection of dark background"""
        # Create black image
        img = Image.new('RGB', (100, 100), color='black')
        result = detect_background_color(img)
        assert result is True  # Dark background
    
    def test_detect_gray_background(self):
        """Test detection with gray background"""
        # Create gray image (midpoint)
        img = Image.new('RGB', (100, 100), color=(128, 128, 128))
        result = detect_background_color(img)
        # Should be False (light) since 128 is at midpoint
        assert isinstance(result, bool)
    
    def test_detect_with_grayscale_image(self):
        """Test detection with grayscale image"""
        img = Image.new('L', (100, 100), color=200)  # Light gray
        result = detect_background_color(img)
        assert result is False
    
    def test_detect_with_small_image(self):
        """Test detection with small image"""
        img = Image.new('RGB', (10, 10), color='white')
        result = detect_background_color(img)
        assert result is False


class TestNormalizeSearchImage:
    """Tests for normalize_search_image function"""
    
    def test_normalize_white_background_image(self):
        """Test normalization of image with white background"""
        img = Image.new('RGB', (100, 100), color='white')
        normalized = normalize_search_image(img, target_size=224)
        assert normalized.size == (224, 224)
        assert normalized.mode == 'RGB'
    
    def test_normalize_black_background_image(self):
        """Test normalization of image with black background (should invert)"""
        img = Image.new('RGB', (100, 100), color='black')
        normalized = normalize_search_image(img, target_size=224)
        assert normalized.size == (224, 224)
        assert normalized.mode == 'RGB'
    
    def test_normalize_different_size(self):
        """Test normalization with different target size"""
        img = Image.new('RGB', (50, 50), color='white')
        normalized = normalize_search_image(img, target_size=128)
        assert normalized.size == (128, 128)
    
    def test_normalize_non_rgb_image(self):
        """Test normalization of non-RGB image"""
        img = Image.new('L', (100, 100), color=255)  # Grayscale
        normalized = normalize_search_image(img, target_size=224)
        assert normalized.mode == 'RGB'
        assert normalized.size == (224, 224)
    
    def test_normalize_with_icon_content(self):
        """Test normalization with icon-like content (black on white)"""
        # Create image with black square on white background
        img = Image.new('RGB', (100, 100), color='white')
        # Draw black square in center
        pixels = np.array(img)
        pixels[40:60, 40:60] = [0, 0, 0]  # Black square
        img = Image.fromarray(pixels)
        
        normalized = normalize_search_image(img, target_size=224)
        assert normalized.size == (224, 224)
        assert normalized.mode == 'RGB'


class TestNormalizeImage:
    """Tests for normalize_image function"""
    
    def test_normalize_pil_image(self):
        """Test normalization of PIL Image"""
        img = Image.new('RGB', (100, 100), color='red')
        normalized = normalize_image(img, target_size=224)
        assert normalized.size == (224, 224)
        assert normalized.mode == 'RGB'
    
    def test_normalize_image_bytes(self):
        """Test normalization of image bytes"""
        img = Image.new('RGB', (100, 100), color='blue')
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_bytes = buffer.getvalue()
        
        normalized = normalize_image(img_bytes, target_size=224)
        assert normalized.size == (224, 224)
        assert normalized.mode == 'RGB'
    
    def test_normalize_non_rgb(self):
        """Test normalization of non-RGB image"""
        img = Image.new('L', (100, 100), color=128)  # Grayscale
        normalized = normalize_image(img, target_size=224)
        assert normalized.mode == 'RGB'
        assert normalized.size == (224, 224)


class TestImageToBytes:
    """Tests for image_to_bytes function"""
    
    def test_image_to_bytes_png(self):
        """Test converting image to PNG bytes"""
        img = Image.new('RGB', (100, 100), color='white')
        img_bytes = image_to_bytes(img, format='PNG')
        assert isinstance(img_bytes, bytes)
        assert len(img_bytes) > 0
    
    def test_image_to_bytes_jpeg(self):
        """Test converting image to JPEG bytes"""
        img = Image.new('RGB', (100, 100), color='white')
        img_bytes = image_to_bytes(img, format='JPEG')
        assert isinstance(img_bytes, bytes)
        assert len(img_bytes) > 0
    
    def test_image_to_bytes_default(self):
        """Test converting image with default format"""
        img = Image.new('RGB', (100, 100), color='white')
        img_bytes = image_to_bytes(img)
        assert isinstance(img_bytes, bytes)
        assert len(img_bytes) > 0

