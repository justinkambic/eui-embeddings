# MCP Server for EUI Icon Search

This document describes the Model Context Protocol (MCP) server that exposes EUI icon search capabilities to AI agents.

## Overview

The MCP server provides two tools that allow agents to search for EUI icons:
1. **search_by_svg** - Search using SVG code
2. **search_by_image** - Search using image data (base64 or data URI)

## Installation

1. Install the MCP SDK:
```bash
pip install mcp
```

Or install all dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

The MCP server uses environment variables for configuration:

```bash
# Embedding service URL (default: http://localhost:8000)
export EMBEDDING_SERVICE_URL=http://localhost:8000

# Search API URL (default: http://localhost:8000/search)
# This defaults to the Python API search endpoint
export SEARCH_API_URL=http://localhost:8000/search

# Optional: Direct Elasticsearch access (for Python API)
export ELASTICSEARCH_ENDPOINT=https://your-cluster.es.amazonaws.com
export ELASTICSEARCH_API_KEY=your-api-key
```

## Docker Usage

The MCP server can be run as a Docker container. This is useful for:
- Consistent execution environment
- Isolated dependencies
- Easy distribution to team members

### Building the Docker Image

```bash
docker build -f Dockerfile.mcp -t eui-icon-search-mcp:latest .
```

### Running with Docker

The MCP server requires environment variables to be passed at runtime:

```bash
docker run -i \
  -e ELASTICSEARCH_ENDPOINT=https://your-cluster.es.amazonaws.com \
  -e ELASTICSEARCH_API_KEY=your-api-key \
  -e EMBEDDING_SERVICE_URL=http://localhost:8000 \
  eui-icon-search-mcp:latest
```

**Note**: When running in Docker, `EMBEDDING_SERVICE_URL` should point to the host machine or a service accessible from the container. For example:
- If the embedding service runs on the host: `http://host.docker.internal:8000`
- If both services are in Docker: Use the Docker service name (e.g., `http://python-api:8000`)

### Using with Claude Desktop (Docker)

Update your Claude Desktop configuration to use Docker:

```json
{
  "mcpServers": {
    "eui-icon-search": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e", "ELASTICSEARCH_ENDPOINT=https://your-cluster.es.amazonaws.com",
        "-e", "ELASTICSEARCH_API_KEY=your-api-key",
        "-e", "EMBEDDING_SERVICE_URL=http://host.docker.internal:8000",
        "eui-icon-search-mcp:latest"
      ]
    }
  }
}
```

**Note**: The `-i` flag keeps stdin open for MCP protocol communication, and `--rm` removes the container after it exits.

### Docker Compose Example

If you're using Docker Compose, you can add the MCP server as a service:

```yaml
services:
  mcp-server:
    build:
      context: .
      dockerfile: Dockerfile.mcp
    environment:
      - ELASTICSEARCH_ENDPOINT=${ELASTICSEARCH_ENDPOINT}
      - ELASTICSEARCH_API_KEY=${ELASTICSEARCH_API_KEY}
      - EMBEDDING_SERVICE_URL=http://python-api:8000
    stdin_open: true
    tty: true
    networks:
      - eui-network
```

## Running the Server

### Prerequisites

Before running the MCP server, ensure:
1. The Python embedding service is running (`uvicorn embed:app --port 8000`)
2. Elasticsearch is configured and accessible (required for search functionality)

### Start the Server (Local)

The MCP server uses stdio transport by default:

```bash
python mcp_server.py
```

Or using the MCP module directly:
```bash
python -m mcp.server.stdio mcp_server
```

### Testing Without MCP Client

You can test the server functions directly using the built-in CLI mode:

```bash
# Test SVG search
python mcp_server.py svg '<svg>...</svg>'

# Test image search (base64)
python mcp_server.py image 'iVBORw0KGgoAAAANSUhEUgAA...'
```

### Using the Test Script

For more comprehensive testing, use the dedicated test script:

```bash
# Run all tests (default behavior)
python test_mcp_server.py

# Or explicitly request all tests
python test_mcp_server.py --all
```

