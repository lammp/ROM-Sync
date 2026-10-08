# Capture: the current interface, function by function

Captured 8 October 2026 from the working tree, not from memory.

| Source | Lines | Bytes |
|---|---|---|
| `ui/index.html` | 106 | 6,991 |
| `ui/app.css` | 232 | 19,051 |
| `ui/app.js` | 1,170 | 95,937 |

Read in full, then cross-checked against a mechanical extraction of declared
functions, `api.*` call sites, `localStorage` keys and native dialog calls. The
two agree: 77 declared functions, 37 distinct endpoint call sites, 2 storage
keys, 6 native dialogs.

## 1. What the interface is, structurally

One global script, no modules, no build step. All data over `fetch` to `/api/*`
on the same loopback origin. All rendering by assembling HTML strings and
assigning `innerHTML` (47 assignment sites), with `esc()` applied at every
interpolation. Event handling is a mix of direct `onclick` assignment and
delegated listeners on six container elements.

There are **eleven module-level mutable singletons**:

| Name | Holds |
|---|---|
| `S` | library, games, systems, current view, query, sort, grid flag, all filter sets and ranges, selected device, device view, current game, filtered list, size-log bounds, twin map, sort cache |
| `V` | grid windowing: columns, gap, row height, first and last visible row, pending frame, mode |
| `SYNC` | the running sync: job id, device, start time, banked per-run totals, current run, timer, last computed progress |
| `CAP` | capacity meter: poll timer, last reading, device, debounce handle |
| `TWIN` | the twin compare card: element, game id, timer |
| `SF` | system files: payload, selected system, busy set |
| `FX` | facet expanded and collapsed sets |
| `DEVWATCH` | device page watcher: timer, id, last connection state |
| `devPageId` | which device the device page is drawn for |
| `devPageView` | the profile payload the device page was drawn from |
| `qTimer` | the search debounce handle |

`SPEC.md` section 10 requires one state container and no module-level mutable
state outside it. That is eleven containers, and three of them (`SYNC`, `CAP`,
`DEVWATCH`) own live timers with no owner responsible for stopping them on
navigation.

## 2. Views

Five sections in `index.html`, switched by toggling an `active` class. There is
no URL routing: the address never changes, the back button does nothing, and no
view is linkable.

| Section id | Nav button | Rendered by |
|---|---|---|
| `view-library` | Library | static markup plus `renderGrid`, `renderFacets`, `renderChips`, `renderDetail` |
| `view-devices` | Devices | `renderDevices` |
| `view-device` | none (reached from a card or the selection summary) | `renderDevicePage` |
| `view-sysfiles` | System files | `renderSysfiles` |
| `view-settings` | cog | `renderSettings` |

**Finding: there is a sixth view with no way in.** `renderRecover()` exists at
`app.js:1060` and writes into `#recover-page`. No such element exists in
`index.html`, no nav button targets it, and `showView()` has no branch for it.
The engine side is complete: `server.py:616` serves `place`, backed by
`transfer.place_pulled`. So Recover is a finished feature, on both sides, that
cannot be reached. The rebuild has to decide whether to route it in or drop it;
it must not silently carry it forward as unreachable code.

## 3. Function inventory

Destination column: the atomic layer the behaviour belongs to after the
rebuild. `engine` means the behaviour should not be in the interface at all.

### Utilities

| Function | Does | API | Owns | Destination |
|---|---|---|---|---|
| `$`, `$$` | query selector shorthands | | | removed: React refs and props |
| `api.get`, `api.post` | fetch wrapper; throws on a JSON `error` field | all | | removed: generated client |
| `esc` | HTML-escapes five characters | | | removed: JSX escapes by default |
| `fmtB` | bytes to B/KB/MB/GB/TB, 2 or 1 decimals by magnitude, negative-aware | | | `lib/format` |
| `parseSize` | "10mb", "2 gb", "512k" to bytes; null on no match | | | `lib/format` |
| `fmtEta` | seconds to "45 s", "12 min", "1.4 h" | | | `lib/format` |
| `toast` | sets text, bad class, auto-hides after 2.5 s or 6 s | | `#toast` | atom `Toast` plus a store queue |
| `modal`, `closeModal` | injects HTML into `#modal-box`, toggles `hidden`; backdrop click closes | | `#modal` | organism `Modal` |

