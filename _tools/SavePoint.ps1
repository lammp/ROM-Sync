<#
.SYNOPSIS
    Save points for D:\Games (Constitution law 4).

.DESCRIPTION
    Every removal or move of library files by Claude runs through this script.
    A save point is a manifest in _tools\rounds\ recording each operation, so a
    round can be rolled back: moves are reversed, recycled files are restored
    from the Windows Recycle Bin by their original path.

    Nothing is ever permanently deleted here. Recycled files stay in the bin
    until Matt empties it. Save points older than -KeepHours (48) are pruned on
    every -List and -Save; pruned manifests go to the bin too.

.EXAMPLE  Save
    .\SavePoint.ps1 -Save -Name round-23-layout -Description "framework layout" `
        -RecycleList list.tsv -MoveList moves.tsv [-WhatIf]
    RecycleList: path<TAB>reason  (one per line; files or folders)
    MoveList:    from<TAB>to      (one per line; files or folders)

.EXAMPLE  List (prunes first, then numbers the survivors, newest first)
    .\SavePoint.ps1 -List

.EXAMPLE  Restore, by number from -List or by id
    .\SavePoint.ps1 -Restore 1 [-WhatIf]

.NOTES
    Manifest format (tab separated, comment lines start with #):
      op    path    bytes   detail
      recycle  <original path>   <bytes>  <reason>
      move     <from>            <bytes>  <to>
    A recycled folder is one row and one Recycle Bin item; restoring it puts
    the whole folder back.
#>
[CmdletBinding()]
param(
    [switch] $Save,
    [switch] $List,
    [string] $Restore,
    [string] $Name,
    [string] $Description = '',
    [string] $RecycleList,
    [string] $MoveList,
    [switch] $WhatIf,
    [int]    $KeepHours = 48
)

$ErrorActionPreference = 'Stop'
$Root      = 'D:\Games'
$RoundsDir = Join-Path $PSScriptRoot 'rounds'
$OffLimits = @('D:\Games\_torrents\_incomplete', 'D:\Games\Downloading', 'D:\Games\$RECYCLE.BIN', $RoundsDir)
# Recycle Bin quota for D:, read live rather than assumed: a hardcoded cap silently approves a round
# that Windows then deletes permanently. MaxCapacity absent means Windows is on its own default,
# which is 10% of the first 40 GB of the volume plus 5% of the rest.
function BinCapMB {
    $dev  = (Get-CimInstance Win32_Volume -Filter "DriveLetter='D:'").DeviceID
    $guid = $dev.Substring($dev.IndexOf('{'), $dev.IndexOf('}') - $dev.IndexOf('{') + 1)
    $key  = "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\BitBucket\\Volume\\$guid"
    $v    = (Get-ItemProperty -Path $key -Name MaxCapacity -ErrorAction SilentlyContinue).MaxCapacity
    if ($v) { return [int64] $v }
    $gb = (Get-Volume -DriveLetter D).Size / 1GB
    return [int64] ((40 * 0.10 + ($gb - 40) * 0.05) * 1024)
}
$BinCapMB = BinCapMB
New-Item -ItemType Directory -Force $RoundsDir | Out-Null
Add-Type -AssemblyName Microsoft.VisualBasic

function Norm([string] $p) { return [IO.Path]::GetFullPath($p).TrimEnd('\') }
function InsideRoot([string] $p) { return $p.ToLowerInvariant().StartsWith(($Root + '\').ToLowerInvariant()) }
function OffLimits([string] $p) {
    $l = $p.ToLowerInvariant()
    foreach ($o in $OffLimits) { $ol = $o.ToLowerInvariant(); if ($l -eq $ol -or $l.StartsWith($ol + '\')) { return $true } }
    return $false
}
function SizeOf([string] $p) {
    if (Test-Path -LiteralPath $p -PathType Container) {
        $s = Get-ChildItem -LiteralPath $p -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum
        return [int64]($s.Sum)
    }
    return (Get-Item -LiteralPath $p -Force).Length
}
function BinUsedBytes {
    $s = Get-ChildItem 'D:\$Recycle.Bin' -Force -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum
    return [int64]($s.Sum)
}
function SendToBin([string] $p) {
    if (Test-Path -LiteralPath $p -PathType Container) {
        [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteDirectory($p, 'OnlyErrorDialogs', 'SendToRecycleBin')
    } else {
        [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile($p, 'OnlyErrorDialogs', 'SendToRecycleBin')
    }
}
function ReadTsv([string] $path, [int] $cols) {
    $rows = @()
    if (-not $path) { return $rows }
    foreach ($line in [IO.File]::ReadAllLines($path, [Text.Encoding]::UTF8)) {
        if (-not $line.Trim() -or $line.StartsWith('#')) { continue }
        $p = $line -split "`t", $cols
        while ($p.Count -lt $cols) { $p += '' }
        # objects, not nested arrays: a one-row nested array unrolls into its columns
        $rows += [pscustomobject]@{ c0 = $p[0]; c1 = $p[1] }
    }
    return $rows
}
function ReadManifest([string] $file) {
    $m = [ordered]@{ id = [IO.Path]::GetFileNameWithoutExtension($file); name = ''; description = ''; created = $null; rows = @() }
    foreach ($line in [IO.File]::ReadAllLines($file, [Text.Encoding]::UTF8)) {
        if ($line -like '# name:*')        { $m.name = ($line -replace '^# name:\s*', ''); continue }
        if ($line -like '# description:*') { $m.description = ($line -replace '^# description:\s*', ''); continue }
        if ($line -like '# created:*')     { $m.created = [datetime]::ParseExact(($line -replace '^# created:\s*', ''), 'yyyy-MM-dd HH:mm:ss', $null); continue }
        if (-not $line.Trim() -or $line.StartsWith('#') -or $line.StartsWith('op' + "`t")) { continue }
        $p = $line -split "`t", 4
        $m.rows += [pscustomobject]@{ op = $p[0]; path = $p[1]; bytes = [int64]$p[2]; detail = $(if ($p.Count -gt 3) { $p[3] } else { '' }) }
    }
    if (-not $m.created) { $m.created = (Get-Item -LiteralPath $file).CreationTime }
    return $m
}
function Prune {
    $cut = (Get-Date).AddHours(-$KeepHours); $n = 0
    foreach ($f in (Get-ChildItem -LiteralPath $RoundsDir -Filter *.tsv -File)) {
        $m = ReadManifest $f.FullName
        if ($m.created -lt $cut) { SendToBin $f.FullName; $n++ }
    }
    return $n
}
function SavePoints {
    $out = @()
    foreach ($f in (Get-ChildItem -LiteralPath $RoundsDir -Filter *.tsv -File)) { $out += ReadManifest $f.FullName }
    return @($out | Sort-Object { $_.created } -Descending)
}

