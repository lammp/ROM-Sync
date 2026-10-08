# ROM-Sync 2: test module

Normative. Every statement is a requirement.

[BACKLOG.md](BACKLOG.md) names, for every one of the 136 stories, the test
functions that close it. This document says where those functions live, what
they are allowed to touch, what they run against, and what single command
decides whether the work is finished.

## 1. The gate

There is one entry point:

```
python tools/verify.py
```

| Requirement |
|---|
| No other command is a gate. No story is closed by a passing subset. |
| The stages run in the order below. The gate stops at the first non-zero stage and exits with that stage's number, so a failure is identifiable from the exit code alone. |
| Every stage is also runnable alone, for a human, by `python tools/verify.py --stage <name>`. That is a convenience, never the gate. |
| The gate takes no arguments that change what it checks. There is no `--skip`, no `--fast` and no environment variable that relaxes a stage. |
| The gate is pure: it writes only inside a temporary directory it creates and removes, plus `.coverage` and `reports/`. It never writes into the source tree, the user's data directory, or any store. |

| # | Stage | What it does | Fails when |
|---|---|---|---|
| 1 | `format` | `ruff format --check`, `prettier --check` over `ui/` | any file would be reformatted |
| 2 | `lint` | `ruff check`, `eslint` | any diagnostic |
| 3 | `types` | `mypy --strict` over `engine/`, `api/`, `desktop/`, `tools/`; `tsc --noEmit` over `ui/` | any error |
| 4 | `structure` | the structural tests: layering, layout, no-kind-branching, SQL safety, no SQL in the API tree, determinism harness self-test | any failure |
| 5 | `unit` | `pytest tests/unit` | any failure |
| 6 | `contract` | `pytest tests/contract` against `dest_fake` and `dest_volume` | any failure |
| 7 | `golden` | `pytest tests/golden` | any mismatch against a committed golden |
| 8 | `e2e_fake` | `pytest tests/e2e_fake` | any failure |
| 9 | `ui` | `vitest run` over `ui/tests` | any failure |
| 10 | `coverage` | the coverage gates in section 7 | any gate below its floor |
| 11 | `openapi` | `tools/openapi_check.py`: regenerate the document and diff it against the committed copy | any undeclared drift |
| 12 | `publication` | `_tools/repo-lint.py --strict` and the secret scan over the working tree | any finding |

Stage 12 is in the gate on purpose. The publication lint is the check that
keeps a private path, a machine name or a credential out of a public
repository, and a check that runs only when someone remembers it is not a
check. Requirement S9 of [SPEC.md](SPEC.md) is satisfied here and nowhere else.

### Timing

| Requirement |
|---|
| Stages 1 to 7 complete in under 60 seconds on the development machine. |
| The whole gate completes in under 5 minutes. |
| A test that cannot meet its stage's share of that budget is wrong, not slow. There is no "slow" marker and no deselection by duration. |

The reason is history, not taste. Version 1's pre-commit hook once took minutes
on a seventy-file commit, and the first thing anyone wanted was a way around
it. A gate nobody waits for is a gate nobody runs.

## 2. Test tree

```
tests/
  conftest.py              the determinism harness, applied to every test
  helpers/
    fakes.py               the fakes listed in section 4
    builders.py            model builders, so a test states only what it means
    trees.py               fixture store and device tree construction
  unit/                    one module under test, everything else a fake
    domain/ ports/ config/ app/ jobs/ api/ desktop/ installer/ tools/
    adapters/
      db/ store/ dest_adb/ dest_mtp/ metadata/
    test_layering.py test_layout.py test_no_kind_branching.py
    test_determinism.py test_sink.py test_verify_gate.py
    test_ci_config.py test_logging.py
  contract/
    test_dest_contract.py  parameterised over every destination adapter
  golden/
    test_title_identity.py test_twins.py test_plan.py test_matcher.py
    data/                  the committed golden files
  e2e_fake/
    test_first_run.py      the whole engine, every adapter faked
  fixtures/
    titles.tsv             the title corpus
    scoring.tsv            the matcher corpus
    escapes.txt            the path escape corpus
    store_tree.yaml        the fixture store
    device_tree.yaml       the fixture device inventory
    igdb/                  recorded metadata responses
    v1.db                  a version 1 database, synthetic
ui/
  tests/                   vitest, jsdom, the generated client mocked
```

