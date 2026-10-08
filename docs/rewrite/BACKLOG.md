# ROM-Sync 2: features, stories, dependencies, tests

Each story is a unit of autonomous work: one branch, one pull request, gated by
`python tools/verify.py`. A story is done when its named tests exist, failed
before the change, and pass after it, and the whole gate is green.

Story IDs are stable. The Notion board mirrors this file; this file is
authoritative.

## Feature order

```
F1 ─┬─ F2 ─┬─ F3 ─┬─ F4 ─┐
    │      │      ├─ F5 ─┤
    │      │      └─ F6 ─┴─ F7 ─┬─ F8 ─┐
    └─ F14 │                    └─ F9 ─┴─ F10 ─┬─ F11 ─┬─ F13
           └────────────────────────────────────└─ F12 ─┘
```

| ID | Feature | Depends on |
|---|---|---|
| F1 | Foundations and the verification gate | none |
| F2 | Persistence and migrations | F1 |
| F3 | Domain model and rules | F1 |
| F4 | Store scanning | F2, F3 |
| F5 | Metadata and matching | F2, F3 |
| F6 | Destination ports and adapters | F2, F3 |
| F7 | Transfer engine | F6 |
| F8 | System files | F7 |
| F9 | Jobs service | F2, F7 |
| F10 | HTTP API v1 | F4, F5, F7, F9 |
| F11 | Interface port to TypeScript | F10 |
| F12 | Desktop shell | F10 |
| F13 | Installer, dependency checks, release | F11, F12 |
| F14 | Import from version 1 | F2, F3 |
| F15 | Diagnostics and support bundle | F9, F10 |

---

## F1 Foundations and the verification gate

| ID | Story | Depends on | Acceptance | Tests |
|---|---|---|---|---|
| F1-S1 | Repository layout created as specified, with empty packages and `pyproject.toml` pinning Python 3.12 or newer | none | Every directory in SPEC section 1 exists and imports | `tests/unit/test_layout.py::test_packages_importable` |
| F1-S2 | Layering test enforces the dependency rule | F1-S1 | A deliberate illegal import fails the test | `tests/unit/test_layering.py::test_no_illegal_edges`, `::test_detects_planted_violation` |
| F1-S3 | `tools/verify.py` runs format, lint, type check, tests, coverage gate, repo lint and OpenAPI check, and exits non-zero on any failure | F1-S1 | A single command; a forced failure in each stage is reported and exits 1 | `tests/unit/test_verify_gate.py::test_each_stage_can_fail` |
| F1-S4 | Determinism harness: frozen clock, seeded randomness, temp data directory, socket guard that fails any test touching the network | F1-S1 | A test that opens a socket fails with a named error | `tests/unit/test_determinism.py::test_socket_guard`, `::test_clock_frozen` |
| F1-S5 | Error taxonomy in `domain/errors.py`, with a code per class | F1-S1 | Every raised domain error carries a stable code | `tests/unit/domain/test_errors.py::test_codes_unique_and_stable` |
| F1-S6 | Structured progress and job sink protocols | F1-S5 | A sink receives phase, done, total, current; no formatted prose | `tests/unit/test_sink.py::test_event_shape` |
| F1-S7 | GitHub Actions workflow runs the gate on a Windows runner for pull requests | F1-S3 | A pull request shows the gate as a required check | `tests/unit/test_ci_config.py::test_gate_is_the_only_entrypoint` |
| F1-S8 | Config registry with type, default, range, secret flag and restart flag; loader and validators | F1-S5 | An out-of-range value is rejected with the field named | `tests/unit/config/test_registry.py::test_defaults_have_no_absolute_paths`, `::test_validation_rejects_out_of_range`, `::test_secret_never_serialised` |

## F2 Persistence and migrations

