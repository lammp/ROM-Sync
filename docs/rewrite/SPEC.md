# ROM-Sync 2: specification

Normative. Every statement is a requirement.

## 1. Layout

```
engine/
  romsync/
    domain/        pure. stdlib only. no IO, no clock, no randomness
      models.py        GameUnit, SystemKey, Selection, Plan, Op, DeviceRef
      identity.py      title normalisation, twin keys
      selection.py     selection algebra
      planning.py      the mirror diff and its guards
      paths.py         ContainedPath, RomsRoot, StoreRoot
      errors.py        the domain error taxonomy
    ports/         Protocol definitions only. no implementations
      store.py         StorePort
      dest.py          DestIdentity, DestCapacity, DestInventory, DestFiles,
                       DestBulkTransfer, DestVerify
      metadata.py      MetadataPort
      repo.py          GameRepo, DeviceRepo, SelectionRepo, RunRepo, JobRepo,
                       ConfigRepo, TagRepo, SysfileRepo
      clock.py         ClockPort, IdPort
      sink.py          ProgressSink, JobSink
    app/           use cases. depends on domain + ports only
      library.py metadata.py devices.py selection.py sync.py sysfiles.py
      maintenance.py diagnostics.py
    adapters/
      db_sqlite/       repositories, schema, migrations
      store_fs/        filesystem scanner
      dest_volume/ dest_adb/ dest_mtp/ dest_fake/
      metadata_igdb/   client, throttle, matcher
      shell_win/       reveal, pick folder, open external
    jobs/          registry, persistence, cancellation, reconciliation
    config/        registry definition, loader, validators
    compose.py     the composition root: builds an Engine from config
api/
  romsync_api/     FastAPI app, DTOs, routers, error envelope, OpenAPI export
desktop/
  romsync_desktop/ pywebview shell, window, native dialog endpoints
ui/                TypeScript, Vite, generated client
installer/         PyInstaller spec, Inno Setup script, dependency checks
tools/             verify.py (the gate), import_v1.py, openapi_check.py
tests/             unit, contract, golden, e2e_fake
```

## 2. Dependency rule

`domain` imports stdlib only. `ports` imports `domain` only. `app` imports
`domain` and `ports` only. `adapters` import `domain`, `ports` and their own
third-party libraries. `api` and `desktop` import `app` and `compose`. Nothing
imports `api`, `desktop` or `ui`.

The rule is enforced by a test, not by convention: `tests/unit/test_layering.py`
walks the import graph and fails on any edge that violates the order above.

## 3. Contained paths

`domain/paths.py` defines `ContainedPath`. It is constructed only by
`RomsRoot.resolve(relative)` or `StoreRoot.resolve(relative)`. Construction:

1. rejects an absolute input,
2. rejects any input containing a path separator where a single name is required,
3. normalises the result,
4. asserts the normalised result is inside the root,
5. raises `PathEscape` otherwise.

No function in `ports` or `adapters` that deletes, writes or reads a file
accepts `str` for a path. Signatures take `ContainedPath`. This is the
structural replacement for call-site validation.

`tests/unit/domain/test_paths.py` includes the escape corpus: `..`, nested `..`,
a separator inside a name, a drive-qualified absolute, a UNC path, a trailing
dot, a reserved Windows device name, and a symlink target outside the root.

## 4. Destination ports

Six roles. An adapter implements the roles it can honour and declares them.

| Port | Methods |
|---|---|
| `DestIdentity` | `describe()`, `identity()`, `root_exists()`, `create_root()`, `read_marker()`, `write_marker(marker)` |
| `DestCapacity` | `capacity()` returning total and free |
| `DestInventory` | `scan(systems, sink)`, `list_paths(paths)` |
| `DestFiles` | `put_file(folder, src)`, `delete_file(path)`, `get_file(path, dst_dir)` |
| `DestBulkTransfer` | `run(ops, sink, cancel)` returning a terminal result per op |
| `DestVerify` | `digest_many(paths)` |

Capability is queried, never sniffed: `Dest.supports(Port) -> bool`. No caller
branches on a transport name. `tests/unit/test_no_kind_branching.py` greps the
`app` and `api` trees for transport-name comparisons and fails on a match.

### Contract requirements, binding on every adapter

