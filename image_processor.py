"""
Image Processing Utilities

Functions for normalizing and processing images for embedding.
"""

from PIL import Image
import io
import numpy as np
from typing import Union

def detect_background_color(image: Image.Image, sample_size: int = 5) -> bool:
    """
    Detect if background is dark (True) or light (False).
    
    Samples edge and corner pixels to determine dominant background color.
    
    Args:
        image: PIL Image (should be grayscale or RGB)
        sample_size: Number of pixels to sample from each edge/corner
    
    Returns:
        True if background is dark (needs inversion), False if light
    """
    # Convert to numpy array
    img_array = np.array(image)
    
    # Convert to grayscale if RGB
    if len(img_array.shape) == 3:
        # Use luminance formula: 0.299*R + 0.587*G + 0.114*B
        gray_array = np.dot(img_array[...,:3], [0.299, 0.587, 0.114])
    else:
        gray_array = img_array
    
    height, width = gray_array.shape
    
    # Sample edge pixels (top, bottom, left, right) and corners
    edge_pixels = []
    
    # Top edge
    edge_pixels.extend(gray_array[0, :sample_size].flatten())
    edge_pixels.extend(gray_array[0, -sample_size:].flatten())
    
    # Bottom edge
    edge_pixels.extend(gray_array[-1, :sample_size].flatten())
    edge_pixels.extend(gray_array[-1, -sample_size:].flatten())
    
    # Left edge
    edge_pixels.extend(gray_array[:sample_size, 0].flatten())
    edge_pixels.extend(gray_array[-sample_size:, 0].flatten())
    
    # Right edge
    edge_pixels.extend(gray_array[:sample_size, -1].flatten())
    edge_pixels.extend(gray_array[-sample_size:, -1].flatten())
    
    # Calculate average brightness
    avg_brightness = np.mean(edge_pixels)
    
    # If average brightness is below 128 (midpoint), background is dark
    return avg_brightness < 128

def normalize_search_image(image: Image.Image, target_size: int = 224) -> Image.Image:
    """
    Normalize search image to match embedding style (white background, black icon).
    
    This function:
    1. Converts to grayscale
    2. Detects background color (light/dark)
    3. Inverts if background is dark (to make it white)
    4. Ensures white background (255) with black icon (0)
    5. Resizes to target_size
    
    Args:
        image: PIL Image to normalize
        target_size: Target size in pixels (default: 224)
    
    Returns:
        Normalized PIL Image (grayscale, white background, black icon, target_size x target_size)
    """
    # Convert to RGB first if needed
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    # Convert to grayscale
    gray_image = image.convert('L')
    
    # Detect if background is dark
    is_dark_background = detect_background_color(gray_image)
    
    # Convert to numpy array for processing
    img_array = np.array(gray_image, dtype=np.float32)
    
    # Invert if background is dark
    if is_dark_background:
        img_array = 255 - img_array
    
    # Normalize to ensure white background (255) with black icon (0)
    # Find the minimum and maximum values
    min_val = np.min(img_array)
    max_val = np.max(img_array)
    
    # If there's contrast, normalize to full range (0-255)
    # This ensures background becomes white (255) and icon becomes black (0)
    if max_val > min_val:
        # Normalize to 0-255 range
        img_array = ((img_array - min_val) / (max_val - min_val)) * 255
    else:
        # If no contrast (all same color), set to white background
        img_array.fill(255)
    
    # Convert back to uint8
    img_array = np.clip(img_array, 0, 255).astype(np.uint8)
    
    # Convert back to PIL Image
    normalized_image = Image.fromarray(img_array, mode='L')
    
    # Convert to RGB (CLIP expects RGB)
    normalized_image = normalized_image.convert('RGB')
    
    # Resize to target size
    normalized_image = normalized_image.resize((target_size, target_size), Image.Resampling.LANCZOS)
    
    return normalized_image

def normalize_image(image: Union[Image.Image, bytes, str], target_size: int = 224) -> Image.Image:
    """
    Normalize an image for embedding.
    
    Args:
        image: PIL Image, image bytes, or file path
        target_size: Target size in pixels (default: 224 for CLIP)
    
    Returns:
        Normalized PIL Image (RGB, target_size x target_size)
    """
    # Load image if needed
    if isinstance(image, bytes):
        image = Image.open(io.BytesIO(image))
    elif isinstance(image, str):
        image = Image.open(image)
    
    # Convert to RGB if needed
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    # Resize to target size (maintaining aspect ratio with center crop)
    # For icons, we'll use a simple resize since they're usually square
    image = image.resize((target_size, target_size), Image.Resampling.LANCZOS)
    
    return image

def image_to_bytes(image: Image.Image, format: str = 'PNG') -> bytes:
    """Convert PIL Image to bytes"""
    buffer = io.BytesIO()
    image.save(buffer, format=format)
    return buffer.getvalue()

