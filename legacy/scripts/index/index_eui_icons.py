#!/usr/bin/env python3
"""
Automated EUI Icon Indexing Script

Automates the process of cloning the EUI repository, extracting icon mappings,
and indexing both icon and tokenized icon embeddings with version tracking.

Usage:
    python scripts/index/index_eui_icons.py [--index] [--limit N] [--force] [--skip-tokens]

Examples:
    # Dry run (no indexing)
    python scripts/index/index_eui_icons.py

    # Index all icons
    python scripts/index/index_eui_icons.py --index

    # Index first 10 icons only (for testing)
    python scripts/index/index_eui_icons.py --index --limit 10

    # Force re-indexing even if version already processed
    python scripts/index/index_eui_icons.py --index --force

    # Skip token rendering (index only icons)
    python scripts/index/index_eui_icons.py --index --skip-tokens
"""

import os
import sys
import json
import re
import subprocess
import argparse
import io
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import requests
from elasticsearch import Elasticsearch
from PIL import Image

# Configuration
EMBEDDING_SERVICE_URL = os.getenv("EMBEDDING_SERVICE_URL", "http://localhost:8000")
TOKEN_RENDERER_URL = os.getenv("TOKEN_RENDERER_URL", "http://localhost:3002/render-token")
INDEX_NAME = "icons"
VERSION_FILE = "data/processed_version.txt"
EUI_LOCATION = os.getenv("EUI_LOCATION", "./data/eui")
EUI_REPO = os.getenv("EUI_REPO", "https://github.com/elastic/eui.git")
ICON_MAP_PATH = "packages/eui/src/components/icon/icon_map.ts"
# SVG files can be anywhere in the repository, we'll search recursively


def get_elasticsearch_client() -> Optional[Elasticsearch]:
    """Initialize Elasticsearch client if environment variables are set"""
    endpoint = os.getenv("ELASTICSEARCH_ENDPOINT")
    api_key = os.getenv("ELASTICSEARCH_API_KEY")
    
    if endpoint and api_key:
        return Elasticsearch(
            [endpoint],
            api_key=api_key,
            request_timeout=30
        )
    return None


def ensure_directory(path: str) -> None:
    """Create directory if it doesn't exist"""
    Path(path).mkdir(parents=True, exist_ok=True)


def clone_repository(repo_url: str, target_dir: str) -> bool:
    """Clone git repository if it doesn't exist"""
    if os.path.exists(os.path.join(target_dir, ".git")):
        print(f"✓ Repository already exists at {target_dir}")
        return True
    
    print(f"Cloning repository {repo_url} to {target_dir}...")
    try:
        subprocess.run(
            ["git", "clone", repo_url, target_dir],
            check=True,
            capture_output=True,
            text=True
        )
        print(f"✓ Successfully cloned repository")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Error cloning repository: {e.stderr}")
        return False


