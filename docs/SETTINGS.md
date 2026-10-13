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

- One page, its groups as tabs in first-run order; one tab shown at a time.
- Every section states its own readiness. Only a section with a problem is loud.
- Saving is explicit and **per tab**: Save and Cancel act on the tab they sit
  in, and nothing else. Edits in a tab survive a visit to another, and a tab
  with unsaved edits carries a dot.
- Destructive and long actions share one confirmation component, with a
  typed-word gate reserved for the irreversible two.
- A running job is visible from anywhere on the page, not only from the card
  that started it.
- Nothing is read-only prose where an action is possible: a path gets Reveal and
  Copy, a size gets a breakdown, a credential gets a test.

### Controls (F11-S51, the owner's design decisions)

- **A tab's main actions sit at its top**, as large buttons above its
  settings: what the tab *does* comes before what it *sets*. Library: Rescan
  ROMs folder and Reveal. Metadata: Run Initial or Update Metadata, and
  Refresh Metadata. Tag suggestions: Propose franchise tags. Transports: Look
  for devices again, with what each transport reported. Data: Reveal the data
  folder. Diagnostics: Export a support bundle.
- **A saved value is locked.** It is shown, not editable, with an edit icon at
  its end that opens it, and once open an undo icon that puts the saved value
  back. An empty field is open: there is nothing to protect. Saving or
  Cancel locks every field in the tab again. Paths are already chosen rather
  than typed, through the chooser at their end.
- **A secret is one field**, always shown: open while nothing is saved, with
  an eye that shows what is being typed; locked as dots once saved, with an
  icon to enter a new one and one to remove it. The engine never returns a
  saved secret, so the eye can only ever show what is typed now.
- **A button that runs something shows how it went on itself**: its words stay,
  and its glyph is a recycle sign that turns while the work runs, then a tick
  when it passed or a red cross when it failed. The outcome is also said
  beside it in words, so neither the colour nor the glyph carries it alone.
- **A bounded number is a scale** with its number in a small field to its
  left for fine tuning; the scale's ends are the registry's bounds, and those
  bounds are kept to what is sensible (no more than 100 failures in a row, no
  more than 1,000 games before a removal is confirmed).
- **A short range or a size is a list**: requests a second is 1 to 4, sizes
  are the powers of two within the setting's bounds, and a stored value that
  is none of them is listed too.
- **A setting nothing reads is not shown.** Auto enrich and the verify
  percentage were removed: nothing fetches screenshots or tags after a match,
  and every transfer is already verified wherever its transport can.

## Information architecture

```
Settings  (a cog in the header)
├─ Library
├─ Metadata and artwork
├─ Tag suggestions
├─ Transports and tools
├─ Sync behaviour and guards
├─ Data and storage
└─ Diagnostics
```

Each group is a tab; the address names the open one (`/settings#metadata`), so
a link can open a tab and a reload keeps it. Each tab's panel is a `<section>`
with an `<h2>` and a status pill. The arrow keys, Home and End move between
tabs.

### Setup, as notifications

The setup steps are notifications in the header's bell, not a section. Each is
listed while it is to do, points at its tab, and leaves the bell once done.

| Notification | Listed while | Opens |
|---|---|---|
| Choose your ROMs folder | no ROMs folder is chosen | the Library tab |
| Read the library | a ROMs folder is chosen and no system is read | the Library tab |
| Add IGDB credentials for covers and details | no client ID and secret are saved; libretro box art needs no account | the Metadata and artwork tab |

## Field specifications

