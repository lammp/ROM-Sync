/**
 * The token corpus: version 1's declared tokens and the 31 contrast pairs
 * measured over its stylesheet, as `_tools/contrast.py` reports them. The
 * tool is the oracle; this module runs it against app.css from the tag and
 * reads its report.
 */
import { execFileSync } from 'node:child_process'
import { existsSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { normalise } from '../fixture/fixture.ts'
import { REPO_ROOT, UI_ROOT, v1Source } from '../v1/v1.ts'

export const FIXTURE = join(UI_ROOT, 'src/design/tokens/__fixtures__/palette.v1.json')
export const PAIRS = join(REPO_ROOT, '_tools/contrast-pairs.txt')
const TOOL = join(REPO_ROOT, '_tools/contrast.py')

export type Pair = {
  readonly label: string
  readonly fg: string
  readonly bg: string
  readonly ratio: number
  readonly target: number
  readonly verdict: 'PASS' | 'FAIL'
  readonly correction: string
}
export type TokenCases = {
  readonly tokens: Readonly<Record<string, string>>
  readonly pairs: readonly Pair[]
}

/** The interpreter the gate runs under, else the repository's environment, else the path's. */
export function python(): string {
  const fromGate = process.env.ROMSYNC_PYTHON
  if (fromGate) return fromGate
  for (const candidate of [
    join(REPO_ROOT, '.venv/Scripts/python.exe'),
    join(REPO_ROOT, '.venv/bin/python'),
  ]) {
    if (existsSync(candidate)) return candidate
  }
  return 'python'
}

const PAIR_LINE = /^(.*?)\s+(\S+)\s+(\S+)\s+(\d+\.\d\d)\s+(\d+\.\d)\s+(PASS|FAIL)\s*(.*)$/

export function parseReport(report: string): TokenCases {
  const lines = report.split(/\r?\n/)
  const tokens: Record<string, string> = {}
  const declared = lines.indexOf('declared tokens')
  for (const line of lines.slice(declared + 1)) {
    const m = /^\s+(--[a-z0-9-]+)\s+(.+)$/.exec(line)
    if (!m?.[1] || !m[2]) break
    tokens[m[1]] = m[2].trim()
  }
  const rules = lines.flatMap((l, i) => (/^-{20,}$/.test(l) ? [i] : []))
  const [from, to] = rules
  if (from === undefined || to === undefined) throw new Error('no pair table in the report')
  const pairs = lines.slice(from + 1, to).map((line) => {
    const m = PAIR_LINE.exec(line)
    if (!m) throw new Error(`unreadable pair line: ${line}`)
    const [, label, fg, bg, ratio, target, verdict, correction] = m
    return {
      label: (label ?? '').trim(),
      fg: fg ?? '',
      bg: bg ?? '',
      ratio: Number(ratio),
      target: Number(target),
      verdict: verdict as 'PASS' | 'FAIL',
      correction: (correction ?? '').trim(),
    }
  })
  return { tokens, pairs }
}

export async function captureTokens(): Promise<TokenCases> {
  const dir = mkdtempSync(join(tmpdir(), 'romsync-tokens-'))
  try {
    const css = join(dir, 'app.css')
    writeFileSync(css, v1Source('app.css'), 'utf8')
    let report: string
    try {
      report = execFileSync(python(), [TOOL, css, '--pairs', PAIRS, '--strict'], {
        encoding: 'utf8',
      })
    } catch (error) {
      // --strict exits 1 when a pair fails, and version 1 has failing pairs: the report is still the oracle's.
      const out = (error as { status?: number; stdout?: string }).stdout
      if ((error as { status?: number }).status !== 1 || !out) throw error
      report = out
    }
    return normalise(parseReport(report)) as TokenCases
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
}

export const TOKENS = { name: 'tokens', fixture: FIXTURE, capture: captureTokens } as const
