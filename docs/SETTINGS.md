# The Settings page

A design, detailed enough to implement from. It assumes the config registry in
[ARCHITECTURE.md](ARCHITECTURE.md) step 8, and the `Platform` adapter from the
same document.

## Why it needs redoing

The page works. Four things are wrong with it structurally, and each shows up as
a user problem rather than a tidiness complaint.

| Problem | Evidence | What the user experiences |
|---|---|---|
| Four equal cards in an auto-fill grid, so there is no order | `app.js:1096-1160`, `app.css:28` | Nothing says store root first, then credentials, then rescan. Reflow at a different width changes which card is met first |
| Only three keys can be saved at all | `server.py:446` whitelists `store_root`, `client_id`, `client_secret` | Twelve values a different machine needs are module constants with no path to them |
| An empty value is dropped rather than applied | `server.py:448-449` | **No setting can ever be cleared.** A stale secret cannot be removed |
| Every job completion re-renders the whole page | `app.js:1149-1159` | A half-typed secret is lost when a rescan finishes |

Three more, worth naming:

- **Nothing is validated** beyond one `isdir` check on the store root
  (`server.py:450`). A valid folder that is not a ROMs tree is accepted
  silently; the user learns nothing until a rescan returns zero systems.
- **No destructive or expensive action confirms** except Re-match everything
  (`app.js:1154`). Rescan store rewrites the authoritative inventory. Retry
  not-found starts a network job over every unmatched game at 4 requests a
  second. None of the five metadata buttons is disabled while a job runs, and
  `POST /api/scrape` has no running-job guard, so two clicks start two
  concurrent scrapes sharing one rate limiter and writing into the same progress
  element.
- **Credentials can appear that the user never typed.** `igdb.credentials()`
  falls back to a retired application's database and *saves what it finds*
  (`igdb.py:32-40`), while `settings_view` reads only the app config
  (`server.py:188`). So the field can fill with a value from nowhere, and the
  page has no way to say where it came from.

On restarts, the good news: verified, **neither editable setting needs one**.
`db.store_root()` and `igdb.credentials()` both re-read config on every call.
What is read once at startup is the HTTP port and the WebView storage path. The
page should say so rather than spraying restart warnings it does not need.

## Principles

- One page, one scroll, sections in first-run order.
- Every section states its own readiness. Only a section with a problem is loud.
- Saving is explicit and **per section**, so one section's job cannot discard
  another's edit.
- Destructive and long actions share one confirmation component, with a
  typed-word gate reserved for the irreversible two.
- A running job is visible from anywhere on the page, not only from the card
  that started it.
- Nothing is read-only prose where an action is possible: a path gets Reveal and
  Copy, a size gets a breakdown, a credential gets a test.

## Information architecture

```
Settings
├─ 0  Setup                 shown only while incomplete
├─ 1  Library
├─ 2  Metadata and artwork
├─ 3  Tag suggestions
├─ 4  Transports and tools
├─ 5  Sync behaviour and guards
├─ 6  Data and storage
├─ 7  Diagnostics
└─ 8  Suggested tags review  the existing list, moved last
```

Single column, about 900px wide, `<section>` with an `<h2>` and a status pill.
Keep `.card`, `.field`, `.stat`, `.pill` and `.job` exactly as they are; the
only new CSS is a two-column label/control grid and a sticky section nav on wide
viewports. Section 8 stays full width because it is a work queue, not a setting,
and it is already good.

### Section 0, Setup

A view over existing data, no new state. Shown while any of three conditions
holds: no store root, zero systems, no credentials.

| Step | Complete when | Action |
|---|---|---|
| 1. Point at your ROMs folder | `counts.systems > 0` | scrolls to Library |
| 2. Read the library | `counts.games > 0` | runs Rescan store |
| 3. Add IGDB credentials for covers and details | `has_secret && client_id` | scrolls to Metadata, with one line noting libretro box art needs no account |

Collapses to a single dismissible "Setup complete" line when all three are met.

