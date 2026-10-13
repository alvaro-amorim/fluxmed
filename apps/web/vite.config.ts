import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

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
      '/api': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.ts',
    include: ['src/**/*.test.{ts,tsx}'],
  },
})
