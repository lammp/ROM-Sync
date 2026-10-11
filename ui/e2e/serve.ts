// Serves the static export by manifest lookup, as the engine does, and answers
// /api/v1 from the fake engine.
import { readFileSync } from 'node:fs'
import { createServer } from 'node:http'
import { join } from 'node:path'
import { answer } from './fake-engine.ts'

const ROOT = 'out'
const port = Number(process.argv[2] ?? 4310)
const manifest = JSON.parse(readFileSync(join(ROOT, 'manifest.json'), 'utf8')) as Record<
  string,
  { file: string; type: string }
>

createServer((req, res) => {
  const url = new URL(req.url ?? '/', 'http://127.0.0.1')
  if (url.pathname.startsWith('/api/')) {
    let raw = ''
    req.on('data', (chunk: Buffer) => (raw += chunk.toString()))
    req.on('end', () => {
      const result = answer(req.method ?? 'GET', url.pathname, raw ? JSON.parse(raw) : null)
      res.writeHead(result.status, { 'content-type': 'application/json' })
      res.end(JSON.stringify(result.body))
    })
    return
  }
  const asset = manifest[url.pathname] ?? manifest[url.pathname.replace(/\/?$/, '/')]
  if (!asset) {
    res.writeHead(404, { 'content-type': 'text/plain' })
    res.end('not found')
    return
  }
  res.writeHead(200, { 'content-type': asset.type })
  res.end(readFileSync(join(ROOT, asset.file)))
}).listen(port, '127.0.0.1')