# ------------------------------------------------------------------ LIST
if ($List) {
    $pruned = Prune
    $sps = @(SavePoints)
    if ($pruned) { Write-Host "pruned $pruned save point(s) older than $KeepHours h (manifests sent to the Recycle Bin)" }
    if (-not $sps) { Write-Host "no save points in the last $KeepHours h"; return }
    Write-Host ''
    Write-Host ('{0,3}  {1,-16}  {2,-32}  {3,9}  {4,8}  {5,-14}  {6}' -f '#', 'CREATED', 'ID', 'ITEMS', 'GB', 'OPS', 'DESCRIPTION')
    $i = 0
    foreach ($m in $sps) {
        $i++
        $rec = @($m.rows | Where-Object op -eq 'recycle').Count; $mv = @($m.rows | Where-Object op -eq 'move').Count
        $gb = [math]::Round((($m.rows | Measure-Object bytes -Sum).Sum) / 1GB, 2)
        $ops = @(); if ($rec) { $ops += "recycle $rec" }; if ($mv) { $ops += "move $mv" }
        Write-Host ('{0,3}  {1,-16:yyyy-MM-dd HH:mm}  {2,-32}  {3,9}  {4,8}  {5,-14}  {6}' -f $i, $m.created, $m.id, $m.rows.Count, $gb, ($ops -join ', '), $m.description)
    }
    Write-Host ''
    Write-Host 'restore one with:  SavePoint.ps1 -Restore <#>   (add -WhatIf to preview)'
    return
}

