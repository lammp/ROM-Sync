/**
 * Writes the fixtures. Run from ui/:
 *
 *     npm run capture             every corpus
 *     npm run capture -- search   one corpus
 *
 * The capture tests compare against what this writes; they never write.
 */
import { fileURLToPath } from 'node:url'
import { writeFixture } from '../fixture/fixture.ts'
import { FACETS } from '../facets/facets.capture.ts'
import { FORMAT } from '../format/format.capture.ts'
import { PROGRESS } from '../progress/progress.capture.ts'
import { SEARCH } from '../search/search.capture.ts'
import { SORT } from '../sort/sort.capture.ts'
import { TOKENS } from '../tokens/tokens.capture.ts'
import { writeTitles } from '../titles/titles.capture.ts'
import { TWINS } from '../twins/twins.capture.ts'
import { WINDOWING } from '../windowing/windowing.capture.ts'

export type Corpus = {
  readonly name: string
  readonly fixture: string
  readonly capture: () => Promise<unknown>
}

export const CORPORA: readonly Corpus[] = [
  SEARCH,
  FACETS,
  TWINS,
  SORT,
  FORMAT,
  WINDOWING,
  PROGRESS,
  TOKENS,
]

/** Corpora that live outside `ui/` and are written in place, not as fixtures. */
export const WRITERS: Readonly<Record<string, () => Promise<string>>> = { titles: writeTitles }

export async function captureAll(names: readonly string[]): Promise<string[]> {
  const written: string[] = []
  for (const name of names.filter((n) => n in WRITERS)) {
    const writer = WRITERS[name]
    if (writer) written.push(await writer())
  }
  names = names.filter((n) => !(n in WRITERS))
  if (written.length && !names.length) return written
  const unknown = names.filter((n) => !CORPORA.some((c) => c.name === n))
  if (unknown.length) throw new Error(`no such corpus: ${unknown.join(', ')}`)
  const chosen = names.length ? CORPORA.filter((c) => names.includes(c.name)) : CORPORA
  for (const corpus of chosen) {
    writeFixture(corpus.fixture, corpus.name, await corpus.capture())
    written.push(corpus.fixture)
  }
  return written
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  for (const path of await captureAll(process.argv.slice(2))) console.log(`wrote ${path}`)
}
