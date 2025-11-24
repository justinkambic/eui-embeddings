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
};

module.exports = nextConfig;

