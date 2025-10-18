/** @type {import('next').NextConfig} */
const nextConfig = {
  // Performance optimizations
  swcMinify: true,
  compiler: {
    // Remove console.logs in production
    removeConsole: process.env.NODE_ENV === "production",
  },
  
  experimental: {
    appDir: true,
    // Enable modern bundling optimizations
    optimizePackageImports: ['lucide-react', 'framer-motion'],
  },
  
  // Use src directory
  pageExtensions: ['tsx', 'ts', 'jsx', 'js'],
  
  // Optimized image configuration
  images: {
    formats: ['image/webp', 'image/avif'],
    domains: [
      's.gravatar.com',
      'lh3.googleusercontent.com', 
      'avatars.githubusercontent.com',
      'platform-lookaside.fbsbx.com'
    ],
  },

  // Bundle optimization
  webpack: (config, { dev, isServer }) => {
    // Optimize bundle splitting for better loading
    if (!dev && !isServer) {
      config.optimization.splitChunks = {
        ...config.optimization.splitChunks,
        cacheGroups: {
          ...config.optimization.splitChunks.cacheGroups,
          animations: {
            name: 'animations',
            chunks: 'all',
            test: /[\\/]node_modules[\\/](framer-motion)[\\/]/,
            priority: 30,
            reuseExistingChunk: true,
          },
          icons: {
            name: 'icons', 
            chunks: 'all',
            test: /[\\/]node_modules[\\/](lucide-react)[\\/]/,
            priority: 25,
            reuseExistingChunk: true,
          },
        },
      };
    }
    
    return config;
  },
}

module.exports = nextConfig