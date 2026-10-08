# ROM-Sync 2: the interface rebuild

Normative. This document amends [SCOPE.md](SCOPE.md) and [SPEC.md](SPEC.md) and
re-cuts feature F11 in [BACKLOG.md](BACKLOG.md). Where it conflicts with those
files, this document wins and they are updated in the same pull request.

Grounded on the capture in [../design/CAPTURE-FUNCTIONS.md](../design/CAPTURE-FUNCTIONS.md),
[../design/CAPTURE-COMPONENTS.md](../design/CAPTURE-COMPONENTS.md) and
[../design/CAPTURE-TOKENS.md](../design/CAPTURE-TOKENS.md).

## 1. Two decisions are retired

| Retired | Said | Why it dies |
|---|---|---|
| **D2** | "The interface is ported, not redesigned." | Atomic design is a re-decomposition of the component tree. The current interface is one 1,170-line file with eleven mutable singletons and 47 `innerHTML` assignments; splitting it into 24 atoms, 27 molecules and 24 organisms under React is a rebuild, whatever it is called. |
| **D3** | "TypeScript, built with Vite, no UI framework." | Atomic components in Next.js means React, a different build and a different serving story. |

D2's death has a cost, and `SCOPE.md` already named it: the residual-risk table
says "a TypeScript port is a rewrite of the interface by another name,
mitigated by D2 and by behaviour fixtures". With D2 gone, **the fixtures are
the only mitigation left.** That is why F0 below exists and why it blocks
everything.

## 2. New decisions

| # | Decision |
|---|---|
| D17 | The interface is rebuilt as atomic components. Behaviour parity is the constraint, not the method, and is pinned by fixtures captured from version 1 before any interface work begins. |
| D18 | The interface is TypeScript and React on Next.js 16 with the App Router. |
| D19 | `output: 'export'`. No Node process exists at runtime. The engine serves the exported bundle. |
| D20 | No route takes a runtime identifier as a path segment. |
| D21 | Styling is CSS Modules over a generated token layer. No utility-class framework. |
| D22 | One client store, Zustand. Server state in TanStack Query. No module-level mutable state outside the store. |
| D23 | The windowed grid algorithm is ported as a hook, not replaced by a virtualisation library. |
| D24 | The API client is generated from the committed OpenAPI document. |
| D25 | The design system is generated from the same token source the application imports, so the reference cannot drift from the code. |
| D26 | Version 1 is tagged before F0 begins, and every parity fixture names that tag. |

## 3. What static export forbids, and why none of it costs anything

Verified against the Next.js documentation for version 16.4.0, not assumed.
Under `output: 'export'` these features are unsupported:

| Unsupported | Already the engine's job |
|---|---|
| Server Actions | every mutation is a POST to `/api/v1` |
| Cookies | the page token is issued to the page, not set as a cookie |
| Rewrites, redirects, headers | the engine serves and sets headers |
| Proxy and middleware | there is nothing to proxy: one origin, one engine |
| Incremental Static Regeneration | nothing is regenerated; the catalogue is a query |
| Image Optimization with the default loader | covers and screenshots are engine routes |
| Route Handlers that read the request | the engine is the API |
| Draft Mode, Intercepting Routes | not used |
| Dynamic routes without `generateStaticParams`, or with `dynamicParams: true` | **this one bites. See D20 below.** |

So the loss is nil except for one thing, and what remains is React, the App
Router's file conventions, and the bundler. That is a smaller return than
Next.js usually gives, bought for familiarity and conventions, at the cost of a
heavier toolchain inside a frozen build than Vite with React would be. Stating
the trade is the point; the decision is made.

### D20 in detail

A device id is runtime data. It cannot be known at `next build`, so
`/devices/[id]` has no `generateStaticParams` to give and the route cannot
exist. The device page is therefore `/devices?id={id}`, read with
`useSearchParams` in a client component.

This is a hard constraint of the chosen stack, not a preference. Any future
route keyed on runtime data follows the same rule.

### Serving the export

