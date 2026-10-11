import { mkdirSync, mkdtempSync, readdirSync, readFileSync, statSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, test } from 'vitest'
import { manifest } from '../../scripts/manifest.ts'
import config from '../../vitest.config.mts'

const UI = resolve(dirname(fileURLToPath(import.meta.url)), '../..')

type Project = { test?: { name?: string; environment?: string; include?: string[] } }

function readJson(name: string): Record<string, unknown> {
  return JSON.parse(readFileSync(resolve(UI, name), 'utf8')) as Record<string, unknown>
}

function project(name: string): Project | undefined {
  const projects = (config.test?.projects ?? []) as unknown[]
  return projects.find(
    (p): p is Project => typeof p === 'object' && p !== null && (p as Project).test?.name === name,
  )
}

describe('toolchain', () => {
  test('unit_project_runs', () => {
    const unit = project('unit')
    expect(unit, 'vitest.config.mts declares no project named unit').toBeDefined()
    expect(unit?.test?.environment).toBe('jsdom')
    expect(unit?.test?.include).toEqual(
      expect.arrayContaining([
        'src/**/*.test.{ts,tsx}',
        'parity/**/*.test.ts',
        'structure/**/*.test.ts',
      ]),
    )
  })

  test('typescript_is_strict', () => {
    const tsconfig = readJson('tsconfig.json') as { compilerOptions?: Record<string, unknown> }
    expect(tsconfig.compilerOptions?.strict).toBe(true)
    expect(tsconfig.compilerOptions?.noUncheckedIndexedAccess).toBe(true)
  })

  test('every_dependency_is_pinned', () => {
    const pkg = readJson('package.json') as {
      dependencies?: Record<string, string>
      devDependencies?: Record<string, string>
    }
    const all = { ...pkg.dependencies, ...pkg.devDependencies }
    const loose = Object.entries(all).filter(([, v]) => !/^\d+\.\d+\.\d+$/.test(v))
    expect(loose, 'a dependency is not pinned to an exact version').toEqual([])
  })

  test('static_export_is_declared', () => {
    const source = readFileSync(resolve(UI, 'next.config.ts'), 'utf8')
    expect(source).toMatch(/output:\s*'export'/)
  })

  test('exports_static', () => {
    const source = readFileSync(resolve(UI, 'next.config.ts'), 'utf8')
    expect(source).toMatch(/trailingSlash:\s*true/)
    expect(source).toMatch(/images:\s*\{\s*unoptimized:\s*true\s*\}/)
    const pkg = readJson('package.json') as { scripts?: Record<string, string> }
    expect(pkg.scripts?.bundle).toMatch(/next build && .*scripts\/manifest\.ts out/)
  })

  test('no_node_at_runtime', () => {
    const pkg = readJson('package.json') as { scripts?: Record<string, string> }
    expect(Object.values(pkg.scripts ?? {}).join(' ')).not.toMatch(/next start/)
    const app = resolve(UI, 'src/app')
    const sources = walk(app).filter((f) => /\.(ts|tsx)$/.test(f))
    expect(sources.length).toBeGreaterThan(0)
    for (const file of sources) {
      expect(file, 'a route handler needs a server').not.toMatch(/[\\/]route\.(ts|tsx)$/)
      const text = readFileSync(file, 'utf8')
      expect(text, `${file} asks for a server`).not.toMatch(/['"]use server['"]|server-only/)
    }
  })

  test('storybook_project_runs_in_chromium', () => {
    const storybook = project('storybook') as
      { test?: { browser?: { enabled?: boolean; instances?: { browser: string }[] } } } | undefined
    expect(storybook?.test?.browser?.enabled).toBe(true)
    expect(storybook?.test?.browser?.instances).toEqual([{ browser: 'chromium' }])
    const preview = readFileSync(resolve(UI, '.storybook/preview.ts'), 'utf8')
    expect(preview, 'an accessibility violation must fail the story').toMatch(/test:\s*'error'/)
  })

  test('playwright_serves_the_export', () => {
    const source = readFileSync(resolve(UI, 'playwright.config.ts'), 'utf8')
    expect(source).toMatch(/testDir:\s*'e2e'/)
    expect(source).toMatch(/npm run bundle/)
    const serve = readFileSync(resolve(UI, 'e2e/serve.ts'), 'utf8')
    expect(serve, 'the export is served by manifest lookup').toMatch(/manifest\.json/)
  })

  test('the_manifest_lists_every_file_by_its_url', () => {
    const root = mkdtempSync(join(tmpdir(), 'export-'))
    mkdirSync(join(root, 'devices'))
    mkdirSync(join(root, '_next'))
    writeFileSync(join(root, 'index.html'), '<h1>x</h1>')
    writeFileSync(join(root, 'devices', 'index.html'), '<h1>y</h1>')
    writeFileSync(join(root, '_next', 'app.js'), 'run()')
    expect(manifest(root)).toEqual({
      '/': { file: 'index.html', type: 'text/html' },
      '/index.html': { file: 'index.html', type: 'text/html' },
      '/devices/': { file: 'devices/index.html', type: 'text/html' },
      '/devices/index.html': { file: 'devices/index.html', type: 'text/html' },
      '/_next/app.js': { file: '_next/app.js', type: 'text/javascript' },
    })
  })
})

function walk(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name)
    return statSync(path).isDirectory() ? walk(path) : [path]
  })
}
