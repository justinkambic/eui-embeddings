const nextJest = require('next/jest')

const createJestConfig = nextJest({
  // Provide the path to your Next.js app to load next.config.js and .env files in your test environment
  dir: './',
})

// Add any custom config to be passed to Jest
const customJestConfig = {
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  testEnvironment: 'jest-environment-jsdom',
  moduleNameMapper: {
    // Handle module aliases (if you use them in your project)
    '^@/(.*)$': '<rootDir>/$1',
    // Mock node-fetch to avoid ESM issues
    '^node-fetch$': '<rootDir>/__mocks__/node-fetch.js',
    // Handle CSS imports (with CSS modules)
    '^.+\\.module\\.(css|sass|scss)$': 'identity-obj-proxy',
    // Handle CSS imports (without CSS modules)
    '^.+\\.(css|sass|scss)$': '<rootDir>/__mocks__/styleMock.js',
    // Handle image imports
    '^.+\\.(png|jpg|jpeg|gif|webp|avif|ico|bmp|svg)$/i': '<rootDir>/__mocks__/fileMock.js',
  },
  testPathIgnorePatterns: [
    '<rootDir>/.next/', 
    '<rootDir>/node_modules/',
    '<rootDir>/__tests__/utils/test-helpers.tsx',
  ],
  transformIgnorePatterns: [
    'node_modules/(?!(uuid|@elastic/eui|node-fetch)/)',
  ],
  collectCoverageFrom: [
    'pages/**/*.{js,jsx,ts,tsx}',
    'components/**/*.{js,jsx,ts,tsx}',
    'lib/**/*.{js,jsx,ts,tsx}',
    'utils/**/*.{js,jsx,ts,tsx}',
    '!**/*.d.ts',
    '!**/node_modules/**',
    '!**/.next/**',
    // Exclude Next.js-specific files that are hard to test in Jest
    '!pages/_app.tsx',
    '!pages/_document.tsx',
    // Exclude browser-only RUM code that doesn't work in Jest environment
    '!lib/rum.ts',
    // Exclude dynamic route pages that require complex setup
    '!pages/icon/**',
  ],
  coverageThreshold: {
    global: {
      branches: 70, // Lower threshold due to complex conditional logic in API routes and components
      functions: 70,
      lines: 70,
      statements: 70,
    },
  },
}

// createJestConfig is exported this way to ensure that next/jest can load the Next.js config which is async
module.exports = createJestConfig(customJestConfig)