### Derivation

| Function | Does | API | Owns | Destination |
|---|---|---|---|---|
| `prep` | per game: system label, decade, region array, tag names, tags split by kind, search haystack, sort title with leading article stripped, sort key with accents stripped and digit runs zero-padded to 8 | | | `engine`: these are catalogue facts, not view state |
| `sortedGames` | sorts the whole library once per sort mode and caches it | | | `lib/sort` plus a store selector |

### Cross-system twins

The comment block records the measurement that chose the algorithm: on this
catalogue on 17 September 2026, `igdb_id` linked 39 per cent of the pairs a
human would call duplicates, because IGDB issues an id per platform release;
IGDB's canonical name linked 95 per cent.

| Function | Does | API | Owns | Destination |
|---|---|---|---|---|
| `twinWords` | lowercases, `&` to "and", drops apostrophes, folds four leetspeak characters, non-alphanumeric to spaces, drops three stop words, roman numerals ii to x into digits | | | `engine`: same normalisation the matcher needs |
| `twinKey` | joins those words | | | `engine` |
| `twinKeyLoose` | additionally pops trailing release-form words (3d, hd, dx, deluxe, remaster, remastered, remake, definitive, anniversary, edition) while more than one word remains | | | `engine` |
| `buildTwins` | builds exact and loose maps over the library; a loose-only pair is flagged `loose`; same-system pairs are excluded | | | `engine` |
| `twinsOf` | lookup | | | store selector |
| `twinBadge` | the corner glyph; `dupe` when both copies are selected for the device | | tile corner | molecule `TwinBadge` |
| `twinRow` | one row of the compare card, with Switch or Select or a kept or this-one label | | | molecule `TwinRow` |
| `twinCardHtml` | card body, sorted by system label, with the matched-on-name note or the no-IGDB-match warning | | | organism `TwinCompareCard` |
| `showTwinCard`, `hideTwinCard` | creates a fixed-position popover beside the tile, flips it left or up at the viewport edge, fades in on the next frame, fades out after 120 to 220 ms | | `.twinpop` | organism `TwinCompareCard` |

The card is deliberately bound to the **selected** tile only, so hovering the
grid while browsing stays quiet. That is a behaviour, not an accident, and the
comment says so.

### Search and filtering

| Function | Does | API | Owns | Destination |
|---|---|---|---|---|
| `parseQuery` | tokenises on whitespace with double-quoted phrases; recognises 14 operator keys with 6 comparators; numeric keys parse as float, `size` through `parseSize`, the rest as substring | | | `lib/search` and a parity fixture |
| `num` | numeric accessor; `files` defaults to 1 | | | `lib/search` |
| `matchClause` | applies one clause; `~` is a case-insensitive substring over a per-key pool; `≈` is within 5 per cent | | | `lib/search` |
| `facetFail` | one pass returning the single facet a game fails, or `many`, or null. Serves both the result list and every facet's counts | | | `lib/facets` |
| `passesRanges` | size, year, rating floors and the four boolean flags | | | `lib/filters` |
| `passes` | combines, optionally skipping one facet | | | `lib/filters` |
| `passesQuery` | every term in the haystack and every clause satisfied | | | `lib/search` |
| `applyFilters` | the central recompute: iterate the sorted library once, build the base list and the per-game failing facet, then render facets, grid, chips, the count line and the shown buttons | | `#count` | store action plus derived selectors |
| `updateShownButton` | re-labels and enables the two shown buttons from the current filter without redrawing the summary | | two buttons | component state |

The operator grammar, verbatim from the regex: `year`, `size`, `rating`,
`votes`, `system`, `genre`, `region`, `tag`, `files`, `franchise`, `theme`,
`mode`, `perspective`, each with `>=`, `<=`, `>`, `<`, `:`, `=`.

### Facets, chips, ranges

