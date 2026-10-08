# Legislation — _torrents/ (example)

> The working `CLAUDE.md` for this directory is excluded from the repository.
> It describes how this machine acquires files, which is not something the
> repository discloses. This file ships in its place: it carries the laws,
> which are the reusable part, and none of the configuration.

The download intake. Two subfolders: `_incomplete` for transfers still in
progress, owned by the download client, and `_complete` for finished ones
awaiting sorting into the library.

## Laws for this directory

1. **`_incomplete/` is off-limits.** Never read, moved, deleted or counted. It
   holds partial files the download client has open, and touching one corrupts
   the transfer (Constitution law 2). This separation is the entire reason
   `_complete` exists: only finished, released files are worked.
2. **A file is a keeper only once it is complete and passes the library's
   filtering policy.** A partial-file suffix means still downloading; it is
   never a source.
3. **Sorting a completed set into the library is a round.** The copy in and
   any removal of the source both go through the `save` skill, so an intake is
   reversible like any other library change (Constitution law 4).
4. **Nothing in this directory is ever published (Constitution law 8).**
   Neither its contents, nor its configuration, nor the working Legislation
   that describes them.
