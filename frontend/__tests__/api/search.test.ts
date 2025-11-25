/**
 * Unit tests for pages/api/search.ts
 */
// Mock node-fetch before importing handler
jest.mock('node-fetch', () => {
  const mockFetch = jest.fn()
  return {
    __esModule: true,
    default: mockFetch,
  }
})

// Mock OpenTelemetry before importing handler
jest.mock('@opentelemetry/api', () => ({
  trace: {
    getTracer: jest.fn(() => ({
      startSpan: jest.fn(() => ({
        setAttribute: jest.fn(),
        recordException: jest.fn(),
        setStatus: jest.fn(),
        end: jest.fn(),
      })),
    })),
  },
}))

import type { NextApiRequest, NextApiResponse } from 'next'
import handler from '../../pages/api/search'
import fetch from 'node-fetch'

// Get the mocked fetch function
const mockFetch = fetch as jest.MockedFunction<typeof fetch>

// Helper to create mock request/response
function createMocks(method: string, body?: any) {
  const req = {
    method,
    body,
    headers: {},
  } as NextApiRequest
  
  let statusCode = 200
  let responseData: any = {}
  
  const res = {
    status: jest.fn((code: number) => {
      statusCode = code
      return res
    }),
    json: jest.fn((data: any) => {
      responseData = data
      return res
    }),
    setHeader: jest.fn(),
    _getStatusCode: () => statusCode,
    _getData: () => JSON.stringify(responseData),
  } as unknown as NextApiResponse
  
  return { req, res }
}

describe('/api/search', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    process.env.EMBEDDING_SERVICE_URL = 'http://localhost:8000'
    process.env.FRONTEND_API_KEY = 'test-api-key'
  })

  afterEach(() => {
    delete process.env.FRONTEND_API_KEY
  })

  it('should handle POST request successfully', async () => {
    const mockResponse = {
      results: [
        { icon_name: 'icon1', score: 0.95 }
      ],
      total: 1
    }
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => mockResponse,
      headers: {
        get: jest.fn(() => 'application/json'),
      },
    })

    const { req, res } = createMocks('POST', {
      type: 'text',
      query: 'test icon'
    })

    await handler(req, res)

    expect(res._getStatusCode()).toBe(200)
    const data = JSON.parse(res._getData())
    expect(data.results).toHaveLength(1)
    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/search',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          'X-API-Key': 'test-api-key'
        })
      })
    )
  })

  it('should reject non-POST requests', async () => {
    const { req, res } = createMocks('GET')

    await handler(req, res)

    expect(res.status).toHaveBeenCalledWith(405)
    const data = JSON.parse(res._getData())
    expect(data.error).toContain('Method not allowed')
  })

  it('should validate required fields', async () => {
    const { req, res } = createMocks('POST', {
      type: 'text'
      // Missing query
    })

    await handler(req, res)

    expect(res.status).toHaveBeenCalledWith(400)
    const data = JSON.parse(res._getData())
    expect(data.error).toContain('Missing')
  })

  it('should forward icon_type parameter', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ results: [], total: 0 }),
      headers: {
        get: jest.fn(() => 'application/json'),
      },
    })

    const { req, res } = createMocks('POST', {
      type: 'text',
      query: 'test',
      icon_type: 'icon'
    })

    await handler(req, res)

    expect(mockFetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        body: expect.stringContaining('"icon_type":"icon"')
      })
    )
  })

  it('should forward fields parameter', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ results: [], total: 0 }),
      headers: {
        get: jest.fn(() => 'application/json'),
      },
    })

    const { req, res } = createMocks('POST', {
      type: 'text',
      query: 'test',
      fields: ['icon_image_embedding', 'icon_svg_embedding']
    })

    await handler(req, res)

    expect(mockFetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        body: expect.stringContaining('"fields"')
      })
    )
  })

  it('should handle API errors', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({ detail: 'Internal server error' }),
      headers: {
        get: jest.fn(() => 'application/json'),
      },
    })

    const { req, res } = createMocks('POST', {
      type: 'text',
      query: 'test'
    })

    await handler(req, res)

    expect(res.status).toHaveBeenCalledWith(500)
    const data = JSON.parse(res._getData())
    expect(data.error).toBeDefined()
  })

  it('should handle fetch errors', async () => {
    mockFetch.mockRejectedValue(new Error('Network error'))

    const { req, res } = createMocks('POST', {
      type: 'text',
      query: 'test'
    })

    await handler(req, res)

    expect(res.status).toHaveBeenCalledWith(500)
    const data = JSON.parse(res._getData())
    expect(data.error).toBeDefined()
  })

  it('should work without API key', async () => {
    delete process.env.FRONTEND_API_KEY
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ results: [], total: 0 }),
      headers: {
        get: jest.fn(() => 'application/json'),
      },
    })

    const { req, res } = createMocks('POST', {
      type: 'text',
      query: 'test'
    })

    await handler(req, res)

    expect(res._getStatusCode()).toBe(200)
    // Should not include X-API-Key header when not set
    expect(mockFetch).toHaveBeenCalled()
  })
})

