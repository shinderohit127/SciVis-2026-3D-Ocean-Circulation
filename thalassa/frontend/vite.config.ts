import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  optimizeDeps: {
    // maplibre-gl ships its own web worker; exclude from pre-bundling
    exclude: ['maplibre-gl'],
  },
  build: {
    rollupOptions: {
      output: {
        // Keep maplibre in its own chunk to avoid timeouts
        manualChunks: {
          maplibre: ['maplibre-gl'],
          plotly: ['plotly.js', 'react-plotly.js'],
        },
      },
    },
  },
})
