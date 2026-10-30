import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { readFileSync } from 'node:fs'
const policy = JSON.parse(readFileSync(new URL('./vercel.json', import.meta.url), 'utf8')).headers[0].headers as { key: string; value: string }[]
export default defineConfig({
  plugins: [react(), { name: 'demo-build-marker', generateBundle() { this.emitFile({ type: 'asset', fileName: 'demo-build.json', source: JSON.stringify({ mode: 'browser-only-demo', api: false, revision: process.env.VERCEL_GIT_COMMIT_SHA || 'local-build' }) }) } }], define: { 'import.meta.env.VITE_BROWSER_DEMO': JSON.stringify('1') },
  build: { outDir: 'dist-demo' },
  server: { host: '127.0.0.1', port: 5174, strictPort: true }, preview: { host: '127.0.0.1', port: 4174, strictPort: true, headers: Object.fromEntries(policy.map(h => [h.key, h.value])) },
})