| ID | Story | Depends on | Acceptance | Tests |
|---|---|---|---|---|
| F2-S1 | Schema version 1 as a single migration step, all DDL in one place | F1-S1 | A fresh database reports `user_version = 1` | `tests/unit/adapters/db/test_migrations.py::test_fresh_database_at_head` |
| F2-S2 | Migration runner: ordered, forward-only, transactional, idempotent, under a file lock, from the composition root only | F2-S1 | Running twice is a no-op; two concurrent runners do not both apply | `::test_idempotent`, `::test_concurrent_runners_serialise`, `::test_not_run_from_connect` |
| F2-S3 | Pre-migration backup for any non-metadata-only step | F2-S2 | A backup file exists before the step and is removed only on success | `::test_backup_taken_and_retained_on_failure` |
| F2-S4 | An unversioned legacy database reads as version 1 and migrates forward | F2-S2 | A database with `user_version = 0` reaches head without data loss | `::test_unversioned_treated_as_v1` |
| F2-S5 | Connection factory: WAL, foreign keys on, busy timeout from config, path injectable | F1-S8 | A test can point the engine at a temp database | `tests/unit/adapters/db/test_connect.py::test_path_injectable`, `::test_pragmas_applied` |
| F2-S6 | Repositories for games, devices, selections, runs, jobs, tags, sysfiles and config, returning domain models | F2-S5, F3-S1 | No sqlite row type crosses a repository boundary | `tests/unit/adapters/db/test_repos.py::test_returns_domain_models`, `::test_no_row_leaks` |
| F2-S7 | Config stored one row per key, secrets in a separate namespace, partial writes, `null` deletes | F2-S6 | A secret can be replaced and removed without touching other keys | `tests/unit/adapters/db/test_config_repo.py::test_partial_write`, `::test_delete_key`, `::test_secret_namespace_separate` |
| F2-S8 | SQL audit test: every statement binds its values; no identifier interpolation | F2-S6 | A planted f-string statement fails the test | `tests/unit/adapters/db/test_sql_safety.py::test_no_interpolated_sql` |

## F3 Domain model and rules

| ID | Story | Depends on | Acceptance | Tests |
|---|---|---|---|---|
| F3-S1 | Models: `GameUnit`, `SystemKey`, `Selection`, `Plan`, `Op`, `DeviceRef`, `Marker` | F1-S1 | Immutable, typed, no IO | `tests/unit/domain/test_models.py::test_immutable` |
| F3-S2 | `ContainedPath`, `RomsRoot`, `StoreRoot` with the full escape corpus refused | F3-S1 | Every entry in the corpus raises `PathEscape` | `tests/unit/domain/test_paths.py::test_escape_corpus`, `::test_name_with_separator_refused`, `::test_absolute_refused`, `::test_symlink_outside_root_refused` |
| F3-S3 | Title identity: strict and loose keys | F3-S1 | The title corpus fixture produces the expected keys | `tests/golden/test_title_identity.py::test_corpus` |
| F3-S4 | Twin clustering over the title corpus | F3-S3 | Known pairs cluster; known false pairs do not | `tests/golden/test_twins.py::test_known_pairs`, `::test_known_non_pairs` |
| F3-S5 | Selection algebra, including minimal-override storage | F3-S1 | An override agreeing with the mode is not stored | `tests/unit/domain/test_selection.py::test_minimal_override`, `::test_clear_override` |
| F3-S6 | Plan diff producing send, update, remove, unchanged and unknown systems | F3-S5 | A fixture store and device inventory produce the expected plan | `tests/golden/test_plan.py::test_fixture_plan` |
| F3-S7 | Guards: unmanaged folders, emulator state, bios | F3-S6 | An emulator state folder is never in `remove`, whatever its recorded kind | `tests/unit/domain/test_guards.py::test_emulator_state_never_removed`, `::test_kind_drift_still_guarded`, `::test_unmanaged_untouched`, `::test_bios_not_games` |
| F3-S8 | Fit arithmetic models peak usage, with the margin from config | F3-S6, F1-S8 | An update-heavy plan on a nearly full volume does not report a fit | `tests/unit/domain/test_fit.py::test_peak_not_net`, `::test_margin_from_config` |
| F3-S9 | Operation ordering defined once | F3-S6 | The order is remove, update, send, asserted from one source | `tests/unit/domain/test_ordering.py::test_single_definition` |

