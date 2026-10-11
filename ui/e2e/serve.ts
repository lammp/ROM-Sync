// Serves the static export by manifest lookup, as the engine does, and answers
// /api/v1 from the fake engine's world. `POST /__reset` starts a fresh world,
// so each spec begins from the same data; `POST /__seed/<name>` adds a named
// state on top of it; `POST /__fail` makes reads under the given paths fail.
import { readFileSync } from 'node:fs'
import { createServer } from 'node:http'
import { join } from 'node:path'
import { answer, freshWorld, seed } from './fake/world.ts'

const ROOT = 'out'
const port = Number(process.argv[2] ?? 4310)
const manifest = JSON.parse(readFileSync(join(ROOT, 'manifest.json'), 'utf8')) as Record<
  string,
  { file: string; type: string }
>

let world = freshWorld()

createServer((req, res) => {
  const url = new URL(req.url ?? '/', 'http://127.0.0.1')
  if (req.method === 'POST' && url.pathname === '/__fail') {
    let raw = ''
    req.on('data', (chunk: Buffer) => (raw += chunk.toString()))
    req.on('end', () => {
      world.failing = (JSON.parse(raw || '{}') as { paths?: string[] }).paths ?? []
      res.writeHead(204)
      res.end()
    })
    return
  }
  if (req.method === 'POST' && url.pathname.startsWith('/__seed/')) {
    seed(world, url.pathname.slice('/__seed/'.length))
    res.writeHead(204)
    res.end()
    return
  }
  if (req.method === 'POST' && url.pathname === '/__reset') {
    world = freshWorld()
    res.writeHead(204)
    res.end()
    return
  }
  if (url.pathname.startsWith('/api/')) {
    let raw = ''
    req.on('data', (chunk: Buffer) => (raw += chunk.toString()))
    req.on('end', () => {
      const result = answer(world, req.method ?? 'GET', url.pathname, raw ? JSON.parse(raw) : null)
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
