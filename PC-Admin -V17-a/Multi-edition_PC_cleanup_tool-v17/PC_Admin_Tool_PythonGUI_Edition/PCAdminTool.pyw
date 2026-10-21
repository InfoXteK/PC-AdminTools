#!/usr/bin/env python3
"""
================================================================================
  PC Admin & Performance Tool  v3.7  -- Native Python GUI Edition (Tkinter)
  (c) 2024-2026 Abdullah | All Rights Reserved
  Contact: abuabdullah.be@outlook.com
  Unauthorized copying, modification or redistribution is strictly prohibited.

  Operations ported directly from the Docker/Flask Web-Service edition
  (app.py) -- same 67 remote PowerShell operations (36 original + 28 added
  in v3.0's "Power Recycle"/"Remote Tools" categories + 3 added in v3.2's
  network-drive-mapping trio), same PSRP execution model, packaged here
  as a single-file Tkinter desktop app (no browser, no Docker, no server
  -- just Python + pypsrp).

  v3.0: 12 of the 64 operations take a runtime parameter (an IP, an
  adapter name, a device Instance ID, ...) instead of running a fixed
  script -- see PARAM_VALIDATORS / validate_and_substitute().
  rt_open_computer_management is handled specially: it launches mmc.exe
  locally on THIS machine (connected to the target) instead of going
  through the remote PSRP session, since a remote, non-interactive
  session has no desktop to show a GUI app on.

  v3.1: added a "bool" param kind (a real Checkbutton, not a text field)
  and an "Auto-Restart" checkbox on the three operations that previously
  restarted unconditionally as a side effect of their real work
  (pr_full_soft_recycle, rt_rename_pc_domain, rt_rename_pc_workgroup).
  Default stays checked (unchanged behavior); unchecked, the operation
  still does its real work but skips the trailing restart.

  v3.2 (port 3032 -> 3033):
    FIX  The "servicename" validator rejected every service Name that contains
         a space, so real services such as "ManageEngine UEMS - Agent" showed
         "looks invalid" and could not be restarted. It now accepts letters,
         digits, spaces and _ . - $ # + ( ) (max 256 chars). The command body
         uses a single-quoted PowerShell literal now, so $ and ( ) inside a
         name can never expand or execute.
    NEW  Per-user network drive mapping (Remote Tools): rt_map_network_drive,
         rt_unmap_network_drive, rt_list_mapped_drives -- 67 operations total.
         A drive mapped from a WinRM session only exists inside that session,
         so the mapping is written into the target user's own registry hive
         (HKEY_USERS, "Network" key; NTUSER.DAT is loaded temporarily if the
         user is signed out) and, when the user is signed in, connected live
         through a one-shot scheduled task that runs inside the user's own
         session. New param kinds: uncpath, mapdrive, useraccount. New param
         attribute "wide" (input takes the full row instead of sharing a
         half-width column -- used by SHARE_PATH, a long UNC path).
    FIX  List All Services sizes its Name column to the longest name.

  v3.3: no functional change in this file -- fixed for consistency of the
  synchronized version number across all three editions. The actual fix
  this version ships is in the Web edition's launcher scripts, plus a
  proactive check of install_and_run.bat (this edition's own launcher)
  for the same class of issue -- see the README for the full explanation.

  v3.4: no functional change in this file either -- the actual fix this
  version ships is in the Web edition's pcadmintool_service.py and its
  two launcher scripts (a pywin32 exception-handling gap that could
  never be tested on Linux, plus much more detailed diagnostics) --
  see the Web edition's README for the full explanation.

  v3.5: no functional change in this file -- the actual fixes this version
  ships are in the Web edition (a false-positive in v3.4's own WindowsApps
  detection, and Computer Management now actually launching locally instead
  of only printing text -- this edition already did the latter correctly)
  -- see the Web edition's README for the full explanation.

  v3.6: one functional fix in this file -- Network Adapter Speed and Traffic
  Stats threw a conversion error on real adapters (LinkSpeed is TEXT such
  as 1 Gbps; it now uses the numeric Speed property). Otherwise the fix
  this version ships is in every edition's LAUNCHER script (an unescaped closing
  parenthesis inside a block made cmd.exe abort the batch file at parse
  time, which closed the window with no message). This edition's own
  install_and_run.bat had that defect and is rewritten, and its title
  line no longer runs the word Performance as a command. See the README.

  v3.7: same functional changes as the Web edition's v3.7 entry, ported
  1:1 -- PC rename fixed on domain-joined targets (explicit domain credential
  built inside the remote session, WMI fallback, decoded error codes), detached
  run-and-reconnect for network-changing and very long tasks, reboot-class tasks
  treated as expected, VSS storage resize, DISM RestoreHealth / component
  cleanup, CIM replacements for WMIC, CHKDSK online scan, and the new
  "Admin Consoles" category (85 operations in total). These consoles open on
  THIS PC, connected to the target. See the Web edition's README.
================================================================================
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pypsrp.client import Client
from pypsrp.exceptions import AuthenticationError, WinRMTransportError, WSManFaultError
import requests.exceptions
import threading
import queue
import socket
import datetime
import re
import os
import time
import sys
import subprocess
import platform
import base64
import secrets
from pathlib import Path

VER = "v3.7  Native Python GUI Edition (Tkinter)"
COPYRIGHT = ("(c) 2024-2026 Abdullah | PC Admin & Performance Tool v3.7 | "
             "All Rights Reserved | abuabdullah.be@outlook.com")
COPYRIGHT_LONG = ("(c) 2024-2026 Abdullah | PC Admin & Performance Tool v3.7 | "
                   "Native Python GUI Edition | All Rights Reserved | "
                   "abuabdullah.be@outlook.com")

BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) \
    if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "PC_Admin_Logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ══════════════════════════════════════════════════════════════════════════
#  DARK NAVY THEME  (matches the PowerShell GUI edition palette)
# ══════════════════════════════════════════════════════════════════════════
BG    = "#111827"
PNL   = "#1a2438"
CARD  = "#1f2e47"
CRD2  = "#263654"
BDR   = "#2e4368"
BDR2  = "#3a5580"
ACC   = "#1d4ed8"
CYAN  = "#22d3ee"
GRN   = "#22c55e"
RED   = "#ef4444"
YEL   = "#f59e0b"
TXT   = "#d1dff0"
TXTB  = "#eef2ff"
TXDD  = "#5c7a9a"
LOGBG = "#090f1a"
HDRB  = "#08111e"
DIM   = "#2d4a68"
OUT2  = "#8ab0cc"

# ══════════════════════════════════════════════════════════════════════════
#  OPERATIONS -- ported verbatim from app.py (Web-Service Edition, v2.0)
#  Same ids, same labels, same categories, same PowerShell command bodies.
# ══════════════════════════════════════════════════════════════════════════
OPERATIONS = [

    # ─── CLEANUP ────────────────────────────────────────────────────────
    {
        "id": "clear_user_temp",
        "label": "Clear All Users' Temp Files",
        "category": "Cleanup",
        "description": "Removes %TEMP% from every user profile, incl. SYSTEM/service accounts",
        "command": r"""
Write-Output "  Running as : $([Security.Principal.WindowsIdentity]::GetCurrent().Name)"
Write-Output "  Computer   : $env:COMPUTERNAME"
$totalFreed = 0
$denied = 0
$profCount = 0
$users = Get-ChildItem 'C:\Users' -Directory -Force -ErrorAction SilentlyContinue
if (-not $users) {
    Write-Output "  WARNING: C:\Users not found or not accessible"
} else {
    Write-Output "  Found $($users.Count) user profile folder(s) under C:\Users"
    foreach ($user in $users) {
        if ($user.Name -in @("Default","Default User","Public","All Users")) { continue }
        $profCount++
        $path = "$($user.FullName)\AppData\Local\Temp"
        if (Test-Path $path) {
            $items = Get-ChildItem $path -Recurse -Force -ErrorAction SilentlyContinue
            $sizeBefore = ($items | Measure-Object -Property Length -Sum -ErrorAction SilentlyContinue).Sum
            if (-not $sizeBefore) { $sizeBefore = 0 }
            $before = $items.Count
            $items | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue -ErrorVariable delErrs
            $freed = [math]::Round($sizeBefore / 1MB, 2)
            $totalFreed += $freed
            if ($delErrs -and $delErrs.Count -gt 0) {
                $denied++
                Write-Output "  [$($user.Name)] Freed ${freed} MB  ($($delErrs.Count) file(s) skipped -- in use / access denied)"
            } else {
                Write-Output "  [$($user.Name)] Freed ${freed} MB  ($before items)"
            }
        } else {
            Write-Output "  [$($user.Name)] No temp folder (profile never fully loaded)"
        }
    }
}
$svcProfiles = @(
    @{Name="SYSTEM";         Path="C:\Windows\System32\config\systemprofile\AppData\Local\Temp"},
    @{Name="LocalService";   Path="C:\Windows\ServiceProfiles\LocalService\AppData\Local\Temp"},
    @{Name="NetworkService"; Path="C:\Windows\ServiceProfiles\NetworkService\AppData\Local\Temp"}
)
foreach ($sp in $svcProfiles) {
    if (Test-Path $sp.Path) {
        $items = Get-ChildItem $sp.Path -Recurse -Force -ErrorAction SilentlyContinue
        $sizeBefore = ($items | Measure-Object -Property Length -Sum -ErrorAction SilentlyContinue).Sum
        if (-not $sizeBefore) { $sizeBefore = 0 }
        $items | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue -ErrorVariable svcErrs
        $freed = [math]::Round($sizeBefore / 1MB, 2)
        $totalFreed += $freed
        $note = if ($svcErrs -and $svcErrs.Count -gt 0) { " ($($svcErrs.Count) file(s) skipped -- in use)" } else { "" }
        Write-Output "  [$($sp.Name)] Freed ${freed} MB$note"
        $profCount++
    }
}
Write-Output "  ------------------------------------------------"
Write-Output "  Profiles processed: $profCount   |   TOTAL FREED: $totalFreed MB"
if ($denied -gt 0) { Write-Output "  NOTE: $denied profile(s) had files in use and were partially skipped (normal for the logged-in user's active session)" }
""",
        "danger": False,
    },
    {
        "id": "clear_windows_temp",
        "label": "Clear Windows System Temp (C:\\Windows\\Temp)",
        "category": "Cleanup",
        "description": "Deletes files in the Windows system temp directory",
        "command": r"""
$path = "C:\Windows\Temp"
if (-not (Test-Path $path)) { Write-Output "  Path not found: $path"; return }
$items  = Get-ChildItem $path -Recurse -ErrorAction SilentlyContinue
$count  = $items.Count
$size   = ($items | Measure-Object -Property Length -Sum -ErrorAction SilentlyContinue).Sum
if (-not $size) { $size = 0 }
$items | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Write-Output "  Deleted $count items | Freed: $([math]::Round($size/1MB,2)) MB"
""",
        "danger": False,
    },
    {
        "id": "clear_prefetch",
        "label": "Clear Windows Prefetch Files",
        "category": "Cleanup",
        "description": "Removes .pf files from C:\\Windows\\Prefetch",
        "command": r"""
$path = "C:\Windows\Prefetch"
if (-not (Test-Path $path)) { Write-Output "  Prefetch folder not found"; return }
$files = Get-ChildItem $path -Filter "*.pf" -ErrorAction SilentlyContinue
$size  = ($files | Measure-Object -Property Length -Sum -ErrorAction SilentlyContinue).Sum
if (-not $size) { $size = 0 }
$files | Remove-Item -Force -ErrorAction SilentlyContinue
Write-Output "  Removed $($files.Count) prefetch files | Freed: $([math]::Round($size/1MB,2)) MB"
""",
        "danger": False,
    },
    {
        "id": "clear_thumbnail_cache",
        "label": "Clear Thumbnail Cache (All Users)",
        "category": "Cleanup",
        "description": "Deletes thumbcache_*.db from all user Explorer profiles",
        "command": r"""
$totalFreed = 0
$users = Get-ChildItem 'C:\Users' -Directory -ErrorAction SilentlyContinue
if (-not $users) { Write-Output "  WARNING: Cannot enumerate C:\Users"; return }
foreach ($user in $users) {
    $path = "$($user.FullName)\AppData\Local\Microsoft\Windows\Explorer"
    if (Test-Path $path) {
        $files = Get-ChildItem $path -Filter "thumbcache_*.db" -ErrorAction SilentlyContinue
        $size  = ($files | Measure-Object -Property Length -Sum -ErrorAction SilentlyContinue).Sum
        if (-not $size) { $size = 0 }
        $files | Remove-Item -Force -ErrorAction SilentlyContinue
        $freed = [math]::Round($size/1MB,2)
        $totalFreed += $freed
        Write-Output "  [$($user.Name)] Removed $($files.Count) files | Freed: ${freed} MB"
    }
}
Write-Output "  Total thumbnail cache freed: $totalFreed MB"
""",
        "danger": False,
    },
    {
        "id": "clear_wu_cache",
        "label": "Clear Windows Update Download Cache",
        "category": "Cleanup",
        "description": "Stops WU/BITS, clears SoftwareDistribution\\Download, restarts services",
        "command": r"""
