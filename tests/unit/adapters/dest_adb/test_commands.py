"""Debug-bridge commands, asserted as argument vectors (F6-S5)."""

from __future__ import annotations

import pytest

from romsync.adapters.dest_adb import commands as cmd
from romsync.domain.errors import DestinationToolMissing

NAMES = [
    "Legend of Zelda, The - A Link to the Past (USA).sfc",
    "Tom & Jerry (Europe).nes",
    "Pac-Man's Revenge (Japan).nes",
    "It's a 'quote' (World).zip",
    "$(rm -rf) `echo` ; | > <.nes",
]


@pytest.mark.parametrize("name", NAMES)
def test_quoting(name: str) -> None:
    quoted = cmd.q(f"/sdcard/ROMs/snes/{name}")
    assert quoted.startswith("'") and quoted.endswith("'")
    # every embedded single quote is closed, escaped and reopened, so the shell
    # reads the whole name as one word with nothing expanded
    inner = quoted[1:-1].replace("'\\''", "")
    assert "'" not in inner
    assert inner.replace("/sdcard/ROMs/snes/", "") == name.replace("'", "")


def test_a_quote_round_trips_through_posix_shell_rules() -> None:
    import shlex

    for name in NAMES:
        assert shlex.split(cmd.q(name)) == [name]


def test_shell_sends_the_command_as_one_argument() -> None:
    command = cmd.remove("/sdcard/ROMs/nes/Tom & Jerry (Europe).nes")
    argv = cmd.shell("adb", "R5CT", command)
    assert argv == ["adb", "-s", "R5CT", "shell", command]


def test_push_and_pull_paths_travel_unquoted() -> None:
    name = "/sdcard/ROMs/nes/Tom & Jerry (Europe).nes"
    assert cmd.push("adb", "R5CT", "C:\\store\\a.nes", name) == [
        "adb",
        "-s",
        "R5CT",
        "push",
        "C:\\store\\a.nes",
        name,
    ]
    assert cmd.pull("adb", "R5CT", name, "out")[-2:] == [name, "out"]


def test_read_uses_exec_out_so_bytes_are_not_mangled() -> None:
    assert cmd.read("adb", "R5CT", "/sdcard/ROMs/ROM-Sync.json") == [
        "adb",
        "-s",
        "R5CT",
        "exec-out",
        "cat '/sdcard/ROMs/ROM-Sync.json'",
    ]


def test_missing_tool_error() -> None:
    with pytest.raises(DestinationToolMissing, match="on the PATH") as raised:
        cmd.locate("", lambda _name: None)
    assert raised.value.field == "adb.path"
    with pytest.raises(DestinationToolMissing, match=r"at D:/tools/adb\.exe"):
        cmd.locate("D:/tools/adb.exe", lambda _name: None)
    assert cmd.locate("", lambda name: f"/usr/bin/{name}") == "/usr/bin/adb"


def test_remote_paths_join_below_the_storage() -> None:
    assert cmd.remote("/sdcard/", ("ROMs", "nes", "A.nes")) == "/sdcard/ROMs/nes/A.nes"
    assert cmd.remote("storage/1234-ABCD", ()) == "/storage/1234-ABCD"


def test_the_push_deadline_grows_with_the_file() -> None:
    assert cmd.push_deadline(1024) == cmd.PUSH_FLOOR_SECONDS
    eight_gb = 8 * 1024**3
    assert cmd.push_deadline(eight_gb) == eight_gb / cmd.PUSH_FLOOR_RATE


def test_place_keeps_the_old_copy_until_the_new_one_is_there() -> None:
    script = cmd.place("/r/A.rs-part", "/r/A")
    assert script.index("mv '/r/A' '/r/A.rs-old'") < script.index("mv '/r/A.rs-part' '/r/A'")
    assert "mv '/r/A.rs-old' '/r/A'" in script.split("else", 1)[1]


def test_parse_devices() -> None:
    out = (
        "List of devices attached\n"
        "* daemon started successfully\n"
        "R5CT123 device product:thor model:AYN_Thor device:thor\n"
        "ZX1 unauthorized\n"
        "\n"
    )
    found = cmd.parse_devices(out)
    assert [(d.serial, d.state, d.model, d.usable) for d in found] == [
        ("R5CT123", "device", "AYN Thor", True),
        ("ZX1", "unauthorized", "", False),
    ]
    assert cmd.devices("adb") == ["adb", "devices", "-l"]


def test_parse_df() -> None:
    out = (
        "Filesystem 1K-blocks Used Available Use% Mounted on\n"
        "/dev/fuse 1000 400 600 40% /sdcard\n"
    )
    assert cmd.parse_df(out) == (1024000, 614400)
    assert cmd.parse_df("df: /nowhere: No such file\n") is None


def test_parse_scan() -> None:
    out = (
        "@@@D\nnes\nsnes\nps2\nps2/Game\nps2/Game/disc\n"
        "@@@F\n3\tnes/A.nes\n4\tsnes/B.sfc\n5\tps2/Game/1.iso\n6\tps2/Game/disc/2.iso\n"
        "9\ttop-level.txt\nx\tnes/bad.nes\n"
    )
    tree = cmd.parse_scan(out)
    assert tree.top == ["nes", "ps2", "snes"]
    assert tree.folders == {("ps2", "Game")}
    assert tree.sizes == {("nes", "A.nes"): 3, ("snes", "B.sfc"): 4, ("ps2", "Game"): 11}


def test_parse_listing() -> None:
    paths = ["/sdcard/ROMs/bios", "/sdcard/It's here", "/sdcard/absent"]
    assert "'@@@>/sdcard/It'\\''s here'" in cmd.listing(paths)
    out = (
        "@@@>/sdcard/ROMs/bios\n@@@DIR\n@@@dpsx\n10\tscph.bin\n"
        "@@@>/sdcard/It's here\n@@@DIR\n"
        "@@@>/sdcard/absent\n@@@MISSING\n"
    )
    assert cmd.parse_listing("stray line\n" + out) == {
        "/sdcard/ROMs/bios": [("psx", "folder", None), ("scph.bin", "file", 10)],
        "/sdcard/It's here": [],
        "/sdcard/absent": None,
    }


def test_parse_md5() -> None:
    out = (
        "900150983cd24fb0d6963f7d28e17f72  /sdcard/ROMs/nes/A b.nes\n"
        "md5sum: /sdcard/ROMs/nes/gone.nes: No such file or directory\n"
    )
    assert cmd.parse_md5(out) == {
        "/sdcard/ROMs/nes/A b.nes": "900150983cd24fb0d6963f7d28e17f72"
    }
