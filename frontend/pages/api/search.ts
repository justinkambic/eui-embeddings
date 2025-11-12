import type { NextApiRequest, NextApiResponse } from "next";
import fetch from "node-fetch";

type SearchType = "text" | "image" | "svg";

interface SearchRequest {
  type: SearchType;
  query: string; // text string, base64 image, or SVG code
  icon_type?: "icon" | "token"; // Optional filter for icon type (deprecated, use fields instead)
  fields?: string[]; // Optional: specific embedding fields to search (e.g., ["icon_image_embedding", "icon_svg_embedding"])
}

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  const { type, query, icon_type, fields }: SearchRequest = req.body;

  if (!type || !query) {
    return res.status(400).json({ error: "Missing 'type' or 'query' field" });
  }

  try {
    // Forward request to Python API
    const pythonApiUrl = process.env.EMBEDDING_SERVICE_URL || "http://localhost:8000";
    const searchUrl = `${pythonApiUrl}/search`;
    
    // Get API key from environment variable
    const apiKey = process.env.FRONTEND_API_KEY;
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (apiKey) {
      headers["X-API-Key"] = apiKey;
    }

    const response = await fetch(searchUrl, {
        method: "POST",
        headers,
      body: JSON.stringify({
        type,
        query,
        icon_type,
        fields,
      }),
      });

    if (!response.ok) {
      // Read response body once
      const contentType = response.headers.get("content-type") || "";
      let errorData: any;
      
      if (contentType.includes("application/json")) {
        // FastAPI returns JSON errors with "detail" field
        errorData = await response.json();
      } else {
        // Fallback to text
        const errorText = await response.text();
        errorData = { error: errorText || "Search failed" };
      }
      
      console.error("Python API error:", errorData);
      return res.status(response.status).json({ 
        error: errorData.detail || errorData.error || "Search failed" 
      });
    }

    const data = await response.json();
    return res.status(200).json(data);
  } catch (error: any) {
    console.error("Search proxy error:", error);
    return res.status(500).json({ error: error.message || "Search failed" });
  }
}

