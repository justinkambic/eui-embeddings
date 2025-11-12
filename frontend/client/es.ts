
import { Client } from "@elastic/elasticsearch";

// Initialize Elasticsearch client only if endpoint and API key are provided
const esEndpoint = process.env.ELASTICSEARCH_ENDPOINT;
const esApiKey = process.env.ELASTICSEARCH_API_KEY;

export const client: Client | null = esEndpoint && esApiKey
  ? new Client({
      node: esEndpoint,
      auth: {
        apiKey: esApiKey,
      },
    })
  : null;

export const INDEX_NAME = "icons";