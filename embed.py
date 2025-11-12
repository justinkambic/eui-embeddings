from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from typing import List, Optional, Literal, Union
import os
from elasticsearch import Elasticsearch
from PIL import Image
import io
import numpy as np
from cairosvg import svg2png
import base64
import binascii

app = FastAPI()
text_model = SentenceTransformer("all-MiniLM-L6-v2")
image_model = SentenceTransformer("clip-ViT-B-32")

# Initialize Elasticsearch client for ELSER inference and search
es_client = None
INDEX_NAME = "icons"
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

class SearchRequest(BaseModel):
    type: Literal["text", "image", "svg"]
    query: str  # text string, base64 image, or SVG code
    icon_type: Optional[Literal["icon", "token"]] = None
    fields: Optional[List[str]] = None

class SearchResult(BaseModel):
    icon_name: str
    score: float
    descriptions: Optional[List[str]] = None
    release_tag: Optional[str] = None
    icon_type: Optional[str] = None

class SearchResponse(BaseModel):
    results: List[SearchResult]
    total: Union[int, dict]

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

@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """Search for icons using text, image, or SVG"""
    if not es_client:
        raise HTTPException(status_code=500, detail="Elasticsearch client not configured. Set ELASTICSEARCH_ENDPOINT and ELASTICSEARCH_API_KEY")
    
    # Generate embeddings based on type
    embeddings = None
    sparse_embeddings = None
    
    if request.type == "text":
        # Generate text embeddings
        embeddings = text_model.encode(request.query, convert_to_numpy=True).tolist()
        
        # Generate ELSER sparse embeddings if ES client is available
        if es_client:
            try:
                inference_response = es_client.ml.infer_trained_model(
                    model_id=".elser_model_2",
                    body={
                        "docs": [{"text_field": request.query}]
                    }
                )
                
                if inference_response and len(inference_response.get("inference_results", [])) > 0:
                    tokens = inference_response["inference_results"][0].get("predicted_value", {})
                    sparse_embeddings = tokens
            except Exception as e:
                print(f"Warning: Could not generate ELSER embeddings: {e}")
    
    elif request.type == "image":
        # Decode base64 image
        try:
            image_bytes = base64.b64decode(request.query)
            image = Image.open(io.BytesIO(image_bytes))
            
            from image_processor import normalize_search_image
            image = normalize_search_image(image, target_size=224)
            embeddings = image_model.encode(image, convert_to_numpy=True).tolist()
        except (binascii.Error, ValueError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid base64 image data: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error processing image: {str(e)}")
    
    elif request.type == "svg":
        # Generate SVG embeddings (reuse embed_svg logic)
        try:
            import re
            svg_content = request.query
            
            # Add white background rectangle
            viewbox_match = re.search(r'viewBox=["\']([^"\']+)["\']', svg_content)
            if viewbox_match:
                viewbox = viewbox_match.group(1)
                coords = viewbox.split()
                if len(coords) == 4:
                    x, y, width, height = map(float, coords)
                    bg_rect = f'<rect x="{x}" y="{y}" width="{width}" height="{height}" fill="white"/>'
                    svg_content = re.sub(r'(<svg[^>]*>)', r'\1' + bg_rect, svg_content, count=1)
            
            # Add fill="black" to paths
            def add_fill_to_path(match):
                full_match = match.group(0)
                if 'fill=' not in full_match:
                    if ' ' in full_match:
                        return full_match.replace('<path ', '<path fill="black" ', 1)
                    else:
                        return full_match.replace('<path>', '<path fill="black">', 1)
                return full_match
            
            svg_content = re.sub(r'<path\s*[^>]*>', add_fill_to_path, svg_content)
            
            # Convert SVG to PNG
            png_data = svg2png(
                bytestring=svg_content.encode('utf-8'),
                output_width=224,
                output_height=224,
                background_color='white'
            )
            
            if not png_data or len(png_data) == 0:
                raise ValueError("SVG to PNG conversion produced empty image")
            
            image = Image.open(io.BytesIO(png_data))
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            embeddings = image_model.encode(image, convert_to_numpy=True).tolist()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error processing SVG: {str(e)}")
    
    if embeddings is None:
        raise HTTPException(status_code=500, detail="Failed to generate embeddings")
    
    # Build filter for icon_type if provided
    icon_type_filter = None
    if request.icon_type:
        icon_type_filter = {
            "term": {
                "icon_type": request.icon_type
            }
        }
    
    # Build search query
    search_body = {
        "size": 50
    }
    
    # For text searches, use hybrid search (dense + sparse)
    if request.type == "text" and sparse_embeddings:
        # Hybrid search: combine knn with text_expansion
        bool_query = {
            "should": [
                {
                    "text_expansion": {
                        "text_embedding_sparse": {
                            "model_text": request.query,
                            "model_id": ".elser_model_2"
                        }
                    }
                }
            ]
        }
        
        if icon_type_filter:
            bool_query["filter"] = [icon_type_filter]
        
        search_body["query"] = {
            "bool": bool_query
        }
        
        search_body["knn"] = {
            "field": "text_embedding",
            "query_vector": embeddings,
            "k": 10,
            "num_candidates": 100
        }
        
        if icon_type_filter:
            search_body["knn"]["filter"] = [icon_type_filter]
    
    elif request.type == "image" or request.type == "svg":
        # Image/SVG searches: use fields parameter if provided
        valid_fields = [
            "icon_image_embedding",
            "icon_svg_embedding",
            "token_image_embedding",
            "token_svg_embedding"
        ]
        
        # Determine which fields to search
        fields_to_search = []
        
        if request.fields and len(request.fields) > 0:
            # Use explicitly provided fields (filter to only valid ones)
            fields_to_search = [f for f in request.fields if f in valid_fields]
        else:
            # Fall back to icon_type logic for backward compatibility
            if request.icon_type == "icon":
                fields_to_search = ["icon_image_embedding", "icon_svg_embedding"]
            elif request.icon_type == "token":
                fields_to_search = ["token_image_embedding", "token_svg_embedding"]
            else:
                # Default: search all fields
                fields_to_search = valid_fields
        
        # If no valid fields, default to all fields
        if len(fields_to_search) == 0:
            fields_to_search = valid_fields
        
        # If only one field, use a single KNN query
        if len(fields_to_search) == 1:
            search_body["knn"] = {
                "field": fields_to_search[0],
                "query_vector": embeddings,
                "k": 10,
                "num_candidates": 100
            }
        else:
            # Build KNN queries for each selected field
            knn_queries = []
            for field in fields_to_search:
                knn_queries.append({
                    "field": field,
                    "query_vector": embeddings,
                    "k": 10,
                    "num_candidates": 100
                })
            search_body["knn"] = knn_queries
    
    else:
        # Fallback: text search without sparse embeddings
        search_body["knn"] = {
            "field": "text_embedding",
            "query_vector": embeddings,
            "k": 10,
            "num_candidates": 100
        }
        if icon_type_filter:
            search_body["knn"]["filter"] = [icon_type_filter]
    
    # Execute search
    try:
        search_response = es_client.search(
            index=INDEX_NAME,
            body=search_body
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Elasticsearch search failed: {str(e)}")
    
    # Format results
    hits = search_response.get("hits", {})
    total = hits.get("total", 0)
    hits_list = hits.get("hits", [])
    
    results = []
    for hit in hits_list:
        source = hit.get("_source", {})
        results.append(SearchResult(
            icon_name=source.get("icon_name") or hit.get("_id", ""),
            score=hit.get("_score", 0.0),
            descriptions=source.get("descriptions"),
            release_tag=source.get("release_tag"),
            icon_type=source.get("icon_type")
        ))
    
    return SearchResponse(
        results=results,
        total=total
    )
