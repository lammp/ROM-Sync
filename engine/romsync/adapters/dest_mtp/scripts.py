"""The PowerShell the MTP adapter runs, and the one arrival policy it runs with.

A media-transfer device is reached through the Windows shell namespace, which
needs an STA thread, so each operation is a script run by `powershell.exe`.
The scripts are constants: every name, path and number reaches them through
environment variables, never by being formatted into the text, so a game
called `$(Remove-Item ...)` is a name and nothing else.

Reading from the device copies with every dialog off and waits (F6-S10).
Sending still uses `CopyHere`, which is asynchronous so its progress can be
reported, and Windows may show its own dialog if that copy fails. `CopyHere`
is asynchronous and MTP reports a growing file's size in coarse
steps (a 4 GB file can sit at one size for minutes), so a copy is judged
arrived by polling its size, and judged stalled only after a time that scales
with the file. That allowance is `ArrivalPolicy`, sized from the file and read
from config, and it is the same object for staging a single file and for a
bulk run (F6-S7). Version 1 had 90 seconds in one place and ten minutes in the
other.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final

#: The config keys the policy is read from.
FLOOR_KEY: Final = "mtp.arrival_floor"
RATE_KEY: Final = "mtp.arrival_rate"


@dataclass(frozen=True, slots=True)
class ArrivalPolicy:
    """How long a copy may sit without growing before it counts as stalled."""

    floor_seconds: int
    bytes_per_second: int

    def __post_init__(self) -> None:
        if self.floor_seconds <= 0 or self.bytes_per_second <= 0:
            raise ValueError("an arrival policy needs a positive floor and rate")

    def stall_seconds(self, size: int) -> int:
        return max(self.floor_seconds, size // self.bytes_per_second)

    @classmethod
    def from_config(cls, values: Mapping[str, object]) -> ArrivalPolicy:
        floor = values[FLOOR_KEY]
        rate = values[RATE_KEY]
        assert isinstance(floor, int) and isinstance(rate, int)
        return cls(floor, rate)


@dataclass(frozen=True, slots=True)
class Script:
    """A script and the environment it reads its parameters from."""

    text: str
    env: Mapping[str, str]


PROLOGUE: Final = r"""
$ErrorActionPreference = 'Stop'
$utf8 = New-Object System.Text.UTF8Encoding($false)

