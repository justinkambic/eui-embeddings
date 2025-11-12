import PageTemplate from "../components/pageTemplate";
import { GetServerSideProps } from "next";
import { client, INDEX_NAME } from "../client/es";
import { MainPageContent } from "../components/mainPage/content";
type HomePageProps = {
  iconTypes: string[];
};

export default function HomePage({ iconTypes }: HomePageProps) {
  return (
    <PageTemplate>
      <MainPageContent />
    </PageTemplate>
  );
}

export const getServerSideProps: GetServerSideProps = async (context) => {
  try {
    const esRes = await client.search({
      index: INDEX_NAME,
      size: 10000,
      body: {
        query: {
          match_all: {},
        },
      } as any,
    });
    const hits = (esRes.hits.hits as any) || [];
    const iconTypes = hits.map((b: any) => b._id);
    return {
      props: {
        iconTypes,
      },
    };
  } catch (e: any) {
    console.log("error fetching from es", e);
    return {
      props: {
        iconTypes: [],
        error: e.message || "Failed to fetch iconTypes",
      },
    };
  }
};
