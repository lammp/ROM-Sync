/**
 * Version 1 of the interface, loaded from the tag and run unchanged.
 *
 * The source is read with `git show` from `parity-source-v1`, never from the
 * working tree, so a capture means the same thing after version 1 is gone.
 * It runs in jsdom against its own `index.html`, with `fetch` answered by the
 * caller, which is how a corpus feeds it a synthetic library.
 */
import { execFileSync } from 'node:child_process'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { Script } from 'node:vm'
import { JSDOM, VirtualConsole } from 'jsdom'

export const V1_TAG = 'parity-source-v1'
export const V1_DIR = 'ROM-Sync/ui'
export const UI_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
export const REPO_ROOT = resolve(UI_ROOT, '..')

export type V1File = 'app.js' | 'app.css' | 'index.html'

export function v1Source(file: V1File): string {
  return execFileSync('git', ['show', `${V1_TAG}:${V1_DIR}/${file}`], {
    cwd: REPO_ROOT,
    encoding: 'utf8',
    maxBuffer: 1 << 26,
  })
}

export function v1Commit(): string {
  return execFileSync('git', ['rev-parse', `${V1_TAG}^{commit}`], {
    cwd: REPO_ROOT,
    encoding: 'utf8',
  }).trim()
}

export type V1Library = {
  readonly systems: Record<string, string>
  readonly games: readonly object[]
}

/** Answers one `/api/` call: the path after `/api/`, and the posted body if any. */
export type Responder = (path: string, body: unknown) => unknown

export type V1 = {
  /** Errors version 1 reported while running. A capture with any is not a capture. */
  readonly errors: readonly string[]
  /** Evaluates an expression in version 1's global scope, `const` declarations included. */
  evaluate<T>(expression: string): T
  /** Lets version 1 finish whatever its last call started. */
  settle(): Promise<void>
  readonly document: Document
  close(): void
}

const tick = (): Promise<void> => new Promise((done) => setTimeout(done, 0))

export async function bootV1(options: {
  readonly library: V1Library
  readonly respond?: Responder
}): Promise<V1> {
  const errors: string[] = []
  const virtualConsole = new VirtualConsole()
  virtualConsole.on('jsdomError', (e) => errors.push(e.message))
  virtualConsole.on('error', (...args: unknown[]) => errors.push(args.map(String).join(' ')))

  const html = v1Source('index.html').replace(/<script src="\/ui\/app\.js"><\/script>/, '')
  const dom = new JSDOM(html, {
    url: 'http://localhost/',
    runScripts: 'outside-only',
    pretendToBeVisual: true,
    virtualConsole,
  })
  const window = dom.window

  const answer = (path: string, body: unknown): unknown => {
    if (path === 'library') return options.library
    if (path === 'devices') return { profiles: [] }
    if (options.respond) return options.respond(path, body)
    throw new Error(`no answer for /api/${path}`)
  }
  Object.assign(window, {
    fetch: async (input: unknown, init?: { body?: string }) => {
      const path = String(input).replace(/^\/api\//, '')
      const body: unknown = init?.body ? JSON.parse(init.body) : undefined
      const value = answer(path, body)
      return { json: async () => value }
    },
    ResizeObserver: class {
      observe(): void {}
      unobserve(): void {}
      disconnect(): void {}
    },
  })

  const evaluate = <T>(expression: string): T => window.eval(expression) as T
  const settle = async (): Promise<void> => {
    for (let i = 0; i < 10; i++) await tick()
  }

  // As a script, not through eval: strict-mode eval would keep its declarations to itself.
  new Script(v1Source('app.js'), { filename: `${V1_DIR}/app.js` }).runInContext(
    dom.getInternalVMContext(),
  )
  for (let i = 0; i < 400; i++) {
    await tick()
    const booted = evaluate<boolean>(
      "S.lib !== null && document.querySelector('#device-select').options.length > 0",
    )
    if (booted) {
      await settle()
      return { errors, evaluate, settle, document: window.document, close: () => window.close() }
    }
  }
  window.close()
  throw new Error(`version 1 did not finish booting: ${errors.join('; ') || 'no error reported'}`)
}