def fetch_tags(repo_dir: str) -> bool:
    """Fetch latest tags from remote"""
    print("Fetching latest tags...")
    try:
        subprocess.run(
            ["git", "fetch", "--tags"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
            text=True
        )
        print("✓ Tags fetched")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Error fetching tags: {e.stderr}")
        return False


def get_latest_major_release_tag(repo_dir: str) -> Optional[str]:
    """Get the latest major release tag (e.g., v109.0.0)"""
    try:
        result = subprocess.run(
            ["git", "tag", "-l", "v*.0.0"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=True
        )
        
        tags = [tag.strip() for tag in result.stdout.strip().split("\n") if tag.strip()]
        if not tags:
            return None
        
        # Sort tags by version number (descending)
        def version_key(tag: str) -> Tuple[int, ...]:
            # Extract version numbers from tag (e.g., "v109.0.0" -> (109, 0, 0))
            match = re.match(r"v(\d+)\.(\d+)\.(\d+)", tag)
            if match:
                return tuple(map(int, match.groups()))
            return (0, 0, 0)
        
        tags.sort(key=version_key, reverse=True)
        latest_tag = tags[0]
        print(f"✓ Latest major release tag: {latest_tag}")
        return latest_tag
    except subprocess.CalledProcessError as e:
        print(f"✗ Error getting tags: {e.stderr}")
        return None


def checkout_tag(repo_dir: str, tag: str) -> bool:
    """Checkout a specific git tag"""
    print(f"Checking out tag {tag}...")
    try:
        subprocess.run(
            ["git", "checkout", tag],
            cwd=repo_dir,
            check=True,
            capture_output=True,
            text=True
        )
        print(f"✓ Checked out tag {tag}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Error checking out tag: {e.stderr}")
        return False


def read_processed_version() -> Optional[str]:
    """Read the last processed version from file"""
    if not os.path.exists(VERSION_FILE):
        return None
    
    try:
        with open(VERSION_FILE, 'r', encoding='utf-8') as f:
            version = f.read().strip()
            return version if version else None
    except Exception as e:
        print(f"⚠ Warning: Could not read version file: {e}")
        return None


def write_processed_version(version: str) -> None:
    """Write processed version to file"""
    ensure_directory(os.path.dirname(VERSION_FILE))
    try:
        with open(VERSION_FILE, 'w', encoding='utf-8') as f:
            f.write(version)
        print(f"✓ Wrote processed version to {VERSION_FILE}")
    except Exception as e:
        print(f"⚠ Warning: Could not write version file: {e}")


def check_all_icons_indexed(
    es_client: Elasticsearch,
    matched_icons: List[Tuple[str, str, str]],
    release_tag: str,
    skip_tokens: bool
) -> bool:
    """
    Check if all icons for a version are indexed.
    
    Returns True if all icons (with all embeddings) are indexed, False otherwise.
    """
    if not es_client:
        return False
    
    try:
        for svg_file, icon_name, filename in matched_icons:
            # Check icon document (now contains all embeddings)
            doc_id = f"{icon_name}_{release_tag}"
            if not es_client.exists(index=INDEX_NAME, id=doc_id):
                return False
            
            # Check if document has at least icon embeddings (icon_image_embedding and icon_svg_embedding)
            try:
                doc = es_client.get(index=INDEX_NAME, id=doc_id)
                source = doc.get("_source", {})
                
                # Must have at least icon embeddings
                if "icon_image_embedding" not in source or "icon_svg_embedding" not in source:
                    return False
                
                # If tokens are not skipped, check for token embeddings
                if not skip_tokens:
                    if "token_image_embedding" not in source or "token_svg_embedding" not in source:
                        return False
                
                # Verify it's the correct version
                if source.get("release_tag") != release_tag:
                    return False
            except Exception:
                return False
        
        return True
    except Exception as e:
        print(f"⚠ Warning: Error checking indexed icons: {e}")
        return False


def extract_type_to_path_map(icon_map_path: str) -> Dict[str, str]:
    """
    Extract typeToPathMap from TypeScript file.
    
    Handles TypeScript syntax like:
    export const typeToPathMap = {
      iconName: 'filename',
      ...
    };
    """
    if not os.path.exists(icon_map_path):
        print(f"✗ Icon map file not found: {icon_map_path}")
        return {}
    
    print(f"Extracting typeToPathMap from {icon_map_path}...")
    
    try:
        with open(icon_map_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the typeToPathMap object
        # Match: export const typeToPathMap = { ... };
        pattern = r'export\s+const\s+typeToPathMap\s*=\s*\{([^}]+)\}'
        match = re.search(pattern, content, re.DOTALL)
        
        if not match:
            print("✗ Could not find typeToPathMap in file")
            return {}
        
        object_content = match.group(1)
        
        # Extract key-value pairs
        # Match: key: 'value', or key: "value",
        mapping = {}
        pattern = r'(\w+):\s*["\']([^"\']+)["\']'
        for match in re.finditer(pattern, object_content):
            key = match.group(1)
            value = match.group(2)
            mapping[key] = value
        
        print(f"✓ Extracted {len(mapping)} icon mappings")
        return mapping
    except Exception as e:
        print(f"✗ Error extracting typeToPathMap: {e}")
        return {}


def create_filename_to_icon_name_map(type_to_path_map: Dict[str, str]) -> Dict[str, str]:
    """Create reverse mapping: filename -> icon_name"""
    filename_to_icon = {}
    for icon_name, filename in type_to_path_map.items():
        filename_to_icon[filename] = icon_name
    return filename_to_icon


def find_svg_files(repo_dir: str) -> List[str]:
    """Find all SVG files recursively in the repository"""
    if not os.path.exists(repo_dir):
        print(f"✗ Repository directory not found: {repo_dir}")
        return []
    
    svg_files = []
    # Exclude common directories that shouldn't be searched
    exclude_dirs = {'.git', 'node_modules', 'dist', 'build', '__pycache__', '.next'}
    
    for root, dirs, files in os.walk(repo_dir):
        # Filter out excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            if file.endswith('.svg'):
                svg_files.append(os.path.join(root, file))
    
    print(f"✓ Found {len(svg_files)} SVG files in repository")
    return svg_files


def get_filename_from_path(file_path: str) -> str:
    """Extract filename without extension from path"""
    return os.path.splitext(os.path.basename(file_path))[0]


def read_svg_file(file_path: str) -> str:
    """Read SVG file content"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def generate_embedding(svg_content: str, service_url: str = None) -> Optional[List[float]]:
    """Generate embedding for SVG content"""
    if service_url is None:
        service_url = EMBEDDING_SERVICE_URL
    
    # Use /embed-svg endpoint
    embed_url = f"{service_url.rstrip('/')}/embed-svg"
    
    try:
        response = requests.post(
            embed_url,
            json={"svg_content": svg_content},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        return data.get("embeddings")
    except requests.exceptions.RequestException as e:
        print(f"  ✗ Error generating embedding: {e}")
        return None


def generate_embedding_from_image(image_bytes: bytes, service_url: str = None) -> Optional[List[float]]:
    """Generate embedding for image bytes using /embed-image endpoint"""
    import io
    
    if service_url is None:
        service_url = EMBEDDING_SERVICE_URL
    
    # Use /embed-image endpoint which expects multipart form data
    embed_url = f"{service_url.rstrip('/')}/embed-image"
    
    try:
        # Create a file-like object from bytes
        files = {'file': ('token.png', io.BytesIO(image_bytes), 'image/png')}
        response = requests.post(
            embed_url,
            files=files,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        return data.get("embeddings")
    except requests.exceptions.RequestException as e:
        print(f"  ✗ Error generating embedding from image: {e}")
        return None


def render_icon_image(icon_name: str, component_type: str, service_url: str = None, size: str = None) -> Optional[bytes]:
    """Render EuiIcon or EuiToken to base64 PNG image using icon renderer service
    Returns decoded image bytes (not base64 string)
    
    Args:
        icon_name: Icon name to render
        component_type: 'icon' for EuiIcon or 'token' for EuiToken (required)
        service_url: Renderer service base URL (default: derived from TOKEN_RENDERER_URL)
                     If provided, should be base URL like http://localhost:3002, not full endpoint
        size: Icon/token size (e.g., 's', 'm', 'l', 'xl', 'xxl'). If None, uses service default.
    """
    if component_type not in ('icon', 'token'):
        raise ValueError(f'component_type must be "icon" or "token", got: {component_type}')
    import base64
    
    # Always use /render-icon endpoint, construct from base URL
    if service_url is None:
        # Use the new /render-icon endpoint
        base_url = TOKEN_RENDERER_URL.replace('/render-token', '')
    else:
        # If service_url is provided, it might be a full endpoint URL
        # Extract base URL by removing any endpoint paths
        base_url = service_url.replace('/render-token', '').replace('/render-icon', '').rstrip('/')
    
    # Always use /render-icon endpoint (it handles both icon and token via componentType)
    service_url = f"{base_url}/render-icon"
    
    try:
        request_body = {"iconName": icon_name, "componentType": component_type}
        if size:
            request_body["size"] = size
        print(f"    Calling {service_url} with componentType={component_type}, size={size or 'default'}")
        response = requests.post(
            service_url,
            json=request_body,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        # Verify the response has the correct componentType
        returned_component_type = data.get("componentType")
        if returned_component_type != component_type:
            print(f"    ⚠ Warning: Requested {component_type} but got {returned_component_type}")
        
        image_base64 = data.get("image")
        
        if not image_base64:
            return None
        
        # Decode base64 to bytes
        image_bytes = base64.b64decode(image_base64)
        return image_bytes
    except requests.exceptions.RequestException as e:
        print(f"  ✗ Error rendering {component_type}: {e}")
        return None


def render_token_image(icon_name: str, service_url: str = None) -> Optional[bytes]:
    """Render EuiToken to base64 PNG image using token renderer service (backward compatibility)
    Returns decoded image bytes (not base64 string)
    Note: Tokens don't use a size parameter - they use the service default
    """
    return render_icon_image(icon_name, component_type='token', service_url=service_url, size=None)


def render_icon_svg(icon_name: str, component_type: str, service_url: str = None, size: str = None) -> Optional[str]:
    """Render EuiIcon or EuiToken to SVG/HTML content using icon renderer service
    Returns SVG/HTML content string
    
    Args:
        icon_name: Icon name to render
        component_type: 'icon' for EuiIcon or 'token' for EuiToken (required)
        service_url: Renderer service base URL (default: derived from TOKEN_RENDERER_URL)
        size: Icon/token size (e.g., 's', 'm', 'l', 'xl', 'xxl'). If None, uses service default.
    """
    if component_type not in ('icon', 'token'):
        raise ValueError(f'component_type must be "icon" or "token", got: {component_type}')
    
    # Always use /render-svg endpoint, construct from base URL
    if service_url is None:
        base_url = TOKEN_RENDERER_URL.replace('/render-token', '').replace('/render-icon', '').replace('/render-svg', '').rstrip('/')
    else:
        base_url = service_url.replace('/render-token', '').replace('/render-icon', '').replace('/render-svg', '').rstrip('/')
    
    service_url = f"{base_url}/render-svg"
    
    try:
        request_body = {"iconName": icon_name, "componentType": component_type}
        if size:
            request_body["size"] = size
        print(f"    Calling {service_url} with componentType={component_type}, size={size or 'default'}")
        response = requests.post(
            service_url,
            json=request_body,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        svg_content = data.get("svgContent")
        
        if not svg_content:
            return None
        
        return svg_content
    except requests.exceptions.RequestException as e:
        print(f"  ✗ Error rendering {component_type} SVG: {e}")
        return None


def save_image_bytes(image_bytes: bytes, output_path: str) -> bool:
    """Save image bytes to PNG file"""
    try:
        # Ensure parent directory exists
        parent_dir = os.path.dirname(output_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        
        # Load image with PIL to verify it's valid
        img = Image.open(io.BytesIO(image_bytes))
        
        # Save PNG
        img.save(output_path, 'PNG')
        return True
    except Exception as e:
        print(f"  ✗ Error saving image to {output_path}: {e}")
        return False


def index_embedding(
    client: Elasticsearch,
    doc_id: str,
    icon_name: str,
    filename: str,
    release_tag: str,
    svg_content: str,
    icon_image_embedding: Optional[List[float]] = None,
    token_image_embedding: Optional[List[float]] = None,
    icon_svg_embedding: Optional[List[float]] = None,
    token_svg_embedding: Optional[List[float]] = None,
    token_svg_content: Optional[str] = None,
    token_type: Optional[str] = None
) -> bool:
    """Index all embeddings for an icon in a single Elasticsearch document"""
    try:
        document = {
            "icon_name": icon_name,
            "filename": filename,
            "release_tag": release_tag,
            "svg_content": svg_content,
        }
        
        # Add embeddings if provided
        if icon_image_embedding:
            document["icon_image_embedding"] = icon_image_embedding
        if token_image_embedding:
            document["token_image_embedding"] = token_image_embedding
        if icon_svg_embedding:
            document["icon_svg_embedding"] = icon_svg_embedding
        if token_svg_embedding:
            document["token_svg_embedding"] = token_svg_embedding
        if token_svg_content:
            document["token_svg_content"] = token_svg_content
        if token_type:
            document["token_type"] = token_type
        
        # Check if document exists
        exists = client.exists(index=INDEX_NAME, id=doc_id)
        
        if exists:
            client.update(
                index=INDEX_NAME,
                id=doc_id,
                doc=document,
                doc_as_upsert=True
            )
        else:
            client.index(
                index=INDEX_NAME,
                id=doc_id,
                document=document
            )
        
        return True
    except Exception as e:
        print(f"  ✗ Error indexing in Elasticsearch: {e}")
        return False


def process_icon(
    svg_file_path: str,
    icon_name: str,
    filename: str,
    release_tag: str,
    es_client: Optional[Elasticsearch],
    index: bool,
    skip_tokens: bool,
    service_url: str = None,
    token_renderer_url: str = None,
    save_images: bool = False,
    images_output_dir: Optional[str] = None
) -> Dict:
    """Process a single icon and generate all embeddings (icon + token, image + SVG) in one document"""
    result = {
        "icon_name": icon_name,
        "filename": filename,
        "success": False,
        "indexed": False,
        "errors": []
    }
    
    try:
        # Read original SVG file content
        svg_content = read_svg_file(svg_file_path)
        
        # Initialize embeddings
        icon_image_embedding = None
        token_image_embedding = None
        icon_svg_embedding = None
        token_svg_embedding = None
        token_svg_content = None
        
        # 1. Render icon as image and generate embedding
        print(f"  Rendering icon as image (size: xxl)...")
        icon_image_bytes = render_icon_image(icon_name, component_type='icon', service_url=token_renderer_url, size='xxl')
        
        if icon_image_bytes:
            print(f"  ✓ Icon image rendered ({len(icon_image_bytes)} bytes)")
            
            # Save icon image if requested
            if save_images and images_output_dir:
                icon_image_path = os.path.join(images_output_dir, release_tag, f"{icon_name}_icon.png")
                if save_image_bytes(icon_image_bytes, icon_image_path):
                    print(f"  ✓ Icon image saved to: {icon_image_path}")
            
            # Generate embedding from rendered image
            print(f"  Generating icon image embedding...")
            icon_image_embedding = generate_embedding_from_image(icon_image_bytes, service_url)
            
            if icon_image_embedding:
                print(f"  ✓ Icon image embedding generated ({len(icon_image_embedding)} dimensions)")
            else:
                result["errors"].append("Failed to generate icon image embedding")
        else:
            result["errors"].append("Failed to render icon image - renderer service is required")
        
        # 2. Generate icon SVG embedding from original SVG
        print(f"  Generating icon SVG embedding...")
        icon_svg_embedding = generate_embedding(svg_content, service_url)
        
        if icon_svg_embedding:
            print(f"  ✓ Icon SVG embedding generated ({len(icon_svg_embedding)} dimensions)")
        else:
            result["errors"].append("Failed to generate icon SVG embedding")
        
        # 3. Process token version (if not skipped)
        if not skip_tokens:
            # 3a. Render token as image and generate embedding
            print(f"  Rendering token as image...")
            token_image_bytes = render_token_image(icon_name, token_renderer_url)
            
            if token_image_bytes:
                print(f"  ✓ Token image rendered ({len(token_image_bytes)} bytes)")
                
                # Save token image if requested
                if save_images and images_output_dir:
                    token_image_path = os.path.join(images_output_dir, release_tag, f"{icon_name}_token.png")
                    if save_image_bytes(token_image_bytes, token_image_path):
                        print(f"  ✓ Token image saved to: {token_image_path}")
                
                # Generate token image embedding
                print(f"  Generating token image embedding...")
                token_image_embedding = generate_embedding_from_image(token_image_bytes, service_url)
                
                if token_image_embedding:
                    print(f"  ✓ Token image embedding generated ({len(token_image_embedding)} dimensions)")
                else:
                    result["errors"].append("Failed to generate token image embedding")
            else:
                result["errors"].append("Failed to render token image")
            
            # 3b. Render token as SVG/HTML and generate embedding
            print(f"  Rendering token as SVG...")
            token_svg_content = render_icon_svg(icon_name, component_type='token', service_url=token_renderer_url, size=None)
            
            if token_svg_content:
                print(f"  ✓ Token SVG rendered ({len(token_svg_content)} bytes)")
                
                # Extract just the SVG element from token HTML (token has span wrapper)
                import re
                svg_match = re.search(r'<svg[^>]*>.*?</svg>', token_svg_content, re.DOTALL)
                token_svg_only = svg_match.group(0) if svg_match else token_svg_content
                
                # Generate token SVG embedding
                print(f"  Generating token SVG embedding...")
                token_svg_embedding = generate_embedding(token_svg_only, service_url)
                
                if token_svg_embedding:
                    print(f"  ✓ Token SVG embedding generated ({len(token_svg_embedding)} dimensions)")
                else:
                    result["errors"].append("Failed to generate token SVG embedding")
            else:
                result["errors"].append("Failed to render token SVG")
        
        # 4. Index all embeddings in a single document
        if index and es_client:
            doc_id = f"{icon_name}_{release_tag}"
            print(f"  Indexing all embeddings as {doc_id}...")
            
            if index_embedding(
                es_client,
                doc_id,
                icon_name,
                filename,
                release_tag,
                svg_content,
                icon_image_embedding=icon_image_embedding,
                token_image_embedding=token_image_embedding,
                icon_svg_embedding=icon_svg_embedding,
                token_svg_embedding=token_svg_embedding,
                token_svg_content=token_svg_content,
                token_type="string" if not skip_tokens else None
            ):
                print(f"  ✓ All embeddings indexed")
                result["indexed"] = True
            else:
                result["errors"].append("Failed to index embeddings")
        else:
            # If not indexing, still mark as success if at least some embeddings were generated
            if icon_image_embedding or icon_svg_embedding:
                result["indexed"] = True
        
        result["success"] = len(result["errors"]) == 0
        return result
        
    except Exception as e:
        result["errors"].append(str(e))
        print(f"  ✗ Error processing icon: {e}")
        import traceback
        traceback.print_exc()
        return result


def main():
    parser = argparse.ArgumentParser(
        description="Automated EUI icon indexing script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--index",
        action="store_true",
        help="Index embeddings in Elasticsearch (requires ELASTICSEARCH_ENDPOINT and ELASTICSEARCH_API_KEY)"
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit processing to first N icons (useful for testing)"
    )
    
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-indexing even if version already processed"
    )
    
    parser.add_argument(
        "--skip-tokens",
        action="store_true",
        help="Skip token rendering (index only icons)"
    )
    
    parser.add_argument(
        "--save-images",
        action="store_true",
        help="Save rendered icon and token images as PNG files"
    )
    
    parser.add_argument(
        "--images-output-dir",
        default="data/rendered_images",
        help="Directory to save rendered images (default: data/rendered_images)"
    )
    
    parser.add_argument(
        "--eui-location",
        default=EUI_LOCATION,
        help=f"Directory path for EUI repository (default: {EUI_LOCATION})"
    )
    
    parser.add_argument(
        "--eui-repo",
        default=EUI_REPO,
        help=f"Git repository URL (default: {EUI_REPO})"
    )
    
    args = parser.parse_args()
    
    # Ensure data directory exists
    ensure_directory("data")
    
    # Repository management
    eui_location = os.path.abspath(args.eui_location)
    ensure_directory(eui_location)
    
    # Clone repository if needed
    if not clone_repository(args.eui_repo, eui_location):
        print("✗ Failed to clone repository")
        sys.exit(1)
    
    # Fetch tags and get latest major release
    if not fetch_tags(eui_location):
        print("⚠ Warning: Could not fetch tags, continuing with existing tags")
    
    latest_tag = get_latest_major_release_tag(eui_location)
    if not latest_tag:
        print("✗ Could not determine latest major release tag")
        sys.exit(1)
    
    # Checkout latest tag
    if not checkout_tag(eui_location, latest_tag):
        print("✗ Failed to checkout tag")
        sys.exit(1)
    
    # Extract icon mapping
    icon_map_path = os.path.join(eui_location, ICON_MAP_PATH)
    type_to_path_map = extract_type_to_path_map(icon_map_path)
    if not type_to_path_map:
        print("✗ Failed to extract icon mappings")
        sys.exit(1)
    
    # Create reverse mapping
    filename_to_icon = create_filename_to_icon_name_map(type_to_path_map)
    
    # Find SVG files recursively in the entire repository
    svg_files = find_svg_files(eui_location)
    if not svg_files:
        print("✗ No SVG files found in repository")
        sys.exit(1)
    
    # Match SVG files to icon mappings
    matched_icons = []
    unmatched_svgs = []
    
    for svg_file in svg_files:
        filename = get_filename_from_path(svg_file)
        if filename in filename_to_icon:
            icon_name = filename_to_icon[filename]
            matched_icons.append((svg_file, icon_name, filename))
        else:
            unmatched_svgs.append((svg_file, filename))
    
    # Check if version already processed and all icons are indexed
    processed_version = read_processed_version()
    if processed_version == latest_tag and not args.force:
        # Initialize Elasticsearch client to check if all icons are indexed
        es_client_check = get_elasticsearch_client()
        if es_client_check:
            print(f"Checking if all icons for version {latest_tag} are indexed...")
            if check_all_icons_indexed(es_client_check, matched_icons, latest_tag, args.skip_tokens):
                print(f"✓ Version {latest_tag} already fully indexed. Use --force to re-index.")
                sys.exit(0)
            else:
                print(f"⚠ Version {latest_tag} was processed but not all icons are indexed. Continuing...")
        else:
            print(f"⚠ Version {latest_tag} was processed but cannot verify indexing status. Continuing...")
    
    # Warn about unmatched SVGs
    if unmatched_svgs:
        print(f"\n⚠ Warning: {len(unmatched_svgs)} SVG files not found in typeToPathMap:")
        for svg_file, filename in unmatched_svgs[:10]:  # Show first 10
            print(f"  - {filename} ({svg_file})")
        if len(unmatched_svgs) > 10:
            print(f"  ... and {len(unmatched_svgs) - 10} more")
    
    # Warn about missing SVGs
    # Create a set of all SVG filenames (without extension) found in the repo
    found_svg_filenames = {get_filename_from_path(svg_file) for svg_file in svg_files}
    
    missing_icons = []
    for icon_name, filename in type_to_path_map.items():
        # Check if SVG file exists in the found files
        if filename not in found_svg_filenames:
            missing_icons.append((icon_name, filename))
    
    if missing_icons:
        print(f"\n⚠ Warning: {len(missing_icons)} icons in typeToPathMap without corresponding SVG files:")
        for icon_name, filename in missing_icons[:10]:  # Show first 10
            print(f"  - {icon_name} -> {filename}")
        if len(missing_icons) > 10:
            print(f"  ... and {len(missing_icons) - 10} more")
    
    print(f"\n✓ Matched {len(matched_icons)} icons for processing")
    
    # Apply limit if specified
    if args.limit and args.limit > 0:
        matched_icons = matched_icons[:args.limit]
        print(f"  Limiting to first {len(matched_icons)} icons")
    
    # Initialize Elasticsearch client if indexing
    es_client = None
    if args.index:
        es_client = get_elasticsearch_client()
        if not es_client:
            print("✗ Error: --index specified but Elasticsearch environment variables not set")
            print("  Set ELASTICSEARCH_ENDPOINT and ELASTICSEARCH_API_KEY")
            sys.exit(1)
        
        # Test connection
        try:
            es_client.info()
            print("✓ Connected to Elasticsearch")
        except Exception as e:
            print(f"✗ Error connecting to Elasticsearch: {e}")
            sys.exit(1)
    
    # Set up images output directory if saving images
    images_output_dir = None
    if args.save_images:
        images_output_dir = os.path.abspath(args.images_output_dir)
        # Create base directory
        os.makedirs(images_output_dir, exist_ok=True)
        print(f"✓ Images will be saved to: {images_output_dir}")
    
    # Process icons
    print(f"\nProcessing {len(matched_icons)} icons...")
    print("=" * 60)
    
    results = []
    for i, (svg_file, icon_name, filename) in enumerate(matched_icons, 1):
        print(f"\n[{i}/{len(matched_icons)}] Processing: {icon_name} ({filename})")
        print(f"  SVG file: {svg_file}")
        
        result = process_icon(
            svg_file,
            icon_name,
            filename,
            latest_tag,
            es_client,
            args.index,
            args.skip_tokens,
            EMBEDDING_SERVICE_URL,
            TOKEN_RENDERER_URL,
            save_images=args.save_images,
            images_output_dir=images_output_dir
        )
        
        results.append(result)
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    successful = sum(1 for r in results if r["success"])
    indexed = sum(1 for r in results if r["indexed"])
    failed = len(results) - successful
    
    print(f"Total icons: {len(results)}")
    print(f"Successful: {successful}")
    if args.index:
        print(f"Icons indexed: {indexed}")
    print(f"Failed: {failed}")
    
    if failed > 0:
        print("\nFailed icons:")
        for result in results:
            if not result["success"]:
                print(f"  - {result['icon_name']}: {', '.join(result['errors'])}")
    
    # Write processed version if successful
    if successful > 0 and args.index:
        write_processed_version(latest_tag)
        print(f"\n✓ Version {latest_tag} processed successfully")
    
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()

