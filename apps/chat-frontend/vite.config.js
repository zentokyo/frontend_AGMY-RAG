import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const port = Number(process.env.VITE_DEV_PORT || process.env.PORT || 5174)
const hmr = process.env.VITE_HMR_PATH
  ? {
      clientPort: Number(process.env.VITE_HMR_CLIENT_PORT || port),
      path: process.env.VITE_HMR_PATH,
    }
  : undefined

export default defineConfig({
  base: process.env.VITE_BASE || '/',
  plugins: [react()],
  server: {
    host: process.env.VITE_HOST || '127.0.0.1',
    port,
    strictPort: true,
    hmr,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})
