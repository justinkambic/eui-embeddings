
import { Client } from "@elastic/elasticsearch";

export const client = new Client({
  node: process.env.ELASTICSEARCH_ENDPOINT,
  auth: {
    apiKey: process.env.ELASTICSEARCH_API_KEY,
  },
});

export const INDEX_NAME = "icons";