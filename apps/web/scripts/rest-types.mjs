import { writeFile } from 'node:fs/promises'
import openapiTS, { astToString } from 'openapi-typescript'

const source = new URL('../src/api/openapi.json', import.meta.url)
const destination = new URL('../src/api/rest.d.ts', import.meta.url)
const ast = await openapiTS(source, { alphabetize: true })
await writeFile(destination, astToString(ast), 'utf8')
