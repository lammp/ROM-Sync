/**
 * The grouping rule, enforced (REBUILD-UI section 14.2).
 *
 * `check` takes every file under `ui/` by its `/`-separated path and returns
 * each folder that is missing a companion: a component or feature without
 * its stories or test, a function without its test, a captured corpus
 * without its parity test, a component test that rebuilds its props instead
 * of composing its stories, a barrel file, or an end-to-end spec outside its
 * flow's folder. It is pure, so the test can plant violations.
 */
import { readdirSync, readFileSync } from 'node:fs'
import { join, relative, sep } from 'node:path'

export type Missing = { readonly folder: string; readonly rule: string; readonly detail: string }
export type Tree = Readonly<Record<string, string>>

const COMPONENT_ROOTS =
  /^src\/(components\/(atoms|molecules|organisms|templates)|features\/[^/]+)\/([^/]+)$/
const FUNCTION_ROOTS = /^src\/(lib|design|store|queries)(\/.+)?$/
const SOURCE = /^(?!.*\.(test|parity\.test|stories)\.tsx?$).+\.tsx?$/

function folders(tree: Tree): Map<string, string[]> {
  const out = new Map<string, string[]>()
  for (const path of Object.keys(tree)) {
    const cut = path.lastIndexOf('/')
    const folder = path.slice(0, cut)
    const list = out.get(folder) ?? []
    list.push(path.slice(cut + 1))
    out.set(folder, list)
  }
  return out
}

export function check(tree: Tree): Missing[] {
  const out: Missing[] = []
  const miss = (folder: string, rule: string, detail: string) => out.push({ folder, rule, detail })
  const all = folders(tree)
  for (const [folder, files] of all) {
    const has = (name: string) => files.includes(name)
    const name = folder.split('/').at(-1) ?? ''
    for (const f of files) if (/^index\.tsx?$/.test(f)) miss(folder, 'barrel', f)
    const component = COMPONENT_ROOTS.exec(folder)
    if (component) {
      for (const f of [`${name}.tsx`, `${name}.stories.tsx`, `${name}.test.tsx`])
        if (!has(f)) miss(folder, 'component', f)
      const test = tree[`${folder}/${name}.test.tsx`]
      if (
        test !== undefined &&
        !(/composeStories/.test(test) && test.includes(`./${name}.stories`))
      )
        miss(folder, 'compose', `${name}.test.tsx does not compose ./${name}.stories`)
      continue
    }
    if (FUNCTION_ROOTS.test(folder) && !folder.endsWith('/__fixtures__')) {
      const sources = files.filter((f) => SOURCE.test(f) && !/^index\.tsx?$/.test(f))
      if (sources.length > 0) {
        if (!has(`${name}.ts`) && !has(`${name}.tsx`)) miss(folder, 'function', `${name}.ts`)
        if (!has(`${name}.test.ts`) && !has(`${name}.test.tsx`))
          miss(folder, 'function', `${name}.test.ts`)
      }
      const corpora = (all.get(`${folder}/__fixtures__`) ?? []).filter((f) =>
        f.endsWith('.v1.json'),
      )
      if (corpora.length > 0 && sources.length > 0 && !has(`${name}.parity.test.ts`))
        miss(folder, 'parity', `${name}.parity.test.ts`)
    }
    if (folder.startsWith('e2e')) {
      for (const f of files.filter((f) => f.endsWith('.spec.ts'))) {
        const flow = f.slice(0, -'.spec.ts'.length)
        if (folder !== `e2e/${flow}` && !(folder === 'e2e/a11y'))
          miss(folder, 'e2e', `${f} belongs in e2e/${flow}/`)
      }
    }
  }
  return out
}

const SKIP = new Set([
  'node_modules',
  '.next',
  'out',
  'test-results',
  'playwright-report',
  'coverage',
  'storybook-static',
])

/** Every source, story, test, spec and fixture under `ui/`, keyed by path. */
export function readTree(ui: string): Record<string, string> {
  const out: Record<string, string> = {}
  const walk = (dir: string) => {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      if (SKIP.has(entry.name)) continue
      const path = join(dir, entry.name)
      const key = relative(ui, path).split(sep).join('/')
      if (entry.isDirectory()) walk(path)
      else if (
        (key.startsWith('src/') || key.startsWith('e2e/')) &&
        /\.(tsx?|json|css)$/.test(entry.name)
      )
        out[key] = readFileSync(path, 'utf8')
    }
  }
  walk(ui)
  return out
}
