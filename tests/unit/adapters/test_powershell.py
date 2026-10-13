"""Windows PowerShell is found under the Windows folder, not on the PATH."""

from __future__ import annotations

from romsync.adapters.system.powershell import powershell_exe


def test_named_under_the_windows_folder_whatever_the_path() -> None:
    env = {"SystemRoot": "X:\\Win", "PATH": "X:\\nothing"}
    assert powershell_exe(env) == "X:\\Win\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"
    assert powershell_exe({"SYSTEMROOT": "X:\\Win"}).startswith("X:\\Win\\System32")


def test_the_path_only_where_the_windows_folder_is_unknown() -> None:
    assert powershell_exe({"PATH": "X:\\bin"}) == "powershell.exe"
    assert powershell_exe({"SystemRoot": ""}) == "powershell.exe"
