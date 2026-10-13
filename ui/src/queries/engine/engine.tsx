/**
 * The query layer's connection to the engine (D22, D24).
 *
 * One typed client and one QueryClient per engine. Requests that change state
 * carry the session token the engine hands out at `/session`; it is fetched
 * once and kept on the engine object, never in module state. Every request
 * passes TanStack Query's abort signal through, so a page that unmounts
 * cancels what it started.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { Middleware } from 'openapi-fetch'
import { createContext, useContext, useState, type ReactNode } from 'react'
import { createApi, type Api } from '../../lib/api/api'

export const TOKEN_HEADER = 'X-RomSync-Token'
const SAFE = new Set(['GET', 'HEAD', 'OPTIONS'])

export type Engine = {
  readonly api: Api
  readonly client: QueryClient
  /** Where the engine answers; empty for this page's own origin. */
  readonly baseUrl: string
  /** How often a running job is asked for, in milliseconds. */
  readonly pollMs: number
}

export type EngineOptions = {
  readonly baseUrl?: string
  readonly fetch?: typeof fetch
  readonly pollMs?: number
  readonly retry?: number
}

/** An error the engine reported in its envelope, or a failed exchange. */
export class EngineError extends Error {
  constructor(
    readonly code: string,
    message: string,
    readonly field: string | null = null,
  ) {
    super(message)
    this.name = 'EngineError'
  }
}

type Envelope = { error?: { code?: string; message?: string; field?: string | null } }

/** Turns an openapi-fetch result into its data, or throws what the engine said. */
export function unwrap<T>(result: { data?: T; error?: unknown; response: Response }): T {
  if (result.error === undefined && result.data !== undefined) return result.data
  const body = (result.error ?? {}) as Envelope
  throw new EngineError(
    body.error?.code ?? `http.${result.response.status}`,
    body.error?.message ?? result.response.statusText,
    body.error?.field ?? null,
  )
}

/** Reads that reach this computer's disk, which the engine asks the token for too (F16-S1). */
const GUARDED_READS = ['/api/v1/shell/folders']

/** Adds the session token to every request that changes state, and to the guarded reads. */
export function sessionToken(token: () => Promise<string>): Middleware {
  return {
    async onRequest({ request }) {
      const guarded = GUARDED_READS.some((p) => new URL(request.url).pathname === p)
      if (SAFE.has(request.method) && !guarded) return request
      request.headers.set(TOKEN_HEADER, await token())
      return request
    },
  }
}

export function createEngine(options: EngineOptions = {}): Engine {
  const api = createApi(options.baseUrl ?? '', options.fetch)
  let session: Promise<string> | null = null
  const token = () => {
    session ??= api.GET('/api/v1/session').then((r) => unwrap(r).token)
    session.catch(() => {
      session = null
    })
    return session
  }
  api.use(sessionToken(token))
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: options.retry ?? 1, refetchOnWindowFocus: false },
      mutations: { retry: false },
    },
  })
  return { api, client, pollMs: options.pollMs ?? 1000, baseUrl: options.baseUrl ?? '' }
}

const EngineContext = createContext<Engine | null>(null)

/** Mounts the engine for the features beneath it; one engine per page load. */
export function EngineProvider({ engine, children }: { engine?: Engine; children: ReactNode }) {
  const [mine] = useState(() => engine ?? createEngine())
  return (
    <EngineContext value={mine}>
      <QueryClientProvider client={mine.client}>{children}</QueryClientProvider>
    </EngineContext>
  )
}

export function useEngine(): Engine {
  const engine = useContext(EngineContext)
  if (engine === null) throw new Error('useEngine outside an EngineProvider')
  return engine
}