Add-Type -Language CSharp @'
using System;
using System.Runtime.InteropServices;
public static class Mtp {
  [ComImport, Guid("43826D1E-E718-42EE-BC55-A1E261C37BFE"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
  public interface IShellItem {
    void BindToHandler(IntPtr pbc, ref Guid bhid, ref Guid riid, out IntPtr ppv);
    void GetParent(out IShellItem ppsi);
    void GetDisplayName(uint sigdnName, out IntPtr ppszName);
    void GetAttributes(uint mask, out uint attribs);
    void Compare(IShellItem psi, uint hint, out int order);
  }
  [ComImport, Guid("947AAB5F-0A5C-4C13-B4D6-4BF7836FC9F8"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
  public interface IFileOperation {
    uint Advise(IntPtr sink, out uint cookie);
    uint Unadvise(uint cookie);
    uint SetOperationFlags(uint flags);
    uint SetProgressMessage([MarshalAs(UnmanagedType.LPWStr)] string msg);
    uint SetProgressDialog(IntPtr popd);
    uint SetProperties(IntPtr array);
    uint SetOwnerWindow(IntPtr owner);
    uint ApplyPropertiesToItem(IShellItem item);
    uint ApplyPropertiesToItems(object items);
    uint RenameItem(IShellItem item, [MarshalAs(UnmanagedType.LPWStr)] string n, IntPtr sink);
    uint RenameItems(object items, [MarshalAs(UnmanagedType.LPWStr)] string n);
    uint MoveItem(IShellItem item, IShellItem dest, [MarshalAs(UnmanagedType.LPWStr)] string n, IntPtr sink);
    uint MoveItems(object items, IShellItem dest);
    uint CopyItem(IShellItem item, IShellItem dest, [MarshalAs(UnmanagedType.LPWStr)] string n, IntPtr sink);
    uint CopyItems(object items, IShellItem dest);
    uint DeleteItem(IShellItem item, IntPtr sink);
    uint DeleteItems(object items);
    uint NewItem(IShellItem dest, uint attrs, [MarshalAs(UnmanagedType.LPWStr)] string name,
                 [MarshalAs(UnmanagedType.LPWStr)] string template, IntPtr sink);
    uint PerformOperations();
    uint GetAnyOperationsAborted(out bool aborted);
  }
  [DllImport("shell32.dll", PreserveSig = false)]
  static extern void SHGetIDListFromObject([MarshalAs(UnmanagedType.IUnknown)] object punk, out IntPtr ppidl);
  [DllImport("shell32.dll", PreserveSig = false)]
  static extern void SHCreateItemFromIDList(IntPtr pidl, [MarshalAs(UnmanagedType.LPStruct)] Guid riid,
      [MarshalAs(UnmanagedType.Interface)] out IShellItem item);
  [DllImport("shell32.dll", CharSet = CharSet.Unicode, PreserveSig = false)]
  static extern void SHCreateItemFromParsingName(string path, IntPtr pbc,
      [MarshalAs(UnmanagedType.LPStruct)] Guid riid, [MarshalAs(UnmanagedType.Interface)] out IShellItem item);
  [DllImport("ole32.dll")] static extern void CoTaskMemFree(IntPtr pv);
  static readonly Guid CLSID_FileOperation = new Guid("3AD05575-8857-4850-9277-11B85BDB8E09");
  static readonly Guid IID_IShellItem = new Guid("43826D1E-E718-42EE-BC55-A1E261C37BFE");
  const uint FOF_NO_UI = 0x0004 | 0x0010 | 0x0200 | 0x0400;
  static IShellItem ItemOf(object o) {
    IShellItem si;
    string path = o as string;
    if (path != null) { SHCreateItemFromParsingName(path, IntPtr.Zero, IID_IShellItem, out si); return si; }
    IntPtr pidl; SHGetIDListFromObject(o, out pidl);
    try { SHCreateItemFromIDList(pidl, IID_IShellItem, out si); return si; }
    finally { CoTaskMemFree(pidl); }
  }
  // Copy one item into a folder with every dialog off, waiting for it to finish
  // (F6-S10). Folder.CopyHere lets Windows show its own error dialog for a
  // phone whatever its flags say, and the dialog holds the copy until someone
  // presses OK; this way a failure is a result, never a window.
  public static uint CopyQuietly(object item, object intoFolder) {
    IFileOperation op = (IFileOperation)Activator.CreateInstance(Type.GetTypeFromCLSID(CLSID_FileOperation));
    op.SetOperationFlags(FOF_NO_UI);
    op.CopyItem(ItemOf(item), ItemOf(intoFolder), null, IntPtr.Zero);
    uint hr = op.PerformOperations();
    bool aborted; op.GetAnyOperationsAborted(out aborted);
    if (hr == 0 && aborted) return 0x000004C7;
    return hr;
  }
  public static uint DeleteMany(object[] folderItems) {
    if (folderItems == null || folderItems.Length == 0) return 0;
    IFileOperation op = (IFileOperation)Activator.CreateInstance(Type.GetTypeFromCLSID(CLSID_FileOperation));
    op.SetOperationFlags(FOF_NO_UI);
    foreach (object fi in folderItems) {
      IntPtr pidl; SHGetIDListFromObject(fi, out pidl);
      try { IShellItem si; SHCreateItemFromIDList(pidl, IID_IShellItem, out si); op.DeleteItem(si, IntPtr.Zero); }
      finally { CoTaskMemFree(pidl); }
    }
    uint hr = op.PerformOperations();
    bool aborted; op.GetAnyOperationsAborted(out aborted);
    if (hr == 0 && aborted) return 0x000004C7;
    return hr;
  }
}
'@

function Remove-DeviceItems($list) {
  $raw = New-Object System.Collections.ArrayList
  foreach ($i in $list) { if ($null -ne $i) { [void]$raw.Add($i.PSObject.BaseObject) } }
  if ($raw.Count -eq 0) { return [uint32]0 }
  return [Mtp]::DeleteMany($raw.ToArray())
}

function Get-Child($folder, $name, $wantFolder) {
  foreach ($i in $folder.Items()) {
    if ($i.Name -eq $name -and ((-not $wantFolder) -or $i.IsFolder)) { return $i }
  }
  return $null
}

function Resolve-Storage {
  $shell = New-Object -ComObject Shell.Application
  $device = $shell.NameSpace(17).Items() | Where-Object { $_.Name -eq $env:RS_DEVICE }
  if (-not $device) { throw "UNAVAILABLE`tthe device is not connected" }
  $stores = @($device.GetFolder.Items())
  $st = $stores | Where-Object { $_.Name -eq $env:RS_STORAGE }
  if (-not $st) { throw "UNAVAILABLE`tthe device has no storage by that name; is it in File Transfer mode?" }
  return $st
}

# Walk the parts (newline separated) below a storage. $create makes missing ones.
function Resolve-Parts($storageItem, $parts, $create) {
  $folder = $storageItem.GetFolder
  foreach ($seg in ($parts -split "`n" | Where-Object { $_ })) {
    $item = Get-Child $folder $seg $true
    if (-not $item -and $create) {
      $folder.NewFolder($seg)
      for ($i = 0; $i -lt 20 -and -not $item; $i++) { Start-Sleep -Milliseconds 200; $item = Get-Child $folder $seg $true }
    }
    if (-not $item) { return $null }
    $folder = $item.GetFolder
  }
  return $folder
}

function Size-Of($item) {
  if (-not $item.IsFolder) {
    $sz = [int64]0
    try { $sz = [int64]$item.ExtendedProperty('System.Size') } catch {}
    return $sz
  }
  $t = [int64]0
  foreach ($i in $item.GetFolder.Items()) { $t += (Size-Of $i) }
  return $t
}

# Wait for $name under $folder to reach $size, giving up once it has not grown for $stall seconds.
function Wait-Arrival($folder, $name, $size, $stall, $onBytes) {
  $last = -1; $still = 0.0
  while ($true) {
    Start-Sleep -Milliseconds 500
    $it = Get-Child $folder $name $false
    $now = if ($it) { Size-Of $it } else { -1 }
    if ($onBytes -and $now -ge 0) { & $onBytes $now }
    if ($it -and $now -ge $size) { return $true }
    if ($now -eq $last) { $still += 0.5 } else { $still = 0.0 }
    $last = $now
    if ($still -ge $stall) { return $false }
  }
}

# Copy a local file or folder into $folder under a staging folder, wait for it,
# then put it at its name: the old copy is renamed aside, the new one moved in,
# and the old one removed only once the new one is there.
function Send-Item($folder, $src, $name, $size, $stall, $onBytes) {
  $stageName = '.rs-part'
  $stage = Get-Child $folder $stageName $true
  if (-not $stage) {
    $folder.NewFolder($stageName)
    for ($i = 0; $i -lt 20 -and -not $stage; $i++) { Start-Sleep -Milliseconds 200; $stage = Get-Child $folder $stageName $true }
  }
  if (-not $stage) { throw "FAILED`tthe staging folder could not be made" }
  $staging = $stage.GetFolder
  $stale = Get-Child $staging $name $false
  if ($stale) { [void](Remove-DeviceItems @($stale)) }
  $staging.CopyHere($src, 1556)
  if (-not (Wait-Arrival $staging $name $size $stall $onBytes)) { throw "FAILED`tthe copy stalled or did not reach full size" }
  $old = Get-Child $folder $name $false
  if ($old) { $old.Name = "$name.rs-old" }
  $folder.MoveHere((Get-Child $staging $name $false), 1556)
  $placed = $null
  for ($i = 0; $i -lt 50 -and -not $placed; $i++) { Start-Sleep -Milliseconds 200; $placed = Get-Child $folder $name $false }
  if (-not $placed) {
    $back = Get-Child $folder "$name.rs-old" $false
    if ($back) { $back.Name = $name }
    throw "FAILED`tthe copy could not be put in place"
  }
  $old = Get-Child $folder "$name.rs-old" $false
  if ($old) { [void](Remove-DeviceItems @($old)) }
  return (Size-Of $placed)
}
"""

#: Every result line a script prints starts with one of these and a tab.
EPILOGUE: Final = r"""
} catch {
  $m = "$($_.Exception.Message)"
  if ($m -notmatch "^(UNAVAILABLE|FAILED|MISSING)`t") { $m = "FAILED`t$m" }
  Write-Output $m
  exit 3
}
"""


def _wrap(body: str) -> str:
    return PROLOGUE + "\ntry {\n" + body + EPILOGUE


def parts_env(parts: Sequence[str]) -> str:
    return "\n".join(parts)


ROOT_EXISTS: Final = _wrap(
    r"""
  $st = Resolve-Storage
  if (Resolve-Parts $st $env:RS_PARTS $false) { Write-Output "OK`tyes" } else { Write-Output "OK`tno" }
"""
)

CREATE_ROOT: Final = _wrap(
    r"""
  $st = Resolve-Storage
  if (Resolve-Parts $st $env:RS_PARTS $true) { Write-Output "OK`tyes" } else { Write-Output "FAILED`tnot created" }
"""
)

CAPACITY: Final = _wrap(
    r"""
  $st = Resolve-Storage
  $cap = [int64]$st.ExtendedProperty('System.Capacity')
  $free = [int64]$st.ExtendedProperty('System.FreeSpace')
  Write-Output "OK`t$cap`t$free"
"""
)

FETCH: Final = _wrap(
    r"""
  $st = Resolve-Storage
  $folder = Resolve-Parts $st $env:RS_PARTS $false
  $item = if ($folder) { Get-Child $folder $env:RS_NAME $false } else { $null }
  if (-not $item) { Write-Output "MISSING`t$env:RS_NAME"; exit 0 }
  $target = Join-Path $env:RS_LOCAL $env:RS_NAME
  if (Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target -Recurse -Force }
  $want = Size-Of $item
  $hr = [Mtp]::CopyQuietly($item.PSObject.BaseObject, [string]$env:RS_LOCAL)
  if ($hr -ne 0) { Write-Output ("FAILED`tthe device refused the copy (0x{0:X8})" -f $hr); exit 0 }
  $last = -1; $still = 0.0
  while ($true) {
    Start-Sleep -Milliseconds 500
    $now = if (Test-Path -LiteralPath $target) { (Get-Item -LiteralPath $target).Length } else { -1 }
    if ($now -ge $want) { Write-Output "OK`t$now"; exit 0 }
    if ($now -eq $last) { $still += 0.5 } else { $still = 0.0 }
    $last = $now
    if ($still -ge [double]$env:RS_STALL) { Write-Output "FAILED`tthe fetch stalled"; exit 0 }
  }
"""
)

PUT: Final = _wrap(
    r"""
  $st = Resolve-Storage
  $folder = Resolve-Parts $st $env:RS_PARTS $true
  if (-not $folder) { throw "FAILED`tthe folder could not be made" }
  $size = (Get-Item -LiteralPath $env:RS_SRC).Length
  $landed = Send-Item $folder $env:RS_SRC $env:RS_NAME $size ([double]$env:RS_STALL) $null
  Write-Output "OK`t$landed"
"""
)

DELETE: Final = _wrap(
    r"""
  $st = Resolve-Storage
  $folder = Resolve-Parts $st $env:RS_PARTS $false
  $it = if ($folder) { Get-Child $folder $env:RS_NAME $false } else { $null }
  if (-not $it) { Write-Output "OK`tabsent"; exit 0 }
  [void](Remove-DeviceItems @($it))
  for ($i = 0; $i -lt 25; $i++) {
    Start-Sleep -Milliseconds 200
    if (-not (Get-Child $folder $env:RS_NAME $false)) { Write-Output "OK`tdeleted"; exit 0 }
  }
  Write-Output "FAILED`tstill present after deleting"
"""
)

SCAN: Final = _wrap(
    r"""
  $st = Resolve-Storage
  $roms = Resolve-Parts $st $env:RS_PARTS $false
  if (-not $roms) { Write-Output "MISSING`troot"; exit 0 }
  $only = @{}
  foreach ($n in ($env:RS_SYSTEMS -split "`n" | Where-Object { $_ })) { $only[$n] = $true }
  foreach ($sys in $roms.Items()) {
    if (-not $sys.IsFolder) { continue }
    Write-Output "TOP`t$($sys.Name)"
    if ($env:RS_ALL -ne '1' -and -not $only.ContainsKey($sys.Name)) { continue }
    foreach ($g in $sys.GetFolder.Items()) {
      $kind = if ($g.IsFolder) { 'folder' } else { 'file' }
      Write-Output "ITEM`t$($sys.Name)`t$($g.Name)`t$kind`t$(Size-Of $g)"
    }
  }
  Write-Output "OK`tscanned"
"""
)

LIST: Final = _wrap(
    r"""
  $st = Resolve-Storage
  $i = 0
  foreach ($parts in ($env:RS_PATHS -split "`t")) {
    $f = Resolve-Parts $st $parts $false
    if (-not $f) { Write-Output "ABSENT`t$i" }
    else {
      Write-Output "PRESENT`t$i"
      foreach ($e in $f.Items()) {
        if ($e.IsFolder) { Write-Output "ENTRY`t$i`t$($e.Name)`tfolder`t" }
        else { Write-Output "ENTRY`t$i`t$($e.Name)`tfile`t$(Size-Of $e)" }
      }
    }
    $i++
  }
  Write-Output "OK`tlisted"
"""
)

#: The bulk worker. It reads its plan from a file, reports one line per event,
#: and looks for the cancel file only between items.
RUN: Final = _wrap(
    r"""
  $st = Resolve-Storage
  $rows = @(Get-Content -LiteralPath $env:RS_PLAN -Encoding UTF8 | Where-Object { $_ })
  foreach ($line in $rows) {
    $p = $line -split "`t"
    $i = $p[0]; $action = $p[1]; $parts = $p[2] -replace '/', "`n"; $name = $p[3]
    $size = [int64]$p[5]; $src = $p[6]; $stall = [double]$p[7]
    if (Test-Path -LiteralPath $env:RS_CANCEL) { Write-Output "STOPPED`t$i"; exit 0 }
    Write-Output "START`t$i"
    try {
      if ($action -eq 'remove') {
        $folder = Resolve-Parts $st $parts $false
        $it = if ($folder) { Get-Child $folder $name $false } else { $null }
        if ($it) { [void](Remove-DeviceItems @($it)); Start-Sleep -Milliseconds 500 }
        if ($folder -and (Get-Child $folder $name $false)) { throw "FAILED`tstill present after deleting" }
        Write-Output "DONE`t$i`t"
      } else {
        if (-not (Test-Path -LiteralPath $src)) { throw "FAILED`tnot in the store" }
        $folder = Resolve-Parts $st $parts $true
        if (-not $folder) { throw "FAILED`tthe folder could not be made" }
        # written straight to the console: a function's output is its return value
        $report = { param($n) [Console]::Out.WriteLine("BYTES`t$i`t$n"); [Console]::Out.Flush() }
        $landed = Send-Item $folder $src $name $size $stall $report
        Write-Output "DONE`t$i`t$landed"
      }
    } catch {
      $m = "$($_.Exception.Message)" -replace "[`r`n]", ' '
      if ($m -notmatch "^(UNAVAILABLE|FAILED)`t") { $m = "FAILED`t$m" }
      Write-Output "FAIL`t$i`t$m"
    }
  }
  Write-Output "OK`tfinished"
"""
)
