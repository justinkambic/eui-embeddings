import { useState } from "react";
import {
  EuiButtonEmpty,
  EuiCopy,
  EuiFlexGrid,
  EuiFlexGroup,
  EuiFlexItem,
  EuiIcon,
  EuiLink,
  EuiPanel,
  EuiSearchBar,
} from "@elastic/eui";
import { css } from "@emotion/react";
import PageTemplate from "../components/pageTemplate";
import { GetServerSideProps } from "next";
import { client, INDEX_NAME } from "../client/es";

type HomePageProps = {
  iconTypes: string[];
};

export default function HomePage({ iconTypes }: HomePageProps) {
  const [searchTerm, setSearchTerm] = useState<string | null>(null);
  return (
    <PageTemplate>
      <EuiSearchBar
        box={{ placeholder: "Search for icons..." }}
        onChange={({ query }) => {
          setSearchTerm(query?.text || "");
        }}
      />
      <EuiFlexGrid
        alignItems="stretch"
        columns={4}
        gutterSize="l"
        style={{ marginTop: 24 }}
      >
        {iconTypes.map((iconType) => (
          <EuiFlexItem key={iconType}>
            <EuiCopy
              textToCopy={iconType}
              afterMessage={`${iconType} copied`}
              tooltipProps={{ display: "block" }}
            >
              {(copy) => (
                <EuiPanel hasShadow={false} hasBorder={false} paddingSize="s">
                  <EuiIcon
                    className="eui-alignMiddle"
                    type={iconType}
                    size="xl"
                  />{" "}
                  &emsp;{" "}
                  <EuiLink href={`/icon/${iconType}`}>{iconType}</EuiLink>
                </EuiPanel>
              )}
            </EuiCopy>
          </EuiFlexItem>
        ))}
      </EuiFlexGrid>
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