**Test Script Arguments:**

- `--svg-file <path>` - Test SVG search with a specific SVG file
  ```bash
  python test_mcp_server.py --svg-file path/to/test.svg
  ```
  Mutually exclusive with `--svg-string`. If neither is provided, uses a default test SVG.

- `--svg-string <svg>` - Test SVG search with SVG content provided as a string
  ```bash
  python test_mcp_server.py --svg-string "<svg viewBox='0 0 16 16'><circle cx='8' cy='8' r='6'/></svg>"
  ```
  Mutually exclusive with `--svg-file`. If neither is provided, uses a default test SVG.

- `--image-file <path>` - Test image search with a specific image file (PNG, JPG, etc.)
  ```bash
  python test_mcp_server.py --image-file path/to/test.png
  ```
  If not provided, image search test is skipped.

- `--icon-type <type>` - Specify icon type: `icon` or `token` (affects default field selection)
  ```bash
  python test_mcp_server.py --icon-type token
  ```
  When specified, defaults to the appropriate token field instead of icon field.

- `--icon-image` - Include `icon_image_embedding` field in search (flag, no value needed)
- `--icon-svg` - Include `icon_svg_embedding` field in search (flag, no value needed)
- `--token-image` - Include `token_image_embedding` field in search (flag, no value needed)
- `--token-svg` - Include `token_svg_embedding` field in search (flag, no value needed)

  These field override flags can be combined to search multiple fields. If any are specified, they override the default field selection based on `icon_type`.
  ```bash
  # Search both icon and token SVG embeddings
  python test_mcp_server.py --icon-svg --token-svg --svg-string "<svg>...</svg>"
  
  # Search all four fields
  python test_mcp_server.py --icon-image --icon-svg --token-image --token-svg --image-file test.png
  ```

- `--all` - Run all tests (this is the default behavior if no specific tests are requested)

**Examples:**

```bash
# Test with specific inputs
python test_mcp_server.py --svg-file path/to/test.svg
python test_mcp_server.py --svg-string "<svg>...</svg>"
python test_mcp_server.py --image-file path/to/test.png

# Combine multiple tests
python test_mcp_server.py --svg-file icon.svg --image-file screenshot.png

# Test only SVG with a specific file
python test_mcp_server.py --svg-file my-icon.svg

# Test only SVG with inline content
python test_mcp_server.py --svg-string "<svg viewBox='0 0 16 16'><circle cx='8' cy='8' r='6'/></svg>"

# Test with icon type specified (uses token fields by default)
python test_mcp_server.py --icon-type token --svg-file token.svg

# Test with specific fields (overrides defaults)
python test_mcp_server.py --icon-svg --token-svg --svg-string "<svg>...</svg>"

# Test image search with all fields
python test_mcp_server.py --icon-image --icon-svg --token-image --token-svg --image-file test.png
```

**Notes:**
- `--svg-file` and `--svg-string` are mutually exclusive - you can only use one at a time.
- Field override flags (`--icon-image`, `--icon-svg`, `--token-image`, `--token-svg`) can be combined to search multiple fields simultaneously.
- If field override flags are specified, they take precedence over `--icon-type` defaults.
- If no field flags are specified, `--icon-type` determines the default field (icon fields for "icon", token fields for "token").

The test script will:
- Check prerequisites (API URLs, services)
- Test SVG and image search functions (or only specified ones)
- Provide detailed output and error messages
- Show a summary of test results with pass/fail status

## MCP Tools

### 1. search_by_svg

Search for icons by providing SVG code.

**Parameters:**
- `svg_content` (required): The SVG code to search for
- `icon_type` (optional): Filter by "icon" or "token"
- `fields` (optional): Array of specific embedding fields to search
- `max_results` (optional): Maximum results to return (default: 10)

**Example:**
```json
{
  "name": "search_by_svg",
  "arguments": {
    "svg_content": "<svg viewBox=\"0 0 16 16\"><path d=\"M8 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6z\"/></svg>",
    "max_results": 5
  }
}
```

### 2. search_by_image

Search for icons by providing image data.

