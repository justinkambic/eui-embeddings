# EUI icons MCP server

A Model Context Protocol server that lets AI assistants (Claude Code,
Cursor, Claude Desktop, etc.) search EUI icons by image or text. The
typical flow:

1. You paste a screenshot of an icon into your AI chat.
2. The assistant calls the `icon_search` tool with the image path.
3. This server forwards to the hosted icon-search API with your bearer
   token. On first use it opens a browser tab for Google sign-in.
4. The assistant gets back a ranked list with EUI prop names and can
   drop `<EuiIcon type="search" />` straight into your code.

This server holds **no Elasticsearch credentials**. It authenticates as
*you*, with the same Google OAuth flow the EUI docs search UI uses, and
the hosted API holds the key. Anyone with an `@elastic.co` Google
account can use it.

## Quick start

```bash
git clone git@github.com:justinkambic/eui-embeddings.git
cd eui-embeddings

# 1. Install MCP deps in a dedicated venv.
python3 -m venv .venv-mcp
.venv-mcp/bin/pip install -r examples/mcp/requirements.txt

# 2. Sign in once. Opens your browser; finish the Google login and the
#    token is cached at ~/.config/eui-icons/tokens.json (mode 0600).
.venv-mcp/bin/python examples/mcp/server.py login

# 3. Check it worked.
.venv-mcp/bin/python examples/mcp/server.py status
```

Tokens expire after seven days. When that happens the next tool call
re-opens the browser automatically; you can also run `login` again at
any time, or `logout` to forget the token.

## Configure your AI client

### Claude Code

See `claude_code_config.example.json`. Add the `mcpServers` block to
`~/.claude.json`, substituting your absolute paths, and restart Claude
Code. Two tools appear: `icon_search` and `icon_versions`.

### Other clients

The server speaks standard MCP over stdio. Any MCP-compatible client
can launch it the same way: `python server.py`.

## Tools

### `icon_search`

Search by text or by image.

| Argument | Type | Notes |
|---|---|---|
| `text` | string? | Description like "search icon" or "warning triangle". |
| `image_path` | string? | **Preferred for image search.** Path to an image file on disk. |
| `image_base64` | string? | Base64-encoded image. Use only when the image isn't on disk. |
| `version` | string? | EUI tag like `v115.0.0`. Default: all versions. |
| `limit` | int | 1..50, default 12. |

Provide exactly ONE of `text`, `image_path`, or `image_base64`.

**Why `image_path` is preferred:** when a user pastes an image into chat,
their AI client typically attaches it as a file on disk and surfaces the
path in the conversation. Passing the path lets this server read the
bytes locally, which is both faster and more reliable than serializing
~10 KB of base64 through tool-call argument JSON.

Returns a markdown table of candidates with cosine score, version, and a
`view` link that deep-links to the icon on the docs page.

### `icon_versions`

Lists the EUI release tags currently indexed (e.g. `v116.5.0`,
`v91.0.0`).

## Environment

| Variable | Default | Notes |
|---|---|---|
| `ICON_SEARCH_BASE_URL` | hosted Cloud Run API | Set to `http://127.0.0.1:4555` to use the local Express sidecar (no auth). |
| `ICON_SEARCH_TOKEN` | unset | Bearer token override. Skips the cache and the browser flow. |
| `ICON_DOCS_BASE_URL` | hosted docs site | Base for `view` links. |
| `ICON_SEARCH_LOGIN_TIMEOUT_S` | `180` | How long to wait for the browser sign-in. |
| `XDG_CONFIG_HOME` | `~/.config` | Where `eui-icons/tokens.json` lives. |

## How sign-in works

```
server.py login
   │ 1. start one-shot listener on 127.0.0.1:<random port>
   │ 2. open browser → API /auth/login?cli_port=<port>&state=<nonce>
   ▼
Google consent → API /auth/callback
   │ 3. API verifies the account is @elastic.co, signs a token
   │ 4. redirects browser → http://127.0.0.1:<port>/callback?token=…&state=<nonce>
   ▼
server.py checks the nonce, saves the token, prints who you are
```

The redirect host is hard-coded to loopback on the API side, and the
nonce is compared in constant time, so a stray tab cannot inject a token.
The cached token is a bearer credential: anyone who can read the file
can search as you until it expires.

## Architecture

```
[ Claude Code / Cursor / etc. ]
        │ stdio (MCP protocol)
        ▼
[  examples/mcp/server.py  ]
        │ HTTPS POST /api/icon-search  (Authorization: Bearer …)
        ▼
[  icon-search API on Cloud Run (server/)  ]
        │ POST _inference + kNN
        ▼
[  Elasticsearch on Elastic Cloud  ]
```

The MCP server is the assistant-facing front end; it does no inference
or storage of its own.
