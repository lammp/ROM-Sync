# Legislation — ROMs/

The ES-DE ROM library itself: one folder per system, holding the games in the format that system's emulator on the Thor accepts. This is the authoritative library; everything else in `D:\Games` exists to build, check or manage it. The folder skeleton comes from `_firmware\ROMs.zip` (re-extract it to reset the tree). `bios/` holds every BIOS, firmware and system file. `.nomedia` and `systeminfo.txt` / `systems.txt` are ES-DE's, not games.

## Formats per system

| System(s) | Format | Notes |
|---|---|---|
| psx, ps2, psp | `.chd` | multi-disc PSX uses an `.m3u` playlist beside the discs |
| gc, wii | `.rvz` | RVZ magic bytes `82 86 90 01` at offset 0 |
| n3ds | decrypted `.3ds` | Azahar needs decrypted; NCSD `NCSD` at 0x100, NoCrypto flag at 0x418F bit 2 set |
| switch | one merged `.xci`/`.nsp` per game, flat | base+update+DLC merged with SAK; Eden scans the flat folder |
| fbneo | `.zip` (arcade set, MAME short names) | keep zipped |
| snes and most retro | `.zip` where the emulator accepts an archive | keep compressed unless the target needs it extracted |

General rule: keep ROMs compressed where the target system accepts the archive; extract only where it does not, and check per system rather than assuming.

## Filtering policy

- **English only.** Any release not in English is removed, whatever its region.
- **Region rank:** Australia > USA > Europe > other. Where the same game exists in several regions, keep the highest.
- **One copy only.** No source tree kept beside a game once its keeper is in place.
- **No** demos, betas, samples, prototypes, kiosk/aging/program carts, homebrew, mods, bad dumps (`[b]`). Where only a USA prototype and a finished non-USA release exist, keep the finished release.
- **Unlicensed:** remove cheat devices, hardware utilities, bootlegs, clones, pirate conversions; keep Western unlicensed commercial releases (Tengen, Codemasters/Camerica, Color Dreams/Wisdom Tree, AVE, HES, Active Enterprises).
- **Cross-system:** generally prefer the same game on the newer system; keep the original where it is the better version; where no real difference, keep the original platform. Keep one title per name — but a shared name is not a shared game: confirm it is the same game (a port) before treating two systems' copies as one title. Penny Racers on N64 (Choro Q 64) and Penny Racers on GBA (Gadget Racers) are different games; round 15 dropped the N64 one as a duplicate of the GBA one (restored in round 26).
- **Named keeps** (explicit exceptions): the GTA V homebrew Switch port with its IPS mod, and `nds\_DS_MSHL.NDS`.
- **Keep** coprocessor firmware and enhancement-chip images.

## Laws for this directory

1. **Verify a file's true type before trusting its extension.** Justify a format call with two or three facts read from the file itself (header magic, size against source, structure), never the extension alone. A mislabelled or re-wrapped file passes an extension check and fails the emulator.
2. **A removal or move runs through the `save` skill.** Never delete or move a game here directly; the save point is what makes the filtering reversible (Constitution law 4).
3. **`bios/` is system files, not games.** It is not filtered by the game policy and is never counted as library titles.
4. **A drop must leave the game somewhere.** Before recycling a `duplicate` or `no region` drop, confirm its keeper is still in the set or the store at that moment. Keepers named in one round that a later round removes (the `(Auto Demo)` and `(Possible Proto)` copies rounds 07/12 took out after round 03 had kept them over the retail dumps) orphaned Moonwalker and Tiger-Heli. `intake-plan.py` flags these as ORPHAN-DROP; a tag word counts anywhere inside a parenthesis, and a multi-game cart's `(En+En,Es)` language tag is English only if every game on it lists En.

## Publication

<!-- publication-law -->
5. **Nothing in this directory is ever published (Constitution law 8).** This
   file ships because it describes formats and policy; the library it governs
   does not, and neither does any manifest that enumerates it. A `.tsv` or
   `.csv` listing titles discloses the library as surely as the files would.