## F4 Store scanning

| ID | Story | Depends on | Acceptance | Tests |
|---|---|---|---|---|
| F4-S1 | `StorePort` and a filesystem adapter over a fixture tree | F3-S2 | A fixture store yields the expected units | `tests/unit/adapters/store/test_scan.py::test_fixture_tree` |
| F4-S2 | Multi-disc sets and folder games resolve to one unit with members | F4-S1 | A playlist beside discs is one unit | `::test_multi_disc_is_one_unit`, `::test_folder_game` |
| F4-S3 | System recognition from the front-end system file, with absent and unreadable distinguished | F4-S1 | An unreadable file raises; an absent one skips | `::test_absent_vs_unreadable` |
| F4-S4 | Prune is scoped to systems actually visited, and refuses when nothing was indexed | F4-S3 | An unreadable system file cannot delete that system's games | `tests/unit/adapters/store/test_prune.py::test_unreadable_system_does_not_prune`, `::test_zero_systems_refuses` |
| F4-S5 | Scan is incremental by size and modification time, with a tolerance | F4-S1 | A second scan of an unchanged tree reports no changes | `::test_second_scan_idempotent` |
| F4-S6 | The scanner never writes to the store | F4-S1 | A read-only fixture tree scans successfully | `::test_store_not_written` |

## F5 Metadata and matching

| ID | Story | Depends on | Acceptance | Tests |
|---|---|---|---|---|
| F5-S1 | `MetadataPort` and a recorded-response fake | F3-S1 | No test reaches the network | `tests/unit/adapters/metadata/test_fake.py::test_offline` |
| F5-S2 | IGDB adapter receives credentials by injection and touches no storage | F5-S1 | Constructing it without storage succeeds | `::test_no_storage_dependency`, `::test_credentials_injected` |
| F5-S3 | One shared throttle honouring the configured rate across concurrent passes | F5-S2 | Two concurrent passes do not exceed the budget | `tests/unit/adapters/metadata/test_throttle.py::test_shared_budget` |
| F5-S4 | Token lifecycle: refresh margin, invalidation on rejection, retry and backoff | F5-S2 | Each path is exercised against the fake | `tests/unit/adapters/metadata/test_token.py::test_refresh`, `::test_invalidate_on_401`, `::test_backoff_on_429` |
| F5-S5 | Matcher ported with its thresholds, pinned by the scoring fixture | F5-S1, F3-S3 | The fixture's expected matches and rejections reproduce exactly | `tests/golden/test_matcher.py::test_scoring_corpus`, `::test_accept_threshold`, `::test_off_platform_penalty` |
| F5-S6 | Query construction escapes every delimiter of the query language | F5-S2 | A title containing a delimiter cannot alter the query | `tests/unit/adapters/metadata/test_query_escaping.py::test_delimiter_corpus` |
| F5-S7 | Full summaries stored; truncation is a presentation concern | F5-S2 | The stored summary is the source text | `tests/unit/app/test_metadata.py::test_summary_not_truncated_at_write` |
| F5-S8 | Cover preservation: a re-match with no cover keeps the existing one | F5-S5 | The prior cover survives | `::test_cover_preserved_on_rematch` |
| F5-S9 | Resumable passes with per-item commit and an error-abort valve | F5-S5 | An interrupted pass resumes without repeating work | `::test_resume`, `::test_abort_after_consecutive_errors` |
| F5-S10 | Franchise rules loaded from a data file; the pass only proposes | F5-S1 | A rule change needs no code change; a human decision is never overwritten | `tests/unit/app/test_tags.py::test_rules_from_data_file`, `::test_never_overwrites_decision` |
| F5-S11 | Artwork fallback source as a declared capability | F5-S1 | Absent credentials still yield a working catalogue with fallback art | `::test_fallback_without_credentials` |