# ------------------------------------------------------------------ SAVE
if ($Save) {
    if (-not $Name) { throw 'Save needs -Name' }
    $slug = ($Name.ToLowerInvariant() -replace '[^a-z0-9]+', '-').Trim('-')
    $recycles = @(ReadTsv $RecycleList 2)
    $moves    = @(ReadTsv $MoveList 2)
    if (-not $recycles -and -not $moves) { throw 'Save needs -RecycleList and/or -MoveList with at least one row' }

    # --- verify everything before touching anything
    $errors = @(); $plan = @(); $bytesToBin = [int64]0
    foreach ($r in $recycles) {
        $p = Norm $r.c0
        if (-not (Test-Path -LiteralPath $p)) { $errors += "recycle: not found: $p"; continue }
        if (-not (InsideRoot $p)) { $errors += "recycle: outside $Root : $p"; continue }
        if (OffLimits $p) { $errors += "recycle: off-limits: $p"; continue }
        $b = SizeOf $p; $bytesToBin += $b
        $plan += [pscustomobject]@{ op = 'recycle'; path = $p; bytes = $b; detail = $r.c1 }
    }
    $dests = @{}
    foreach ($mv in $moves) {
        $from = Norm $mv.c0; $to = Norm $mv.c1
        if (-not (Test-Path -LiteralPath $from)) { $errors += "move: source not found: $from"; continue }
        if (-not (InsideRoot $from) -or -not (InsideRoot $to)) { $errors += "move: outside $Root : $from -> $to"; continue }
        if ((OffLimits $from) -or (OffLimits $to)) { $errors += "move: off-limits: $from -> $to"; continue }
        if (Test-Path -LiteralPath $to) { $errors += "move: destination exists: $to"; continue }
        if ($dests.ContainsKey($to.ToLowerInvariant())) { $errors += "move: two sources share a destination: $to"; continue }
        $dests[$to.ToLowerInvariant()] = 1
        $plan += [pscustomobject]@{ op = 'move'; path = $from; bytes = (SizeOf $from); detail = $to }
    }
    if ($bytesToBin -gt 0) {
        $used = BinUsedBytes
        if (($used + $bytesToBin) -gt ($BinCapMB * 1MB)) {
            $errors += ("recycle: Recycle Bin would exceed its {0} GB quota on D: (in use {1} GB, this round {2} GB); Windows would delete permanently instead" -f [math]::Round($BinCapMB/1024), [math]::Round($used/1GB,1), [math]::Round($bytesToBin/1GB,1))
        }
    }
    if ($errors) {
        Write-Host "SAVE REFUSED - $($errors.Count) check(s) failed, nothing was changed:"
        $errors | ForEach-Object { Write-Host "  $_" }
        exit 1
    }

    $stamp = Get-Date
    $id = '{0:yyyyMMdd-HHmm}-{1}' -f $stamp, $slug
    $file = Join-Path $RoundsDir "$id.tsv"
    if ($WhatIf) {
        Write-Host "would create save point $id with $($plan.Count) operation(s):"
        $plan | ForEach-Object { Write-Host ("  {0,-8} {1}  {2}" -f $_.op, $_.path, $(if ($_.op -eq 'move') { '-> ' + $_.detail } else { '(' + $_.detail + ')' })) }
        return
    }

    # --- execute, recording each operation as it succeeds
    $lines = @("# name: $Name", "# description: $Description", ('# created: {0:yyyy-MM-dd HH:mm:ss}' -f $stamp), "op`tpath`tbytes`tdetail")
    [IO.File]::WriteAllLines($file, $lines, [Text.Encoding]::UTF8)
    $done = 0; $failed = 0
    foreach ($op in $plan) {
        try {
            if ($op.op -eq 'move') {
                $parent = Split-Path -Parent $op.detail
                if (-not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Force $parent | Out-Null }
                Move-Item -LiteralPath $op.path -Destination $op.detail
            } else {
                SendToBin $op.path
            }
            [IO.File]::AppendAllText($file, ("{0}`t{1}`t{2}`t{3}`n" -f $op.op, $op.path, $op.bytes, $op.detail), [Text.Encoding]::UTF8)
            $done++
        } catch {
            Write-Warning "failed: $($op.op) $($op.path) :: $($_.Exception.Message)"; $failed++
        }
    }
    $null = Prune
    Write-Host ("save point {0}: {1} done, {2} failed, {3} GB" -f $id, $done, $failed, [math]::Round((($plan | Measure-Object bytes -Sum).Sum)/1GB, 2))
    Write-Host "manifest: $file"
    return
}

