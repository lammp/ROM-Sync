# Architecture: engine, browser UI, desktop UI

The target shape, the seams that already exist, and the order to cut them in.
Written from a read of every module. Line references are to the commit that
carries this file.

## The target

```
                      ┌──────────────────────┐
   desktop shell  ────▶│                      │
   (WebView2)         │   romsync.engine     │────▶ store (read only)
   browser shell  ────▶│   one public API     │────▶ device (3 transports)
   CLI            ────▶│   owns jobs          │────▶ SQLite
   scheduled task ────▶└──────────────────────┘
```

Four consumers, one engine. Today there are three entry points
(`app.py:13`, `server.py:638`, `__main__.py:324`), two of which start an HTTP
server, and the engine does not exist as a thing you can import.

| Module | Owns | Must not know about |
|---|---|---|
| `romsync.engine` | library, metadata, devices, selection, sync, system files, jobs, config | HTTP, JSON shapes, colours, WebView2 |
| `romsync.web` | routing, serialisation, static files, the browser shell's needs | how a sync works |
| `romsync.desktop` | the window, the WebView2 profile, native dialogs, notifications | anything the browser shell cannot also do |
| `romsync.cli` | argument parsing, text output | duplicating engine workflows |

## The decisive finding

**Jobs live in the web layer, so nothing else can have them.** `_jobs`
(`server.py:21`) and `_job` (`server.py:25`) are module-level state in the HTTP
module, and every caller is inside the request handler. The CLI has no job
concept at all; `cmd_sync` blocks on `transfer.wait` (`__main__.py:273`).

The consequence is concrete, not theoretical: a scheduled sync today requires
starting an HTTP listener on 8765 that nothing will connect to, or
reimplementing the sync workflow, which is exactly what `__main__.py:252-280`
is. That duplicate has already drifted from `server.py:572-607` in five ways,
including an unguarded marker write and a missing sync-log line.

Moving `_jobs`, `_jobs_lock`, `_job` and `_device_busy` into `romsync/jobs.py`
unchanged is the single highest-value change in the whole refactor, and it is a
cut and paste.

## Durability: runs are durable, jobs are not

