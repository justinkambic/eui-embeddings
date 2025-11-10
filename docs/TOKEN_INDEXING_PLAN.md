# Token Icon Indexing Plan

## Problem

Icons in Kibana can be rendered as "tokens" using the `EuiToken` component, which adds an additional outline/border around the icon. This creates a visual difference between:

- **Regular icons**: Just the icon shape
- **Token icons**: Icon shape + outline/border around it

When users search with screenshots of tokenized icons, they don't match regular icon embeddings because the token outline changes the visual appearance significantly.

## Solution

Index tokenized versions of icons separately using the `EuiToken` component. Since `EuiToken` outputs SVG, we can use the existing SVG embedding pipeline with minimal modifications.

## Implementation

### 1. Add Token Rendering Function

**File**: `frontend/utils/icon_renderer.ts`

Add a new function to render icons as tokens:

```typescript
/**
 * Render an EuiToken to SVG string
 * @param iconType - The icon type name
 * @param tokenType - Token type (e.g., 'string', 'number', 'boolean', etc.)
 * @param size - Icon size (default: 'xl')
 * @returns SVG string or null on error
 */
export async function renderTokenToSVG(
  iconType: string, 
  tokenType: string = 'string',
  size: string = 'xl'
): Promise<string | null> {
  try {
    const tokenElement = React.createElement(EuiToken, {
      iconType: iconType,
      tokenType: tokenType,
      size: size
    });
    
    const htmlString = renderToStaticMarkup(tokenElement);
    
    // Extract just the SVG part
    const svgMatch = htmlString.match(/<svg[^>]*>.*<\/svg>/s);
    if (svgMatch) {
      return svgMatch[0];
    }
    
    return htmlString;
  } catch (error: any) {
    console.error(`Error rendering token ${iconType}:`, error.message);
    return null;
  }
}
```

### 2. Create Batch Token Indexing API

**File**: `frontend/pages/api/batchIndexTokens.ts`

Create a new API route to batch index tokenized icons:

```typescript
import type { NextApiRequest, NextApiResponse } from "next";
import { client, INDEX_NAME } from "../../client/es";
import fetch from "node-fetch";
import { renderTokenToSVG, normalizeSVG } from "../../utils/icon_renderer";

interface BatchIndexTokensRequest {
  iconNames: string[];
  tokenType?: string; // Optional: default token type
}

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  const { iconNames, tokenType = 'string' }: BatchIndexTokensRequest = req.body;

  // Process each icon as a token
  // Index with ID: {iconName}_token
  // Use existing SVG embedding pipeline
}
```

### 3. Update Batch Embedding Script

**File**: `batch_embed_svgs.py`

Add support for tokenized icons:

- Add `--token` flag to process tokens
- Add `--token-type` option to specify token type
- Index with ID: `{iconName}_token`
- Use same SVG embedding pipeline

### 4. Update Search API

**File**: `frontend/pages/api/search.ts`

Update search to also check tokenized versions:

- When searching, also search for `{iconName}_token` variants
- Or search both regular and token embeddings
- Return results with indication if it's a token match

## Indexing Strategy

### Document ID Format

- **Regular icon**: `{iconName}` (e.g., `app_discover`)
- **Token icon**: `{iconName}_token` (e.g., `app_discover_token`)

### Index Fields

Tokenized icons will have the same fields as regular icons:
- `icon_name`: Original icon name (e.g., `app_discover`)
- `icon_type`: `'token'` to distinguish from regular icons
- `token_type`: Token type used (e.g., `'string'`, `'number'`, etc.)
- `svg_embedding`: CLIP embeddings (512 dimensions)
- `text_embedding`: Text embeddings (384 dimensions) - optional
- `text_embedding_sparse`: ELSER sparse embeddings - optional

## Token Types

EuiToken supports various token types. Common ones include:
- `string`
- `number`
- `boolean`
- `date`
- `geo`
- `ip`
- `keyword`
- `text`
- And many more (see EUI documentation)

## Implementation Steps

1. **Add `renderTokenToSVG()` function** to `frontend/utils/icon_renderer.ts`
2. **Create `batchIndexTokens.ts` API route** for batch token indexing
3. **Update `batch_embed_svgs.py`** to support `--token` flag
4. **Test token rendering** with a few icons first
5. **Index tokenized versions** of all icons (or subset)
6. **Update search logic** to handle token matches
7. **Test search accuracy** with token screenshots

## Files to Create/Modify

### New Files
- `frontend/pages/api/batchIndexTokens.ts` - Batch token indexing API

### Modified Files
- `frontend/utils/icon_renderer.ts` - Add `renderTokenToSVG()` function
- `batch_embed_svgs.py` - Add `--token` flag support
- `frontend/pages/api/search.ts` - Update to handle token matches (optional)

## Testing

1. Test token rendering with a few icons:
   ```bash
   # Test rendering tokenNull as token
   # Verify SVG output includes token outline
   ```

2. Test token indexing:
   ```bash
   # Index a few icons as tokens
   # Verify they're indexed with _token suffix
   ```

3. Test token search:
   ```bash
   # Search with token screenshot
   # Verify token matches appear in results
   ```

## Future Enhancements

- Support multiple token types per icon (index all variants)
- Automatic token type detection from screenshots
- Token type filtering in search results
- Visual distinction in search results (token vs regular)

## Notes

- This is an advanced feature for future implementation
- Token indexing can be done incrementally (not all icons need tokens)
- Token types can be customized per icon if needed
- Search can be enhanced to prefer token matches when searching with token screenshots

