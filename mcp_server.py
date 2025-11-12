#!/usr/bin/env python3
"""
MCP Server for EUI Icon Search

This MCP server exposes tools for searching EUI icons by SVG code, image data, or text.
It interfaces with the existing Python embedding API and Elasticsearch search functionality.

The server includes signal handling for immediate exit on Ctrl+C. Note that if the server
is blocked reading from stdin (waiting for MCP protocol messages), it may require
pressing Ctrl+C twice or using kill -9 to force termination.

Usage:
    python mcp_server.py
    # Or with stdio transport:
    python -m mcp.server.stdio mcp_server
"""

import asyncio
import base64
import json
import os
import signal
import sys
from typing import Any, Optional, Sequence
from pathlib import Path

# Try to import MCP SDK, fall back to basic implementation if not available
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    MCP_AVAILABLE = True
except ImportError:
    try:
        # Try alternative import paths
        from mcp import Server
        from mcp.server.stdio import stdio_server
        from mcp.types import Tool, TextContent
        MCP_AVAILABLE = True
    except ImportError:
        MCP_AVAILABLE = False
        print("Warning: MCP SDK not installed. Install with: pip install mcp")
        print("Creating basic server structure...")

import requests
from PIL import Image
import io

# Configuration
EMBEDDING_SERVICE_URL = os.getenv("EMBEDDING_SERVICE_URL", "http://localhost:8000")
SEARCH_API_URL = os.getenv("SEARCH_API_URL", "http://localhost:3001/api/search")
ELASTICSEARCH_ENDPOINT = os.getenv("ELASTICSEARCH_ENDPOINT")
ELASTICSEARCH_API_KEY = os.getenv("ELASTICSEARCH_API_KEY")
INDEX_NAME = "icons"

# If Elasticsearch is configured, we can search directly
USE_DIRECT_SEARCH = ELASTICSEARCH_ENDPOINT and ELASTICSEARCH_API_KEY

if USE_DIRECT_SEARCH:
    try:
        from elasticsearch import Elasticsearch
        es_client = Elasticsearch(
            [ELASTICSEARCH_ENDPOINT],
            api_key=ELASTICSEARCH_API_KEY,
            request_timeout=30
        )
    except ImportError:
        USE_DIRECT_SEARCH = False
        print("Warning: elasticsearch package not available, will use API endpoint")


