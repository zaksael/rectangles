import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/ws': { target: 'ws://localhost:8765', ws: true },
    },
  },
  test: {
    environment: 'jsdom',
    // One jsdom per worker instead of one per file (about half the run time); setupTests cleans up after each test, and a test that leaks global state would show up as an order-dependent failure.
    isolate: false,
    setupFiles: './src/setupTests.ts',
  },
})