**Parameters:**
- `image_data` (required): Base64-encoded image or data URI
- `icon_type` (optional): Filter by "icon" or "token"
- `fields` (optional): Array of specific embedding fields to search
- `max_results` (optional): Maximum results to return (default: 10)

**Example:**
```json
{
  "name": "search_by_image",
  "arguments": {
    "image_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
    "icon_type": "icon",
    "max_results": 10
  }
}
```

## Response Format

All tools return formatted text results with:
- Total number of matches
- Top N results (configurable)
- For each result:
  - Icon name
  - Similarity score
  - Icon type (if available)
  - Release tag (if available)
  - Descriptions (if available)

**Example Response:**
```
Found 25 total matches, showing top 10:

1. user (score: 0.9234)
   Type: icon
   Release: v109.0.0
   Descriptions: user icon, person icon, account icon

2. userAvatar (score: 0.8912)
   Type: icon
   Release: v109.0.0
   Descriptions: user avatar, profile icon, account avatar

...
```

## Integration with MCP Clients

### Claude Desktop

#### Local Python Installation

Add to your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "eui-icon-search": {
      "command": "python",
      "args": ["/path/to/eui-embeddings/mcp_server.py"],
      "env": {
        "SEARCH_API_URL": "http://localhost:8000/search",
        "EMBEDDING_SERVICE_URL": "http://localhost:8000",
        "ELASTICSEARCH_ENDPOINT": "https://your-cluster.es.amazonaws.com",
        "ELASTICSEARCH_API_KEY": "your-api-key"
      }
    }
  }
}
```

#### Docker (Alternative)

If you prefer to use Docker, see the [Docker Usage](#docker-usage) section above for configuration examples.

### Other MCP Clients

The server uses stdio transport, which is compatible with any MCP client that supports stdio. Configure your client to:
- Command: `python`
- Args: `["/path/to/mcp_server.py"]`
- Transport: stdio

## Architecture

The MCP server acts as a wrapper around the existing search infrastructure:

```
Agent → MCP Server → Search API → Embedding Service → Elasticsearch
```

Or directly:

```
Agent → MCP Server → Embedding Service → Elasticsearch
```

The server:
1. Receives tool calls from agents via MCP protocol
2. Validates and processes input (SVG/image/text)
3. Calls the appropriate API endpoint or direct search
4. Formats results for agent consumption
5. Returns formatted text response

## Error Handling

The server handles errors gracefully:
- Invalid input parameters return error messages
- API failures are caught and returned as error text
- Missing dependencies fall back to CLI mode with warnings

## Development

### Adding New Tools

To add a new tool:
1. Add tool definition to `list_tools()`
2. Add handler to `call_tool()`
3. Implement the search/processing function
4. Update this documentation

### Testing

#### Method 1: Using the Test Script (Recommended)

The easiest way to test the server is using the provided test script:

```bash
# Run all tests
python test_mcp_server.py

# Test specific functionality
python test_mcp_server.py --text "user icon"
python test_mcp_server.py --svg-file test.svg
python test_mcp_server.py --image-file test.png
```

#### Method 2: Using MCP Inspector (Official Tool)

The MCP Inspector is an official tool for testing MCP servers:

```bash
# Install and run the inspector
npx @modelcontextprotocol/inspector python mcp_server.py

# Or with custom ports
CLIENT_PORT=8080 SERVER_PORT=9000 npx @modelcontextprotocol/inspector python mcp_server.py
```

This will:
- Start a web UI at http://localhost:5173 (or your custom port)
- Allow you to interactively test all tools
- Show tool definitions and responses
- Help debug issues

#### Method 3: Using MCP Server Tester (Automated)

For automated testing:

```bash
# Clone the tester
git clone https://github.com/r-huijts/mcp-server-tester.git
cd mcp-server-tester

# Install dependencies
npm install
npm run build

# Create .env file
echo "ANTHROPIC_API_KEY=your-api-key" > .env

# Run tests (configure to point to your server)
npm start
```

#### Method 4: Programmatic Testing

Test individual functions programmatically:

```python
import asyncio
from mcp_server import search_by_svg, search_by_image, search_by_text

