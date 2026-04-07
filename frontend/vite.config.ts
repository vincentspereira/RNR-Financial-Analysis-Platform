import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    // Bundle optimization
    rollupOptions: {
      output: {
        manualChunks: {
          // Vendor chunks for better caching
          'react-vendor': ['react', 'react-dom'],
          'router-vendor': ['react-router-dom'],
          'query-vendor': ['@tanstack/react-query'],
          'chart-vendor': ['chart.js', 'react-chartjs-2'],
          'ui-vendor': ['@headlessui/react', 'lucide-react'],
          'form-vendor': ['react-hook-form', '@hookform/resolvers', 'zod'],
          'utils-vendor': ['date-fns', 'clsx', 'tailwind-merge'],
        },
      },
    },
    // Optimize chunk size
    chunkSizeWarningLimit: 1000,
    // Source maps only in development
    sourcemap: process.env.NODE_ENV !== 'production',
    // Minification
    minify: 'esbuild',
    // Asset optimization
    assetsInlineLimit: 4096, // Inline assets smaller than 4kb
  },
  // Development server optimization
  server: {
    port: 3030,
    host: true,
    // Enable HTTP/2 for better performance
    https: false, // Set to true with certificates for HTTPS
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
    },
  },
  // Preview server configuration
  preview: {
    port: 3030,
    host: true,
  },
  // CSS optimization
  css: {
    devSourcemap: true,
  },
  // Test configuration
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/tests/setup.tsx'],
    css: true,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'src/tests/',
        '**/*.d.ts',
        '**/*.config.*',
        '**/coverage/**',
      ],
    },
  },
  // Performance optimizations
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      'react-router-dom',
      '@tanstack/react-query',
      'chart.js',
      'react-chartjs-2',
      '@headlessui/react',
      'lucide-react',
      'react-hook-form',
      '@hookform/resolvers',
      'zod',
      'date-fns',
      'clsx',
      'tailwind-merge',
    ],
  },
  // Define environment variables
  define: {
    __APP_VERSION__: JSON.stringify(process.env.npm_package_version),
    __BUILD_TIME__: JSON.stringify(new Date().toISOString()),
  },
})