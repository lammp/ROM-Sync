/**
 * The unit layer's socket guard, the counterpart of the engine's: a test that
 * reaches for the network fails at once, naming what it tried. Every test that
 * needs the engine is given a fake fetch instead.
 */
export class NetworkInTest extends Error {
  constructor(what: string) {
    super(`network access in a unit test: ${what}`)
    this.name = 'NetworkInTest'
  }
}

export const GUARDED = Symbol.for('romsync.network-guard')

function refuse(what: string): never {
  throw new NetworkInTest(what)
}

const fetchGuard = Object.assign(
  (input: RequestInfo | URL) =>
    Promise.reject(
      new NetworkInTest(`fetch ${input instanceof Request ? input.url : String(input)}`),
    ),
  { [GUARDED]: true },
)

class SocketGuard {
  constructor(url: string | URL) {
    refuse(`WebSocket ${String(url)}`)
  }
}

class EventSourceGuard {
  constructor(url: string | URL) {
    refuse(`EventSource ${String(url)}`)
  }
}

globalThis.fetch = fetchGuard as unknown as typeof fetch
globalThis.WebSocket = SocketGuard as unknown as typeof WebSocket
globalThis.EventSource = EventSourceGuard as unknown as typeof EventSource
if (typeof XMLHttpRequest !== 'undefined') {
  XMLHttpRequest.prototype.open = function open(_method: string, url: string | URL) {
    refuse(`XMLHttpRequest ${String(url)}`)
  }
}