| Store | Contents | Survives a restart |
|---|---|---|
| `server._jobs` | job id, state, progress, result, error | **No** |
| SQLite `sync_runs` / `sync_ops` | run, device, counts, bytes, per-op status | Yes |
| `data\runs\<id>\` | `plan.tsv`, `results.tsv`, `status.json`, `worker.log` | Yes |

So `GET /api/run/<id>` survives a restart and `GET /api/job/<id>` returns 404.
That asymmetry is the cleanest seam in the codebase: the engine already owns
durable runs and the web layer owns an ephemeral wrapper.

Restart behaviour that needs attention when the engine takes ownership:

- Volume and ADB workers are in-process daemon threads and die with the server.
  **MTP workers do not**: `_start_mtp` launches a detached PowerShell process
  (`transfer.py:551-556`) that keeps writing `status.json` with nobody left to
  ingest it.
- `sync_runs.state` stays `running` for ever. Nothing reconciles orphans at
  startup. `db.py:136` already declares a `cancelled` state that nothing writes.
- `device_files` never learns what was copied, because the inventory update is
  inside `ingest()` (`transfer.py:581-591`).
- Recovery is partly accidental: `plan()` diffs against `device_files`, so an
  unrecorded send is simply re-sent. That does not hold for removes.

There is **no cancellation anywhere**. Honour the device law when adding it: a
cancel must mean "stop after the current item", never kill a worker mid-copy.

## The engine's public surface

Derived from what the code already does. Nothing here is new behaviour.

| Group | Operations |
|---|---|
| Library | `scan_store(progress)`, `list_games()`, `game(id)`, `systems()`, `store_root()` |
| Metadata | `scrape(...)`, `enrich(...)`, `covers_libretro(...)`, `match_all(...)`, `rematch(id, ref)`, `propose_tags(dry)`, `proposed_tags()`, `set_tag`, `decide_tags` |
| Devices | `probe(force)`, `device_list()`, `device(id)`, `create_profile(ref, name, roms_root, write_marker)`, `adopt_profile(ref)`, `rename_device(id, name)`, `scan_device(id, progress)`, `write_marker(id)`, `capacity(id)`, `refresh_device_stats(id)` |
| Selection | `selection(id)`, `select_system`, `select_game`, `clear_game_override`, `select_games`, `clear_selection`, `decide`, `decide_many` |
| Sync | `plan(id, free)`, `start_sync(id) -> job`, `run_status(run)`, `pulled_items(run)`, `place_pulled(...)`, `is_device_busy(id)` |
| System files | `store_status()`, `readiness(id)`, `scan_sysfiles(id, progress)`, `stage`, `unstage`, `remove_other`, `apply` |

Operations that exist today only inside a request handler, and therefore have no
home in the domain:

- `match_all`: the `scrape` → `enrich` → `thumbs` pipeline at `server.py:432-437`.
  This is what the UI calls "Match" and it exists nowhere else.
- `start_sync`: nine domain steps at `server.py:580-602`.
- `run_status` byte arithmetic: `server.py:396-402`.
- `clear_game_override`: raw SQL at `server.py:492-494`, bypassing the minimal
  override rule `planner.set_games` implements at `planner.py:69-70`.
- `proposed_tags`: raw SQL at `server.py:417-419`.
- `rename_device`: raw SQL at `server.py:508-510`.

### Shapes that must change at the boundary

| Today | Problem | Engine should return |
|---|---|---|
| `_cand_json` returns a positional `index` (`server.py:68`), dereferenced at `server.py:466` and `:481` | The index is meaningful only within one 45-second cache generation. See the safety note below. | A content-derived `ref` built from transport kind plus serial or device and storage names, all of which `profiles.recognise` already has |
| `capacity_view` returns `"green" \| "yellow" \| "red" \| "full"` (`server.py:301-302`) | UI thresholds in the engine | `fraction` and `short_by`; each UI picks its bands. `FULL_MARGIN` stays engine policy |
| `profile_view` stringifies override keys (`server.py:227`) | JSON has no integer keys; the engine does | integer game ids |
| `library()` collapses `scrape_state` to `matched`, derives `year`, rounds `rating` (`server.py:141-145`) | Thin, and both shells want it identically | leave it, but move the function into a `views` module beside the engine rather than decomposing it |
| `run_status(brief=...)` (`server.py:405`) | Transport concern | everything; HTTP decides what to omit |
| Progress callbacks receive formatted English (`scanner.py:134`, `scrape.py:182`, `enrich.py:90`) | No UI can draw a progress bar; the counts exist and are thrown into a string | a dict of `phase`, `done`, `total`, `current` |

## The transports: what is and is not abstracted

The project claims one contract with three implementations. That holds for
**inventory and single-file work**, which is why `sysfiles.py` is transport
blind in its hot paths. It does not hold for **bulk transfer**.

`transfer.py:166-175` branches on `dest.kind` into three hand-written workers.
Those workers then reach around the abstraction: `dest._env` (a private member
of `MtpDest`) at `transfer.py:555`, `dest.root` at `:266` and `:339` (which
`MtpDest` does not have), and `dest.serial` passed straight to `adb.*` at
`:350-367`.

**The missing abstraction is `DestBulkTransfer`:** "run this op list, report per
op results and progress". Extracting it removes the kind dispatch, the private
reach-in, the direct `adb`/`ps` imports and 161 lines of inline PowerShell from
`transfer.py` in one move, putting each worker beside its transport.

Four roles, not one eleven-method interface:

| Role | Methods | Consumers |
|---|---|---|
| `DestIdentity` | `describe`, `identity`, `root_exists`, `create_root`, `read_marker`, `write_marker` | profiles, device list, marker action |
| `DestCapacity` | `capacity()` | the 45-second poll |
| `DestInventory` | `scan`, `list_paths` | `profiles.scan_into`, `sysfiles.scan` |
| `DestFiles` | `put_file`, `delete_file`, `get_file` | sysfiles staging |
| `DestBulkTransfer` | `run(ops, sink)` | `transfer.start` |
| `DestVerify` (optional, queried not sniffed) | `digest_many(paths)` | verification |

Splitting `capacity()` out of `info()` matters on its own: `MtpDest.info`
re-runs the whole system probe including the shell walk (`devices.py:325`), and
it sits on a poll that fires every 45 seconds.

### Contract divergences to settle while splitting

Same call, three behaviours. Each of these is a latent bug for any caller
written against one transport:

| Divergence | Evidence |
|---|---|
| `scan` reports failure three ways: silently, by a sentinel row, by exception | `devices.py:124` vs `:414` vs `:509` |
| `create_root` is a no-op on MTP, so `create_root(); root_exists()` holds for two of three | `devices.py:338` |
| `put_file` returns the destination size on Volume and the **source** size on MTP and ADB | `devices.py:178` vs `:390` vs `:609` |
| `delete_file` returns true when the path never existed | `devices.py:186`, `:295`, `:613` |
| `read_marker` on corrupt JSON returns `None` on two, raises on MTP | `devices.py:112`, `:487` vs `:349` |
| `info["serial"]` is a volume serial, an adb serial, or `None`, and all three land in one column | `devices.py:102`, `:466`, `:331`; `profiles.py:110` |
| `progress` is honoured by two of three | `devices.py:133`, `:517`, `:404` |

## Policy versus IO

`planner.py` is already the engine: pure policy over `db`, no HTTP, no UI, no
device. `plan()` never receives a dest, and the module imports nothing from
`devices`, `adb` or `ps`.

Four things stand between that and a unit test:

| # | Obstacle | Evidence |
|---|---|---|
| 1 | `db.connect()` is hardwired to one path derived from `__file__`; no parameter, no override | `db.py:189-203` |
| 2 | `planner` imports `transfer` only for two DTO factories, inverting the dependency | `planner.py:12`; `transfer.py:55-66` |
| 3 | `op_from_game` reads configuration, so even the op shape is not pure | `transfer.py:64` |
| 4 | The 512 MB fit margin is defined twice | `planner.py:174` and `server.py:239` |

Move `make_op`/`op_from_game` into an `ops` module, give `db.connect` a path
parameter, and the mirror diff becomes a pure function over dicts.

**One ordering decision is written four times:** remove, then update, then send,
at `planner.ops_of`, `transfer.py:262`, `:334` and in the MTP worker phases.

## `sysfiles.py` divides in three

509 lines with three independent reasons to change: a new emulator, a new
transport, a UI change.

| Unit | Contents |
|---|---|
| `sysfiles/registry.py` | `LOC`, `ANDROID_DATA`, `STAGE`, `R()`, `SYSTEMS` (40 lines of pure data that changes when an emulator does) |
| `sysfiles/store.py` | store-side resolution, hashing, the process cache (`:107-163`) |
| `sysfiles/device.py` | path computation, device hashing, scan, the mutations (`:168-264`, `:420-495`) |
| `sysfiles/readiness.py` | the 127-line state machine at `:289-415`, which is where the UI vocabulary lives |

## SOLID findings, in priority order

| # | Principle | Evidence | Consequence today | Smallest fix |
|---|---|---|---|---|
| 1 | SRP | `_api_post` is 203 lines (`server.py:424-626`) | **Three unreachable duplicate branches shipped**: `rename` at `:542` duplicates `:507`, `scan` at `:546` duplicates `:511`, `scan-sysfiles` at `:553` duplicates `:518`. Nineteen lines that can never run, inside the method that performs device writes | Delete `:542-560`, then reduce each branch to one engine call |
| 2 | DIP | jobs are web-layer state (`server.py:21-45`) | No headless or scheduled sync without an HTTP listener | Move to `romsync/jobs.py` verbatim |
| 3 | Global mutable state | `_cands` with a 45 s TTL (`server.py:50-56`); the UI holds a positional `index`; `profile/new` dereferences it (`:466`) and **mutates the shared cache entry** (`:469`) | A stale index can point at a different device, and `profile/new` then calls `create_root()` and writes `ROM-Sync.json` to it. Since the marker is the identity join, that is a wrong-device write with lasting effect. Two shells make it likelier | Stable `ref` in `profiles.recognise`; look up by `ref` |
| 4 | SRP | `capacity_view` runs `UPDATE devices SET capacity=?, free=?` inside a GET (`server.py:280`) | A polled read writes the database; two shells means two writers on one row | Extract `refresh_device_stats` and call it from the probe path |
| 5 | DRY | the fit margin at `planner.py:174` and `server.py:239` | The meter can say "full" while the sync proceeds | `planner.FULL_MARGIN`, referenced from both |
| 6 | SRP | raw SQL in handlers: `server.py:492`, `:508`, `:417` | Two code paths write selection state with different semantics; the engine would not reproduce the UI's behaviour | `planner.clear_game`, `devices.rename`, `tags.proposed` |
| 7 | ISP | `settings_view` runs six queries plus two directory walks plus a jobs read (`server.py:185-204`) | A headless caller asking "how many unmatched" walks `data\covers` file by file | Split into `counts`, `paths`, `storage_stats`, `jobs` |
| 8 | Reliability | `_jobs` is never evicted; `server.py:392` and `:204` read it without the lock while `_job` writes `finished` from a worker thread (`:42`) | Unbounded growth holding every job result; a `dictionary changed size during iteration` on a poll is plausible | Copy under the lock, pre-create every key, evict terminal jobs |
| 9 | DIP | `igdb.credentials()` reads **and writes** the config table, and opens a second SQLite file on a hardcoded path (`igdb.py:21-41`) | An HTTP client that needs a database and silently saves credentials the user never typed | Require credentials at `Client.__init__`; the host supplies them |
| 10 | DIP | `scrape.py:151`, `:207` and `enrich.py:47` each build their own `igdb.Client`, and the throttle is per instance (`igdb.py:50`) | Two concurrent passes issue 8 req/s against a 4 req/s budget | `client=None` parameter, one shared instance |
| 11 | SRP | `scanner.py:112-190`: `seen` is only filled for systems whose `systeminfo.txt` parsed, and `read_systeminfo` returns empty on any `OSError` (`:61`), then the prune deletes every row not in `seen` (`:182`) | **A locked or unreadable `systeminfo.txt` silently deletes that system's games**, cascading into `game_files` and `selection_overrides` | Scope the prune to systems actually visited; never prune when zero systems indexed; distinguish absent from unreadable |
| 12 | SRP | `reason.py:16-354` is a 300-row lookup table in Python syntax | A franchise fix needs a code change. The table already carries errors it cannot be corrected out of: `:352` maps Green Lantern to Marvel | Move the rules to a data file; `reason.py` becomes a loader plus the matcher |
| 13 | OCP | schema applied from three places, two lazily (`db.py:201`, `tags.py:25`, `enrich.py:31`), with `ensure()` sprinkled defensively | Table existence depends on call order | One `migrations.py`, run once at startup |
| 14 | Correctness | `enrich.py:85` writes `games.similar`, guarded by `_has_column`; `games` has no such column and `CREATE TABLE IF NOT EXISTS` will never add it | `similar_games` is requested in every enrich query, paid for, and always discarded. The guard is a live workaround for the missing migration mechanism | Add the column in a migration, or drop the field from the query |

## Migrations

There is no migration mechanism. `connect()` runs `executescript(SCHEMA)` with
every statement `IF NOT EXISTS` (`db.py:193-203`), so a new column in `SCHEMA`
is silently ignored on an existing database and the failure arrives later as
`no such column`. There is no version marker; `meta` holds exactly one key.

Minimum viable mechanism, in order:

1. Set `PRAGMA user_version = 1` for the current shape, treating 0 as version 1.
2. Collect all DDL, including the `tags.py` and `enrich.py` fragments, into one
   ordered idempotent list.
3. Run it once at startup under a process lock, inside a transaction, after
   copying the database aside. **Not inside `connect()`**, which runs per thread.
4. Delete every `ensure()` call.

Adding a column to a 654 MB database is metadata-only and effectively free.
Dropping or retyping one is a full table rebuild, and `PRAGMA foreign_keys=ON`
plus the cascades at `db.py:92-100` will take the selection rows with it unless
foreign keys are disabled for the rebuild.

## Two shells, one page

The honest finding: **nothing in the UI touches a desktop API today**. No
`window.chrome.webview`, no `pywebview` bridge, no file input, no clipboard
call, no `window.open`. Both shells are served over HTTP. The browser shell
already works.

What leans one way is layout and dialogs: `html,body{overflow:hidden}` and a
fixed 52px header (`app.css:7,22`) assume an app window; a 260px rail plus a
420px detail panel need about 1000px; `modal` has `min-width: 420px`
(`app.css:153`); and native `confirm`/`prompt` are used in six places
(`app.js:545,552,563,860,926,929`).

The thinnest abstraction is one object, `ui/platform.js`, chosen at load:

```js
const Platform = {
  kind: 'browser',              // or 'desktop'
  can(feature),                 // pickFolder | reveal | notify | quit
  confirm(opts), promptText(opts),
  pickFolder(opts), reveal(path), openExternal(url), copy(text),
  notify(opts), quit(),
};
```

Most of the desktop implementation is the **server**, not a webview bridge: the
server already runs on the user's machine with their rights, so `reveal`,
`pickFolder` and `openExternal` are local API calls. Only native notification,
quit and a dropped file's real path need the host.

Capability detection comes from the server, not from sniffing: `GET /api/settings`
gains `shell: {kind, address, port, can: [...]}`, set from whether `app.py`
created a window. The adapter starts in browser mode and upgrades once settings
load, and every method degrades, so nothing breaks in the gap.

Where this loses, stated up front:

1. The folder picker opens on the **server's** desktop. Correct only while the
   server is loopback-bound. Gate `pickFolder` and `reveal` on that.
2. Drag and drop cannot be unified: a browser `drop` yields a `File` with no
   path. Recommendation is not to build it; the store lives on disk and the
   scanner reads it.
3. Native notifications have no delivery guarantee, so the toast stays the
   source of truth rather than the fallback.

## What not to change

| Keep | Why |
|---|---|
| The dest contract for inventory and single files | Three implementations, callers blind to which. The one place the codebase already does DIP properly |
| `planner.py` entire | Pure policy, no globals, deterministic given the database. It is already the engine |
| `transfer.py` run folders and `status.json` | Deliberately out of process because the MTP worker **is** out of process, and the only reason an interrupted run is observable at all |
| `.rs-part` then `os.replace` | A kill leaves an orphan, never a corrupt game file |
| `db.connect()` per-thread connections, WAL, 30 s busy timeout, foreign keys on | Correct choices for a threaded local server over SQLite |
| The game-unit model: one row per unit, `kind` file or folder, members in `game_files` | The right abstraction for multi-disc sets and folder games, and the hardest thing here to get right |
| Parameterised SQL everywhere | Reviewed: no injection is reachable on any path. Do not tidy these into f-strings |
| `_sync_log` as a TSV, including its `except: pass` | The triage workflow starts from these files, and the log must never fail a sync |
| `app.py` as the desktop shell, at 34 lines | Already the Windows module. It needs the engine to exist, not more abstraction |
| The `/api` JSON shapes | Both shells consume them. Freeze them |
| Atomic image download, cover preservation on re-match, `INSERT OR IGNORE` on tags | Each is a considered behaviour that is easy to break by accident |

### Boundaries not worth drawing

- **No view layer over `library()` and `game_detail()`.** The shaping is a year,
  a boolean, a rounded rating and a JSON parse, and both shells want it
  identically. Move the functions, do not decompose them.
- **No repository or ORM over `db.py`.** The SQL in `planner`, `profiles` and
  `sysfiles` is specific and readable. The problem is that *`server.py`* writes
  SQL. Fix those four sites and stop.
- **No plugin shape for metadata sources.** There will never be a fifth.
- **No abstract "shell" interface.** Two shells is not enough shells to justify
  one.

## Work order

Steps 1 to 6 are mechanical, change no behaviour a UI can see, and leave
`server.py` as transport over an engine the CLI and a daemon can call.

| # | Change | Size | Unblocks |
|---|---|---|---|
| 0 | The two containment fixes and the static-path fix (tracked privately until released) | small | publishing a browser UI at all |
| 1 | Delete `server.py:542-560` | minutes | reading the file |
| 2 | `romsync/jobs.py`: move `_jobs`, `_job`, `_device_busy` verbatim | small | headless jobs |
| 3 | `sync.start(device_id)`: move `server.py:580-602`; both the route and the CLI call it | small | one sync, one marker behaviour, one sync log |
| 4 | Stable candidate `ref`; stop dereferencing by index | small | two shells safely; removes the wrong-device write |
| 5 | `device_registry` module for the probe cache; extract the write out of `capacity_view` | small | GETs stop writing |
| 6 | `planner.FULL_MARGIN`, `planner.clear_game`, `tags.proposed`, `devices.rename` | small | one definition per rule |
| 7 | `views` module for `library`, `game_detail`, `profile_view`, `plan_view`, `device_entries`, `settings_view` | medium | `server.py` becomes routing plus `_json` and `_file` |
| 8 | `config` registry and the Settings work (see [SETTINGS.md](SETTINGS.md)) | medium | portability, and the hardcoded paths in [KNOWN-LIMITATIONS.md](KNOWN-LIMITATIONS.md) |
| 9 | `migrations.py` with a version marker | medium | any schema change on a live database |
| 10 | `DestBulkTransfer`; move the three workers beside their transports | large | `transfer.py` loses its kind dispatch and its private reach-in |
| 11 | Persist job records, reconcile `running` rows at startup, add cooperative cancellation | medium | restart safety; real job ownership |