| Requirement |
|---|
| A test file's path mirrors the module it covers. `tests/unit/adapters/db/test_repos.py` covers `engine/romsync/adapters/db_sqlite/repos.py`. |
| A test in `tests/unit` imports exactly one production module tree: the one under test. Anything else it needs comes from `tests/helpers`. |
| No test imports another test. Shared setup is a fixture or a helper. |
| Test names state the behaviour, not the mechanism: `test_unreadable_system_does_not_prune`, not `test_prune_2`. |
| The names in [BACKLOG.md](BACKLOG.md) are the contract. A story's named test may gain siblings; it may not be renamed without amending that file in the same pull request. |

## 3. Determinism

`tests/conftest.py` applies all of the following to every test, with no opt-out
marker. A test that needs an exception is a test in the wrong tree.

| Control | Requirement |
|---|---|
| Clock | `ClockPort` is a frozen clock at a fixed instant. Production code never calls `time`, `datetime.now` or `perf_counter` directly; a test asserts this by scanning the source tree. |
| Identifiers | `IdPort` is a counting generator. No `uuid4` in production code outside the adapter that wraps it. |
| Randomness | Seeded. The seed is printed on failure. Any unseeded use fails the determinism self-test. |
| Network | A socket guard replaces `socket.socket` and raises `NetworkInTest` naming the test. There is no allow-list. Every HTTP interaction in the suite goes through a fake or a recorded response. |
| Subprocess | A guard replaces `subprocess.Popen` and `subprocess.run` and raises unless the test declares the executable it expects. ADB and MTP command construction is tested by asserting on the argument vector, never by running a binary. |
| Filesystem | `tmp_path` only. A guard fails any test that writes outside it, or that reads an absolute path not under it, with the two documented exceptions: the repository's own `tests/fixtures` tree, read-only, and `sys.prefix`. |
| Data directory | Set to a temp directory per test. A test that can see the developer's real data directory is a test that will pass on one machine. |
| Environment | A fixed, minimal environment. The Windows home, application-data and temporary-directory variables are all redirected inside `tmp_path`, so no test can resolve a real user path. |
| Ordering | `pytest-randomly` with a fixed seed in the gate, and a nightly run with a random seed. Order dependence is a defect, found by the nightly and fixed, not worked around by ordering. |
| Parallelism | The gate runs `pytest -p xdist -n auto`. A test that fails only under `-n auto` is sharing state and is a defect. |
| Sleeping | No `sleep` in any test. Waiting is modelled by the fake clock and by explicit event objects. A test containing a sleep fails the determinism self-test. |
| Concurrency | Tests that assert serialisation, for instance two migration runners, use barriers and events, never timing. |

`tests/unit/test_determinism.py` tests the harness itself: a planted socket
open, a planted sleep, a planted write outside `tmp_path` and a planted
`datetime.now` each fail with a named error. A harness nobody tests is a
harness that quietly stops working.

## 4. Fakes

A fake is a real implementation of a port with an in-memory or in-tree
substrate. A mock that merely records calls is used only where the assertion
genuinely is "it called this": the command vectors, the progress events, the
notifications.

| Fake | Substrate | Notes |
|---|---|---|
| `dest_fake` | an in-memory tree | ships in `engine/romsync/adapters/dest_fake/`, not in `tests/`, because it is also the destination the e2e suite and the first-run acceptance run against. It is the reference implementation of the contract in SPEC section 4. |
| `dest_fake` fault injection | per-method | can be told to fail a named op, to fail after N bytes, to report a short size, to go away mid-run, to return a wrong digest, and to be slow by fake-clock ticks. Every row of the contract suite's failure half is driven from here. |
| `metadata_fake` | recorded responses under `tests/fixtures/igdb/` | returns the recorded body for a recorded query and raises `NotRecorded` otherwise, so a new query cannot silently reach the network. Recordings are redacted of any token at capture time, and the capture tool is in `tools/`, not in the gate. |
| `store_fake` | a real tree under `tmp_path`, built from `store_tree.yaml` | the store adapter is tested against real files, because its defects are filesystem defects. |
| `clock_fake`, `id_fake` | counters | section 3. |
| `sink_spy` | a list of events | asserts shape, order and totals. |
| `shell_fake` | a recorder | asserts the platform adapter is called, never that a dialog appeared. |
| `repo_fake` | in-memory dicts | used by `app` tests, so a use case is tested without SQLite. `tests/unit/adapters/db` is where SQLite itself is tested. |

| Requirement |
|---|
| Every fake that implements a port is exercised by the same contract suite as the real adapters, where a contract exists. A fake that is more permissive than the real thing is worse than no fake. |
| `metadata_fake` and the real client share their response parsing. Only the transport is swapped. A recorded response that the real parser would reject must also fail in the fake. |

## 5. Fixtures and corpora

