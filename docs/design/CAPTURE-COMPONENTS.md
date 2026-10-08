# Capture: the component inventory, in atomic layers

Derived from the real DOM in `ui/index.html` and the 47 `innerHTML` assignment
sites in `ui/app.js`. Nothing here is invented: every entry names the class or
element it comes from.

## 1. The placement rule

Atomic design argues with itself about whether a thing is a molecule or an
organism. Two yes-or-no questions settle it, so an autonomous run never has to
form an opinion.

| Layer | Renders another project component? | Reads the store or fetches? | Owns local UI state? |
|---|---|---|---|
| **Atom** | no | no | no |
| **Molecule** | atoms only | no | allowed |
| **Organism** | anything | yes | allowed |
| **Template** | slots only | no | no |
| **Page** | a template plus organisms | yes | allowed |

Consequences worth stating, because they are where the rule bites:

- An atom cannot import `useStore`. A `Button` that knows whether a sync is
  running is not an atom.
- A molecule cannot fetch. `CapacityMeter` takes a reading as a prop; the
  organism above it owns the query.
- A template cannot know what a game is. `TwoPaneWithSidebar` takes three
  slots.
- `tests/unit/test_layering.py` gets a second rule: a file under `atoms/` that
  imports from `molecules/`, `organisms/`, the store or the API client fails the
  test. Placement becomes enforced, not reviewed.

## 2. Atoms

| Component | From | Variants and states |
|---|---|---|
| `Button` | `button`, `.primary`, `.danger`, `.active`, `:disabled` | default, primary, danger, active; disabled; small |
| `IconButton` | `header .cog`, `#detail .close` | needs an accessible name, which today only the cog has |
| `NavButton` | `.nav`, `.nav.active` | becomes a real link in the rebuild, since views become routes |
| `TextInput` | `input[type=text]`, `input:not([type])` | with and without invalid state |
| `SearchInput` | `#search` | the 20 px pill radius |
| `PasswordInput` | `#s-sec` | never shows a stored value |
| `Select` | `select`, `select.vpick` | default and the chip-shaped variant |
| `Checkbox` | `.row input[type=checkbox]` | always with its label, per `SPEC.md` section 10 |
| `Range` | `#rating-min`, `#tile` | single thumb |
| `Pill` | `.pill`, `.ok`, `.warn`, `.bad` | four |
| `Chip` | `.chip` and seven `kind-*` classes | removable and plain; the suggested kind carries a dashed outline |
| `Dot` | `.dot`, `.ok`, `.warn`, `.bad` | four |
| `Lamp` | `.lamp`, `.on`, `.bad` | three, and never red for merely unplugged |
| `Spinner` | `.spin` | must respect `prefers-reduced-motion` |
| `Bar` | `.bar > i` | single fill |
| `CoverImage` | `.cov`, `.big`, `.lrow img` | lazy, async decode |
| `NoCover` | `.nocov` | the gradient placeholder that shows the title |
| `Muted`, `KeyValueText`, `NumCell` | `.muted`, `.kv`, `.num` | typographic atoms |
| `TextLink`, `ActionLink` | `a`, `.link` | the second is a span today and becomes a button |
| `Chevron` | `.chev` | rotates when collapsed |
| `TwinGlyph` | `.twin`, `.twin.dupe` | the `⇄` corner mark |
| `Divider`, `SectionLabel` | `.sf-divider` | |

## 3. Molecules

