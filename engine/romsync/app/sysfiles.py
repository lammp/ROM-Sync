"""System files: what each emulator needs, what the store has, what is staged on
a device, and what the emulator can actually read (F8).

The engine stages; it never generates a file and never writes into an
emulator's own folders (F8-S7). Everything it places goes to one folder per
system, from the configured template (F8-S3), and the person installs from
there with each emulator's own menus.

Two statuses per file, reported as states for the interface to word (F8-S6):

    staged     in the staging folder: current, different, present (nothing in
               the store to compare with), absent, or unknown (not surveyed)
    installed  where the emulator reads: installed, different, missing,
               unseen (its app folder is not there), not applicable (the
               device has no app folders at all), or unknown

Readiness comes from the installed status only; staging never makes a system
ready. Nothing here asks which transport a device uses: what a device exposes
is learned from the survey (F8-S3).
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from romsync.app.devices import require
from romsync.app.sysfiles_registry import APP_FOLDERS, Requirement, SystemEntry, load
from romsync.domain.errors import ConfigOutOfRange, DestinationItemMissing, PathEscape
from romsync.domain.paths import ContainedPath, LocalRoot, check_name
from romsync.ports.clock import ClockPort
from romsync.ports.dest import Dest, DestFiles, DestInventory, DestRoots, DestVerify, Listing
from romsync.ports.repo import SurveyEntry, SysfileRepo
from romsync.ports.sysfiles import SysfileStore

TEMPLATE_KEY: Final = "device.staging_template"
HASH_LIMIT_KEY: Final = "sysfiles.hash_limit"


class Staged(StrEnum):
    UNKNOWN = "unknown"
    ABSENT = "absent"
    CURRENT = "current"
    DIFFERENT = "different"
    PRESENT = "present"


class Installed(StrEnum):
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"
    UNSEEN = "unseen"
    MISSING = "missing"
    DIFFERENT = "different"
    INSTALLED = "installed"


class Readiness(StrEnum):
    UNKNOWN = "unknown"
    NONE = "none"
    UNSEEN = "unseen"
    MISSING = "missing"
    OPTIONAL = "optional"
    READY = "ready"


class Staging(StrEnum):
    UNKNOWN = "unknown"
    NOTHING_TO_STAGE = "nothing_to_stage"
    ABSENT = "absent"
    OUTDATED = "outdated"
    CURRENT = "current"


# --- the staging folder (F8-S3) ------------------------------------------------------


def staging_folder(template: str, roots: DestRoots, system: str) -> ContainedPath:
    """Where `system`'s files are staged. `{system}` is required; `{roms}` is the
    device's ROMs folder. The result must sit inside the device's storage."""
    if "{system}" not in template:
        raise ConfigOutOfRange("the staging folder must contain {system}", field=TEMPLATE_KEY)
    leftover = template.replace("{system}", "").replace("{roms}", "")
    if "{" in leftover or "}" in leftover:
        raise ConfigOutOfRange(
            "the staging folder may use only {roms} and {system}", field=TEMPLATE_KEY
        )
    if ".." in re.split(r"[\\/]", template):
        raise ConfigOutOfRange("the staging folder may not climb with ..", field=TEMPLATE_KEY)
    check_name(system)
    rel = template.replace("{roms}", roots.roms_at.relative("/")).replace("{system}", system)
    return roots.device.resolve(rel)


def staging_root(template: str, roots: DestRoots) -> ContainedPath:
    """The folder every system's staging folder sits in: the template up to {system}."""
    head = template.split("{system}", 1)[0].rstrip("/\\")
    if not head:
        raise ConfigOutOfRange(
            "the staging folder needs a parent folder before {system}", field=TEMPLATE_KEY
        )
    return roots.device.resolve(head.replace("{roms}", roots.roms_at.relative("/")))


# --- the store side (F8-S2) ------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class StoreCopy:
    present: bool
    staged_name: str
    path: ContainedPath | None = None
    size: int | None = None
    md5: str | None = None
    verified: bool | None = None


