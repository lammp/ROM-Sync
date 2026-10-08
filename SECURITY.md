# Security and privacy

This repository is the public half of a workspace whose private half is a
personal game library. The two live in the same directory tree. Everything
below exists so that boundary holds under ordinary use, under a careless
`git add -A`, and under a future edit made by someone who has not read this
file.

## 1. What must never be committed

| Class | Examples in this tree | Why |
|---|---|---|
| Credentials | The IGDB / Twitch `client_id` and `client_secret` | Stored inside `ROM-Sync/data/romsync.db`, not in source. A committed database is a committed credential. |
| Console keys | `prod.keys`, `title.keys` | Distributing them is unlawful in most jurisdictions and they identify the console they came from. |
| Firmware and BIOS | Switch firmware, PlayStation and DS BIOS sets | Copyrighted binaries. |
| Game data | Anything under `ROMs/` | Copyrighted binaries, and several terabytes of them. |
| Library manifests | `*.tsv`, `*.csv`, `romsync.db` | These enumerate the library title by title. They disclose its contents as surely as the files would. |
| Agent memory | `memory/`, `MEMORY.md`, `.memory-log/` | Accumulated facts about the owner: preferences, machine layout, working habits. |
| Embedded browser profile | `ROM-Sync/data/webview/` | A full Chromium profile including cookies, session state and client certificates. Any site signed into through the application has a live session token in there. |
| Machine-local identifiers | Windows account name, machine name, `C:\Users\...` paths | Personal identifiers with no business in a public repository. |

## 2. How the boundary is held

Three independent layers. Each is expected to be sufficient on its own; none
is trusted to be.

**Deny by default.** `.gitignore` excludes the entire working tree on its
first rule and then names what may return. A file that nobody has explicitly
allowed cannot be staged, so a new sensitive file added to the tree tomorrow
is excluded on arrival rather than waiting for a rule to catch it.

**Belt and braces.** The final block of `.gitignore` re-excludes sensitive
patterns after the allow-list, so a careless future edit to the allow-list
does not open a path. Those patterns win because git applies the last
matching rule.

**A pre-commit gate.** `.githooks/pre-commit` scans staged content, not just
filenames, and refuses the commit on a match. It is the only layer that
catches a secret pasted into an allowed source file. Enable it once per
clone:

```
git config core.hooksPath .githooks
```

A hook is not a security control against a determined author, since
`--no-verify` bypasses it. It is a control against a distracted one, which is
the realistic failure mode.

## 3. Verifying rather than trusting

Run the audit before any first push, and after any change to `.gitignore`:

```
python _tools/repo-lint.py --strict
```

It reports what `git add -A` would actually stage, checks every staged path
against the sensitive classes above, scans staged file content for credential
and identifier patterns, and fails on anything unresolved. It reads its list
of machine-local identifiers from `_tools/repo-lint.local.txt`, which is
itself excluded from the repository; copy
`_tools/repo-lint.local.example.txt` to that name and fill it in.

Two manual checks are worth doing once by eye, because a tool that agrees
with itself proves nothing:

```
git status --porcelain --untracked-files=all
git check-ignore -v ROMs/psx/some-game.chd _firmware/ProdKeys.NET-v22.5.0/prod.keys ROM-Sync/data/romsync.db
```

The first should list only files you intend. The second should name the rule
that excluded each path.

## 4. If something sensitive is committed

Assume disclosure from the moment the commit exists, whether or not it was
pushed and whether or not the repository was public. Deleting the file in a
later commit does not remove it from history.

1. **Rotate first, clean second.** For the IGDB credential, issue a new
   client secret in the Twitch developer console and update the application
   configuration. Rotation is what actually ends the exposure; history
   rewriting only reduces how long it stays discoverable.
2. Rewrite history with `git filter-repo`, or delete the repository and start
   a fresh one if it has no history worth keeping. The second option is
   usually faster and always more complete.
3. If the repository was public and pushed, treat any credential in it as
   compromised regardless of how briefly it was up. Automated scrapers index
   new public repositories within minutes.

## 5. Reporting

This is a personal project with no security support commitment. If you find
an exposure in it, open an issue describing the class of problem without
including the exposed value.
