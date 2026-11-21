// Budget: JavaScript needed to show Home (entry + Home chunk and their static imports), gzip.
import { readFileSync } from 'node:fs'
import { gzipSync } from 'node:zlib'

// React DOM (67.4 KB) + TanStack Router (27.0 KB) are a measured floor of 94.4 KB; the app shell gets the rest.
const BUDGET = 105 * 1024
const dist = new URL('../dist/', import.meta.url)
const manifest = JSON.parse(readFileSync(new URL('.vite/manifest.json', dist), 'utf8'))
const files = new Set()
const walk = (key) => {
  const chunk = manifest[key]
  if (!chunk || files.has(chunk.file)) return
  files.add(chunk.file)
  for (const child of chunk.imports ?? []) walk(child)
}
walk('index.html')
walk('src/pages/Home.tsx')
let total = 0
for (const file of files) {
  const size = gzipSync(readFileSync(new URL(file, dist))).length
  total += size
  console.log(`${(size / 1024).toFixed(1).padStart(7)} KB  ${file}`)
}
console.log(`${(total / 1024).toFixed(1).padStart(7)} KB  total (budget ${BUDGET / 1024} KB)`)
if (total > BUDGET) process.exit(1)
