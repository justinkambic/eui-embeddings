import type { NextApiRequest, NextApiResponse } from "next";
import fetch from "node-fetch";
import { trace } from "@opentelemetry/api";
import { extractTraceContext, getTraceId, injectTraceContext } from "../../lib/traceContext";

const tracer = trace.getTracer("eui-frontend-api");

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

  // Forward request to Python API
  const searchApiUrl =
    process.env.EMBEDDING_SERVICE_URL || "http://localhost:8000";
  
  // Extract trace context from incoming request headers (from RUM or other services)
  const extractedContext = extractTraceContext(req);
  
  // Create span for search operation within the extracted trace context
  const span = tracer.startSpan("api.search", {
    attributes: {
      "search.type": type,
      "search.has_icon_type": !!icon_type,
      "search.has_fields": !!(fields && fields.length > 0),
      "http.method": req.method || "POST",
      "http.route": "/api/search",
    },
  }, extractedContext);
  
  // Add trace ID to span attributes for easier correlation
  const traceId = getTraceId();
  if (traceId) {
    span.setAttribute("trace.id", traceId);
  }

  if (icon_type) {
    span.setAttribute("search.icon_type", icon_type);
  }
  if (fields && fields.length > 0) {
    span.setAttribute("search.fields", fields.join(","));
  }

  try {
    const searchUrl = `${searchApiUrl}/search`;

    // Get API key from environment variable
    const apiKey = process.env.FRONTEND_API_KEY;
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (apiKey) {
      headers["X-API-Key"] = apiKey;
    }
    
    // Inject trace context into headers for propagation to Python API
    // FetchInstrumentation should handle this automatically, but we ensure it's done
    injectTraceContext(headers);

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
      
      // Record error in span
      span.setAttribute("http.status_code", response.status);
      span.recordException(new Error(errorData.detail || errorData.error || "Search failed"));
      span.setStatus({ code: 2, message: errorData.detail || errorData.error || "Search failed" }); // ERROR
      span.end();
      
      return res.status(response.status).json({
        error: errorData.detail || errorData.error || "Search failed",
      });
    }

    const data = await response.json() as { results?: any[]; total?: number | { value?: number } };
    
    // Set span attributes for successful response
    span.setAttribute("http.status_code", 200);
    span.setAttribute("search.result_count", data.results?.length || 0);
    span.setAttribute("search.total_results", typeof data.total === 'object' ? data.total?.value || 0 : (data.total || 0));
    span.setStatus({ code: 1 }); // OK
    span.end();
    
    // Add trace ID to response header for debugging (optional)
    if (traceId) {
      res.setHeader("X-Trace-Id", traceId);
    }
    
    return res.status(200).json(data);
  } catch (error: any) {
    console.error("Search proxy error:", error);
    
    // Record error in span
    span.recordException(error);
    span.setStatus({ code: 2, message: error.message || "Search failed" }); // ERROR
    span.end();

    // Provide more detailed error messages
    let errorMessage = "Search failed";
    if (error.code === "ECONNREFUSED") {
      errorMessage = `Cannot connect to Python API at ${searchApiUrl}. Make sure the Python API is running.`;
    } else if (error.code === "ETIMEDOUT") {
      errorMessage = `Connection to Python API timed out. The API may be overloaded or not responding.`;
    } else if (error.message) {
      errorMessage = error.message;
    } else if (typeof error === "string") {
      errorMessage = error;
    }

    return res.status(500).json({
      error: errorMessage,
      details: error.code || "Unknown error",
      pythonApiUrl: searchApiUrl,
    });
  }
}
