import type { NextApiRequest, NextApiResponse } from "next";
import { client, INDEX_NAME } from "../../client/es";
import fetch from "node-fetch";
import FormData from "form-data";

type SearchType = "text" | "image" | "svg";

interface SearchRequest {
  type: SearchType;
  query: string; // text string, base64 image, or SVG code
  icon_type?: "icon" | "token"; // Optional filter for icon type
}

interface SearchResult {
  icon_name: string;
  score: number;
  descriptions?: string[];
  release_tag?: string;
  icon_type?: string;
}

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  const { type, query, icon_type }: SearchRequest = req.body;

  if (!type || !query) {
    return res.status(400).json({ error: "Missing 'type' or 'query' field" });
  }

  try {
    let embeddings: number[];
    let sparseEmbeddings: Record<string, number> | undefined;

    // Generate embeddings based on type
    if (type === "text") {
      const embedRes = await fetch("http://localhost:8000/embed", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: query }),
      });

      if (!embedRes.ok) {
        return res.status(500).json({ error: "Failed to generate text embeddings" });
      }

      const embedData = await embedRes.json() as { embeddings: number[]; sparse_embeddings?: Record<string, number> };
      embeddings = embedData.embeddings;
      sparseEmbeddings = embedData.sparse_embeddings;
    } else if (type === "image") {
      // Decode base64 image
      const imageBuffer = Buffer.from(query, "base64");
      const formData = new FormData();
      formData.append("file", imageBuffer, { filename: "image.png", contentType: "image/png" });

      const embedRes = await fetch("http://localhost:8000/embed-image", {
        method: "POST",
        body: formData,
      });

      if (!embedRes.ok) {
        return res.status(500).json({ error: "Failed to generate image embeddings" });
      }

      const embedData = await embedRes.json() as { embeddings: number[] };
      embeddings = embedData.embeddings;
    } else if (type === "svg") {
      const embedRes = await fetch("http://localhost:8000/embed-svg", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ svg_content: query }),
      });

      if (!embedRes.ok) {
        return res.status(500).json({ error: "Failed to generate SVG embeddings" });
      }

      const embedData = await embedRes.json() as { embeddings: number[] };
      embeddings = embedData.embeddings;
    } else {
      return res.status(400).json({ error: "Invalid search type" });
    }

    // Determine which embedding field to search
    // For image searches, search svg_embedding since both use CLIP (512 dimensions)
    // and are compatible. If you've indexed image_embedding separately, you can
    // change this to "image_embedding" or search both fields separately.
    let embeddingField: string;
    if (type === "text") {
      embeddingField = "text_embedding";
    } else if (type === "image") {
      // Image searches use svg_embedding since both use CLIP model (512 dimensions)
      // Both are compatible - SVGs are converted to images before embedding
      embeddingField = "svg_embedding";
    } else {
      embeddingField = "svg_embedding";
    }

    // Build search query
    const searchBody: any = {
      size: 10,
    };

    // Build filter for icon_type if provided
    const iconTypeFilter = icon_type
      ? {
          term: {
            icon_type: icon_type,
          },
        }
      : null;

    // For text searches, use hybrid search (dense + sparse)
    if (type === "text" && sparseEmbeddings) {
      // Hybrid search: combine knn with text_expansion
      const boolQuery: any = {
        should: [
          {
            text_expansion: {
              text_embedding_sparse: {
                model_text: query,
                model_id: ".elser_model_2",
              },
            },
          },
        ],
      };

      // Add icon_type filter if provided
      if (iconTypeFilter) {
        boolQuery.filter = [iconTypeFilter];
      }

      searchBody.query = {
        bool: boolQuery,
      };
      searchBody.knn = {
        field: embeddingField,
        query_vector: embeddings,
        k: 10,
        num_candidates: 100,
        filter: iconTypeFilter ? [iconTypeFilter] : undefined,
      };
    } else {
      // Pure knn search for image/SVG or text without sparse embeddings
      searchBody.knn = {
        field: embeddingField,
        query_vector: embeddings,
        k: 10,
        num_candidates: 100,
        filter: iconTypeFilter ? [iconTypeFilter] : undefined,
      };
    }

    // Execute search
    const searchResponse = await client.search({
      index: INDEX_NAME,
      body: searchBody,
    });

    // Format results
    // Use icon_name from document source, not document ID
    // Document ID includes version tag (e.g., "search_v109.0.0"), but icon_name should be just "search"
    const results: SearchResult[] = (searchResponse.hits.hits || []).map((hit: any) => ({
      icon_name: hit._source?.icon_name || hit._id,
      score: hit._score || 0,
      descriptions: hit._source?.descriptions,
      release_tag: hit._source?.release_tag,
      icon_type: hit._source?.icon_type,
    }));

    return res.status(200).json({
      results,
      total: searchResponse.hits.total,
    });
  } catch (error: any) {
    console.error("Search error:", error);
    return res.status(500).json({ error: error.message || "Search failed" });
  }
}

