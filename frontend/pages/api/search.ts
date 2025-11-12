import type { NextApiRequest, NextApiResponse } from "next";
import { client, INDEX_NAME } from "../../client/es";
import fetch from "node-fetch";
import FormData from "form-data";

type SearchType = "text" | "image" | "svg";

interface SearchRequest {
  type: SearchType;
  query: string; // text string, base64 image, or SVG code
  icon_type?: "icon" | "token"; // Optional filter for icon type (deprecated, use fields instead)
  fields?: string[]; // Optional: specific embedding fields to search (e.g., ["icon_image_embedding", "icon_svg_embedding"])
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

  const { type, query, icon_type, fields }: SearchRequest = req.body;

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

    // Build filter for icon_type if provided
    const iconTypeFilter = icon_type
      ? {
          term: {
            icon_type: icon_type,
          },
        }
      : null;

    // Build search query
    const searchBody: any = {
      size: 50,
    };

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
      // Text searches use text_embedding field
      searchBody.knn = {
        field: "text_embedding",
        query_vector: embeddings,
        k: 10,
        num_candidates: 100,
        filter: iconTypeFilter ? [iconTypeFilter] : undefined,
      };
    } else if (type === "image" || type === "svg") {
      // Image/SVG searches: use fields parameter if provided, otherwise fall back to icon_type logic
      const knnQueries: any[] = [];
      
      // Valid embedding fields
      const validFields = [
        "icon_image_embedding",
        "icon_svg_embedding",
        "token_image_embedding",
        "token_svg_embedding",
      ];
      
      // Determine which fields to search
      let fieldsToSearch: string[] = [];
      
      if (fields && Array.isArray(fields) && fields.length > 0) {
        // Use explicitly provided fields (filter to only valid ones)
        fieldsToSearch = fields.filter((f) => validFields.includes(f));
      } else {
        // Fall back to icon_type logic for backward compatibility
        if (icon_type === "icon") {
          fieldsToSearch = ["icon_image_embedding", "icon_svg_embedding"];
        } else if (icon_type === "token") {
          fieldsToSearch = ["token_image_embedding", "token_svg_embedding"];
        } else {
          // Default: search all fields
          fieldsToSearch = validFields;
        }
      }
      
      // If no valid fields, default to all fields
      if (fieldsToSearch.length === 0) {
        fieldsToSearch = validFields;
      }
      
      // If only one field, use a single KNN query (scores will be normalized 0-1 for cosine similarity)
      // If multiple fields, use an array (scores will be combined and may exceed 1.0)
      if (fieldsToSearch.length === 1) {
        searchBody.knn = {
          field: fieldsToSearch[0],
          query_vector: embeddings,
          k: 10,
          num_candidates: 100,
        };
      } else {
        // Build KNN queries for each selected field
        for (const field of fieldsToSearch) {
          knnQueries.push({
            field: field,
            query_vector: embeddings,
            k: 10,
            num_candidates: 100,
          });
        }
        
        // Note: When using multiple KNN queries, Elasticsearch combines scores which can result
        // in scores > 1.0. This is expected behavior - scores are still relative (higher = better match).
        searchBody.knn = knnQueries;
      }
    } else {
      // Fallback: text search without sparse embeddings
      searchBody.knn = {
        field: "text_embedding",
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

