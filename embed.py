from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response as FastAPIResponse
from starlette.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
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
import json
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import multiprocessing
import time

# Initialize OpenTelemetry before FastAPI app creation
from otel_config import initialize_instrumentation, instrument_fastapi, tracer, meter
from opentelemetry import trace

# Initialize OpenTelemetry instrumentation
initialize_instrumentation()

# Set multiprocessing start method early to avoid issues with sentence-transformers
# This must be done before any models are loaded (sentence-transformers uses multiprocessing)
# On macOS, 'fork' can cause semaphore leaks, so we use 'spawn' instead
try:
    current_method = multiprocessing.get_start_method(allow_none=True)
    if current_method is None:
        multiprocessing.set_start_method('spawn')
    elif current_method == 'fork':
        # Force to spawn if currently fork (macOS default can cause issues)
        multiprocessing.set_start_method('spawn', force=True)
except RuntimeError:
    # Already set or can't be changed, ignore
    pass

app = FastAPI()

# Instrument FastAPI after app creation
instrument_fastapi(app)

# Environment variable configuration
PYTHON_API_HOST = os.getenv("PYTHON_API_HOST", "0.0.0.0")
PYTHON_API_PORT = int(os.getenv("PORT", os.getenv("PYTHON_API_PORT", "8000")))
PYTHON_API_BASE_URL = os.getenv("PYTHON_API_BASE_URL", "")

# CORS configuration
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
if CORS_ORIGINS == "*":
    cors_origins = ["*"]
else:
    cors_origins = [origin.strip() for origin in CORS_ORIGINS.split(",")]

# Security headers middleware for HTTPS
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        # HSTS header - only add if using HTTPS
        # Check via base URL, request scheme, or X-Forwarded-Proto header (from load balancer)
        is_https = (
            PYTHON_API_BASE_URL.startswith("https://") or
            request.url.scheme == "https" or
            request.headers.get("X-Forwarded-Proto") == "https"
        )
        if is_https:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        # Content Security Policy - adjust as needed for your use case
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        # Add rate limit headers manually (since headers_enabled=False in slowapi)
        # Extract rate limit info from request.state (set by slowapi middleware)
        try:
            # Get rate limit info from request state (set by slowapi)
            rate_limit_info = getattr(request.state, 'view_rate_limit', None)
            
            if rate_limit_info:
                # Extract limit from rate limit info
                # slowapi stores limit info in request.state.view_rate_limit
                try:
                    # Try to get limit from the rate limit info object
                    limit_value = getattr(rate_limit_info, 'limit', None)
                    if limit_value:
                        # Parse limit string (e.g., "30 per 1 minute" -> 30)
                        if isinstance(limit_value, str):
                            limit_parts = limit_value.split()
                            limit_int = int(limit_parts[0]) if limit_parts else 60
                        else:
                            limit_int = int(limit_value)
                    else:
                        limit_int = 60  # Default
                    
                    response.headers["X-RateLimit-Limit"] = str(limit_int)
                    
                    # Get remaining count
                    remaining = getattr(rate_limit_info, 'remaining', limit_int - 1)
                    if remaining is None:
                        remaining = limit_int - 1
                    response.headers["X-RateLimit-Remaining"] = str(max(0, int(remaining)))
                    
                    # Get reset time
                    reset_at = getattr(rate_limit_info, 'reset_at', None)
                    if reset_at:
                        reset_time = int(reset_at) if isinstance(reset_at, (int, float)) else int(time.time()) + 60
                    else:
                        reset_time = int(time.time()) + 60
                    response.headers["X-RateLimit-Reset"] = str(reset_time)
                except (AttributeError, ValueError, TypeError) as e:
                    # Fallback to default values if parsing fails
                    response.headers["X-RateLimit-Limit"] = "60"
                    response.headers["X-RateLimit-Remaining"] = "59"
                    response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 60)
            else:
                # No rate limit info available - check if this is a rate-limited endpoint
                # For endpoints without rate limiting (like /health), don't add headers
                path = request.url.path
                if path not in ["/health", "/docs", "/openapi.json", "/redoc"]:
                    # Add default headers for rate-limited endpoints
                    response.headers["X-RateLimit-Limit"] = "60"
                    response.headers["X-RateLimit-Remaining"] = "59"
                    response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 60)
        except Exception as e:
            # Don't break the response if header processing fails
            # In production, you might want to log this error
            pass
        
        return response

