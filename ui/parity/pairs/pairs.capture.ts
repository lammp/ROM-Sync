/**
 * The twin corpus oracle: how version 1 relates each pair of games in
 * `tests/fixtures/twins.py`, the engine's twin corpus, by running version 1's
 * own `buildTwins` over the two games alone.
 */
import { readFileSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { REPO_ROOT, bootV1 } from '../v1/v1.ts'

export const CORPUS = join(REPO_ROOT, 'tests/fixtures/twins.py')

export type PairRow = {
  readonly aTitle: string
  readonly aSystem: string
  readonly bTitle: string
  readonly bSystem: string
  readonly relation: string
  readonly pins: string
}

const BLOCK = /(ROWS = r""")\n([\s\S]*?)\n(""")/

export function readRows(source: string = readFileSync(CORPUS, 'utf8')): PairRow[] {
  const match = BLOCK.exec(source)
  if (!match?.[2]) throw new Error('no ROWS block in the twin corpus')
  return match[2].split('\n').map((line) => {
    const [aTitle, aSystem, bTitle, bSystem, relation, pins] = line.split('\t')
    if (
      aTitle === undefined ||
      aSystem === undefined ||
      bTitle === undefined ||
      bSystem === undefined ||
      pins === undefined
    ) {
      throw new Error(`unreadable row: ${line}`)
    }
    return { aTitle, aSystem, bTitle, bSystem, relation: relation ?? '', pins }
  })
}

export function writeRows(rows: readonly PairRow[], source: string): string {
  const body = rows
    .map((r) => [r.aTitle, r.aSystem, r.bTitle, r.bSystem, r.relation, r.pins].join('\t'))
    .join('\n')
  return source.replace(
    BLOCK,
    (_m, open: string, _b: string, close: string) => `${open}\n${body}\n${close}`,
  )
}

/** The rows with version 1's relation in place of whatever the corpus holds. */
export async function versionOneRelations(rows: readonly PairRow[]): Promise<PairRow[]> {
  const v1 = await bootV1({ library: { systems: {}, games: [] } })
  try {
    const pairs = rows.map((r) => [r.aTitle, r.aSystem, r.bTitle, r.bSystem])
    const relations = v1.evaluate<string[]>(
      `${JSON.stringify(pairs)}.map(([at, as, bt, bs]) => {
        S.games = [
          { id: 1, igdb: null, title: at, name: at, system: as },
          { id: 2, igdb: null, title: bt, name: bt, system: bs },
        ];
        buildTwins();
        const t = twinsOf(S.games[0]).find((x) => x.g.id === 2);
        return t ? (t.loose ? 'loose' : 'exact') : 'none';
      })`,
    )
    if (v1.errors.length) throw new Error(`version 1 reported: ${v1.errors.join('; ')}`)
    return rows.map((r, i) => ({ ...r, relation: relations[i] ?? '' }))
  } finally {
    v1.close()
  }
}

export async function writePairs(): Promise<string> {
  const source = readFileSync(CORPUS, 'utf8')
  writeFileSync(CORPUS, writeRows(await versionOneRelations(readRows(source)), source), 'utf8')
  return CORPUS
}
