"""The config registry: declared once, validated at the boundary."""

from __future__ import annotations

from pathlib import Path

import pytest

from romsync.config.registry import REGISTRY, Registry, Setting
from romsync.domain.errors import (
    ConfigOutOfRange,
    ConfigWrongType,
    UnknownConfigKey,
)
from romsync.domain.planning import FULL_MARGIN

#: SPEC section 7 names the minimum coverage. Each of these must be declared.
REQUIRED_KEYS = (
    "store.root",
    "data.directory",
    "adb.path",
    "adb.enabled",
    "mtp.enabled",
    "device.staging_template",
    "sysfiles.hash_limit",
    "device.probe_interval",
    "plan.free_space_margin",
    "capacity.warn_fraction",
    "capacity.alarm_fraction",
    "sync.confirm_remove_threshold",
    "device.write_marker_after_sync",
    "sync.verify_percentage",
    "igdb.client_id",
    "igdb.client_secret",
    "igdb.requests_per_second",
    "match.accept_threshold",
    "match.auto_libretro_covers",
    "match.auto_enrich",
    "server.preferred_port",
    "log.level",
    "store.rescan_on_launch",
    "jobs.history_length",
    "runs.retention",
)


@pytest.mark.parametrize("key", REQUIRED_KEYS)
def test_minimum_coverage_is_declared(key: str) -> None:
    assert key in REGISTRY, f"SPEC section 7 requires {key}"


def test_keys_are_unique() -> None:
    assert len(REGISTRY.keys()) == len(set(REGISTRY.keys()))


def test_duplicate_keys_are_refused() -> None:
    one = Setting("a.b", "int", 1, "x")
    with pytest.raises(ValueError, match="duplicate"):
        Registry(settings=(one, one))


def test_defaults_have_no_absolute_paths() -> None:
    """The application has no opinion about whose machine it is on."""
    offenders = [
        s.key
        for s in REGISTRY.settings
        if s.kind == "path" and isinstance(s.default, str) and s.default
    ]
    assert not offenders, offenders
    for s in REGISTRY.settings:
        if isinstance(s.default, str) and s.default:
            assert not Path(s.default).is_absolute(), s.key
            assert ":" not in s.default or s.key == "server.bind_host", s.key


def test_an_absolute_path_default_cannot_be_declared() -> None:
    with pytest.raises(ValueError, match="never absolute"):
        Setting("x.y", "path", "C:/Games/ROMs", "nope")


def test_validation_rejects_out_of_range() -> None:
    with pytest.raises(ConfigOutOfRange) as caught:
        REGISTRY.validate_all({"device.probe_interval": 1})
    assert caught.value.field == "device.probe_interval"
    assert "at least" in caught.value.message


def test_validation_rejects_above_the_maximum() -> None:
    with pytest.raises(ConfigOutOfRange) as caught:
        REGISTRY.validate_all({"sync.verify_percentage": 101})
    assert caught.value.field == "sync.verify_percentage"


def test_validation_rejects_a_value_outside_an_allowed_set() -> None:
    with pytest.raises(ConfigOutOfRange) as caught:
        REGISTRY.validate_all({"log.level": "chatty"})
    assert "one of" in caught.value.message


def test_validation_rejects_the_wrong_type() -> None:
    with pytest.raises(ConfigWrongType) as caught:
        REGISTRY.validate_all({"jobs.history_length": "many"})
    assert caught.value.field == "jobs.history_length"


def test_a_bool_is_not_an_integer() -> None:
    with pytest.raises(ConfigWrongType):
        REGISTRY.get("jobs.history_length").validate(True)


def test_an_undeclared_key_is_refused() -> None:
    with pytest.raises(UnknownConfigKey) as caught:
        REGISTRY.validate_all({"made.up": 1})
    assert caught.value.field == "made.up"


def test_a_partial_write_touches_only_what_it_is_given() -> None:
    written = REGISTRY.validate_all({"log.level": "debug"})
    assert written == {"log.level": "debug"}


def test_null_clears_a_value() -> None:
    assert REGISTRY.validate_all({"adb.path": None}) == {"adb.path": None}


def test_secret_never_serialised() -> None:
    rows = {row["key"]: row for row in REGISTRY.describe()}
    secret = rows["igdb.client_secret"]
    assert secret["secret"] is True
    assert "default" not in secret, "a secret must not carry a value here"
    assert all("default" in r for r in rows.values() if not r["secret"])


def test_a_secret_cannot_be_declared_with_a_default() -> None:
    with pytest.raises(ValueError, match="cannot have a default"):
        Setting("x.secret", "str", "hunter2", "nope", secret=True)


def test_every_setting_has_a_description() -> None:
    for s in REGISTRY.settings:
        assert len(s.description) > 20, f"{s.key} needs a real description"


def test_restart_only_values_are_declared_as_such() -> None:
    """A change the interface cannot apply now must say so."""
    restart = {s.key for s in REGISTRY.settings if s.restart}
    assert {"data.directory", "server.preferred_port", "server.bind_host"} <= restart


def test_describe_is_what_the_interface_renders_from() -> None:
    for row in REGISTRY.describe():
        assert {"key", "kind", "description", "secret", "restart"} <= set(row)


def test_bool_accepts_its_string_spellings() -> None:
    setting = REGISTRY.get("adb.enabled")
    assert setting.validate("true") is True
    assert setting.validate("False") is False
    with pytest.raises(ConfigWrongType):
        setting.validate("yes")


def test_a_real_bool_passes_through() -> None:
    assert REGISTRY.get("mtp.enabled").validate(False) is False


def test_a_float_setting_accepts_an_integer() -> None:
    assert REGISTRY.get("igdb.requests_per_second").validate(2) == 2.0


def test_a_float_setting_accepts_a_numeric_string() -> None:
    assert REGISTRY.get("match.accept_threshold").validate("0.75") == 0.75


def test_a_bool_is_not_a_float() -> None:
    with pytest.raises(ConfigWrongType):
        REGISTRY.get("igdb.requests_per_second").validate(True)


def test_a_string_setting_refuses_a_number() -> None:
    with pytest.raises(ConfigWrongType):
        REGISTRY.get("igdb.client_id").validate(42)


def test_a_value_inside_both_bounds_is_returned() -> None:
    assert REGISTRY.get("device.probe_interval").validate(30) == 30


def test_a_value_at_a_bound_is_accepted() -> None:
    setting = REGISTRY.get("sync.verify_percentage")
    assert setting.validate(0) == 0
    assert setting.validate(100) == 100


def test_defaults_are_available_for_a_first_run() -> None:
    defaults = REGISTRY.defaults()
    assert set(defaults) == set(REGISTRY.keys())
    assert defaults["log.level"] == "info"
    assert defaults["igdb.client_secret"] == ""


def test_a_setting_with_no_bounds_skips_the_range_check() -> None:
    assert Setting("x.y", "int", 0, "no bounds declared here at all").validate(10**9) == 10**9


def test_free_space_margin_is_version_ones() -> None:
    """The plan's margin key is declared, with version 1's 512 MB and the design's range."""
    setting = REGISTRY.get(FULL_MARGIN)
    assert setting.default == 512 * 1024 * 1024
    assert (setting.minimum, setting.maximum) == (0, 8 * 1024 * 1024 * 1024)