Write-Output "  Stopping Windows Update & BITS services..."
Stop-Service wuauserv -Force -ErrorAction SilentlyContinue
Stop-Service bits     -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
$path = "C:\Windows\SoftwareDistribution\Download"
if (Test-Path $path) {
    $size = (Get-ChildItem $path -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
    if (-not $size) { $size = 0 }
    Remove-Item "$path\*" -Recurse -Force -ErrorAction SilentlyContinue
    Write-Output "  Cache cleared | Freed: $([math]::Round($size/1MB,2)) MB"
} else { Write-Output "  WU cache path not found" }
Start-Service wuauserv -ErrorAction SilentlyContinue
Start-Service bits     -ErrorAction SilentlyContinue
Write-Output "  Windows Update & BITS services restarted"
""",
        "danger": False,
    },
    {
        "id": "flush_dns",
        "label": "Flush DNS Resolver Cache",
        "category": "Cleanup",
        "description": "SAFE: Clears local DNS cache + /registerdns to preserve network connectivity",
        "command": r"""
Write-Output "  SAFE FLUSH -- local DNS cache only"
$before = @(Get-DnsClientCache -ErrorAction SilentlyContinue).Count
Write-Output "  Entries before : $before"
Clear-DnsClientCache -ErrorAction SilentlyContinue
ipconfig /flushdns 2>&1 | Out-Null
ipconfig /registerdns 2>&1 | Out-Null
$after = @(Get-DnsClientCache -ErrorAction SilentlyContinue).Count
Write-Output "  Entries after  : $after"
$gw = (Get-NetIPConfiguration -ErrorAction SilentlyContinue | Where-Object {$_.IPv4DefaultGateway} | Select-Object -First 1).IPv4DefaultGateway.NextHop
if ($gw) {
    $ping = Test-NetConnection -ComputerName $gw -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
    $gwStatus = if ($ping.PingSucceeded) { "REACHABLE" } else { "check connectivity" }
    Write-Output "  Gateway $gw : $gwStatus"
}
Write-Output "  DNS flushed safely -- domain connectivity preserved"
""",
        "danger": True,
    },
    {
        "id": "clear_browser_cache",
        "label": "Clear Browser Caches (Chrome / Edge / Firefox)",
        "category": "Cleanup",
        "description": "Purges browser cache folders for all user profiles",
        "command": r"""
$totalFreed = 0
$browsers = @{
    "Google Chrome"  = "\AppData\Local\Google\Chrome\User Data\Default\Cache"
    "Microsoft Edge" = "\AppData\Local\Microsoft\Edge\User Data\Default\Cache"
}
$users = Get-ChildItem 'C:\Users' -Directory -ErrorAction SilentlyContinue
if (-not $users) { Write-Output "  WARNING: Cannot enumerate C:\Users"; return }
foreach ($user in $users) {
    foreach ($b in $browsers.GetEnumerator()) {
        $p = "$($user.FullName)$($b.Value)"
        if (Test-Path $p) {
            $size = (Get-ChildItem $p -Recurse -EA SilentlyContinue | Measure-Object Length -Sum).Sum
            if (-not $size) { $size = 0 }
            Remove-Item "$p\*" -Recurse -Force -EA SilentlyContinue
            $freed = [math]::Round($size/1MB,2); $totalFreed += $freed
            Write-Output "  [$($user.Name)] $($b.Key): Freed ${freed} MB"
        }
    }
    # Firefox
    $ffBase = "$($user.FullName)\AppData\Local\Mozilla\Firefox\Profiles"
    if (Test-Path $ffBase) {
        Get-ChildItem $ffBase -Directory -EA SilentlyContinue | foreach {
            $cache = "$($_.FullName)\cache2"
            if (Test-Path $cache) {
                $size = (Get-ChildItem $cache -Recurse -EA SilentlyContinue | Measure-Object Length -Sum).Sum
                if (-not $size) { $size = 0 }
                Remove-Item "$cache\*" -Recurse -Force -EA SilentlyContinue
                $freed = [math]::Round($size/1MB,2); $totalFreed += $freed
                Write-Output "  [$($user.Name)] Firefox: Freed ${freed} MB"
            }
        }
    }
}
Write-Output "  TOTAL browser cache freed: $totalFreed MB"
""",
        "danger": False,
    },
    {
        "id": "clear_event_logs",
        "label": "Clear Windows Event Logs",
        "category": "Cleanup",
        "description": "Clears Application, System, and Setup logs; skips Security if >100k entries",
        "command": r"""
$logs = @("Application","System","Security","Setup")
foreach ($log in $logs) {
    try {
        $count = 0
        try { $li = Get-WinEvent -ListLog $log -ErrorAction SilentlyContinue; if ($li) { $count = $li.RecordCount } } catch {}
        if ($log -eq "Security" -and $count -gt 100000) {
            Write-Output "  SKIPPED: $log ($count entries) -- too large, would hang session"
            continue
        }
        wevtutil cl "$log" 2>$null
        Write-Output "  Cleared: $log ($count entries)"
    } catch { Write-Output "  Skipped: $log" }
}
""",
        "danger": False,
    },
    {
        "id": "empty_recycle_bin",
        "label": "Empty Recycle Bin (All Drives & Users)",
        "category": "Cleanup",
        "description": "Permanently empties the Recycle Bin on all drives",
        "command": r"""
try {
    $shell = New-Object -ComObject Shell.Application
    $rb = $shell.Namespace(0xA)
    $items = $rb.Items()
    $count = ($items | Measure-Object).Count
    Clear-RecycleBin -Force -ErrorAction Stop
    Write-Output "  Recycle Bin emptied: $count items removed"
} catch { Write-Output "  Recycle Bin already empty or access error: $_" }
""",
        "danger": True,
    },
    {
        "id": "disk_cleanup",
        "label": "Run Disk Cleanup Utility (cleanmgr)",
        "category": "Cleanup",
        "description": "Runs Windows built-in Disk Cleanup silently with all categories",
        "command": r"""
Write-Output "  Configuring Disk Cleanup categories..."
$regBase = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\VolumeCaches"
$keys = Get-ChildItem $regBase -ErrorAction SilentlyContinue
$count = 0
foreach ($key in $keys) {
    Set-ItemProperty -Path $key.PSPath -Name StateFlags0099 -Value 2 -ErrorAction SilentlyContinue
    $count++
}
Write-Output "  Configured $count cleanup categories"
Write-Output "  Launching cleanmgr (max wait: 10 minutes)..."
$proc = Start-Process cleanmgr -ArgumentList "/sagerun:99" -WindowStyle Hidden -PassThru -ErrorAction SilentlyContinue
if ($proc) {
    $finished = $proc.WaitForExit(600000)
    if (-not $finished) {
        Write-Output "  WARNING: cleanmgr did not finish within 10 minutes. Remote/service"
        Write-Output "  sessions have no desktop, so cleanmgr can silently wait forever on a"
        Write-Output "  UI dialog nobody can see. Terminating it now."
        try { $proc.Kill() } catch {}
        Get-Process cleanmgr -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
        Write-Output "  Disk Cleanup was terminated after timeout -- some categories may be incomplete"
    } else {
        Write-Output "  Disk Cleanup completed (exit code: $($proc.ExitCode))"
    }
} else {
    Write-Output "  Failed to launch cleanmgr"
}
""",
        "danger": True,
    },

    # ─── DISK ───────────────────────────────────────────────────────────
    {
        "id": "disk_space_report",
        "label": "Disk Space Report (All Drives)",
        "category": "Disk",
        "description": "Shows used/free space and health status for all fixed drives",
        "command": r"""
Write-Output "  Drive   FS         Total     Used      Free      Used%   Health"
Write-Output "  ──────────────────────────────────────────────────────────────────"
$vols = Get-Volume -ErrorAction SilentlyContinue | Where-Object {$_.DriveType -eq 'Fixed' -and $_.DriveLetter}
if (-not $vols) { Write-Output "  No fixed volumes found (may need admin rights)"; return }
foreach ($v in $vols) {
    $total = [math]::Round($v.Size/1GB,2)
    $free  = [math]::Round($v.SizeRemaining/1GB,2)
    $used  = [math]::Round($total - $free, 2)
    $pct   = if($total -gt 0) { "$([math]::Round(($used/$total)*100,1))%" } else { "N/A" }
    $warn  = if($total -gt 0 -and ($used/$total) -gt 0.9) { " ⚠CRITICAL" } elseif($total -gt 0 -and ($used/$total) -gt 0.8) { " ⚠LOW" } else { "" }
    Write-Output "  $($v.DriveLetter):      $($v.FileSystem.PadRight(10)) ${total} GB    ${used} GB    ${free} GB   $pct$warn   $($v.HealthStatus)"
}
""",
        "danger": False,
    },
    {
        "id": "defrag_drives",
        "label": "Optimize / Defragment All Fixed Drives",
        "category": "Disk",
        "description": "Defragments HDDs; runs TRIM on SSDs (auto-detects drive type)",
        "command": r"""
$vols = Get-Volume -ErrorAction SilentlyContinue | Where-Object {$_.DriveType -eq 'Fixed' -and $_.DriveLetter -and ($_.FileSystem -eq 'NTFS' -or $_.FileSystem -eq 'ReFS')}
if (-not $vols) { Write-Output "  No eligible NTFS/ReFS volumes found"; return }
foreach ($v in $vols) {
    $dl = $v.DriveLetter
    Write-Output "  Optimizing drive ${dl}: ($($v.FileSystem))..."
    $result = Optimize-Volume -DriveLetter $dl -Verbose 4>$null -ErrorAction SilentlyContinue
    Write-Output "  Drive ${dl}: optimization complete"
}
""",
        "danger": False,
    },
    {
        "id": "disk_health_scan",
        "label": "Scan Disk Health (Quick Scan — No Reboot)",
        "category": "Disk",
        "description": "Runs Repair-Volume scan on all drives without requiring a reboot",
        "command": r"""
$vols = Get-Volume -ErrorAction SilentlyContinue | Where-Object {$_.DriveType -eq 'Fixed' -and $_.DriveLetter}
if (-not $vols) { Write-Output "  No fixed volumes found"; return }
foreach ($v in $vols) {
    $dl = $v.DriveLetter
    Write-Output "  Scanning Drive ${dl}: ..."
    $result = Repair-Volume -DriveLetter $dl -Scan -ErrorAction SilentlyContinue
    Write-Output "  Drive ${dl}: Scan=$result | Health=$($v.HealthStatus) | FS=$($v.FileSystem)"
}
""",
        "danger": False,
    },
    {
        "id": "large_files_report",
        "label": "Find Top 20 Largest Files on C: Drive",
        "category": "Disk",
        "description": "Identifies the biggest disk space consumers on the C: drive",
        "command": r"""
Write-Output "  Scanning C: drive for large files (>100MB)..."
$files = Get-ChildItem "C:\" -Recurse -File -ErrorAction SilentlyContinue | Where-Object {$_.Length -gt 100MB}
$sorted = $files | Sort-Object Length -Descending | Select-Object -First 20
Write-Output "  Size (GB)    Path"
Write-Output "  ─────────────────────────────────────────────────────────"
foreach ($f in $sorted) {
    $sz = [math]::Round($f.Length/1GB,3)
    Write-Output "  $($sz.ToString('F3')) GB   $($f.FullName)"
}
Write-Output "  Total large files found: $($files.Count)"
""",
        "danger": False,
    },

    # ─── PERFORMANCE ────────────────────────────────────────────────────
    {
        "id": "high_perf_power",
        "label": "Set High Performance Power Plan",
        "category": "Performance",
        "description": "Activates the built-in High Performance power scheme",
        "command": r"""
$guid = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
$result = powercfg -setactive $guid 2>&1
$active  = powercfg -getactivescheme 2>&1
Write-Output "  Power plan set to: High Performance"
Write-Output "  Active: $active"
""",
        "danger": True,
    },
    {
        "id": "visual_effects_perf",
        "label": "Optimize Visual Effects for Performance",
        "category": "Performance",
        "description": "Sets Windows to Best Performance visual mode (disables animations)",
        "command": r"""
$regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects"
if (-not (Test-Path $regPath)) { New-Item $regPath -Force -ErrorAction SilentlyContinue | Out-Null }
Set-ItemProperty -Path $regPath -Name VisualFXSetting -Value 2 -ErrorAction SilentlyContinue
$dp = "HKCU:\Control Panel\Desktop"
Set-ItemProperty $dp -Name DragFullWindows -Value "0" -ErrorAction SilentlyContinue
Set-ItemProperty $dp -Name MenuShowDelay   -Value "0" -ErrorAction SilentlyContinue
$wm = "HKCU:\Control Panel\Desktop\WindowMetrics"
if (Test-Path $wm) { Set-ItemProperty $wm -Name MinAnimate -Value "0" -ErrorAction SilentlyContinue }
Write-Output "  Visual effects set to Best Performance"
Write-Output "  Animations & shadows disabled"
Write-Output "  Note: Re-login required for full effect"
""",
        "danger": False,
    },
    {
        "id": "optimize_ram",
        "label": "Optimize RAM / Force Garbage Collection",
        "category": "Performance",
        "description": "Reports RAM usage before and after forcing .NET GC collection",
        "command": r"""
$os = Get-CimInstance Win32_OperatingSystem -ErrorAction SilentlyContinue
if (-not $os) { Write-Output "  Cannot query WMI — insufficient rights"; return }
$totalGB  = [math]::Round($os.TotalVisibleMemorySize/1MB,2)
$freeBefore = [math]::Round($os.FreePhysicalMemory/1MB,2)
$usedBefore = [math]::Round($totalGB - $freeBefore,2)
Write-Output "  RAM BEFORE — Total: ${totalGB} GB | Used: ${usedBefore} GB | Free: ${freeBefore} GB"
[System.GC]::Collect()
[System.GC]::WaitForPendingFinalizers()
[System.GC]::Collect()
$freeAfter = [math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB,2)
$usedAfter = [math]::Round($totalGB - $freeAfter,2)
$recovered = [math]::Round($freeAfter - $freeBefore,2)
Write-Output "  RAM AFTER  — Total: ${totalGB} GB | Used: ${usedAfter} GB | Free: ${freeAfter} GB"
Write-Output "  Recovered : ${recovered} GB"
""",
        "danger": False,
    },
    {
        "id": "tune_sysmain",
        "label": "Auto-Tune SysMain / Superfetch (SSD Detection)",
        "category": "Performance",
        "description": "Disables SysMain on SSDs; keeps it active on HDDs",
        "command": r"""
$svc  = Get-Service -Name "SysMain" -ErrorAction SilentlyContinue
$ssds = Get-PhysicalDisk -ErrorAction SilentlyContinue | Where-Object {$_.MediaType -eq 'SSD'}
if ($ssds) {
    Write-Output "  SSD detected on this system"
    if ($svc -and $svc.Status -eq 'Running') {
        Stop-Service SysMain -Force -ErrorAction SilentlyContinue
        Set-Service  SysMain -StartupType Disabled -ErrorAction SilentlyContinue
        Write-Output "  SysMain DISABLED (recommended for SSD performance)"
    } else { Write-Output "  SysMain already stopped/disabled" }
} else {
    Write-Output "  HDD-only system — SysMain kept ACTIVE"
    if ($svc -and $svc.Status -ne 'Running') {
        Start-Service SysMain -ErrorAction SilentlyContinue
        Set-Service   SysMain -StartupType Automatic -ErrorAction SilentlyContinue
        Write-Output "  SysMain re-enabled for HDD performance"
    }
}
""",
        "danger": False,
    },
    {
        "id": "restart_search",
        "label": "Restart & Reset Windows Search Indexer",
        "category": "Performance",
        "description": "Restarts WSearch service to free CPU/disk from heavy indexing",
        "command": r"""
$svc = Get-Service -Name "WSearch" -ErrorAction SilentlyContinue
if ($svc) {
    Stop-Service WSearch -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    Start-Service WSearch -ErrorAction SilentlyContinue
    Write-Output "  Windows Search indexer restarted successfully"
} else { Write-Output "  Windows Search service not found" }
""",
        "danger": False,
    },
    {
        "id": "startup_report",
        "label": "Startup Programs & Services Report",
        "category": "Performance",
        "description": "Lists all auto-start programs from registry and scheduled tasks",
        "command": r"""
Write-Output "  === STARTUP REGISTRY ENTRIES ==="
$paths = @(
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
    "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
    "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"
)
foreach ($p in $paths) {
    if (Test-Path $p) {
        $branch = $p.Split('\')[-3]
        Get-ItemProperty $p -ErrorAction SilentlyContinue | ForEach-Object {
            $_.PSObject.Properties | Where-Object {$_.Name -notlike 'PS*'} | ForEach-Object {
                Write-Output "  [$branch] $($_.Name) = $($_.Value)"
            }
        }
    }
}
Write-Output ""
Write-Output "  === WIN32 STARTUP COMMANDS ==="
Get-CimInstance Win32_StartupCommand -ErrorAction SilentlyContinue | foreach {
    Write-Output "  [$($_.User)] $($_.Name) — $($_.Command)"
}
Write-Output ""
Write-Output "  === ENABLED THIRD-PARTY SCHEDULED TASKS ==="
Get-ScheduledTask -ErrorAction SilentlyContinue |
    Where-Object {$_.State -eq 'Ready' -and $_.TaskPath -notlike '\Microsoft\*'} |
    Select-Object -First 15 | foreach { Write-Output "  $($_.TaskPath)$($_.TaskName)" }
""",
        "danger": False,
    },
    {
        "id": "pagefile_report",
        "label": "Virtual Memory / Page File Report",
        "category": "Performance",
        "description": "Shows current page file settings, usage and recommendations",
        "command": r"""
$sys = Get-CimInstance Win32_ComputerSystem -ErrorAction SilentlyContinue
if (-not $sys) { Write-Output "  Cannot query WMI"; return }
$ramGB = [math]::Round($sys.TotalPhysicalMemory/1GB,2)
Write-Output "  RAM Installed     : ${ramGB} GB"
Write-Output "  Auto-Managed PF   : $($sys.AutomaticManagedPagefile)"
Get-CimInstance Win32_PageFileUsage -ErrorAction SilentlyContinue | foreach {
    Write-Output "  Page File Path    : $($_.Name)"
    Write-Output "  Allocated Size    : $($_.AllocatedBaseSize) MB"
    Write-Output "  Current Usage     : $($_.CurrentUsage) MB"
    Write-Output "  Peak Usage        : $($_.PeakUsage) MB"
}
$recMin = [math]::Round($ramGB * 1024 * 1.5)
$recMax = [math]::Round($ramGB * 1024 * 3)
Write-Output "  Recommended Range : ${recMin} MB — ${recMax} MB (1.5x–3x RAM)"
""",
        "danger": False,
    },
    {
        "id": "non_essential_services",
        "label": "Non-Essential Running Services Report",
        "category": "Performance",
        "description": "Lists third-party services consuming CPU/memory resources",
        "command": r"""
Write-Output "  === THIRD-PARTY AUTO-START SERVICES ==="
$svcs = Get-WmiObject Win32_Service -ErrorAction SilentlyContinue |
    Where-Object { $_.State -eq 'Running' -and $_.StartMode -eq 'Auto' -and
        $_.PathName -notlike '*system32*' -and $_.PathName -notlike '*SysWOW64*' -and
        $_.PathName -notlike '*SystemRoot*' }
if ($svcs) {
    foreach ($s in $svcs) {
        $mem = "N/A"
        try { $proc = Get-Process -Id $s.ProcessId -EA SilentlyContinue
              if ($proc) { $mem = "$([math]::Round($proc.WorkingSet64/1MB,1)) MB" } } catch {}
        Write-Output "  $($s.Name.PadRight(40)) RAM: $mem"
    }
} else { Write-Output "  No non-system auto-start services found" }
""",
        "danger": False,
    },

    # ─── WINDOWS HEALTH ─────────────────────────────────────────────────
    {
        "id": "system_info",
        "label": "Full System Information Report",
        "category": "Windows Health",
        "description": "CPU, RAM, OS version, uptime, BIOS, and model info",
        "command": r"""
$cs  = Get-CimInstance Win32_ComputerSystem  -ErrorAction SilentlyContinue
$os  = Get-CimInstance Win32_OperatingSystem -ErrorAction SilentlyContinue
$cpu = Get-CimInstance Win32_Processor       -ErrorAction SilentlyContinue | Select-Object -First 1
$bio = Get-CimInstance Win32_BIOS            -ErrorAction SilentlyContinue
if (-not $cs) { Write-Output "  Cannot query WMI — check permissions"; return }
$uptime = (Get-Date) - $os.LastBootUpTime
Write-Output "  Hostname     : $($cs.Name)"
Write-Output "  Manufacturer : $($cs.Manufacturer) $($cs.Model)"
Write-Output "  OS           : $($os.Caption) $($os.OSArchitecture)"
Write-Output "  OS Build     : $($os.Version) (Build $($os.BuildNumber))"
Write-Output "  CPU          : $($cpu.Name)"
Write-Output "  CPU Cores    : $($cpu.NumberOfCores) Physical / $($cpu.NumberOfLogicalProcessors) Logical"
Write-Output "  CPU Speed    : $($cpu.MaxClockSpeed) MHz"
Write-Output "  RAM Total    : $([math]::Round($cs.TotalPhysicalMemory/1GB,2)) GB"
if ($bio) { Write-Output "  BIOS         : $($bio.Manufacturer) v$($bio.SMBIOSBIOSVersion)" }
Write-Output "  Last Boot    : $($os.LastBootUpTime.ToString('yyyy-MM-dd HH:mm:ss'))"
Write-Output "  Uptime       : $($uptime.Days)d $($uptime.Hours)h $($uptime.Minutes)m $($uptime.Seconds)s"
Write-Output "  Domain       : $($cs.Domain)"
Write-Output "  Logged Users : $($cs.UserName)"
""",
        "danger": False,
    },
    {
        "id": "top_processes",
        "label": "Top CPU & RAM Consuming Processes",
        "category": "Windows Health",
        "description": "Lists top 10 processes by CPU time and working set memory",
        "command": r"""
Write-Output "  === TOP 10 PROCESSES BY CPU ==="
Write-Output "  Process Name                     CPU (s)      RAM (MB)"
Write-Output "  ──────────────────────────────────────────────────────────"
Get-Process -ErrorAction SilentlyContinue | Sort-Object CPU -Descending | Select-Object -First 10 | foreach {
    $cpu = if($_.CPU){ [math]::Round($_.CPU,1) } else { 0 }
    $ram = [math]::Round($_.WorkingSet64/1MB,1)
    Write-Output "  $($_.Name.PadRight(33)) $($cpu.ToString().PadLeft(8)) s   $($ram.ToString().PadLeft(8)) MB"
}
Write-Output ""
Write-Output "  === TOP 10 PROCESSES BY RAM ==="
Write-Output "  Process Name                     RAM (MB)     PID"
Write-Output "  ──────────────────────────────────────────────────────────"
Get-Process -ErrorAction SilentlyContinue | Sort-Object WorkingSet64 -Descending | Select-Object -First 10 | foreach {
    $ram = [math]::Round($_.WorkingSet64/1MB,1)
    Write-Output "  $($_.Name.PadRight(33)) $($ram.ToString().PadLeft(8)) MB   PID:$($_.Id)"
}
""",
        "danger": False,
    },
    {
        "id": "run_sfc",
        "label": "Run SFC /scannow (System File Check)",
        "category": "Windows Health",
        "description": "Scans & repairs corrupted Windows system files (5-15 min)",
        "command": r"""
Write-Output "  Starting SFC scan — this may take several minutes..."
$result = sfc /scannow 2>&1
$result | foreach { Write-Output "  $_" }
Write-Output "  SFC scan complete"
""",
        "danger": True,
    },
    {
        "id": "run_dism",
        "label": "Run DISM Health Check & Scan",
        "category": "Windows Health",
        "description": "Checks and scans the Windows component store for corruption",
        "command": r"""
Write-Output "  Running DISM CheckHealth..."
DISM /Online /Cleanup-Image /CheckHealth 2>&1 | foreach { Write-Output "  $_" }
Write-Output ""
Write-Output "  Running DISM ScanHealth..."
DISM /Online /Cleanup-Image /ScanHealth 2>&1 | foreach { Write-Output "  $_" }
""",
        "danger": True,
    },
    {
        "id": "wu_history",
        "label": "Windows Update History Report",
        "category": "Windows Health",
        "description": "Shows last 20 installed Windows updates with install dates",
        "command": r"""
Write-Output "  === LAST 20 WINDOWS UPDATES INSTALLED ==="
Write-Output "  Date          HotFix ID       Description"
Write-Output "  ───────────────────────────────────────────────────────────"
Get-HotFix -ErrorAction SilentlyContinue | Sort-Object InstalledOn -Descending | Select-Object -First 20 | foreach {
    $date = if($_.InstalledOn){ $_.InstalledOn.ToString('yyyy-MM-dd') } else { "Unknown    " }
    Write-Output "  $date      $($_.HotFixID.PadRight(15)) $($_.Description)"
}
""",
        "danger": False,
    },
    {
        "id": "recent_errors",
        "label": "Recent System & App Errors (Last 24h)",
        "category": "Windows Health",
        "description": "Pulls critical errors and warnings from System and Application logs",
        "command": r"""
$since = (Get-Date).AddHours(-24)
Write-Output "  === SYSTEM ERRORS/WARNINGS (last 24 hours) ==="
$sysEvts = Get-EventLog -LogName System -EntryType Error,Warning -After $since -Newest 15 -ErrorAction SilentlyContinue
if ($sysEvts) {
    $sysEvts | foreach {
        Write-Output "  [$($_.TimeGenerated.ToString('HH:mm'))] [$($_.EntryType)] $($_.Source): $($_.Message.Split([char]10)[0].Trim().Substring(0,[math]::Min(100,$_.Message.Length)))"
    }
} else { Write-Output "  No System errors in last 24 hours" }
Write-Output ""
Write-Output "  === APPLICATION ERRORS (last 24 hours) ==="
$appEvts = Get-EventLog -LogName Application -EntryType Error -After $since -Newest 15 -ErrorAction SilentlyContinue
if ($appEvts) {
    $appEvts | foreach {
        Write-Output "  [$($_.TimeGenerated.ToString('HH:mm'))] $($_.Source): $($_.Message.Split([char]10)[0].Trim().Substring(0,[math]::Min(100,$_.Message.Length)))"
    }
} else { Write-Output "  No Application errors in last 24 hours" }
""",
        "danger": False,
    },
    {
        "id": "installed_software",
        "label": "Installed Software Inventory",
        "category": "Windows Health",
        "description": "Lists all installed applications with version and install date",
        "command": r"""
Write-Output "  === INSTALLED APPLICATIONS ==="
$reg = @(
    "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*",
    "HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*",
    "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*"
)
$apps = $reg | ForEach-Object { Get-ItemProperty $_ -ErrorAction SilentlyContinue } |
    Where-Object {$_.DisplayName} | Sort-Object DisplayName
Write-Output "  Total: $($apps.Count) applications"
Write-Output "  Application Name                                  Version          Installed"
Write-Output "  ─────────────────────────────────────────────────────────────────────────────"
$apps | foreach {
    $ver  = if($_.DisplayVersion){ $_.DisplayVersion } else { "—" }
    $date = if($_.InstallDate){ $_.InstallDate } else { "Unknown" }
    Write-Output "  $($_.DisplayName.PadRight(50)) $($ver.PadRight(16)) $date"
}
""",
        "danger": False,
    },

    # ─── NETWORK ────────────────────────────────────────────────────────
    {
        "id": "net_ip_config",
        "label": "Network Adapter & IP Configuration",
        "category": "Network",
        "description": "Displays IP, subnet, gateway, DNS for all active adapters",
        "command": r"""
Write-Output "  === NETWORK ADAPTERS ==="
$configs = Get-NetIPConfiguration -ErrorAction SilentlyContinue | Where-Object {$_.IPv4Address}
if (-not $configs) { Write-Output "  No active IPv4 adapters found"; return }
foreach ($c in $configs) {
    $dns = ($c.DNSServer | Where-Object {$_.AddressFamily -eq 2} | Select-Object -ExpandProperty ServerAddresses) -join ', '
    $mac = (Get-NetAdapter -Name $c.InterfaceAlias -ErrorAction SilentlyContinue).MacAddress
    Write-Output "  Adapter      : $($c.InterfaceAlias)"
    Write-Output "  IPv4 Address : $($c.IPv4Address.IPAddress)"
    Write-Output "  Prefix Len   : /$($c.IPv4Address.PrefixLength)"
    Write-Output "  Default GW   : $($c.IPv4DefaultGateway.NextHop)"
    Write-Output "  DNS Servers  : $dns"
    Write-Output "  MAC Address  : $mac"
    Write-Output "  ──────────────────────────────────────────────"
}
""",
        "danger": False,
    },
    {
        "id": "net_connectivity",
        "label": "Test Network Connectivity (Ping Suite)",
        "category": "Network",
        "description": "Tests ping to gateway, DNS providers, Google, and Microsoft",
        "command": r"""
$gw = (Get-NetIPConfiguration -ErrorAction SilentlyContinue | Where-Object {$_.IPv4DefaultGateway} | Select-Object -First 1).IPv4DefaultGateway.NextHop
$targets = [ordered]@{
    "Default Gateway"        = $gw
    "Google Public DNS"      = "8.8.8.8"
    "Cloudflare DNS"         = "1.1.1.1"
    "Google.com"             = "google.com"
    "Microsoft.com"          = "microsoft.com"
    "Windows Update"         = "windowsupdate.microsoft.com"
}
Write-Output "  Target                      Address                   Status   Latency"
Write-Output "  ─────────────────────────────────────────────────────────────────────"
foreach ($t in $targets.GetEnumerator()) {
    if (-not $t.Value) { continue }
    $r = Test-NetConnection -ComputerName $t.Value -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
    $ok      = if($r.PingSucceeded) { "✓ PASS" } else { "✗ FAIL" }
    $latency = if($r.PingReplyDetails) { "$($r.PingReplyDetails.RoundtripTime) ms" } else { "—" }
    Write-Output "  $($t.Key.PadRight(28)) $($t.Value.PadRight(26)) $ok   $latency"
}
""",
        "danger": False,
    },
    {
        "id": "net_adapter_stats",
        "label": "Network Adapter Speed & Traffic Stats",
        "category": "Network",
        "description": "Shows link speed, status, and byte counters for active adapters",
        "command": r"""
$adapters = Get-NetAdapter -ErrorAction SilentlyContinue | Where-Object {$_.Status -eq 'Up'}
if (-not $adapters) { Write-Output "  No active adapters found"; return }
foreach ($a in $adapters) {
    $stats = $a | Get-NetAdapterStatistics -ErrorAction SilentlyContinue
    $speed = if($a.Speed) { "$([math]::Round($a.Speed/1e6,0)) Mbps" } elseif($a.LinkSpeed) { "$($a.LinkSpeed)" } else { "Unknown" }
    Write-Output "  Adapter  : $($a.Name) — $($a.InterfaceDescription)"
    Write-Output "  Status   : $($a.Status)  |  Speed: $speed  |  MAC: $($a.MacAddress)"
    if ($stats) {
        Write-Output "  Sent     : $([math]::Round($stats.SentBytes/1MB,2)) MB ($($stats.SentUnicastPackets) pkts)"
        Write-Output "  Received : $([math]::Round($stats.ReceivedBytes/1MB,2)) MB ($($stats.ReceivedUnicastPackets) pkts)"
    }
    Write-Output "  ──────────────────────────────────────────────────────────"
}
""",
        "danger": False,
    },
    {
        "id": "reset_network",
        "label": "Reset TCP/IP & Winsock Stack",
        "category": "Network",
        "description": "Resets Winsock, TCP/IP stack, flushes DNS, renews IP lease",
        "command": r"""
Write-Output "  Resetting Winsock catalog..."
netsh winsock reset 2>&1 | Out-Null
Write-Output "  Winsock reset complete"
Write-Output "  Resetting TCP/IP stack (IPv4 & IPv6)..."
netsh int ip   reset 2>&1 | Out-Null
netsh int ipv6 reset 2>&1 | Out-Null
Write-Output "  TCP/IP stack reset complete"
Write-Output "  Flushing DNS resolver cache..."
ipconfig /flushdns 2>&1 | Out-Null
ipconfig /registerdns 2>&1 | Out-Null
Write-Output "  Releasing IP address..."
ipconfig /release 2>&1 | Out-Null
Start-Sleep -Seconds 2
Write-Output "  Renewing IP address..."
ipconfig /renew 2>&1 | Out-Null
Write-Output "  Network stack reset complete"
Write-Output "  NOTE: A REBOOT is recommended to fully apply Winsock/TCP-IP changes"
""",
        "danger": True,
    },
    {
        "id": "dns_test",
        "label": "DNS Resolution & Latency Test",
        "category": "Network",
        "description": "Tests DNS lookup speed for multiple domains",
        "command": r"""
$domains = @("google.com","microsoft.com","amazon.com","github.com","youtube.com")
Write-Output "  === DNS RESOLUTION LATENCY TEST ==="
Write-Output "  Domain                        IP Address         Latency"
Write-Output "  ──────────────────────────────────────────────────────────"
foreach ($d in $domains) {
    $t  = Measure-Command { $ip = (Resolve-DnsName $d -ErrorAction SilentlyContinue | Select-Object -First 1).IPAddress }
    $ms = [math]::Round($t.TotalMilliseconds,1)
    Write-Output "  $($d.PadRight(30)) $($ip.PadRight(19)) ${ms} ms"
}
""",
        "danger": False,
    },
    {
        "id": "firewall_status",
        "label": "Firewall & Security Status Report",
        "category": "Network",
        "description": "Reports Windows Firewall profiles, AV products, and listening ports",
        "command": r"""
Write-Output "  === WINDOWS FIREWALL PROFILES ==="
Get-NetFirewallProfile -ErrorAction SilentlyContinue | foreach {
    Write-Output "  $($_.Name.PadRight(14)): Enabled=$($_.Enabled)  Inbound=$($_.DefaultInboundAction)  Outbound=$($_.DefaultOutboundAction)"
}
Write-Output ""
Write-Output "  === ANTIVIRUS / SECURITY PRODUCTS ==="
$av = Get-CimInstance -Namespace root/SecurityCenter2 -ClassName AntiVirusProduct -ErrorAction SilentlyContinue
if ($av) { $av | foreach { Write-Output "  AV: $($_.displayName) | State: $($_.productState)" } }
else { Write-Output "  None registered (may be server OS or WMI namespace unavailable)" }
Write-Output ""
Write-Output "  === TOP LISTENING PORTS (TCP) ==="
netstat -an 2>$null | Select-String "LISTENING" | Select-Object -First 20 | foreach { Write-Output "  $_" }
""",
        "danger": False,
    },
    {
        "id": "active_connections",
        "label": "Active Network Connections Report",
        "category": "Network",
        "description": "Lists all active TCP connections with owning process names",
        "command": r"""
Write-Output "  === ACTIVE TCP CONNECTIONS ==="
Write-Output "  Process                    Local                      Remote                     State"
Write-Output "  ─────────────────────────────────────────────────────────────────────────────────────"
Get-NetTCPConnection -ErrorAction SilentlyContinue |
    Where-Object {$_.State -ne 'Listen' -and $_.RemoteAddress -ne '0.0.0.0' -and $_.RemoteAddress -ne '::'} |
    Select-Object -First 25 | foreach {
        $proc = (Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue).Name
        if (-not $proc) { $proc = "PID:$($_.OwningProcess)" }
        $local  = "$($_.LocalAddress):$($_.LocalPort)"
        $remote = "$($_.RemoteAddress):$($_.RemotePort)"
        Write-Output "  $($proc.PadRight(27)) $($local.PadRight(27)) $($remote.PadRight(27)) $($_.State)"
    }
""",
        "danger": False,
    },

    # ─── 🔁 POWER RECYCLE ───────────────────────────────────────────────────
    {
        "id": "pr_collect_evidence",
        "label": "Collect Evidence (Pre-Recycle Snapshot)",
        "category": "Power Recycle",
        "description": "Top CPU processes, CPU load, disk health, and last 100 System log events -- capture this BEFORE trying a fix",
        "command": r"""
Write-Output "  === TOP 20 PROCESSES BY CPU ==="
Get-Process -ErrorAction SilentlyContinue | Sort-Object CPU -Descending | Select-Object -First 20 |
    ForEach-Object { Write-Output ("  {0,-28} PID:{1,-7} CPU:{2,10} WS:{3,8}MB" -f $_.ProcessName, $_.Id, [math]::Round($_.CPU,1), [math]::Round($_.WorkingSet64/1MB,1)) }

Write-Output ""
Write-Output "  === CPU LOAD (3 samples, 1s apart) ==="
try {
    $samples = Get-Counter '\Processor(_Total)\% Processor Time' -SampleInterval 1 -MaxSamples 3 -ErrorAction Stop
    $vals = $samples.CounterSamples | ForEach-Object { [math]::Round($_.CookedValue,1) }
    $avg = ($vals | Measure-Object -Average -ErrorAction SilentlyContinue).Average
    Write-Output ("  Samples: {0}%   Average: {1}%" -f ($vals -join "%, "), [math]::Round($avg,1))
} catch { Write-Output "  Get-Counter unavailable: $($_.Exception.Message)" }

Write-Output ""
Write-Output "  === PHYSICAL DISK STATUS ==="
Get-PhysicalDisk -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Output ("  {0,-24} Media:{1,-8} Health:{2,-12} Size:{3}GB" -f $_.FriendlyName, $_.MediaType, $_.HealthStatus, [math]::Round($_.Size/1GB,1))
}

Write-Output ""
Write-Output "  === LAST 100 SYSTEM LOG EVENTS (summary) ==="
$evts = Get-WinEvent -LogName System -MaxEvents 100 -ErrorAction SilentlyContinue
if ($evts) {
    Get-WinEvent -LogName System -MaxEvents 100 -EA SilentlyContinue | Group-Object LevelDisplayName | Sort-Object Count -Descending |
        ForEach-Object { Write-Output ("  {0,-14}: {1}" -f $_.Name, $_.Count) }
    Write-Output "  --- Most recent Warning/Error/Critical entries (up to 15) ---"
    $evts | Where-Object { $_.LevelDisplayName -in @("Error","Warning","Critical") } | Select-Object -First 15 | ForEach-Object {
        $msg = ($_.Message -replace "`r`n"," ")
        if ($msg.Length -gt 110) { $msg = $msg.Substring(0,110) + "..." }
        Write-Output ("  [{0}] {1,-9} {2,-28} {3}" -f $_.TimeCreated.ToString("MM-dd HH:mm:ss"), $_.LevelDisplayName, $_.ProviderName, $msg)
    }
} else { Write-Output "  Could not read the System event log (insufficient rights?)" }
""",
        "danger": False,
    },
    {
        "id": "pr_diagnose_driver_hang",
        "label": "Diagnose: Possible Driver Hang (Top Processes + Stuck Services)",
        "category": "Power Recycle",
        "description": "Top 10 CPU processes plus any service stuck in a Pending state -- a common symptom of a hung driver",
        "command": r"""
Write-Output "  === TOP 10 PROCESSES BY CPU ==="
Get-Process -ErrorAction SilentlyContinue | Sort-Object CPU -Descending | Select-Object -First 10 |
    ForEach-Object { Write-Output ("  {0,-28} PID:{1,-7} CPU:{2,10} WS:{3,8}MB" -f $_.ProcessName, $_.Id, [math]::Round($_.CPU,1), [math]::Round($_.WorkingSet64/1MB,1)) }

Write-Output ""
Write-Output "  === SERVICES STUCK IN A PENDING STATE ==="
$pending = Get-Service -ErrorAction SilentlyContinue | Where-Object { $_.Status -match 'Pending' }
if ($pending) {
    $pending | ForEach-Object { Write-Output ("  {0,-32} {1}" -f $_.Name, $_.Status) }
    Write-Output "  A pending service above may be the 'hanging driver' -- try 'Restart a Specific Service' (Remote Tools)"
    Write-Output "  or find its owning device with a 'List ... Devices' report and use 'Cycle a Device Driver' below."
} else {
    Write-Output "  No services currently stuck in a pending state."
}
""",
        "danger": False,
    },
    {
        "id": "pr_list_storage_devices",
        "label": "List Storage Controllers & Disk Drives",
        "category": "Power Recycle",
        "description": "Lists DiskDrive-class and SCSI/Storage-class PnP devices with their Instance IDs",
        "command": r"""
Write-Output "  === DISK DRIVE CLASS DEVICES ==="
Get-PnpDevice -Class DiskDrive -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Output ("  [{0}] {1}" -f $_.Status, $_.FriendlyName)
    Write-Output ("      InstanceId: {0}" -f $_.InstanceId)
}
Write-Output ""
Write-Output "  === SCSI / STORAGE CONTROLLER CLASS DEVICES ==="
Get-PnpDevice -ErrorAction SilentlyContinue | Where-Object { $_.Class -match 'SCSI|Storage' } | ForEach-Object {
    Write-Output ("  [{0}] {1}  (Class: {2})" -f $_.Status, $_.FriendlyName, $_.Class)
    Write-Output ("      InstanceId: {0}" -f $_.InstanceId)
}
Write-Output ""
Write-Output "  WARNING: never disable the controller hosting the boot/system volume -- it can crash the target immediately."
Write-Output "  Copy an InstanceId above into 'Cycle a Device Driver' to disable/re-enable it."
""",
        "danger": False,
    },
    {
        "id": "pr_list_usb_devices",
        "label": "List USB Devices",
        "category": "Power Recycle",
        "description": "Lists USB-class PnP devices with their Instance IDs",
        "command": r"""