## F6 Destination ports and adapters

| ID | Story | Depends on | Acceptance | Tests |
|---|---|---|---|---|
| F6-S1 | The six destination ports, with a capability query | F3-S2 | `supports()` answers per port | `tests/unit/ports/test_dest_ports.py::test_capability_query` |
| F6-S2 | `dest_fake`: in-memory, scriptable failures, deterministic | F6-S1 | Every contract requirement is exercisable | `tests/contract/test_dest_contract.py` parameterised on the fake |
| F6-S3 | The contract suite, requirements C1 to C10 | F6-S2 | An adapter that violates any requirement fails | `tests/contract/test_dest_contract.py::test_c1_errors_are_exceptions` through `::test_c10_no_partial_final_names` |
| F6-S4 | Volume adapter | F6-S3 | Passes the contract suite against a temp directory | contract suite, parameterised |
| F6-S5 | ADB adapter, command construction isolated and unit tested without a device | F6-S3 | Commands are built and quoted correctly; absence of the tool is a clear error | `tests/unit/adapters/dest_adb/test_commands.py::test_quoting`, `::test_missing_tool_error` |
| F6-S6 | MTP adapter, script construction isolated and unit tested without a device | F6-S3 | Scripts are built correctly; arrival policy is a parameter, not a literal | `tests/unit/adapters/dest_mtp/test_scripts.py::test_arrival_policy_from_config` |
| F6-S7 | One arrival policy, sized from the file, shared by staging and bulk transfer | F6-S6 | Staging a large file uses the same budget as a transfer | `::test_single_arrival_policy` |
| F6-S8 | Device identity is typed per kind and never cross-assigned | F6-S1 | Each adapter's identity names its own kind | `tests/unit/adapters/test_identity.py::test_kind_specific` |
| F6-S9 | Stable device reference derived from identity, not a list position | F6-S8 | A reference survives a probe refresh and a reordering | `tests/unit/app/test_devices.py::test_ref_stable_across_refresh`, `::test_no_positional_index` |
| F6-S10 | Capacity has no side effects and performs no device-wide probe | F6-S1 | Reading capacity writes nothing | `::test_capacity_is_pure` |
| F6-S11 | Marker is the device identity; a profile survives a transport change | F6-S8 | The same marker over a different transport resolves to one profile | `::test_marker_is_identity`, `::test_transport_change_keeps_profile` |
| F6-S12 | A marker read from a device is untrusted: every path validated on ingress | F6-S11, F3-S2 | A crafted marker is rejected and nothing is written | `tests/unit/app/test_marker_trust.py::test_crafted_paths_rejected` |

## F7 Transfer engine