# Add security headers middleware (before CORS)
app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Key authentication configuration
API_KEY_HEADER = os.getenv("API_KEY_HEADER", "X-API-Key")
API_KEYS_SECRET_NAME = os.getenv("API_KEYS_SECRET_NAME", "")
API_KEYS_ENV = os.getenv("API_KEYS", "")

# Load API keys from environment or Secret Manager
_valid_api_keys = set()

def load_api_keys():
    """Load API keys from environment variable or Secret Manager"""
    global _valid_api_keys
    
    # Try environment variable first (for local development)
    if API_KEYS_ENV:
        keys = [key.strip() for key in API_KEYS_ENV.split(",") if key.strip()]
        _valid_api_keys.update(keys)
    
    # Try Secret Manager if configured (for production)
    if API_KEYS_SECRET_NAME:
        try:
            # Try to import Google Cloud Secret Manager
            from google.cloud import secretmanager
            
            client = secretmanager.SecretManagerServiceClient()
            project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "")
            if not project_id:
                # Try to get project ID from metadata server
                try:
                    import requests
                    metadata_url = "http://metadata.google.internal/computeMetadata/v1/project/project-id"
                    headers = {"Metadata-Flavor": "Google"}
                    response = requests.get(metadata_url, headers=headers, timeout=2)
                    if response.status_code == 200:
                        project_id = response.text
                except:
                    pass
            
            if project_id:
                secret_name = f"projects/{project_id}/secrets/{API_KEYS_SECRET_NAME}/versions/latest"
                response = client.access_secret_version(request={"name": secret_name})
                keys_json = response.payload.data.decode("UTF-8")
                keys = json.loads(keys_json)
                if isinstance(keys, list):
                    _valid_api_keys.update(keys)
        except ImportError:
            # google-cloud-secret-manager not installed, skip
            pass
        except Exception as e:
            print(f"Warning: Could not load API keys from Secret Manager: {e}")

# Load API keys on startup
load_api_keys()

# Rate limiting configuration (after API keys are loaded)
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
RATE_LIMIT_PER_HOUR = int(os.getenv("RATE_LIMIT_PER_HOUR", "1000"))
RATE_LIMIT_BURST = int(os.getenv("RATE_LIMIT_BURST", "10"))

def get_rate_limit_key(request: Request) -> str:
    """Get rate limit key - use API key if available, otherwise use IP address"""
    # Try to get API key first (for per-key rate limiting)
    # Note: API_KEY_HEADER is defined above, so this is safe
    api_key = request.headers.get(API_KEY_HEADER, "")
    if api_key and api_key in _valid_api_keys:
        return f"api_key:{api_key}"
    # Fall back to IP address
    return get_remote_address(request)

# Initialize rate limiter
# Use in-memory storage (sufficient for low traffic)
# Track by API key (if available) or IP address
# headers_enabled=True ensures rate limit headers are added to responses
# Note: slowapi adds headers, but they may not always include Remaining/Reset
# We'll ensure headers are complete via middleware if needed
limiter = Limiter(key_func=get_rate_limit_key, headers_enabled=False, auto_check=True)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add SlowAPI middleware to handle rate limiting and headers
# This must be added AFTER app.state.limiter is set
# Note: Middleware executes in reverse order (last added runs first)
# So this will run before SecurityHeadersMiddleware, allowing rate limit headers to be added first
app.add_middleware(SlowAPIMiddleware)

