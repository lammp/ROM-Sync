/**
 * The title corpus oracle: version 1's strict and loose twin keys for every
 * title in `tests/fixtures/titles.py`, the engine's identity corpus.
 *
 * The corpus is a Python data module because the publication rules return
 * only source to `tests/`. This module reads its ROWS block, runs version 1's
 * own `twinKey` and `twinKeyLoose` over each title, and either checks the
 * committed keys or writes them.
 */
import { readFileSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { REPO_ROOT, bootV1 } from '../v1/v1.ts'

export const CORPUS = join(REPO_ROOT, 'tests/fixtures/titles.py')

export type TitleRow = {
  readonly title: string
  readonly strict: string
  readonly loose: string
  readonly pins: string
}

const BLOCK = /(ROWS = r""")\n([\s\S]*?)\n(""")/

export function readRows(source: string = readFileSync(CORPUS, 'utf8')): TitleRow[] {
  const match = BLOCK.exec(source)
  if (!match?.[2]) throw new Error('no ROWS block in the title corpus')
  return match[2].split('\n').map((line) => {
    const [title, strict, loose, pins] = line.split('\t')
    if (title === undefined || pins === undefined) throw new Error(`unreadable row: ${line}`)
    return { title, strict: strict ?? '', loose: loose ?? '', pins }
  })
}

export function writeRows(rows: readonly TitleRow[], source: string): string {
  const body = rows.map((r) => [r.title, r.strict, r.loose, r.pins].join('\t')).join('\n')
  return source.replace(
    BLOCK,
    (_m, open: string, _b: string, close: string) => `${open}\n${body}\n${close}`,
  )
}

/** The rows with version 1's keys in place of whatever the corpus holds. */
export async function versionOneKeys(rows: readonly TitleRow[]): Promise<TitleRow[]> {
  const v1 = await bootV1({ library: { systems: {}, games: [] } })
  try {
    const keys = v1.evaluate<[string, string][]>(
      `${JSON.stringify(rows.map((r) => r.title))}.map((t) => {
        const g = { igdb: null, title: t, name: t };
        return [twinKey(g), twinKeyLoose(g)];
      })`,
    )
    if (v1.errors.length) throw new Error(`version 1 reported: ${v1.errors.join('; ')}`)
    return rows.map((r, i) => {
      const pair = keys[i]
      if (!pair) throw new Error(`no key for ${r.title}`)
      return { ...r, strict: pair[0], loose: pair[1] }
    })
  } finally {
    v1.close()
  }
}

export async function writeTitles(): Promise<string> {
  const source = readFileSync(CORPUS, 'utf8')
  writeFileSync(CORPUS, writeRows(await versionOneKeys(readRows(source)), source), 'utf8')
  return CORPUS
}
