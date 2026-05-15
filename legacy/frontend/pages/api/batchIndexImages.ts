import type { NextApiRequest, NextApiResponse } from "next";
import { client, INDEX_NAME } from "../../client/es";
import fetch from "node-fetch";
import { trace } from "@opentelemetry/api";
import { extractTraceContext, getTraceId, injectTraceContext } from "../../lib/traceContext";
import { renderIconToImage } from "../../utils/icon_renderer";
import fs from "fs/promises";
import { verifyAdminAuth } from "../../lib/auth";
import { rateLimit } from "../../lib/rateLimit";

const tracer = trace.getTracer("eui-frontend-api");

interface BatchIndexImagesRequest {
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
    // Add rate limit headers
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

  const { iconNames }: BatchIndexImagesRequest = req.body;

  if (!iconNames || !Array.isArray(iconNames) || iconNames.length === 0) {
    return res.status(400).json({ error: "Missing or empty 'iconNames' array" });
  }

  // Extract trace context from incoming request headers
  const extractedContext = extractTraceContext(req);
  const span = tracer.startSpan("api.batchIndexImages", {
    attributes: {
      "batch.size": iconNames.length,
      "http.method": req.method || "POST",
      "http.route": "/api/batchIndexImages",
    },
  }, extractedContext);
  
  const traceId = getTraceId();
  if (traceId) {
    span.setAttribute("trace.id", traceId);
  }

  const results = {
    success: 0,
    failed: 0,
    errors: [] as Array<{ iconName: string; error: string }>,
  };

  // Process icons in batches
  const batchSize = 5; // Smaller batch size for image processing
  for (let i = 0; i < iconNames.length; i += batchSize) {
    const batch = iconNames.slice(i, i + batchSize);

    await Promise.all(
      batch.map(async (iconName) => {
        try {
          // Render icon to image (this returns SVG path, we'll convert in Python)
          const svgPath = await renderIconToImage(iconName, "./rendered-icons", 224);
          
          if (!svgPath) {
            throw new Error("Failed to render icon to image");
          }

          // Read SVG and convert to image via Python API
          // For now, we'll read the SVG and send it to the embed-svg endpoint
          // In production, you might want to convert SVG to PNG first
          const svgContent = await fs.readFile(svgPath, "utf-8");

          // Generate embeddings from SVG (which converts to image internally)
          const embeddingServiceUrl = process.env.EMBEDDING_SERVICE_URL || "http://localhost:8000";
          const apiKey = process.env.FRONTEND_API_KEY;
          const headers: Record<string, string> = { "Content-Type": "application/json" };
          if (apiKey) {
            headers["X-API-Key"] = apiKey;
          }
          
          // Inject trace context for propagation to Python API
          injectTraceContext(headers);
          
          const embedRes = await fetch(`${embeddingServiceUrl}/embed-svg`, {
            method: "POST",
            headers,
            body: JSON.stringify({ svg_content: svgContent }),
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
            image_embedding: embeddings,
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
          console.error(`Error indexing image for ${iconName}:`, error);
        }
      })
    );

    // Delay between batches
    if (i + batchSize < iconNames.length) {
      await new Promise((resolve) => setTimeout(resolve, 200));
    }
  }

  // Set span attributes and end span
  span.setAttribute("batch.success", results.success);
  span.setAttribute("batch.failed", results.failed);
  span.setStatus({ code: results.failed === 0 ? 1 : 2 }); // OK if no failures, ERROR otherwise
  span.end();
  
  // Add trace ID to response header for debugging
  if (traceId) {
    res.setHeader("X-Trace-Id", traceId);
  }

  return res.status(200).json({
    total: iconNames.length,
    success: results.success,
    failed: results.failed,
    errors: results.errors,
  });
}

