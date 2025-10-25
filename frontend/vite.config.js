import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  base: '/',  // Root path for Central Server
  server: {
    host: '0.0.0.0',  // Allow external connections (for Nginx proxy)
    port: 5173,
    proxy: {
      '/api/user': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        secure: false
      }
    }
  }
})
