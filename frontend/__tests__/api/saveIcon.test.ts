/**
 * Unit tests for pages/api/saveIcon.ts
 */
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
import handler from '../../pages/api/saveIcon'

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

// Mock node-fetch
jest.mock('node-fetch', () => {
  const mockFetch = jest.fn()
  return {
    __esModule: true,
    default: mockFetch,
  }
})

import fetch from 'node-fetch'
const mockFetch = fetch as jest.MockedFunction<typeof fetch>

describe('/api/saveIcon', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    process.env.EMBEDDING_SERVICE_URL = 'http://localhost:8000'
    process.env.FRONTEND_API_KEY = 'test-api-key'
  })

  it('should save icon successfully', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ success: true }),
      headers: new Headers({ 'content-type': 'application/json' }),
    })

    const { client } = require('../../client/es')
    client.exists.mockResolvedValue(false)
    client.index.mockResolvedValue({ _id: 'test-icon', result: 'created' })
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ embeddings: [0.1] * 384 }),
    })

    const { req, res } = createMocks('POST', {
      iconName: 'test-icon',
      description: 'Test icon description'
    })

    await handler(req, res)

    expect(res.status).toHaveBeenCalledWith(200)
    expect(mockFetch).toHaveBeenCalled()
  })

  it('should reject non-POST requests', async () => {
    const { req, res } = createMocks('GET')

    await handler(req, res)

    expect(res.status).toHaveBeenCalledWith(405)
  })

  it('should handle missing description', async () => {
    const { client } = require('../../client/es')
    client.exists.mockResolvedValue(false)
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ embeddings: [0.1] * 384 }),
    })

    const { req, res } = createMocks('POST', {
      iconName: 'test-icon'
      // Missing description
    })

    await handler(req, res)

    // Handler doesn't validate description, so it will proceed
    expect(res.status).toHaveBeenCalledWith(200)
  })

  it('should handle API errors', async () => {
    const { client } = require('../../client/es')
    client.exists.mockResolvedValue(false)
    
    mockFetch.mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({ detail: 'Error' }),
      headers: {
        get: jest.fn(() => 'application/json'),
      },
    })

    const { req, res } = createMocks('POST', {
      iconName: 'test-icon',
      description: 'Test'
    })

    await handler(req, res)

    expect(res.status).toHaveBeenCalledWith(500)
  })
})

