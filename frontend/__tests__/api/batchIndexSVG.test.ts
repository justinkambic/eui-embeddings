/**
 * Unit tests for pages/api/batchIndexSVG.ts
 */
// Mock uuid before importing handler to avoid ESM issues
jest.mock('uuid', () => ({
  v4: jest.fn(() => 'mock-uuid'),
  v1: jest.fn(() => 'mock-uuid'),
}))

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
  createContextKey: jest.fn(() => Symbol('context-key')),
  context: {
    active: jest.fn(() => ({})),
    with: jest.fn((ctx, fn) => fn()),
  },
}))

// Mock Elasticsearch client before importing handler
jest.mock('../../client/es', () => ({
  client: {
    exists: jest.fn(),
    index: jest.fn(),
  },
  INDEX_NAME: 'icons',
}))

import type { NextApiRequest, NextApiResponse } from 'next'
import handler from '../../pages/api/batchIndexSVG'
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
  
  const res = {
    status: jest.fn().mockReturnThis(),
    json: jest.fn().mockReturnThis(),
    setHeader: jest.fn(),
    _getStatusCode: function() { return this.status.mock.results[0]?.value },
    _getData: function() { return JSON.stringify(this.json.mock.calls[0]?.[0] || {}) },
  } as unknown as NextApiResponse
  
  return { req, res }
}

describe('/api/batchIndexSVG', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    process.env.EMBEDDING_SERVICE_URL = 'http://localhost:8000'
    process.env.FRONTEND_API_KEY = 'test-api-key'
  })

  it('should batch index SVG successfully', async () => {
    const { client } = require('../../client/es')
    client.exists.mockResolvedValue(false)
    client.index.mockResolvedValue({ _id: 'icon1', result: 'created' })
    
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ embeddings: [0.3] * 512 }),
    })

    const { req, res } = createMocks('POST', {
      iconNames: ['icon1', 'icon2']
    })

    await handler(req, res)

    expect(res.status).toHaveBeenCalledWith(200)
    expect(mockFetch).toHaveBeenCalled()
  })

  it('should handle empty iconNames array', async () => {
    const { req, res } = createMocks('POST', {
      iconNames: []
    })

    await handler(req, res)

    expect(res.status).toHaveBeenCalledWith(400)
  })
})

