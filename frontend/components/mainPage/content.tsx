import {
  EuiBasicTable,
  EuiBasicTableColumn,
  EuiCheckboxGroup,
  EuiFieldText,
  EuiFilePicker,
  EuiFlexGroup,
  EuiFlexItem,
  EuiFormRow,
  EuiIcon,
  EuiLoadingSpinner,
  EuiSpacer,
  EuiImage,
  EuiText,
  EuiToken,
  EuiSkeletonText,
} from "@elastic/eui";
import { useState, useEffect, useMemo } from "react";
import type { CriteriaWithPagination } from "@elastic/eui";

// Performance monitoring helpers
const markPerformance = (name: string) => {
  if (typeof window !== 'undefined' && 'performance' in window && 'mark' in window.performance) {
    window.performance.mark(name);
  }
};

const measurePerformance = (name: string, startMark: string, endMark: string) => {
  if (typeof window !== 'undefined' && 'performance' in window && 'measure' in window.performance) {
    try {
      window.performance.measure(name, startMark, endMark);
      const measure = window.performance.getEntriesByName(name)[0];
      if (measure) {
        console.log(`[Performance] ${name}: ${measure.duration.toFixed(2)}ms`);
      }
    } catch (e) {
      // Ignore if marks don't exist
    }
  }
};

interface SearchResult {
  icon_name: string;
  score: number;
  descriptions?: string[];
  icon_type?: "icon" | "token";
  release_tag?: string;
}

