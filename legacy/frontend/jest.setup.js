// Learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom'

// Mock Next.js router
jest.mock('next/router', () => ({
  useRouter() {
    return {
      route: '/',
      pathname: '/',
      query: {},
      asPath: '/',
      push: jest.fn(),
      pop: jest.fn(),
      reload: jest.fn(),
      back: jest.fn(),
      prefetch: jest.fn().mockResolvedValue(undefined),
      beforePopState: jest.fn(),
      events: {
        on: jest.fn(),
        off: jest.fn(),
        emit: jest.fn(),
      },
      isFallback: false,
      isLocaleDomain: false,
      isReady: true,
      defaultLocale: 'en',
      domainLocales: [],
      isPreview: false,
    }
  },
}))

// Mock Next.js Image component
jest.mock('next/image', () => ({
  __esModule: true,
  default: (props) => {
    // eslint-disable-next-line @next/next/no-img-element, jsx-a11y/alt-text
    return <img {...props} />
  },
}))

// Mock window.performance for performance marks
Object.defineProperty(window, 'performance', {
  value: {
    mark: jest.fn(),
    measure: jest.fn(),
    getEntriesByName: jest.fn(() => []),
    now: jest.fn(() => Date.now()),
  },
  writable: true,
})

// Polyfill TextEncoder/TextDecoder for Node.js environment
import { TextEncoder, TextDecoder } from 'util'
global.TextEncoder = TextEncoder
global.TextDecoder = TextDecoder

// Polyfill ReadableStream for Node.js environment (needed for undici/Elasticsearch client)
if (typeof ReadableStream === 'undefined') {
  try {
    const { ReadableStream: NodeReadableStream } = require('stream/web')
    global.ReadableStream = NodeReadableStream
  } catch (e) {
    // Fallback for older Node versions
    global.ReadableStream = class ReadableStream {
      constructor(underlyingSource = {}) {
        this._underlyingSource = underlyingSource
      }
      getReader() {
        return {
          read: () => Promise.resolve({ done: true, value: undefined }),
          cancel: (reason) => Promise.resolve(),
          releaseLock: () => {},
          closed: Promise.resolve(),
        }
      }
      cancel(reason) {
        return Promise.resolve()
      }
    }
  }
}

// Mock fetch globally
global.fetch = jest.fn()

// Setup fetch mock defaults
beforeEach(() => {
  fetch.mockClear()
})