def store_copy(store: SysfileStore, req: Requirement, hash_limit: int) -> StoreCopy:
    """The store's copy of a requirement. Hashed only up to the limit; above it,
    files are compared by size alone."""
    found = store.locate(req.source, req.source_name)
    if found is None:
        return StoreCopy(False, req.name)
    md5 = store.md5(found.path) if found.size <= hash_limit else None
    verified = (md5 in req.md5s) if (req.md5s and md5) else None
    # a firmware zip keeps its real name on the device, so its version shows
    staged_name = found.path.name if req.source == "firmware-zip" else req.name
    return StoreCopy(True, staged_name, found.path, found.size, md5, verified)


# --- readiness (F8-S6) ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RequirementState:
    requirement: Requirement
    store: StoreCopy
    staged: Staged
    installed: Installed
    installed_at: str


@dataclass(frozen=True, slots=True)
class SystemState:
    system: SystemEntry
    package: str | None
    #: True or False once a survey has seen the device's app folders; None
    #: when there are none to look in, or no survey yet.
    emulator_seen: bool | None
    readiness: Readiness
    staging: Staging
    staging_folder: str
    requirements: tuple[RequirementState, ...]
    missing: tuple[str, ...]

    @property
    def staged_any(self) -> bool:
        return any(
            r.staged in (Staged.CURRENT, Staged.DIFFERENT, Staged.PRESENT)
            for r in self.requirements
        )


@dataclass(frozen=True, slots=True)
class Other:
    """Something under the staging root that no system accounts for."""

    path: str
    name: str
    kind: str
    size: int | None


@dataclass(frozen=True, slots=True)
class Report:
    surveyed_at: str | None
    apps: Mapping[str, str]
    systems: tuple[SystemState, ...]
    others: tuple[Other, ...]


def _listing(entries: Sequence[SurveyEntry]) -> dict[str, dict[str, SurveyEntry]]:
    """Each surveyed folder that is there, to its entries. An absent folder is
    left out, so `get` answers None for it."""
    folders: dict[str, dict[str, SurveyEntry]] = {}
    for e in entries:
        if e.kind == "missing":
            continue
        folders.setdefault(e.path, {})
        if e.name:
            folders[e.path][e.name] = e
    return folders


def detect_apps(systems: Sequence[SystemEntry], app_folders: Sequence[str]) -> dict[str, str]:
    """Each package pattern to the first app folder it matches."""
    found: dict[str, str] = {}
    for s in systems:
        if s.package is None or s.package in found:
            continue
        hits = sorted(n for n in app_folders if re.search(s.package, n, re.I))
        if hits:
            found[s.package] = hits[0]
    return found


