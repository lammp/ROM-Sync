"""The fit: judged on the most the run ever holds, against the configured margin."""

from __future__ import annotations

import inspect

import pytest

from romsync.domain.models import Action, DeviceItem, GameUnit, Kind, Mode, Op, Plan, SystemKey
from romsync.domain.planning import fit, plan
from romsync.domain.selection import EMPTY, with_mode
from tests.helpers.trees import item

PSX = SystemKey("psx")
T = 1_700_000_000.0
GB = 1_000_000_000
MIB = 1024 * 1024


def _plan(
    units: list[GameUnit],
    inventory: list[DeviceItem],
    *,
    free: int | None,
    margin: int = 512 * MIB,
    replace_first: bool = True,
) -> Plan:
    return plan(
        systems=[PSX],
        units=units,
        selection=with_mode(EMPTY, PSX, Mode.ALL),
        inventory=inventory,
        free=free,
        margin=margin,
        replace_first=replace_first,
    )


def _update_heavy(free: int, replace_first: bool = True) -> Plan:
    """A 4 GB game replaced by a 4.1 GB copy on a volume with 1 GB free."""
    unit = GameUnit(PSX, "Big.chd", Kind.FILE, 4 * GB + GB // 10, T + 10, id=1)
    held = item("psx\\Big.chd", size=4 * GB, sent_size=4 * GB, sent_mtime=T)
    return _plan([unit], [held], free=free, replace_first=replace_first)


def test_peak_not_net() -> None:
    """On net it fits with room to spare; at its peak it does not fit at all."""
    p = _update_heavy(free=GB)
    assert p.bytes.net == GB // 10
    assert GB - p.bytes.net > 512 * MIB
    assert p.bytes.peak == 4 * GB + GB // 10
    assert p.bytes.fits is False


def test_removing_first_peaks_at_the_difference() -> None:
    """Where the old copy goes before the new one lands, only the growth counts."""
    p = _update_heavy(free=GB, replace_first=False)
    assert p.bytes.peak == GB // 10
    assert p.bytes.fits is True


def test_removes_run_first_and_free_room_for_what_follows() -> None:
    units = [GameUnit(PSX, "New.chd", Kind.FILE, 3 * GB, T, id=1)]
    p = _plan(units, [item("psx\\Old.chd", size=2 * GB)], free=2 * GB, margin=0)
    assert (p.bytes.net, p.bytes.peak, p.bytes.fits) == (GB, GB, True)


def test_the_peak_is_never_below_where_the_run_started() -> None:
    p = _plan([], [item("psx\\Old.chd", size=GB)], free=0, margin=0)
    assert (p.bytes.net, p.bytes.peak, p.bytes.fits) == (-GB, 0, True)


def test_margin_from_config() -> None:
    """The margin is whatever the caller read from config, and nothing else."""
    assert inspect.signature(plan).parameters["margin"].default is inspect.Parameter.empty
    assert inspect.signature(fit).parameters["margin"].default is inspect.Parameter.empty
    peak = 4 * GB + GB // 10
    for margin, free, fits in [
        (512 * MIB, peak + 512 * MIB, True),
        (512 * MIB, peak + 512 * MIB - 1, False),
        (0, peak, True),
        (2 * GB, peak + GB, False),
    ]:
        p = _plan(
            [GameUnit(PSX, "Big.chd", Kind.FILE, peak, T + 10, id=1)],
            [item("psx\\Big.chd", size=4 * GB, sent_size=4 * GB, sent_mtime=T)],
            free=free,
            margin=margin,
        )
        assert p.bytes.fits is fits, (margin, free)


def test_an_unknown_free_space_has_no_verdict() -> None:
    assert _plan([], [], free=None).bytes.fits is None


@pytest.mark.parametrize("replace_first", [True, False])
def test_fit_alone_walks_the_same_order(replace_first: bool) -> None:
    send = Op(Action.SEND, PSX, "A", Kind.FILE, 5)
    remove = Op(Action.REMOVE, PSX, "B", Kind.FILE, 5)
    ops = {Action.SEND: (send,), Action.UPDATE: (), Action.REMOVE: (remove,)}
    bytes_ = fit(ops, {}, free=5, margin=5, replace_first=replace_first)
    assert (bytes_.peak, bytes_.fits) == (0, True)
