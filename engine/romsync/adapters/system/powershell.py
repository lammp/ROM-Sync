"""Where Windows PowerShell is, found without the PATH.

Drives, MTP devices and notifications are read through PowerShell. Asking the
PATH for it lets a narrowed PATH hide every device, which is what happened
when the application was started with Windows' own folders left off it. The
executable sits at the same place under the Windows folder on every Windows
since 7, so it is named there; only where the Windows folder is unknown is
the PATH asked.
"""

from __future__ import annotations

import ntpath
import os
from collections.abc import Mapping

#: The executable's place under the Windows folder.
UNDER_WINDOWS = ("System32", "WindowsPowerShell", "v1.0", "powershell.exe")


def powershell_exe(env: Mapping[str, str] | None = None) -> str:
    """Windows PowerShell's full path, from the Windows folder the environment names."""
    found = os.environ if env is None else env
    root = next((v for k, v in found.items() if k.upper() == "SYSTEMROOT" and v), None)
    return ntpath.join(root, *UNDER_WINDOWS) if root else "powershell.exe"
