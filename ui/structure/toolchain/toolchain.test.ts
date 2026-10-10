import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, test } from 'vitest'
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
})
