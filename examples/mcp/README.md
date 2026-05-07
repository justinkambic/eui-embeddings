# EUI icons MCP server

A Model Context Protocol server that lets AI assistants (Claude Code,
Cursor, Claude Desktop, etc.) search EUI icons by image or text. The
typical flow:

1. You paste a screenshot of an icon into your AI chat.
2. The assistant calls the `icon_search` tool with the image bytes as
   base64.
3. This server forwards to the local `icon-search-server` sidecar
   running on `http://127.0.0.1:4555`.
4. The assistant gets back a ranked list with EUI prop names and can
   drop `<EuiIcon type="search" />` straight into your code.

This server holds **no credentials**. It only talks to the sidecar over
localhost. The sidecar (in the EUI worktree's
`packages/icon-search-server/`) is the one with the Elasticsearch API
key.

## Quick start

```bash
cd ~/git/justinkambic/eui-embeddings

# 1. Install MCP deps in a dedicated venv (separate from the ingester's venv).
python3 -m venv .venv-mcp
source .venv-mcp/bin/activate
pip install -r examples/mcp/requirements.txt

# 2. Make sure the sidecar is running on http://127.0.0.1:4555.
#    (In a different terminal, in the EUI worktree:)
#    yarn workspace @elastic/icon-search-server start

# 3. Verify the MCP server starts.
.venv-mcp/bin/python examples/mcp/server.py
# (will hang on stdin waiting for MCP protocol messages — that's normal;
#  Ctrl+C to exit)
```

## Configure your AI client

### Claude Code

See `claude_code_config.example.json`. Add the `mcpServers` block to
your Claude Code config (`~/.claude.json` on macOS), substituting your
absolute paths.

After restart, Claude Code will automatically launch this server when
the tools are needed.

### Other clients

The server speaks standard MCP over stdio. Any MCP-compatible client
should be able to launch it the same way: `python server.py`.

## Tools

### `icon_search`

Search by text or by image.

| Argument | Type | Notes |
|---|---|---|
| `text` | string? | Description like "search icon" or "warning triangle". |
| `image_base64` | string? | Base64-encoded image. Data URL prefix OK. |
| `version` | string? | EUI tag like `v115.0.0`. Default: all versions. |
| `limit` | int | 1..50, default 8. |

Provide exactly one of `text` or `image_base64`.

Returns a ranked markdown list:

```
Top 3 matches:
1. `search` (score 1.000, v115.0.0)
2. `magnify` (score 0.987, v115.0.0)
3. `magnifyExclamation` (score 0.961, v115.0.0)

Best match: `<EuiIcon type="search" />`
```

### `icon_versions`

Lists the EUI release tags currently indexed (e.g. `v115.0.0`,
`v91.0.0`).

## Environment

| Variable | Default | Notes |
|---|---|---|
| `ICON_SEARCH_BASE_URL` | `http://127.0.0.1:4555` | The sidecar URL. |

## Architecture

```
[ Claude Code / Cursor / etc. ]
        │ stdio (MCP protocol)
        ▼
[  examples/mcp/server.py  ]
        │ HTTP POST /api/icon-search
        ▼
[  icon-search-server sidecar (localhost:4555)  ]
        │ POST _inference + kNN
        ▼
[  Elasticsearch on Elastic Cloud  ]
```

The MCP server is the assistant-facing front end; it does no inference
or storage of its own.