| Requirement |
|---|
| `next.config.ts` sets `output: 'export'`, `trailingSlash: true`, `images.unoptimized: true`, and `distDir` pointing into the engine's static directory. |
| `trailingSlash: true` makes every route a directory with an `index.html`, so the manifest maps a route to exactly one file with no path arithmetic. |
| The build writes a manifest enumerating every emitted file. The engine serves by exact-name lookup against that manifest and joins nothing from a request, which is `SPEC.md` S2. `BACKLOG.md` F10-S6 is amended to read the manifest the export produces. |
| The desktop shell loads `http://127.0.0.1:{port}/` and navigates client-side thereafter. |

## 4. Layout

```
ui/
  src/
    app/                      App Router routes, thin: a template plus organisms
      layout.tsx  page.tsx
      devices/page.tsx
      system-files/page.tsx
      settings/page.tsx
    design/
      tokens.ts               THE source of truth: every token, typed
      tokens.css              generated, never hand-edited
      contrast.ts             the ratio function the test and the artefact share
    atoms/        24 components, one folder each
    molecules/    27
    organisms/    24
    templates/    5
    lib/
      api/                    generated client, never hand-edited
      format.ts search.ts facets.ts sort.ts scale.ts progress.ts windowing.ts
    store/
      index.ts                the one store
      slices/                 library, filters, selection, sync, capacity, ui
    queries/                  one hook per endpoint group
  tests/
    fixtures/                 the F0 corpora, committed
    atoms/ molecules/ organisms/ parity/ a11y/
  next.config.ts
```

Enforced by a test, not convention. `ui/tests/layering.test.ts` fails when:

- a file under `atoms/` imports from `molecules/`, `organisms/`, `store/`,
  `queries/` or `lib/api/`,
- a file under `molecules/` imports from `organisms/`, `store/`, `queries/` or
  `lib/api/`,
- a file under `templates/` imports anything but atoms and React,
- any module outside `store/` declares mutable module-level state,
- `tokens.css` is imported by anything other than the root layout,
- any file other than `tokens.ts` contains a colour literal.

That last rule is what stops the 40-literal drift from happening a second time.

## 5. Stack, pinned

| Choice | Version | Reason |
|---|---|---|
| Next.js | 16.4.x | the App Router conventions, with static export |
| React | 19.x | required by Next 16 |
| TypeScript | 5.x, `strict` | `SPEC.md` section 10 |
| Zustand | 5.x | one container, selector subscriptions so an 8,000-tile grid does not re-render on an unrelated change, about 1 KB |
| TanStack Query | 5.x | polling, invalidation and cancellation on navigation, which is `BACKLOG.md` F11-S10 solved structurally rather than by hand |
| CSS Modules | built in | zero config, and the token layer stays inspectable |
| openapi-typescript and openapi-fetch | current | D24 |
| Vitest and Testing Library | current | `TESTING.md` section 6 |

Not Tailwind. A utility framework dissolves the token layer into class names
and makes the design system a second source of truth, which D25 forbids.

Not a virtualisation library. D23: the measure-one-row-then-lay-out algorithm is
40 lines and is itself the behaviour under test.

## 6. F0: parity capture, which blocks everything

New feature. It runs **first**, before F1, because it must run against the
version 1 application while that application still works. Every story produces a
committed fixture file and a loader.