| # | Requirement |
|---|---|
| C1 | Failure is an exception from the port's error taxonomy. No sentinel rows, no empty result standing for an error. |
| C2 | `create_root()` either creates the root or raises. It never silently does nothing. |
| C3 | `put_file` returns the size measured at the destination, never the source size. |
| C4 | `delete_file` returns only after the path is absent, and distinguishes "deleted" from "was not there" by return value. |
| C5 | `read_marker` returns `None` for absent or unparsable, and never raises for malformed content. |
| C6 | `identity()` returns a typed identity naming its own kind. One adapter's serial never lands in another's column. |
| C7 | `capacity()` performs no device-wide probe and has no side effects. |
| C8 | `scan` and `run` report progress through the sink, with structured events. |
| C9 | `run` honours the cancel token between items and never inside a copy. |
| C10 | An interrupted `run` leaves no file at a final name that was not fully written. |

`tests/contract/test_dest_contract.py` is parameterised over `dest_fake`,
`dest_volume` against a temp directory, and, when a device is present and an
opt-in marker is set, `dest_adb` and `dest_mtp`. The default run uses the fake
and the volume adapter only, so the gate stays deterministic.

## 5. Domain rules

| Rule | Requirement |
|---|---|
| Game unit | One unit per game. `kind` is `file` or `folder`. A multi-disc set is one unit with its members listed. |
| Title identity | Lowercase, ampersand to "and", apostrophes dropped, leetspeak folded, non-alphanumeric to a separator, stop words dropped, roman numerals to digits. A loose key additionally drops trailing edition words. |
| Selection | A system mode of `all`, `none` or `off`, plus per-game overrides. An override that agrees with the mode is not stored. |
| Plan | A mirror diff over the selection producing `send`, `update`, `remove`, `unchanged` and `unknown_systems`. |
| Guards | `UNMANAGED_ALWAYS` names what is never managed. `EMULATOR_STATE` names folders inside a managed system that are never removed. `bios` is never treated as games. |
| Guard placement | The guard is enforced at the destructive site, not only in the planner. A `remove` whose resolved basename is in `EMULATOR_STATE` is refused by the transfer engine regardless of recorded kind or of who built the op. |
| Fit | `plan.bytes.fits` models peak usage, not net. Where the adapter writes the replacement before removing the original, the old size counts towards the peak. |
| Fit margin | One constant, `planning.FULL_MARGIN`, read from config. No second definition. |
| Ordering | Remove, then update, then send. Defined once, in `planning.ops_of`. |

## 6. Persistence

| Requirement |
|---|
| SQLite, WAL, foreign keys on, busy timeout from config. |
| Schema version in `PRAGMA user_version`. An unversioned existing database reads as version 1. |
| Migrations are an ordered list of forward-only steps. Each is idempotent and transactional. |
| Migrations run once, at startup, from the composition root, under a file lock, before any worker thread opens a connection. Never from `connect()`. |
| A backup copy of the database file is taken before any migration that is not metadata-only. |
| All DDL lives in the migration list. No module creates its own tables, and no `ensure()` function exists. |
| Repositories return domain models or DTOs. No sqlite row escapes a repository. |
| Every statement binds its values. No identifier or value is interpolated into SQL. |
| Config is stored as one row per key, not as a single JSON blob. Secrets are stored under a separate key namespace so they can be read, replaced and deleted independently. |
| A config write is a single upsert of the keys supplied. It never rewrites keys it was not given. |

## 7. Config registry

Every tunable is declared once, in `config/registry.py`, with: key, type,
default, range or allowed values, whether it is a secret, whether it takes
effect only at startup, and a one-line description.

| Requirement |
|---|
| `GET /api/v1/settings` returns the registry alongside the current values, so the interface renders its controls from the registry. |
| `POST /api/v1/settings` validates against the registry, applies only supplied keys, deletes a key sent as `null`, and returns a per-field error on rejection. |
| No default is an absolute path. Path defaults are relative to the install or are empty. |
| A secret is never returned. The response carries presence, length, when it was saved, and where it came from. |
| Minimum registry coverage: store root, data directory, adb path, adb enabled, MTP enabled, firmware folder, device staging template, staged hash limit, device probe interval, free-space margin, warn thresholds, confirm-remove threshold, write marker after sync, verify percentage, IGDB client id, IGDB secret, IGDB requests per second, match acceptance threshold, auto libretro covers, auto enrich, preferred port, log level, rescan on launch, job history length, run folder retention. |

## 8. Jobs

