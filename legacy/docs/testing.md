# Testing Guide

This document provides guidance on writing and running tests for the EUI Icon Embeddings project.

## Overview

The project uses two testing frameworks:
- **Python**: pytest for FastAPI endpoints and utility modules
- **Node/React**: Jest with React Testing Library for Next.js API routes and React components

## Python Testing

### Running Tests

```bash
# Run all Python unit tests
pytest tests/unit/python/

# Run with coverage
pytest tests/unit/python/ --cov=. --cov-report=html

# Run specific test file
pytest tests/unit/python/test_embed.py

# Run specific test
pytest tests/unit/python/test_embed.py::TestHealthEndpoint::test_health_endpoint_success
```

### Test Structure

Python tests are organized in `tests/unit/python/`:
- `conftest.py` - Shared fixtures and test configuration
- `test_embed.py` - FastAPI endpoint tests
- `test_image_processor.py` - Image processing utility tests
- `test_svg_processor.py` - SVG processing utility tests
- `test_otel_config.py` - OpenTelemetry configuration tests
- `test_mcp_server.py` - MCP server tests
- `utils/` - Tests for utility scripts

### Writing Python Tests

```python
import pytest
from unittest.mock import Mock, patch

def test_example(client):
    """Test example with fixtures"""
    response = client.get("/health")
    assert response.status_code == 200
```

### Fixtures

Common fixtures available in `conftest.py`:
- `client` - FastAPI test client
- `authenticated_client` - Test client with API key
- `mock_elasticsearch_client` - Mock Elasticsearch client
- `mock_text_model` - Mock text embedding model
- `mock_image_model` - Mock image embedding model
- `sample_svg_content` - Sample SVG string
- `sample_base64_image` - Sample base64 image

## Node/React Testing

### Running Tests

```bash
cd frontend

# Run all tests
npm test

# Run in watch mode
npm run test:watch

# Run with coverage
npm run test:coverage

# Run in CI mode
npm run test:ci
```

### Test Structure

Frontend tests are organized in `frontend/__tests__/`:
- `components/` - React component tests
- `pages/` - Page component tests
- `api/` - Next.js API route tests
- `utils/` - Utility function tests
- `utils/test-helpers.tsx` - Shared test utilities

### Writing React Tests

```typescript
import { render, screen } from '@testing-library/react'
import { MainPageContent } from '../../../components/mainPage/content'

describe('MainPageContent', () => {
  it('should render component', () => {
    render(<MainPageContent />)
    expect(screen.getByText(/EUI Icon/i)).toBeInTheDocument()
  })
})
```

### Test Utilities

Custom render function with providers:
```typescript
import { render } from '../../utils/test-helpers'

render(<Component />) // Automatically wrapped with EuiProvider and CacheProvider
```

Mock data fixtures:
```typescript
import { mockSearchResults, mockBase64Image, mockSVGContent } from '../../utils/test-helpers'
```

## Coverage Goals

- **Python**: 80%+ coverage for core modules (`embed.py`, utilities)
- **React/Node**: 80%+ coverage for components and API routes

## Best Practices

1. **Test Independence**: Each test should be independent and not rely on other tests
2. **Descriptive Names**: Use clear, descriptive test names that explain what is being tested
3. **AAA Pattern**: Follow Arrange, Act, Assert pattern
4. **Test Both Paths**: Test both success and error paths
5. **Edge Cases**: Test edge cases and boundary conditions
6. **Mock External Dependencies**: Mock external services (Elasticsearch, APIs) to keep tests fast and reliable

## Mocking Strategy

### Python
- **Elasticsearch**: Mock `Elasticsearch` client and method calls
- **SentenceTransformer**: Mock model loading and `encode()` methods
- **External APIs**: Mock `requests` calls
- **Environment Variables**: Use pytest fixtures to set test env vars

### Node/React
- **Fetch API**: Mock `global.fetch` or use MSW
- **Next.js Router**: Mock `next/router` (already configured in `jest.setup.js`)
- **Elasticsearch Client**: Mock `@elastic/elasticsearch` client
- **Environment Variables**: Mock `process.env`

## Continuous Integration

Tests should run automatically in CI/CD:
- Python tests: `pytest tests/unit/python/ --cov=. --cov-report=xml`
- Frontend tests: `npm run test:ci`

## Troubleshooting

### Python Tests
- **Import Errors**: Ensure virtual environment is activated
- **Missing Dependencies**: Run `pip install -r requirements.txt`
- **Elasticsearch Connection**: Tests use mocked clients, no real ES needed

### Frontend Tests
- **Module Resolution**: Check `jest.config.js` for module name mapping
- **Emotion CSS**: Already configured in `jest.setup.js`
- **Next.js Modules**: Already mocked in `jest.setup.js`

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [Jest Documentation](https://jestjs.io/)
- [React Testing Library](https://testing-library.com/react)
- [Testing Best Practices](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library)