| ID | Story | Acceptance | Tests |
|---|---|---|---|
| F0-S1 | Tag version 1 and record the tag in every fixture header | every fixture names one tag | `ui/tests/parity/test_provenance.ts::every_fixture_names_a_tag` |
| F0-S2 | Search grammar corpus: query string to parsed terms and clauses, over all 14 operator keys and all 6 comparators, quoted phrases, and malformed input | version 1's `parseQuery` output is reproduced exactly | `ui/tests/parity/search.test.ts::grammar_corpus` |
| F0-S3 | Facet corpus: a synthetic library to facet counts, ordering, caps, zero retention and above-the-fold placement | counts and order match | `ui/tests/parity/facets.test.ts::counts`, `::ordering`, `::caps`, `::zero_retained` |
| F0-S4 | Twin corpus: title pairs to exact and loose clusters, including the known false pairs | clusters match, and loose pairs are marked loose | `ui/tests/parity/twins.test.ts::exact`, `::loose`, `::known_non_pairs` |
| F0-S5 | Sort corpus: titles to sort keys, covering accents, leading articles and digit runs | keys match, and 2 sorts before 10 | `ui/tests/parity/sort.test.ts::keys` |
| F0-S6 | Format corpus: bytes to strings, size strings to bytes, seconds to ETA, including negatives and nulls | output matches character for character | `ui/tests/parity/format.test.ts::corpus` |
| F0-S7 | Grid layout corpus: viewport width and tile size to column count, measured row height and window bounds | the same window is computed | `ui/tests/parity/windowing.test.ts::bounds` |
| F0-S8 | Progress corpus: run samples to percentage, rate and ETA, including the run-banking transition and the 99 per cent cap | identical arithmetic | `ui/tests/parity/progress.test.ts::corpus` |
| F0-S9 | Token and contrast snapshot: the as-is table from `CAPTURE-TOKENS.md`, committed, so the correction set is reviewable as a diff | the snapshot reproduces the 31 measured pairs, and `_tools/contrast.py --strict` is the oracle | `ui/tests/parity/tokens.test.ts::as_is_snapshot` |
| F0-S10 | Every corpus is synthetic or built from published game titles. No path, filename, hash, device identifier or catalogue row from the owner's library appears in any fixture | the publication lint passes over `ui/tests/fixtures` | `_tools/repo-lint.py --strict`, `ui/tests/parity/test_provenance.ts::no_owner_data` |

F0-S10 is not ceremony. D6 says the repository ships no data, and a parity
fixture is the most tempting place to smuggle a real library in.

## 7. F11 re-cut

The existing 19 stories are replaced by 34 in five bands. Story identifiers are
reissued, so the Notion board's F11 rows are re-seeded from this file.

### Band A, foundations

| ID | Story | Depends on | Tests |
|---|---|---|---|
| F11-S1 | Next.js project, App Router, strict TypeScript, static export, pinned versions, exported into the engine's static directory | F10-S2 | `ui/tests/build.test.ts::exports_static`, `::no_node_at_runtime` |
| F11-S2 | `tokens.ts` as the single source, generating `tokens.css` and types, carrying the corrected values from `CAPTURE-TOKENS.md` section 6 | F0-S9 | `ui/tests/design/tokens.test.ts::generated_matches_source` |
| F11-S3 | Contrast test over the generated token set, text at 4.5 and non-text at 3.0, computed not asserted by hand | F11-S2 | `ui/tests/design/contrast.test.ts::aa_all_pairs`, `::focus_ring_on_every_surface` |
| F11-S4 | Layering test per section 4, including the colour-literal rule | F11-S1 | `ui/tests/layering.test.ts` and its six planted violations |
| F11-S5 | Generated API client, with a check that the committed client matches the committed OpenAPI document | F10-S2 | `ui/tests/api/client.test.ts::generated_matches_openapi` |
| F11-S6 | One Zustand store with six slices, and a test that no module outside it holds mutable module state | F11-S1 | `ui/tests/store.test.ts::single_container`, `::no_module_state` |
| F11-S7 | Query layer and the job-polling hook, cancelled on navigation, with the socket guard satisfied | F11-S5 | `ui/tests/queries/job.test.ts::cancels_on_navigation`, `::no_network_in_tests` |

### Band B, atoms

