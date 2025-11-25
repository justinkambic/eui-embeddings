/**
 * Unit tests for pages/api/getAllIndexedIcons.ts
 */
import type { NextApiRequest, NextApiResponse } from 'next'
import handler from '../../pages/api/getAllIndexedIcons'

// Helper to create mock request/response
function createMocks(options: { method: string; body?: any }) {
  const req = {
    method: options.method,
    body: options.body,
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

// Mock Elasticsearch client before importing handler
jest.mock('../../client/es', () => ({
  client: {
    search: jest.fn(),
  },
  INDEX_NAME: 'icons',
}))

describe('/api/getAllIndexedIcons', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('should return all indexed icons', async () => {
    const { client } = require('../../client/es')
    client.search.mockResolvedValue({
      aggregations: {
        iconTypes: {
          buckets: [
            { key: 'icon1' },
            { key: 'icon2' }
          ]
        }
      }
    })

    const { req, res } = createMocks({ method: 'GET' })

    await handler(req, res)

    expect(res.status).toHaveBeenCalledWith(200)
    expect(res.json).toHaveBeenCalled()
    const data = JSON.parse(res._getData())
    expect(data).toHaveProperty('iconTypes')
    expect(Array.isArray(data.iconTypes)).toBe(true)
    expect(data.iconTypes).toHaveLength(2)
  })

  it('should handle Elasticsearch errors', async () => {
    const { client } = require('../../client/es')
    client.search.mockRejectedValue(new Error('ES error'))

    const { req, res } = createMocks({ method: 'GET' })

    await handler(req, res)

    expect(res.status).toHaveBeenCalledWith(500)
  })
})