| ID | Story | Depends on | Acceptance | Tests |
|---|---|---|---|---|
| F7-S1 | `DestBulkTransfer` implemented per transport, dispatched by capability | F6-S3 | No caller branches on transport name | `tests/unit/test_no_kind_branching.py::test_app_and_api_clean` |
| F7-S2 | Run records: durable per-run folder and database rows, written by the worker | F2-S6 | An interrupted run remains observable | `tests/unit/app/test_sync.py::test_run_record_durable` |
| F7-S3 | Guard enforced at the destructive site | F3-S7 | A remove op naming an emulator state folder is refused by the engine | `::test_remove_guard_at_destructive_site`, `::test_refuses_op_built_externally` |
| F7-S4 | Containment assertion immediately before every destructive call | F3-S2 | A planted escaping op raises and deletes nothing | `::test_containment_before_delete` |
| F7-S5 | Verified transfer: content verification where the transport supports it, and no recorded hash where it does not | F6-S1 | An unverified transfer records no hash | `::test_no_hash_when_unverified`, `::test_hash_when_verified` |
| F7-S6 | Replacement never leaves a window with neither copy | F6-S3 | A simulated interruption leaves either the old file or the new, never neither | `::test_replace_atomic`, `::test_folder_replace_has_rollback` |
| F7-S7 | A run with failures is reported as failed, with counts | F7-S2 | A run where every op fails is not `done` | `::test_all_failed_is_failed`, `::test_counts_reported` |
| F7-S8 | Cooperative cancellation between items, never inside a copy | F9-S3 | A cancel during a run stops after the current item | `::test_cancel_between_items`, `::test_never_cancels_mid_copy` |
| F7-S9 | The sync log append cannot fail a sync and is written even on an interrupted run | F7-S2 | An interrupted run still appends a line | `::test_log_written_on_interrupt`, `::test_log_failure_does_not_fail_sync` |
| F7-S10 | One sync workflow, used by the API, the CLI and a scheduled run | F7-S2 | There is exactly one implementation | `::test_single_sync_entrypoint` |
| F7-S11 | Pull and place: a device item the store lacks can be retrieved and placed without overwriting | F7-S2 | Placing never overwrites | `::test_place_never_overwrites` |

## F8 System files

| ID | Story | Depends on | Acceptance | Tests |
|---|---|---|---|---|
| F8-S1 | Registry split into data: systems, requirements, install locations | F3-S1 | Adding a system is a data change | `tests/unit/app/test_sysfiles_registry.py::test_data_driven` |
| F8-S2 | Store-side resolution and hashing, with the limit from config | F8-S1, F1-S8 | Files above the limit are size-compared only | `tests/unit/app/test_sysfiles_store.py::test_hash_limit` |
| F8-S3 | Device-side staging to the configured template, with no transport branching | F8-S1, F6-S1 | The template is honoured; `{system}` is required | `tests/unit/app/test_sysfiles_device.py::test_template`, `::test_no_kind_branching` |
| F8-S4 | Staging is replace-safe: no delete before a successful write, with rollback | F8-S3 | A failed write leaves the previous staged file intact | `::test_rollback_on_failed_write`, `::test_no_delete_before_write` |
| F8-S5 | `remove_other` takes a contained path and a bare name | F3-S2 | A name containing a separator or an absolute path is refused | `::test_name_corpus_refused` |
| F8-S6 | Readiness state machine, returning state rather than interface vocabulary | F8-S3 | Staged and installed are reported separately, with no button names | `tests/unit/app/test_readiness.py::test_state_not_presentation` |
| F8-S7 | The engine never writes into an emulator's own directories | F8-S3 | Only the staging folder is written | `::test_only_staging_written` |

## F9 Jobs service

| ID | Story | Depends on | Acceptance | Tests |
|---|---|---|---|---|
| F9-S1 | Job registry in the engine, usable with no HTTP layer present | F2-S6 | A job runs from a plain script | `tests/unit/jobs/test_registry.py::test_runs_without_http` |
| F9-S2 | Jobs persisted on every state change | F9-S1 | A record survives a process restart | `::test_persisted` |
| F9-S3 | Cooperative cancellation tokens | F9-S1 | A cancel moves to `cancelling` then `cancelled` | `::test_cancel_lifecycle` |
| F9-S4 | Startup reconciliation of interrupted jobs and runs, including out-of-process workers | F9-S2 | Nothing remains `running` after startup | `::test_reconcile_on_startup`, `::test_detects_out_of_process_worker` |
| F9-S5 | Conflict guard by kind and target | F9-S1 | A second metadata job is refused while one runs | `::test_guard_by_kind_and_target` |
| F9-S6 | Snapshot reads under the lock; no partial record observable | F9-S2 | A concurrent reader never sees a half-updated record | `::test_snapshot_consistent` |
| F9-S7 | Eviction of terminal jobs beyond the configured history | F9-S2, F1-S8 | The table does not grow without bound | `::test_eviction` |
| F9-S8 | Structured progress throughout, no formatted prose in the engine | F1-S6 | Every progress event is structured | `::test_structured_progress_only` |

