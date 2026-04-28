import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Порт 5174 — не пересекается с админ-панелью (5173)
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    proxy: {
      '/api': {
        target: 'http://localhost:3001',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})
