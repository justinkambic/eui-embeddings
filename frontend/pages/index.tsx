import { useState, useEffect, useRef, ChangeEvent } from "react";
import {
  EuiFlexGrid,
  EuiFlexGroup,
  EuiFlexItem,
  EuiIcon,
  EuiSearchBar,
  EuiFilePicker,
  EuiSpacer,
  EuiText,
  EuiLoadingSpinner,
  EuiFieldText,
  EuiImage,
  EuiToken,
  EuiButtonGroup,
  EuiFormRow,
} from "@elastic/eui";
import { css } from "@emotion/react";
import PageTemplate from "../components/pageTemplate";
import { GetServerSideProps } from "next";
import { client, INDEX_NAME } from "../client/es";
import { typeToPathMap } from "../utils/file_to_name";
const getIconName = (icon: string) => {
  return (
    Object.entries(typeToPathMap).find(([key, value]) => value === icon)?.[0] ||
    null
  );
};
type HomePageProps = {
  iconTypes: string[];
};

interface SearchResult {
  icon_name: string;
  score: number;
  descriptions?: string[];
  icon_type?: "icon" | "token";
  release_tag?: string;
}

export default function HomePage({ iconTypes }: HomePageProps) {
  // const [searchTerm, setSearchTerm] = useState<string | null>(null);
  const [searchResults, setSearchResults] = useState<SearchResult[] | null>(
    null
  );
  // const [searchType, setSearchType] = useState<"text" | "image">("text");
  const [isSearching, setIsSearching] = useState(false);
  const [searchImage, setSearchImage] = useState<string | null>(null);
  const [searchImageDataUrl, setSearchImageDataUrl] = useState<string | null>(null);
  const [svgCode, setSvgCode] = useState<string>("");
  const [iconTypeFilter, setIconTypeFilter] = useState<"icon" | "token" | undefined>("icon");
  
  // Convert image file to base64 (for API) and data URL (for display)
  const imageToBase64 = (file: File): Promise<{ base64: string; dataUrl: string }> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const result = reader.result as string;
        // Remove data:image/...;base64, prefix for API
        const base64 = result.split(",")[1];
        // Keep full data URL for display
        const dataUrl = result;
        resolve({ base64, dataUrl });
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  };

  // Perform image search
  const performImageSearch = async (imageBase64: string) => {
    setIsSearching(true);
    try {
      const response = await fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          type: "image",
          query: imageBase64,
          icon_type: iconTypeFilter,
        }),
      });

      if (!response.ok) {
        throw new Error("Search failed");
      }

      const data = await response.json();
      console.log("search results", data);
      setSearchResults(data.results || []);
      // setSearchType("image");
    } catch (error) {
      console.error("Error performing image search:", error);
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  // Perform SVG search
  const performSVGSearch = async (svgContent: string) => {
    if (!svgContent.trim()) {
      setSearchResults(null);
      return;
    }

    setIsSearching(true);
    try {
      const response = await fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          type: "svg",
          query: svgContent,
          icon_type: iconTypeFilter,
        }),
      });

      if (!response.ok) {
        throw new Error("Search failed");
      }

      const data = await response.json();
      console.log("SVG search results", data);
      setSearchResults(data.results || []);
    } catch (error) {
      console.error("Error performing SVG search:", error);
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  // Effect to search when SVG code or icon type filter changes
  useEffect(() => {
    // Debounce SVG search to avoid too many API calls while typing
    const timeoutId = setTimeout(() => {
      if (svgCode.trim()) {
        performSVGSearch(svgCode);
      } else {
        setSearchResults(null);
      }
    }, 500); // 500ms debounce

    return () => clearTimeout(timeoutId);
  }, [svgCode, iconTypeFilter]);

  // Handle image paste
  useEffect(() => {
    const handlePaste = async (e: ClipboardEvent) => {
      const items = e.clipboardData?.items;
      if (!items) return;

      for (let i = 0; i < items.length; i++) {
        const item = items[i];
        if (item.type.indexOf("image") !== -1) {
          e.preventDefault();
          const file = item.getAsFile();
          if (file) {
            const { base64, dataUrl } = await imageToBase64(file);
            setSearchImage(base64);
            setSearchImageDataUrl(dataUrl);
            await performImageSearch(base64);
          }
          break;
        }
      }
    };

    window.addEventListener("paste", handlePaste);
    return () => {
      window.removeEventListener("paste", handlePaste);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [iconTypeFilter]);

  // Handle file upload
  const handleFileUpload = async (files: FileList) => {
    console.log("file upload", files);
    if (!files || files.length === 0) return;

    const file = files[0];

    if (!file.type.startsWith("image/")) {
      alert("Please select an image file");
      return;
    }

    try {
      const { base64, dataUrl } = await imageToBase64(file);
      setSearchImage(base64);
      setSearchImageDataUrl(dataUrl);
      await performImageSearch(base64);
    } catch (error) {
      console.error("Error uploading file:", error);
      alert("Error uploading image");
    }
  };

  // Icon type filter options
  const iconTypeOptions = [
    {
      id: "all",
      label: "All",
    },
    {
      id: "icon",
      label: "Icons",
    },
    {
      id: "token",
      label: "Tokens",
    },
  ];

  const selectedIconTypeId = iconTypeFilter || "icon";

  const handleIconTypeChange = (optionId: string) => {
    if (optionId === "all") {
      setIconTypeFilter(undefined);
    } else {
      setIconTypeFilter(optionId as "icon" | "token");
    }
    
    // Re-trigger search if we have active search
    if (searchImage) {
      performImageSearch(searchImage);
    } else if (svgCode.trim()) {
      performSVGSearch(svgCode);
    }
  };

  return (
    <PageTemplate>
      {/* Icon Type Filter */}
      <EuiFormRow label="Search type" helpText="Filter results by icon type">
        <EuiButtonGroup
          legend="Icon type filter"
          options={iconTypeOptions}
          idSelected={selectedIconTypeId}
          onChange={handleIconTypeChange}
          color="primary"
          isFullWidth
        />
      </EuiFormRow>

      <EuiSpacer size="m" />

      {/*<EuiSearchBar
        box={{ placeholder: "Search for icons..." }}
        onChange={({ query }) => {
          // setSearchTerm(query?.text || "");
          // Reset image search when text search changes
          if (query?.text) {
            setSearchResults(null);
            // setSearchType("text");
            setSearchImage(null);
          }
        }}
      />*/}

      <EuiFieldText
        placeholder="Paste SVG code"
        value={svgCode}
        onChange={(e) => {
          console.log("paste event e");
          return setSvgCode(e.target.value);
        }}
      />

      <EuiSpacer size="m" />

      {/* Image upload option */}
      <EuiFilePicker
        id="image-upload"
        accept="image/*"
        onChange={handleFileUpload}
        display="large"
        fullWidth
        initialPromptText="Upload image"
      />

      {searchImageDataUrl && (
        <>
          <EuiSpacer size="m" />
          <EuiImage
            src={searchImageDataUrl}
            alt="Search image"
            size="l"
            allowFullScreen
          />
          <EuiSpacer size="s" />
          <EuiText size="s" color="subdued">
            Searching with this image...
          </EuiText>
        </>
      )}

      {isSearching && (
        <>
          <EuiSpacer size="m" />
          <EuiLoadingSpinner size="l" />
          <EuiText size="s" color="subdued">
            Searching...
          </EuiText>
        </>
      )}

      {searchResults && !isSearching && (
        <>
          <EuiSpacer size="m" />
          <EuiText>
            <h3>Search Results ({searchResults.length})</h3>
          </EuiText>
        </>
      )}

      <EuiSpacer size="l" />

      {searchResults && searchResults.length > 0 && (
        <EuiFlexGrid columns={4}>
          {searchResults.map((result) => {
            console.log('result', result);
            const iconName = result.icon_name;
            // const iconName = getIconName(result.icon_name);
            // if (!iconName) return null;
            
            return (
              <EuiFlexGroup key={`${iconName}-${result.icon_type || 'unknown'}`} direction="column" gutterSize="s">
                <EuiFlexItem grow={false}>
                  {result.icon_type === "token" ? (
                    <EuiToken iconType={iconName} size="m" />
                  ) : (
                    <EuiIcon type={iconName} size="xl" />
                  )}
                </EuiFlexItem>
                <EuiFlexItem grow={false}>
                  <EuiText size="s">{iconName}</EuiText>
                  {result.icon_type && (
                    <EuiText size="xs" color="subdued">
                      {result.icon_type}
                    </EuiText>
                  )}
                  {result.score && (
                    <EuiText size="xs" color="subdued">
                      Score: {result.score.toFixed(3)}
                    </EuiText>
                  )}
                </EuiFlexItem>
              </EuiFlexGroup>
            );
          })}
        </EuiFlexGrid>
      )}
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
