/** Writes `src/design/tokens/tokens.css` from `tokens.ts`, the single source. */
import { writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { stylesheet } from '../src/design/tokens/tokens.ts'

const target = join(dirname(fileURLToPath(import.meta.url)), '../src/design/tokens/tokens.css')
writeFileSync(target, stylesheet(), 'utf8')