Write-Output "  === USB CLASS DEVICES ==="
Get-PnpDevice -Class USB -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Output ("  [{0}] {1}" -f $_.Status, $_.FriendlyName)
    Write-Output ("      InstanceId: {0}" -f $_.InstanceId)
}
Write-Output ""
Write-Output "  Copy an InstanceId above into 'Cycle a Device Driver' to disable/re-enable one specific USB device,"
Write-Output "  or use 'Cycle All USB Hub Devices' to cycle every USB-matching device at once."
""",
        "danger": False,
    },
    {
        "id": "pr_cycle_device_by_id",
        "label": "Cycle a Device Driver (Disable -> Enable by Instance ID)",
        "category": "Power Recycle",
        "description": "Disables then re-enables one PnP device by Instance ID -- get the ID from a 'List ... Devices' report first",
        "params": [
            {"key": "DEVICE_ID", "kind": "deviceid", "label": "Device Instance ID",
             "required": True, "help": "Copy exactly from a 'List ... Devices' report above"}
        ],
        "command": r"""
$deviceId = "{{DEVICE_ID}}"
$before = Get-PnpDevice -InstanceId $deviceId -ErrorAction SilentlyContinue
if (-not $before) {
    Write-Output "  No device found with InstanceId: $deviceId"
    Write-Output "  Run one of the 'List ... Devices' reports first and copy the exact InstanceId."
    return
}
Write-Output "  BEFORE: $($before.FriendlyName)  [$($before.Status)]"
Disable-PnpDevice -InstanceId $deviceId -Confirm:$false -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3
Enable-PnpDevice -InstanceId $deviceId -Confirm:$false -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1
$after = Get-PnpDevice -InstanceId $deviceId -ErrorAction SilentlyContinue
Write-Output "  AFTER : $($after.FriendlyName)  [$($after.Status)]"
if ($after.Status -eq "OK") { Write-Output "  Device cycled successfully." }
else { Write-Output "  Device did not return to OK status -- check Device Manager before assuming it's fixed." }
""",
        "danger": True,
    },
    {
        "id": "pr_restart_all_adapters",
        "label": "Restart All Network Adapters",
        "category": "Power Recycle",
        "description": "Restarts every network adapter -- the tool auto-reconnects if this session was using one of them",
        "command": r"""
Write-Output "  === RESTARTING ALL NETWORK ADAPTERS ==="
Write-Output "  If this session is on the adapter being restarted you may see a short gap -- the tool auto-reconnects."
Get-NetAdapter -ErrorAction SilentlyContinue | ForEach-Object { Write-Output "  Restarting: $($_.Name) [$($_.Status)]" }
Get-NetAdapter -ErrorAction SilentlyContinue | Restart-NetAdapter -Confirm:$false -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3
Write-Output "  === POST-RESTART STATUS ==="
Get-NetAdapter -ErrorAction SilentlyContinue | ForEach-Object { Write-Output "  $($_.Name): $($_.Status)" }
""",
        "danger": True,
    },
    {
        "id": "pr_restart_named_adapter",
        "label": "Restart Network Adapter by Name",
        "category": "Power Recycle",
        "description": "Restarts one named adapter (Restart-NetAdapter) -- the direct fix for a wedged network driver",
        "params": [
            {"key": "ADAPTER", "kind": "adaptername", "label": "Adapter Name", "required": True, "default": "Ethernet"}
        ],
        "command": r"""
$adapterName = "{{ADAPTER}}"
$nic = Get-NetAdapter -Name $adapterName -ErrorAction SilentlyContinue
if (-not $nic) {
    Write-Output "  Adapter '$adapterName' not found. Available adapters:"
    Get-NetAdapter -ErrorAction SilentlyContinue | ForEach-Object { Write-Output "    $($_.Name)  [$($_.Status)]" }
    return
}
Write-Output "  BEFORE: $($nic.Name) = $($nic.Status)"
Restart-NetAdapter -Name $adapterName -Confirm:$false -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3
$nic2 = Get-NetAdapter -Name $adapterName -ErrorAction SilentlyContinue
Write-Output "  AFTER : $($nic2.Name) = $($nic2.Status)"
""",
        "danger": True,
    },
    {
        "id": "pr_disable_enable_adapter",
        "label": "Disable then Enable a Network Adapter",
        "category": "Power Recycle",
        "description": "Full Disable-NetAdapter / Enable-NetAdapter cycle -- more thorough than a restart for a stuck driver",
        "params": [
            {"key": "ADAPTER", "kind": "adaptername", "label": "Adapter Name", "required": True, "default": "Ethernet"}
        ],
        "command": r"""
$adapterName = "{{ADAPTER}}"
$nic = Get-NetAdapter -Name $adapterName -ErrorAction SilentlyContinue
if (-not $nic) {
    Write-Output "  Adapter '$adapterName' not found. Available adapters:"
    Get-NetAdapter -ErrorAction SilentlyContinue | ForEach-Object { Write-Output "    $($_.Name)  [$($_.Status)]" }
    return
}
Write-Output "  BEFORE: $($nic.Name) = $($nic.Status)"
Disable-NetAdapter -Name $adapterName -Confirm:$false -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3
Enable-NetAdapter -Name $adapterName -Confirm:$false -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
$nic2 = Get-NetAdapter -Name $adapterName -ErrorAction SilentlyContinue
Write-Output "  AFTER : $($nic2.Name) = $($nic2.Status)"
""",
        "danger": True,
    },
    {
        "id": "pr_cycle_usb_hubs",
        "label": "Cycle All USB Hub Devices",
        "category": "Power Recycle",
        "description": "Disables then re-enables every PnP device whose name matches USB -- fixes a USB device causing interrupts",
        "command": r"""
Write-Output "  === CYCLING ALL USB-MATCHING PNP DEVICES ==="
$usbDevices = Get-PnpDevice -ErrorAction SilentlyContinue | Where-Object { $_.FriendlyName -match "USB" }
if (-not $usbDevices) { Write-Output "  No USB-matching PnP devices found."; return }
$count = 0
foreach ($dev in $usbDevices) {
    Write-Output "  Cycling: $($dev.FriendlyName)"
    Disable-PnpDevice -InstanceId $dev.InstanceId -Confirm:$false -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    Enable-PnpDevice -InstanceId $dev.InstanceId -Confirm:$false -ErrorAction SilentlyContinue
    $count++
}
Write-Output "  Cycled $count USB device(s)."
""",
        "danger": True,
    },
    {
        "id": "pr_firmware_info",
        "label": "Firmware / BIOS Version Report",
        "category": "Power Recycle",
        "description": "BIOS/firmware version and system model -- read-only, useful when suspecting a firmware bug",
        "command": r"""
Write-Output "  === FIRMWARE / BIOS INFO (Get-ComputerInfo can take a few seconds) ==="
$info = Get-ComputerInfo -ErrorAction SilentlyContinue
if ($info) {
    Write-Output "  BIOS Version      : $($info.BiosVersion -join ', ')"
    Write-Output "  BIOS Manufacturer : $($info.BiosManufacturer)"
    Write-Output "  BIOS Release Date : $($info.BiosReleaseDate)"
    Write-Output "  Firmware Type     : $($info.BiosFirmwareType)"
    Write-Output "  System Model      : $($info.CsManufacturer) $($info.CsModel)"
} else {
    Write-Output "  Get-ComputerInfo failed -- falling back to Win32_BIOS"
    Get-CimInstance Win32_BIOS -ErrorAction SilentlyContinue | ForEach-Object {
        Write-Output "  BIOS Version: $($_.SMBIOSBIOSVersion)  Manufacturer: $($_.Manufacturer)  ReleaseDate: $($_.ReleaseDate)"
    }
}
""",
        "danger": False,
    },
    {
        "id": "pr_force_restart",
        "label": "Force Restart Now (Unsaved Work Will Be Lost)",
        "category": "Power Recycle",
        "description": "Restart-Computer -Force -- the firmware-bug workaround and the last resort before a real power cycle",
        "command": r"""
Write-Output "  Forcing an immediate restart -- any unsaved work on the target WILL be lost."
Write-Output "  The connection will drop now; this is expected."
shutdown.exe /r /f /t 3
""",
        "danger": True,
    },
    {
        "id": "pr_wake_armed_devices",
        "label": "List Devices Armed to Wake the System",
        "category": "Power Recycle",
        "description": "powercfg /devicequery wake_armed (+ wake_programmable) -- diagnoses devices not waking correctly from sleep",
        "command": r"""
Write-Output "  === DEVICES CURRENTLY ARMED TO WAKE THIS SYSTEM ==="
powercfg /devicequery wake_armed | ForEach-Object { Write-Output "  $_" }
Write-Output ""
Write-Output "  === DEVICES THAT CAN BE PROGRAMMED TO WAKE THIS SYSTEM ==="
powercfg /devicequery wake_programmable | ForEach-Object { Write-Output "  $_" }
""",
        "danger": False,
    },
    {
        "id": "pr_disable_hibernation",
        "label": "Disable Hibernation",
        "category": "Power Recycle",
        "description": "powercfg /h off -- removes hiberfil.sys and Fast Startup/S4 hybrid-sleep behavior",
        "command": r"""
Write-Output "  Disabling hibernation (also removes hiberfil.sys and Fast Startup/hybrid-sleep behavior)..."
powercfg /h off
Write-Output "  Verifying available sleep states..."
powercfg /a | ForEach-Object { Write-Output "  $_" }
""",
        "danger": True,
    },
    {
        "id": "pr_force_signout_restart",
        "label": "Force Sign-out & Restart (shutdown /g)",
        "category": "Power Recycle",
        "description": "shutdown /g /f /t 3 -- restarts and reopens registered apps, distinct from a plain restart",
        "command": r"""
Write-Output "  Signing out and restarting now (shutdown /g) -- Windows will try to reopen registered apps on next login."
Write-Output "  Any unsaved work WILL be lost. The connection will drop now; this is expected."
shutdown /g /f /t 3
""",
        "danger": True,
    },
    {
        "id": "pr_full_soft_recycle",
        "label": "Full Soft-Recycle Bundle (Network + USB Cycle, Restart Optional)",
        "category": "Power Recycle",
        "description": "LAST RESORT before a real power cycle: restarts every adapter, cycles every USB device, then restarts Windows unless Auto-Restart is unchecked",
        "params": [
            {"key": "AUTO_RESTART", "kind": "bool", "label": "Automatically restart when done",
             "required": True, "default": "true",
             "help": "Unchecked: cycle network + USB only, skip the restart"}
        ],
        "command": r"""
$autoRestart = {{AUTO_RESTART}}
Write-Output "  === FULL SOFT-RECYCLE: NETWORK + USB CYCLE + RESTART ==="
Write-Output "  This is the closest software-only equivalent to a physical power recycle."
Write-Output ""
Write-Output "  [1/3] Restarting network adapters..."
Get-NetAdapter -ErrorAction SilentlyContinue | Restart-NetAdapter -Confirm:$false -ErrorAction SilentlyContinue

Write-Output "  [2/3] Cycling USB-matching devices..."
Get-PnpDevice -ErrorAction SilentlyContinue | Where-Object { $_.FriendlyName -match "USB" } | ForEach-Object {
    Disable-PnpDevice -InstanceId $_.InstanceId -Confirm:$false -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    Enable-PnpDevice -InstanceId $_.InstanceId -Confirm:$false -ErrorAction SilentlyContinue
}

if ($autoRestart) {
    Write-Output "  [3/3] Restarting the computer now (shutdown /g)..."
    shutdown /g /f /t 3
} else {
    Write-Output "  [3/3] Auto-Restart is OFF -- network + USB cycle complete, restart skipped."
    Write-Output "  Run 'Force Restart Now' or 'Force Sign-out & Restart' (Power Recycle) manually when ready."
}
""",
        "danger": True,
    },

    # ─── 🛠️ REMOTE TOOLS ────────────────────────────────────────────────────
    {
        "id": "rt_set_static_ip",
        "label": "Set Static IP Address",
        "category": "Remote Tools",
        "description": "netsh interface ipv4 set address ... static -- optionally sets primary/secondary DNS too",
        "params": [
            {"key": "ADAPTER", "kind": "adaptername", "label": "Adapter Name", "required": True, "default": "Ethernet"},
            {"key": "IP", "kind": "ipv4", "label": "IP Address", "required": True, "help": "e.g. 192.168.1.100"},
            {"key": "MASK", "kind": "subnetmask", "label": "Subnet Mask (or CIDR, e.g. 24)", "required": True, "default": "255.255.255.0"},
            {"key": "GATEWAY", "kind": "ipv4", "label": "Default Gateway", "required": True, "help": "e.g. 192.168.1.1"},
            {"key": "DNS1", "kind": "ipv4", "label": "Primary DNS (optional)", "required": False},
            {"key": "DNS2", "kind": "ipv4", "label": "Secondary DNS (optional)", "required": False},
        ],
        "command": r"""
$adapterName = "{{ADAPTER}}"
$ip = "{{IP}}"
$mask = "{{MASK}}"
$gw = "{{GATEWAY}}"
$dns1 = "{{DNS1}}"
$dns2 = "{{DNS2}}"

$nic = Get-NetAdapter -Name $adapterName -ErrorAction SilentlyContinue
if (-not $nic) {
    Write-Output "  Adapter '$adapterName' not found. Available adapters:"
    Get-NetAdapter -ErrorAction SilentlyContinue | ForEach-Object { Write-Output "    $($_.Name)" }
    return
}

Write-Output "  Setting static IP on '$adapterName': $ip / $mask, gateway $gw"
netsh interface ipv4 set address name="$adapterName" static $ip $mask $gw 2>&1 | ForEach-Object { Write-Output "  $_" }

if ($dns1) {
    Write-Output "  Setting primary DNS: $dns1"
    netsh interface ipv4 set dns name="$adapterName" static $dns1 primary 2>&1 | ForEach-Object { Write-Output "  $_" }
}
if ($dns2) {
    Write-Output "  Adding secondary DNS: $dns2"
    netsh interface ipv4 add dns name="$adapterName" $dns2 index=2 2>&1 | ForEach-Object { Write-Output "  $_" }
}

Start-Sleep -Seconds 2
Write-Output "  === RESULTING CONFIGURATION ==="
Get-NetIPConfiguration -InterfaceAlias $adapterName -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Output "  IPv4 Address : $($_.IPv4Address.IPAddress)"
    Write-Output "  Gateway      : $($_.IPv4DefaultGateway.NextHop)"
    Write-Output "  DNS Servers  : $($_.DNSServer.ServerAddresses -join ', ')"
}
""",
        "danger": True,
    },
    {
        "id": "rt_set_dhcp",
        "label": "Set Adapter to DHCP (Automatic)",
        "category": "Remote Tools",
        "description": "Reverts a static adapter back to DHCP for both address and DNS, then renews the lease",
        "params": [
            {"key": "ADAPTER", "kind": "adaptername", "label": "Adapter Name", "required": True, "default": "Ethernet"}
        ],
        "command": r"""
$adapterName = "{{ADAPTER}}"
$nic = Get-NetAdapter -Name $adapterName -ErrorAction SilentlyContinue
if (-not $nic) {
    Write-Output "  Adapter '$adapterName' not found. Available adapters:"
    Get-NetAdapter -ErrorAction SilentlyContinue | ForEach-Object { Write-Output "    $($_.Name)" }
    return
}
Write-Output "  Switching '$adapterName' to DHCP..."
netsh interface ipv4 set address name="$adapterName" source=dhcp 2>&1 | ForEach-Object { Write-Output "  $_" }
netsh interface ipv4 set dnsservers name="$adapterName" source=dhcp 2>&1 | ForEach-Object { Write-Output "  $_" }
ipconfig /renew "$adapterName" | Out-Null
Start-Sleep -Seconds 2
Write-Output "  === RESULTING CONFIGURATION ==="
Get-NetIPConfiguration -InterfaceAlias $adapterName -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Output "  IPv4 Address : $($_.IPv4Address.IPAddress)"
    Write-Output "  Gateway      : $($_.IPv4DefaultGateway.NextHop)"
    Write-Output "  DNS Servers  : $($_.DNSServer.ServerAddresses -join ', ')"
}
""",
        "danger": True,
    },
    {
        "id": 'rt_rename_pc_domain',
        "label": 'Rename Computer (Domain-Joined)',
        "category": 'Remote Tools',
        "description": 'Renames a domain member using the username/password you connected with as an explicit domain credential (no CredSSP needed); restart optional',
        "needs_cred": True,
        "params": [
            {'key': 'NEW_NAME', 'kind': 'computername', 'label': 'New Computer Name', 'required': True},
            {'key': 'AUTO_RESTART', 'kind': 'bool', 'label': 'Automatically restart when done', 'required': True, 'default': 'true', 'help': "Unchecked: rename now, restart later yourself (name won't take effect until then)"}
        ],
        "command": r"""
$hint = {
    param($c)
    switch ([string]$c) {
        '5'    { 'Access denied: the account you connected with is not allowed to rename this computer object in AD (needs Domain Admin or delegated "rename computer" rights), or is not a local admin on the target.' }
        '53'   { 'Network path not found: the target cannot reach a domain controller (check DNS / VPN / firewall on the target).' }
        '87'   { 'Invalid parameter: the new name is not accepted (NetBIOS rules: max 15 chars, letters/digits/hyphen).' }
        '1326' { 'Logon failure: the username/password you connected with was rejected by the domain controller.' }
        '1355' { 'The domain, or a domain controller for it, could not be contacted from the target (DNS).' }
        '1909' { 'That account is locked out.' }
        '2224' { 'A computer account with the NEW name already exists in AD -- pick a different name or delete the stale account first.' }
        '2691' { 'The computer is already joined to that name/domain.' }
        default { "Win32 code $c." }
    }
}

$newName = "{{NEW_NAME}}"
$autoRestart = {{AUTO_RESTART}}
$cs = Get-CimInstance Win32_ComputerSystem
Write-Output "  Current name : $($cs.Name)"
Write-Output "  Renaming to  : $newName"
Write-Output "  Membership   : $(if ($cs.PartOfDomain) { 'DOMAIN ' + $cs.Domain } else { 'WORKGROUP ' + $cs.Domain })"
if (-not $cs.PartOfDomain) {
    Write-Output "  This target is NOT domain-joined -- use 'Rename Computer (Workgroup/Local)' instead. Nothing was changed."
    return
}
if ($cs.Name -ieq $newName) { Write-Output "  Computer is already named $newName -- nothing to do."; return }
Write-Output "  Using the username/password you connected with as an explicit DOMAIN credential"
Write-Output "  (built on the target, so no CredSSP / double-hop is needed)."
$done = $false
try {
    Rename-Computer -NewName $newName -DomainCredential $__cred -Force -ErrorAction Stop
    $done = $true
    Write-Output "  Method 1 (Rename-Computer -DomainCredential) succeeded."
} catch {
    Write-Output "  Method 1 failed: $($_.Exception.Message)"
}
if (-not $done) {
    try {
        $r = Invoke-CimMethod -InputObject (Get-CimInstance Win32_ComputerSystem) -MethodName Rename -Arguments @{ Name = $newName; UserName = $__cred.UserName; Password = $__cred.GetNetworkCredential().Password } -ErrorAction Stop
        if ($r.ReturnValue -eq 0) { $done = $true; Write-Output "  Method 2 (WMI Win32_ComputerSystem.Rename) succeeded." }
        else { Write-Output "  Method 2 failed, code $($r.ReturnValue): $(& $hint $r.ReturnValue)" }
    } catch {
        Write-Output "  Method 2 failed: $($_.Exception.Message)"
    }
}
if (-not $done) {
    Write-Output "  Rename FAILED -- nothing was changed."
    Write-Output "  Check: (1) the account is Domain Admin / has rename rights on the computer object,"
    Write-Output "         (2) the target can resolve + reach a domain controller,"
    Write-Output "         (3) no AD computer account with the new name already exists."
    try { Write-Output "  Secure channel to domain: $(Test-ComputerSecureChannel)" } catch { Write-Output "  Secure channel test could not run: $($_.Exception.Message)" }
}