Section D6 of [SCOPE.md](SCOPE.md) removes the owner's library as an oracle.
These corpora replace it, and they are the weakest part of the plan: the
residual risk table says so plainly. They are therefore specified, not left to
whoever writes the first test.

| Corpus | File | Content | Minimum |
|---|---|---|---|
| Titles | `fixtures/titles.tsv` | raw title, expected strict key, expected loose key, a comment naming the property it pins | 400 rows, covering roman numerals, leetspeak, ampersands, apostrophes, region tags, revision tags, disc tags, edition words, articles, subtitle colons, and non-Latin script |
| Twins | derived from the title corpus | known cross-system pairs, and known false pairs that must not cluster | 60 pairs and 40 non-pairs, the non-pairs including sequels, remakes and same-series different-game |
| Matcher | `fixtures/scoring.tsv` | candidate title, platform, year, expected score band, expected accept or reject at the pinned thresholds | 200 rows, including the deliberate near-misses that the 0.55 threshold was chosen to exclude |
| Escapes | `fixtures/escapes.txt` | one path per line, every one of which must raise `PathEscape` | the corpus in SPEC section 3, plus a separator inside a name, a drive-qualified absolute, a UNC path, a trailing dot, a reserved device name, a symlink out of the root, an overlong name, and a mixed-separator form |
| Store tree | `fixtures/store_tree.yaml` | systems, game files, folder games, multi-disc sets, a `bios` folder, an unmanaged folder, an unreadable system file, a zero-byte file, a name at the path length limit | every branch the scanner has |
| Device tree | `fixtures/device_tree.yaml` | a matching inventory, plus an emulator state folder, a folder that is not a store system, and a partially transferred `.part` file | every branch the planner has |
| Version 1 database | `fixtures/v1.db` | synthetic, built by a script in `tools/`, with an unversioned schema | the import tool's full input surface |

| Requirement |
|---|
| Every title in every corpus is a real, published game title, which is public fact and not library data. No row is taken from, or derived from, the author's catalogue, and no corpus contains a path, a filename from a real store, or a hash of a real file. |
| A corpus row carries the property it pins. A row nobody can explain is deleted, not kept for coverage. |
| A fixture tree is built by code from a declarative file. No binary tree is committed, and no test depends on a tree that a human assembled by hand. |
| Fixture media is generated: a file of a stated size filled with a seeded pattern. No real ROM, image, BIOS, firmware or key file exists anywhere in the repository, including under `tests/`. `_tools/repo-lint.py` asserts this, and stage 12 runs it. |

## 6. The test kinds, and what each is for

### Unit

One module. Every dependency a fake. No database, no network, no subprocess, no
sleep. This is where the domain rules live, and the domain layer should reach
very high coverage cheaply because it imports nothing outside the standard
library. That is the point of D1.

### Structural

Tests that assert properties of the source tree rather than of a behaviour, and
the reason several of version 1's defects could exist at all:

| Test | Asserts |
|---|---|
| `test_layering.py` | the import graph obeys SPEC section 2, and a planted illegal import is detected |
| `test_layout.py` | every declared package exists and imports |
| `test_no_kind_branching.py` | no comparison against a transport name in `app` or `api` |
| `test_sql_safety.py` | every statement binds its values; a planted f-string statement fails |
| `test_no_sql_in_api.py` | no SQL text in the API tree |
| `test_determinism.py` | the harness, per section 3 |
| `test_verify_gate.py` | each stage of the gate can fail the gate |
| `test_ci_config.py` | the workflow calls the gate and nothing else |
| `test_logging.py` | a secret passed through the engine reaches no log |
| path-type audit | no function that deletes, writes or reads a file accepts `str` where SPEC section 3 requires `ContainedPath`, asserted from signatures |
| clock audit | no direct `datetime.now`, `time.time` or `perf_counter` outside the clock adapter |

Each of these is a defect class made unrepresentable. A structural test is
worth more than the unit tests it makes unnecessary, because it holds for code
nobody has written yet.

### Contract

`tests/contract/test_dest_contract.py` is one suite, parameterised over the
destination adapters. It is the whole of D12.

| Requirement |
|---|
| The suite is written once, against the ports, and knows no adapter name. Parameterisation supplies a factory and the set of roles that factory declares. |
| A role an adapter does not declare is skipped, and the skip is reported in the gate's summary. A silently skipped role is how transports drift apart. |
| Every row of SPEC section 4's C1 to C10 has at least one test function, named after the requirement: `test_c3_put_file_returns_destination_size`. |
| The default parameter set is `dest_fake` and `dest_volume` over `tmp_path`, so the gate is deterministic and needs no hardware. |
| `dest_adb` and `dest_mtp` are additional parameters, enabled only by an explicit opt-in flag plus a connected device. They are never part of the gate. |
| An adapter that does not pass the suite is not registered. Registration asserts it, at composition time, not by comment. |