# Test SVG search
result = asyncio.run(search_by_svg("<svg>...</svg>"))
print(result)

# Test image search
result = asyncio.run(search_by_image("base64_data_here"))
print(result)

# Test text search
result = asyncio.run(search_by_text("user icon"))
print(result)
```

#### Method 5: Manual Testing with MCP Client

Connect with an MCP-compatible client (Claude Desktop, VS Code Copilot, etc.):

1. Configure the client to use your MCP server
2. Send tool calls through the client interface
3. Verify responses are correct

See the "Integration with MCP Clients" section for configuration details.

## Testing Guide

### Quick Test

The fastest way to verify the server is working:

```bash
# 1. Ensure services are running
# Terminal 1: Start embedding service
uvicorn embed:app --port 8000

# Terminal 2: Start frontend API (optional)
cd frontend && npm run dev

# Terminal 3: Run tests
python test_mcp_server.py
```

### Step-by-Step Testing

1. **Verify Prerequisites**
   ```bash
   # Check if services are accessible
   curl http://localhost:8000/docs  # Embedding service
   curl -X POST http://localhost:8000/search -H "Content-Type: application/json" -d '{"type":"text","query":"test"}'  # Search API
   ```

2. **Test SVG Search**
   ```bash
   # Create a test SVG file or use existing one
   python test_mcp_server.py --svg-file test.svg
   ```

3. **Test Image Search**
   ```bash
   # Use any PNG/JPG image
   python test_mcp_server.py --image-file screenshot.png
   ```

4. **Test with MCP Inspector** (if MCP SDK installed)
   ```bash
   npx @modelcontextprotocol/inspector python mcp_server.py
   ```
   Then open http://localhost:5173 in your browser and test tools interactively.

### Expected Results

A successful test should show:
- ✅ SVG and image search return results
- Results include icon names, scores, and descriptions
- No connection errors or timeouts
- Results are formatted correctly

## Troubleshooting

### "MCP SDK not installed"
Install with: `pip install mcp`

**Note**: The server will still work in CLI mode without the SDK, but you won't be able to use it as an MCP server.

### "Connection refused" errors
Ensure the embedding service is running:
- Embedding service: `uvicorn embed:app --port 8000`

**Test connectivity:**
```bash
curl http://localhost:8000/docs
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"type":"text","query":"test"}'
```

### "No results found"
- Verify Elasticsearch index exists and has data
- Check that embeddings have been generated for icons
- Verify search API is accessible
- Check Elasticsearch connection and credentials

**Debug steps:**
```bash
# Check if index exists
python check_index.py

# Test search API directly
python test_image_search.py --image-file test.png
python test_svg_search.py --svg-content "<svg>...</svg>"
```

### Server not responding
- Check that stdio transport is configured correctly
- Verify Python path is correct in MCP client config
- Check for errors in server logs
- Ensure Python version is 3.8+ (required for MCP SDK)

### Server hangs on Ctrl+C

The server includes signal handling for immediate exit. However, if the server is blocked reading from stdin (waiting for MCP protocol messages), it may not respond immediately to Ctrl+C.

**If the server hangs on Ctrl+C:**

1. **Try pressing Ctrl+C twice** - sometimes the first interrupt is consumed by the blocking read
2. **Use `kill -9`** - If Ctrl+C doesn't work, find the process ID and force kill:
   ```bash
   # Find the process
   ps aux | grep mcp_server.py
   
   # Force kill (replace <pid> with actual process ID)
   kill -9 <pid>
   ```
3. **Close the MCP client** - If you're running the server through an MCP client (like Claude Desktop), closing the client should terminate the server process

**Note**: The stdio transport reads from stdin, which can block signal handling. This is a limitation of the MCP stdio protocol. The server will exit immediately once the blocking read is interrupted.

### Test script fails
- Verify all dependencies are installed: `pip install -r requirements.txt`
- Check that `mcp_server.py` is in the same directory
- Ensure environment variables are set correctly
- Check that services are running before testing