if ($done) {
    if ($autoRestart) {
        shutdown.exe /r /t 15 /c "PC Admin Tool: computer rename to $newName" | Out-Null
        Write-Output "  Rename submitted -- target restarts in 15 seconds (the session will drop; that is expected)."
    } else {
        Write-Output "  Rename submitted -- Auto-Restart is OFF. The new name will NOT take effect until"
        Write-Output "  this computer restarts -- run 'Force Restart Now' (Power Recycle) when ready."
    }
}
""",
        "danger": True,
    },
    {
        "id": 'rt_rename_pc_workgroup',
        "label": 'Rename Computer (Workgroup/Local)',
        "category": 'Remote Tools',
        "description": 'Local rename for NON-domain targets (refuses on a domain member and says so); restart optional',
        "needs_cred": True,
        "params": [
            {'key': 'NEW_NAME', 'kind': 'computername', 'label': 'New Computer Name', 'required': True},
            {'key': 'AUTO_RESTART', 'kind': 'bool', 'label': 'Automatically restart when done', 'required': True, 'default': 'true', 'help': "Unchecked: rename now, restart later yourself (name won't take effect until then)"}
        ],
        "command": r"""
$hint = {
    param($c)
    switch ([string]$c) {
        '5'    { 'Access denied: the account you connected with is not allowed to rename this computer object in AD (needs Domain Admin or delegated "rename computer" rights), or is not a local admin on the target.' }
        '53'   { 'Network path not found: the target cannot reach a domain controller (check DNS / VPN / firewall on the target).' }
        '87'   { 'Invalid parameter: the new name is not accepted (NetBIOS rules: max 15 chars, letters/digits/hyphen).' }
        '1326' { 'Logon failure: the username/password you connected with was rejected by the domain controller.' }
        '1355' { 'The domain, or a domain controller for it, could not be contacted from the target (DNS).' }
        '1909' { 'That account is locked out.' }
        '2224' { 'A computer account with the NEW name already exists in AD -- pick a different name or delete the stale account first.' }
        '2691' { 'The computer is already joined to that name/domain.' }
        default { "Win32 code $c." }
    }
}

$newName = "{{NEW_NAME}}"
$autoRestart = {{AUTO_RESTART}}
$cs = Get-CimInstance Win32_ComputerSystem
Write-Output "  Current name : $($cs.Name)"
Write-Output "  Renaming to  : $newName"
Write-Output "  Membership   : $(if ($cs.PartOfDomain) { 'DOMAIN ' + $cs.Domain } else { 'WORKGROUP ' + $cs.Domain })"
if ($cs.PartOfDomain) {
    Write-Output "  This target IS joined to domain $($cs.Domain). A local-only rename would leave its AD computer"
    Write-Output "  account out of sync and can break domain logon -- use 'Rename Computer (Domain-Joined)'. Nothing was changed."
    return
}
if ($cs.Name -ieq $newName) { Write-Output "  Computer is already named $newName -- nothing to do."; return }
$done = $false
try {
    Rename-Computer -NewName $newName -Force -ErrorAction Stop
    $done = $true
    Write-Output "  Method 1 (Rename-Computer) succeeded."
} catch {
    Write-Output "  Method 1 failed: $($_.Exception.Message)"
}
if (-not $done) {
    try {
        $r = Invoke-CimMethod -InputObject (Get-CimInstance Win32_ComputerSystem) -MethodName Rename -Arguments @{ Name = $newName } -ErrorAction Stop
        if ($r.ReturnValue -eq 0) { $done = $true; Write-Output "  Method 2 (WMI Win32_ComputerSystem.Rename) succeeded." }
        else { Write-Output "  Method 2 failed, code $($r.ReturnValue): $(& $hint $r.ReturnValue)" }
    } catch {
        Write-Output "  Method 2 failed: $($_.Exception.Message)"
    }
}
if (-not $done) {
    Write-Output "  Rename FAILED -- nothing was changed."
    Write-Output "  If you connected with a LOCAL (non-domain) admin account that is not the built-in Administrator,"
    Write-Output "  Windows remote UAC filtering blocks this. Fix on the target (Admin PowerShell):"
    Write-Output "    reg add HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System /v LocalAccountTokenFilterPolicy /t REG_DWORD /d 1 /f"
}

if ($done) {
    if ($autoRestart) {
        shutdown.exe /r /t 15 /c "PC Admin Tool: computer rename to $newName" | Out-Null
        Write-Output "  Rename submitted -- target restarts in 15 seconds (the session will drop; that is expected)."
    } else {
        Write-Output "  Rename submitted -- Auto-Restart is OFF. The new name will NOT take effect until"
        Write-Output "  this computer restarts -- run 'Force Restart Now' (Power Recycle) when ready."
    }
}
""",
        "danger": True,
    },
    {
        "id": 'rt_rename_pc_wmic_legacy',
        "label": 'Rename Computer via WMIC (Legacy -- Manual Restart Required)',
        "category": 'Remote Tools',
        "description": 'WMIC where present; automatically uses the same WMI rename method via CIM when WMIC is removed (Win11 24H2+) or the target is domain-joined',
        "needs_cred": True,
        "params": [
            {'key': 'NEW_NAME', 'kind': 'computername', 'label': 'New Computer Name', 'required': True}
        ],
        "command": r"""
$hint = {
    param($c)
    switch ([string]$c) {
        '5'    { 'Access denied: the account you connected with is not allowed to rename this computer object in AD (needs Domain Admin or delegated "rename computer" rights), or is not a local admin on the target.' }
        '53'   { 'Network path not found: the target cannot reach a domain controller (check DNS / VPN / firewall on the target).' }
        '87'   { 'Invalid parameter: the new name is not accepted (NetBIOS rules: max 15 chars, letters/digits/hyphen).' }
        '1326' { 'Logon failure: the username/password you connected with was rejected by the domain controller.' }
        '1355' { 'The domain, or a domain controller for it, could not be contacted from the target (DNS).' }
        '1909' { 'That account is locked out.' }
        '2224' { 'A computer account with the NEW name already exists in AD -- pick a different name or delete the stale account first.' }
        '2691' { 'The computer is already joined to that name/domain.' }
        default { "Win32 code $c." }
    }
}

$newName = "{{NEW_NAME}}"
$cs = Get-CimInstance Win32_ComputerSystem
Write-Output "  Current name : $($cs.Name)"
Write-Output "  Renaming to  : $newName"
Write-Output "  Membership   : $(if ($cs.PartOfDomain) { 'DOMAIN ' + $cs.Domain } else { 'WORKGROUP ' + $cs.Domain })"
if ($cs.Name -ieq $newName) { Write-Output "  Computer is already named $newName -- nothing to do."; return }
$wmic = Get-Command wmic.exe -ErrorAction SilentlyContinue
$done = $false
if ($wmic -and -not $cs.PartOfDomain) {
    Write-Output "  wmic.exe found -- using it (workgroup target)."
    $result = wmic computersystem where "name='$env:COMPUTERNAME'" call rename name="$newName" 2>&1
    $result | ForEach-Object { Write-Output "  $_" }
    if (($result | Out-String) -match 'ReturnValue = 0') { $done = $true }
} else {
    if (-not $wmic) { Write-Output "  wmic.exe is not present on this target (removed in Windows 11 24H2+) -- using the same WMI method through CIM instead." }
    else { Write-Output "  Domain-joined target: using the WMI rename method via CIM with your credentials (avoids putting a password on a wmic command line)." }
    try {
        if ($cs.PartOfDomain) { $args2 = @{ Name = $newName; UserName = $__cred.UserName; Password = $__cred.GetNetworkCredential().Password } }
        else { $args2 = @{ Name = $newName } }
        $r = Invoke-CimMethod -InputObject (Get-CimInstance Win32_ComputerSystem) -MethodName Rename -Arguments $args2 -ErrorAction Stop
        if ($r.ReturnValue -eq 0) { $done = $true; Write-Output "  WMI Win32_ComputerSystem.Rename succeeded." }
        else { Write-Output "  WMI rename failed, code $($r.ReturnValue): $(& $hint $r.ReturnValue)" }
    } catch {
        Write-Output "  WMI rename failed: $($_.Exception.Message)"
    }
}
if ($done) { Write-Output "  Rename submitted -- this does NOT auto-restart. Run 'Force Restart Now' (Power Recycle) when ready." }
else { Write-Output "  Rename FAILED -- nothing was changed." }
""",
        "danger": True,
    },
    {
        "id": "rt_vss_view",
        "label": "VSS Shadow Copy Storage Report",
        "category": "Remote Tools",
        "description": "vssadmin list shadowstorage + list shadows -- size/usage per volume and every shadow copy instance",
        "command": r"""
Write-Output "  === VSS SHADOW STORAGE (size/usage per volume) ==="
vssadmin list shadowstorage 2>&1 | ForEach-Object { Write-Output "  $_" }
Write-Output ""
Write-Output "  === VSS SHADOW COPIES (instances) ==="
vssadmin list shadows 2>&1 | ForEach-Object { Write-Output "  $_" }
""",
        "danger": False,
    },
    {
        "id": "rt_vss_delete_all",
        "label": "Delete ALL VSS Shadow Copies (Every Volume)",
        "category": "Remote Tools",
        "description": "vssadmin delete shadows /all /quiet -- IRREVERSIBLE, removes every restore point on every volume",
        "command": r"""
Write-Output "  Deleting ALL VSS shadow copies on ALL volumes -- IRREVERSIBLE, removes every System Restore /"
Write-Output "  previous-versions recovery point on this machine."
vssadmin delete shadows /all /quiet 2>&1 | ForEach-Object { Write-Output "  $_" }
Write-Output "  Done."
""",
        "danger": True,
    },
    {
        "id": "rt_vss_delete_volume_all",
        "label": "Delete ALL VSS Shadow Copies for One Volume",
        "category": "Remote Tools",
        "description": "vssadmin delete shadows /for=<volume> /all /quiet -- IRREVERSIBLE for that volume only",
        "params": [
            {"key": "VOLUME", "kind": "drive", "label": "Volume (drive letter)", "required": True, "default": "C"}
        ],
        "command": r"""
$vol = "{{VOLUME}}"
Write-Output "  Deleting ALL VSS shadow copies on volume $vol -- IRREVERSIBLE for that volume."
vssadmin delete shadows /for=$vol /all /quiet 2>&1 | ForEach-Object { Write-Output "  $_" }
Write-Output "  Done."
""",
        "danger": True,
    },
    {
        "id": "rt_vss_delete_oldest",
        "label": "Delete Oldest VSS Shadow Copy (One Volume, or Every Volume if Blank)",
        "category": "Remote Tools",
        "description": "vssadmin delete shadows /for=<volume> /oldest /quiet -- loops every fixed volume if left blank",
        "params": [
            {"key": "VOLUME", "kind": "drive", "label": "Volume (blank = every fixed volume's oldest)", "required": False}
        ],
        "command": r"""
$vol = "{{VOLUME}}"
if ([string]::IsNullOrWhiteSpace($vol)) {
    Write-Output "  No volume specified -- deleting the oldest shadow copy on every fixed volume that has one."
    Get-Volume -ErrorAction SilentlyContinue | Where-Object { $_.DriveLetter } | ForEach-Object {
        $d = "$($_.DriveLetter):"
        Write-Output "  --- $d ---"
        vssadmin delete shadows /for=$d /oldest /quiet 2>&1 | ForEach-Object { Write-Output "    $_" }
    }
} else {
    Write-Output "  Deleting the oldest VSS shadow copy on volume $vol"
    vssadmin delete shadows /for=$vol /oldest /quiet 2>&1 | ForEach-Object { Write-Output "  $_" }
}
""",
        "danger": True,
    },
    {
        "id": "rt_run_scheduled_task_query",
        "label": "Query Scheduled Task Details",
        "category": "Remote Tools",
        "description": "Full details + last-run info for a named scheduled task, with a fuzzy-match fallback",
        "params": [
            {"key": "TASK_NAME", "kind": "taskname", "label": "Task Name", "required": True,
             "help": "Exact name, or partial text to search"}
        ],
        "command": r"""
$tn = "{{TASK_NAME}}"
$tasks = Get-ScheduledTask -ErrorAction SilentlyContinue | Where-Object { $_.TaskName -eq $tn }
if (-not $tasks) {
    Write-Output "  No exact match for '$tn'. Closest matches:"
    Get-ScheduledTask -ErrorAction SilentlyContinue | Where-Object { $_.TaskName -like "*$tn*" } | Select-Object -First 15 |
        ForEach-Object { Write-Output "    $($_.TaskPath)$($_.TaskName)" }
} else {
    foreach ($t in $tasks) {
        Write-Output "  === $($t.TaskPath)$($t.TaskName) ==="
        $t | Format-List * | Out-String | Write-Output
        Get-ScheduledTaskInfo -TaskName $t.TaskName -TaskPath $t.TaskPath -ErrorAction SilentlyContinue | Format-List * | Out-String | Write-Output
    }
}
""",
        "danger": False,
    },
    {
        "id": "rt_restart_service",
        "label": "Restart a Specific Service",
        "category": "Remote Tools",
        "description": "Restart-Service -Force by exact service Name, reporting status before and after",
        "params": [
            {"key": "SERVICE_NAME", "kind": "servicename", "label": "Service Name (not Display Name)",
             "required": True, "help": "Copy it exactly from 'List All Services' -- spaces are fine"}
        ],
        "command": r"""
$svcName = '{{SERVICE_NAME}}'
$svc = Get-Service -Name $svcName -ErrorAction SilentlyContinue
if (-not $svc) {
    Write-Output "  Service '$svcName' not found. Use 'List All Services' to find the exact Name (not DisplayName)."
    $byDisp = @(Get-Service -DisplayName $svcName -ErrorAction SilentlyContinue)
    if ($byDisp.Count -gt 0) {
        Write-Output "  Note: that text is the DISPLAY name of the service whose Name is '$($byDisp[0].Name)' -- run this again with that Name."
    }
    return
}
Write-Output "  BEFORE: $($svc.Name) [$($svc.DisplayName)] = $($svc.Status)  (StartType: $($svc.StartType))"
Restart-Service -Name $svcName -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
$svc2 = Get-Service -Name $svcName -ErrorAction SilentlyContinue
Write-Output "  AFTER : $($svc2.Name) [$($svc2.DisplayName)] = $($svc2.Status)"
if ($svc2.Status -ne "Running" -and $svc.StartType -ne "Disabled") {
    Write-Output "  WARNING: service is not Running after restart -- check its dependencies or the System event log."
}
""",
        "danger": True,
    },
    {
        "id": "rt_list_all_services",
        "label": "List All Services (Name, Status, Start Type)",
        "category": "Remote Tools",
        "description": "Full raw Get-Service inventory -- every service, not just non-essential/third-party ones",
        "command": r"""
$svcs = @(Get-Service -ErrorAction SilentlyContinue | Sort-Object Status, Name)
$w = 20
foreach ($s in $svcs) { if ($s.Name.Length -gt $w) { $w = $s.Name.Length } }
Write-Output "  === ALL SERVICES (Name | Status | StartType) ==="
Write-Output ("  {0,-$w} {1,-10} {2}" -f 'Name', 'Status', 'StartType')
foreach ($s in $svcs) {
    Write-Output ("  {0,-$w} {1,-10} {2}" -f $s.Name, $s.Status, $s.StartType)
}
$total = $svcs.Count
$running = @($svcs | Where-Object Status -eq 'Running').Count
Write-Output ""
Write-Output "  Total: $total services -- $running running"
""",
        "danger": False,
    },
    {
        "id": "rt_map_network_drive",
        "label": "Map Network Drive for a User (Shared Folder -> Drive Letter)",
        "category": "Remote Tools",
        "description": "Maps a shared folder to a drive letter for ONE user account on the target -- saved in that user's profile (reconnects at every sign-in) and connected live too if they are signed in",
        "params": [
            {"key": "SHARE_PATH", "kind": "uncpath", "label": "Shared Folder Path (UNC)", "required": True, "wide": True, "help": "\\\\fileserver\\share   (a subfolder works too: \\\\fileserver\\share\\dept)"},
            {"key": "DRIVE_LETTER", "kind": "mapdrive", "label": "Drive Letter", "required": True, "default": "Z", "help": "D to Z -- must not be a local disk on the target"},
            {"key": "USER_ACCOUNT", "kind": "useraccount", "label": "Map It For This User Account", "required": True, "help": "DOMAIN\\jsmith   or   jsmith@corp.local   or   .\\localuser"},
            {"key": "APPLY_NOW", "kind": "bool", "label": "Also connect it right now if that user is signed in", "required": True, "default": "true", "help": "Unchecked: only saved -- the drive appears at the user's next sign-in"},
            {"key": "REPLACE_EXISTING", "kind": "bool", "label": "Replace an existing mapping on this drive letter", "required": True, "default": "false", "help": "Unchecked: stop if that letter already points at a different share"}
        ],
        "command": r"""
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
function Invoke-Reg([string[]]$RegArgs) {
    # reg.exe wrapper: stderr is merged into text so it can never leak into the error stream
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $o = (& "$env:SystemRoot\System32\reg.exe" @RegArgs 2>&1 | ForEach-Object { "$_" }) -join ' '
        $c = $LASTEXITCODE
    } finally { $ErrorActionPreference = $prev }
    return @{ Code = $c; Out = "$o".Trim() }
}
function Resolve-TargetUser([string]$Account) {
    # DOMAIN\user, user@domain, .\localuser or a bare name -> SID + canonical DOMAIN\user
    $a = $Account.Trim()
    if ($a -match '^\.\\') { $a = "$env:COMPUTERNAME\" + $a.Substring(2) }
    try {
        $sid = (New-Object System.Security.Principal.NTAccount($a)).Translate([System.Security.Principal.SecurityIdentifier])
        $name = $sid.Translate([System.Security.Principal.NTAccount]).Value
    } catch {
        throw "Windows on the target cannot find the account '$Account'. Use DOMAIN\username for a domain user, or .\username for a local user."
    }
    return @{ Sid = $sid.Value; Name = $name }
}
function Get-UserProfilePath([string]$Sid) {
    $k = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList\$Sid"
    if (Test-Path -LiteralPath $k) { return [string](Get-ItemProperty -LiteralPath $k).ProfileImagePath }
    return $null
}
function Open-UserHive([string]$Sid, [string]$ProfilePath) {
    # Already loaded (user signed in / process running as user) -> use it. Otherwise load NTUSER.DAT temporarily.
    if ([Microsoft.Win32.Registry]::Users.GetSubKeyNames() -contains $Sid) { return @{ Name = $Sid; Temp = $false } }
    if (-not $ProfilePath) { throw 'That account has no profile on the target (it has never signed in there), so there is nothing to map into yet.' }
    $dat = Join-Path $ProfilePath 'NTUSER.DAT'
    if (-not [System.IO.File]::Exists($dat)) { throw "NTUSER.DAT was not found at $dat" }
    $tmp = 'PCAdminTmp_' + [guid]::NewGuid().ToString('N').Substring(0, 8)
    $r = Invoke-Reg @('load', "HKU\$tmp", $dat)
    if ($r.Code -ne 0) { throw "Could not load the user's registry hive (the user may be signing in right now): $($r.Out)" }
    return @{ Name = $tmp; Temp = $true }
}
function Close-UserHive($Hive) {
    if (-not $Hive -or -not $Hive.Temp) { return }
    [gc]::Collect(); [gc]::WaitForPendingFinalizers()
    $r = $null
    for ($i = 0; $i -lt 8; $i++) {
        $r = Invoke-Reg @('unload', "HKU\$($Hive.Name)")
        if ($r.Code -eq 0) { return }
        Start-Sleep -Milliseconds 500
        [gc]::Collect()
    }
    Write-Output "  WARNING: the temporary registry hive HKU\$($Hive.Name) could not be unloaded: $($r.Out)"
}
function Get-NetDriveKeys($Hive) {
    # Persistent mapped drives live in HKU\<SID>\Network\<letter>
    $found = @()
    $nk = [Microsoft.Win32.Registry]::Users.OpenSubKey("$($Hive.Name)\Network")
    if ($nk) {
        try {
            foreach ($n in $nk.GetSubKeyNames()) {
                $k = $nk.OpenSubKey($n)
                if ($k) {
                    try {
                        $found += New-Object PSObject -Property @{
                            Letter     = $n.ToUpper()
                            RemotePath = [string]$k.GetValue('RemotePath')
                            UserName   = [string]$k.GetValue('UserName')
                        }
                    } finally { $k.Close() }
                }
            }
        } finally { $nk.Close() }
    }
    return $found
}
function Set-NetDriveKey($Hive, [string]$Letter, [string]$Share) {
    # The exact value set Windows itself writes for a persistent mapping (read back at sign-in)
    $key = [Microsoft.Win32.Registry]::Users.CreateSubKey("$($Hive.Name)\Network\$Letter")
    try {
        $key.SetValue('RemotePath', $Share, [Microsoft.Win32.RegistryValueKind]::String)
        $key.SetValue('UserName', '0', [Microsoft.Win32.RegistryValueKind]::String)
        $key.SetValue('ProviderName', 'Microsoft Windows Network', [Microsoft.Win32.RegistryValueKind]::String)
        $key.SetValue('ProviderType', 131072, [Microsoft.Win32.RegistryValueKind]::DWord)
        $key.SetValue('ConnectionType', 1, [Microsoft.Win32.RegistryValueKind]::DWord)
        $key.SetValue('DeferFlags', 4, [Microsoft.Win32.RegistryValueKind]::DWord)
    } finally { $key.Close() }
}
function Test-UserLoggedOn([string]$Sid) {
    # A user is "signed in at a desktop" if explorer.exe is running under their SID
    try {
        foreach ($p in @(Get-CimInstance -ClassName Win32_Process -Filter "Name='explorer.exe'" -ErrorAction Stop)) {
            $o = Invoke-CimMethod -InputObject $p -MethodName GetOwnerSid -ErrorAction Stop
            if ($o.Sid -eq $Sid) { return $true }
        }
    } catch { }
    return $false
}
function Invoke-AsUser([string]$Account, [string]$CmdArgs, [int]$TimeoutSec) {
    # One-shot scheduled task that runs cmd.exe inside the user's OWN interactive session (limited token),
    # because a drive mapped from this WinRM session would only exist inside this WinRM session.
    $tn  = 'PCAdminTool_Drive_' + [guid]::NewGuid().ToString('N').Substring(0, 10)
    $act = New-ScheduledTaskAction -Execute "$env:SystemRoot\System32\cmd.exe" -Argument $CmdArgs
    $prn = New-ScheduledTaskPrincipal -UserId $Account -LogonType Interactive -RunLevel Limited
    $set = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 2)
    $code = [int64]267011
    try {
        Register-ScheduledTask -TaskName $tn -Action $act -Principal $prn -Settings $set -Force | Out-Null
        Start-ScheduledTask -TaskName $tn
        $limit = (Get-Date).AddSeconds($TimeoutSec)
        do {
            Start-Sleep -Milliseconds 700
            $code = [int64](Get-ScheduledTaskInfo -TaskName $tn).LastTaskResult
        } while ((Get-Date) -lt $limit -and ($code -eq 267009 -or $code -eq 267011))
    } finally {
        Unregister-ScheduledTask -TaskName $tn -Confirm:$false -ErrorAction SilentlyContinue
    }
    return $code
}
function Test-SmbReachable([string]$UncPath) {
    # Network-level check only (DNS + TCP 445). Deliberately NOT Test-Path on the UNC path:
    # from inside a WinRM session that is a double-hop and would fail even when the user has access.
    $srv = ($UncPath.Substring(2) -split '\\')[0]
    $tcp = New-Object System.Net.Sockets.TcpClient
    $ok = $false
    try {
        $iar = $tcp.BeginConnect($srv, 445, $null, $null)
        $ok = ($iar.AsyncWaitHandle.WaitOne(4000, $false) -and $tcp.Connected)
    } catch { $ok = $false } finally { $tcp.Close() }
    return @{ Server = $srv; Ok = [bool]$ok }
}
function Get-ProfileTempLog([string]$ProfilePath, [string]$Name) {
    if ($ProfilePath) { return (Join-Path $ProfilePath "AppData\Local\Temp\$Name") }
    return $null
}
function Read-AndDeleteLog([string]$Path) {
    $t = ''
    if ($Path -and [System.IO.File]::Exists($Path)) {
        $t = ((Get-Content -LiteralPath $Path -ErrorAction SilentlyContinue) -join ' ').Trim()
        Remove-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
    }
    return $t
}