The failure half of the suite matters more than the success half: an
interrupted run, a short write, a wrong digest, a vanished destination, a
cancel between items, a cancel attempted during a copy. Those are the paths
that corrupted data in version 1, and `dest_fake`'s fault injection is how they
become ordinary tests instead of stories.

### Golden

Behaviour pinned against a committed expected output: the title keys, the twin
clusters, the plan over the fixture trees, the matcher's scores.

| Requirement |
|---|
| A golden file is text, line-oriented, sorted, and diffable. No pickle, no JSON blob on one line. |
| A golden is regenerated only by `python tools/verify.py --regenerate-goldens`, which is not a gate stage. |
| A pull request that changes a golden file must say, in its description, which behaviour changed and why. A golden diff with no stated reason is rejected in review. This is the only review rule in this document, and it exists because a golden that is regenerated whenever it fails tests nothing at all. |
| The matcher's thresholds are pinned here. SCOPE's non-goals forbid re-tuning them, so a change to a matcher golden is out of scope by default. |

### End to end, faked

`tests/e2e_fake/` runs the composed engine with every adapter faked and the
HTTP layer in process: first run on an empty data directory, choose a store
root, scan, select, sync to `dest_fake`, verify, remove, prune, restart with a
job left running and observe the reconciliation. It is the test that the parts
fit together, and the only place the composition root is exercised.

It is not a test of the real transports, the real device, the real installer or
the real browser. Those are section 8.

### Interface

`ui/tests`, vitest over jsdom, the generated client mocked at the fetch
boundary.

| Requirement |
|---|
| The mocked fetch layer validates request and response bodies against the committed OpenAPI document. A UI test cannot pass against a shape the engine does not serve. |
| Behaviour parity with version 1 is pinned by fixtures captured from the current implementation's output: the search grammar's parse results, the facet counts and ordering, and the twin clustering. These are captured once, from code, with no library data in them, and then treated as goldens. |
| The accessibility tests are assertions, not an audit tool's score: keyboard traversal reaches every interactive element, a dialog traps and restores focus, every input has a programmatically associated label, the live region receives every toast, and every state has a channel other than colour. |
| `contrast.test.ts` computes the contrast ratio over every foreground and background pair in the token set and fails any pair below AA. It reads the tokens, so a new token is covered the day it is added. |
| No UI test asserts on a pixel, a screenshot or a class name. It asserts on roles, accessible names and behaviour. |

## 7. Coverage gates

Coverage is a floor, not a target. It is here to catch a module nobody tested,
not to be maximised.

| Scope | Floor | Rationale |
|---|---|---|
| `domain/` | 100 percent of statements and branches | pure, stdlib only, no excuse exists |
| `app/` | 95 percent | use cases over fakes |
| `jobs/`, `config/` | 95 percent | state machines and validation |
| `adapters/db_sqlite/` | 90 percent | real SQLite in a temp file |
| `adapters/store_fs/` | 90 percent | real trees under `tmp_path` |
| `api/` | 90 percent | in-process client |
| other adapters | 70 percent | the device-facing remainder is section 8 |
| `ui/` | 80 percent of statements | the parity fixtures carry the weight |
| whole repository | no file at 0 percent | a file nobody imports in a test is either dead or untested, and both need a decision |

| Requirement |
|---|
| Branch coverage, not statement coverage, wherever a floor is above 90 percent. |
| `# pragma: no cover` requires a comment stating why, and the gate fails on a bare pragma. |
| A floor is raised when it is comfortably exceeded. It is never lowered to make a pull request pass; the test is written instead. |

## 8. What is not tested automatically

Stating this precisely is part of the specification. An unlisted gap becomes a
claim that the gate proves more than it does.

| Not covered | Why | How it is verified |
|---|---|---|
| Real ADB and MTP behaviour | the contract suite proves the adapters agree with each other and with the fake, not that any of them agrees with a handheld | the opt-in contract run on a connected device, per story, recorded in the pull request |
| Arrival polling sized by file size | the behaviour exists because MTP reports a static size for minutes on a large file, which no fake reproduces honestly | one manual transfer of a file over 4 GB per release |
| Killing a transfer worker mid-copy | the rule is that it is never done; there is nothing to assert | code review of the cancel path, plus the contract test that cancel is honoured only between items |
| The frozen artefact on a machine with no Python | the build is the thing under test | a clean virtual machine per release, running the first-run acceptance by hand |
| The embedded browser runtime check | it depends on a system component | the same clean virtual machine, once with the runtime absent |
| Recycle Bin semantics for store removals | a shell API, not a filesystem call | manual, once per release, confirming the item is restorable |
| The matcher against a real library | D6 removes the oracle | the scoring corpus, and an acknowledged residual risk |
| Visual appearance | no screenshot tests | human review |

