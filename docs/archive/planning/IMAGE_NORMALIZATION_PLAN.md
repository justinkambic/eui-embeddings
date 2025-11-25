# Normalize Image Search for Real-World Screenshots

## Problem

Search images from real-world Kibana screenshots don't match indexed SVG embeddings because:

- Indexed embeddings: white background, black icon
- Real-world screenshots: various backgrounds (light/dark), colored icons, different styling
- CLIP embeddings are sensitive to these visual differences

## Solution

Add image preprocessing to `/embed-image` endpoint to normalize search images to match embedding style:

1. Convert to grayscale
2. Detect background color (light vs dark)
3. Invert if needed to ensure white background
4. Normalize to white background with black icon
5. (Optional) Use edge detection to extract icon region

## Implementation

### 1. Enhance `image_processor.py`

Add functions to `image_processor.py`:

- `normalize_search_image()` - Main normalization function
  - Convert to grayscale
  - Detect dominant background color (edge pixels or corner pixels)
  - Invert if background is dark (to make it white)
  - Ensure white background (255) with black icon (0)
  - Resize to 224x224

- `detect_background_color()` - Detect if background is light or dark
  - Sample edge pixels or corner pixels
  - Calculate average brightness
  - Return True if dark (needs inversion)

- `invert_if_needed()` - Invert image if background is dark
  - Check background color
  - Invert: `255 - pixel_value`
  - Return normalized image

### 2. Update `/embed-image` endpoint in `embed.py`

Modify `embed_image()` function:

- After loading image, call `normalize_search_image()` before resizing
- This ensures search images match the style of indexed SVG embeddings
- Keep existing resize to 224x224

### 3. Testing

- Test with light mode screenshots (should work as-is)
- Test with dark mode screenshots (should invert to white background)
- Test with colored icons (should normalize to black)
- Verify similarity scores improve for real-world screenshots

## Files to Modify

- `image_processor.py` - Add normalization functions
- `embed.py` - Update `/embed-image` endpoint to use normalization

## Key Functions

```python
def normalize_search_image(image: Image.Image, target_size: int = 224) -> Image.Image:
    """Normalize search image to match embedding style (white bg, black icon)"""
    # 1. Convert to grayscale
    # 2. Detect background (light/dark)
    # 3. Invert if dark background
    # 4. Ensure white background (255) with black icon (0)
    # 5. Resize to target_size
    pass

def detect_background_color(image: Image.Image) -> bool:
    """Detect if background is dark (True) or light (False)"""
    # Sample edge/corner pixels
    # Calculate average brightness
    # Return True if dark
    pass
```

## Expected Results

- Search images normalized to white background with black icon
- Better similarity scores for real-world screenshots
- Works with both light and dark mode screenshots
- Colored icons normalized to grayscale/black