export function MainPageContent() {
  // Performance mark: component mount
  useEffect(() => {
    markPerformance('main-page-content-mounted');
    return () => {
      markPerformance('main-page-content-unmounted');
    };
  }, []);

  // const [searchTerm, setSearchTerm] = useState<string | null>(null);
  const [searchResults, setSearchResults] = useState<SearchResult[] | null>(
    null
  );
  // const [searchType, setSearchType] = useState<"text" | "image">("text");
  const [isSearching, setIsSearching] = useState(false);
  const [searchImage, setSearchImage] = useState<string | null>(null);
  const [searchImageDataUrl, setSearchImageDataUrl] = useState<string | null>(
    null
  );
  const [svgCode, setSvgCode] = useState<string>("");
  const [iconTypeFilter, setIconTypeFilter] = useState<
    "icon" | "token" | undefined
  >("icon");

  // Embedding field selection
  type EmbeddingField =
    | "icon_image_embedding"
    | "icon_svg_embedding"
    | "token_image_embedding"
    | "token_svg_embedding";
  const [selectedFields, setSelectedFields] = useState<EmbeddingField[]>([
    "icon_image_embedding",
    "icon_svg_embedding",
  ]);

  // Pagination state
  const [pagination, setPagination] = useState({ pageIndex: 0, pageSize: 50 });

  // Convert image file to base64 (for API) and data URL (for display)
  const imageToBase64 = (
    file: File
  ): Promise<{ base64: string; dataUrl: string }> => {
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
    markPerformance('image-search-start');
    setIsSearching(true);
    try {
      const response = await fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          type: "image",
          query: imageBase64,
          icon_type: iconTypeFilter,
          fields: selectedFields,
        }),
      });

      markPerformance('image-search-response-received');
      measurePerformance('image-search-network-time', 'image-search-start', 'image-search-response-received');

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: "Search failed" }));
        console.error("Search API error:", errorData);
        throw new Error(errorData.error || errorData.detail || "Search failed");
      }

      const data = await response.json();
      markPerformance('image-search-complete');
      measurePerformance('image-search-total-time', 'image-search-start', 'image-search-complete');
      console.log("search results", data);
      setSearchResults(data.results || []);
      // setSearchType("image");
    } catch (error) {
      markPerformance('image-search-error');
      measurePerformance('image-search-error-time', 'image-search-start', 'image-search-error');
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

    markPerformance('svg-search-start');
    setIsSearching(true);
    try {
      const response = await fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          type: "svg",
          query: svgContent,
          icon_type: iconTypeFilter,
          fields: selectedFields,
        }),
      });

      markPerformance('svg-search-response-received');
      measurePerformance('svg-search-network-time', 'svg-search-start', 'svg-search-response-received');

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: "Search failed" }));
        console.error("Search API error:", errorData);
        throw new Error(errorData.error || errorData.detail || "Search failed");
      }

      const data = await response.json();
      markPerformance('svg-search-complete');
      measurePerformance('svg-search-total-time', 'svg-search-start', 'svg-search-complete');
      console.log("SVG search results", data);
      setSearchResults(data.results || []);
    } catch (error) {
      markPerformance('svg-search-error');
      measurePerformance('svg-search-error-time', 'svg-search-start', 'svg-search-error');
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

  // Embedding field options
  const embeddingFieldOptions = [
    {
      id: "icon_image_embedding",
      label: "Icon Image",
    },
    {
      id: "icon_svg_embedding",
      label: "Icon SVG",
    },
    {
      id: "token_image_embedding",
      label: "Token Image",
    },
    {
      id: "token_svg_embedding",
      label: "Token SVG",
    },
  ];

  const handleFieldSelectionChange = (optionId: string) => {
    const field = optionId as EmbeddingField;
    setSelectedFields((prev) => {
      if (prev.includes(field)) {
        // Remove if already selected
        const newFields = prev.filter((f) => f !== field);
        // Ensure at least one field is selected
        return newFields.length > 0 ? newFields : prev;
      } else {
        // Add if not selected
        return [...prev, field];
      }
    });
  };

  // Re-trigger search when fields change
  useEffect(() => {
    if (searchImage) {
      performImageSearch(searchImage);
    } else if (svgCode.trim()) {
      performSVGSearch(svgCode);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedFields]);

  // Define table columns
  const columns: Array<EuiBasicTableColumn<SearchResult>> = useMemo(() => {
    // Determine which columns to show based on selected fields
    const hasIconFields = selectedFields.some(
      (field) => field === "icon_image_embedding" || field === "icon_svg_embedding"
    );
    const hasTokenFields = selectedFields.some(
      (field) =>
        field === "token_image_embedding" || field === "token_svg_embedding"
    );

    const cols: Array<EuiBasicTableColumn<SearchResult>> = [];

    // Conditionally add Icon column
    if (hasIconFields) {
      cols.push({
        name: "Icon",
        width: "80px",
        render: (item: SearchResult) => (
          <EuiIcon type={item.icon_name} size="l" />
        ),
      });
    }

    // Conditionally add Token column
    if (hasTokenFields) {
      cols.push({
        name: "Token",
        width: "80px",
        render: (item: SearchResult) => (
          <EuiToken iconType={item.icon_name} size="m" />
        ),
      });
    }

    // Always show these columns
    cols.push(
      {
        field: "icon_name",
        name: "Icon Name",
      },
      {
        field: "icon_type",
        name: "Type",
        render: (icon_type: string) => icon_type || "icon",
      },
      {
        field: "score",
        name: "Score",
        render: (score: number) => score.toFixed(3),
      },
      {
        field: "release_tag",
        name: "Release",
      }
    );

    return cols;
  }, [selectedFields]);

  // Table change handler
  const onTableChange = ({ page }: CriteriaWithPagination<SearchResult>) => {
    if (page) {
      setPagination({ pageIndex: page.index, pageSize: page.size });
    }
  };
  return (
    <>
      <EuiFlexGroup gutterSize="l">
        <EuiFlexItem>
          <EuiFilePicker
            id="image-upload"
            accept="image/*"
            onChange={handleFileUpload}
            fullWidth
            initialPromptText="Upload image"
          />
          <EuiSpacer size="s" />
          <EuiFieldText
            placeholder="Paste SVG code"
            value={svgCode}
            fullWidth
            onChange={(e) => {
              console.log("paste event e");
              return setSvgCode(e.target.value);
            }}
          />
        </EuiFlexItem>
        <EuiFlexItem>
          {/* Embedding Field Selection */}
          <EuiFormRow
            label="Search Fields"
            helpText="Select which embedding fields to search against"
          >
            <EuiCheckboxGroup
              options={embeddingFieldOptions}
              idToSelectedMap={{
                icon_image_embedding: selectedFields.includes(
                  "icon_image_embedding"
                ),
                icon_svg_embedding:
                  selectedFields.includes("icon_svg_embedding"),
                token_image_embedding: selectedFields.includes(
                  "token_image_embedding"
                ),
                token_svg_embedding: selectedFields.includes(
                  "token_svg_embedding"
                ),
              }}
              onChange={(optionId) => handleFieldSelectionChange(optionId)}
            />
          </EuiFormRow>
        </EuiFlexItem>
        <EuiFlexItem>
          {/* Fixed size container to prevent layout shift */}
          <div
            style={{
              width: 200,
              height: 200,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              minHeight: 200,
            }}
          >
            {searchImageDataUrl && (
              <EuiImage
                src={searchImageDataUrl}
                alt="Search image"
                size="m"
                hasShadow
              />
            )}
            {svgCode.trim() && !searchImageDataUrl && (
              <div
                style={{
                  width: "100%",
                  height: "100%",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  border: "1px solid #d3dae6",
                  borderRadius: "4px",
                  padding: "8px",
                  backgroundColor: "#fff",
                }}
                dangerouslySetInnerHTML={{ __html: svgCode }}
              />
            )}
          </div>
        </EuiFlexItem>
      </EuiFlexGroup>

      {/* Results section with fixed height to prevent layout shift */}
      <div style={{ minHeight: searchResults || isSearching ? '400px' : '0px' }}>
        {isSearching && (
          <>
            <EuiSpacer size="m" />
            <EuiFlexGroup direction="column" alignItems="center">
              <EuiLoadingSpinner size="l" />
              <EuiSpacer size="s" />
              <EuiText size="s" color="subdued">
                Searching...
              </EuiText>
              {/* Skeleton for table while loading */}
              <EuiSpacer size="m" />
              <div style={{ width: '100%' }}>
                <EuiSkeletonText lines={5} />
              </div>
            </EuiFlexGroup>
          </>
        )}

        {searchResults && !isSearching && (
          <>
            <EuiSpacer size="m" />
            <EuiText>
              <h3>Search Results ({searchResults.length})</h3>
            </EuiText>
            <EuiSpacer size="m" />
            {searchResults.length > 0 ? (
              <EuiBasicTable
                items={searchResults}
                columns={columns}
                pagination={{
                  pageIndex: pagination.pageIndex,
                  pageSize: pagination.pageSize,
                  totalItemCount: searchResults.length,
                  pageSizeOptions: [10, 20, 50],
                  showPerPageOptions: true,
                }}
                onChange={onTableChange}
                responsiveBreakpoint={false}
              />
            ) : (
              <EuiText color="subdued">
                No results found. Try a different search.
              </EuiText>
            )}
          </>
        )}
      </div>
    </>
  );
}