A release checklist carries the manual rows. The checklist is a file in the
repository, versioned, and a release that skips a row says which row and why.

## 9. Continuous integration

| Requirement |
|---|
| One workflow, one job, one step that matters: `python tools/verify.py` on a Windows runner. Windows because the application is Windows-only and because the path rules in SPEC section 3 are Windows rules. |
| The workflow adds nothing the local gate does not do. If CI can fail where a clean local run passed, the gate is wrong, and that is the defect to fix. |
| The gate is a required check on the `v2` branch. Merging on a red gate is not available, not merely discouraged. |
| A second, scheduled workflow runs the gate nightly with a random test order seed and a fresh dependency resolution, and opens an issue on failure. Order dependence and a dependency that moved under us are both found here rather than by a developer. |
| A tag builds the release, computes checksums, and attaches the artefacts. The release workflow runs the gate first and refuses to publish on a red gate. |
| No secret is available to the gate. A workflow that needs a credential to pass is a workflow testing the network. |

## 10. The autonomous run

The gate exists so that a story can be implemented without supervision and the
result can be trusted. This is how that run is bounded.

### Per story

1. Read the story row in [BACKLOG.md](BACKLOG.md): identifier, dependencies,
   acceptance, named tests.
2. Refuse to start if any dependency story is not closed. The dependency graph
   is not advisory.
3. Create a branch named for the story identifier.
4. Write the named tests first, and run the gate. The new tests must fail, and
   they must fail for the stated reason, not on an import error. A test that
   passes before the implementation is a test of nothing, and the run stops
   there.
5. Implement the smallest change that makes them pass.
6. Run the full gate. Not the new tests, the gate.
7. Open one pull request, titled with the story identifier, describing what
   changed, naming any golden diff and its reason, and listing any manual
   verification the story's row requires.
8. Stop. A green gate closes the story's code; a human closes the story.

### Stop conditions

The run halts and reports, rather than continuing or working around, when any
of these holds:

| # | Condition |
|---|---|
| 1 | The gate is red after the implementation, twice, for the same stage. |
| 2 | The gate was already red before any change was made. The tree is not a base to build on. |
| 3 | A named test passed before the implementation existed. |
| 4 | Closing the story would need a change to [SPEC.md](SPEC.md). The specification is amended by a human, in its own pull request, and only then is the story reattempted. |
| 5 | Closing the story would need a coverage floor lowered, a pragma added without a reason, a determinism control disabled, a stage skipped, or `--no-verify` used. |
| 6 | Closing the story would need a golden regenerated for a reason the run cannot state in one sentence. |
| 7 | The story's acceptance needs a real device, or any other row of section 8. |
| 8 | Two stories would have to be implemented together. Either the dependency graph is wrong, which is a specification change, or the split is wrong, which is a backlog change. Both are human decisions. |
| 9 | The change would touch a file outside the story's stated scope, other than the test files it names. |
| 10 | A security requirement from SPEC section 12 would be weakened, in any degree, for any reason. |

Conditions 4, 8 and 10 are the ones that matter. An autonomous run that is
allowed to amend the specification to make a story pass is not building this
application; it is building whichever application is easiest to finish.

### What a story may not do

| Requirement |
|---|
| Never relax the gate to land work. The gate's definition changes only in a pull request whose stated purpose is to change the gate. |
| Never commit a fixture derived from real library, device or credential data. |
| Never write to any path outside the repository and `tmp_path`. |
| Never hard-delete. Removals in the development tree follow the same rule as the application's: they move to the Recycle Bin. |
| Never push or open a pull request against `main`. Version 2 lives on `v2` until it passes its gate, per D16. |

## 11. Order of work

The test module is not a later phase. F1 is the gate, the determinism harness,
the error taxonomy, the sink protocols, the config registry and the CI
workflow, and every other feature depends on it. Nothing in F2 to F15 can be
closed before F1 is closed, because the thing that closes a story is the gate
that F1 builds.

The first pull request of the rewrite therefore contains no application code at
all. It contains a layout, a gate that runs and reports, a harness that fails a
planted violation of each determinism control, and a workflow that calls the
gate. If that pull request is not worth merging on its own, the rest will not
hold.
