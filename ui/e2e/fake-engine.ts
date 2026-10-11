// The engine, faked over HTTP for the end-to-end layer: the API's answers come
// from these tables, so a spec drives the real interface against known data.
export type Handler = (body: unknown) => { status: number; body: unknown }

export const routes: Record<string, Handler> = {
  'GET /api/v1/version': () => ({
    status: 200,
    body: { application: 'ROM-Sync', version: '2.0.0.dev0', api: 'v1' },
  }),
  'GET /api/v1/session': () => ({ status: 200, body: { token: 'e2e-token', shell: true } }),
}

export function answer(
  method: string,
  path: string,
  body: unknown,
): { status: number; body: unknown } {
  const handler = routes[`${method} ${path}`]
  if (!handler) {
    return {
      status: 404,
      body: {
        error: { code: 'request.not_found', message: `no fake for ${method} ${path}`, field: null },
      },
    }
  }
  return handler(body)
}