| ID | Story | Depends on | Tests |
|---|---|---|---|
| F11-S8 | 24 atoms with the variants in `CAPTURE-COMPONENTS.md` section 2 | F11-S2 | `ui/tests/atoms/*.test.ts` |
| F11-S9 | Focus ring: `--focus` with a 2 px offset in the surrounding surface, so it passes 3:1 on every surface including the primary fill | F11-S3 | `ui/tests/a11y/focus.test.ts::visible_on_every_surface` |
| F11-S10 | Every interactive atom is a button or a link; the eight element classes that are `div` or `span` today become real controls | F11-S8 | `ui/tests/a11y/keyboard.test.ts::all_atoms_operable` |
| F11-S11 | Every input atom carries a programmatically associated label | F11-S8 | `ui/tests/a11y/labels.test.ts::no_unlabelled_input` |
| F11-S12 | `prefers-reduced-motion` honoured by the spinner and the compare-card fade | F11-S8 | `ui/tests/a11y/motion.test.ts::respects_preference` |

### Band C, molecules and logic

| ID | Story | Depends on | Tests |
|---|---|---|---|
| F11-S13 | `lib/format` pinned by the F0 corpus | F0-S6 | `ui/tests/parity/format.test.ts` |
| F11-S14 | `lib/search`: the 14 keys and 6 comparators, pinned by the F0 corpus | F0-S2 | `ui/tests/parity/search.test.ts` |
| F11-S15 | `lib/facets`: the one-pass fail computation, caps, zero retention, above-the-fold chosen values | F0-S3 | `ui/tests/parity/facets.test.ts` |
| F11-S16 | `lib/sort` and `lib/scale`: the sort key and the log size scale | F0-S5 | `ui/tests/parity/sort.test.ts`, `::scale` |
| F11-S17 | `lib/windowing` as a hook, the ported algorithm with a two-row overscan and one definition of the grid gap | F0-S7 | `ui/tests/parity/windowing.test.ts` |
| F11-S18 | `lib/progress`: the sync arithmetic, removal weighting, the 99 per cent cap, rate from the first byte | F0-S8 | `ui/tests/parity/progress.test.ts` |
| F11-S19 | `FacetSection` and `RangeFacet`, with the paired-thumb constraints and persisted collapse | F11-S15 | `ui/tests/molecules/facets.test.ts::paired_thumbs`, `::collapse_persists` |
| F11-S20 | `GameTile` and `GameRow` with all four badges | F11-S8 | `ui/tests/molecules/tile.test.ts` |
| F11-S21 | `CapacityMeter`, five states, thresholds from settings rather than from the page | F10-S8 | `ui/tests/molecules/capacity.test.ts::thresholds_from_settings`, `::five_states` |
| F11-S22 | `SyncControl` across idle, disabled and running | F11-S18 | `ui/tests/molecules/sync-control.test.ts` |
| F11-S23 | The remaining 21 molecules | F11-S8 | `ui/tests/molecules/*.test.ts` |

### Band D, organisms, templates and pages

| ID | Story | Depends on | Tests |
|---|---|---|---|
| F11-S24 | The five templates, slots only, no data | F11-S8 | `ui/tests/templates/*.test.ts` |
| F11-S25 | `Modal` with dialog role, accessible name, focus move, trap, restore and Escape; `ConfirmDialog` and `PromptDialog` replacing all six native dialogs | F11-S24 | `ui/tests/a11y/modal.test.ts::role_and_name`, `::trap`, `::restore`, `::escape`; `ui/tests/organisms/no-native-dialogs.test.ts` |
| F11-S26 | `VirtualGameGrid` over the ported hook | F11-S17 | `ui/tests/organisms/grid.test.ts::window_matches_fixture` |
| F11-S27 | `FilterSidebar`: nine facets, two range facets, smart lists, four flags, chip list | F11-S19 | `ui/tests/organisms/sidebar.test.ts` |
| F11-S28 | `LibraryToolbar` and `SelectionSummary`, with the debounced capacity refresh | F11-S21 | `ui/tests/organisms/toolbar.test.ts` |
| F11-S29 | `DetailPanel`, version picker, tag decisions, rematch | F11-S23 | `ui/tests/organisms/detail.test.ts` |
| F11-S30 | `TwinCompareCard`, bound to the selected tile, keyboard reachable, both actions firing without a pointer | F0-S4 | `ui/tests/organisms/twins.test.ts::keyboard_reachable`, `::switch_and_select`, `::selected_tile_only` |
| F11-S31 | `/devices`: `DeviceCard` in both variants with the three candidate sub-states, and `NewProfileDialog` | F10-S10 | `ui/tests/pages/devices.test.ts` |
| F11-S32 | `/devices?id=`: systems table, plan summary, run history, the device watcher as a query | F10-S10 | `ui/tests/pages/device.test.ts::search_param_route`, `::watcher_is_a_query` |
| F11-S33 | `/system-files`: list, detail, others, and the store-only table when no device is chosen | F10-S7 | `ui/tests/pages/sysfiles.test.ts` |
| F11-S34 | `/settings` built to `SETTINGS.md`, including the setup section in first-run order | F10-S8 | `ui/tests/pages/settings.test.ts::per_section_save`, `::edit_survives_job`, `::setup_steps` |

