/**
 * Test utilities and helpers for React component testing
 */
// Mock uuid before importing EuiProvider to avoid ESM issues
jest.mock('uuid', () => ({
  v4: jest.fn(() => 'mock-uuid'),
  v1: jest.fn(() => 'mock-uuid'),
}))

import React from 'react'
import { render, RenderOptions } from '@testing-library/react'
import { EuiProvider } from '@elastic/eui'
import { CacheProvider, EmotionCache } from '@emotion/react'
import { createEmotionCache } from '../../lib/emotionCache'

// Create a test Emotion cache
const testEmotionCache = createEmotionCache()

interface AllTheProvidersProps {
  children: React.ReactNode
  emotionCache?: EmotionCache
}

const AllTheProviders = ({ children, emotionCache = testEmotionCache }: AllTheProvidersProps) => {
  return (
    <CacheProvider value={emotionCache}>
      <EuiProvider colorMode="light">
        {children}
      </EuiProvider>
    </CacheProvider>
  )
}

const customRender = (
  ui: React.ReactElement,
  options?: Omit<RenderOptions, 'wrapper'> & { emotionCache?: EmotionCache }
) => {
  const { emotionCache, ...renderOptions } = options || {}
  return render(ui, {
    wrapper: ({ children }) => (
      <AllTheProviders emotionCache={emotionCache}>{children}</AllTheProviders>
    ),
    ...renderOptions,
  })
}

// Re-export everything from @testing-library/react
export * from '@testing-library/react'
export { customRender as render }

// Mock data fixtures
export const mockSearchResults = [
  {
    icon_name: 'icon1',
    score: 0.95,
    descriptions: ['test icon 1'],
    icon_type: 'icon',
    release_tag: 'v1.0.0',
  },
  {
    icon_name: 'icon2',
    score: 0.85,
    descriptions: ['test icon 2'],
    icon_type: 'icon',
  },
]

export const mockBase64Image = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='

export const mockSVGContent = '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M12 2L2 7v10l10 5 10-5V7L12 2z"/></svg>'

// Mock fetch responses
export const createMockFetchResponse = (data: any, ok: boolean = true) => {
  return Promise.resolve({
    ok,
    status: ok ? 200 : 500,
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
    headers: new Headers(),
  } as Response)
}

// Mock Next.js router
export const mockRouter = {
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