class SystemFiles:
    def __init__(
        self,
        store: SysfileStore,
        repo: SysfileRepo,
        clock: ClockPort,
        scratch: LocalRoot,
        template: str,
        hash_limit: int,
        systems: Sequence[SystemEntry] | None = None,
    ) -> None:
        self._store = store
        self._repo = repo
        self._clock = clock
        self._scratch = scratch
        self.template = template
        self.hash_limit = hash_limit
        self.systems = tuple(systems) if systems is not None else load()

    @property
    def store(self) -> SysfileStore:
        return self._store

    def _system(self, key: str) -> SystemEntry:
        for s in self.systems:
            if s.key == key:
                return s
        raise ConfigOutOfRange(f"no system files are known for {key}", field="system")

    def _location(
        self, req: Requirement, roots: DestRoots, system: str, pkg: str | None
    ) -> str:
        if req.install.key == "staged":
            return staging_folder(self.template, roots, system).relative("/")
        return req.install.template.format(pkg=pkg or "?")

    # --- survey ----------------------------------------------------------------------

    def watched(
        self, roots: DestRoots, apps: Mapping[str, str], subfolders: Sequence[str] = ()
    ) -> list[ContainedPath]:
        root = staging_root(self.template, roots)
        paths = {
            root,
            roots.device.resolve(APP_FOLDERS),
            roots.device.resolve("RetroArch/system"),
        }
        paths.update(root.join(s) for s in subfolders)
        for s in self.systems:
            paths.add(staging_folder(self.template, roots, s.key))
            pkg = apps.get(s.package or "")
            for req in s.requirements:
                if req.install.needs_package and pkg:
                    paths.add(roots.device.resolve(self._location(req, roots, s.key, pkg)))
        return sorted(paths, key=lambda p: p.parts)

    def survey(self, device_id: str, dest: Dest) -> int:
        """List every watched folder (read-only), hash small staged files, record it.
        Returns the number of entries seen."""
        inventory: DestInventory = require(dest, DestInventory)
        roots = dest.roots()
        root = staging_root(self.template, roots)
        first = inventory.list_paths(self.watched(roots, {}))
        by_path = {listing.path: listing for listing in first}
        app_folder = by_path.get(roots.device.resolve(APP_FOLDERS))
        names = [e.name for e in app_folder.entries if e.kind == "folder"] if app_folder else []
        apps = detect_apps(self.systems, names)
        subs = (
            [e.name for e in by_path[root].entries if e.kind == "folder"]
            if root in by_path
            else []
        )
        more = [p for p in self.watched(roots, apps, subs) if p not in by_path]
        listings: list[Listing] = [*first, *(inventory.list_paths(more) if more else ())]
        hashes = self._hash_staged(dest, root, listings)
        entries: list[SurveyEntry] = []
        for listing in listings:
            rel = listing.path.relative("/")
            if not listing.present:
                entries.append(SurveyEntry(rel, "", "missing"))
                continue
            entries.append(SurveyEntry(rel, "", "folder"))
            for e in listing.entries:
                entries.append(
                    SurveyEntry(rel, e.name, e.kind, e.size, hashes.get((rel, e.name)))
                )
        self._repo.replace_survey(
            device_id, entries, self._clock.now().isoformat(timespec="seconds")
        )
        return sum(1 for e in entries if e.name)

    def _hash_staged(
        self, dest: Dest, root: ContainedPath, listings: Sequence[Listing]
    ) -> dict[tuple[str, str], str]:
        """md5 of each staged file up to the limit: on the device where it can, or
        from a copy fetched to the scratch folder."""
        wanted = [
            listing.path.join(e.name)
            for listing in listings
            if listing.present and listing.path.parts[: len(root.parts)] == root.parts
            for e in listing.entries
            if e.kind == "file" and e.size is not None and 0 < e.size <= self.hash_limit
        ]
        if not wanted:
            return {}
        if dest.supports(DestVerify):
            verify: DestVerify = require(dest, DestVerify)
            digests = verify.digest_many(wanted)
        else:
            files: DestFiles = require(dest, DestFiles)
            digests = {}
            fetch = self._scratch.child("sysfile-hash")
            for path in wanted:
                digests[path] = self._store.md5(files.get_file(path, fetch))
        return {("/".join(p.parts[:-1]), p.name): d for p, d in digests.items()}

    # --- readiness --------------------------------------------------------------------

    def report(self, device_id: str, roots: DestRoots) -> Report:
        surveyed_at = self._repo.surveyed_at(device_id)
        listing = _listing(self._repo.survey(device_id))
        app_listing = listing.get(APP_FOLDERS)
        has_apps = surveyed_at is not None and app_listing is not None
        apps = detect_apps(
            self.systems, [n for n, e in (app_listing or {}).items() if e.kind == "folder"]
        )
        claimed: set[tuple[str, str]] = set()
        states = tuple(
            self._system_state(s, roots, listing, surveyed_at, has_apps, apps, claimed)
            for s in self.systems
        )
        return Report(surveyed_at, apps, states, self._others(roots, listing, claimed))

    def _staged(
        self, staged_dir: Mapping[str, SurveyEntry], copy: StoreCopy, surveyed: bool
    ) -> Staged:
        if not surveyed:
            return Staged.UNKNOWN
        entry = staged_dir.get(copy.staged_name)
        if entry is None or entry.kind != "file":
            return Staged.ABSENT
        if not copy.present:
            return Staged.PRESENT
        if entry.size != copy.size:
            return Staged.DIFFERENT
        if copy.md5 and entry.hash:
            return Staged.CURRENT if entry.hash == copy.md5 else Staged.DIFFERENT
        return Staged.CURRENT

    def _installed(
        self,
        req: Requirement,
        copy: StoreCopy,
        staged: Staged,
        where: str,
        listing: Mapping[str, Mapping[str, SurveyEntry]],
        surveyed: bool,
        has_apps: bool,
        pkg: str | None,
    ) -> Installed:
        if not surveyed:
            return Installed.UNKNOWN
        if req.install.needs_package and not has_apps:
            return Installed.NOT_APPLICABLE
        if req.install.needs_package and pkg is None:
            return Installed.UNSEEN
        if req.install.key == "staged":
            return (
                Installed.INSTALLED
                if staged in (Staged.CURRENT, Staged.PRESENT)
                else Installed.MISSING
            )
        folder = listing.get(where)
        if folder is None:
            return Installed.MISSING
        if req.match is not None:
            pattern = re.compile(req.match, re.I)
            hit = any(e.kind == "file" and pattern.search(n) for n, e in folder.items())
            return Installed.INSTALLED if hit else Installed.MISSING
        entry = folder.get(req.name)
        if entry is None or entry.kind != "file":
            return Installed.MISSING
        if copy.size is None or entry.size == copy.size:
            return Installed.INSTALLED
        return Installed.DIFFERENT

    def _system_state(
        self,
        system: SystemEntry,
        roots: DestRoots,
        listing: Mapping[str, Mapping[str, SurveyEntry]],
        surveyed_at: str | None,
        has_apps: bool,
        apps: Mapping[str, str],
        claimed: set[tuple[str, str]],
    ) -> SystemState:
        surveyed = surveyed_at is not None
        pkg = apps.get(system.package) if system.package else None
        seen = (pkg is not None) if has_apps and system.package else None
        folder = staging_folder(self.template, roots, system.key).relative("/")
        staged_dir = listing.get(folder, {})
        rows: list[RequirementState] = []
        groups: dict[str, bool] = {}
        for req in system.requirements:
            copy = store_copy(self._store, req, self.hash_limit)
            staged = self._staged(staged_dir, copy, surveyed)
            if staged is not Staged.ABSENT and staged is not Staged.UNKNOWN:
                claimed.add((folder, copy.staged_name))
            where = self._location(req, roots, system.key, pkg)
            installed = self._installed(
                req, copy, staged, where, listing, surveyed, has_apps, pkg
            )
            if req.group:
                groups[req.group] = (
                    groups.get(req.group, False) or installed is Installed.INSTALLED
                )
            rows.append(RequirementState(req, copy, staged, installed, where))
        readiness = self._readiness(system, rows, groups, surveyed, seen)
        missing = tuple(
            r.requirement.name
            for r in rows
            if r.requirement.required
            and r.installed is not Installed.INSTALLED
            and not (r.requirement.group and groups.get(r.requirement.group))
        )
        return SystemState(
            system,
            pkg,
            seen,
            readiness,
            self._staging(rows, surveyed),
            folder,
            tuple(rows),
            missing,
        )

    @staticmethod
    def _readiness(
        system: SystemEntry,
        rows: Sequence[RequirementState],
        groups: Mapping[str, bool],
        surveyed: bool,
        seen: bool | None,
    ) -> Readiness:
        if not rows:
            return Readiness.UNSEEN if seen is False else Readiness.NONE
        if not surveyed:
            return Readiness.UNKNOWN
        if seen is False:
            return Readiness.UNSEEN
        ok = [r.installed is Installed.INSTALLED for r in rows]
        need = [(r, k) for r, k in zip(rows, ok, strict=True) if r.requirement.required]
        singles = all(k for r, k in need if not r.requirement.group)
        grouped = all(groups[r.requirement.group] for r, _ in need if r.requirement.group)
        if not (singles and grouped):
            return Readiness.MISSING
        if any(not k and not r.requirement.required for r, k in zip(rows, ok, strict=True)):
            return Readiness.OPTIONAL
        return Readiness.READY

    @staticmethod
    def _staging(rows: Sequence[RequirementState], surveyed: bool) -> Staging:
        stageable = [r for r in rows if r.store.present]
        if not stageable:
            return Staging.NOTHING_TO_STAGE
        if not surveyed:
            return Staging.UNKNOWN
        if all(r.staged is Staged.CURRENT for r in stageable):
            return Staging.CURRENT
        if any(r.staged in (Staged.CURRENT, Staged.DIFFERENT, Staged.PRESENT) for r in rows):
            return Staging.OUTDATED
        return Staging.ABSENT

    def _others(
        self,
        roots: DestRoots,
        listing: Mapping[str, Mapping[str, SurveyEntry]],
        claimed: set[tuple[str, str]],
    ) -> tuple[Other, ...]:
        root = staging_root(self.template, roots).relative("/")
        keys = {s.key for s in self.systems}
        found: list[Other] = []
        for path, entries in listing.items():
            if path != root and not path.startswith(root + "/"):
                continue
            for name, e in entries.items():
                if (path, name) in claimed:
                    continue
                if path == root and e.kind == "folder" and name in keys:
                    continue  # a system's own staging folder
                found.append(Other(path, name, e.kind, e.size))
        return tuple(sorted(found, key=lambda o: (o.path, o.name.lower())))

    # --- actions ----------------------------------------------------------------------

    def stage(self, device_id: str, dest: Dest, key: str) -> tuple[str, ...]:
        """Put every store-present file of `key` in its staging folder. A staged
        copy is replaced by the write itself, never deleted first (F8-S4); an
        older copy under another name (a firmware zip of an earlier version) is
        removed only once the new one has landed. Returns what was placed."""
        self._system(key)
        files: DestFiles = require(dest, DestFiles)
        roots = dest.roots()
        folder = staging_folder(self.template, roots, key)
        report = self.report(device_id, roots)
        state = next(s for s in report.systems if s.system.key == key)
        placed: list[str] = []
        superseded: list[str] = []
        listing = _listing(self._repo.survey(device_id)).get(folder.relative("/"), {})
        for row in state.requirements:
            if not row.store.present or row.staged is Staged.CURRENT or row.store.path is None:
                continue
            files.put_file(folder, row.store.path)
            placed.append(row.store.staged_name)
            if row.requirement.source == "firmware-zip":
                prefix = row.requirement.source_name.lower()
                superseded += [
                    n
                    for n, e in listing.items()
                    if e.kind == "file"
                    and n != row.store.staged_name
                    and n.lower().startswith(prefix)
                    and n.lower().endswith(".zip")
                ]
        for name in superseded:
            files.delete_file(folder.join(name))
        self.survey(device_id, dest)
        return tuple(placed)

    def unstage(self, device_id: str, dest: Dest, key: str) -> tuple[str, ...]:
        """Remove `key`'s staged files from its staging folder. The folder stays."""
        self._system(key)
        files: DestFiles = require(dest, DestFiles)
        roots = dest.roots()
        folder = staging_folder(self.template, roots, key)
        state = next(s for s in self.report(device_id, roots).systems if s.system.key == key)
        removed = []
        for row in state.requirements:
            if row.staged in (Staged.CURRENT, Staged.DIFFERENT, Staged.PRESENT):
                files.delete_file(folder.join(row.store.staged_name))
                removed.append(row.store.staged_name)
        self.survey(device_id, dest)
        return tuple(removed)

    def remove_other(
        self, device_id: str, dest: Dest, folder: ContainedPath, name: str
    ) -> None:
        """Delete one stray item under the staging root. `folder` is contained and
        `name` is a bare name (F8-S5)."""
        check_name(name)
        files: DestFiles = require(dest, DestFiles)
        roots = dest.roots()
        root = staging_root(self.template, roots)
        if folder.root != roots.device or folder.parts[: len(root.parts)] != root.parts:
            raise PathEscape(
                "only items under the staging folder can be removed here", field="path"
            )
        if not files.delete_file(folder.join(name)):
            raise DestinationItemMissing(f"{name} was not there")
        self.survey(device_id, dest)
