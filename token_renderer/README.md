# Token Renderer Microservice

Standalone Node.js microservice for rendering EuiToken components to SVG. This service is designed to be controlled by Python scripts for automated icon indexing.

## Setup

1. Install dependencies:
```bash
cd token_renderer
npm install
```

2. Start the service:
```bash
npm start
```

Or for development with auto-restart on file changes:
```bash
npm run dev
```

Or set a custom port:
```bash
TOKEN_RENDERER_PORT=3002 npm start
# or for development:
TOKEN_RENDERER_PORT=3002 npm run dev
```

## API Endpoints

### Health Check
```
GET /health
```

Returns:
```json
{
  "status": "ok",
  "service": "token-renderer"
}
```

### Render Token
```
POST /render-token
Content-Type: application/json

{
  "iconName": "app_discover",
  "tokenType": "string",  // optional, default: "string"
  "size": "m"             // optional, default: "m"
}
```

Returns:
```json
{
  "svg": "<svg>...</svg>",
  "iconName": "app_discover",
  "tokenType": "string",
  "size": "m"
}
```

### Batch Render Tokens
```
POST /render-tokens
Content-Type: application/json

{
  "tokens": [
    { "iconName": "app_discover", "tokenType": "string" },
    { "iconName": "logoElasticsearch", "tokenType": "string" }
  ]
}
```

Returns:
```json
{
  "results": [
    {
      "iconName": "app_discover",
      "tokenType": "string",
      "size": "m",
      "svg": "<svg>...</svg>",
      "error": null
    },
    ...
  ]
}
```

## Environment Variables

- `TOKEN_RENDERER_PORT` - Port to run the service on (default: 3002)

## Usage with Python Scripts

The Python indexing script (`scripts/index_eui_icons.py`) will automatically use this service when token rendering is enabled. Make sure the service is running before starting the indexing process.

## Error Handling

If an icon cannot be rendered, the service will return:
- For single token: HTTP 500 with error message
- For batch: Error message in the result object for that specific token