### Band E, cross-cutting gates

These are not a phase. Each is a test that runs from the moment the first
component exists and fails the gate until the whole interface satisfies it.

| ID | Story | Tests |
|---|---|---|
| F11-S35 | Keyboard traversal reaches every interactive element on every page | `ui/tests/a11y/keyboard.test.ts::all_controls_reachable` |
| F11-S36 | The live region announces every toast | `ui/tests/a11y/live-region.test.ts::announces_every_toast` |
| F11-S37 | No state is carried by colour alone; every state has a second channel | `ui/tests/a11y/non-colour.test.ts::every_state_has_a_second_channel` |
| F11-S38 | Every view recovers from a failed fetch with a retry, and no view can reach a permanent loading state | `ui/tests/organisms/errors.test.ts::retry_everywhere`, `::no_permanent_loading` |

## 8. Counts after this amendment (superseded by section 12)

| | Before | After |
|---|---|---|
| Features | 15 | 16 |
| Stories | 136 | 161 |
| F11 stories | 19 | 38 |
| New blocking feature | | F0, 10 stories |

The dependency graph gains F0 ahead of everything, and F11 moves from one band
to five:

```
F0 ─ F1 ─┬─ F2 ─┬─ F3 ─┬─ F4 ─┐
         │      │      ├─ F5 ─┤
         │      │      └─ F6 ─┴─ F7 ─┬─ F8 ─┐
         └─ F14 │                    └─ F9 ─┴─ F10 ─┬─ F11 A..E ─┬─ F13
                └──────────────────────────────────────└─ F12 ───┘
```

## 9. SPEC amendments

`SPEC.md` section 10 is replaced by the following. Everything else in `SPEC.md`
stands unchanged.

| Requirement |
|---|
| TypeScript, strict mode, React on Next.js with the App Router, built by `next build` with `output: 'export'` to a static bundle the engine serves by manifest lookup. |
| No Node.js process exists at runtime. The export is produced at build time and frozen into the release artefact. |
| No route takes a runtime identifier as a path segment. |
| Components are organised as atoms, molecules, organisms, templates and pages, with placement decided by the two mechanical questions in `CAPTURE-COMPONENTS.md` section 1 and enforced by `ui/tests/layering.test.ts`. |
| Every design token is declared once in `ui/src/design/tokens.ts`. No colour literal exists anywhere else, enforced by a test. |
| The published design system is generated from that same token source. |
| The API client is generated from the OpenAPI document. No hand-written fetch wrapper. |
| One client store. Server state in a query layer. No module-level mutable state outside the store, enforced by a test. |
| Behaviour parity with version 1 for the search grammar, facet counts and ordering, twin clustering, sort keys, formatting, the windowed grid's layout arithmetic and the sync progress arithmetic, each pinned by a fixture captured from the tagged version 1. |
| A platform adapter chosen at load from the shell the engine reports. Methods: confirm, prompt, pick folder, reveal, open external, copy, notify, quit. Each degrades in the browser. |
| No native `confirm`, `prompt` or `alert`. |
| The Settings page is implemented to `SETTINGS.md`. |
| Every interactive element is reachable and operable by keyboard. Elements that act as buttons are buttons. |
| Modals carry a dialog role and an accessible name, move focus in, trap focus, restore focus on close, and close on Escape. |
| Every input has a programmatically associated label. |
| The live region announces every toast. |
| Text contrast meets 4.5:1 and non-text contrast 3:1, verified by a test that computes ratios over the generated token set. |
| A visible focus indicator reaches 3:1 against every surface it can appear on, including filled accent surfaces. |
| `prefers-reduced-motion` is honoured. |
| State is never carried by colour alone. |
| A failed fetch produces an error state with a retry, never a permanent loading state. |
| A job poller survives navigation and does not write to a detached node. |

