"""
Image Processing Utilities

Functions for normalizing and processing images for embedding.
"""

from PIL import Image
import io
import numpy as np
from typing import Union

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