| Function | Does | API | Owns | Destination |
|---|---|---|---|---|
| `renderFacets` | nine facets; counts from the one-pass fail map; chosen-but-now-zero values retained; seven facets capped at 60 values; decade sorted by name, the rest by count then name; top 10 shown with chosen values pulled above the fold; more and less toggles | | `.facet-body` | organism `FilterSidebar` plus molecule `FacetSection` |
| `saveFacetState` | persists expanded and collapsed sets to `localStorage` under `romsync.facets`, inside try and catch | | | store persistence slice |
| `renderChips` | active filter chips including size, year and rating summaries, plus a clear-all chip | | `#active-chips` | molecule `ActiveChipList` |
| `resetFilters` | clears every set, nulls every range, unchecks the four flags, resyncs the inputs | | | store action |
| `sliderToBytes`, `bytesToSlider` | log scale between 1 KB and the largest file in the library times 1.05, over 1000 steps | | | `lib/scale` |
| `syncSizeInputs`, `syncYearInputs` | push store values back into the paired sliders and the exact inputs | | 8 inputs | controlled inputs; the function disappears |

The paired sliders enforce a 10-step gap for size and no crossing for year, and
treat the extremes as "no limit" rather than as a value.

### Selection

| Function | Does | API | Owns | Destination |
|---|---|---|---|---|
| `isSelected` | override if present, else the system mode is `all` | | | store selector |
| `isOverride` | whether an explicit override exists | | | store selector |
| `onDevice` | membership of the on-device set, keyed `system\name` | | | store selector |
| `toggleSelect` | flips one game; drops the override when the new state equals the system default; starts managing an unmanaged system as `none` with this one game included | `select-system`, `select-game` | one tile, the summary, the detail panel | store action; the rule belongs in `engine` |
| `setSelected` | the same rule for an explicit target state; never starts managing a system merely to exclude | `select-system`, `select-game` | | store action; rule to `engine` |
| `switchTo` | deselects every other version in the twin family, then selects one | repeated `select-game` | | store action; **should be one engine call, not N** |
| `renderSelSummary` | device name link, selected count and bytes, on-device count excluding `bios\`, the sync control, three bulk buttons; debounces the capacity refresh by 250 ms | | `#sel-summary` | organism `SelectionSummary` |
| `reloadSelection` | re-reads the device view after a bulk change | `profile/{id}` | | query invalidation |
| `clearShown` | deselects the selected games in the current filter, behind a native confirm | `select-games` | | store action plus `ConfirmDialog` |
| `selectShown` | selects the unselected games in the current filter, managing unmanaged systems first, behind a native confirm | `select-system` per system, `select-games` | | store action plus `ConfirmDialog` |
| `clearAll` | clears every selection for the device, behind a native confirm | `select-clear` | | store action plus `ConfirmDialog` |

The selection rule is stated three times, in `toggleSelect`, `setSelected` and
`selectShown`. One rule, three implementations, in the layer furthest from the
data. `SPEC.md` section 5 puts it in the domain.

### Sync

| Function | Does | API | Owns | Destination |
|---|---|---|---|---|
| `syncCtlHtml` | button, or disabled button when not connected, or the progress span | | | molecule `SyncControl` |
| `syncProgressHtml` | spinner, percentage, ETA, phase text, with the byte detail as a tooltip | | | molecule `SyncControl` |
| `renderSyncCtl` | redraws the control in both places it appears, the toolbar and the device page | | `#sync-ctl`, `#dv-sync` | one component, two mounts |
| `startSync` | reads the plan, refuses on nothing to do or on a fit failure, shows a confirmation modal with per-bucket counts and sizes and the net change, starts the job, snapshots the starting free space, capacity, on-device count and totals, then polls every second | `plan`, `sync`, `profile/{id}` | modal | organism `SyncDialog` plus a store slice |
| `pollSync` | banks each finished run's totals when the run id changes, computes work as bytes plus removals times one megabyte, caps the percentage at 99, derives the rate from the first byte moved rather than from the start, drives the live on-device count and the capacity meter, then on completion toasts, refreshes the device, the capacity and the device page | `job/{id}`, `run/{id}?brief=1` | | query with `refetchInterval`; the arithmetic to `lib/progress` |

