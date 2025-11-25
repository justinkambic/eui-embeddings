# Image Search Frontend Implementation

## Overview

Add image search functionality to the home page that allows users to paste screenshots into the searchbar and see filtered, rendered icon results from Elasticsearch.

## Current State

- Home page has `EuiSearchBar` for text search
- Search API already supports image search (`type: "image"`, `query: base64`)
- Icons are displayed in a grid
- Search results are not currently filtered/displayed

## Implementation

### 1. Enhance Home Page (`frontend/pages/index.tsx`)

**Add image paste/upload functionality:**
- Add image paste handler to searchbar
- Add file input for image upload
- Convert image to base64
- Call search API with image
- Display filtered results

**Key changes:**
- Add state for search results
- Add state for search type (text vs image)
- Add image paste handler
- Add file input handler
- Add search API call
- Filter and display results

### 2. Add Image Search Components

**Create image search UI:**
- Image paste area in searchbar
- Image preview (optional)
- File upload button
- Loading state during search
- Results display with icons

### 3. Update Search Logic

**Modify search behavior:**
- Support both text and image search
- Detect if input is text or image
- Call appropriate search API
- Display results filtered by search

### 4. Display Search Results

**Show filtered icon results:**
- Display matching icons in grid
- Show icon name and score
- Show similarity score (optional)
- Limit results to top matches
- Show "no results" message if empty

## Implementation Details

### Home Page Updates

```typescript
// Add state
const [searchResults, setSearchResults] = useState<string[] | null>(null);
const [searchType, setSearchType] = useState<'text' | 'image'>('text');
const [isSearching, setIsSearching] = useState(false);
const [searchImage, setSearchImage] = useState<string | null>(null);

// Add image paste handler
const handleImagePaste = async (e: ClipboardEvent) => {
  const items = e.clipboardData?.items;
  // Find image item
  // Convert to base64
  // Call search API
  // Update results
};

// Add file upload handler
const handleFileUpload = async (e: ChangeEvent<HTMLInputElement>) => {
  const file = e.target.files?.[0];
  // Convert to base64
  // Call search API
  // Update results
};

// Add search API call
const performImageSearch = async (imageBase64: string) => {
  // Call /api/search with type: "image"
  // Update searchResults state
};
```

### Search Bar Enhancement

- Add image paste support to `EuiSearchBar`
- Add file input for image upload
- Show image preview when image is selected
- Add clear button to reset search

### Results Display

- Filter `iconTypes` based on `searchResults`
- Display matching icons in grid
- Show similarity scores (optional)
- Show "no results" message if empty
- Show loading state during search

## Files to Modify

- `frontend/pages/index.tsx` - Main home page component
  - Add image search state
  - Add image paste/upload handlers
  - Add search API call
  - Update results display

## Optional Enhancements

- Image preview in searchbar
- Drag-and-drop image support
- Clear search button
- Search type toggle (text vs image)
- Similarity score display
- Result count display

## Testing

- Test image paste from clipboard
- Test file upload
- Test search API call
- Test results display
- Test with various image formats
- Test with no results case
- Test loading states