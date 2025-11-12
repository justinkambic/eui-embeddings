import type { NextApiRequest, NextApiResponse } from "next";
import { client, INDEX_NAME } from "../../client/es";
import fetch from "node-fetch";

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

  const { items }: BatchIndexTextRequest = req.body;

  if (!items || !Array.isArray(items) || items.length === 0) {
    return res.status(400).json({ error: "Missing or empty 'items' array" });
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
          
          const embedRes = await fetch(`${embeddingServiceUrl}/embed`, {
            method: "POST",
            headers,
            body: JSON.stringify({ content: item.description }),
          });

          if (!embedRes.ok) {
            throw new Error(`Embedding generation failed: ${embedRes.statusText}`);
          }

          const { embeddings, sparse_embeddings } = await embedRes.json();

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
            });

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

  return res.status(200).json({
    total: items.length,
    success: results.success,
    failed: results.failed,
    errors: results.errors,
  });
}