## 10. Deviations from parity, declared

Parity is the constraint, so every departure is listed here or it is a defect.

| Deviation | Why |
|---|---|
| Views become routes; the back button works and screens are linkable | unavoidable with the App Router, and an improvement |
| The device page is `/devices?id=`, not a path segment | forced by static export, D20 |
| Eight classes of clickable `div` and `span` become buttons and links | `SPEC.md` section 10 |
| Five `confirm()` and one `prompt()` become dialogs | `SPEC.md` section 10 |
| Control borders become visible: `--border` at `#666f85` against `--divider` at the old `#2e323c` | 1.4.11 at 3:1. **The single largest visual change in the set, and one token to revert.** |
| Primary fills deepen to `--accent-solid: #1f6cff` | white labels were at 3.22:1 |
| The offline lamp becomes a visible grey disc | it was at 1.61:1 |
| A focus ring exists | there was none |
| The spinner stops for `prefers-reduced-motion` | there was no such block |
| The settings page is rebuilt, not ported | already specified separately in `SETTINGS.md` |
| Capacity thresholds arrive from the engine | `SPEC.md` section 7 |
| Job results stop being rendered as `JSON.stringify` | `SPEC.md` section 8 |

## 11. Recover is routed in

**Decided 8 October 2026: Recover gets its own page and a way to reach it.**

`renderRecover()` exists at `app.js:1060`, the `place` endpoint exists at
`server.py:616`, and `transfer.place_pulled` implements it. No section, no nav
button and no `showView` branch has ever reached it. The feature is finished on
both sides and has never been usable. It is now built properly rather than
quietly dropped, which means it also gets tested and maintained like everything
else.

| Requirement |
|---|
| `/recover` is a route with a nav entry, not a page you have to know about. |
| It shows, per device, the items on that device that the store has no copy of, and says plainly that an unselected item is removed by the next sync. |
| It shows, per run, the items that run pulled back off a device, with a place action. |
| Placing never overwrites a store file. A name that already exists is reported, not replaced. This is `BACKLOG.md` F7-S11 and it holds whatever the interface does. |
| After a successful place the store is rescanned, so the placed game appears in the library without a manual step. |
| The nav entry is present only when there is something to recover, so an empty Recover page is never a dead end the user navigates to. |

Two stories are added to band D:

| ID | Story | Depends on | Tests |
|---|---|---|---|
| F11-S39 | `/recover`, with a nav entry that appears only when a device holds something the store does not, and copy that states the next sync would remove it | F10-S10 | `ui/tests/pages/recover.test.ts::lists_missing_from_store`, `::nav_hidden_when_empty`, `::states_removal_consequence` |
| F11-S40 | Pulled-item placement per run, refusing a name the store already holds, rescanning on success | F7-S11 | `ui/tests/pages/recover.test.ts::place_refuses_existing_name`, `::rescan_after_place` |

## 12. Counts, final

| | Before | After |
|---|---|---|
| Features | 15 | 16 |
| Stories | 136 | 163 |
| F11 stories | 19 | 40 |
| New blocking feature | | F0, 10 stories |

## 13. Release, decided

**Decided 8 October 2026: the release waits for the portability refactor.**

The 10 hardcoded locations in `docs/KNOWN-LIMITATIONS.md` are fixed first, so
the artefact works on a machine that is not this one, and the first release is
then tagged `v0.1.0`. No `v0.0.1-prerelease` is cut. An installer that only
works on its author's PC is not an installer, and publishing one invites a bug
report that is really a configuration report.
