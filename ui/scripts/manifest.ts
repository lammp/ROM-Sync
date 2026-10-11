// Writes manifest.json into the static export: every emitted file, by the URL
// that names it, with its media type. The engine serves only what this lists
// (SPEC section 12, S2), so nothing from a request is ever joined to a folder.
import { readdirSync, statSync, writeFileSync } from 'node:fs'
import { extname, join, relative, resolve, sep } from 'node:path'
import { fileURLToPath } from 'node:url'

const TYPES: Record<string, string> = {
  '.html': 'text/html',
  '.js': 'text/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.txt': 'text/plain',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.ico': 'image/x-icon',
  '.woff2': 'font/woff2',
  '.map': 'application/json',
}

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name)
    return statSync(path).isDirectory() ? files(path) : [path]
  })
}

export function manifest(root: string): Record<string, { file: string; type: string }> {
  const out: Record<string, { file: string; type: string }> = {}
  for (const path of files(root).sort()) {
    const file = relative(root, path).split(sep).join('/')
    if (file === 'manifest.json') continue
    const type = TYPES[extname(file).toLowerCase()] ?? 'application/octet-stream'
    out['/' + file] = { file, type }
    if (file === 'index.html') out['/'] = { file, type }
    else if (file.endsWith('/index.html'))
      out['/' + file.slice(0, -'index.html'.length)] = { file, type }
  }
  return out
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const root = process.argv[2] ?? 'out'
  writeFileSync(join(root, 'manifest.json'), JSON.stringify(manifest(root), null, 1))
}
