import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import vercel from './vercel.json'

const headers = Object.fromEntries(vercel.headers.find((rule) => rule.source === '/(.*)')!.headers.map(({ key, value }) => [key, value]))

export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: { manifest: true },
  preview: { headers, strictPort: true },
  test: { environment: 'jsdom', include: ['src/**/*.test.{ts,tsx}'] },
})
