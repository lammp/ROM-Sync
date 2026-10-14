# Architecture

ROM-Sync 2.0.0, in overview. The binding detail is in
[rewrite/SPEC.md](rewrite/SPEC.md); this page is the map. The analysis of
version 1 that planned this split is this file's history before 2.0.0.

## The shape

One Windows process. The desktop shell starts the engine and its HTTP API on a
loopback port, and shows the interface, a set of static files the API serves,
in a WebView2 window. The interface talks to the engine only through the API,
so the same page works in a browser pointed at the same address.

```
 ROM-Sync.exe (desktop/)
 ├─ WebView2 window ──► static interface (ui/, built)        the page
 │                          │  fetch /api/v1/...  + page token
 │                          ▼
 ├─ HTTP API (api/)  FastAPI on 127.0.0.1 or ::1 only         the boundary
 │                          │  calls
 │                          ▼
 └─ engine (engine/romsync)                                   the application
      compose ─► app use cases ─► ports ◄─ adapters ─► SQLite, files, adb, MTP, IGDB, libretro
                    │
                    └─ domain rules (pure)
```

## The engine

### Layers, and the one rule between them

Each layer may import only the layers listed. `tests/unit/test_layering.py`
enforces it over the real tree and proves it catches a planted breach.

| Layer | Holds | May import |
|---|---|---|
| `domain` | Pure rules: models, contained paths, planning, matching, markers, staging, redaction, errors | the standard library only |
| `ports` | Protocols the use cases need: repositories, destinations, store, metadata, artwork, clock, shell | `domain` |
| `app` | Use cases: library, metadata passes, devices, selection, plans, sync, system files, recover, maintenance, settings, support bundle | `domain`, `ports` |
| `adapters` | Implementations of the ports: SQLite, the store's file system, drives, ADB, MTP, IGDB, libretro, the Windows shell, discovery | `domain`, `ports`, their own libraries |
| `jobs` | The job registry: one worker per job, cancel tokens, conflict rules, durable records | `domain`, `ports`, `app` |
| `config` | The settings registry: every key, kind, bound and check | `domain` |
| `compose` | Builds the engine from all of the above | everything in the engine |

Nothing in the engine imports the API, the desktop shell or the interface.

### Paths a destination can be told to touch

Every path on a device is a `ContainedPath`, built by that destination's own
root (`RomsRoot` for games, `DeviceRoot` for system files). A path that would
escape its root cannot be constructed, and an adapter refuses a path built by
another destination's root. On a drive, nothing is written or removed through a
link or junction. SPEC section 3.

### Destinations

A drive, ADB and MTP each implement one destination port. A contract suite
(`tests/contract/`) runs every adapter, and a fake, through the same cases, and
is shown to fail against adapters that break each requirement. Discovery asks
every transport, lists a device it can see but not use with the reason, and
recognises a device by its `ROM-Sync.json` marker over whichever transport it
came on. SPEC section 4.

### Persistence

One SQLite database in the data folder. Every statement that shapes it is a
numbered migration step (four so far: version 1's schema, version 2's tables,
per-transport identities, hand-match pins). A step that changes rows is
preceded by a backup; a database newer than the application is refused.
Version 1's database is brought to version 2 only by the explicit importer.
SPEC section 6.

### Jobs

Long work runs as a job: scan, metadata, franchise proposals, sync, device
read, system files, recover, maintenance. Jobs that write the library exclude
one another; device jobs exclude others on the same device. A job is cancelled
between items, reports structured progress, and ends done, failed or
cancelled with its result kept. A sync's run folder carries a heartbeat, so a
run left by a crash is marked interrupted at the next start. SPEC section 8.

### Settings

Every setting is declared once in `config/registry.py` with its kind, bounds,
choices and any further check, and validated there on every write. The
interface draws its controls from that registry. A secret is described (present,
length, when saved) and never returned. SPEC section 7, and
[SETTINGS.md](SETTINGS.md) for the page.

## The API

`/api/v1/...`, FastAPI, generated into a committed OpenAPI document that the
gate checks against the application, and into the interface's typed client.

| Control | What it stops |
|---|---|
| Binds to `127.0.0.1` or `::1` only | Anything on the network reaching it. |
| Host header must be the loopback address | DNS rebinding. |
| Origin check and a per-session page token on every change, and on the folder listing | Another page or site driving the engine. |
| Frame, sniffing and referrer headers on every response, refusals included | Clickjacking and leaks through the page. |
| Path settings refuse network shares and device paths | The Windows sign-in being sent to whatever answers. |
| Errors redacted before they are shown or bundled | A secret appearing in diagnostics or the support bundle. |

SPEC sections 9 and 12, and [SECURITY.md](../SECURITY.md).

## The interface

Next.js with TypeScript, exported as static files: no Node.js at run time.

| Layer | Holds | Rule |
|---|---|---|
| `design/` | Tokens and base styles | The only place a colour is written. |
| `components/atoms`, `molecules`, `organisms` | Presentational components, each with its stories and tests | Read no store and call no query; an atom imports no molecule. |
| `lib/` | Pure functions: search grammar, facets, capacity, progress, twins, settings parsing | Each with its test. |
| `store/` | Client state (zustand): the chosen device, filters, notifications | The only module with mutable state. |
| `queries/` | Engine reads and writes (TanStack Query) over the generated client | |
| `features/` | Pages and the shell, binding components to queries and the store | A feature imports no other feature. |

The structure tests (`ui/structure/`) enforce these rules, and accessibility
across every story: labels, keyboard operation, a visible focus ring, reduced
motion, a second channel for every colour, and one live region for messages.
One fake engine (`ui/e2e/fake/world.ts`) answers in the engine's shapes for
stories, unit tests and the Playwright specs. SPEC section 10, and
[rewrite/REBUILD-UI.md](rewrite/REBUILD-UI.md).

## The desktop shell

`desktop/romsync_desktop` starts the engine and API in-process and opens the
window. Closing it stops the server, asks running jobs to stop between items,
waits up to ten seconds, and closes the database. The window's browser profile
is kept in the data folder, never the user profile. `--self-test REPORT` checks
a build headlessly: dependencies, the window's modules, that the interface is
carried, that the engine starts on the data folder and that the API answers.
SPEC section 11.

## Verification

`tools/verify.py` is the gate: twelve stages (format, lint, types, structure,
unit, contract, golden, e2e against fakes, interface, coverage floors, OpenAPI
drift, publication lint), stopping at the first failure, with no flag that
relaxes one. The same gate runs on a Windows runner for every push and pull
request, and before every release. The golden stage pins version 2's
behaviour to version 1's captured output where the two must agree.
[rewrite/TESTING.md](rewrite/TESTING.md) is the strategy.

## Where to read more

| Document | For |
|---|---|
| [rewrite/SPEC.md](rewrite/SPEC.md) | The binding specification |
| [rewrite/BACKLOG.md](rewrite/BACKLOG.md) | Every story, its acceptance and its tests |
| [rewrite/SCOPE.md](rewrite/SCOPE.md) | Decisions, non-goals and residual risk |
| [rewrite/TESTING.md](rewrite/TESTING.md) | The test strategy |
| [rewrite/REBUILD-UI.md](rewrite/REBUILD-UI.md) | The interface rebuild |
| [SETTINGS.md](SETTINGS.md) | The Settings page |