`pollSync` is 40 lines holding progress arithmetic, two live derived displays,
run banking and completion side effects. It is the single most tangled function
in the file and the clearest case for the engine owning job progress as
structured events.

### Capacity meter

| Function | Does | API | Owns | Destination |
|---|---|---|---|---|
| `stopCapacity` | clears the timer and the reading, hides the meter | | `#cap-meter` | store action |
| `refreshCapacity` | resets on device change, polls every 30 s, toasts on the first crossing into full or red | `capacity` | | query plus a store-level threshold watcher |
| `renderCapacity` | two stacked fills, now and after, a percentage, a label that changes with live, full or projected, and a multi-line tooltip; unknown state when capacity is not known | | `#cap-meter` | molecule `CapacityMeter` |

Thresholds are hardcoded in the comment and in the engine: green below 80 per
cent, yellow 80 to 90, red at or above 90, full when it would not fit. `SPEC.md`
section 7 requires these to come from the config registry, and
`ui/tests/device.test.ts::thresholds_from_settings` is the story that proves it.

### Grid

| Function | Does | API | Owns | Destination |
|---|---|---|---|---|
| `tileHtml` | one tile or one list row: cover or a titled placeholder, selection badge with in and over states, on-device badge, twin badge, caption with system, year and rating | | | molecules `GameTile`, `GameRow` |
| `gridCols` | columns from the measured client width minus padding, the `--tile` custom property and the 14 px gap | | | `useWindowedGrid` |
| `renderGrid` | full reset after a filter, sort, view, tile-size or resize change | | `#grid` | `useWindowedGrid` |
| `renderWindow` | measures one row at the current width, then lays out only the rows in the viewport plus two either side, with a spacer height and a padding-top offset | | `#grid-inner` | `useWindowedGrid` |
| `refreshTile` | replaces one tile in place on a selection toggle | | one tile | React reconciliation |

The windowing exists because the full library is over eight thousand tiles:
rendering all of them cost about one second per filter click and sixty thousand
DOM nodes. The measure-one-row-then-lay-out algorithm is the behaviour, and the
rebuild ports it rather than substituting a library.

### Detail panel

| Function | Does | API | Owns | Destination |
|---|---|---|---|---|
| `openDetail` | marks the tile current, shows the panel, fetches the game, renders | `game/{id}` | `#detail` | organism `DetailPanel` |
| `versionPicker` | the system chip becomes a select when the game exists on more than one system, with a tick on selected versions and a loose marker | | | molecule `VersionPicker` |
| `renderDetail` | cover, title, meta row, select button, genre and tag chips with accept and reject on proposed tags, tag add with a `kind:value` shorthand for franchise, theme and genre, screenshot strip, summary, IGDB name and confidence, path, a rematch input, on-device list, other versions | `tag/add`, `tag/remove`, `tag/decide`, `game/{id}/rematch` | `#detail` | organism `DetailPanel` and six molecules |

### Device picker and view switching

| Function | Does | API | Owns | Destination |
|---|---|---|---|---|
| `loadDevicePicker` | fills the select, restores the last device from `localStorage` under `romsync.device` | `devices` | `#device-select` | molecule `DevicePicker` |
| `setDevice` | stores the choice, loads the profile view, builds the on-device set, redraws the summary, the filters and the detail panel | `profile/{id}` | | store action plus query |
| `showView` | toggles the active section and the active nav button, and calls the renderer for devices, sysfiles and settings | | all sections | the App Router |

### Devices

