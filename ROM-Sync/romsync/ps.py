"""Running PowerShell from the app.

Everything that touches a USB (MTP) device goes through the Windows shell
namespace, which needs an STA thread, so those scripts run in their own
powershell.exe. Scripts are written under the app's data folder, never C:.
"""
import json
import os
import subprocess
import sys
import tempfile

from . import db

# PowerShell prologue shared by every MTP script: resolve a device and storage to a
# Folder object, plus the IFileOperation delete interop (FolderItem.InvokeVerb is a
# no-op on MTP items; this route is the one that works).
MTP_PROLOGUE = r'''
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
  [DllImport("ole32.dll")] static extern void CoTaskMemFree(IntPtr pv);
  static readonly Guid CLSID_FileOperation = new Guid("3AD05575-8857-4850-9277-11B85BDB8E09");
  static readonly Guid IID_IShellItem = new Guid("43826D1E-E718-42EE-BC55-A1E261C37BFE");
  const uint FOF_NO_UI = 0x0004 | 0x0010 | 0x0200 | 0x0400;
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

function Resolve-Storage($deviceName, $storageName) {
  $shell = New-Object -ComObject Shell.Application
  $device = $shell.NameSpace(17).Items() | Where-Object { $_.Name -eq $deviceName }
  if (-not $device) { throw "Device '$deviceName' is not connected." }
  $stores = @($device.GetFolder.Items())
  if ($stores.Count -eq 0) { throw "'$deviceName' exposes no storage. Set its USB mode to File Transfer." }
  if ($storageName) {
    $st = $stores | Where-Object { $_.Name -eq $storageName }
    if (-not $st) { throw "'$deviceName' has no storage named '$storageName'." }
  } else { $st = $stores[0] }
  return $st
}

# Walk a path under a storage. $create makes missing segments. Returns the Folder.
function Resolve-Path-OnDevice($storageItem, $relPath, $create) {
  $folder = $storageItem.GetFolder
  foreach ($seg in ($relPath -split '[\\/]' | Where-Object { $_ })) {
    $item = Get-Child $folder $seg $true
    if (-not $item -and $create) {
      $folder.NewFolder($seg); Start-Sleep -Milliseconds 800
      $item = Get-Child $folder $seg $true
    }
    if (-not $item) { return $null }
    $folder = $item.GetFolder
  }
  return $folder
}

function Size-Of($item) {
  $sz = 0
  try { $sz = [int64]$item.ExtendedProperty('System.Size') } catch {}
  return $sz
}
'''


def run(script_text, env_extra=None, timeout=None, background=False, log=None, name="job"):
    """Run a PowerShell script (STA). Foreground returns CompletedProcess; background returns Popen."""
    if sys.platform != "win32":
        raise RuntimeError("Device access is only available on Windows.")
    data = db.data_dir()
    os.makedirs(os.path.join(data, "tmp"), exist_ok=True)
    if background:
        script = os.path.join(data, "tmp", f"{name}.ps1")
    else:
        fd, script = tempfile.mkstemp(suffix=".ps1", dir=os.path.join(data, "tmp"))
        os.close(fd)
    with open(script, "w", encoding="utf-8-sig", newline="\r\n") as f:
        f.write(script_text)
    env = dict(os.environ)
    env.update(env_extra or {})
    cmd = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-STA", "-File", script]
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    if background:
        logf = open(log or os.path.join(data, "logs", f"{name}.log"), "w")
        return subprocess.Popen(cmd, env=env, stdout=logf, stderr=subprocess.STDOUT, creationflags=flags)
    try:
        return subprocess.run(cmd, env=env, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout, creationflags=flags)
    finally:
        try:
            os.unlink(script)
        except OSError:
            pass


def run_json(script_text, env_extra=None, timeout=120):
    r = run(script_text, env_extra, timeout=timeout)
    out = (r.stdout or "").strip()
    if r.returncode != 0 and not out:
        raise RuntimeError((r.stderr or "PowerShell failed").strip()[:2000])
    try:
        return json.loads(out) if out else None
    except ValueError:
        raise RuntimeError("Unreadable PowerShell output: " + out[:500])