## F10 HTTP API v1

| ID | Story | Depends on | Acceptance | Tests |
|---|---|---|---|---|
| F10-S1 | Application factory, routers, declared models, error envelope | F9-S1 | Every response validates against its model | `tests/unit/api/test_contracts.py::test_models_declared`, `::test_error_envelope` |
| F10-S2 | Checked-in OpenAPI document and a drift check in the gate | F10-S1 | An undeclared change fails the gate | `tools/openapi_check.py`, `tests/unit/api/test_openapi.py::test_no_drift` |
| F10-S3 | No write on a GET, enforced by a test over the route table | F10-S1 | A planted write on a GET fails the test | `::test_no_write_on_get` |
| F10-S4 | Loopback bind by default; any other bind requires explicit config and logs what it disables | F1-S8 | A non-loopback bind disables the shell endpoints | `tests/unit/api/test_binding.py::test_default_loopback`, `::test_shell_disabled_off_loopback` |
| F10-S5 | Same-origin check and a page token on every mutation | F10-S1 | A cross-origin mutation is refused | `tests/unit/api/test_csrf.py::test_cross_origin_refused`, `::test_token_required` |
| F10-S6 | Static assets served from a build manifest by name | F10-S1 | A traversal attempt cannot reach any file outside the bundle | `tests/unit/api/test_static.py::test_traversal_corpus_refused`, `::test_manifest_lookup_only` |
| F10-S7 | Library, game, systems and settings read endpoints | F4-S1, F5-S1 | Shapes match the models | `tests/unit/api/test_library_routes.py` |
| F10-S8 | Settings write with per-field validation, `null` delete, and a never-echoed secret | F2-S7 | A rejected field names itself; the secret never appears in a response | `tests/unit/api/test_settings_routes.py::test_field_error`, `::test_secret_never_returned`, `::test_null_deletes` |
| F10-S9 | Credential test endpoint reporting the failing stage, working on unsaved input | F5-S4 | Each stage is reported distinctly | `tests/unit/api/test_igdb_test_route.py::test_stages` |
| F10-S10 | Device endpoints using the stable reference | F6-S9 | No positional index crosses the boundary | `tests/unit/api/test_device_routes.py::test_ref_only` |
| F10-S11 | Selection endpoints delegating to the domain, no SQL in the layer | F3-S5 | A route-level SQL statement fails a test | `tests/unit/api/test_no_sql_in_api.py::test_clean` |
| F10-S12 | Sync endpoints: plan, start, status, cancel | F7-S10, F9-S3 | Starting returns a job; cancel is honoured | `tests/unit/api/test_sync_routes.py` |
| F10-S13 | Job endpoints: list, get, cancel | F9-S1 | Snapshot semantics preserved | `tests/unit/api/test_job_routes.py` |
| F10-S14 | Maintenance endpoints: compact, clear cache, prune covers, prune runs, all as jobs with a dry run where destructive | F9-S1 | A destructive maintenance action dry-runs first | `tests/unit/api/test_maintenance_routes.py::test_dry_run_first` |
| F10-S15 | Shell endpoints: reveal, pick folder, open external, each root-checked and loopback-only | F10-S4 | A path outside the roots is refused | `tests/unit/api/test_shell_routes.py::test_root_check`, `::test_scheme_allowlist` |

## F11 Interface port to TypeScript

