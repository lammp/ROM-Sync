"""The engine's goldens, captured from version 1.

    python tools/verify.py --regenerate-goldens

A golden here is version 1's own answer over a fixture, so the rebuild is held
to what version 1 did rather than to what someone remembered it doing. The
plan golden runs version 1's planner, read from the `parity-source-v1` tag
with `git archive`, against a throwaway database filled from
`tests/fixtures/store_tree.py` and `tests/fixtures/device_tree.py`.

Regenerating is never a gate stage. A golden that changes needs a one-sentence
reason in its commit (TESTING.md, section 5).

The repository publishes Python modules only under `tests/`, so a golden is a
module holding its lines in one raw string: text, line-oriented, sorted and
diffable all the same.
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
import tarfile
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
TAG = "parity-source-v1"
V1_PACKAGE = "ROM-Sync/romsync"
PLAN_GOLDEN = ROOT / "tests" / "golden" / "data" / "plan.py"

ACTIONS = ("send", "update", "remove")

#: Runs inside a child interpreter with version 1 on its path. It fills a
#: fresh database from the fixture, asks version 1 for the plan, and prints
#: the plan in the neutral form `plan_lines` reads.
_DRIVER = r"""
import json, os, sys, tempfile
source, inputs = sys.argv[1], sys.argv[2]
sys.path.insert(0, source)
from romsync import db, planner

work = tempfile.mkdtemp()
db.db_path = lambda: os.path.join(work, "v1.db")
with open(inputs, encoding="utf-8") as f:
    data = json.load(f)
conn = db.connect()
now = db.now()
dev = data["device_id"]
conn.execute(
    "INSERT INTO devices(id,name,kind,roms_root,first_seen,last_seen) VALUES(?,?,?,?,?,?)",
    (dev, "fixture", "volume", "ROMs", now, now),
)
for key in data["systems"]:
    conn.execute("INSERT INTO systems(key,label) VALUES(?,?)", (key, key))
for u in data["units"]:
    conn.execute(
        "INSERT INTO games(id,system,rel_path,kind,name,title,size,mtime,seen_at)"
        " VALUES(?,?,?,?,?,?,?,?,?)",
        (u["id"], u["system"], u["system"] + "\\" + u["name"], u["kind"], u["name"],
         u["name"], u["size"], u["mtime"], now),
    )
for system, mode in data["modes"].items():
    conn.execute(
        "INSERT INTO selections(device_id,system,mode) VALUES(?,?,?)", (dev, system, mode)
    )
for game_id, include in data["overrides"].items():
    conn.execute(
        "INSERT INTO selection_overrides(device_id,game_id,include) VALUES(?,?,?)",
        (dev, int(game_id), 1 if include else 0),
    )
for i in data["inventory"]:
    conn.execute(
        "INSERT INTO device_files(device_id,rel_path,kind,size,sent_size,sent_mtime)"
        " VALUES(?,?,?,?,?,?)",
        (dev, i["rel_path"], i["kind"], i["size"], i["sent_size"], i["sent_mtime"]),
    )
conn.commit()
p = planner.plan(dev)
out = {k: [[o["system"], o["name"], o["kind"], o["size"]] for o in p[k]]
       for k in ("send", "update", "remove")}
out["unchanged"] = p["unchanged"]
out["unknown"] = p["unknown_systems"]
out["managed"] = list(p["managed_systems"])
out["bytes"] = {k: p["bytes"][k] for k in ("add", "drop", "net")}
print(json.dumps(out))
"""


def plan_lines(plan: Mapping[str, Any]) -> list[str]:
    """A plan in its golden form: one fact per line, each section sorted.

    `plan` is the neutral form: `send`, `update` and `remove` as lists of
    `[system, name, kind, size]`; `unchanged`; `unknown` as a mapping of
    folder to count; `managed` as a list; and `bytes` with `add`, `drop` and
    `net`. Version 1's output and the rebuild's are both rendered through
    here, so the comparison is of one format with itself.
    """
    lines: list[str] = []
    for action in ACTIONS:
        ops = sorted(plan[action], key=lambda o: (o[0], o[1].lower()))
        lines += [f"{action}\t{s}\t{n}\t{k}\t{z}" for s, n, k, z in ops]
    lines.append(f"unchanged\t{plan['unchanged']}")
    lines += [f"unknown\t{s}\t{c}" for s, c in sorted(plan["unknown"].items())]
    lines += [f"managed\t{s}" for s in sorted(plan["managed"])]
    lines += [f"bytes\t{k}\t{plan['bytes'][k]}" for k in ("add", "drop", "net")]
    return lines


def fixture_inputs() -> dict[str, Any]:
    """The fixture store and device, as plain data for version 1's tables."""
    from tests.fixtures import device_tree, store_tree

    return {
        "device_id": device_tree.DEVICE_ID,
        "systems": list(store_tree.SYSTEMS),
        "units": [u._asdict() for u in store_tree.UNITS],
        "modes": device_tree.MODES,
        "overrides": {str(k): v for k, v in device_tree.OVERRIDES.items()},
        "inventory": [i._asdict() for i in device_tree.INVENTORY],
    }


def _git(*args: str) -> bytes:
    return subprocess.run(("git", *args), cwd=ROOT, check=True, capture_output=True).stdout


def v1_plan(work: Path) -> dict[str, Any]:
    """Version 1's plan over the fixture, run from the tag."""
    archive = _git("archive", "--format=tar", TAG, V1_PACKAGE)
    source = work / "v1"
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(source, filter="data")
    driver = work / "driver" / "plan_driver.py"
    driver.parent.mkdir()
    driver.write_text(_DRIVER, encoding="utf-8")
    inputs = work / "inputs.json"
    inputs.write_text(json.dumps(fixture_inputs()), encoding="utf-8")
    completed = subprocess.run(
        (sys.executable, "-I", str(driver), str(source / "ROM-Sync"), str(inputs)),
        check=True,
        capture_output=True,
        text=True,
    )
    result: dict[str, Any] = json.loads(completed.stdout)
    return result


def render_module(lines: Sequence[str], commit: str) -> str:
    """The golden module's text."""
    body = "\n".join(lines)
    return (
        '"""The plan golden: version 1\'s plan over the fixture store and device.\n'
        "\n"
        "Generated by `python tools/verify.py --regenerate-goldens`. Do not edit by\n"
        "hand; a change needs a reason in its commit.\n"
        '"""\n'
        "\n"
        f'SOURCE = "{TAG} {commit}"\n'
        "\n"
        f'LINES = r"""\n{body}\n"""\n'
    )


def regenerate() -> list[Path]:
    """Rewrite every golden from version 1. Returns the files written."""
    commit = _git("rev-parse", f"{TAG}^{{commit}}").decode().strip()
    with tempfile.TemporaryDirectory() as tmp:
        plan = v1_plan(Path(tmp))
    PLAN_GOLDEN.write_text(render_module(plan_lines(plan), commit), encoding="utf-8")
    return [PLAN_GOLDEN]
