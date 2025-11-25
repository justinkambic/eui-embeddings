# Tests

This directory contains test files for the EUI Icon Embeddings project.

## Directory Structure

- `integration/` - Integration tests for core functionality
- `phase/` - Phase-specific tests (kept for regression testing)

## Running Tests

### Integration Tests

```bash
# Test Elasticsearch setup
python tests/integration/test_elasticsearch_setup.py

# Test SVG search
python tests/integration/test_svg_search.py

# Test image search
python tests/integration/test_image_search.py

# Test MCP server
python tests/integration/test_mcp_server.py
```

### Phase Tests

```bash
# Test Phase 3 (HTTPS)
python tests/phase/test_phase3_https.py

# Test Phase 4 (API Keys)
python tests/phase/test_phase4_api_keys.py

# Test Phase 5 (Rate Limiting)
python tests/phase/test_phase5_rate_limiting.py
```

## Prerequisites

Before running tests, ensure:

1. Environment variables are set (see `docs/api/environment-variables.md`)
2. Services are running (if testing against live services)
3. Elasticsearch cluster is accessible
4. Python dependencies are installed: `pip install -r requirements.txt`

## Test Categories

### Integration Tests

These tests verify core functionality:
- Elasticsearch index setup and configuration
- Search functionality (text, image, SVG)
- MCP server functionality

### Phase Tests

These tests verify phase-specific implementations:
- HTTPS/SSL configuration
- API key authentication
- Rate limiting

## Notes

- Some tests require live services to be running
- Some tests may make actual API calls
- Check individual test files for specific requirements

