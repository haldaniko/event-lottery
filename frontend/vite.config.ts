import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const appBase = '/event-lottery/'
const backend = 'http://127.0.0.1:8000'
const stripAppBase = (path: string) => path.replace(/^\/event-lottery/, '')

export default defineConfig({
  plugins: [react()],
  base: appBase,
  server: {
    proxy: {
      '/event-lottery/api': { target: backend, rewrite: stripAppBase },
      '/event-lottery/admin': { target: backend, rewrite: stripAppBase },
      '/event-lottery/static': { target: backend, rewrite: stripAppBase },
      '/admin': backend,
      '/static': backend,
    },
  },
})

