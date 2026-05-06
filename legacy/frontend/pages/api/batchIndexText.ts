import type { NextApiRequest, NextApiResponse } from "next";
import { client, INDEX_NAME } from "../../client/es";
import fetch from "node-fetch";
import { trace } from "@opentelemetry/api";
import { extractTraceContext, getTraceId, injectTraceContext } from "../../lib/traceContext";
import { verifyAdminAuth } from "../../lib/auth";
import { rateLimit } from "../../lib/rateLimit";

const tracer = trace.getTracer("eui-frontend-api");

interface TextIndexItem {
  iconName: string;
  description: string;
}

interface BatchIndexTextRequest {
  items: TextIndexItem[];
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

  const { items }: BatchIndexTextRequest = req.body;

  if (!items || !Array.isArray(items) || items.length === 0) {
    return res.status(400).json({ error: "Missing or empty 'items' array" });
  }

  // Extract trace context from incoming request headers
  const extractedContext = extractTraceContext(req);
  const span = tracer.startSpan("api.batchIndexText", {
    attributes: {
      "batch.size": items.length,
      "http.method": req.method || "POST",
      "http.route": "/api/batchIndexText",
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

  // Process items in batches to avoid overwhelming the API
  const batchSize = 10;
  for (let i = 0; i < items.length; i += batchSize) {
    const batch = items.slice(i, i + batchSize);

    await Promise.all(
      batch.map(async (item) => {
        try {
          // Generate embeddings
          const embeddingServiceUrl = process.env.EMBEDDING_SERVICE_URL || "http://localhost:8000";
          const apiKey = process.env.FRONTEND_API_KEY;
          const headers: Record<string, string> = { "Content-Type": "application/json" };
          if (apiKey) {
            headers["X-API-Key"] = apiKey;
          }
          
          // Inject trace context for propagation to Python API
          injectTraceContext(headers);
          
          const embedRes = await fetch(`${embeddingServiceUrl}/embed`, {
            method: "POST",
            headers,
            body: JSON.stringify({ content: item.description }),
          });

          if (!embedRes.ok) {
            throw new Error(`Embedding generation failed: ${embedRes.statusText}`);
          }

          const responseData = await embedRes.json() as { 
            embeddings: number[]; 
            sparse_embeddings?: Record<string, number> 
          };
          const { embeddings, sparse_embeddings } = responseData;

          // Check if document exists
          const exists = await client.exists({
            index: INDEX_NAME,
            id: item.iconName,
          });

          const document: any = {
            icon_name: item.iconName,
            text_embedding: embeddings,
            descriptions: [item.description],
          };

          if (sparse_embeddings) {
            document.text_embedding_sparse = sparse_embeddings;
          }

          if (exists) {
            // Update existing document
            const existingDoc = await client.get({
              index: INDEX_NAME,
              id: item.iconName,
            }) as { _source?: { descriptions?: string[] } };

            const existingDescriptions = existingDoc._source?.descriptions || [];
            const allDescriptions = Array.isArray(existingDescriptions)
              ? [...existingDescriptions, item.description]
              : [item.description];

            document.descriptions = allDescriptions;

            await client.update({
              index: INDEX_NAME,
              id: item.iconName,
              doc: document,
              doc_as_upsert: true,
            });
          } else {
            // Create new document
            await client.index({
              index: INDEX_NAME,
              id: item.iconName,
              document: document,
            });
          }

          results.success++;
        } catch (error: any) {
          results.failed++;
          results.errors.push({
            iconName: item.iconName,
            error: error.message || "Unknown error",
          });
          console.error(`Error indexing ${item.iconName}:`, error);
        }
      })
    );

    // Small delay between batches
    if (i + batchSize < items.length) {
      await new Promise((resolve) => setTimeout(resolve, 100));
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
    total: items.length,
    success: results.success,
    failed: results.failed,
    errors: results.errors,
  });
}

