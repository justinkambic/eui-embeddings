import type { NextApiRequest, NextApiResponse } from "next";
import { client, INDEX_NAME } from "../../client/es";

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  const esEndpoint = process.env.ELASTICSEARCH_ENDPOINT;

  try {
    const esRes = await client.search({
      index: INDEX_NAME,
      size: 0,
      body: {
        aggregations: {
          iconTypes: {
            terms: { field: "_id", size: 10000 },
          },
        },
      },
    });
    const buckets = (esRes.aggregations?.iconTypes as any)?.buckets || [];
    const iconTypes = buckets.map((b: any) => b.key);
    res.status(200).json({ iconTypes });
  } catch (e: any) {
    res.status(500).json({ error: e.message || "Failed to fetch iconTypes" });
  }
}