| ID | Story | Depends on | Acceptance | Tests |
|---|---|---|---|---|
| F11-S1 | Vite and TypeScript strict project, bundle served by the engine, generated client | F10-S2 | The client is generated, not hand-written | `ui/tests/client.test.ts::generated_matches_openapi` |
| F11-S2 | One state container, no module-level mutable state | F11-S1 | A lint rule fails on module-level mutation | `ui/tests/state.test.ts::single_container` |
| F11-S3 | Platform adapter with browser and desktop implementations | F11-S1 | Every method degrades in the browser | `ui/tests/platform.test.ts::degrades`, `::no_native_dialogs` |
| F11-S4 | Search grammar ported, pinned by a parse fixture | F11-S1 | The fixture's queries parse to the same filters as version 1 | `ui/tests/search.test.ts::grammar_corpus` |
| F11-S5 | Facets ported: counts, ordering, zero handling, persistence | F11-S4 | Counts match the fixture | `ui/tests/facets.test.ts::counts`, `::zero_values_readable` |
| F11-S6 | Windowed grid and list, tile sizing | F11-S1 | Rendering is stable at fixture widths | `ui/tests/grid.test.ts::windowing` |
| F11-S7 | Detail panel, including versions and screenshots | F11-S1 | Behaviour parity | `ui/tests/detail.test.ts` |
| F11-S8 | Twin badge and compare card, reachable by keyboard | F11-S3 | The card opens and both actions fire without a pointer | `ui/tests/twins.test.ts::keyboard_reachable`, `::switch_and_select` |
| F11-S9 | Device page, selection controls, capacity meter with thresholds from settings | F10-S10 | Thresholds come from the engine, not the page | `ui/tests/device.test.ts::thresholds_from_settings` |
| F11-S10 | Sync modal, live progress, job polling that survives navigation | F10-S12 | A navigation mid-sync does not detach the poller | `ui/tests/sync.test.ts::poller_survives_navigation` |
| F11-S11 | System files page | F10-S7 | Behaviour parity | `ui/tests/sysfiles.test.ts` |
| F11-S12 | Settings page as specified, section by section, per-section save | F10-S8 | A job completing elsewhere does not discard an edit | `ui/tests/settings.test.ts::edit_survives_job`, `::per_section_save` |
| F11-S13 | Setup section shown while incomplete, in first-run order | F11-S12 | Each step completes from the page alone | `ui/tests/setup.test.ts::three_steps` |
| F11-S14 | Keyboard operability across every interactive element | F11-S1 | A traversal test reaches every control | `ui/tests/a11y.test.ts::all_controls_reachable` |
| F11-S15 | Modal semantics: role, name, focus move, focus trap, focus restore | F11-S1 | Focus cannot leave an open dialog | `ui/tests/a11y.test.ts::modal_focus` |
| F11-S16 | Labels associated with every input; live region announces toasts | F11-S1 | No input without a programmatic label | `ui/tests/a11y.test.ts::labels`, `::live_region` |
| F11-S17 | Contrast tokens meeting AA, verified over the palette | F11-S1 | Every foreground and background pair passes | `ui/tests/contrast.test.ts::aa_all_pairs` |
| F11-S18 | No state carried by colour alone | F11-S17 | Each state has a non-colour channel | `ui/tests/a11y.test.ts::non_colour_channel` |
| F11-S19 | Fetch failure produces an error state with retry, never a permanent loading state | F11-S1 | Every view recovers | `ui/tests/errors.test.ts::retry_everywhere` |

## F12 Desktop shell

| ID | Story | Depends on | Acceptance | Tests |
|---|---|---|---|---|
| F12-S1 | Shell process starts the engine in-process and opens the window | F10-S1 | Closing the window shuts the engine down cleanly | `tests/unit/desktop/test_shell.py::test_clean_shutdown` |
| F12-S2 | The embedded browser profile lives in the data directory | F12-S1 | Nothing is written to the user profile | `::test_profile_location` |
| F12-S3 | The engine reports the shell kind and capabilities | F10-S7 | The page upgrades from browser to desktop mode | `::test_shell_reported` |
| F12-S4 | Native dialogs through the shell endpoints, loopback-gated | F10-S15 | A non-loopback bind hides them | `::test_dialogs_gated` |
| F12-S5 | Notification for a job over the threshold, with the toast as source of truth | F9-S8 | A failed notification does not lose the message | `::test_notify_falls_back` |