$share    = '{{SHARE_PATH}}'
$letter   = '{{DRIVE_LETTER}}'
$account  = '{{USER_ACCOUNT}}'
$applyNow = {{APPLY_NOW}}
$replace  = {{REPLACE_EXISTING}}
$L = $letter.TrimEnd(':')
$hive = $null

Write-Output "  === MAP NETWORK DRIVE FOR A USER ==="
Write-Output "  Shared folder : $share"
Write-Output "  Drive letter  : $letter"
Write-Output "  For account   : $account"
try {
    $u = Resolve-TargetUser $account
    Write-Output "  Account found : $($u.Name)  [$($u.Sid)]"
    $prof = Get-UserProfilePath $u.Sid

    $local = Get-CimInstance -ClassName Win32_LogicalDisk -Filter "DeviceID='$letter'" -ErrorAction SilentlyContinue
    if ($local -and $local.DriveType -ne 4) {
        Write-Output "  ERROR: $letter is already a local disk on this PC -- choose a different drive letter."
        return
    }

    $reach = Test-SmbReachable $share
    if ($reach.Ok) {
        Write-Output "  Network check : $($reach.Server) answers on TCP 445 from this PC."
    } else {
        Write-Output "  WARNING: $($reach.Server) did not answer on TCP 445 from this PC -- the mapping is still saved, but the drive shows as disconnected until that server is reachable."
    }

    $hive = Open-UserHive $u.Sid $prof
    if ($hive.Temp) {
        Write-Output "  Profile       : user is not signed in -- profile registry loaded temporarily"
    } else {
        Write-Output "  Profile       : profile registry already loaded (user is signed in or has a running process)"
    }

    $old = @(Get-NetDriveKeys $hive) | Where-Object { $_.Letter -eq $L } | Select-Object -First 1
    $write = $true
    if ($old) {
        if ($old.RemotePath -ieq $share) {
            Write-Output "  $letter is already saved for this user with the same share -- registry left as it is."
            $write = $false
        } elseif (-not $replace) {
            Write-Output "  STOPPED: $letter is already saved for this user as $($old.RemotePath). Tick 'Replace an existing mapping' to overwrite it, or use another drive letter."
            return
        } else {
            Write-Output "  Replacing the saved mapping $letter -> $($old.RemotePath)"
        }
    }
    if ($write) {
        Set-NetDriveKey $hive $L $share
        Write-Output "  Saved in the user's profile: $letter -> $share (reconnects at every sign-in)"
    }

    if (-not $applyNow) {
        Write-Output "  Apply-now is OFF -- the drive appears the next time this user signs in."
    } elseif (-not (Test-UserLoggedOn $u.Sid)) {
        Write-Output "  This user is not signed in at a desktop right now -- the drive appears at their next sign-in."
    } else {
        Write-Output "  User is signed in -- connecting the drive inside their own session now..."
        $logName = "pcadmintool_map_$L.log"
        $logFile = Get-ProfileTempLog $prof $logName
        if ($logFile) { Remove-Item -LiteralPath $logFile -Force -ErrorAction SilentlyContinue }
        $cmdArgs = '/c net use ' + $letter + ' /delete /y >nul 2>&1 & net use ' + $letter + ' "' + $share + '" /persistent:yes > "%TEMP%\' + $logName + '" 2>&1'
        try {
            $rc = Invoke-AsUser $u.Name $cmdArgs 30
            $detail = Read-AndDeleteLog $logFile
            if ($rc -eq 0) {
                Write-Output "  Live connection complete: $letter is now available in the user's session. $detail"
            } elseif ($rc -eq 267011 -or $rc -eq 267009) {
                Write-Output "  WARNING: the connect task did not finish within 30 seconds (still running, or it never started)."
            } else {
                Write-Output "  WARNING: the live connection failed (task result $rc): $detail"
                Write-Output "           The saved mapping is still in place and is retried at the next sign-in."
            }
        } catch {
            Write-Output "  WARNING: could not start the live connection: $($_.Exception.Message)"
            Write-Output "           The saved mapping is still in place and appears at the next sign-in."
        }
    }
    Write-Output "  Registry mapping complete for $($u.Name): $letter -> $share"
} catch {
    Write-Output "  ERROR: $($_.Exception.Message)"
} finally {
    Close-UserHive $hive
}
""",
        "danger": True,
    },
    {
        "id": "rt_unmap_network_drive",
        "label": "Remove Mapped Network Drive for a User",
        "category": "Remote Tools",
        "description": "Removes a saved drive mapping from ONE user's profile on the target (and disconnects it live if that user is signed in)",
        "params": [
            {"key": "DRIVE_LETTER", "kind": "mapdrive", "label": "Drive Letter", "required": True, "default": "Z", "help": "D to Z"},
            {"key": "USER_ACCOUNT", "kind": "useraccount", "label": "Remove It For This User Account", "required": True, "help": "DOMAIN\\jsmith   or   jsmith@corp.local   or   .\\localuser"},
            {"key": "APPLY_NOW", "kind": "bool", "label": "Also disconnect it right now if that user is signed in", "required": True, "default": "true", "help": "Unchecked: only removed from the profile -- a live connection stays until sign-out"}
        ],
        "command": r"""
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
function Invoke-Reg([string[]]$RegArgs) {
    # reg.exe wrapper: stderr is merged into text so it can never leak into the error stream
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $o = (& "$env:SystemRoot\System32\reg.exe" @RegArgs 2>&1 | ForEach-Object { "$_" }) -join ' '
        $c = $LASTEXITCODE
    } finally { $ErrorActionPreference = $prev }
    return @{ Code = $c; Out = "$o".Trim() }
}
function Resolve-TargetUser([string]$Account) {
    # DOMAIN\user, user@domain, .\localuser or a bare name -> SID + canonical DOMAIN\user
    $a = $Account.Trim()
    if ($a -match '^\.\\') { $a = "$env:COMPUTERNAME\" + $a.Substring(2) }
    try {
        $sid = (New-Object System.Security.Principal.NTAccount($a)).Translate([System.Security.Principal.SecurityIdentifier])
        $name = $sid.Translate([System.Security.Principal.NTAccount]).Value
    } catch {
        throw "Windows on the target cannot find the account '$Account'. Use DOMAIN\username for a domain user, or .\username for a local user."
    }
    return @{ Sid = $sid.Value; Name = $name }
}
function Get-UserProfilePath([string]$Sid) {
    $k = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList\$Sid"
    if (Test-Path -LiteralPath $k) { return [string](Get-ItemProperty -LiteralPath $k).ProfileImagePath }
    return $null
}
function Open-UserHive([string]$Sid, [string]$ProfilePath) {
    # Already loaded (user signed in / process running as user) -> use it. Otherwise load NTUSER.DAT temporarily.
    if ([Microsoft.Win32.Registry]::Users.GetSubKeyNames() -contains $Sid) { return @{ Name = $Sid; Temp = $false } }
    if (-not $ProfilePath) { throw 'That account has no profile on the target (it has never signed in there), so there is nothing to map into yet.' }
    $dat = Join-Path $ProfilePath 'NTUSER.DAT'
    if (-not [System.IO.File]::Exists($dat)) { throw "NTUSER.DAT was not found at $dat" }
    $tmp = 'PCAdminTmp_' + [guid]::NewGuid().ToString('N').Substring(0, 8)
    $r = Invoke-Reg @('load', "HKU\$tmp", $dat)
    if ($r.Code -ne 0) { throw "Could not load the user's registry hive (the user may be signing in right now): $($r.Out)" }
    return @{ Name = $tmp; Temp = $true }
}
function Close-UserHive($Hive) {
    if (-not $Hive -or -not $Hive.Temp) { return }
    [gc]::Collect(); [gc]::WaitForPendingFinalizers()
    $r = $null
    for ($i = 0; $i -lt 8; $i++) {
        $r = Invoke-Reg @('unload', "HKU\$($Hive.Name)")
        if ($r.Code -eq 0) { return }
        Start-Sleep -Milliseconds 500
        [gc]::Collect()
    }
    Write-Output "  WARNING: the temporary registry hive HKU\$($Hive.Name) could not be unloaded: $($r.Out)"
}
function Get-NetDriveKeys($Hive) {
    # Persistent mapped drives live in HKU\<SID>\Network\<letter>
    $found = @()
    $nk = [Microsoft.Win32.Registry]::Users.OpenSubKey("$($Hive.Name)\Network")
    if ($nk) {
        try {
            foreach ($n in $nk.GetSubKeyNames()) {
                $k = $nk.OpenSubKey($n)
                if ($k) {
                    try {
                        $found += New-Object PSObject -Property @{
                            Letter     = $n.ToUpper()
                            RemotePath = [string]$k.GetValue('RemotePath')
                            UserName   = [string]$k.GetValue('UserName')
                        }
                    } finally { $k.Close() }
                }
            }
        } finally { $nk.Close() }
    }
    return $found
}
function Remove-NetDriveKey($Hive, [string]$Letter) {
    $nk = [Microsoft.Win32.Registry]::Users.OpenSubKey("$($Hive.Name)\Network", $true)
    if ($nk) {
        try { $nk.DeleteSubKeyTree($Letter, $false) } finally { $nk.Close() }
    }
}
function Test-UserLoggedOn([string]$Sid) {
    # A user is "signed in at a desktop" if explorer.exe is running under their SID
    try {
        foreach ($p in @(Get-CimInstance -ClassName Win32_Process -Filter "Name='explorer.exe'" -ErrorAction Stop)) {
            $o = Invoke-CimMethod -InputObject $p -MethodName GetOwnerSid -ErrorAction Stop
            if ($o.Sid -eq $Sid) { return $true }
        }
    } catch { }
    return $false
}
function Invoke-AsUser([string]$Account, [string]$CmdArgs, [int]$TimeoutSec) {
    # One-shot scheduled task that runs cmd.exe inside the user's OWN interactive session (limited token),
    # because a drive mapped from this WinRM session would only exist inside this WinRM session.
    $tn  = 'PCAdminTool_Drive_' + [guid]::NewGuid().ToString('N').Substring(0, 10)
    $act = New-ScheduledTaskAction -Execute "$env:SystemRoot\System32\cmd.exe" -Argument $CmdArgs
    $prn = New-ScheduledTaskPrincipal -UserId $Account -LogonType Interactive -RunLevel Limited
    $set = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 2)
    $code = [int64]267011
    try {
        Register-ScheduledTask -TaskName $tn -Action $act -Principal $prn -Settings $set -Force | Out-Null
        Start-ScheduledTask -TaskName $tn
        $limit = (Get-Date).AddSeconds($TimeoutSec)
        do {
            Start-Sleep -Milliseconds 700
            $code = [int64](Get-ScheduledTaskInfo -TaskName $tn).LastTaskResult
        } while ((Get-Date) -lt $limit -and ($code -eq 267009 -or $code -eq 267011))
    } finally {
        Unregister-ScheduledTask -TaskName $tn -Confirm:$false -ErrorAction SilentlyContinue
    }
    return $code
}
function Get-ProfileTempLog([string]$ProfilePath, [string]$Name) {
    if ($ProfilePath) { return (Join-Path $ProfilePath "AppData\Local\Temp\$Name") }
    return $null
}
function Read-AndDeleteLog([string]$Path) {
    $t = ''
    if ($Path -and [System.IO.File]::Exists($Path)) {
        $t = ((Get-Content -LiteralPath $Path -ErrorAction SilentlyContinue) -join ' ').Trim()
        Remove-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
    }
    return $t
}

$account  = '{{USER_ACCOUNT}}'
$letter   = '{{DRIVE_LETTER}}'
$applyNow = {{APPLY_NOW}}
$L = $letter.TrimEnd(':')
$hive = $null

