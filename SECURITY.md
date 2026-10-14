# Security and privacy

This repository is the public half of a workspace whose private half is a
personal game library. The two live in the same directory tree. Everything
below exists so that boundary holds under ordinary use, under a careless
`git add -A`, and under a future edit made by someone who has not read this
file.

## 1. What must never be committed

| Class | Examples in this tree | Why |
|---|---|---|
| Credentials | The IGDB / Twitch `client_id` and `client_secret` | Stored inside the application's database (`romsync.db`), not in source. Version 2 keeps it in `%LOCALAPPDATA%\ROM-Sync\data`, outside the repository; version 1 kept it in `ROM-Sync/data/`. A committed database is a committed credential. |
| Console keys | `prod.keys`, `title.keys` | Distributing them is unlawful in most jurisdictions and they identify the console they came from. |
| Firmware and BIOS | Switch firmware, PlayStation and DS BIOS sets | Copyrighted binaries. |
| Game data | Anything under `ROMs/` | Copyrighted binaries, and several terabytes of them. |
| Library manifests | `*.tsv`, `*.csv`, `romsync.db` | These enumerate the library title by title. They disclose its contents as surely as the files would. |
| Agent memory | `memory/`, `MEMORY.md`, `.memory-log/` | Accumulated facts about the owner: preferences, machine layout, working habits. |
| Embedded browser profile | `webview/` in the data folder | A full Chromium profile including cookies, session state and client certificates. Any site signed into through the application has a live session token in there. |
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

## 5. The application's own security

ROM-Sync 2 runs a local web server for its own window. It is built so that
nothing but that window can drive it.

| Control | What it stops |
|---|---|
| The server binds to `127.0.0.1` or `::1` only; nothing reachable from the network can be configured | Another machine reaching it. |
| The `Host` header must be the loopback address | DNS rebinding: a web page using a hostname that resolves to your own machine. |
| Every change, and the folder listing, needs the page's origin and a token issued to the page for its session | Another site, or another program's page, driving the engine. |
| Every response, refusals included, forbids framing, MIME sniffing and referrers | Clickjacking, and the address leaking through links. |
| Path settings refuse network shares (`\\server\share`) and device paths (`\\?\`, `\\.\`) | Reading one would send your Windows sign-in to whoever answers. |
| A secret is never returned by the API; logs, diagnostics and the support bundle are searched for every set secret and have it removed | A secret reaching a bug report. |
| A sync can remove games only after the removal count is confirmed; a device's first sync always asks; folders that are not library systems, `bios` and emulator state are never removed | Losing a device's saves or unrelated files. |
| Nothing is written through a link or junction on a drive, and a drive overlapping the library is never offered as a destination | A sync writing over the library or outside the device's ROMs folder. |
| The release token reaches only the job that publishes, the build keeps no credentials in its checkout, and a tag that is not a plain version stops the release | A compromised build step publishing anything. |

Open items are listed in [docs/KNOWN-LIMITATIONS.md](docs/KNOWN-LIMITATIONS.md)
section 8.

## 6. The repository's own controls

| Control | Holds |
|---|---|
| `main` | Changes only through a pull request with one approving review from the code owner (`.github/CODEOWNERS`) and the `gate` check passing; stale approvals are dismissed by a new push; conversations must be resolved; never force-pushed or deleted. |
| `v2` | Never force-pushed or deleted. |
| Release tags (`v*`) | Created only by the owner; never moved or deleted. |
| Releases | Immutable once published: the files and the tag cannot be changed. |
| Pull requests from forks | Their workflows run only after the owner approves them. |
| GitHub Actions | Only GitHub's own actions may run; the default token is read-only and cannot approve pull requests. |
| Scanning | Secret scanning with push protection, Dependabot alerts and security updates, weekly Dependabot update pull requests (`.github/dependabot.yml`), and CodeQL code scanning. |

The owner may bypass the branch and tag rules, and is expected to follow them
regardless.

## 7. Reporting

This is a personal project with no security support commitment. Report a
vulnerability privately through the repository's **Security** tab, **Report a
vulnerability**. Do not open a public issue for it, and do not include an
exposed value in any report.
