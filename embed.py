from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from typing import List, Optional
import os
from elasticsearch import Elasticsearch
from PIL import Image
import io
import numpy as np
from cairosvg import svg2png

app = FastAPI()
text_model = SentenceTransformer("all-MiniLM-L6-v2")
image_model = SentenceTransformer("clip-ViT-B-32")

# Initialize Elasticsearch client for ELSER inference
es_client = None
if os.getenv("ELASTICSEARCH_ENDPOINT") and os.getenv("ELASTICSEARCH_API_KEY"):
    es_client = Elasticsearch(
        [os.getenv("ELASTICSEARCH_ENDPOINT")],
        api_key=os.getenv("ELASTICSEARCH_API_KEY"),
        request_timeout=30
    )

class EmbedRequest(BaseModel):
    content: str

class EmbedResponse(BaseModel):
    embeddings: List[float]
    sparse_embeddings: Optional[dict] = None

class ImageEmbedResponse(BaseModel):
    embeddings: List[float]

class SVGEmbedRequest(BaseModel):
    svg_content: str

@app.post("/embed", response_model=EmbedResponse)
async def embed_text(request: EmbedRequest):
    # Generate dense embeddings
    embeddings = text_model.encode(request.content, convert_to_numpy=True).tolist()
    
    # Generate ELSER sparse embeddings if ES client is available
    sparse_embeddings = None
    if es_client:
        try:
            # Use Elasticsearch inference API for ELSER
            inference_response = es_client.ml.infer_trained_model(
                model_id=".elser_model_2",
                body={
                    "docs": [{"text_field": request.content}]
                }
            )
            
            # Extract sparse vector from response
            if inference_response and len(inference_response.get("inference_results", [])) > 0:
                tokens = inference_response["inference_results"][0].get("predicted_value", {})
                sparse_embeddings = tokens
        except Exception as e:
            # ELSER not available or error - continue without sparse embeddings
            print(f"Warning: Could not generate ELSER embeddings: {e}")
    
    return EmbedResponse(
        embeddings=embeddings,
        sparse_embeddings=sparse_embeddings
    )

@app.post("/embed-image", response_model=ImageEmbedResponse)
async def embed_image(file: UploadFile = File(...)):
    """Generate embeddings for an image file"""
    from image_processor import normalize_search_image
    
    # Read image file
    image_bytes = await file.read()
    image = Image.open(io.BytesIO(image_bytes))
    
    # Normalize search image to match embedding style (white background, black icon)
    # This ensures real-world screenshots match indexed SVG embeddings
    image = normalize_search_image(image, target_size=224)
    
    # Generate embeddings using CLIP
    embeddings = image_model.encode(image, convert_to_numpy=True).tolist()
    
    return ImageEmbedResponse(embeddings=embeddings)

@app.post("/embed-svg", response_model=ImageEmbedResponse)
async def embed_svg(request: SVGEmbedRequest):
    """Generate embeddings for SVG content (converts SVG to image first)"""
    try:
        # Preprocess SVG: ensure it has proper fill and background for cairosvg
        # Many SVGs don't have explicit fill attributes and cairosvg renders them incorrectly
        import re
        svg_content = request.svg_content
        
        # Add white background rectangle first
        # Extract viewBox or create default
        viewbox_match = re.search(r'viewBox=["\']([^"\']+)["\']', svg_content)
        if viewbox_match:
            viewbox = viewbox_match.group(1)
            coords = viewbox.split()
            if len(coords) == 4:
                x, y, width, height = map(float, coords)
                # Insert white background rectangle after opening <svg> tag
                bg_rect = f'<rect x="{x}" y="{y}" width="{width}" height="{height}" fill="white"/>'
                svg_content = re.sub(r'(<svg[^>]*>)', r'\1' + bg_rect, svg_content, count=1)
        
        # Add fill="black" to all path elements that don't already have a fill attribute
        # This regex matches <path> tags with or without attributes
        def add_fill_to_path(match):
            full_match = match.group(0)
            # Check if fill already exists
            if 'fill=' not in full_match:
                # Add fill="black" - insert after <path and before any existing attributes
                if ' ' in full_match:
                    # Has attributes: <path attr1="val1" attr2="val2">
                    return full_match.replace('<path ', '<path fill="black" ', 1)
                else:
                    # No attributes: <path>
                    return full_match.replace('<path>', '<path fill="black">', 1)
            return full_match
        
        # Replace all <path> tags that don't have fill
        # Match <path> with optional whitespace and attributes
        svg_content = re.sub(r'<path\s*[^>]*>', add_fill_to_path, svg_content)
        
        # Convert SVG to PNG with background color
        # Use background_color parameter to ensure white background
        png_data = svg2png(
            bytestring=svg_content.encode('utf-8'),
            output_width=224,
            output_height=224,
            background_color='white'
        )
        
        if not png_data or len(png_data) == 0:
            raise ValueError("SVG to PNG conversion produced empty image")
        
        # Load PNG as PIL Image
        image = Image.open(io.BytesIO(png_data))
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Verify image is not empty
        if image.size[0] == 0 or image.size[1] == 0:
            raise ValueError("Converted image has zero dimensions")
        
        # Check if image is completely empty (all pixels are the same)
        # This is a basic check - if all pixels are the same color, it might indicate a conversion issue
        image_array = np.array(image)
        if image_array.size > 0:
            unique_colors = len(np.unique(image_array.reshape(-1, image_array.shape[-1]), axis=0))
            if unique_colors == 1:
                # All pixels are the same - might be a conversion issue, but not necessarily an error
                # Log a warning but continue
                print(f"Warning: Converted image has only one unique color (might indicate conversion issue)")
        
        # Generate embeddings using CLIP
        embeddings = image_model.encode(image, convert_to_numpy=True).tolist()
        
        if not embeddings or len(embeddings) == 0:
            raise ValueError("Embedding generation produced empty result")
        
        return ImageEmbedResponse(embeddings=embeddings)
    except Exception as e:
        raise ValueError(f"Error processing SVG: {str(e)}")