def search_via_api(search_type: str, query: str, icon_type: Optional[str] = None, fields: Optional[list] = None) -> dict:
    """Search using the Next.js API endpoint"""
    # Log search requests to stderr for debugging
    print(f"[MCP] Search request: type={search_type}, icon_type={icon_type}, fields={fields}", file=sys.stderr, flush=True)
    
    payload = {
        "type": search_type,
        "query": query
    }
    if icon_type:
        payload["icon_type"] = icon_type
    if fields:
        payload["fields"] = fields
    
    try:
        response = requests.post(
            SEARCH_API_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        result_count = len(result.get("results", []))
        print(f"[MCP] Search completed: {result_count} results", file=sys.stderr, flush=True)
        return result
    except requests.exceptions.RequestException as e:
        print(f"[MCP] Search error: {e}", file=sys.stderr, flush=True)
        return {
            "error": str(e),
            "results": [],
            "total": 0
        }


def format_search_results(result: dict, max_results: int = 10) -> str:
    """Format search results as a readable string for agents"""
    if "error" in result:
        return f"Error: {result['error']}"
    
    results = result.get("results", [])
    total = result.get("total", 0)
    
    if isinstance(total, dict):
        total = total.get("value", 0)
    
    if not results:
        return f"No results found (total: {total})"
    
    # Limit results
    results = results[:max_results]
    
    lines = [
        f"Found {total} total matches, showing top {len(results)}:",
        ""
    ]
    
    for i, item in enumerate(results, 1):
        icon_name = item.get("icon_name", "unknown")
        score = item.get("score", 0)
        descriptions = item.get("descriptions", [])
        release_tag = item.get("release_tag")
        icon_type = item.get("icon_type")
        
        lines.append(f"{i}. {icon_name} (score: {score:.4f})")
        if icon_type:
            lines.append(f"   Type: {icon_type}")
        if release_tag:
            lines.append(f"   Release: {release_tag}")
        if descriptions:
            desc_text = ", ".join(descriptions[:3])
            if len(descriptions) > 3:
                desc_text += f" (+{len(descriptions) - 3} more)"
            lines.append(f"   Descriptions: {desc_text}")
        lines.append("")
    
    return "\n".join(lines)


async def search_by_svg(svg_content: str, icon_type: Optional[str] = None, fields: Optional[list] = None, max_results: int = 10) -> str:
    """Search for icons using SVG code"""
    # If fields are explicitly provided, use them
    # Otherwise, default based on icon_type
    if fields is None or len(fields) == 0:
        if icon_type == "token":
            fields = ["token_svg_embedding"]
        else:
            fields = ["icon_svg_embedding"]
    
    print(f"[MCP] SVG search using fields: {fields}", file=sys.stderr, flush=True)
    result = search_via_api("svg", svg_content, icon_type=icon_type, fields=fields)
    return format_search_results(result, max_results=max_results)


async def search_by_image(image_data: str, icon_type: Optional[str] = None, fields: Optional[list] = None, max_results: int = 10) -> str:
    """
    Search for icons using image data.
    
    Args:
        image_data: Base64-encoded image data or data URI (data:image/...;base64,...)
    """
    # If fields are explicitly provided, use them
    # Otherwise, default based on icon_type
    if fields is None or len(fields) == 0:
        if icon_type == "token":
            fields = ["token_image_embedding"]
        else:
            fields = ["icon_image_embedding"]
    
    print(f"[MCP] Image search using fields: {fields}", file=sys.stderr, flush=True)
    
    # Handle data URI format
    if image_data.startswith("data:image"):
        # Extract base64 part from data URI
        base64_part = image_data.split(",", 1)[1] if "," in image_data else image_data
    else:
        base64_part = image_data
    
    result = search_via_api("image", base64_part, icon_type=icon_type, fields=fields)
    return format_search_results(result, max_results=max_results)


if MCP_AVAILABLE:
    # Create MCP server
    app = Server("eui-icon-search")
    
    @app.list_tools()
    async def list_tools() -> list[Tool]:
        """List available tools"""
        return [
            Tool(
                name="search_by_svg",
                description="Search for EUI icons by providing SVG code. Returns matching icons with similarity scores.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "svg_content": {
                            "type": "string",
                            "description": "The SVG code to search for (e.g., '<svg>...</svg>')"
                        },
                        "icon_type": {
                            "type": "string",
                            "enum": ["icon", "token"],
                            "description": "Optional: Specify 'token' to search token embeddings instead of icon embeddings. Defaults to 'icon' (searches icon_svg_embedding)."
                        },
                        "fields": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional: Override default field selection. Defaults to ['icon_svg_embedding'] for icons or ['token_svg_embedding'] for tokens. Valid fields: icon_svg_embedding, token_svg_embedding, icon_image_embedding, token_image_embedding"
                        },
                        "max_results": {
                            "type": "integer",
                            "default": 10,
                            "description": "Maximum number of results to return (default: 10)"
                        }
                    },
                    "required": ["svg_content"]
                }
            ),
            Tool(
                name="search_by_image",
                description="Search for EUI icons by providing image data (base64 encoded or data URI). Returns matching icons with similarity scores.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "image_data": {
                            "type": "string",
                            "description": "Base64-encoded image data or data URI (data:image/...;base64,...)"
                        },
                        "icon_type": {
                            "type": "string",
                            "enum": ["icon", "token"],
                            "description": "Optional: Specify 'token' to search token embeddings instead of icon embeddings. Defaults to 'icon' (searches icon_image_embedding)."
                        },
                        "fields": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional: Override default field selection. Defaults to ['icon_image_embedding'] for icons or ['token_image_embedding'] for tokens. Valid fields: icon_svg_embedding, token_svg_embedding, icon_image_embedding, token_image_embedding"
                        },
                        "max_results": {
                            "type": "integer",
                            "default": 10,
                            "description": "Maximum number of results to return (default: 10)"
                        }
                    },
                    "required": ["image_data"]
                }
            )
        ]
    
    @app.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        """Handle tool calls"""
        # Log tool calls to stderr for debugging
        print(f"[MCP] Tool called: {name}", file=sys.stderr, flush=True)
        try:
            if name == "search_by_svg":
                svg_content = arguments.get("svg_content")
                if not svg_content:
                    return [TextContent(
                        type="text",
                        text="Error: svg_content is required"
                    )]
                
                result = await search_by_svg(
                    svg_content,
                    icon_type=arguments.get("icon_type"),
                    fields=arguments.get("fields"),
                    max_results=arguments.get("max_results", 10)
                )
                return [TextContent(type="text", text=result)]
            
            elif name == "search_by_image":
                image_data = arguments.get("image_data")
                if not image_data:
                    return [TextContent(
                        type="text",
                        text="Error: image_data is required"
                    )]
                
                result = await search_by_image(
                    image_data,
                    icon_type=arguments.get("icon_type"),
                    fields=arguments.get("fields"),
                    max_results=arguments.get("max_results", 10)
                )
                return [TextContent(type="text", text=result)]
            
            else:
                return [TextContent(
                    type="text",
                    text=f"Unknown tool: {name}"
                )]
        
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error executing tool {name}: {str(e)}"
            )]
    
    async def main():
        """Run the MCP server"""
        
        # Log startup information to stderr (stdout is used for MCP protocol)
        # Use flush=True to ensure output is visible immediately
        print("=" * 60, file=sys.stderr, flush=True)
        print("EUI Icon Search MCP Server", file=sys.stderr, flush=True)
        print("=" * 60, file=sys.stderr, flush=True)
        print(f"Search API URL: {SEARCH_API_URL}", file=sys.stderr, flush=True)
        print(f"Embedding Service URL: {EMBEDDING_SERVICE_URL}", file=sys.stderr, flush=True)
        if USE_DIRECT_SEARCH:
            print(f"Elasticsearch: {ELASTICSEARCH_ENDPOINT} (direct access)", file=sys.stderr, flush=True)
        else:
            print("Elasticsearch: Using API endpoint", file=sys.stderr, flush=True)
        print(f"Index Name: {INDEX_NAME}", file=sys.stderr, flush=True)
        print("Available tools:", file=sys.stderr, flush=True)
        print("  - search_by_svg: Search icons using SVG code", file=sys.stderr, flush=True)
        print("  - search_by_image: Search icons using image data", file=sys.stderr, flush=True)
        print("=" * 60, file=sys.stderr, flush=True)
        print("Server starting...", file=sys.stderr, flush=True)
        print("(Press Ctrl+C to stop)", file=sys.stderr, flush=True)
        print("=" * 60, file=sys.stderr, flush=True)
        
        # Use stdio transport for MCP communication
        from mcp.server.stdio import stdio_server
        
        # Set up asyncio signal handlers (must be done after event loop is running)
        loop = asyncio.get_running_loop()
        shutdown_event = asyncio.Event()
        
        def signal_handler():
            """Handle shutdown signal"""
            print("\nShutdown signal received, shutting down gracefully...", file=sys.stderr, flush=True)
            shutdown_event.set()
        
        # Register signal handlers using asyncio (thread-safe, runs in event loop)
        if sys.platform != "win32":
            try:
                loop.add_signal_handler(signal.SIGINT, signal_handler)
                loop.add_signal_handler(signal.SIGTERM, signal_handler)
            except NotImplementedError:
                # Some platforms don't support add_signal_handler
                signal.signal(signal.SIGINT, lambda s, f: shutdown_event.set())
                signal.signal(signal.SIGTERM, lambda s, f: shutdown_event.set())
        else:
            signal.signal(signal.SIGINT, lambda s, f: shutdown_event.set())
        
        try:
            async with stdio_server() as (read_stream, write_stream):
                print("MCP server initialized, ready for connections", file=sys.stderr, flush=True)
                
                # Create the server task
                server_task = asyncio.create_task(
                    app.run(
                        read_stream,
                        write_stream,
                        app.create_initialization_options()
                    )
                )
                
                # Create a task that waits for shutdown signal
                shutdown_task = asyncio.create_task(shutdown_event.wait())
                
                # Wait for either server completion or shutdown signal
                done, pending = await asyncio.wait(
                    [server_task, shutdown_task],
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # Cancel pending tasks
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                
                # If shutdown was requested, cancel the server task and exit immediately
                if shutdown_event.is_set():
                    server_task.cancel()
                    # Exit the context manager by raising an exception that will be caught
                    raise SystemExit(0)
        except KeyboardInterrupt:
            # Allow KeyboardInterrupt to propagate for clean exit
            print("\nServer shutdown requested", file=sys.stderr, flush=True)
            raise
        except Exception as e:
            print(f"Error running server: {e}", file=sys.stderr, flush=True)
            import traceback
            traceback.print_exc(file=sys.stderr)
            raise
    
    if __name__ == "__main__":
        # Force unbuffered output for stderr to ensure logging is visible
        sys.stderr.reconfigure(line_buffering=True)
        
        # Immediate startup message (before anything else)
        print("EUI Icon Search MCP Server - Starting...", file=sys.stderr, flush=True)
        print(f"Python: {sys.version}", file=sys.stderr, flush=True)
        print(f"MCP SDK Available: {MCP_AVAILABLE}", file=sys.stderr, flush=True)
        
        if not MCP_AVAILABLE:
            print("ERROR: MCP SDK not available! Install with: pip install mcp", file=sys.stderr, flush=True)
            print("Running in fallback CLI mode instead.", file=sys.stderr, flush=True)
        
        # Signal handlers are set up inside the async main() function
        # using asyncio's add_signal_handler for proper async handling
        
        # Run the server
        try:
            asyncio.run(main())
        except* BaseException as eg:
            # Handle ExceptionGroup (from anyio task group in stdio_server)
            # Check if it contains KeyboardInterrupt or SystemExit
            has_exit = False
            for exc in eg.exceptions:
                if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                    has_exit = True
                    # If SystemExit, use its code
                    if isinstance(exc, SystemExit) and exc.code is not None:
                        sys.exit(exc.code)
                    break
            
            if has_exit:
                # Exit signal in task group - exit immediately
                sys.exit(0)
            else:
                # Other exception - log and exit
                print(f"Error running server:", file=sys.stderr, flush=True)
                import traceback
                for exc in eg.exceptions:
                    traceback.print_exception(type(exc), exc, exc.__traceback__, file=sys.stderr)
                sys.exit(1)

else:
    # Fallback: Simple CLI interface for testing
    async def main():
        """Simple CLI for testing without MCP SDK"""
        print("MCP SDK not available. Running in test mode.")
        print("Install with: pip install mcp")
        print()
        
        if len(sys.argv) < 2:
            print("Usage:")
            print("  python mcp_server.py svg '<svg>...</svg>'")
            print("  python mcp_server.py image <base64_data>")
            return
        
        command = sys.argv[1]
        
        if command == "svg" and len(sys.argv) > 2:
            svg_content = sys.argv[2]
            result = await search_by_svg(svg_content)
            print(result)
        elif command == "image" and len(sys.argv) > 2:
            image_data = sys.argv[2]
            result = await search_by_image(image_data)
            print(result)
        else:
            print("Invalid command")
    
    if __name__ == "__main__":
        asyncio.run(main())

