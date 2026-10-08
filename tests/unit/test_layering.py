"""The dependency rule, enforced rather than remembered.

SPEC section 2: `domain` imports the standard library only, `ports` imports
`domain`, `app` imports `domain` and `ports`, adapters import those plus their
own third-party libraries, and nothing imports `api`, `desktop` or `ui`.

The checker is a function so the test can run it over a planted violation as
well as over the real tree. A rule that cannot catch a deliberate breach is a
rule nobody has tested.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

#: Layer to the layers it may import. The standard library is always allowed.
ALLOWED: dict[str, frozenset[str]] = {
    "domain": frozenset(),
    "ports": frozenset({"domain"}),
    "app": frozenset({"domain", "ports"}),
    "adapters": frozenset({"domain", "ports"}),
    "jobs": frozenset({"domain", "ports", "app"}),
    "config": frozenset({"domain"}),
    "compose": frozenset({"domain", "ports", "app", "adapters", "jobs", "config"}),
}

#: Nothing inside the engine may import these at all.
FORBIDDEN_ROOTS = ("romsync_api", "romsync_desktop")


@dataclass(frozen=True, slots=True)
class Edge:
    source: str
    target: str
    line: int

    def __str__(self) -> str:
        return f"{self.source}:{self.line} imports {self.target}"


def _layer_of(module: str) -> str | None:
    if not module.startswith("romsync."):
        return None
    rest = module.removeprefix("romsync.")
    head = rest.split(".")[0]
    return head if head in ALLOWED else None


def _imports(path: Path) -> list[tuple[str, int]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [(alias.name, node.lineno) for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.append((node.module, node.lineno))
    return found


def illegal_edges(engine_root: Path) -> list[Edge]:
    """Every import that the dependency rule forbids."""
    bad: list[Edge] = []
    for path in sorted(engine_root.rglob("*.py")):
        relative = path.relative_to(engine_root)
        dotted = "romsync." + ".".join(relative.with_suffix("").parts)
        dotted = dotted.removesuffix(".__init__")
        source_layer = _layer_of(dotted)
        if source_layer is None:
            continue
        allowed = ALLOWED[source_layer]
        for target, line in _imports(path):
            if target.startswith(FORBIDDEN_ROOTS):
                bad.append(Edge(str(relative), target, line))
                continue
            target_layer = _layer_of(target)
            if target_layer is None or target_layer == source_layer:
                continue
            if target_layer not in allowed:
                bad.append(Edge(str(relative), target, line))
    return bad


def test_no_illegal_edges() -> None:
    bad = illegal_edges(ROOT / "engine" / "romsync")
    assert not bad, "the dependency rule is broken:\n" + "\n".join(str(e) for e in bad)


def test_domain_imports_the_standard_library_only() -> None:
    domain = ROOT / "engine" / "romsync" / "domain"
    for path in sorted(domain.rglob("*.py")):
        for target, line in _imports(path):
            assert not target.startswith("romsync."), (
                f"{path.name}:{line} imports {target}: the domain is pure"
            )


@pytest.mark.parametrize(
    ("layer", "offending_import"),
    [
        ("domain", "from romsync.adapters.db_sqlite import connect"),
        ("domain", "from romsync.ports.clock import ClockPort"),
        ("ports", "from romsync.app.sync import run"),
        ("app", "from romsync.adapters.dest_volume import VolumeDest"),
        ("config", "from romsync.adapters.store_fs import scan"),
        ("domain", "import romsync_api"),
    ],
)
def test_detects_planted_violations(tmp_path: Path, layer: str, offending_import: str) -> None:
    """A deliberate breach in each layer is caught."""
    fake = tmp_path / "romsync"
    (fake / layer).mkdir(parents=True)
    (fake / "__init__.py").write_text("", encoding="utf-8")
    (fake / layer / "__init__.py").write_text("", encoding="utf-8")
    (fake / layer / "planted.py").write_text(offending_import + "\n", encoding="utf-8")
    bad = illegal_edges(fake)
    assert bad, f"a {layer} module importing {offending_import!r} was not caught"
