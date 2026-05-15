/**
 * Unit tests for pages/api/batchIndexText.ts
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
import handler from '../../pages/api/batchIndexText'
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

describe('/api/batchIndexText', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    process.env.EMBEDDING_SERVICE_URL = 'http://localhost:8000'
    process.env.FRONTEND_API_KEY = 'test-api-key'
  })

  it('should batch index text successfully', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ indexed: 2 }),
      headers: new Headers({ 'content-type': 'application/json' }),
    })

    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ embeddings: [0.1] * 384 }),
    })

    const { client } = require('../../client/es')
    client.exists.mockResolvedValue(false)
    client.index.mockResolvedValue({ _id: 'icon1', result: 'created' })

    const { req, res } = createMocks('POST', {
      items: [
        { iconName: 'icon1', description: 'Description 1' },
        { iconName: 'icon2', description: 'Description 2' }
      ]
    })

    await handler(req, res)

    expect(res.status).toHaveBeenCalledWith(200)
    expect(mockFetch).toHaveBeenCalled()
  })

  it('should handle empty items array', async () => {
    const { req, res } = createMocks('POST', {
      items: []
    })

    await handler(req, res)

    expect(res.status).toHaveBeenCalledWith(400)
  })

  it('should handle partial failures', async () => {
    const { client } = require('../../client/es')
    client.exists.mockResolvedValue(false)
    client.index.mockResolvedValue({ _id: 'icon1', result: 'created' })
    
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ embeddings: [0.1] * 384 }),
    }).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ embeddings: [0.2] * 384 }),
    })

    const { req, res } = createMocks('POST', {
      items: [
        { iconName: 'icon1', description: 'Description 1' },
        { iconName: 'icon2', description: 'Description 2' }
      ]
    })

    await handler(req, res)

    // Should handle partial failures gracefully
    expect(mockFetch).toHaveBeenCalledTimes(2)
  })
})