## Field specifications

Legend: **restart** means it is read once at startup. Everything unmarked takes
effect immediately, because the server re-reads config per call.

### 1. Library

| Field | Control | Validation | Default | Restart |
|---|---|---|---|---|
| Store root | text + Browse + Reveal | must exist and be a directory; **new:** must contain at least one subfolder with a recognised extension, else save with a warning "no systems found here"; reject a path equal to or inside the data folder | `D:\Games\ROMs` (`db.py:248`) | No, but the loaded library is stale: call `loadLibrary()` on success and offer Rescan inline |
| Systems table | read-only: system, games, folders, bytes, matched | n/a | `db.system_rows()`, which already returns exactly this and is currently unused by the UI | n/a |
| Rescan store | button, confirms when `counts.games > 0` | n/a | n/a | n/a |
| Rescan on launch | checkbox | n/a | off | **Yes** |

The systems table is the highest-value single addition on the page: it answers
"did the path I just typed actually work" without a trip to the Library view.

### 2. Metadata and artwork

| Field | Control | Validation | Default | Secret |
|---|---|---|---|---|
| Twitch Client ID | text, `autocomplete="off"` | trim, non-empty, soft format warning rather than a hard block | `""` | No, echoed as today |
| Client Secret | see [the credential section](#the-igdb-credentials-specifically) | trim, warn under 20 characters, never submitted when untouched | unset | **Yes** |
| Credential status | read-only line | n/a | derived | n/a |
| Test connection | button | n/a | n/a | n/a |
| Match acceptance threshold | number 0.30–0.95 step 0.05, with "lower matches more games, and more wrongly" | range | 0.55 (`scrape.py:19`) | No |
| Requests per second | number 1–4 | hard cap 4 | 4 (`igdb.py:20`) | No |
| Fill missing covers from libretro after a match | checkbox | n/a | on, which is what happens unconditionally today (`server.py:436`) | No |
| Fetch screenshots and tags after a match | checkbox | n/a | on, same (`server.py:435`) | No |
| Counts | five read-only stats, as today | n/a | n/a | No |

Actions: Match new (N) · Retry not-found (N) · Fill missing covers (N) · Fetch
screenshots and tags · Re-match everything. Each names its count, so the user
knows the size of what they are starting. Each is disabled when its count is
zero and while any metadata job runs. The three network-heavy ones confirm with
the count and an estimate derived from the rate limit. Re-match everything keeps
its modal and gains a typed-word gate.

### 3. Tag suggestions

| Field | Control | Default |
|---|---|---|
| Awaiting review | read-only count, links to section 8 | `counts.proposed` |
| Propose franchise tags | button, disabled while running | n/a |
| Clear all unreviewed proposals | button, confirms with the count | n/a |

`POST /api/reason` runs inline today (`server.py:443`), blocking its request
thread and defeating the job UI, which then prints raw JSON. Make it a job like
its peers.

### 4. Transports and tools

| Field | Control | Validation | Default |
|---|---|---|---|
| ADB executable | text + Browse + Detect + Reveal, with a found / not found pill | must be an existing file; **new:** run `adb version` and show it, else reject with that error | `_tools\platform-tools\adb.exe`, then PATH (`adb.py:20,27`) |
| Enable ADB transport | checkbox, "faster, needs USB debugging" | n/a | on when adb is found |
| Enable MTP transport | checkbox | at least one transport must stay enabled | on |
| Firmware folder | text + Browse + Reveal | must exist if set; empty disables firmware staging | `_firmware` (`sysfiles.py:39`) |
| Staging path on the device | text template with `{roms}` and `{system}` | must contain `{system}`, must be relative, no `..` | `{roms}/bios/{system}` (`sysfiles.py:41`) |
| Verify staged files up to | size input, same syntax as the library filters | 0 to 256 MB | 32 MB (`sysfiles.py:40`) |
| Device probe interval | number, seconds | 15 to 300 | 45 (`server.py:56`) |

Changing the staging path orphans anything already staged, so it confirms and
says so. A read-only Detected transports line belongs here too, fed by
`/api/devices`, so ADB and MTP can be told apart without leaving Settings.

### 5. Sync behaviour and guards

| Field | Control | Validation | Default |
|---|---|---|---|
| Keep free on the device | size input | 0 to 8 GB | 512 MB (`server.py:239`) |
| Warn at | two numbers, yellow % and red % | 50 ≤ yellow < red ≤ 99 | 80 and 90 (`server.py:301`) |
| Confirm a sync that removes more than | number of items, 0 means always | ≥ 0 | 0, matching today's always-confirm modal |
| Write the device marker after every sync | checkbox | n/a | on, unconditional today (`server.py:596`) |
| Protected folders inside a managed system | **read-only** list with a note | n/a | `planner.EMULATOR_STATE` |
| Folders that are not store systems | read-only, "left alone" | n/a | behaviour is fixed |
| Verify a percentage of sent files by hash | number 0–100 | range | 0 |

The protected-folders list is read-only on purpose. It is a law of the project,
and an editable list invites a user to delete the entry that stops a sync eating
their saves. Showing it is what makes the sync modal's "nothing is wiped" claim
evidenced rather than asserted.

### 6. Data and storage

| Field | Control | Notes |
|---|---|---|
| App folder, Data folder | read-only path + Reveal + Copy | |
| Storage breakdown | table: component, files, bytes, share, action | new endpoint |
| Compact the database | button with a reclaimable estimate | runs `VACUUM`; refuses while any job runs |
| Clear the screenshot cache | button, confirms with the size | screenshots refetch on demand |
| Delete unreferenced covers | button, confirms with count and size | covers no game points at |
| Keep sync run folders for | select: forever / 90 / 30 days | forever today |
| Keep job history | number 8–200 | 8 today (`server.py:204`) |

Breakdown rows: database, covers split into IGDB and libretro (the counts
already distinguish them), screenshots, logs, run folders, records, and the
**WebView profile**. The last one matters: a Chromium profile grows unbounded
and is the most sensitive thing in the data folder. Show its size with a Clear
action.

Today's figures come from `_dir_stats` (`server.py:175`), which counts top-level
files only and does not recurse, so the covers and screenshot numbers are
already understated.

### 7. Diagnostics

| Field | Control | Notes |
|---|---|---|
| Shell | read-only: desktop window or browser, plus the WebView2 version when known | from the `shell` block |
| Address | read-only `http://127.0.0.1:<port>/` + Copy | the port is ephemeral in the window |
| Preferred port | number, 0 or 1024–65535, "0 picks a free port" | **restart** |
| Jobs | table: kind, started, state, progress, duration, Cancel | replaces the static "running now" line |
| Recent errors | last N failed jobs, full traceback in a `<pre>` + Copy | the traceback is already kept |
| Last sync | device, when, sent/removed/failed, bytes, link to the device page | from the sync log |
| Log folder | read-only path + Reveal + Open latest | |
| Log level | select: normal / verbose | **restart** |
| Export a support bundle | button | zip of recent job records, the sync log, settings **with the secret redacted**, system info |
| Version | read-only | |

The jobs table replaces three worse things: a static one-liner, per-card
progress elements as the only surface, and the complete absence of a cancel. It
also makes a slow job legible after navigating away, which it is not today.

## The IGDB credentials, specifically

The secret never reaches the page in either direction, except on save. That is
already true (`server.py:193` sends only `has_secret`) and the design
strengthens the contract around it.

**What the server sends:**

```json
"igdb": {
  "client_id": "abcd1234...",
  "has_secret": true,
  "secret_length": 30,
  "secret_saved_at": "2026-10-08T04:11:00+00:00",
  "secret_source": "typed",
  "last_test": { "at": "...", "ok": true, "detail": "token ok, 1 platform read" }
}
```

No fingerprint, no first or last characters, no hash. A published digest of a
30-character secret reduces its secrecy for no user benefit; the length and the
save date identify the key well enough for a human to recognise it.

**What the page shows instead:**

- **Set:** `Saved 8 Oct 2026 · 30 characters · not shown again`, with Replace
  and Remove. The input does not exist until Replace is pressed, so there is
  nothing to focus, nothing to autofill and nothing to submit by accident.
- **Set, and `secret_source` is `imported`:** add `imported from RomCurator`.
  This closes the hole where credentials appear that the user never typed.
- **Unset:** `Not set. Covers and details need Twitch credentials; libretro box
  art does not.` with one Add credentials button revealing both fields.
- **The revealed input:** `type="password"`, `autocomplete="new-password"`, no
  `value` attribute ever, a Show toggle that reveals only what was just typed,
  and a rule that a focused-then-abandoned field submits nothing.

**Test connection** is a separate action, not a side effect of saving, and it
works on unsaved input so a typo is caught before it is stored.
`POST /api/igdb/test` with an optional body; an empty body tests what is saved.
It never echoes either value back, and it reports which stage failed, because
the two failures have different fixes:

| Stage | Returns |
|---|---|
| credentials missing | `{ok: false, stage: "missing"}` |
| token | `stage: "token"`; HTTP 400/401/403 becomes "Twitch rejected the credentials", a network error becomes "Could not reach Twitch" |
| API | `stage: "api"`, surfacing 429 and other codes |
| success | `{ok: true, token_expires_in, detail: "token ok, 1 platform read"}` |

Testing the token alone is not enough: a valid Twitch token with an
IGDB-disabled application fails only at the query, which is precisely the case a
user cannot diagnose from the current single error line.

The result shows inline beside the button as a pill, persists as `last_test` so
it survives a re-render, and goes stale as soon as either field is edited. The
Match buttons gain a precondition: with no secret they are disabled with the
reason given, rather than failing a minute later inside a job.

**Removal.** `POST /api/settings` drops empty values today, so the secret cannot
be cleared. Accept an explicit JSON `null` to delete a key, keep "absent means
unchanged", and treat `""` as absent as now. Removing the secret must also
discard any cached token.

## New endpoints

| Method | Path | Returns | Job |
|---|---|---|---|
| GET | `/api/settings` | extended view: `shell`, the config registry with defaults, `secret_*`, `last_test` | no |
| POST | `/api/settings` | fresh view; per-key validation, `null` deletes, 400 with `{field, message}` | no |
| POST | `/api/settings/validate` | `{ok, message}` for one field, without saving | no |
| POST | `/api/igdb/test` | `{ok, stage, detail, token_expires_in}` | no |
| GET | `/api/systems` | `db.system_rows()` as JSON | no |
| GET | `/api/storage` | per-component files and bytes, recursive, plus reclaimable | no |
| POST | `/api/maintenance/vacuum` | `{before, after, reclaimed}` | yes |
| POST | `/api/maintenance/clear-screens` | `{files, bytes}` | yes |
| POST | `/api/maintenance/prune-covers` | `{files, bytes, names}`, dry run first | yes |
| POST | `/api/maintenance/prune-runs` | `{removed}` | yes |
| GET | `/api/jobs` | full job list with progress and duration | no |
| POST | `/api/job/<id>/cancel` | `{ok}`; means "stop after the current item", never kill a worker mid-copy | no |
| GET | `/api/diagnostics` | shell, version, address, last sync, recent errors | no |
| GET | `/api/diagnostics/bundle` | zip stream, secret redacted | no |
| POST | `/api/shell/reveal` | `{ok}`; loopback-bind check, path must be inside the app, data or store folders | no |
| POST | `/api/shell/pick-folder` | `{path}` or `{cancelled: true}`; desktop shell only | no |
| POST | `/api/shell/open-external` | `{ok}`; allow-list the scheme and host | no |
| POST | `/api/reason` | job, instead of running inline | yes |
| POST | `/api/scrape` | job, plus a 409 when a metadata job is already running | yes |

Three cross-cutting server changes this depends on:

1. **A config registry**: one table of key, type, default, range,
   requires-restart and secret, replacing the twelve scattered module constants.
   `POST /api/settings` validates against it and `GET` returns it, so the page
   renders its controls from the registry rather than hard-coding each one. This
   is the change that makes the page maintainable across the three-way split.
2. **A job guard by kind**, generalising the existing per-device guard so
   metadata jobs, store scans and maintenance jobs cannot double-start.
3. **Structured errors**, `{error, field?, code?}` rather than a bare string, so
   a message can sit next to the field that caused it.

## Feedback model

| Situation | Behaviour |
|---|---|
| A field is edited | that section's Save enables and a dot marks the section |
| Save succeeds | toast, and only that section's status pill refreshes. **No full page re-render**, so no other section loses an edit |
| Save fails validation | inline message under the field, field focused, no toast |
| A job starts | the section's own job line shows progress, and a row appears in Diagnostics; both fed by one poller, not one per card |
| A job finishes | a sentence, not raw JSON; a notification if it ran over 30 seconds; only the affected counts refetch |
| A job fails | the line goes red with the first message, and Details opens the full traceback with Copy |
| The settings fetch fails | an error with Retry, not a permanent `loading…` |
| Navigating away mid-job | the poller keeps running against the Diagnostics model, not a detached DOM node |

## Accessibility work this page should carry

The whole interface has no `keydown` handler and no `tabindex` anywhere. A
keyboard user can reach the nav, the search box, the selects, the sliders, the
checkboxes and the `<button>`s, and nothing else: facets, chips, grid tiles,
selection toggles and system-file rows are all `<div>`s with delegated clicks.
The cross-system compare card is worse than unreachable, appearing on
`mouseover` and dismissing on `mouseleave`, so its Switch and Select buttons
have no keyboard or touch route at all.

Cheap and high value, in order:

1. `#toast` has no `role="status"` and no `aria-live`, so **every** confirmation
   and error in the application is silent to a screen reader. One attribute.
2. `modal()` has no `role="dialog"`, no accessible name, never moves focus in
   and has no focus trap. Tab walks the page behind the overlay.
3. Labels: `#device-select`, `#s-store`, `#s-cid`, `#s-sec`, `#np-name` and
   `#np-root` have sibling `<label>`s with no `for`. The four range inputs have
   only placeholders. `#search` uses a long placeholder as both label and
   documentation, which vanishes on the first keystroke, exactly when the
   operator syntax is being typed.
4. Contrast, measured rather than guessed. The body palette is sound: the
   foreground is 15:1, the muted colour 4.75:1 at worst, every pill passes AA.
   Five pairs fail: white on the accent fill is **3.22:1**, and that is the
   primary action colour on every Sync and Start button; the active
   system-file row uses the same fill; its secondary text at 80% alpha is
   2.43:1; the tile selection tick is 3.56:1; and a zero facet count at
   `opacity: .35` is about 1.41:1, which is effectively invisible. Control
   borders are 1.33:1 against their background, where 3:1 is required.
   Darkening the accent to about `#2f6fe0` gives white 4.8:1 and keeps the hue.
5. Three states are carried by colour alone: the readiness lamp, the status dot
   and the capacity meter. Each has a `title`, which helps a screen reader and
   not a colour-blind sighted user. A glyph on the dot and a word on the meter
   fix it.

## What not to change

| Keep | Why |
|---|---|
| The suggested-tags review list | It is a work queue and it already works well |
| `.card`, `.field`, `.stat`, `.pill`, `.job` | The vocabulary is right; the new page reuses all of it |
| Sending only `has_secret` | Already correct. The design hardens around it rather than replacing it |
| The search operator syntax and the facet model | Dense, fast and genuinely good. Only its keyboard reachability needs work |
| The dark-only palette | Changing the accent is a contrast fix, not a redesign. There is no case for a light theme here |