## F13 Installer, dependency checks, release

| ID | Story | Depends on | Acceptance | Tests |
|---|---|---|---|---|
| F13-S1 | Frozen build of engine, API and desktop shell with the built interface | F11-S1, F12-S1 | The artefact runs with no Python installed | `tests/unit/installer/test_spec.py::test_bundle_contents` |
| F13-S2 | Dependency checks: Windows version, embedded browser runtime, disk space, data directory writability | F13-S1 | A missing runtime is reported and offered, never skipped silently | `::test_checks_reported`, `::test_missing_runtime_blocks` |
| F13-S3 | Installer with a data directory outside the install directory | F13-S1 | Replacing the application cannot touch data | `::test_data_outside_install` |
| F13-S4 | Uninstaller leaves data and says so | F13-S3 | Data survives an uninstall | `::test_uninstall_keeps_data` |
| F13-S5 | No content bundled and no default path to content | F13-S1 | The artefact contains no media, key or firmware file | `::test_no_content_bundled`, `::test_no_content_default_paths` |
| F13-S6 | First-run acceptance: a clean machine reaches a working catalogue through the interface alone | F13-S3, F11-S13 | A scripted first run with a fixture store succeeds with no file edited | `tests/e2e_fake/test_first_run.py::test_clean_machine` |
| F13-S7 | Release pipeline: tag, build, checksum, release notes, attach artefacts | F13-S1 | A tag produces a release with checksums | `tests/unit/test_ci_config.py::test_release_workflow` |
| F13-S8 | Optional transport absence is a state, not an error | F6-S5 | With no transport tool present the application still runs | `tests/e2e_fake/test_first_run.py::test_optional_tool_absent` |

## F14 Import from version 1

| ID | Story | Depends on | Acceptance | Tests |
|---|---|---|---|---|
| F14-S1 | Reader for a version 1 database given a path | F2-S6 | A fixture version 1 database is read without modification | `tests/unit/tools/test_import_v1.py::test_reads_fixture` |
| F14-S2 | Mapping of games, selections, tag decisions and device profiles | F14-S1 | Row counts reconcile and are reported | `::test_counts_reconcile` |
| F14-S3 | Refuses to write into a non-empty version 2 database | F14-S2 | A non-empty target is refused | `::test_refuses_non_empty_target` |
| F14-S4 | Dry run reporting what would be imported | F14-S2 | A dry run writes nothing | `::test_dry_run_writes_nothing` |
| F14-S5 | Opt-in only, never triggered automatically, and never reads a path it was not given | F14-S1 | No automatic discovery of any database | `::test_no_automatic_discovery` |

## F15 Diagnostics and support bundle

| ID | Story | Depends on | Acceptance | Tests |
|---|---|---|---|---|
| F15-S1 | Diagnostics read: shell, address, version, last sync, recent errors | F10-S1 | Every field is populated from a real source | `tests/unit/api/test_diagnostics.py::test_fields` |
| F15-S2 | Storage breakdown, recursive, per component, with reclaimable space | F10-S14 | Figures match a fixture tree | `::test_breakdown_matches_fixture` |
| F15-S3 | Support bundle with every secret redacted | F10-S8 | No secret appears in the bundle | `::test_bundle_redacted` |
| F15-S4 | Logging with a configurable level, no secret ever logged | F1-S8 | A secret passed through the engine never reaches a log | `tests/unit/test_logging.py::test_no_secret_in_logs` |

---

## Counts

| | |
|---|---|
| Features | 15 |
| Stories | 136 |
| Security requirements from SPEC section 12, each covered by at least one story | 9 |
| Stories whose acceptance needs a real device or a clean machine, and therefore sit outside the gate | F6-S5, F6-S6, F13-S1, F13-S2, F13-S6; each is marked for manual verification, and [TESTING.md](TESTING.md) section 8 states what the gate does not prove |
