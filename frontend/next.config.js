/** @type {import('next').NextConfig} */
const nextConfig = {
  // Expose environment variables to the browser (only NEXT_PUBLIC_*)
  env: {
    NEXT_PUBLIC_EMBEDDING_SERVICE_URL: process.env.NEXT_PUBLIC_EMBEDDING_SERVICE_URL,
    NEXT_PUBLIC_FRONTEND_URL: process.env.NEXT_PUBLIC_FRONTEND_URL,
  },
  
  // Server-side environment variables are available via process.env
  // No need to explicitly expose them here
  
  // Production optimizations
  reactStrictMode: true,
  
  // Enable standalone output for Docker
  output: 'standalone',
  
  // Target modern browsers to reduce polyfills and transpilation
  // This tells Next.js to only transpile for browsers that support ES2020+
  compiler: {
    // Remove console.log in production
    removeConsole: process.env.NODE_ENV === 'production' ? {
      exclude: ['error', 'warn'],
    } : false,
  },
  
  // Configure SWC to target modern browsers
  swcMinify: true,
};

