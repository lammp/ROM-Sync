// Generates src/lib/api/api.ts from the committed OpenAPI document (D24): the
// path and schema types from openapi-typescript, then a one-line factory over
// openapi-fetch. Nothing in src/lib/api is edited by hand; api.test.ts fails
// when the committed file and the document disagree.
import { readFileSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import openapiTS, { astToString } from 'openapi-typescript'

const UI = join(dirname(fileURLToPath(import.meta.url)), '..')
export const DOCUMENT = join(UI, '../api/openapi.json')
export const TARGET = join(UI, 'src/lib/api/api.ts')

const HEADER = `/**
 * Generated from api/openapi.json by \`npm run api\`. Do not edit.
 */

`

const FACTORY = `
import createClient, { type Client } from 'openapi-fetch'

export type Api = Client<paths>

/** A typed client for the engine's API, on the page's own origin by default. */
export function createApi(baseUrl = '', fetchImpl?: typeof fetch): Api {
  return createClient<paths>({ baseUrl, ...(fetchImpl ? { fetch: fetchImpl } : {}) })
}
`

export async function generate(document: string = readFileSync(DOCUMENT, 'utf8')): Promise<string> {
  const ast = await openapiTS(JSON.parse(document) as Parameters<typeof openapiTS>[0])
  return HEADER + astToString(ast) + FACTORY
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  writeFileSync(TARGET, await generate(), 'utf8')
}
