# Legislation — _firmware/ (example)

> The working `CLAUDE.md` for this directory is excluded from the repository.
> It inventories what is actually held here, which is a disclosure the
> repository does not make. This file ships in its place: it carries the laws,
> which are the reusable part, and none of the contents.

System files that are not games and are not the live `ROMs/bios` set: console
firmware, encryption keys, spare BIOS collections, and the front-end folder
skeleton. This is a store, not something an emulator reads directly. The BIOS
a device actually uses live under `ROMs/bios`.

## Laws for this directory

1. **Keys are secret (Constitution law 1).** Key files and their contents
   never leave this directory in any shared artefact: not a `CLAUDE.md`, not a
   memory fact, not a commit, not a message. Their filenames are privacy
   markers in the memory gate and in the publication lint.
2. **Nothing in this directory is ever published (Constitution law 8).** The
   repository ships the directory's existence and this file, and nothing else.
3. **The library's live system files are in `ROMs/bios`, not here.** Before
   adding one to `ROMs/bios`, check it is not already installed; the
   collections here are a spare source, most of which the target device never
   uses.
4. **Files kept "for later" carry a label and a note.** A bare dump of
   filenames is not self-explanatory. A folder here is named for what it
   holds, and where the names are cryptic it carries a README decoding them.
