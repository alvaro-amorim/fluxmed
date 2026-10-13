import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// Browser requests remain same-origin, including auth cookies and the GA SSE stream.
// Docker Compose can point the Vite proxy at the API service via the container network.
const apiProxyTarget = process.env.FLUXMED_API_PROXY_TARGET || 'http://localhost:8000'

export default defineConfig({
  envDir: '../..',
  plugins: [react()],
  optimizeDeps: {
    // MapLibre v6 ships an ESM worker that Vite's dependency optimizer can prebundle
    // incorrectly, leaving GeoJSON style layers blank while DOM markers still render.
    exclude: ['maplibre-gl'],
  },
  server: {
    proxy: {
      '/api': apiProxyTarget,
      '/health': apiProxyTarget,
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.ts',
    include: ['src/**/*.test.{ts,tsx}'],
  },
})
