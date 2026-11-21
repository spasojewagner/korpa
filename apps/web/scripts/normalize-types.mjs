import { readFile, readdir, writeFile } from 'node:fs/promises'
import ts from 'typescript'

// Preserve strict unknown boundaries in the operation lookup and generic result helper.
const directory = new URL('../src/gql/', import.meta.url)
for (const filename of await readdir(directory)) {
  if (!filename.endsWith('.ts')) continue
  const path = new URL(filename, directory)
  const source = await readFile(path, 'utf8')
  const strict = source
    .replace(/^\/\* eslint-disable \*\/\r?\n/, '')
    .replace(/\/\*\*[\s\S]*?\*\//g, '')
    .replaceAll('(documents as any)', '(documents as Record<string, unknown>)')
    .replace(/DocumentNode<\s*any,\s*any\s*>/g, 'DocumentNode<unknown, never>')
    .replace(/DocumentNode<\s*infer TType,\s*any\s*>/g, 'DocumentNode<infer TType, never>')
  const ast = ts.createSourceFile(filename, strict, ts.ScriptTarget.Latest, true)
  function check(node) {
    if (node.kind === ts.SyntaxKind.AnyKeyword) throw new Error('Unsafe operation type boundary')
    ts.forEachChild(node, check)
  }
  check(ast)
  await writeFile(path, strict, 'utf8')
}
