// @vitest-environment node
import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { DOCUMENT, TARGET, generate } from '../../../scripts/api.ts'
import { createApi } from './api'

const document = readFileSync(DOCUMENT, 'utf8')

describe('client', () => {
  it('generated_matches_openapi', async () => {
    expect(readFileSync(TARGET, 'utf8')).toBe(await generate(document))
  })

  it('types every path the document declares', () => {
    const committed = readFileSync(TARGET, 'utf8')
    for (const path of Object.keys((JSON.parse(document) as { paths: object }).paths)) {
      expect(committed, path).toContain(`"${path}": {`)
    }
  })

  it('changes when the document changes', async () => {
    const parsed = JSON.parse(document) as { paths: Record<string, unknown> }
    parsed.paths['/api/v1/added'] = {}
    expect(await generate(JSON.stringify(parsed))).not.toBe(await generate(document))
  })

  it('calls the engine through the fetch it is given', async () => {
    const seen: string[] = []
    const fake = async (input: Request) => {
      seen.push(`${input.method} ${input.url}`)
      return Response.json({ application: 'ROM-Sync', version: '2.0.0', api: 'v1' })
    }
    const api = createApi('http://127.0.0.1:8765', fake as typeof fetch)
    const { data, error } = await api.GET('/api/v1/version')
    expect(error).toBeUndefined()
    expect(data?.application).toBe('ROM-Sync')
    expect(seen).toEqual(['GET http://127.0.0.1:8765/api/v1/version'])
  })

  it('defaults to the page origin', () => {
    expect(createApi()).toHaveProperty('GET')
  })
})