Write-Output "  === REMOVE MAPPED NETWORK DRIVE FOR A USER ==="
Write-Output "  Drive letter  : $letter"
Write-Output "  For account   : $account"
try {
    $u = Resolve-TargetUser $account
    Write-Output "  Account found : $($u.Name)  [$($u.Sid)]"
    $prof = Get-UserProfilePath $u.Sid
    $hive = Open-UserHive $u.Sid $prof
    if ($hive.Temp) {
        Write-Output "  Profile       : user is not signed in -- profile registry loaded temporarily"
    } else {
        Write-Output "  Profile       : profile registry already loaded (user is signed in or has a running process)"
    }

    $old = @(Get-NetDriveKeys $hive) | Where-Object { $_.Letter -eq $L } | Select-Object -First 1
    if ($old) {
        Remove-NetDriveKey $hive $L
        Write-Output "  Removed the saved mapping $letter -> $($old.RemotePath) from the user's profile."
    } else {
        Write-Output "  No saved mapping for $letter in this user's profile -- nothing to remove from the registry."
    }

    if (-not $applyNow) {
        Write-Output "  Disconnect-now is OFF -- if the drive is connected in the user's session it stays until they sign out."
    } elseif (-not (Test-UserLoggedOn $u.Sid)) {
        Write-Output "  This user is not signed in at a desktop right now -- nothing to disconnect live."
    } else {
        Write-Output "  User is signed in -- disconnecting the drive inside their own session now..."
        $logName = "pcadmintool_unmap_$L.log"
        $logFile = Get-ProfileTempLog $prof $logName
        if ($logFile) { Remove-Item -LiteralPath $logFile -Force -ErrorAction SilentlyContinue }
        $cmdArgs = '/c net use ' + $letter + ' /delete /y > "%TEMP%\' + $logName + '" 2>&1'
        try {
            $rc = Invoke-AsUser $u.Name $cmdArgs 30
            $detail = Read-AndDeleteLog $logFile
            if ($rc -eq 0) {
                Write-Output "  Live disconnect complete: $letter was disconnected in the user's session. $detail"
            } elseif ($rc -eq 267011 -or $rc -eq 267009) {
                Write-Output "  WARNING: the disconnect task did not finish within 30 seconds (still running, or it never started)."
            } else {
                Write-Output "  Note: nothing was disconnected live (task result $rc) -- the drive was probably not connected in that session. $detail"
            }
        } catch {
            Write-Output "  WARNING: could not start the live disconnect: $($_.Exception.Message)"
        }
    }
    Write-Output "  Removal complete for $($u.Name): $letter"
} catch {
    Write-Output "  ERROR: $($_.Exception.Message)"
} finally {
    Close-UserHive $hive
}
""",
        "danger": True,
    },
    {
        "id": "rt_list_mapped_drives",
        "label": "List Mapped Network Drives (Saved Per User)",
        "category": "Remote Tools",
        "description": "Shows the drive mappings saved in a user's profile on the target -- use it to verify a mapping (blank user = everyone currently signed in)",
        "params": [
            {"key": "USER_ACCOUNT", "kind": "useraccount", "label": "User Account", "required": False, "help": "blank = every signed-in user   |   DOMAIN\\jsmith   |   .\\localuser"}
        ],
        "command": r"""
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
function Invoke-Reg([string[]]$RegArgs) {
    # reg.exe wrapper: stderr is merged into text so it can never leak into the error stream
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $o = (& "$env:SystemRoot\System32\reg.exe" @RegArgs 2>&1 | ForEach-Object { "$_" }) -join ' '
        $c = $LASTEXITCODE
    } finally { $ErrorActionPreference = $prev }
    return @{ Code = $c; Out = "$o".Trim() }
}
function Resolve-TargetUser([string]$Account) {
    # DOMAIN\user, user@domain, .\localuser or a bare name -> SID + canonical DOMAIN\user
    $a = $Account.Trim()
    if ($a -match '^\.\\') { $a = "$env:COMPUTERNAME\" + $a.Substring(2) }
    try {
        $sid = (New-Object System.Security.Principal.NTAccount($a)).Translate([System.Security.Principal.SecurityIdentifier])
        $name = $sid.Translate([System.Security.Principal.NTAccount]).Value
    } catch {
        throw "Windows on the target cannot find the account '$Account'. Use DOMAIN\username for a domain user, or .\username for a local user."
    }
    return @{ Sid = $sid.Value; Name = $name }
}
function Get-UserProfilePath([string]$Sid) {
    $k = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList\$Sid"
    if (Test-Path -LiteralPath $k) { return [string](Get-ItemProperty -LiteralPath $k).ProfileImagePath }
    return $null
}
function Open-UserHive([string]$Sid, [string]$ProfilePath) {
    # Already loaded (user signed in / process running as user) -> use it. Otherwise load NTUSER.DAT temporarily.
    if ([Microsoft.Win32.Registry]::Users.GetSubKeyNames() -contains $Sid) { return @{ Name = $Sid; Temp = $false } }
    if (-not $ProfilePath) { throw 'That account has no profile on the target (it has never signed in there), so there is nothing to map into yet.' }
    $dat = Join-Path $ProfilePath 'NTUSER.DAT'
    if (-not [System.IO.File]::Exists($dat)) { throw "NTUSER.DAT was not found at $dat" }
    $tmp = 'PCAdminTmp_' + [guid]::NewGuid().ToString('N').Substring(0, 8)
    $r = Invoke-Reg @('load', "HKU\$tmp", $dat)
    if ($r.Code -ne 0) { throw "Could not load the user's registry hive (the user may be signing in right now): $($r.Out)" }
    return @{ Name = $tmp; Temp = $true }
}
function Close-UserHive($Hive) {
    if (-not $Hive -or -not $Hive.Temp) { return }
    [gc]::Collect(); [gc]::WaitForPendingFinalizers()
    $r = $null
    for ($i = 0; $i -lt 8; $i++) {
        $r = Invoke-Reg @('unload', "HKU\$($Hive.Name)")
        if ($r.Code -eq 0) { return }
        Start-Sleep -Milliseconds 500
        [gc]::Collect()
    }
    Write-Output "  WARNING: the temporary registry hive HKU\$($Hive.Name) could not be unloaded: $($r.Out)"
}
function Get-NetDriveKeys($Hive) {
    # Persistent mapped drives live in HKU\<SID>\Network\<letter>
    $found = @()
    $nk = [Microsoft.Win32.Registry]::Users.OpenSubKey("$($Hive.Name)\Network")
    if ($nk) {
        try {
            foreach ($n in $nk.GetSubKeyNames()) {
                $k = $nk.OpenSubKey($n)
                if ($k) {
                    try {
                        $found += New-Object PSObject -Property @{
                            Letter     = $n.ToUpper()
                            RemotePath = [string]$k.GetValue('RemotePath')
                            UserName   = [string]$k.GetValue('UserName')
                        }
                    } finally { $k.Close() }
                }
            }
        } finally { $nk.Close() }
    }
    return $found
}
function Get-LoadedUserSids {
    # SIDs of every user whose profile registry is currently loaded (signed in, or a process running as that user)
    return @([Microsoft.Win32.Registry]::Users.GetSubKeyNames() | Where-Object { $_ -match '^S-1-5-21-\d+-\d+-\d+-\d+$' })
}
function Get-NameFromSid([string]$Sid) {
    try { return (New-Object System.Security.Principal.SecurityIdentifier($Sid)).Translate([System.Security.Principal.NTAccount]).Value }
    catch { return '(name not resolvable)' }
}
function Test-UserLoggedOn([string]$Sid) {
    # A user is "signed in at a desktop" if explorer.exe is running under their SID
    try {
        foreach ($p in @(Get-CimInstance -ClassName Win32_Process -Filter "Name='explorer.exe'" -ErrorAction Stop)) {
            $o = Invoke-CimMethod -InputObject $p -MethodName GetOwnerSid -ErrorAction Stop
            if ($o.Sid -eq $Sid) { return $true }
        }
    } catch { }
    return $false
}

$account = '{{USER_ACCOUNT}}'

Write-Output "  === MAPPED NETWORK DRIVES (saved in each user's profile) ==="
$targets = @()
try {
    if ([string]::IsNullOrWhiteSpace($account)) {
        Write-Output "  No account given -- listing every user whose profile is currently loaded (signed in)."
        foreach ($s in @(Get-LoadedUserSids)) { $targets += @{ Sid = $s; Name = '' } }
    } else {
        $u = Resolve-TargetUser $account
        $targets += @{ Sid = $u.Sid; Name = $u.Name }
    }
} catch {
    Write-Output "  ERROR: $($_.Exception.Message)"
    return
}

if ($targets.Count -eq 0) {
    Write-Output "  No signed-in user profiles found."
    return
}

foreach ($t in $targets) {
    $hive = $null
    try {
        $name = $t.Name
        if (-not $name) { $name = Get-NameFromSid $t.Sid }
        $prof = Get-UserProfilePath $t.Sid
        $signedIn = Test-UserLoggedOn $t.Sid
        $hive = Open-UserHive $t.Sid $prof
        $hiveTxt = 'loaded'
        if ($hive.Temp) { $hiveTxt = 'read from disk (user not signed in)' }
        Write-Output ""
        Write-Output "  User : $name   [$($t.Sid)]"
        Write-Output "         signed in at a desktop: $signedIn   |   profile registry: $hiveTxt"
        $drives = @(Get-NetDriveKeys $hive) | Sort-Object Letter
        if ($drives.Count -eq 0) {
            Write-Output "         no saved mapped drives"
        } else {
            foreach ($d in $drives) {
                $cred = ''
                if ($d.UserName -and $d.UserName -ne '0') { $cred = "   (connects as $($d.UserName))" }
                Write-Output ("         {0}:  {1}{2}" -f $d.Letter, $d.RemotePath, $cred)
            }
        }
    } catch {
        Write-Output "  ERROR for $($t.Sid): $($_.Exception.Message)"
    } finally {
        Close-UserHive $hive
    }
}
Write-Output ""
Write-Output "  Note: this lists what is SAVED in the profile (reconnected at every sign-in). Whether a drive is connected"
Write-Output "  right now is only visible inside that user's own session -- ask them to open This PC, or check for a red X."
""",
        "danger": False,
    },

    # ─── v3.7 additions ──────────────────────────────────────────────────────
    {
        "id": 'rt_vss_resize_storage',
        "label": 'Resize VSS Shadow Storage (Max Size)',
        "category": 'Remote Tools',
        "description": 'vssadmin resize shadowstorage /for= /on= /maxsize= -- set the storage cap for shadow copies on a volume (shrinking may delete the oldest copies)',
        "params": [
            {'key': 'VOLUME', 'kind': 'drive', 'label': 'Volume', 'required': True, 'default': 'C'},
            {'key': 'MAXSIZE', 'kind': 'vsssize', 'label': 'Max size (e.g. 10%, 20GB, 51200MB, UNBOUNDED)', 'required': True, 'default': '10%', 'help': '10% | 20GB | 51200MB | UNBOUNDED  (minimum 1MB)'}
        ],
        "command": r"""
$vol = "{{VOLUME}}"
$size = "{{MAXSIZE}}"
Write-Output "  === BEFORE (volume $vol) ==="
vssadmin list shadowstorage /for=$vol 2>&1 | ForEach-Object { Write-Output "  $_" }
Write-Output ""
Write-Output "  Setting maximum shadow storage on $vol to $size ..."
$out = vssadmin resize shadowstorage /for=$vol /on=$vol /maxsize=$size 2>&1
$out | ForEach-Object { Write-Output "  $_" }
if ($LASTEXITCODE -ne 0) {
    Write-Output "  RESIZE FAILED (exit $LASTEXITCODE). Typical causes: no shadow storage association exists yet for this volume"
    Write-Output "  (create a shadow copy first), the size is below 1MB, or the volume letter is wrong."
}
Write-Output ""
Write-Output "  === AFTER ==="
vssadmin list shadowstorage /for=$vol 2>&1 | ForEach-Object { Write-Output "  $_" }
""",
        "danger": True,
    },
    {
        "id": 'run_dism_restorehealth',
        "label": 'DISM RestoreHealth (Repair Component Store)',
        "category": 'Windows Health',
        "description": 'DISM /Online /Cleanup-Image /RestoreHealth -- repairs a corrupt component store from Windows Update; can take 10-30 min (runs detached, tool waits)',
        "long": True,
        "command": r"""
Write-Output "  Running DISM RestoreHealth (needs the target to reach Windows Update or a repair source)..."
DISM /Online /Cleanup-Image /RestoreHealth 2>&1 | ForEach-Object { if ($_ -and "$_".Trim()) { Write-Output "  $_" } }
Write-Output "  DISM exit code: $LASTEXITCODE  (0 = success, 3010 = success but reboot needed)"
Write-Output "  Tip: run 'Run System File Checker (SFC)' afterwards."
""",
        "danger": True,
    },
    {
        "id": 'dism_component_cleanup',
        "label": 'DISM Component Store Cleanup (WinSxS)',
        "category": 'Windows Health',
        "description": 'DISM /AnalyzeComponentStore then /StartComponentCleanup -- reclaims space from superseded updates (optionally /ResetBase)',
        "long": True,
        "params": [
            {'key': 'RESET_BASE', 'kind': 'bool', 'label': 'Also /ResetBase (permanent: installed updates can no longer be uninstalled)', 'required': True, 'default': 'false', 'help': 'Leave unchecked unless you need the extra space; ResetBase cannot be undone'}
        ],
        "command": r"""
$resetBase = {{RESET_BASE}}
Write-Output "  === ANALYZE COMPONENT STORE ==="
DISM /Online /Cleanup-Image /AnalyzeComponentStore 2>&1 | ForEach-Object { if ($_ -and "$_".Trim()) { Write-Output "  $_" } }
Write-Output ""
if ($resetBase) {
    Write-Output "  === START COMPONENT CLEANUP /ResetBase ==="
    DISM /Online /Cleanup-Image /StartComponentCleanup /ResetBase 2>&1 | ForEach-Object { if ($_ -and "$_".Trim()) { Write-Output "  $_" } }
} else {
    Write-Output "  === START COMPONENT CLEANUP ==="
    DISM /Online /Cleanup-Image /StartComponentCleanup 2>&1 | ForEach-Object { if ($_ -and "$_".Trim()) { Write-Output "  $_" } }
}
Write-Output "  DISM exit code: $LASTEXITCODE"
""",
        "danger": True,
    },
    {
        "id": 'perf_hardware_report_cim',
        "label": 'Hardware Inventory via CIM (WMIC Replacement)',
        "category": 'Performance',
        "description": "CPU, RAM modules, disks, BIOS, GPU, board -- what 'wmic cpu/memorychip/diskdrive/bios get' used to show (WMIC is removed on Win11 24H2+)",
        "command": r"""
Write-Output "  === CPU ==="
Get-CimInstance Win32_Processor | ForEach-Object { Write-Output "  $($_.Name.Trim())  cores=$($_.NumberOfCores) threads=$($_.NumberOfLogicalProcessors) maxMHz=$($_.MaxClockSpeed) load=$($_.LoadPercentage)%" }
Write-Output "  === MEMORY MODULES ==="
Get-CimInstance Win32_PhysicalMemory | ForEach-Object { Write-Output "  $($_.DeviceLocator): $([math]::Round($_.Capacity/1GB,1)) GB  $($_.Speed) MHz  $($_.Manufacturer)" }
$os = Get-CimInstance Win32_OperatingSystem
Write-Output "  RAM free now: $([math]::Round($os.FreePhysicalMemory/1MB,2)) GB of $([math]::Round($os.TotalVisibleMemorySize/1MB,2)) GB"
Write-Output "  === DISKS ==="
Get-CimInstance Win32_DiskDrive | ForEach-Object { Write-Output "  $($_.Model)  $([math]::Round($_.Size/1GB,0)) GB  status=$($_.Status)  iface=$($_.InterfaceType)" }
Write-Output "  === BIOS / BOARD ==="
$b = Get-CimInstance Win32_BIOS; Write-Output "  BIOS: $($b.Manufacturer) $($b.SMBIOSBIOSVersion)  serial=$($b.SerialNumber)"
$bb = Get-CimInstance Win32_BaseBoard; Write-Output "  Board: $($bb.Manufacturer) $($bb.Product)"
Write-Output "  === GPU ==="
Get-CimInstance Win32_VideoController | ForEach-Object { Write-Output "  $($_.Name)  driver=$($_.DriverVersion)" }
""",
        "danger": False,
    },
    {
        "id": 'perf_trim_ssd',
        "label": 'Retrim an SSD Volume (Optimize-Volume -ReTrim)',
        "category": 'Performance',
        "description": 'Optimize-Volume -ReTrim -- tells the SSD which blocks are free (skips safely on HDDs)',
        "params": [
            {'key': 'VOLUME', 'kind': 'drive', 'label': 'Drive letter', 'required': True, 'default': 'C'}
        ],
        "command": r"""
$vol = "{{VOLUME}}".TrimEnd(':')
$v = Get-Volume -DriveLetter $vol -ErrorAction SilentlyContinue
if (-not $v) { Write-Output "  Volume $vol`: not found."; return }
$part = Get-Partition -DriveLetter $vol -ErrorAction SilentlyContinue
$disk = if ($part) { Get-PhysicalDisk -ErrorAction SilentlyContinue | Where-Object { $_.DeviceId -eq $part.DiskNumber } } else { $null }
Write-Output "  Volume $vol`: media type = $(if ($disk) { $disk.MediaType } else { 'unknown' })"
if ($disk -and $disk.MediaType -eq 'HDD') { Write-Output "  This is a spinning disk -- ReTrim does not apply. Use 'Defragment' instead. Nothing done."; return }
Optimize-Volume -DriveLetter $vol -ReTrim -ErrorAction SilentlyContinue -Verbose 4>&1 | ForEach-Object { Write-Output "  $_" }
Write-Output "  Retrim finished."
""",
        "danger": False,
    },
    {
        "id": 'perf_wmi_verify_repository',
        "label": 'Verify WMI Repository Health (winmgmt)',
        "category": 'Performance',
        "description": 'winmgmt /verifyrepository -- a corrupt WMI repository makes CIM/WMI-based operations and monitoring slow or failing (read-only check)',
        "command": r"""
Write-Output "  Verifying the WMI repository (read-only)..."
$r = winmgmt /verifyrepository 2>&1
$r | ForEach-Object { Write-Output "  $_" }
if (($r | Out-String) -match 'inconsistent') { Write-Output "  Repository is INCONSISTENT -- consider 'winmgmt /salvagerepository' on the target (Admin), then a restart." }
""",
        "danger": False,
    },
    {
        "id": 'perf_rebuild_perf_counters',
        "label": 'Rebuild Performance Counters (lodctr /R)',
        "category": 'Performance',
        "description": 'lodctr /R -- rebuilds a corrupt performance-counter registry (fixes empty/blank Task Manager, perfmon and monitoring-agent counters)',
        "command": r"""
Write-Output "  Rebuilding performance counters (lodctr /R)..."
$r = lodctr /R 2>&1
$r | ForEach-Object { Write-Output "  $_" }
Write-Output "  Re-syncing with WMI performance adapter..."
winmgmt /resyncperf 2>&1 | ForEach-Object { Write-Output "  $_" }
Write-Output "  Done. Monitoring tools may need a restart to pick the counters up."
""",
        "danger": True,
    },
    {
        "id": 'chkdsk_online_scan',
        "label": 'CHKDSK Online Scan (Read-Only)',
        "category": 'Disk',
        "description": 'chkdsk X: /scan -- online, read-only scan of a volume for file-system errors (no dismount, no repair; runs detached, tool waits)',
        "long": True,
        "params": [
            {'key': 'VOLUME', 'kind': 'drive', 'label': 'Drive letter', 'required': True, 'default': 'C'}
        ],
        "command": r"""
$vol = "{{VOLUME}}"
Write-Output "  Online read-only scan of $vol (this can take several minutes)..."
chkdsk $vol /scan 2>&1 | ForEach-Object { if ($_ -and "$_".Trim()) { Write-Output "  $_" } }
Write-Output "  chkdsk exit code: $LASTEXITCODE  (0 = no errors, 1 = errors found/fixed, 2/3 = cleanup needed)"
""",
        "danger": False,
    },

    # ─── ADMIN CONSOLES (v3.7) ───────────────────────────────────────────────
    {
        "id": 'rt_open_computer_management',
        "label": 'Open Computer Management (Connected to Target)',
        "category": 'Admin Consoles',
        "description": 'mmc compmgmt.msc /computer:\\\\<target> -- Disk Management, Device Manager (read-only), Event Viewer, Services, Shared Folders, Task Scheduler in one console',
        "command": r"""
# Handled by the host application (launch_console) -- never sent to the target.
Write-Output "  (local console launcher)"
""",
        "danger": False,
    },
    {
        "id": 'ac_open_disk_management',
        "label": 'Open Disk Management (Connected to Target)',
        "category": 'Admin Consoles',
        "description": 'mmc diskmgmt.msc /computer:\\\\<target> -- partitions, volumes, drive letters, extend/shrink',
        "command": r"""
# Handled by the host application (launch_console) -- never sent to the target.
Write-Output "  (local console launcher)"
""",
        "danger": False,
    },
    {
        "id": 'ac_open_device_manager',
        "label": 'Open Device Manager (Connected to Target, Read-Only on Win8+)',
        "category": 'Admin Consoles',
        "description": 'mmc devmgmt.msc /computer:\\\\<target> -- Windows 8 / Server 2012 and later only let you VIEW remote devices; use Remote Desktop to change drivers',
        "command": r"""
# Handled by the host application (launch_console) -- never sent to the target.
Write-Output "  (local console launcher)"
""",
        "danger": False,
    },
    {
        "id": 'ac_open_services',
        "label": 'Open Services Console (Connected to Target)',
        "category": 'Admin Consoles',
        "description": 'mmc services.msc /computer:\\\\<target> -- start/stop/configure services on the target',
        "command": r"""
# Handled by the host application (launch_console) -- never sent to the target.
Write-Output "  (local console launcher)"
""",
        "danger": False,
    },
    {
        "id": 'ac_open_event_viewer',
        "label": 'Open Event Viewer (Connected to Target)',
        "category": 'Admin Consoles',
        "description": "mmc eventvwr.msc /computer:<target> -- browse the target's Windows logs",
        "command": r"""
# Handled by the host application (launch_console) -- never sent to the target.
Write-Output "  (local console launcher)"
""",
        "danger": False,
    },
    {
        "id": 'ac_open_shared_folders',
        "label": 'Open Shared Folders Console (Connected to Target)',
        "category": 'Admin Consoles',
        "description": 'mmc fsmgmt.msc /computer:\\\\<target> -- shares, open sessions, open files',
        "command": r"""
# Handled by the host application (launch_console) -- never sent to the target.
Write-Output "  (local console launcher)"
""",
        "danger": False,
    },
    {
        "id": 'ac_open_admin_share',
        "label": 'Open C$ Admin Share in File Explorer',
        "category": 'Admin Consoles',
        "description": "explorer \\\\<target>\\C$ -- browse the target's system drive using the supplied admin credentials",
        "command": r"""
# Handled by the host application (launch_console) -- never sent to the target.
Write-Output "  (local console launcher)"
""",
        "danger": False,
    },
    {
        "id": 'ac_open_firewall',
        "label": 'Open Windows Firewall with Advanced Security (Guided)',
        "category": 'Admin Consoles',
        "description": 'wf.msc has no remote switch -- opens the console and tells you the 3 clicks to connect it to the target',
        "command": r"""
# Handled by the host application (launch_console) -- never sent to the target.
Write-Output "  (local console launcher)"
""",
        "danger": False,
    },
    {
        "id": 'ac_open_remote_shell',
        "label": 'Open Remote PowerShell Window on Target (Enter-PSSession)',
        "category": 'Admin Consoles',
        "description": 'New PowerShell window already connected to the target -- run any admin command (cleanmgr /sagerun, defrag, netsh, ...) there',
        "command": r"""
# Handled by the host application (launch_console) -- never sent to the target.
Write-Output "  (local console launcher)"
""",
        "danger": False,
    },
    {
        "id": 'ac_open_remote_cmd',
        "label": 'Open Remote Command Prompt on Target (winrs)',
        "category": 'Admin Consoles',
        "description": 'New cmd window running on the target through WinRM (winrs) -- asks for the password in that window',
        "command": r"""
# Handled by the host application (launch_console) -- never sent to the target.
Write-Output "  (local console launcher)"
""",
        "danger": False,
    },
    {
        "id": 'ac_open_rdp',
        "label": 'Open Remote Desktop to Target (Credentials Pre-Loaded)',
        "category": 'Admin Consoles',
        "description": 'mstsc /v:<target> with the supplied credentials stored -- the only way to use GUI-only tools remotely: Device Manager (full), Disk Cleanup, Defrag, Firewall, Network Connections',
        "command": r"""
# Handled by the host application (launch_console) -- never sent to the target.
Write-Output "  (local console launcher)"
""",
        "danger": False,
    },
]

CATEGORIES = list(dict.fromkeys(o["category"] for o in OPERATIONS))
assert len(OPERATIONS) == 85, f"Expected 85 operations, got {len(OPERATIONS)}"
assert len({o['id'] for o in OPERATIONS}) == 85, "Duplicate operation id detected"

# ══════════════════════════════════════════════════════════════════════════
#  PARAMETERIZED OPERATIONS -- validation + {{TOKEN}} substitution
#  v3.2: 16 of the 67 operations need a runtime value instead of running a
#  fixed script. Kept byte-for-byte identical to app.py's copy of this same
#  logic (see that file for the full design rationale). Every value is
#  checked against an allow-list regex for its declared "kind" BEFORE
#  substitution -- a value that doesn't match is rejected outright.
# ══════════════════════════════════════════════════════════════════════════
def _cidr_to_mask(n):
    bits = "1" * n + "0" * (32 - n)
    return ".".join(str(int(bits[i:i + 8], 2)) for i in range(0, 32, 8))


_IPV4_RE = re.compile(
    r"^(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])"
    r"(\.(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])){3}$"
)
_COMPUTERNAME_RE = re.compile(r"^[A-Za-z0-9]([A-Za-z0-9-]{0,13}[A-Za-z0-9])?$")
_ADAPTERNAME_RE = re.compile(r"^[A-Za-z0-9 ()./#_-]{1,64}$")
_SERVICENAME_RE = re.compile(r"^[A-Za-z0-9 _.$#+()-]{1,256}$")
_TASKNAME_RE = re.compile(r"^[A-Za-z0-9 _.\\-]{1,200}$")
_DEVICEID_RE = re.compile(r"^[A-Za-z0-9\\&_{}-]{1,300}$")
_DRIVE_RE = re.compile(r"^[A-Za-z]$")
# v3.2 -- network drive mapping kinds. Same reject-don't-escape rule as every other kind.
#   uncpath     \\server\share[\sub\folder]  (no quotes, ; | % ^ = [ ] * ? or ".." segments)
#   mapdrive    one letter D-Z, optional colon (A, B, C are reserved)
#   useraccount DOMAIN\user | user@domain | .\localuser | bare user
_UNCPATH_RE = re.compile(
    r"^\\\\[A-Za-z0-9][A-Za-z0-9._-]{0,200}"
    r"(?:\\(?!\.+(?:\\|$))[A-Za-z0-9 _.$#@&+(),~-]{1,80}){1,30}$"
)
_MAPDRIVE_RE = re.compile(r"^[D-Zd-z]:?$")
_USERACCOUNT_RE = re.compile(
    r"^(?:(?:\.|[A-Za-z0-9][A-Za-z0-9._-]{0,62})\\)?[A-Za-z0-9_.-][A-Za-z0-9 _.-]{0,63}$"
    r"|^[A-Za-z0-9._-]{1,64}@[A-Za-z0-9][A-Za-z0-9.-]{0,252}$"
)


def _validate_ipv4(raw):
    raw = raw.strip()
    if not _IPV4_RE.match(raw):
        return None, f"'{raw}' is not a valid IPv4 address (expected e.g. 192.168.1.100)"
    return raw, None


def _validate_subnetmask(raw):
    raw = raw.strip()
    if raw.isdigit() and 0 <= int(raw) <= 32:
        return _cidr_to_mask(int(raw)), None
    if _IPV4_RE.match(raw):
        return raw, None
    return None, f"'{raw}' is not a valid subnet mask (expected e.g. 255.255.255.0 or CIDR like 24)"


def _validate_computername(raw):
    raw = raw.strip()
    if not _COMPUTERNAME_RE.match(raw):
        return None, f"'{raw}' is not a valid computer name (1-15 letters/digits/hyphens, can't start/end with a hyphen)"
    return raw, None


def _validate_adaptername(raw):
    raw = raw.strip()
    if not _ADAPTERNAME_RE.match(raw):
        return None, f"'{raw}' contains characters not allowed in an adapter name"
    return raw, None


def _validate_servicename(raw):
    # v3.2: real service Names contain spaces ("ManageEngine UEMS - Agent") and often $ or #
    # (MSSQL$SQLEXPRESS, MSSQL$MICROSOFT##WID). The command body treats the value as a
    # SINGLE-quoted PowerShell literal, so none of these can expand or execute. Wildcards
    # (* ? [ ]), quotes, backticks, ; | & < > \ / are still rejected outright.
    raw = raw.strip()
    if not _SERVICENAME_RE.match(raw):
        return None, (f"'{raw}' is not a valid service Name (letters, digits, spaces and _ . - $ # + ( ) only, "
                      f"max 256 characters -- copy the Name exactly from 'List All Services'; it can differ from the Display Name)")
    return raw, None


def _validate_taskname(raw):
    raw = raw.strip()
    if not _TASKNAME_RE.match(raw):
        return None, f"'{raw}' contains characters not allowed in a task name"
    return raw, None


def _validate_deviceid(raw):
    raw = raw.strip()
    if not _DEVICEID_RE.match(raw):
        return None, f"'{raw}' doesn't look like a PNP Instance ID (copy it exactly from a device list report)"
    return raw, None


def _validate_drive(raw):
    raw = raw.strip().rstrip(":").upper()
    if raw == "":
        return "", None  # only reached when the param is optional
    if not _DRIVE_RE.match(raw):
        return None, f"'{raw}' is not a single drive letter (expected e.g. C)"
    return raw + ":", None


def _validate_uncpath(raw):
    shown = raw.strip()
    raw = shown.rstrip("\\")  # tolerate a pasted trailing backslash
    if len(raw) > 260 or not _UNCPATH_RE.match(raw):
        return None, (f"'{shown}' is not a valid shared-folder path (expected \\\\server\\share or "
                      f"\\\\server\\share\\folder -- backslashes, no quotes and none of ; | % ^ = [ ] * ?)")
    return raw, None


def _validate_mapdrive(raw):
    raw = raw.strip()
    if not _MAPDRIVE_RE.match(raw):
        return None, f"'{raw}' is not a usable drive letter (choose D to Z -- A, B and C are reserved)"
    return raw[0].upper() + ":", None


def _validate_useraccount(raw):
    raw = raw.strip()
    if not _USERACCOUNT_RE.match(raw):
        return None, f"'{raw}' is not a valid Windows account (use DOMAIN\\username, username@domain.com or .\\localuser)"
    return raw, None


def _validate_bool(raw):
    v = raw.strip().lower()
    if v in ("true", "1", "yes", "on"):
        return "$true", None
    if v in ("false", "0", "no", "off", ""):
        return "$false", None
    return None, f"'{raw}' is not a valid true/false value"


_VSSSIZE_RE = re.compile(r"^(UNBOUNDED|\d{1,3}%|\d{1,9}(KB|MB|GB|TB|PB|EB))$", re.IGNORECASE)


def _validate_vsssize(raw):
    raw = raw.strip().upper().replace(" ", "")
    if not _VSSSIZE_RE.match(raw):
        return None, f"'{raw}' is not a valid shadow-storage size (use e.g. 10%, 20GB, 51200MB or UNBOUNDED)"
    if raw.endswith("%") and not (1 <= int(raw[:-1]) <= 100):
        return None, "a percentage must be between 1% and 100%"
    return raw, None


PARAM_VALIDATORS = {
    "ipv4": _validate_ipv4,
    "subnetmask": _validate_subnetmask,
    "computername": _validate_computername,
    "adaptername": _validate_adaptername,
    "servicename": _validate_servicename,
    "taskname": _validate_taskname,
    "deviceid": _validate_deviceid,
    "drive": _validate_drive,
    "uncpath": _validate_uncpath,
    "mapdrive": _validate_mapdrive,
    "useraccount": _validate_useraccount,
    "bool": _validate_bool,
    "vsssize": _validate_vsssize,
}


def validate_and_substitute(op, values):
    """(op, {KEY: raw}) -> (final_command_text, error_or_None). See app.py."""
    command = op["command"]
    for p in op.get("params", []):
        key = p["key"]
        raw = (values.get(key) or "").strip()
        if not raw:
            if p.get("default"):
                raw = p["default"]
            elif p.get("required", True):
                return None, f"Missing required value: {p['label']}"
            else:
                command = command.replace("{{%s}}" % key, "")
                continue
        validator = PARAM_VALIDATORS[p["kind"]]
        clean, err = validator(raw)
        if err:
            return None, f"{p['label']}: {err}"
        command = command.replace("{{%s}}" % key, clean)
    return command, None


TRANSPORTS = [
    ("Windows Domain (NTLM) -- Recommended", "ntlm"),
    ("Workgroup / Local Account (Basic)",    "basic"),
    ("Active Directory (Kerberos)",          "kerberos"),
    ("Admin Double-Hop (CredSSP)",           "credssp"),
]

# ══════════════════════════════════════════════════════════════════════════
#  WINRM HELPERS  (same execution model as app.py: EncodedCommand via run_cmd,
#  plus automatic session reconnect on timeout/connection loss)
# ══════════════════════════════════════════════════════════════════════════
def make_session(hostname, username, password, transport="ntlm", fast=False):
    """
    Returns a pypsrp.client.Client -- a real PSRP (PowerShell Remoting
    Protocol) client, identical in spirit to what New-PSSession/
    Invoke-Command use natively in the PowerShell edition. Nothing here
    actually connects yet; the first execute_ps() call opens the runspace.

    transport accepts the exact same strings already used by the "Auth
    Transport" dropdown ("ntlm"/"basic"/"kerberos"/"credssp") -- pypsrp's
    `auth` parameter uses this identical vocabulary, so no translation is
    needed.

    Basic auth is a special case: unlike ntlm/kerberos/credssp/negotiate,
    it has no protocol-level message encryption of its own, so pypsrp
    refuses to construct a WSMan client for it with the default
    encryption="auto" over plain HTTP (raises ValueError immediately --
    caught this in testing before it ever reached a real target). This
    tool has always used plain HTTP for every transport, so Basic auth's
    credentials were already unprotected at the transport layer either
    way; encryption="never" here just makes that pre-existing, already-
    accepted posture explicit for the one auth mode where it actually
    matters, instead of the whole client failing to construct.
    """
    kwargs = dict(
        username=username,
        password=password,
        auth=transport,
        ssl=False,
        port=5985,
        connection_timeout=30,
        read_timeout=180,
        operation_timeout=170,
    )
    if fast:
        kwargs.update(connection_timeout=10, read_timeout=30, operation_timeout=20)
    if transport == "basic":
        kwargs["encryption"] = "never"
    return Client(hostname, **kwargs)


def run_remote_ps(session, script):
    """
    Execute a PowerShell script on the remote host over real PSRP
    (Fix #18) -- mirrors app.py's run_remote_ps exactly; keep both in sync.

    Why this replaced the old -EncodedCommand/chunked-temp-file engine:
    that approach was hand-rolling, at the application layer, exactly what
    the PSRP protocol already does correctly and natively --
    fragmenting arbitrarily large scripts, keeping Success/Error/Warning/
    Verbose/Debug/Progress cleanly separated, and transporting Unicode
    without any file-encoding guesswork. Every one of Fix #6, #7, #11,
    #12, and #17 was a real bug in that hand-rolled machinery; PSRP simply
    doesn't have that class of bug, because it was never re-implementing
    process-spawn/command-line/file-encoding semantics in the first place.
    Concretely, this also means: no command-line-length limit of any kind
    (so no minify/chunk/adaptive-retry machinery needed), no temp files
    written to the target for script delivery (so a near-full disk on the
    target no longer breaks every single operation), and no CLIXML text
    to parse (errors arrive as properly typed, cleanly str()-able
    ErrorRecord objects, and Progress records never mix into them).

    Verified against pypsrp's own recorded real-WinRM-server test fixtures
    (test_client_execute_ps / test_client_execute_ps_failure) rather than
    just the docs -- see the bug-fix history for details.

    NOTE (Fix #19): the preamble deliberately does NOT set
    [Console]::OutputEncoding. That line was carried over unchanged from
    the old -EncodedCommand engine, where it mattered because output was
    captured as a raw console byte stream. Real PSRP sessions run inside
    a RunspacePool with no console at all -- touching [Console] there
    throws "Exception setting 'OutputEncoding': 'The handle is invalid.'"
    on every single call, which is exactly what broke every task after
    Fix #18 shipped. PSRP transports Write-Output/Write-Host text
    correctly on its own regardless of any encoding preference (confirmed
    against multiple independent real-world reports of this exact error
    in remote PSSessions) -- do not add this line back.
    """
    preamble = (
        "$ErrorActionPreference = 'Continue'\n"
        "$ProgressPreference = 'SilentlyContinue'\n"
        "$WarningPreference = 'SilentlyContinue'\n"
    )
    try:
        output, streams, had_errors = session.execute_ps(preamble + script)
        error_lines = [str(e).strip() for e in streams.error if str(e).strip()]
        success = not had_errors
        return output, "\n".join(error_lines), success
    except AuthenticationError:
        return "", "CRED_ERR:Invalid username or password", False
    except (WinRMTransportError, WSManFaultError) as e:
        return "", f"TRANSPORT_ERR:{e}", False
    except (requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout):
        return "", "TIMEOUT_ERR:Operation timed out after 170 seconds", False
    except requests.exceptions.ConnectionError as e:
        return "", f"TRANSPORT_ERR:{e}", False
    except Exception as e:
        return "", f"ERR:{e}", False


_stop_flag = threading.Event()   # shared with PCAdminApp.stop_flag

# ══════════════════════════════════════════════════════════════════════════════
#  v3.7  RESILIENCE ENGINE  (network blips, reboots, long tasks, credentials)
# ══════════════════════════════════════════════════════════════════════════════
# Why this exists: an operation that briefly drops the target's network (flush
# DNS, set static IP, set DHCP, adapter restart, TCP/IP reset) kills the TCP
# connection under the in-flight WinRM call. The old code then sat on a dead
# socket (pypsrp retries a read timeout 5 times x 180 s) and the session was
# never usable again until the app was restarted. Now such operations are
# started DETACHED on the target (Win32_Process.Create, which lives outside the
# WinRM shell, so it survives the shell dying), their output goes to a file on
# the target, and this tool polls with short timeouts, reconnecting with
# back-off, until the file says "done" -- then returns the real output.
NETWORK_BLIP_OPS = {
    "rt_set_static_ip", "rt_set_dhcp", "reset_network", "flush_dns",
    "pr_restart_all_adapters", "pr_restart_named_adapter", "pr_disable_enable_adapter",
}
REBOOT_OPS = {"pr_force_restart", "pr_force_signout_restart", "pr_full_soft_recycle"}
CONDITIONAL_REBOOT_OPS = {"rt_rename_pc_domain", "rt_rename_pc_workgroup"}
REBOOT_MARKERS = ("restarts in 15 seconds", "Restarting the computer now",
                  "Forcing an immediate restart", "Signing out and restarting now")
RECONNECT_ATTEMPTS = 8
RECONNECT_WAIT_SECONDS = 4
DETACH_BLIP_WAIT = 300      # seconds to wait for a network-changing op to finish + target to return
DETACH_LONG_WAIT = 3600     # DISM / CHKDSK
DETACH_POLL_SECONDS = 3


def _ev(d):
    return d


def build_cred_prelude(username, password):
    """
    PowerShell text that rebuilds the connection's own username/password as a
    real PSCredential ($__cred) INSIDE the remote session. Needed by domain
    rename: Rename-Computer -DomainCredential must authenticate to a domain
    controller itself -- the session's NTLM network logon can't be forwarded
    (the "double hop"), which is why every rename variant failed with
    "Access is denied". Values are base64 so no quoting/escaping problem can
    exist; the script travels inside the encrypted PSRP channel (NTLM/Kerberos/
    CredSSP message encryption), the password is never printed, logged or
    placed on any command line.
    """
    u = base64.b64encode(username.encode("utf-8")).decode("ascii")
    p = base64.b64encode(password.encode("utf-8")).decode("ascii")
    return (
        f"$__u = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{u}'))\n"
        f"$__p = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{p}'))\n"
        "$__cred = New-Object System.Management.Automation.PSCredential($__u, (ConvertTo-SecureString $__p -AsPlainText -Force))\n"
        "Remove-Variable __p, __u -ErrorAction SilentlyContinue\n"
    )


def expects_reboot(op_id, params):
    if op_id in ("pr_force_restart", "pr_force_signout_restart"):
        return True
    if op_id == "pr_full_soft_recycle":
        v = (params or {}).get("AUTO_RESTART", "true").strip().lower()
        return v not in ("false", "0", "no", "off")
    return False


def reconnect_gen(hosts, username, password, transport, log=lambda s: None,
                  attempts=None):
    """Generator: yields SSE strings while waiting; returns (session, host) or (None, None)."""
    attempts = attempts or RECONNECT_ATTEMPTS
    for n in range(1, attempts + 1):
        if _stop_flag.is_set():
            return None, None
        for h in hosts:
            try:
                s = make_session(h, username, password, transport, fast=True)
                out, err, ok = run_remote_ps(s, 'Write-Output "RECONNECT_OK"')
                if ok and "RECONNECT_OK" in out:
                    return s, h
                if err.startswith("CRED_ERR"):
                    return None, None
            except Exception:
                pass
        msg = f"    Waiting for the target to come back... attempt {n}/{attempts}"
        log(msg)
        yield _ev({"type": "dim", "text": msg})
        time.sleep(RECONNECT_WAIT_SECONDS)
    return None, None


def _detach_launch_script(tok, body):
    wrapper = (
        "$ErrorActionPreference = 'Continue'\n$ProgressPreference = 'SilentlyContinue'\n$WarningPreference = 'SilentlyContinue'\n"
        "$__base = $PSCommandPath -replace '\\.ps1$',''\n"
        "$__o = $__base + '.out.txt'\n$__d = $__base + '.done.txt'\n"
        "try {\n  & {\n" + body + "\n  } *>&1 | ForEach-Object { \"$_\" } | Out-File -FilePath $__o -Encoding utf8\n"
        "} catch { (\"ERROR: \" + $_.Exception.Message) | Out-File -FilePath $__o -Append -Encoding utf8 }\n"
        "'done' | Out-File -FilePath $__d -Encoding ascii\n"
    )
    b64 = base64.b64encode(b"\xef\xbb\xbf" + wrapper.encode("utf-8")).decode("ascii")
    return (
        f"$tok = '{tok}'\n"
        "$dir = Join-Path $env:windir 'Temp'\n"
        "$ps1 = Join-Path $dir ('pcat_' + $tok + '.ps1')\n"
        f"[IO.File]::WriteAllBytes($ps1, [Convert]::FromBase64String('{b64}'))\n"
        "$cl = 'powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File \"' + $ps1 + '\"'\n"
        "$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cl }\n"
        "if ($r.ReturnValue -eq 0) { Write-Output ('PCAT_LAUNCHED:' + $r.ProcessId) } else { Write-Output ('PCAT_LAUNCH_FAIL:' + $r.ReturnValue) }\n"
    )


def _detach_poll_script(tok):
    return (
        "$b = Join-Path (Join-Path $env:windir 'Temp') 'pcat_" + tok + "'\n"
        "if (Test-Path ($b + '.done.txt')) {\n"
        "  if (Test-Path ($b + '.out.txt')) { Get-Content ($b + '.out.txt') -Raw -Encoding UTF8 }\n"
        "  Write-Output 'PCAT_DONE'\n"
        "} else { Write-Output 'PCAT_PENDING' }\n"
    )


def _detach_cleanup_script(tok):
    return ("$b = Join-Path (Join-Path $env:windir 'Temp') 'pcat_" + tok + "'\n"
            "Remove-Item ($b + '.*') -Force -ErrorAction SilentlyContinue\n")


def detached_run_gen(session, hosts, username, password, transport, body,
                     max_wait, log=lambda s: None):
    """
    Generator. Yields SSE strings; returns (stdout, stderr, success, host_used).
    """
    tok = secrets.token_hex(6)
    cur, cur_host = session, hosts[0]
    out, err, ok = run_remote_ps(cur, _detach_launch_script(tok, body))
    if not ok or "PCAT_LAUNCHED" not in out:
        return out, (err or "Could not start the detached task on the target: " + out.strip()), False, cur_host
    started = time.time()
    deadline = started + max_wait
    last_note = started
    interrupted = False
    while time.time() < deadline:
        if _stop_flag.is_set():
            return "", "STOPPED: the task keeps running on the target; its output file stays in %windir%\\Temp\\pcat_" + tok + ".out.txt", False, cur_host
        o, e, ok2 = run_remote_ps(cur, _detach_poll_script(tok))
        if ok2:
            if interrupted:
                msg = f"    Reconnected to {cur_host}."
                log(msg); yield _ev({"type": "success", "text": msg}); interrupted = False
            if o.rstrip().endswith("PCAT_DONE"):
                text = o.rstrip()[:-len("PCAT_DONE")]
                run_remote_ps(cur, _detach_cleanup_script(tok))
                return text, "", True, cur_host
            now = time.time()
            if now - last_note >= 30:
                last_note = now
                msg = f"    ...still running on the target ({int(now - started)}s)"
                log(msg); yield _ev({"type": "dim", "text": msg})
            time.sleep(DETACH_POLL_SECONDS)
            continue
        if e.startswith("CRED_ERR"):
            return "", e, False, cur_host
        if not interrupted:
            interrupted = True
            msg = "    Connection to the target interrupted (expected for network changes) -- reconnecting..."
            log(msg); yield _ev({"type": "warning", "text": msg})
        s2, h2 = yield from reconnect_gen(hosts, username, password, transport, log=log,
                                          attempts=3)
        if s2 is not None:
            cur, cur_host = s2, h2
        else:
            time.sleep(RECONNECT_WAIT_SECONDS)
    text = ("  The target did not report completion within %d s.\n"
            "  The change was started on the target and has most likely been applied.\n"
            "  If you changed the IP address and connected by IP, reconnect to the NEW address.\n" % max_wait)
    return text, "TIMEOUT_ERR:no completion marker from the target", False, cur_host



# ══════════════════════════════════════════════════════════════════════════════
#  v3.7  ADMIN CONSOLES  (category "Admin Consoles")
# ══════════════════════════════════════════════════════════════════════════════
# These open a window on the machine HOSTING this service (a web server cannot
# open a window on a remote browser's screen -- hard OS limit). Run the Web
# edition on your own admin PC and they appear on your screen. Credentials are
# supplied to Windows in the way each tool supports:
#   * MMC consoles / Explorer : "net use \\host\IPC$" first -- MMC and Explorer
#                               reuse that authenticated session.
#   * Remote Desktop          : cmdkey TERMSRV/<host> (mstsc reads it).
#   * PowerShell window       : password handed over in the child's environment
#                               (never on a command line), then removed.
#   * winrs / Firewall        : prompt in the new window / manual connect.
CONSOLE_OP_IDS = {
    "rt_open_computer_management", "ac_open_disk_management", "ac_open_device_manager",
    "ac_open_services", "ac_open_event_viewer", "ac_open_shared_folders",
    "ac_open_admin_share", "ac_open_firewall", "ac_open_remote_shell",
    "ac_open_remote_cmd", "ac_open_rdp",
}
_MMC_TABLE = {
    "rt_open_computer_management": ("compmgmt.msc", "\\\\{h}"),
    "ac_open_disk_management":     ("diskmgmt.msc", "\\\\{h}"),
    "ac_open_device_manager":      ("devmgmt.msc",  "\\\\{h}"),
    "ac_open_services":            ("services.msc", "\\\\{h}"),
    "ac_open_event_viewer":         ("eventvwr.msc", "{h}"),
    "ac_open_shared_folders":      ("fsmgmt.msc",   "\\\\{h}"),
}
_HOST_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,253}$")
_NEW_CONSOLE = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)   # no flashing console from a .pyw / service


def _ps_quote(s):
    return "'" + s.replace("'", "''") + "'"


def _net_use_ipc(host, username, password):
    """Authenticate this PC to the target (IPC$) so MMC/Explorer inherit it. Returns a status line."""
    try:
        r = subprocess.run(["net", "use", f"\\\\{host}\\IPC$", f"/user:{username}", password,
                            "/persistent:no"],
                           capture_output=True, text=True, timeout=45, creationflags=_NO_WINDOW)
    except Exception as e:
        return f"Could not authenticate first ({e}); the console may ask you to sign in."
    if r.returncode == 0:
        return f"Authenticated to {host} as {username} (net use IPC$)."
    text = (r.stdout + r.stderr).replace(password, "********").strip().replace("\r", " ").replace("\n", " ")
    if "1219" in text:
        return (f"Windows already holds a connection to {host} under a different account (error 1219). "
                f"Run  net use \\\\{host}\\IPC$ /delete  on this PC, then try again. Detail: {text}")
    return f"Authentication to {host} failed: {text}"


def launch_console(op_id, host, username, password, transport):
    """Returns a list of message lines. Never includes the password."""
    if not _HOST_RE.match(host or ""):
        return [f"Refused: '{host}' is not a plain hostname/IP (letters, digits, . : - _ only)."]
    if any(ord(c) < 32 for c in username):
        return ["Refused: the username contains control characters."]
    if platform.system() != "Windows":
        return [f"This service is hosted on {platform.system()}, which cannot open Windows consoles --",
                "nothing was launched. Host the Web edition on a Windows admin PC, or use the",
                "Python GUI / PowerShell edition on your own PC."]
    lines = []
    try:
        if op_id in _MMC_TABLE:
            snap, tmpl = _MMC_TABLE[op_id]
            lines.append(_net_use_ipc(host, username, password))
            arg = "/computer:" + tmpl.format(h=host)
            subprocess.Popen(["mmc.exe", snap, arg])
            lines += [f"Launched: mmc.exe {snap} {arg}",
                      "It opened on the machine HOSTING this service (your screen if you browse from this PC).",
                      f"If the console shows the LOCAL computer instead, right-click its root node > Connect to another computer > {host}."]
            if op_id == "ac_open_device_manager":
                lines.append("Windows 8 / Server 2012 and later show remote devices read-only. For driver changes use 'Open Remote Desktop'.")
        elif op_id == "ac_open_admin_share":
            lines.append(_net_use_ipc(host, username, password))
            subprocess.Popen(["explorer.exe", f"\\\\{host}\\C$"])
            lines.append(f"Launched: explorer \\\\{host}\\C$")
        elif op_id == "ac_open_firewall":
            lines.append(_net_use_ipc(host, username, password))
            subprocess.Popen(["mmc.exe", "wf.msc"])
            lines += ["Launched Windows Firewall with Advanced Security (LOCAL view). To manage the TARGET:",
                      f"  1. Right-click 'Windows Defender Firewall with Advanced Security' (top-left node)",
                      f"  2. Choose 'Connect to Another Computer...'",
                      f"  3. Pick 'Another computer', type {host}, OK.",
                      "(The target must allow 'Windows Defender Firewall Remote Management' inbound.)"]
        elif op_id == "ac_open_remote_shell":
            auth = {"ntlm": "Negotiate", "kerberos": "Kerberos", "basic": "Basic", "credssp": "CredSSP"}.get(transport, "Negotiate")
            inner = (f"$u = {_ps_quote(username)}; "
                     "$sp = ConvertTo-SecureString $env:PCAT_PW -AsPlainText -Force; Remove-Item Env:PCAT_PW; "
                     "$cred = New-Object System.Management.Automation.PSCredential($u, $sp); "
                     f"Enter-PSSession -ComputerName {_ps_quote(host)} -Credential $cred -Authentication {auth}")
            env = dict(os.environ); env["PCAT_PW"] = password
            subprocess.Popen(["powershell.exe", "-NoExit", "-NoProfile", "-Command", inner],
                             env=env, creationflags=_NEW_CONSOLE)
            lines += [f"Launched a PowerShell window connected to {host} ({auth}).",
                      "Inside it, run anything: cleanmgr /sagerun:1, defrag C: /U, netsh advfirewall show allprofiles, Get-NetAdapter ...",
                      "If it says the host is not trusted: on THIS PC run (Admin)  Set-Item WSMan:\\localhost\\Client\\TrustedHosts -Value '" + host + "' -Concatenate -Force"]
        elif op_id == "ac_open_remote_cmd":
            subprocess.Popen(["cmd.exe", "/k", "winrs", f"-r:{host}", f"-u:{username}", "cmd"],
                             creationflags=_NEW_CONSOLE)
            lines += [f"Launched: winrs -r:{host} -u:{username} cmd  (new window).",
                      "Type the password in that window when it asks -- winrs will not take it safely any other way."]
        elif op_id == "ac_open_rdp":
            r = subprocess.run(["cmdkey", f"/generic:TERMSRV/{host}", f"/user:{username}", f"/pass:{password}"],
                               capture_output=True, text=True, timeout=20, creationflags=_NO_WINDOW)
            if r.returncode == 0:
                lines.append(f"Stored the credential for TERMSRV/{host} on this PC.")
            else:
                lines.append("Could not store the credential: " + (r.stdout + r.stderr).replace(password, "********").strip())
            subprocess.Popen(["mstsc.exe", f"/v:{host}"])
            lines += [f"Launched: mstsc /v:{host}",
                      "Inside the session you have EVERYTHING: devmgmt.msc, dfrgui, cleanmgr, wf.msc, ncpa.cpl, services.msc ...",
                      f"When finished, remove the stored credential:  cmdkey /delete:TERMSRV/{host}"]
        else:
            lines.append(f"Unknown console operation: {op_id}")
    except FileNotFoundError as e:
        lines.append(f"Could not launch ({e}). Is this a full Windows install with the RSAT/MMC tools?")
    except Exception as e:
        lines.append(f"Could not launch automatically ({e}).")
    return lines


# ══════════════════════════════════════════════════════════════════════════
#  CUSTOM CANVAS CHECKBOX  (white border, red tick -- matches the docx spec)
#  v3.1: rows for a parameterized op also render an inline entry-field grid
#  (Entry widgets bound to a shared dict via StringVar.trace_add) so the
#  value the user types is visible to run_tasks() without a second dialog.
# ══════════════════════════════════════════════════════════════════════════
class TaskRow(tk.Frame):
    def __init__(self, master, op, on_toggle=None, param_values=None, **kw):
        super().__init__(master, bg=CARD, highlightthickness=1,
                          highlightbackground=BDR, **kw)
        self.op = op
        self.checked = tk.BooleanVar(value=False)
        self.on_toggle = on_toggle
        # param_values: the dict this row's Entry widgets read/write into
        # (owned by the caller, keyed by param "key") -- None for ops with no params.
        self.param_values = param_values
        self.param_entries = {}

        top = tk.Frame(self, bg=CARD)
        top.pack(side="top", fill="x")

        self.cb_canvas = tk.Canvas(top, width=20, height=20, bg=CARD,
                                    highlightthickness=0, cursor="hand2")
        self.cb_canvas.pack(side="left", padx=(10, 8), pady=8)
        self.cb_canvas.bind("<Button-1>", self._toggle)
        self._draw_box()

        txt_frame = tk.Frame(top, bg=CARD)
        txt_frame.pack(side="left", fill="x", expand=True, pady=6)
        txt_frame.bind("<Button-1>", self._toggle)

        prefix = "! " if op["danger"] else ""
        lbl_color = YEL if op["danger"] else TXTB
        self.lbl = tk.Label(txt_frame, text=f"{prefix}{op['label']}", bg=CARD,
                             fg=lbl_color, font=("Segoe UI", 9, "bold"),
                             anchor="w", cursor="hand2")
        self.lbl.pack(anchor="w")
        self.lbl.bind("<Button-1>", self._toggle)
        self.sub = tk.Label(txt_frame, text=op["description"], bg=CARD,
                             fg=TXDD, font=("Segoe UI", 8), anchor="w",
                             cursor="hand2")
        self.sub.pack(anchor="w")
        self.sub.bind("<Button-1>", self._toggle)

        self.cat_lbl = tk.Label(top, text=op["category"], bg=CRD2, fg=OUT2,
                                 font=("Segoe UI", 7, "bold"), padx=6, pady=2)
        self.cat_lbl.pack(side="right", padx=10)

        if op.get("params"):
            sep = tk.Frame(self, bg=BDR2, height=1)
            sep.pack(side="top", fill="x", padx=10, pady=(2, 6))
            grid = tk.Frame(self, bg=CARD)
            grid.pack(side="top", fill="x", padx=10, pady=(0, 8))
            ncols = 2 if len(op["params"]) > 1 else 1
            for cc in range(ncols):
                grid.grid_columnconfigure(cc, weight=1)
            # v3.2: a param can carry "wide": true (e.g. SHARE_PATH -- a long UNC path)
            # to take the whole row on its own instead of sharing a half-width column,
            # same intent as the "wide" flag in the Web edition's index.html. Params
            # with no "wide" flag lay out exactly as before (sequential divmod fill).
            _row, _col = 0, 0
            for p in op["params"]:
                wide = bool(p.get("wide")) and ncols > 1
                if wide and _col != 0:
                    _row += 1
                    _col = 0
                span = ncols if wide else 1
                cell = tk.Frame(grid, bg=CARD)
                cell.grid(row=_row, column=_col, columnspan=span, sticky="ew", padx=4, pady=2)
                if wide:
                    _row += 1
                    _col = 0
                else:
                    _col += 1
                    if _col >= ncols:
                        _col = 0
                        _row += 1

                if p["kind"] == "bool":
                    default_val = (self.param_values.get(p["key"], p.get("default", "true"))
                                   if self.param_values is not None else p.get("default", "true"))
                    if self.param_values is not None and p["key"] not in self.param_values:
                        self.param_values[p["key"]] = default_val
                    bvar = tk.BooleanVar(value=(str(default_val).lower() != "false"))
                    chk = tk.Checkbutton(cell, text=p["label"], variable=bvar, bg=CARD, fg=TXTB,
                                          activebackground=CARD, activeforeground=TXTB,
                                          selectcolor=LOGBG, font=("Segoe UI", 9, "bold"),
                                          anchor="w", highlightthickness=0, bd=0)
                    chk.pack(side="top", fill="x", pady=(4, 0))
                    if p.get("help"):
                        tk.Label(cell, text=p["help"], bg=CARD, fg=TXDD,
                                 font=("Segoe UI", 6)).pack(side="top", fill="x", padx=(20, 0))
                    if self.param_values is not None:
                        def _on_toggle(*_a, key=p["key"], bvar=bvar):
                            self.param_values[key] = "true" if bvar.get() else "false"
                        bvar.trace_add("write", _on_toggle)
                    self.param_entries[p["key"]] = chk
                    continue

                lbl_text = p["label"] + (" (optional)" if p.get("required") is False else "")
                tk.Label(cell, text=lbl_text, bg=CARD, fg=TXDD,
                         font=("Segoe UI", 7, "bold"), anchor="w").pack(side="top", fill="x")
                default_val = (self.param_values.get(p["key"], p.get("default", ""))
                               if self.param_values is not None else p.get("default", ""))
                if self.param_values is not None and p["key"] not in self.param_values:
                    self.param_values[p["key"]] = default_val
                var = tk.StringVar(value=default_val)
                ent = tk.Entry(cell, textvariable=var, bg=LOGBG, fg=TXTB,
                               insertbackground=TXTB, relief="flat",
                               highlightthickness=1, highlightbackground=BDR,
                               highlightcolor=ACC, font=("Segoe UI", 9))
                ent.pack(side="top", fill="x", ipady=3)
                if p.get("help"):
                    tk.Label(cell, text=p["help"], bg=CARD, fg=TXDD,
                             font=("Segoe UI", 6)).pack(side="top", fill="x")
                if self.param_values is not None:
                    def _on_write(*_a, key=p["key"], var=var):
                        self.param_values[key] = var.get()
                    var.trace_add("write", _on_write)
                self.param_entries[p["key"]] = ent

    def _draw_box(self):
        self.cb_canvas.delete("all")
        if self.checked.get():
            self.cb_canvas.create_rectangle(2, 2, 18, 18, outline="#ffffff",
                                             width=2, fill=RED)
            self.cb_canvas.create_line(5, 10, 9, 14, fill="#ffffff", width=2)
            self.cb_canvas.create_line(9, 14, 15, 6, fill="#ffffff", width=2)
        else:
            self.cb_canvas.create_rectangle(2, 2, 18, 18, outline="#ffffff",
                                             width=2, fill=CARD)

    def _toggle(self, _evt=None):
        self.checked.set(not self.checked.get())
        self._draw_box()
        if self.on_toggle:
            self.on_toggle()

    def set_checked(self, val):
        self.checked.set(val)
        self._draw_box()


# ══════════════════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ══════════════════════════════════════════════════════════════════════════
class PCAdminApp:
    def __init__(self, root):
        self.root = root
        root.title(f"PC Admin & Performance Tool -- {VER}")
        root.geometry("1180x760")
        root.minsize(980, 640)
        root.configure(bg=BG)

        self.rows = {}                 # id -> TaskRow
        self.param_values = {}         # op_id -> {KEY: value}, shared with TaskRow entries
        self.log_file = None
        self.log_lines = []
        self.q = queue.Queue()
        self.stop_flag = _stop_flag       # same Event the engine polls
        self.worker = None
        self.running = False

        self._build_ui()
        self._poll_queue()
        self._log("hdr", f"  PC Admin & Performance Tool  {VER}")
        self._log("dim", f"  {COPYRIGHT}")
        self._log("dim", "  " + "-" * 60)
        self._log("info", f"  {len(OPERATIONS)} operations ready across "
                           f"{len(CATEGORIES)} categories")
        self._log("dim", "  Enter Hostname/IP -- Test Connection -- Select tasks -- Run")
        self._log("dim", "")

    # ────────────────────────────────────────────────────────────────
    def _build_ui(self):
        header = tk.Frame(self.root, bg=HDRB, height=54)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="PC ADMIN & PERFORMANCE TOOL", bg=HDRB, fg=TXTB,
                 font=("Segoe UI", 13, "bold")).pack(side="left", padx=16)
        tk.Label(header, text=VER, bg=HDRB, fg=CYAN,
                 font=("Segoe UI", 9)).pack(side="left", padx=4)
        tk.Label(header, text=COPYRIGHT, bg=HDRB, fg=TXDD,
                 font=("Segoe UI", 8)).pack(side="right", padx=16)

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=10, pady=10)

        left = tk.Frame(body, bg=BG, width=460)
        left.pack(side="left", fill="both", padx=(0, 8))
        left.pack_propagate(False)
        right = tk.Frame(body, bg=BG)
        right.pack(side="left", fill="both", expand=True)

        # ---- Connection panel ----
        conn = tk.LabelFrame(left, text=" Target Connection ", bg=PNL, fg=TXTB,
                              font=("Segoe UI", 9, "bold"), bd=1,
                              highlightbackground=BDR)
        conn.pack(fill="x", pady=(0, 8))

        def field(parent, label):
            tk.Label(parent, text=label, bg=PNL, fg=TXT,
                     font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=10, pady=(6, 0))
            e = tk.Entry(parent, bg=LOGBG, fg=TXTB, insertbackground=TXTB,
                         relief="flat", highlightthickness=1,
                         highlightbackground=BDR, highlightcolor=ACC)
            e.pack(fill="x", padx=10, pady=(2, 2), ipady=4)
            return e

        self.tx_host = field(conn, "Hostname / IP")
        self.tx_user = field(conn, "Username  (DOMAIN\\user or user@domain.local)")
        tk.Label(conn, text="Password", bg=PNL, fg=TXT,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=10, pady=(6, 0))
        pw_frame = tk.Frame(conn, bg=PNL)
        pw_frame.pack(fill="x", padx=10, pady=(2, 2))
        self.tx_pass = tk.Entry(pw_frame, bg=LOGBG, fg=TXTB, insertbackground=TXTB,
                                 relief="flat", show="*", highlightthickness=1,
                                 highlightbackground=BDR, highlightcolor=ACC)
        self.tx_pass.pack(side="left", fill="x", expand=True, ipady=4)
        self.show_pw = tk.BooleanVar(value=False)

        def toggle_pw():
            self.tx_pass.config(show="" if self.show_pw.get() else "*")

        tk.Checkbutton(pw_frame, text="show", variable=self.show_pw,
                        command=toggle_pw, bg=PNL, fg=TXDD,
                        selectcolor=CARD, activebackground=PNL,
                        font=("Segoe UI", 7)).pack(side="left", padx=6)

        tk.Label(conn, text="Auth Transport", bg=PNL, fg=TXT,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=10, pady=(6, 0))
        self.cb_transport = ttk.Combobox(
            conn, values=[t[0] for t in TRANSPORTS], state="readonly")
        self.cb_transport.current(0)
        self.cb_transport.pack(fill="x", padx=10, pady=(2, 8))

        btn_row = tk.Frame(conn, bg=PNL)
        btn_row.pack(fill="x", padx=10, pady=(0, 10))
        self.btn_test = tk.Button(btn_row, text="Test Connection", bg=ACC, fg="white",
                                   relief="flat", font=("Segoe UI", 9, "bold"),
                                   activebackground=CYAN, command=self.test_connection)
        self.btn_test.pack(side="left", fill="x", expand=True, ipady=5)

        # ---- Category tabs ----
        tabs = tk.Frame(left, bg=BG)
        tabs.pack(fill="x", pady=(0, 6))
        self.tab_buttons = {}
        self.active_cat = "all"

        # v3.1: 7 categories (was 5) no longer fit on one row -- wrap into two.
        # Full category names are kept (previously truncated to the first word,
        # which turned "Windows Health" into just "Windows"; same bug would have
        # hit "Power Recycle" / "Remote Tools" too, so fixed for every tab).
        tab_specs = [("all", "All")] + [(c, c) for c in CATEGORIES]
        half = (len(tab_specs) + 1) // 2
        tabs_row1 = tk.Frame(tabs, bg=BG)
        tabs_row1.pack(fill="x", pady=(0, 2))
        tabs_row2 = tk.Frame(tabs, bg=BG)
        tabs_row2.pack(fill="x")

        def mk_tab(parent, key, text):
            b = tk.Button(parent, text=text, bg=CRD2, fg=TXT, relief="flat",
                          font=("Segoe UI", 7, "bold"),
                          command=lambda k=key: self._filter_cat(k))
            b.pack(side="left", fill="x", expand=True, padx=1, ipady=4)
            self.tab_buttons[key] = b

        for key, text in tab_specs[:half]:
            mk_tab(tabs_row1, key, text)
        for key, text in tab_specs[half:]:
            mk_tab(tabs_row2, key, text)

        # ---- Task list (scrollable) ----
        list_wrap = tk.Frame(left, bg=BG, highlightthickness=1,
                              highlightbackground=BDR)
        list_wrap.pack(fill="both", expand=True)
        canvas = tk.Canvas(list_wrap, bg=BG, highlightthickness=0)
        vsb = ttk.Scrollbar(list_wrap, orient="vertical", command=canvas.yview)
        self.list_frame = tk.Frame(canvas, bg=BG)
        self.list_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.list_frame, anchor="nw",
                              width=430)
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        def _mousewheel(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _mousewheel)

        for op in OPERATIONS:
            pv = self.param_values.setdefault(op["id"], {}) if op.get("params") else None
            row = TaskRow(self.list_frame, op, on_toggle=self._update_count, param_values=pv)
            row.pack(fill="x", pady=2, padx=2)
            self.rows[op["id"]] = row

        sel_row = tk.Frame(left, bg=BG)
        sel_row.pack(fill="x", pady=6)
        tk.Button(sel_row, text="Select All", bg=CRD2, fg=TXT, relief="flat",
                  font=("Segoe UI", 8), command=self._select_all
                  ).pack(side="left", fill="x", expand=True, padx=2, ipady=3)
        tk.Button(sel_row, text="Select None", bg=CRD2, fg=TXT, relief="flat",
                  font=("Segoe UI", 8), command=self._select_none
                  ).pack(side="left", fill="x", expand=True, padx=2, ipady=3)
        self.lbl_count = tk.Label(left, text="0 tasks selected", bg=BG, fg=CYAN,
                                   font=("Segoe UI", 8, "bold"))
        self.lbl_count.pack(anchor="w", pady=(0, 4))

        # ---- Right: run controls + live log ----
        run_row = tk.Frame(right, bg=BG)
        run_row.pack(fill="x", pady=(0, 6))
        self.btn_run = tk.Button(run_row, text="\u25B6  RUN SELECTED TASKS", bg=GRN,
                                  fg="#062b14", relief="flat",
                                  font=("Segoe UI", 10, "bold"),
                                  command=self.run_tasks)
        self.btn_run.pack(side="left", ipady=8, ipadx=10)
        self.btn_stop = tk.Button(run_row, text="\u25A0  STOP", bg=RED, fg="white",
                                   relief="flat", font=("Segoe UI", 10, "bold"),
                                   state="disabled", command=self.stop_tasks)
        self.btn_stop.pack(side="left", ipady=8, ipadx=10, padx=6)
        tk.Button(run_row, text="Open Logs Folder", bg=CRD2, fg=TXT, relief="flat",
                  font=("Segoe UI", 9), command=self.open_logs
                  ).pack(side="right", ipady=8, ipadx=10)

        self.prg = ttk.Progressbar(right, orient="horizontal", mode="determinate")
        self.prg.pack(fill="x", pady=(0, 4))
        status_row = tk.Frame(right, bg=BG)
        status_row.pack(fill="x")
        self.lbl_dot = tk.Label(status_row, text="\u25CF", bg=BG, fg=TXDD,
                                 font=("Segoe UI", 10))
        self.lbl_dot.pack(side="left")
        self.lbl_stat = tk.Label(status_row, text="Idle", bg=BG, fg=TXT,
                                  font=("Segoe UI", 9))
        self.lbl_stat.pack(side="left", padx=6)
        self.lbl_task = tk.Label(status_row, text="", bg=BG, fg=TXDD,
                                  font=("Segoe UI", 8))
        self.lbl_task.pack(side="right")

        log_wrap = tk.Frame(right, bg=LOGBG, highlightthickness=1,
                             highlightbackground=BDR)
        log_wrap.pack(fill="both", expand=True, pady=(6, 0))
        self.txt = tk.Text(log_wrap, bg=LOGBG, fg=TXT, insertbackground=TXT,
                            font=("Consolas", 9), relief="flat", wrap="word",
                            state="disabled")
        tsb = ttk.Scrollbar(log_wrap, orient="vertical", command=self.txt.yview)
        self.txt.configure(yscrollcommand=tsb.set)
        self.txt.pack(side="left", fill="both", expand=True)
        tsb.pack(side="right", fill="y")

        for tag, color, bold in [
            ("hdr", CYAN, True), ("info", CYAN, False), ("ok", GRN, False),
            ("warn", YEL, False), ("err", RED, False), ("dim", TXDD, False),
            ("task", TXTB, True), ("out", OUT2, False),
        ]:
            self.txt.tag_config(tag, foreground=color,
                                 font=("Consolas", 9, "bold" if bold else "normal"))

    # ────────────────────────────────────────────────────────────────
    def _filter_cat(self, key):
        self.active_cat = key
        for k, b in self.tab_buttons.items():
            b.configure(bg=ACC if k == key else CRD2)
        for op_id, row in self.rows.items():
            show = (key == "all" or row.op["category"] == key)
            if show:
                row.pack(fill="x", pady=2, padx=2)
            else:
                row.pack_forget()

    def _select_all(self):
        for row in self.rows.values():
            if row.winfo_manager():
                row.set_checked(True)
        self._update_count()

    def _select_none(self):
        for row in self.rows.values():
            row.set_checked(False)
        self._update_count()

    def _get_selected(self):
        return [row.op for row in self.rows.values() if row.checked.get()]

    def _update_count(self):
        n = len(self._get_selected())
        self.lbl_count.config(text=f"{n} task{'s' if n != 1 else ''} selected")

    # ────────────────────────────────────────────────────────────────
    def _log(self, tag, text):
        self.txt.configure(state="normal")
        self.txt.insert("end", text + "\n", tag)
        self.txt.see("end")
        self.txt.configure(state="disabled")
        if self.log_file is not None:
            self.log_lines.append(text)

    def open_logs(self):
        try:
            os.startfile(LOG_DIR)  # Windows only
        except AttributeError:
            messagebox.showinfo("Logs", f"Log folder: {LOG_DIR}")
        except Exception as e:
            messagebox.showerror("Logs", str(e))

    # ────────────────────────────────────────────────────────────────
    def test_connection(self):
        host = self.tx_host.get().strip()
        user = self.tx_user.get().strip()
        pwd = self.tx_pass.get()
        transport = TRANSPORTS[self.cb_transport.current()][1]

        if not host:
            messagebox.showwarning("Input", "Enter hostname or IP.")
            return
        if not user:
            messagebox.showwarning("Input", "Enter credentials.")
            return

        self.btn_test.config(state="disabled", text="Testing...")
        self.lbl_stat.config(text="Testing connection...")

        def worker():
            try:
                socket.gethostbyname(host)
            except socket.gaierror:
                self.q.put(("test_result", "error", f"Cannot resolve '{host}'. Check hostname/DNS."))
                return
            try:
                sess = make_session(host, user, pwd, transport)
                stdout, stderr, ok = run_remote_ps(sess, 'Write-Output "PING_OK_$env:COMPUTERNAME"')
                if ok and "PING_OK_" in stdout:
                    remote = stdout.strip().replace("PING_OK_", "")
                    self.q.put(("test_result", "ok",
                                f"Connected to {host} as '{user}'. Remote: {remote}. WinRM OK."))
                else:
                    self.q.put(("test_result", "error",
                                f"WinRM connected but test command failed. {stderr[:200]}"))
            except AuthenticationError:
                self.q.put(("test_result", "error",
                            f"Auth failed for '{user}'. Try DOMAIN\\username or user@domain.local"))
            except Exception as e:
                err = str(e)
                if "5985" in err or "refused" in err.lower() or "timed out" in err.lower():
                    self.q.put(("test_result", "error",
                                f"Cannot reach WinRM on {host}:5985. "
                                f"Run on target (Admin): Enable-PSRemoting -Force"))
                else:
                    self.q.put(("test_result", "error", f"Connection error: {err}"))

        threading.Thread(target=worker, daemon=True).start()

    # ────────────────────────────────────────────────────────────────
    def run_tasks(self):
        if self.running:
            return
        selected = self._get_selected()
        if not selected:
            messagebox.showwarning("No Tasks", "Select at least one task.")
            return
        host = self.tx_host.get().strip()
        user = self.tx_user.get().strip()
        pwd = self.tx_pass.get()
        transport_label, transport = TRANSPORTS[self.cb_transport.current()]
        if not host:
            messagebox.showwarning("Input", "Enter hostname or IP.")
            return
        if not user:
            messagebox.showwarning("Input", "Enter credentials.")
            return

        # ── Validate + substitute every {{KEY}} parameter up front ────────
        # Aborts before any dialog/connection if a required field is blank
        # or a value doesn't match its allow-listed pattern.
        run_ops = []
        for op in selected:
            if op.get("params"):
                cmd, err = validate_and_substitute(op, self.param_values.get(op["id"], {}))
                if err:
                    messagebox.showerror("Invalid Parameter", f"{op['label']}\n\n{err}")
                    return
                op2 = dict(op)
                op2["command"] = cmd
                op2["_params"] = dict(self.param_values.get(op["id"], {}))
                run_ops.append(op2)
            else:
                run_ops.append(op)
        selected = run_ops

        dangerous = [op for op in selected if op["danger"]]
        if dangerous:
            names = "\n".join(f"  * {op['label']}" for op in dangerous)
            ans = messagebox.askyesno(
                "Confirm",
                f"WARNING: {len(dangerous)} sensitive op(s):\n\n{names}\n\n"
                "Some require reboots or may interrupt network.\n\nContinue?")
            if not ans:
                return

        now = datetime.datetime.now()
        ts = now.strftime("%Y%m%d_%H%M%S")
        safe_host = re.sub(r"[^\w\-.]", "_", host)
        log_path = LOG_DIR / f"AdminTool_{safe_host}_{ts}.log"
        self.log_file = log_path
        self.log_lines = []

        self.stop_flag.clear()
        self.running = True
        self.btn_run.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.lbl_dot.config(fg=GRN)
        self.lbl_stat.config(text="Connecting...")
        self.prg["value"] = 0

        header = [
            "=" * 60,
            f"  PC ADMIN & PERFORMANCE TOOL  {VER}",
            f"  {COPYRIGHT_LONG}",
            "=" * 60,
            f"  Target   : {host}",
            f"  Username : {user}  [{transport_label}]",
            f"  Date/Time: {now.strftime('%Y-%m-%d %H:%M:%S')}",
            f"  Tasks    : {len(selected)} selected",
            f"  Log File : {log_path.name}",
            "=" * 60,
            "",
        ]
        for line in header:
            tag = "hdr" if line.startswith("=") or "TOOL" in line else \
                  "info" if line.startswith("  Target") or line.startswith("  Username") or \
                            line.startswith("  Date") or line.startswith("  Tasks") or \
                            line.startswith("  Log") else "dim"
            self._log(tag, line)

        self.worker = threading.Thread(
            target=self._run_worker, args=(host, user, pwd, transport, selected), daemon=True)
        self.worker.start()

    def stop_tasks(self):
        self.stop_flag.set()
        self.q.put(("log", "warn", "  ! STOP requested -- finishing current task..."))

    _TAGMAP = {"info": "info", "dim": "dim", "warning": "warn", "success": "ok", "error": "err"}

    def _drive(self, gen):
        """Run an engine generator, forwarding its progress events to the log; return its result."""
        try:
            while True:
                e = next(gen)
                if isinstance(e, dict) and e.get("text"):
                    self.q.put(("log", self._TAGMAP.get(e.get("type"), "out"), e["text"]))
        except StopIteration as si:
            return si.value

    def _run_worker(self, host, user, pwd, transport, selected):
        try:
            session = make_session(host, user, pwd, transport)
            _, stderr_test, ok_test = run_remote_ps(session, 'Write-Output "SESSION_OK"')
            if not ok_test:
                self.q.put(("log", "err", f"  CONNECT FAILED: {stderr_test}"))
                self.q.put(("done", False))
                return
            self.q.put(("log", "ok", f"  Session ready -- {host}"))
            self.q.put(("log", "dim", ""))
        except AuthenticationError:
            self.q.put(("log", "err", "  CONNECT FAILED: Invalid username or password"))
            self.q.put(("done", False))
            return
        except Exception as e:
            self.q.put(("log", "err", f"  CONNECT FAILED: {e}"))
            self.q.put(("done", False))
            return

        total = len(selected)
        cur_host = host
        target_rebooting = False
        for idx, op in enumerate(selected, start=1):
            if self.stop_flag.is_set():
                self.q.put(("log", "warn", "  ! STOPPED by user"))
                break

            self.q.put(("progress", idx, total, f"[{idx}/{total}] {op['label']}"))
            prefix = "! " if op["danger"] else ""
            self.q.put(("log", "task", f"  >> [{idx}/{total}]  {prefix}{op['label']}"))
            self.q.put(("log", "dim", f"     Category: {op['category']}  --  {op['description']}"))
            self.q.put(("log", "dim", "     " + "-" * 48))

            if target_rebooting:
                self.q.put(("log", "warn", "     Skipped: the target is restarting -- run this task again once it is back online."))
                self.q.put(("log", "dim", ""))
                continue

            # v3.7 Admin Consoles: open on THIS PC, connected to the target.
            if op["id"] in CONSOLE_OP_IDS:
                for line in launch_console(op["id"], cur_host, user, pwd, transport):
                    self.q.put(("log", "out", f"     {line}"))
                self.q.put(("log", "dim", ""))
                continue

            t0 = time.time()
            tid = op["id"]
            cmd_text = op["command"]
            if op.get("needs_cred"):
                cmd_text = build_cred_prelude(user, pwd) + cmd_text
            tparams = op.get("_params", {})

            if tid in NETWORK_BLIP_OPS or op.get("long"):
                alt_hosts = []
                if tid == "rt_set_static_ip":
                    new_ip = (tparams.get("IP") or "").strip()
                    if new_ip and new_ip != cur_host:
                        alt_hosts.append(new_ip)
                self.q.put(("log", "dim", "     Network-changing / long task: running detached on the target; the tool reconnects and fetches the result."))
                stdout, stderr, ok, used_host = self._drive(detached_run_gen(
                    session, [cur_host] + alt_hosts, user, pwd, transport, cmd_text,
                    DETACH_LONG_WAIT if op.get("long") else DETACH_BLIP_WAIT))
                if used_host != cur_host:
                    cur_host = used_host
                    self.q.put(("log", "info", f"     Target is now reached at {cur_host}."))
                session = make_session(cur_host, user, pwd, transport)
            else:
                stdout, stderr, ok = run_remote_ps(session, cmd_text)
                if not ok and stderr.startswith(("TRANSPORT_ERR", "TIMEOUT_ERR")):
                    if expects_reboot(tid, tparams):
                        self.q.put(("log", "ok", "     Connection closed because the target is restarting -- this is the expected result."))
                        stdout, stderr, ok = "  Restart requested; the target is going down.", "", True
                        target_rebooting = True
                    else:
                        self.q.put(("log", "warn", "     Connection lost -- reconnecting..."))
                        s2, h2 = self._drive(reconnect_gen([cur_host], user, pwd, transport))
                        if s2 is not None:
                            session = make_session(cur_host, user, pwd, transport)
                            self.q.put(("log", "ok", "     Session reconnected -- retrying task"))
                            stdout, stderr, ok = run_remote_ps(session, cmd_text)
                        else:
                            self.q.put(("log", "err", "     Reconnect failed -- the target did not come back in time"))
            if ok and tid in (REBOOT_OPS | CONDITIONAL_REBOOT_OPS) and any(mk in stdout for mk in REBOOT_MARKERS):
                target_rebooting = True

            elapsed = round(time.time() - t0, 1)

            if stdout.strip():
                for line in stdout.splitlines():
                    line = line.rstrip()
                    if not line:
                        continue
                    lo = line.lower()
                    if any(k in lo for k in ("freed", "cleared", "complete", "restarted",
                                              "pass", "ok", "removed", "deleted")):
                        tag = "ok"
                    elif any(k in lo for k in ("warn", "skip", "not found", "already", "empty", "cannot")):
                        tag = "warn"
                    elif any(k in lo for k in ("error", "fail", "denied", "critical")):
                        tag = "err"
                    else:
                        tag = "out"
                    self.q.put(("log", tag, f"     {line}"))
            else:
                self.q.put(("log", "warn", "     ! No output -- check permissions or nothing to process"))

            if stderr.strip():
                for line in stderr.splitlines():
                    if not line.strip():
                        continue
                    if line.startswith("CRED_ERR"):
                        line = "Authentication failed -- re-check credentials"
                    elif line.startswith("TRANSPORT_ERR"):
                        line = "WinRM transport error -- connection may have dropped"
                    elif line.startswith("TIMEOUT_ERR"):
                        line = "Task timed out (>170s) -- operation may still be running"
                    elif "AccessDenied" in line or "Access is denied" in line:
                        line = "Access denied -- use an account with admin rights"
                    self.q.put(("log", "err", f"     {line}"))

            status = "Completed" if ok else "Completed with errors"
            self.q.put(("log", "ok" if ok else "warn", f"     {status} in {elapsed}s"))
            self.q.put(("log", "dim", ""))

        stopped = self.stop_flag.is_set()
        footer = [
            "=" * 60,
            "  STOPPED BY USER" if stopped else "  ALL TASKS COMPLETED",
            f"  Finished : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"  Log: {self.log_file.name if self.log_file else ''}",
            f"  {COPYRIGHT}",
            "=" * 60,
        ]
        for line in footer:
            self.q.put(("log", "hdr" if line.startswith("=") else
                                "warn" if "STOPPED" in line else
                                "ok" if "COMPLETED" in line else "dim", line))
        self.q.put(("done", not stopped))

    # ────────────────────────────────────────────────────────────────
    def _poll_queue(self):
        try:
            while True:
                item = self.q.get_nowait()
                kind = item[0]
                if kind == "log":
                    _, tag, text = item
                    self._log(tag, text)
                elif kind == "progress":
                    _, idx, total, task_text = item
                    pct = int((idx / max(total, 1)) * 100)
                    self.prg["value"] = pct
                    self.lbl_stat.config(text=task_text)
                elif kind == "test_result":
                    _, status, msg = item
                    self.btn_test.config(state="normal", text="Test Connection")
                    self.lbl_stat.config(text="Idle")
                    if status == "ok":
                        messagebox.showinfo("Connection OK", msg)
                        self._log("ok", f"  Connected: {msg}")
                    else:
                        messagebox.showerror("Connection Failed", msg)
                        self._log("err", f"  {msg}")
                elif kind == "done":
                    _, success = item
                    self.running = False
                    self.btn_run.config(state="normal")
                    self.btn_stop.config(state="disabled")
                    self.lbl_dot.config(fg=TXDD)
                    self.lbl_task.config(text="")
                    self.prg["value"] = 100 if success else self.prg["value"]
                    self.lbl_stat.config(
                        text="Stopped -- review log" if self.stop_flag.is_set()
                        else "All tasks completed -- log saved")
                    if self.log_file is not None:
                        try:
                            with open(self.log_file, "w", encoding="utf-8") as f:
                                f.write("\n".join(self.log_lines))
                        except Exception:
                            pass
                    self.log_file = None
        except queue.Empty:
            pass
        self.root.after(80, self._poll_queue)


def main():
    root = tk.Tk()
    try:
        root.iconbitmap(default="")
    except Exception:
        pass
    app = PCAdminApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