| Component | From | Local state |
|---|---|---|
| `Field` | `.field` label plus control | none |
| `StatRow` | `.stat` | none |
| `SegmentedControl` | `.seg` | none; controlled |
| `FacetRow` | `.fact`, `.on`, `.zero` | none |
| `FacetSection` | `.facet` with `h4`, `.chev`, `.sel-n`, `.clear`, `.facet-body`, `.more` | collapsed and expanded, persisted |
| `RangeFacet` | `.facet.range`, `.slider2`, `.exact` | the paired-thumb constraint: 10 steps apart for size, no crossing for year |
| `SmartListButton` | `.smart` | none |
| `ActiveChipList` | `#active-chips` | none |
| `SortControl`, `TileSizeControl`, `GridListToggle` | `#toolbar` children | none |
| `CapacityMeter` | `#cap-meter` with `.meter`, `.now`, `.pct`, `.cnt` | none; five states in, green, yellow, red, full, unknown |
| `SyncControl` | `#sync-ctl`, `.syncing` | none; idle, disabled, running |
| `GameTile` | `.tile` with `.cov`, `.sel`, `.ondev`, `.twin`, `.cap` | none |
| `GameRow` | `.lrow` | none |
| `SelectionBadge` | `.sel`, `.in`, `.over` | none |
| `TwinRow` | `.tw-row`, `.me` | none |
| `VersionPicker` | `#d-version` | none |
| `TagChipGroup` | `#detail .chips` | none |
| `TagAdd` | `.tagadd` | the input value |
| `ScreenshotStrip` | `.shots` | none |
| `DeviceFigures` | `.dev-figs` | none |
| `SysfileRow` | `.sf-row`, `.active`, `.dim` | none |
| `SysfileReqRow` | `table.sf-req` row | none; three state vocabularies in |
| `PlanLine`, `PlanDetailList` | `#dv-planbox`, `.plan-detail` | the show-list toggle |
| `JobLine` | `.job`, `.job.bad` | none |
| `Toast` | `#toast` | none; must sit in a live region |
| `DataTable` head and cells | `table`, `th`, `td`, `.num` | none |

## 4. Organisms

| Component | From | Owns |
|---|---|---|
| `AppHeader` | `header#top` | nav, search, device picker, settings link |
| `DevicePicker` | `#device-pick` | the device query and the persisted choice |
| `FilterSidebar` | `#filters` | nine facets, two range facets, smart lists, four flags, the chip list |
| `LibraryToolbar` | `#toolbar` | sort, tile size, view toggle, selection summary, capacity meter |
| `SelectionSummary` | `#sel-summary` | counts, the sync control, three bulk actions, the debounced capacity refresh |
| `VirtualGameGrid` | `#grid`, `#grid-inner` | the windowing hook, the measure-then-layout pass, the two delegated handlers |
| `DetailPanel` | `#detail` | the game query, tag mutations, the rematch action |
| `TwinCompareCard` | `.twinpop` | positioning, the fade, switch and select mutations |
| `Modal` | `#modal`, `#modal-box` | dialog role, name, focus trap, focus restore, Escape |
| `ConfirmDialog` | replaces 5 `confirm()` calls | |
| `PromptDialog` | replaces the 1 `prompt()` call | |
| `DeviceCard` | `.card` in `#device-list` | two variants, profile and candidate; the candidate variant has three sub-states, debugging-state, foreign marker, no profile |
| `NewProfileDialog` | `newProfileDialog` | name, root, marker |
| `DeviceSystemsTable` | the device page systems table | per-system mode, the override count, the not-a-store-system trailer |
| `PlanSummary` | `#dv-planbox` | the plan query |
| `RunHistoryTable` | the device page history table | |
| `SyncDialog` | `startSync`'s modal | the plan, the fit refusal, the start action |
| `JobProgress` | `#dv-job`, `#sf-job` | one job query, structured progress in |
| `SysfileList` | `#sf-list` | ordering, the on-device divider, the Other files row |
| `SysfileDetail` | `#sf-detail` | the stage and unstage mutations, the busy set, the sync-running guard |
| `SysfileOthers` | `renderSfOthers` | per-file removal |
| `SysfileStoreTable` | the no-device branch of `renderSysfiles` | |
| `SettingsSection` | `.card` in `.settings-grid` | one per section of `SETTINGS.md` |
| `SuggestionGroup` | `.sugg`, `.fr`, `.rows`, `.row2` | accept-all, reject-all, per-row decisions |
| `RecoverList` | `renderRecover` | per device, what the store lacks; per run, the pulled items and their place action |

