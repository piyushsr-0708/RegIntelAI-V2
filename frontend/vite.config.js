import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // Serve the generated dataset directory directly so the app reads the latest
  // frontend_state.json without any manual copy step.
  publicDir: path.resolve(__dirname, '../datasets/frontend'),
  server: {
    port: 5173,
    fs: {
      allow: [path.resolve(__dirname), path.resolve(__dirname, '../datasets/frontend')],
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