Every path setting refuses a network share (`\\server\share`) and a device
path (`\\?\`, `\\.\`): reading one would send the Windows sign-in to
whatever answers (F16-S1).

Legend: **restart** means it is read once at startup. Everything unmarked takes
effect immediately, because the server re-reads config per call.

### 1. Library

| Field | Control | Validation | Default | Restart |
|---|---|---|---|---|
| ROMs folder (`store.root`) | folder chooser + Reveal | must exist and be a directory; **new:** must contain at least one subfolder with a recognised extension, else save with a warning "no systems found here"; reject a path equal to or inside the data folder | `D:\Games\ROMs` (`db.py:248`) | No, but the loaded library is stale: call `loadLibrary()` on success and offer Rescan inline |
| Systems table | read-only: system, games, folders, bytes, matched | n/a | `db.system_rows()`, which already returns exactly this and is currently unused by the UI | n/a |
| Rescan store | button, confirms when `counts.games > 0` | n/a | n/a | n/a |
| Rescan on launch | checkbox | n/a | off | **Yes** |

The systems table is the highest-value single addition on the page: it answers
"did the path I just typed actually work" without a trip to the Library view.

### 2. Metadata and artwork

**Actions, at the top (F11-S52).** The metadata is one action, not two:

| Button | Shown | Does |
|---|---|---|
| **Run Initial** | while no game has been looked up | looks up every game, then fills missing covers from libretro when that is on |
| **Update Metadata** | once any game has been looked up | looks up the games never looked up or that failed last time, then fills missing covers |
| **Refresh Metadata** | beside it; needs credentials and a first run | asks first, saying it rebuilds the metadata for every game and how long that takes at the request rate; then looks up every game again, but for one matched by hand, and fills covers |

Beside the tab's settings, or under its actions where the tab is narrow, a
**tracker** shows the metadata as one graphic (F11-S53): at rest, a ring of how
much of the library is matched ("of games matched"), with four coloured counts
(matched; not matched, meaning looked up with no candidate accepted; not looked
up; without a cover); while a pass runs, the ring is the run's progress, turning
and glowing, with the phase (matching games, filling covers), the count, the
game being looked up, the time left at the pace so far, and Stop; when it ends,
a full ring with a tick ("run complete"), or the run's progress with a cross,
what the run did, and the library's coverage in words. The ring never shows
coverage while it stands for a run, so a finished run cannot read as stopped
part way. A pass already running when the tab opens, or
started elsewhere, is followed, so leaving Settings never loses its progress. Without credentials only libretro covers are
filled, and the line says so. The match skipped for want of credentials is said
in the job's result, never as a failure. A game matched by hand is **pinned**,
and a refresh keeps it (F5-S12).

| Field | Control | Validation | Default | Secret |
|---|---|---|---|---|
| Twitch Client ID | locked field once saved, an edit icon to change it | trim | `""` | No |
| Client Secret | see [the credential section](#the-igdb-credentials-specifically) | trim, warn under 20 characters, never submitted when untouched | unset | **Yes** |
| Test connection | button with its outcome on it: a turning recycle glyph, then a tick or a red cross; the stage said beside it | n/a | n/a | n/a |
| Match acceptance threshold | scale 0 to 1, its number to the left | range | 0.55 | No |
| Requests per second | list: 1, 2, 3, 4 | hard cap 4 | 4 | No |
| Stop after this many failed lookups in a row | scale 1 to 100 | range | 25 | No |
| Also fill missing covers from libretro | checkbox | n/a | on | No |

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
| ADB executable | file chooser (`.exe`) + Detect + Reveal, with a found / not found pill | must be an existing file named `adb` or `adb.exe` (F16-S1); **new:** run `adb version` and show it, else reject with that error | `_tools\platform-tools\adb.exe`, then PATH (`adb.py:20,27`) |
| Enable ADB transport | checkbox, "faster, needs USB debugging" | n/a | on when adb is found |
| Enable MTP transport | checkbox | at least one transport must stay enabled | on |
| Staging path on the device | text template with `{roms}` and `{system}`, locked once saved | must contain `{system}`, must be relative, no `..`; may not be `{roms}/{system}` (a system's games) or anything under `Android` (F16-S3) | `{roms}/bios/{system}` (`sysfiles.py:41`) |
| Verify staged files up to | list of sizes | 1 MB to 4 GB | 64 MB |
| Device probe interval | scale, seconds, step 5; how often the page asks for attached devices | 5 to 300 | 15 |
| Wait at least this long for an MTP copy | scale, seconds, step 30 | 60 to 7200 | 600 |
| Assume an MTP copy arrives at least this fast | list of sizes a second | 64 KB/s to 1 GB/s | 2 MB/s |

Changing the staging path orphans anything already staged, so it confirms and
says so. The detected transports sit at the top of the tab with Look for
devices again, so ADB and MTP can be told apart without leaving Settings.

### 5. Sync behaviour and guards

| Field | Control | Validation | Default |
|---|---|---|---|
| Keep free on the device | list of sizes | 0 to 8 GB | 512 MB |
| Warn at, Alarm at | two scales, 0.1 to 1 of the device full | 0.1 to 1 | 0.8 and 0.9 |
| Confirm a sync that removes at least | scale, games; a device's first sync always asks (F16-S2) | 0 to 1,000 | 25 |
| Write the device marker after every sync | checkbox | n/a | on, unconditional today (`server.py:596`) |
| Protected folders inside a managed system | **read-only** list with a note | n/a | `planner.EMULATOR_STATE` |
| Folders that are not store systems | read-only, "left alone" | n/a | behaviour is fixed |

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
| Keep sync run folders | scale, 1 to 200 | 50 |
| Keep job history | scale, 10 to 1,000, step 10 | 200 |
| Database busy timeout | scale, 100 to 60,000 ms, step 100 | 5,000 ms |

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
| Preferred port | number, locked once saved; "0 picks a free port" | **restart** |
| Listen on | select: `127.0.0.1` or `::1`; nothing reachable from the network is offered, because the page token is all that guards a change (F16-S1) | **restart** |
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

- **Set:** the field is locked and drawn as dots, never the secret, with
  `Saved 8 Oct 2026 · 30 characters. A saved secret is never shown again.`
  under it, and two icons at its end: enter a new one, and remove it. Removal
  waits for Save and can be undone until then.
- **Set, and `secret_source` is `imported`:** add `imported from RomCurator`.
  This closes the hole where credentials appear that the user never typed.
- **Unset:** the field is open, with `Covers and details need Twitch
  credentials; libretro box art does not.` under it.
- **Typing:** `type="password"`, `autocomplete="off"`, holding only what is
  typed now; an eye toggles it visible; over a saved secret an undo icon keeps
  the saved one. A field left empty submits nothing.

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

The result shows on the button (a tick or a red cross) and beside it as a pill,
and goes stale as soon as either field is edited: the button turns back to its
recycle glyph and the pill says to test again. Refresh Metadata needs saved
credentials and says so when it is disabled, rather than failing a minute later
inside a job.

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
| A field is edited | that tab's Save and Cancel enable, and a dot marks the tab |
| Save succeeds | toast, and only that section's status pill refreshes. **No full page re-render**, so no other section loses an edit |
| Save fails validation | inline message under the field, field focused, no toast |
| A job starts | the section's own job line shows progress, and a row appears in Diagnostics; both fed by one poller, not one per card |
| A job finishes | a sentence, not raw JSON, as a toast and as a notification in the bell, wherever the person is; a system notification if it ran over 30 seconds; only the affected counts refetch |
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
