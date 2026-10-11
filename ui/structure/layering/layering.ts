/**
 * The separation of duties, enforced (REBUILD-UI section 14.3, F11-S4).
 *
 * `check` takes source files by their path under `src/` and returns every
 * violation: an import across a layer boundary, a feature importing another
 * feature, the global stylesheets imported anywhere but the root layout,
 * mutable module-level state outside `store/`, and a colour literal outside
 * `design/tokens/tokens.ts`. It is pure, so the test can plant violations.
 */
import { readdirSync, readFileSync } from 'node:fs'
import { join, posix, relative, sep } from 'node:path'

export type Violation = { readonly file: string; readonly rule: string; readonly detail: string }
export type Sources = Readonly<Record<string, string>>

type Layer =
  | 'atoms'
  | 'molecules'
  | 'organisms'
  | 'templates'
  | 'features'
  | 'app'
  | 'design'
  | 'lib'
  | 'lib/api'
  | 'store'
  | 'queries'

/** What each layer may import from inside `src/`, its own layer included. */
const MAY_IMPORT: Readonly<Record<Layer, readonly Layer[]>> = {
  atoms: ['atoms', 'design', 'lib'],
  molecules: ['molecules', 'atoms', 'design', 'lib'],
  organisms: ['organisms', 'molecules', 'atoms', 'design', 'lib'],
  templates: ['templates', 'atoms', 'design'],
  features: [
    'features',
    'organisms',
    'molecules',
    'atoms',
    'templates',
    'design',
    'lib',
    'lib/api',
    'store',
    'queries',
  ],
  app: ['app', 'templates', 'features'],
  design: ['design'],
  lib: ['lib', 'design'],
  'lib/api': ['lib/api'],
  store: ['store', 'design', 'lib', 'lib/api'],
  queries: ['queries', 'store', 'lib', 'lib/api'],
}

export const ROOT_LAYOUT = 'app/layout.tsx'
const GLOBAL_CSS = /^design\/(tokens\/tokens|base\/base)\.css$/
const COLOUR_HOME = new Set(['design/tokens/tokens.ts', 'design/tokens/tokens.css'])
/** The palette's own tests measure literal colours; nothing else may name one. */
const PALETTE_TEST = /^design\/[^/]+\/[^/]+\.(test|parity\.test)\.ts$/
const COLOUR = /#[0-9a-fA-F]{3,8}\b|\b(rgba?|hsla?)\(/
const IMPORT =
  /(?:^|\s)(?:import|export)\s(?:[^'"]*?\sfrom\s)?['"]([^'"]+)['"]|import\(\s*['"]([^'"]+)['"]\s*\)/g
const MODULE_STATE = /^(?:export\s+)?(?:let|var)\s+([A-Za-z_$][\w$]*)/gm
const TEST_OR_STORY = /\.(test|parity\.test|stories)\.tsx?$/

export function layerOf(file: string): Layer | undefined {
  const [top, second] = file.split('/')
  if (top === 'components' && second) {
    return (['atoms', 'molecules', 'organisms', 'templates'] as const).find((l) => l === second)
  }
  if (top === 'lib' && second === 'api') return 'lib/api'
  return (['features', 'app', 'design', 'lib', 'store', 'queries'] as const).find((l) => l === top)
}

/** The feature a file belongs to, for the no-cross-feature rule. */
function featureOf(file: string): string | undefined {
  const [top, name] = file.split('/')
  return top === 'features' ? name : undefined
}

/** The `src/`-relative target of a relative import, or undefined for a package. */
export function resolveImport(from: string, specifier: string): string | undefined {
  if (!specifier.startsWith('.')) return undefined
  return posix.normalize(posix.join(posix.dirname(from), specifier))
}

function importsOf(source: string): string[] {
  return [...source.matchAll(IMPORT)].map((m) => m[1] ?? m[2] ?? '')
}

/** Comments are not code: a colour named in prose is not a literal use. */
function withoutComments(source: string): string {
  return source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|[^:'"])\/\/.*$/gm, '$1')
}

export function check(sources: Sources): Violation[] {
  const out: Violation[] = []
  for (const [file, source] of Object.entries(sources)) {
    const layer = layerOf(file)
    for (const specifier of importsOf(source)) {
      const target = resolveImport(file, specifier)
      if (target === undefined) continue
      if (GLOBAL_CSS.test(target)) {
        if (file !== ROOT_LAYOUT)
          out.push({ file, rule: 'global-stylesheet', detail: `${target} outside ${ROOT_LAYOUT}` })
        continue
      }
      const to = layerOf(target)
      if (layer === undefined || to === undefined) continue
      if (!MAY_IMPORT[layer].includes(to))
        out.push({ file, rule: 'layer', detail: `${layer} imports ${to} (${target})` })
      const [a, b] = [featureOf(file), featureOf(target)]
      if (a && b && a !== b) out.push({ file, rule: 'cross-feature', detail: `${a} imports ${b}` })
    }
    const code = withoutComments(source)
    if (!file.startsWith('store/') && !TEST_OR_STORY.test(file)) {
      for (const m of code.matchAll(MODULE_STATE))
        out.push({ file, rule: 'module-state', detail: `module-level ${m[1]}` })
    }
    if (!COLOUR_HOME.has(file) && !PALETTE_TEST.test(file)) {
      const hit = COLOUR.exec(code)
      if (hit) out.push({ file, rule: 'colour-literal', detail: hit[0] })
    }
  }
  return out
}

const SOURCE = /\.(ts|tsx|css)$/

/** Every source file under `src`, keyed by its `/`-separated path. */
export function readTree(src: string): Record<string, string> {
  const out: Record<string, string> = {}
  const walk = (dir: string) => {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const path = join(dir, entry.name)
      if (entry.isDirectory()) walk(path)
      else if (SOURCE.test(entry.name))
        out[relative(src, path).split(sep).join('/')] = readFileSync(path, 'utf8')
    }
  }
  walk(src)
  return out
}
