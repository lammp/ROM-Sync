# Contributing to ROM-Sync

The repository is public and read by anyone; changes are by invitation.

1. **Open an issue first.** Say what you want to change and why. If it fits,
   you will be asked to send a pull request.
2. **Send the pull request from your own fork.** `main` changes only through a
   pull request that the owner has reviewed and approved, with the `gate`
   check passing. A workflow from a fork runs only once the owner approves it.
3. **Run the gate before you push.** `python tools/verify.py` runs the same
   twelve stages the `gate` check runs. The README's *Build from source* sets
   it up.
4. **Keep the publication rules.** `.gitignore` excludes everything by default
   and names what may be published. Never use `git add -f` or
   `git commit --no-verify`; [SECURITY.md](../SECURITY.md) says why and how to
   check with `python _tools/repo-lint.py --strict`.
5. **Follow the specifications.** Behaviour is specified in
   [docs/rewrite/SPEC.md](../docs/rewrite/SPEC.md); a change of behaviour is a
   story in [docs/rewrite/BACKLOG.md](../docs/rewrite/BACKLOG.md) with its
   tests.

Releases are immutable: a published release, its files and its tag cannot be
changed or deleted. A correction is a new release.

Security problems go through the repository's private vulnerability
reporting (the **Security** tab, **Report a vulnerability**), never a public
issue.
