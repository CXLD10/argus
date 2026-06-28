import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/aois': 'http://localhost:8000',
      '/waterbod': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
      '/ready': 'http://localhost:8000',
      '/status': 'http://localhost:8000',
      '/query': 'http://localhost:8000',
      '/anomaly': 'http://localhost:8000',
    },
  },
})