async def verify_api_key(request: Request):
    """Dependency to verify API key"""
    if not _valid_api_keys:
        # No API keys configured, allow all requests (for backward compatibility)
        return True
    
    api_key = request.headers.get(API_KEY_HEADER)
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")
    
    if api_key not in _valid_api_keys:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return True

# Initialize models with OpenTelemetry instrumentation
with tracer.start_as_current_span("model_loading") as span:
    span.set_attribute("model.name", "all-MiniLM-L6-v2")
    span.set_attribute("model.type", "text")
    start_time = time.time()
    text_model = SentenceTransformer("all-MiniLM-L6-v2")
    load_time = time.time() - start_time
    span.set_attribute("model.load_time_seconds", load_time)
    span.set_attribute("model.embedding_dimension", len(text_model.encode("test")))

with tracer.start_as_current_span("model_loading") as span:
    span.set_attribute("model.name", "clip-ViT-B-32")
    span.set_attribute("model.type", "image")
    start_time = time.time()
    image_model = SentenceTransformer("clip-ViT-B-32")
    load_time = time.time() - start_time
    span.set_attribute("model.load_time_seconds", load_time)
    span.set_attribute("model.embedding_dimension", len(image_model.encode(Image.new('RGB', (224, 224), color='white'))))

# Initialize Elasticsearch client with configurable settings
es_client = None
INDEX_NAME = "icons"
es_endpoint = os.getenv("ELASTICSEARCH_ENDPOINT")
es_api_key = os.getenv("ELASTICSEARCH_API_KEY")
es_timeout = int(os.getenv("ELASTICSEARCH_TIMEOUT", "30"))
es_max_retries = int(os.getenv("ELASTICSEARCH_MAX_RETRIES", "3"))

