import type { NextApiRequest, NextApiResponse } from "next";
import fs from "fs";
import path from "path";
import fetch from "node-fetch";
import { client, INDEX_NAME } from "../../client/es";

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method === "POST") {
    const { iconName, description } = req.body;

    console.log("icon, description", iconName, description);
    
    const embeddingServiceUrl = process.env.EMBEDDING_SERVICE_URL || "http://localhost:8000";
    const apiKey = process.env.FRONTEND_API_KEY;
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (apiKey) {
      headers["X-API-Key"] = apiKey;
    }
    
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
      return res
        .status(500)
        .json({ error: "Failed to fetch embeddings from the service" });
    }
    const { embeddings, sparse_embeddings } = (await embeddingsRes.json()) as {
      embeddings: number[];
      sparse_embeddings?: Record<string, number>;
    };
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
      const esResponse = await client.get<{
        descriptions: string[];
        text_embedding: number[];
        text_embedding_sparse?: Record<string, number>;
      }>({
        index: INDEX_NAME,
        id: iconName,
      });
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

  return res.status(405).json({ error: "Method not allowed" });
}