| Requirement |
|---|
| `jobs` is a first-class engine service, usable without the HTTP layer. |
| A job record is persisted on creation and on every state change: id, kind, target, state, progress, result, error, started, finished. |
| States are `queued`, `running`, `cancelling`, `done`, `failed`, `cancelled`. |
| Progress is a structured event: phase, done, total, current item. Never a formatted sentence. |
| Cancellation is cooperative. A cancel sets the token; a worker checks it between items and never inside a copy. |
| At startup the engine reconciles: any job or run left `running` is marked `failed` with the reason `interrupted`, and an out-of-process worker is detected by its run folder rather than assumed dead. |
| A guard prevents two jobs of conflicting kind running against the same target. The guard is by kind and target, not device-only. |
| Terminal jobs older than the configured history length are evicted. |
| Reads return a snapshot taken under the lock. A reader never observes a partially updated record. |

## 9. HTTP API

| Requirement |
|---|
| Version prefix `/api/v1`. The OpenAPI document is generated and checked into the repository; `tools/openapi_check.py` fails the gate on undeclared drift. |
| Request and response bodies are declared models. No endpoint returns an ad-hoc dict. |
| Errors use one envelope: `{"error": {"code", "message", "field"}}`. |
| No endpoint performs a write on a GET. |
| Binds loopback by default. Binding to any other interface requires an explicit config value and logs a warning naming what that disables. |
| Mutations require a same-origin check and a token issued to the page. A cross-origin request cannot reach a mutation. |
| Static assets are served from a built manifest, by name lookup. No path is joined from a request. |
| `/api/v1/shell/*` endpoints are available only while the bind is loopback, and refuse any path outside the configured roots. |
| Long operations return a job. The only synchronous operations are reads and settings writes. |

## 10. Interface

| Requirement |
|---|
| TypeScript, strict mode, built by Vite to a static bundle served by the engine. |
| The API client is generated from the OpenAPI document. No hand-written fetch wrapper. |
| One state container. No module-level mutable state outside it. |
| Behaviour parity with version 1 for: the search grammar, facet counts and ordering, sort options, the windowed grid, the detail panel, the twin badge and compare card, the device page, the sync modal, the system files page. |
| A platform adapter chosen at load from the shell reported by the engine. Methods: confirm, prompt, pick folder, reveal, open external, copy, notify, quit. Each degrades in the browser. |
| No native `confirm`, `prompt` or `alert`. |
| The Settings page is implemented to [SETTINGS.md](../SETTINGS.md). |
| Every interactive element is reachable and operable by keyboard. Elements that act as buttons are buttons. |
| Modals carry a dialog role and an accessible name, move focus in, trap focus, and restore focus on close. |
| Every input has a programmatically associated label. |
| The live region announces every toast. |
| Text and non-text contrast meets WCAG AA, verified by a test over the token set. |
| State is never carried by colour alone. |
| A failed fetch produces an error state with a retry, never a permanent loading state. |
| A job poller survives navigation and does not write to a detached node. |

## 11. Installer and first run

| Requirement |
|---|
| The release artefact installs without a Python installation present. |
| The installer checks and reports: Windows version, WebView2 runtime, available disk space on the install target, and write access to the data directory. A missing WebView2 runtime offers the Microsoft bootstrapper and does not proceed silently. |
| `adb` is optional. Absence disables the ADB transport and is stated in Settings, not as an error. |
| The data directory is chosen at first run and defaults outside the install directory, so replacing the application cannot touch it. |
| A first run on a machine with no prior installation reaches a working catalogue through the interface alone: choose a store root, scan, optionally add credentials. No file is edited by hand. |
| No BIOS, firmware, key or ROM is bundled, fetched or referenced by a default path. |
| The uninstaller removes the application and leaves the data directory, stating so. |
| `tools/import_v1.py` imports a ROM-Sync 1 database from a path given by the user: games, selections, tag decisions and device profiles. It is opt-in, never automatic, and refuses to write into a non-empty version 2 database. |

## 12. Security requirements

| # | Requirement |
|---|
| S1 | No destructive operation accepts a string path. See section 3. |
| S2 | Static assets are resolved by manifest lookup. No join from request input. |
| S3 | Mutations require a same-origin check and a page token. |
| S4 | A marker file read from a device is untrusted input. Every path in it is validated on ingress and again at the destructive site. |
| S5 | A secret is never returned by the API, never written to a log, and never included in a support bundle. |
| S6 | Credentials are supplied to the metadata client by the composition root. The client does not read or write storage. |
| S7 | A transfer that was not content-verified records no hash. |
| S8 | An interrupted run never leaves a file at its final name. |
| S9 | The publication lint and the secret-scan gate run inside the verification command. |
