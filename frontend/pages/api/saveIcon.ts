import type { NextApiRequest, NextApiResponse } from "next";
import fs from "fs";
import path from "path";
import fetch from "node-fetch";
import { trace } from "@opentelemetry/api";
import { extractTraceContext, getTraceId, injectTraceContext } from "../../lib/traceContext";
import { client, INDEX_NAME } from "../../client/es";

const tracer = trace.getTracer("eui-frontend-api");

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method === "POST") {
    if (!client) {
      return res.status(500).json({ error: "Elasticsearch client not configured" });
    }

    const { iconName, description } = req.body;

    console.log("icon, description", iconName, description);
    
    // Extract trace context from incoming request headers (from RUM or other services)
    const extractedContext = extractTraceContext(req);
    
    // Create span for save operation within the extracted trace context
    const span = tracer.startSpan("api.saveIcon", {
      attributes: {
        "icon.name": iconName,
        "icon.description_length": description?.length || 0,
        "http.method": req.method || "POST",
        "http.route": "/api/saveIcon",
      },
    }, extractedContext);
    
    // Add trace ID to span attributes for easier correlation
    const traceId = getTraceId();
    if (traceId) {
      span.setAttribute("trace.id", traceId);
    }
    
    const embeddingServiceUrl = process.env.EMBEDDING_SERVICE_URL || "http://localhost:8000";
    const apiKey = process.env.FRONTEND_API_KEY;
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (apiKey) {
      headers["X-API-Key"] = apiKey;
    }
    
    // Inject trace context into headers for propagation to Python API
    // FetchInstrumentation should handle this automatically, but we ensure it's done
    injectTraceContext(headers);
    
    const [exists, embeddingsRes] = await Promise.all([
      client.exists({ index: INDEX_NAME, id: iconName }),
      fetch(`${embeddingServiceUrl}/embed`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          content: description,
        }),
      }),
    ]);
    console.log("exists", exists);
    if (!embeddingsRes.ok) {
      console.error("Error fetching embeddings:", embeddingsRes.statusText);
      
      // Record error in span
      span.setAttribute("embedding.fetch_failed", true);
      span.recordException(new Error(`Failed to fetch embeddings: ${embeddingsRes.statusText}`));
      span.setStatus({ code: 2, message: "Failed to fetch embeddings" }); // ERROR
      span.end();
      
      return res
        .status(500)
        .json({ error: "Failed to fetch embeddings from the service" });
    }
    const responseData = await embeddingsRes.json() as {
      embeddings: number[];
      sparse_embeddings?: Record<string, number>;
    };
    const { embeddings, sparse_embeddings } = responseData;
    console.log("embeddings data:", embeddings);

    const document: {
      icon_name: string;
      descriptions: string[];
      text_embedding: number[];
      text_embedding_sparse?: Record<string, number>;
    } = {
      icon_name: iconName,
      descriptions: [description],
      text_embedding: embeddings,
    };

    if (sparse_embeddings) {
      document.text_embedding_sparse = sparse_embeddings;
    }

    if (exists) {
      const esResponse = await client.get({
        index: INDEX_NAME,
        id: iconName,
      }) as { _source?: {
        descriptions?: string[];
        text_embedding?: number[];
        text_embedding_sparse?: Record<string, number>;
      }};
      const existingDescriptions = esResponse._source?.descriptions || [];
      // Merge descriptions if needed
      const allDescriptions = Array.isArray(existingDescriptions) 
        ? [...existingDescriptions, description]
        : [description];
      
      document.descriptions = allDescriptions;
      
      await client.update({
        index: INDEX_NAME,
        id: iconName,
        doc: document,
        doc_as_upsert: true,
      });
      console.log("doc updated:", JSON.stringify(esResponse));
    } else {
      const indexPayload = {
        index: INDEX_NAME,
        id: iconName,
        document: document,
      };
      await client.index(indexPayload);
    }
    
    // Set span attributes for successful save
    span.setAttribute("elasticsearch.operation", exists ? "update" : "index");
    span.setAttribute("http.status_code", 200);
    span.setStatus({ code: 1 }); // OK
    span.end();
    
    // Add trace ID to response header for debugging (optional)
    if (traceId) {
      res.setHeader("X-Trace-Id", traceId);
    }
    
    // const [esRes, embeddingsRes] = await Promise.all([
    //   client.get({ index: "icons", id: iconName }).catch((e) => {
    //     console.error("Elasticsearch get error:", e);
    //     return null;
    //   }),
    //   fetch("http://localhost:8000/embed", {
    //     method: "POST",
    //     headers: { "Content-Type": "application/json" },
    //     body: JSON.stringify({
    //       sentences: ["The quick brown fox", "jumps over the lazy dog"],
    //     }),
    //   }),
    // ]);

    // const elasticsearchResponse = await esRes.json();

    // console.log('es data:', elasticsearchResponse);

    // const filePath = path.join(process.cwd(), "data", "icons.json");
    // let data = {};
    // if (fs.existsSync(filePath)) {
    //   data = JSON.parse(fs.readFileSync(filePath, "utf8"));
    // }

    // // Save/merge new description
    // (data as any)[iconName] = description;
    // fs.writeFileSync(filePath, JSON.stringify(data, null, 2));

    return res.status(200).json({ success: true });
  }

  // Extract trace context even for non-POST requests
  const extractedContext = extractTraceContext(req);
  const span = tracer.startSpan("api.saveIcon", {
    attributes: {
      "http.method": req.method || "GET",
      "http.route": "/api/saveIcon",
    },
  }, extractedContext);
  span.setStatus({ code: 2, message: "Method not allowed" }); // ERROR
  span.end();
  
  return res.status(405).json({ error: "Method not allowed" });
}
