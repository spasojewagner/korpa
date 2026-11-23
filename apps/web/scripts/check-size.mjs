// Budget: JavaScript needed to show Home (entry + Home chunk and their static imports), gzip.
import { readFileSync } from 'node:fs'
import { gzipSync } from 'node:zlib'

// Count the shell and Home's static dependency graph, without double-counting shared files.
const BUDGET = 100 * 1024
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
// Home can be eager in the entry, or a separate dynamic entry.
const home = Object.keys(manifest).find((key) =>
  key === 'src/pages/Home.tsx' || (manifest[key].name === 'Home' && manifest[key].isDynamicEntry),
)
if (home) walk(home)
let total = 0
for (const file of files) {
  const size = gzipSync(readFileSync(new URL(file, dist))).length
  total += size
  console.log(`${(size / 1024).toFixed(1).padStart(7)} KB  ${file}`)
}
console.log(`${(total / 1024).toFixed(1).padStart(7)} KB  total (budget ${BUDGET / 1024} KB)`)
if (total > BUDGET) process.exit(1)
