import type { NextApiRequest, NextApiResponse } from "next";
import { client, INDEX_NAME } from "../../client/es";
import fetch from "node-fetch";
import { renderIconToSVG, normalizeSVG } from "../../utils/icon_renderer";
import { verifyAdminAuth } from "../../lib/auth";
import { rateLimit } from "../../lib/rateLimit";

interface BatchIndexSVGRequest {
  iconNames: string[];
}

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  // Rate limiting for admin endpoints (stricter: 10 requests per minute)
  try {
    const rateLimitResult = rateLimit(req, 10, 60 * 1000); // 10 per minute
    res.setHeader("X-RateLimit-Limit", rateLimitResult.limit.toString());
    res.setHeader("X-RateLimit-Remaining", rateLimitResult.remaining.toString());
    res.setHeader("X-RateLimit-Reset", new Date(rateLimitResult.reset).toISOString());
  } catch (error: any) {
    if (error.statusCode === 429) {
      res.setHeader("X-RateLimit-Limit", error.rateLimit.limit.toString());
      res.setHeader("X-RateLimit-Remaining", "0");
      res.setHeader("X-RateLimit-Reset", new Date(error.rateLimit.reset).toISOString());
      return res.status(429).json({ 
        error: "Rate limit exceeded",
        rateLimit: error.rateLimit
      });
    }
    throw error;
  }

  // Optional admin authentication (only enforced if ADMIN_API_KEY is set)
  try {
    verifyAdminAuth(req);
  } catch (error: any) {
    return res.status(401).json({ error: error.message || "Unauthorized" });
  }

  if (!client) {
    return res.status(500).json({ error: "Elasticsearch client not configured" });
  }

  const { iconNames }: BatchIndexSVGRequest = req.body;

  if (!iconNames || !Array.isArray(iconNames) || iconNames.length === 0) {
    return res.status(400).json({ error: "Missing or empty 'iconNames' array" });
  }

  const results = {
    success: 0,
    failed: 0,
    errors: [] as Array<{ iconName: string; error: string }>,
  };

  // Process icons in batches
  const batchSize = 10;
  for (let i = 0; i < iconNames.length; i += batchSize) {
    const batch = iconNames.slice(i, i + batchSize);

    await Promise.all(
      batch.map(async (iconName) => {
        try {
          // Render icon to SVG
          const svgContent = await renderIconToSVG(iconName, "xl");
          
          if (!svgContent) {
            throw new Error("Failed to render icon to SVG");
          }

          // Normalize SVG
          const normalizedSVG = normalizeSVG(svgContent, 224);

          // Generate embeddings from SVG
          const embeddingServiceUrl = process.env.EMBEDDING_SERVICE_URL || "http://localhost:8000";
          const apiKey = process.env.FRONTEND_API_KEY;
          const headers: Record<string, string> = { "Content-Type": "application/json" };
          if (apiKey) {
            headers["X-API-Key"] = apiKey;
          }
          
          const embedRes = await fetch(`${embeddingServiceUrl}/embed-svg`, {
            method: "POST",
            headers,
            body: JSON.stringify({ svg_content: normalizedSVG }),
          });

          if (!embedRes.ok) {
            throw new Error(`Embedding generation failed: ${embedRes.statusText}`);
          }

          const responseData = await embedRes.json() as { embeddings: number[] };
          const { embeddings } = responseData;

          // Check if document exists
          const exists = await client.exists({
            index: INDEX_NAME,
            id: iconName,
          });

          const document: any = {
            icon_name: iconName,
            svg_embedding: embeddings,
          };

          if (exists) {
            // Update existing document
            await client.update({
              index: INDEX_NAME,
              id: iconName,
              doc: document,
              doc_as_upsert: true,
            });
          } else {
            // Create new document
            await client.index({
              index: INDEX_NAME,
              id: iconName,
              document: document,
            });
          }

          results.success++;
        } catch (error: any) {
          results.failed++;
          results.errors.push({
            iconName: iconName,
            error: error.message || "Unknown error",
          });
          console.error(`Error indexing SVG for ${iconName}:`, error);
        }
      })
    );

    // Delay between batches
    if (i + batchSize < iconNames.length) {
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
  }

  return res.status(200).json({
    total: iconNames.length,
    success: results.success,
    failed: results.failed,
    errors: results.errors,
  });
}

