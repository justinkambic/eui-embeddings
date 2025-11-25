# Tests

This directory contains test files for the EUI Icon Embeddings project.

## Directory Structure

```
tests/
├── unit/              # Unit tests
│   └── python/        # Python unit tests
├── integration/       # Integration tests
└── phase/            # Phase-specific tests
```

## Test Types

- **Unit Tests** (`unit/`) - Fast, isolated tests for individual functions and components
- **Integration Tests** (`integration/`) - Tests that verify core functionality with real services
- **Phase Tests** (`phase/`) - Phase-specific implementation tests (kept for regression testing)

## Running Tests

### Python Unit Tests

```bash
# Run all unit tests
pytest tests/unit/python/

# Run with coverage
pytest tests/unit/python/ --cov=. --cov-report=html

# Run specific test file
pytest tests/unit/python/test_embed.py

# Run using test script
./scripts/test/run-python-tests.sh
```

### Frontend Tests

```bash
cd frontend
npm test
npm run test:coverage

# Or using test script
./scripts/test/run-frontend-tests.sh
```

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

### Unit Tests

Fast, isolated tests that mock external dependencies:
- **Python**: FastAPI endpoints, utility functions, OpenTelemetry config
- **Frontend**: React components, Next.js API routes, utility functions

### Integration Tests

These tests verify core functionality with real services:
- Elasticsearch index setup and configuration
- Search functionality (text, image, SVG)
- MCP server functionality

### Phase Tests

These tests verify phase-specific implementations:
- HTTPS/SSL configuration
- API key authentication
- Rate limiting

## Test Coverage Goals

- **Python**: 80%+ coverage for core modules (`embed.py`, utilities)
- **Frontend**: 80%+ coverage for components and API routes

## Documentation

See [docs/testing.md](../docs/testing.md) for detailed testing guide including:
- How to write tests
- Testing best practices
- Mocking strategies
- Troubleshooting

## Notes

- Unit tests use mocked dependencies and don't require live services
- Integration tests may require live services to be running
- Some tests may make actual API calls
- Check individual test files for specific requirements

