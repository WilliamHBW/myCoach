import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    open: true,
    proxy: {
      // Proxy Intervals.icu API requests to Node.js server
      '/api/intervals': {
        target: 'http://localhost:3001',
        changeOrigin: true,
      },
      // Proxy webhook requests to Node.js server
      '/webhook': {
        target: 'http://localhost:3001',
        changeOrigin: true,
      },
      // Proxy all other API requests to Python backend
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  css: {
    preprocessorOptions: {
      scss: {
        api: 'modern-compiler',
      },
    },
  },
})