| Function | Does | API | Owns | Destination |
|---|---|---|---|---|
| `renderDevices` | two card shapes. A profile card: lamp, name, online or offline with transport and ROMs root or last seen, capacity bar, three figures, and Sync, Contents, Choose games. A candidate card: lamp, label, transport, capacity, and one of a debugging-state warning, an adopt action for a foreign marker, or a new-profile action | `devices`, `profile/adopt` | `#device-list` | organism `DeviceCard` with two variants |
| `newProfileDialog` | name, ROMs folder prefilled from the probe, a marker checkbox, behind a native confirm | `profile/new` | modal | organism `NewProfileDialog` |
| `showDevice` | opens the device page | | | route navigation |
| `watchDevice` | probes every 15 s while the page is showing, re-renders and toasts on a connection change, and clears its own timer when the page changes | `devices?refresh=1` | | query with `refetchInterval` |
| `renderDevicePage` | preserves scroll across the redraw, header with connected pill and six actions, systems table with per-system all and none segments and an override count, a trailing section for device folders that are not store systems, the plan summary, a readiness line, and the run history | `profile/{id}`, `select-system`, `rename`, `scan`, `write-marker` | `#device-page` | page plus four organisms |
| `showPlanSummary` | what Sync would do now, read-only, with a show-list toggle and a note naming the untouched folders | `plan` | `#dv-planbox` | organism `PlanSummary` |
| `watchJob` | polls a job every 1.5 s and writes raw JSON into a progress box | `job/{id}` | `#dv-job` | query plus organism `JobProgress` |

`watchJob` renders `JSON.stringify(j.result)` to the user. That is the engine's
shape leaking into the interface because the engine has no structured progress
contract; `SPEC.md` section 8 fixes it.

### System files

| Function | Does | API | Owns | Destination |
|---|---|---|---|---|
| `renderSysfiles` | with no device: the store-side table only, with a note that the app checks and places these files and never generates them. With a device: a two-pane readiness view, a refresh-from-device action, and the staging-path explanation | `sysfiles`, `sysfiles?device=`, `scan-sysfiles` | `#sysfiles-page` | page plus organisms |
| `renderSfList` | systems ordered with on-device first, a divider before the store-only ones, then a divider and an Other files row | | `#sf-list` | organism `SysfileList` |
| `sfDot`, `sfPill` | six states to a colour and a label: ready, missing, optional, nothing needed, not seen over USB, not scanned | | | atoms `Dot`, `Pill` |
| `sfReqRow` | one requirement: name and staged name, required or optional with an any-one note, store presence with size and verification, staged state, installed state with its path | | | molecule `SysfileReqRow` |
| `renderSfDetail` | emulator line with a seen-over-USB qualifier, games on device against in store, installed state with the long explanation for the unseen case, staged state, the requirements table, and Add or Update and Remove actions that block while a sync is running | `sysfiles-stage`, `sysfiles-unstage`, `job/{id}` | `#sf-detail` | organism `SysfileDetail` |
| `renderSfOthers` | stray files under the staging folder, with per-file removal | `sysfiles-remove-other` | `#sf-detail` | organism `SysfileOthers` |

`sfReqRow` carries three separate state vocabularies (`SF_STATE`, `SF_STAGED`,
`SF_INST`) mapping engine strings to a colour and a human label. Those maps are
presentation and belong here. The engine returning `ok`, `warn` and `muted`
would not; it returns states, which is correct.

### Settings

| Function | Does | API | Owns | Destination |
|---|---|---|---|---|
| `runJob` | posts, then polls every 1.5 s writing `jj.progress` into a job line, and `JSON.stringify` of the result on completion | any post plus `job/{id}` | a job line | query plus organism `JobProgress` |
| `renderSettings` | four cards: Library with the store root and three counts and a rescan; IGDB with client id and secret and five counts and five actions including a dangerous re-match-everything behind a modal; Linked tags with the proposal count and a propose action; Data with the app folder, database, cover and screenshot sizes and the log path | `settings`, `scan-store`, `scrape`, `covers-libretro`, `enrich`, `reason` | `#settings-page` | page plus organism `SettingsCard`, rebuilt to `SETTINGS.md` |
| `renderSuggestions` | proposed tags grouped by tag, groups ordered by size, with accept-all, reject-all and per-row accept and reject | `tags/proposed`, `tag/decide`, `tags/decide-many` | `#sugg` | organism `SuggestionGroup` |

### Orphaned

| Function | Does | API | Status |
|---|---|---|---|
| `renderRecover` | per device, the on-device items the store has no copy of, then per run the pulled items with a place action | `devices`, `profile/{id}`, `run/{id}`, `place`, `scan-store` | unreachable: no section, no nav, no `showView` branch |

### Boot