## 5. Templates

| Template | From | Slots |
|---|---|---|
| `AppShell` | `body` | header, main, modal host, toast host |
| `LibraryLayout` | `#view-library` | sidebar, main, optional right panel |
| `PageLayout` | `.page` | heading, body; owns the scroll container |
| `SplitPane` | `.sf-pane` | list at 260 px, detail at 1fr, stacking below 900 px |
| `CardGrid` | `.cards`, `.settings-grid` | auto-fill at a minimum column width |

## 6. Pages

Views become routes, which the current application does not have. One route is
forced into a search parameter rather than a path segment: under
`output: 'export'` a dynamic segment needs `generateStaticParams` at build
time, and device ids are runtime data.

| Route | From | Note |
|---|---|---|
| `/` | `view-library` | the detail panel stays a panel, not a route |
| `/devices` | `view-devices` | |
| `/devices?id={id}` | `view-device` | a search parameter, not `/devices/[id]`, for the reason above |
| `/system-files` | `view-sysfiles` | |
| `/settings` | `view-settings` | rebuilt to `SETTINGS.md` rather than ported |
| `/recover` | `renderRecover` | routed in, decided 8 October 2026. The function and the `place` endpoint both exist and work; no route had ever reached them. Its nav entry appears only when there is something to recover |

## 7. Counts

| Layer | Components |
|---|---|
| Atoms | 24 |
| Molecules | 27 |
| Organisms | 25 |
| Templates | 5 |
| Pages | 6 |

76 components against 77 functions, which is roughly what a faithful
decomposition of a 1,170-line single file should look like. The ratio is a
sanity check, not a target.

## 8. What the decomposition changes, and what it must not

### Changes, intentionally

| Change | Why |
|---|---|
| Views become routes, so the back button works and screens are linkable | unavoidable with the App Router, and an improvement |
| Every clickable `div` and `span` becomes a `button` or a link | `SPEC.md` section 10, and eight element classes today are keyboard-unreachable |
| Five `confirm()` and one `prompt()` become dialog organisms | `SPEC.md` section 10 forbids native dialogs |
| The settings page is rebuilt to `SETTINGS.md`, not ported | it was already specified separately |
| Capacity thresholds arrive from the engine | `SPEC.md` section 7 |
| `JSON.stringify` of a job result stops being user-facing copy | `SPEC.md` section 8 |

### Must not change

Each of these is a measured behaviour with a named test in `BACKLOG.md`.

| Behaviour | Why it exists |
|---|---|
| The windowed grid's measure-one-row-then-lay-out algorithm, with a two-row overscan | 8,000 tiles, about one second per filter click, 60,000 nodes |
| The one-pass facet fail computation serving both results and counts | a second pass per facet is nine passes |
| Chosen facet values stay visible at zero, and above the fold | otherwise a filter can hide its own control |
| Facet caps: top 10 shown, 60 values kept for seven facets | |
| The twin compare card belongs to the selected tile only | the grid stays quiet while browsing |
| Loose twin matches are marked loose and never resolved automatically | Earthworm Jim 3D is not Earthworm Jim |
| An override is stored only when it differs from the system default | |
| Selecting never starts managing a system merely to exclude | |
| The sort key strips accents and zero-pads digit runs to 8 | so 2 sorts before 10 without ICU collation |
| The size slider is log scaled between 1 KB and the real library maximum times 1.05 | |
| The paired sliders treat their extremes as "no limit", not as a value | |
| Sync progress counts a removal as one megabyte of work and caps at 99 per cent | |
| The sync rate is averaged from the first byte moved, not from the start | an MTP session can sit for minutes before the first byte |
| The on-device count excludes the `bios\` prefix | bios is system files, never games |
| Device folders that are not store systems are named and left alone | the destination is not mirrored |