# ------------------------------------------------------------------ RESTORE
if ($Restore) {
    $sps = @(SavePoints)
    $m = $null
    if ($Restore -match '^\d+$') { $n = [int]$Restore; if ($n -ge 1 -and $n -le $sps.Count) { $m = $sps[$n - 1] } }
    if (-not $m) { $m = $sps | Where-Object { $_.id -eq ($Restore -replace '\.tsv$', '') } | Select-Object -First 1 }
    if (-not $m) { Write-Error "no save point '$Restore' (run -List)"; return }
    Write-Host "restoring $($m.id): $($m.description)"

    $restored = 0; $failed = 0; $missing = @()
    # moves back, last first
    $movesBack = @($m.rows | Where-Object op -eq 'move'); [array]::Reverse($movesBack)
    foreach ($mv in $movesBack) {
        if (-not (Test-Path -LiteralPath $mv.detail)) { $missing += "move: no longer at $($mv.detail)"; continue }
        if (Test-Path -LiteralPath $mv.path) { Write-Warning "exists, skipped: $($mv.path)"; $failed++; continue }
        if ($WhatIf) { Write-Host "would move back: $($mv.detail) -> $($mv.path)"; $restored++; continue }
        try { $parent = Split-Path -Parent $mv.path; if (-not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Force $parent | Out-Null }
              Move-Item -LiteralPath $mv.detail -Destination $mv.path; $restored++ }
        catch { Write-Warning "failed: $($mv.detail) :: $($_.Exception.Message)"; $failed++ }
    }
    # recycled items back from the bin, matched on original full path
    $wanted = @{}
    foreach ($r in ($m.rows | Where-Object op -eq 'recycle')) { $wanted[$r.path.ToLowerInvariant()] = $r }
    if ($wanted.Count) {
        $shell = New-Object -ComObject Shell.Application
        $bin = $shell.Namespace(0xA)
        if (-not $bin) { Write-Error 'Could not open the Recycle Bin namespace.'; return }
        $seen = @{}
        foreach ($item in @($bin.Items())) {
            $origDir = $bin.GetDetailsOf($item, 1)
            if (-not $origDir) { continue }
            $full = (Join-Path $origDir $item.Name).ToLowerInvariant()
            if (-not $wanted.ContainsKey($full)) { continue }
            if ($seen.ContainsKey($full)) { continue }
            $seen[$full] = $true
            if ($WhatIf) { Write-Host "would restore: $origDir\$($item.Name)"; $restored++; continue }
            $verb = $item.Verbs() | Where-Object { ($_.Name -replace '&', '') -match '^(Restore|Put back)' } | Select-Object -First 1
            if ($verb) { try { $verb.DoIt(); $restored++ } catch { Write-Warning "failed: $full :: $($_.Exception.Message)"; $failed++ } }
            else { Write-Warning "no Restore verb for: $full"; $failed++ }
        }
        foreach ($k in $wanted.Keys) { if (-not $seen.ContainsKey($k)) { $missing += "recycle: not in Recycle Bin: $($wanted[$k].path)" } }
    }
    Write-Host ''
    Write-Host ("restored : {0}" -f $restored)
    Write-Host ("failed   : {0}" -f $failed)
    Write-Host ("missing  : {0}" -f $missing.Count)
    $missing | ForEach-Object { Write-Host "  $_" }
    return
}

Write-Host 'usage: SavePoint.ps1 -Save -Name <n> [-Description <d>] [-RecycleList <tsv>] [-MoveList <tsv>] [-WhatIf] | -List | -Restore <#|id> [-WhatIf]'