| Function | Does | API |
|---|---|---|
| `loadLibrary` | loads the whole library in one request, preps every game, builds the twin maps, derives the size-slider bounds from the real minimum and maximum, syncs the inputs, filters | `library` |
| `boot` | loads the library, then the device picker; a failure writes the message into the count line and logs to the console | |

The whole catalogue arrives in one response and lives in memory. At 7,900 games
that is the design; it is what makes the client-side search and facet counting
possible at all, and the rebuild keeps it.

## 4. Endpoint surface

37 call sites, 25 distinct endpoints.

| Method | Endpoint |
|---|---|
| GET | `library`, `game/{id}`, `settings`, `devices`, `devices?refresh=1`, `profile/{id}`, `profile/{id}/plan`, `profile/{id}/capacity[?refresh=1]`, `job/{id}`, `run/{id}[?brief=1]`, `sysfiles`, `sysfiles?device={id}`, `tags/proposed` |
| POST | `settings`, `scan-store`, `scrape`, `covers-libretro`, `enrich`, `reason`, `tag/add`, `tag/remove`, `tag/decide`, `tags/decide-many`, `game/{id}/rematch`, `place`, `profile/new`, `profile/adopt`, `profile/{id}/rename`, `profile/{id}/scan`, `profile/{id}/scan-sysfiles`, `profile/{id}/sync`, `profile/{id}/write-marker`, `profile/{id}/select-system`, `profile/{id}/select-game`, `profile/{id}/select-games`, `profile/{id}/select-clear`, `profile/{id}/sysfiles-stage`, `profile/{id}/sysfiles-unstage`, `profile/{id}/sysfiles-remove-other` |

No version prefix, no declared shapes, no error envelope beyond a bare `error`
key. `SPEC.md` section 9 fixes all three.

## 5. Browser storage

| Key | Holds | Guarded |
|---|---|---|
| `romsync.device` | the last selected device id | no |
| `romsync.facets` | expanded and collapsed facet sets | yes, try and catch on both read and write |

## 6. Accessibility, measured

| Check | Result |
|---|---|
| `:focus` or `:focus-visible` rules | **0** in 232 lines of CSS |
| `prefers-reduced-motion` | **0**, and there is a running spinner animation |
| `prefers-color-scheme` | **0**: the dark palette is unconditional |
| `role` attributes | **0** anywhere, including on `#modal` |
| `aria-*` attributes | **1** in the whole application: `aria-label` on the settings cog |
| `<label>` elements | 7, **none** with a `for` attribute; the 7 wrap their control, so those associate implicitly |
| Inputs and selects | 17, of which 10 have no label at all and rely on a placeholder or adjacent text |
| Native dialogs | 5 `confirm`, 1 `prompt`, 0 `alert`, against `SPEC.md` section 10 which forbids all three |
| Modal semantics | no dialog role, no accessible name, no focus move in, no focus trap, no focus restore, no Escape handler; backdrop click is the only close besides the explicit buttons |
| Interactive non-buttons | tiles, list rows, facet rows, chips, system-file rows, twin rows, version rows and the show-list link are all `div` or `span` with click handlers, no `tabindex`, no key handling |
| Live region | none; `#toast` is a plain div, so nothing is announced |

Every one of these is a story in `BACKLOG.md` F11: S14 through S19. This table
is the before measurement they are judged against.

## 7. What the capture says about the rebuild

| Observation | Consequence |
|---|---|
| Eleven mutable singletons, three owning timers | one store, and every poll becomes a query the router can cancel |
| The selection rule written three times | it moves to the domain, once, per `SPEC.md` section 5 |
| Twin normalisation written in the interface | it moves to the domain, where the matcher needs the same function |
| `prep` derives sort and search keys per game on every load | the engine computes them once |
| `switchTo` issues one request per family member | one engine call |
| `watchJob` and `runJob` print `JSON.stringify` to the user | structured progress, per `SPEC.md` section 8 |
| Capacity thresholds hardcoded | config registry, per `SPEC.md` section 7 |
| 47 `innerHTML` assignments | JSX, and `esc` disappears as a category of risk |
| No routing | real routes, which makes the back button work: an intentional deviation from parity |
| Recover is finished and unreachable | a decision, not a port |