if es_endpoint and es_api_key:
    es_client = Elasticsearch(
        [es_endpoint],
        api_key=es_api_key,
        request_timeout=es_timeout,
        max_retries=es_max_retries,
        retry_on_timeout=True
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

@app.get("/health")
async def health_check():
    """Health check endpoint (no authentication required)"""
    health_status = {
        "status": "healthy",
        "service": "eui-icon-embeddings",
        "elasticsearch": "connected" if es_client else "not_configured"
    }
    if es_client:
        try:
            # Test Elasticsearch connection
            es_client.ping()
            health_status["elasticsearch"] = "connected"
        except Exception as e:
            health_status["elasticsearch"] = f"error: {str(e)}"
    return health_status

@app.post("/embed", response_model=EmbedResponse, dependencies=[Depends(verify_api_key)])
@limiter.limit(f"{RATE_LIMIT_PER_MINUTE}/minute")
@limiter.limit(f"{RATE_LIMIT_PER_HOUR}/hour")
async def embed_text(request: Request, embed_request: EmbedRequest):
    with tracer.start_as_current_span("embed_text") as span:
        span.set_attribute("embedding.type", "text")
        span.set_attribute("embedding.content_length", len(embed_request.content))
        
        # Generate dense embeddings
        encode_start = time.time()
        embeddings = text_model.encode(embed_request.content, convert_to_numpy=True).tolist()
        encode_time = time.time() - encode_start
        
        span.set_attribute("embedding.dimension", len(embeddings))
        span.set_attribute("embedding.encode_time_seconds", encode_time)
        
        # Generate ELSER sparse embeddings if ES client is available
        sparse_embeddings = None
        if es_client:
            try:
                with tracer.start_as_current_span("elser_inference") as elser_span:
                    elser_span.set_attribute("model.id", ".elser_model_2")
                    inference_start = time.time()
                    # Use Elasticsearch inference API for ELSER
                    inference_response = es_client.ml.infer_trained_model(
                        model_id=".elser_model_2",
                        body={
                            "docs": [{"text_field": embed_request.content}]
                        }
                    )
                    inference_time = time.time() - inference_start
                    elser_span.set_attribute("inference.time_seconds", inference_time)
                    
                    # Extract sparse vector from response
                    if inference_response and len(inference_response.get("inference_results", [])) > 0:
                        tokens = inference_response["inference_results"][0].get("predicted_value", {})
                        sparse_embeddings = tokens
                        elser_span.set_attribute("sparse_embedding.token_count", len(tokens))
            except Exception as e:
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                # ELSER not available or error - continue without sparse embeddings
                print(f"Warning: Could not generate ELSER embeddings: {e}")
        
        return EmbedResponse(
            embeddings=embeddings,
            sparse_embeddings=sparse_embeddings
        )

@app.post("/embed-image", response_model=ImageEmbedResponse, dependencies=[Depends(verify_api_key)])
@limiter.limit(f"{RATE_LIMIT_PER_MINUTE}/minute")
@limiter.limit(f"{RATE_LIMIT_PER_HOUR}/hour")
async def embed_image(request: Request, file: UploadFile = File(...)):
    """Generate embeddings for an image file"""
    with tracer.start_as_current_span("embed_image") as span:
        span.set_attribute("embedding.type", "image")
        span.set_attribute("file.content_type", file.content_type or "unknown")
        
        from image_processor import normalize_search_image
        
        # Read image file
        image_bytes = await file.read()
        span.set_attribute("file.size_bytes", len(image_bytes))
        
        try:
            image = Image.open(io.BytesIO(image_bytes))
        except Exception as e:
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            raise HTTPException(status_code=400, detail=f"Invalid image file: {str(e)}")
        
        span.set_attribute("image.width", image.size[0])
        span.set_attribute("image.height", image.size[1])
        span.set_attribute("image.mode", image.mode)
        
        # Normalize search image to match embedding style (white background, black icon)
        # This ensures real-world screenshots match indexed SVG embeddings
        image = normalize_search_image(image, target_size=224)
        
        # Generate embeddings using CLIP
        encode_start = time.time()
        embeddings = image_model.encode(image, convert_to_numpy=True).tolist()
        encode_time = time.time() - encode_start
        
        span.set_attribute("embedding.dimension", len(embeddings))
        span.set_attribute("embedding.encode_time_seconds", encode_time)
        
        return ImageEmbedResponse(embeddings=embeddings)

@app.post("/embed-svg", response_model=ImageEmbedResponse, dependencies=[Depends(verify_api_key)])
@limiter.limit(f"{RATE_LIMIT_PER_MINUTE}/minute")
@limiter.limit(f"{RATE_LIMIT_PER_HOUR}/hour")
async def embed_svg(request: Request, svg_request: SVGEmbedRequest):
    """Generate embeddings for SVG content (converts SVG to image first)"""
    with tracer.start_as_current_span("embed_svg") as span:
        span.set_attribute("embedding.type", "svg")
        span.set_attribute("svg.content_length", len(svg_request.svg_content))
        
        # Validate SVG content is not empty
        if not svg_request.svg_content or not svg_request.svg_content.strip():
            raise HTTPException(status_code=422, detail="SVG content cannot be empty")
        
        try:
            # Preprocess SVG: ensure it has proper fill and background for cairosvg
            # Many SVGs don't have explicit fill attributes and cairosvg renders them incorrectly
            import re
            svg_content = svg_request.svg_content
            
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
            encode_start = time.time()
            embeddings = image_model.encode(image, convert_to_numpy=True).tolist()
            encode_time = time.time() - encode_start
            
            if not embeddings or len(embeddings) == 0:
                raise ValueError("Embedding generation produced empty result")
            
            span.set_attribute("embedding.dimension", len(embeddings))
            span.set_attribute("embedding.encode_time_seconds", encode_time)
            span.set_attribute("image.final_width", image.size[0])
            span.set_attribute("image.final_height", image.size[1])
            
            return ImageEmbedResponse(embeddings=embeddings)
        except Exception as e:
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            raise ValueError(f"Error processing SVG: {str(e)}")

@app.post("/search", response_model=SearchResponse, dependencies=[Depends(verify_api_key)])
@limiter.limit("30/minute")  # Stricter limit for search endpoint
@limiter.limit("500/hour")
async def search(request: Request, search_request: SearchRequest):
    """Search for icons using text, image, or SVG"""
    with tracer.start_as_current_span("search") as span:
        span.set_attribute("search.type", search_request.type)
        span.set_attribute("search.has_icon_type_filter", search_request.icon_type is not None)
        if search_request.icon_type:
            span.set_attribute("search.icon_type", search_request.icon_type)
        if search_request.fields:
            span.set_attribute("search.fields", ",".join(search_request.fields))
        
        if not es_client:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Elasticsearch not configured"))
            raise HTTPException(status_code=500, detail="Elasticsearch client not configured. Set ELASTICSEARCH_ENDPOINT and ELASTICSEARCH_API_KEY")
        
        # Generate embeddings based on type
        embeddings = None
        sparse_embeddings = None
        
        if search_request.type == "text":
            # Generate text embeddings
            with tracer.start_as_current_span("generate_text_embeddings") as embed_span:
                embed_span.set_attribute("query.length", len(search_request.query))
                encode_start = time.time()
                embeddings = text_model.encode(search_request.query, convert_to_numpy=True).tolist()
                encode_time = time.time() - encode_start
                embed_span.set_attribute("embedding.dimension", len(embeddings))
                embed_span.set_attribute("embedding.encode_time_seconds", encode_time)
            
            # Generate ELSER sparse embeddings if ES client is available
            if es_client:
                try:
                    with tracer.start_as_current_span("elser_inference") as elser_span:
                        elser_span.set_attribute("model.id", ".elser_model_2")
                        inference_start = time.time()
                        inference_response = es_client.ml.infer_trained_model(
                            model_id=".elser_model_2",
                            body={
                                "docs": [{"text_field": search_request.query}]
                            }
                        )
                        inference_time = time.time() - inference_start
                        elser_span.set_attribute("inference.time_seconds", inference_time)
                        
                        if inference_response and len(inference_response.get("inference_results", [])) > 0:
                            tokens = inference_response["inference_results"][0].get("predicted_value", {})
                            sparse_embeddings = tokens
                            elser_span.set_attribute("sparse_embedding.token_count", len(tokens))
                except Exception as e:
                    span.record_exception(e)
                    print(f"Warning: Could not generate ELSER embeddings: {e}")
        
        elif search_request.type == "image":
            # Decode base64 image
            with tracer.start_as_current_span("generate_image_embeddings") as embed_span:
                try:
                    image_bytes = base64.b64decode(search_request.query)
                    embed_span.set_attribute("image.size_bytes", len(image_bytes))
                    
                    image = Image.open(io.BytesIO(image_bytes))
                    embed_span.set_attribute("image.original_width", image.size[0])
                    embed_span.set_attribute("image.original_height", image.size[1])
                    embed_span.set_attribute("image.mode", image.mode)
                    
                    from image_processor import normalize_search_image
                    image = normalize_search_image(image, target_size=224)
                    
                    encode_start = time.time()
                    embeddings = image_model.encode(image, convert_to_numpy=True).tolist()
                    encode_time = time.time() - encode_start
                    embed_span.set_attribute("embedding.dimension", len(embeddings))
                    embed_span.set_attribute("embedding.encode_time_seconds", encode_time)
                except (binascii.Error, ValueError) as e:
                    embed_span.record_exception(e)
                    embed_span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    raise HTTPException(status_code=400, detail=f"Invalid base64 image data: {str(e)}")
                except Exception as e:
                    embed_span.record_exception(e)
                    embed_span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    raise HTTPException(status_code=400, detail=f"Error processing image: {str(e)}")
        
        elif search_request.type == "svg":
            # Generate SVG embeddings (reuse embed_svg logic)
            with tracer.start_as_current_span("generate_svg_embeddings") as embed_span:
                try:
                    import re
                    svg_content = search_request.query
                    embed_span.set_attribute("svg.content_length", len(svg_content))
                    
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
                    
                    encode_start = time.time()
                    embeddings = image_model.encode(image, convert_to_numpy=True).tolist()
                    encode_time = time.time() - encode_start
                    embed_span.set_attribute("embedding.dimension", len(embeddings))
                    embed_span.set_attribute("embedding.encode_time_seconds", encode_time)
                except Exception as e:
                    embed_span.record_exception(e)
                    embed_span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    raise HTTPException(status_code=400, detail=f"Error processing SVG: {str(e)}")
        
        if embeddings is None:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Failed to generate embeddings"))
            raise HTTPException(status_code=500, detail="Failed to generate embeddings")
        
        # Build filter for icon_type if provided
        icon_type_filter = None
        if search_request.icon_type:
            icon_type_filter = {
                "term": {
                    "icon_type": search_request.icon_type
                }
            }
        
        # Build search query
        search_body = {
            "size": 50
        }
        
        # For text searches, use hybrid search (dense + sparse)
        if search_request.type == "text" and sparse_embeddings:
            # Hybrid search: combine knn with text_expansion
            bool_query = {
                "should": [
                    {
                        "text_expansion": {
                            "text_embedding_sparse": {
                                "model_text": search_request.query,
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
        
        elif search_request.type == "image" or search_request.type == "svg":
            # Image/SVG searches: use fields parameter if provided
            valid_fields = [
                "icon_image_embedding",
                "icon_svg_embedding",
                "token_image_embedding",
                "token_svg_embedding"
            ]
            
            # Determine which fields to search
            fields_to_search = []
            
            if search_request.fields and len(search_request.fields) > 0:
                # Use explicitly provided fields (filter to only valid ones)
                fields_to_search = [f for f in search_request.fields if f in valid_fields]
            else:
                # Fall back to icon_type logic for backward compatibility
                if search_request.icon_type == "icon":
                    fields_to_search = ["icon_image_embedding", "icon_svg_embedding"]
                elif search_request.icon_type == "token":
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
        with tracer.start_as_current_span("elasticsearch_search") as es_span:
            es_span.set_attribute("elasticsearch.index", INDEX_NAME)
            # Extract query type for attribute
            query_type = "unknown"
            if "knn" in search_body:
                query_type = "knn"
            elif "query" in search_body:
                query_type = "query"
            es_span.set_attribute("elasticsearch.query_type", query_type)
            
            try:
                search_start = time.time()
                search_response = es_client.search(
                    index=INDEX_NAME,
                    body=search_body
                )
                search_time = time.time() - search_start
                es_span.set_attribute("elasticsearch.search_time_seconds", search_time)
                
                # Extract result count
                hits = search_response.get("hits", {})
                total = hits.get("total", 0)
                if isinstance(total, dict):
                    total_count = total.get("value", 0)
                else:
                    total_count = total
                es_span.set_attribute("elasticsearch.total_hits", total_count)
                span.set_attribute("search.result_count", total_count)
                
                # Format results
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
                
                span.set_attribute("search.results_returned", len(results))
                return SearchResponse(
                    results=results,
                    total=total
                )
            except Exception as e:
                es_span.record_exception(e)
                es_span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                raise HTTPException(status_code=500, detail=f"Elasticsearch search failed: {str(e)}")

# Start the server if run directly
if __name__ == "__main__":
    import uvicorn
    
    print(f"Starting EUI Icon Embeddings API server on {PYTHON_API_HOST}:{PYTHON_API_PORT}")
    print(f"API keys configured: {len(_valid_api_keys)} key(s)")
    print(f"Elasticsearch: {'configured' if es_client else 'not configured'}")
    print(f"Health check: http://{PYTHON_API_HOST}:{PYTHON_API_PORT}/health")
    print(f"API docs: http://{PYTHON_API_HOST}:{PYTHON_API_PORT}/docs")
    
    # Run uvicorn - use reload=False when running directly to avoid multiprocessing issues
    uvicorn.run(
        app, 
        host=PYTHON_API_HOST, 
        port=PYTHON_API_PORT,
        log_level="info"
    )
