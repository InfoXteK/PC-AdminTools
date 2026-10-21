#!/usr/bin/env python3
"""
================================================================================
  PC Admin & Performance Troubleshooting Tool  v3.7  — Web-Service Edition
  © 2024-2026 Abdullah | All Rights Reserved
  Contact : abuabdullah.be@outlook.com
  Unauthorized copying, modification or redistribution is strictly prohibited.

  Runs as a standalone network service on PORT 3038 -- reachable from any
  host on the same allowed subnet at http://<this-machine-IP>:3038
  Works unmodified on Linux, Windows, and Windows Server hosts (Python 3.9+).
  All logs and session files are written locally on THIS (hosting) machine,
  under the "logs" folder next to this script.

  v3.0 (port 3030 -> 3031): Two new categories were added -- "Power Recycle"
  (software-only alternatives to a physical power cycle: driver/service/
  adapter/USB/device cycling, pre-recycle evidence collection) and "Remote
  Tools" (static IP/DHCP, computer rename, VSS shadow-copy management,
  scheduled task lookup, service restart, Computer Management launch). 64
  operations total, up from 36. Every operation now also carries an explicit
  "danger" field (previously only encoded client-side in index.html's
  DANGER_IDS) so the server itself can refuse to run a flagged operation
  without an explicit confirmation flag from the caller -- see
  "confirmed_danger" in /api/run. Some operations take runtime parameters
  (e.g. an IP address, an adapter name, a device Instance ID) -- see
  PARAM_VALIDATORS / validate_and_substitute() below.

  v3.1 (port 3031 -> 3032): Added an "Auto-Restart" checkbox (kind="bool")
  to the three operations that previously restarted unconditionally as a
  side effect of their real work -- pr_full_soft_recycle, rt_rename_pc_domain,
  rt_rename_pc_workgroup. Unchecked (default stays checked, i.e. unchanged
  behavior), the operation still does its real work (network+USB cycle, or
  the rename) but skips the trailing restart, leaving the change pending
  until the admin restarts manually. NOT added to pr_force_restart or
  pr_force_signout_restart -- those operations ARE the restart with nothing
  else to fall back to, so an "auto-restart: off" toggle on them would just
  mean "do nothing," which isn't a useful option. Also not needed on
  rt_rename_pc_wmic_legacy, which already never auto-restarts.

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
         attribute "wide" (input spans both columns in the web UI).
    FIX  List All Services sizes its Name column to the longest name.
    FIX  index.html: a parameterised task's input area shared a non-wrapping
         flex row with its title, squeezing the title/description to one word
         per line. install_service.bat removes any previous PCAdminTool service
         and the old 3030-3032 firewall rules itself and warns if the port is busy.

  v3.3 (port 3033 -> 3034):
    FIX  run_console_testmode.bat had NO pause anywhere after launching
         app.py, so if it exited for any reason -- most commonly, port 3034
         already held by this tool's own Windows Service, if that was
         separately installed via install_service.bat -- Werkzeug's own
         diagnostic ("Address already in use") flashed on screen for a
         fraction of a second and the window closed before it could be read,
         reported as "opens and closes immediately, no response on
         localhost". app.py's own startup now also wraps app.run() and adds
         a plain-English, tool-specific explanation on top of Werkzeug's own
         message (mentioning `net stop PCAdminTool` specifically, which
         Werkzeug obviously can't know about) -- verified with a same-process
         reproduction of both the failure path and a normal Ctrl+C before
         shipping (Werkzeug raises SystemExit internally on a bind failure
         rather than letting a raw OSError or traceback reach this code, and
         swallows Ctrl+C internally on a normal stop rather than letting
         KeyboardInterrupt reach it either -- an initial version of this fix
         was written against the wrong assumption for both and would have
         silently never triggered; both were corrected before shipping,
         not left as a guess). Independently and more importantly, every
         launcher .bat in all three editions now guarantees its window
         stays open and shows what happened on ANY failure, not just this
         one -- see the reference doc for the full list (this exact gap
         existed, to different degrees, in every edition's own launcher).
    FIX  install_service.bat's dependency-install step is now also checked
         for failure (previously silent -- a failed `pip install` would fall
         through to a confusing later error with no indication why).

  v3.4 (port 3034 -> 3035):
    FIX  Even with v3.3's pause-on-exit fix, both launchers could still
         close early on some machines. Root cause, found this time:
         pcadmintool_service.py called win32serviceutil.HandleCommandLine()
         with no exception handling at all. install_service.bat
         unconditionally calls "remove" (cleanup) before every install,
         including the very first one ever, when there is nothing to
         remove yet -- and depending on the installed pywin32 version,
         that can raise an uncaught exception instead of returning
         cleanly. That exception's traceback was ALSO being hidden by
         ">nul 2>nul" in the batch file, so the true error was invisible
         twice over. This could never be exercised in testing before
         shipping, because pywin32 (and Windows' Service Control Manager)
         do not exist on Linux -- recorded here rather than left
         unstated. Fixed at the source: "remove"/"stop" on a service
         that was never installed or was not running now prints a plain
         one-line note and exits cleanly instead of raising; a genuine
         failure of "install" or any other command still exits non-zero,
         so install_service.bat's own error check on that command is
         unaffected. Verified with a mocked HandleCommandLine covering
         all four cases (a real service-doesn't-exist-style exception on
         remove/stop, a real failure on install, and a normal successful
         call), since pywin32 itself cannot be exercised here.
    NEW  Both run_console_testmode.bat and install_service.bat now print
         a numbered CHECKPOINT before and after every step, and check
         whether "python" on PATH is a real interpreter rather than
         Windows' own placeholder stub in WindowsApps (a stub that Windows
         installs by default, is found by "where python", but does
         nothing when run -- a plausible silent-failure cause this
         version specifically now detects and reports). If either window
         still closes early after this version, the last checkpoint
         number printed pinpoints exactly where.

  v3.5 (port 3035 -> 3036):
    FIX  v3.4's WindowsApps-stub check was itself broken: it scanned the
         ENTIRE "where python" output for the substring "WindowsApps"
         anywhere at all, rather than checking only the FIRST entry (the
         one Windows actually runs when you type "python"). On any machine
         with a real Python installed AND the Store stub also present
         further down PATH -- a completely normal, common configuration,
         and exactly the reported case -- this produced a false positive
         that stopped both launchers even though "python" worked fine.
         Replaced with a direct functional test (python --version, the
         exact same invocation the rest of each script already uses)
         instead of inspecting path text at all; a real WindowsApps-only
         situation is still called out, but only as context inside an
         ACTUAL failure, never as a separate gate that can misfire on its
         own. This is the second launcher-robustness miss in as many
         versions; both are recorded in full at the reference document's
         v3.4/v3.5 addenda rather than only in this summary line.
    FIX  "Open Computer Management (Connected to Target)" now actually
         launches mmc.exe compmgmt.msc locally on the machine hosting the
         Web-Service edition, connected to the target -- matching what
         the PowerShell and Python-GUI desktop editions already did. It
         previously only printed the equivalent command as text. A
         server process can never open a window on a remote browser's
         own screen (a hard OS limit, not a design choice); for the
         common case of running this edition on your own PC and browsing
         to localhost, the machine hosting the service IS your own PC, so
         this now behaves identically to the desktop editions. Falls back
         to printing the manual command, with the reason, if the host
         isn't Windows or the launch itself fails.

  v3.7 (port 3037 -> 3038):
    FIX  Network operations (Set Static IP, Set DHCP, Flush DNS, Reset TCP/IP,
         adapter restarts) no longer leave the tool without a response or force
         an application restart. They now run as a detached SYSTEM job on the
         target; this service polls with fresh short-lived sessions, follows the
         target to its NEW address after Set Static IP, and prints the result.
    FIX  A sensitive operation is no longer silently RE-RUN after a dropped
         connection. It is reported as "outcome unknown -- verify" instead.
    FIX  Rename Computer: all three variants failed with "Access is denied" on a
         domain-joined target because a WinRM (NTLM) logon cannot authenticate
         onward to a domain controller. The Domain variant now passes the
         supplied credential explicitly (-DomainCredential, then the WMI Rename
         method); Workgroup refuses cleanly on a domain-joined PC; the WMIC
         variant falls back to the WMI/CIM Rename where wmic.exe is removed.
    NEW  VSS: size report, set/resize max storage size, create shadow copy now.
    NEW  Performance: DISM analyze / component cleanup / ResetBase / health scan,
         WMI verify + CIM snapshot (WMIC replacement), WMI repair, perf-counter
         rebuild, SSD retrim, system-managed page file.
    NEW  Category "Admin Consoles": opens Computer/Device/Disk Management, dfrgui,
         Disk Cleanup, PowerShell, CMD, Firewall, Network Connections and more on
         the TARGET's own screen, using the admin credentials entered.

  v3.6 (port 3036 -> 3037):
    FIX  ROOT CAUSE of the launcher windows closing with no message, found
         after three versions of guessing. cmd.exe treats an unescaped closing
         parenthesis inside a ( ... ) block as the END of that block. The rest
         of the line is then a syntax error that cmd finds when it PARSES the
         block -- even when the block's condition is false -- and it aborts the
         whole batch run, so a double-clicked window simply vanishes. Three
         files had this defect: check_port.bat (called by BOTH Web-edition
         launchers since v3.3 -- the real reason the installer window closed
         right after its cleanup step), run_console_testmode.bat (dependency
         error block, since v3.4) and the Python-GUI edition's
         install_and_run.bat. Every launcher in all three editions is now
         written with NO parenthesized blocks at all, and saved with CRLF line
         endings (two were LF-only, which cmd.exe can mishandle for goto and
         labels). Nothing in app.py changed for this.
    FIX  Cosmetic: the installer's closing message printed a stray caret, and
         the Python-GUI launcher's title line ran the word Performance as a
         command on every start.
    FIX  "Network Adapter Speed and Traffic Stats" (all three editions
         share this payload): the link speed was computed from the adapter's
         LinkSpeed property, which Windows returns as TEXT such as "1 Gbps",
         not as a number, so the arithmetic threw a conversion error on every
         real adapter -- the task showed as FAILED with blank speeds. It now
         uses the numeric Speed property (bits per second, divided by 1e6)
         and falls back to printing the LinkSpeed text. Found by executing
         the operation under real PowerShell, not by reading it.
    NEW  Both Web-edition launchers now also print which python.exe will
         actually run (Using: ...), since three python.exe entries on PATH is
         a normal configuration and it was not obvious which one was used.
    NEW  PowerShell edition only: eight operations that were quietly less
         complete than the Web and Python-GUI editions are now at
         parity (see the PowerShell file header). No functional change in
         this file beyond the version, the port and the speed fix above.

  Port bumps alongside every versioned release are a standing project
  convention (see the reference doc) -- update any saved bookmarks, firewall
  rules, and the systemd/service files that reference the old port.
================================================================================
"""
from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from pypsrp.client import Client
from pypsrp.exceptions import AuthenticationError, WinRMTransportError, WSManFaultError
import requests.exceptions
import json, datetime, socket, re, os, time, threading, subprocess, platform
from pathlib import Path

app = Flask(__name__)

SERVICE_PORT = 3038

# Logs/files live on the hosting machine (Linux, Windows, or Windows Server),
# in a "logs" folder next to this script -- not tied to a Docker container.
BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

_stop_flag  = threading.Event()
_run_lock   = threading.Lock()

COPYRIGHT = (
    "© 2024-2026 Abdullah | PC Admin & Performance Tool v3.7 | All Rights Reserved\n"
    "Contact: abuabdullah.be@outlook.com | Unauthorized use or redistribution is prohibited."
)

# ══════════════════════════════════════════════════════════════════════════════
#  OPERATIONS  — PowerShell command library
#  command field is server-side only, never sent to the browser
# ══════════════════════════════════════════════════════════════════════════════
OPERATIONS = [

    # ─── 🧹 CLEANUP ──────────────────────────────────────────────────────────
    {
        "id": "clear_user_temp",
        "danger": False,
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
"""
    },
    {
        "id": "clear_windows_temp",
        "danger": False,
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
"""
    },
    {
        "id": "clear_prefetch",
        "danger": False,
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
"""
    },
    {
        "id": "clear_thumbnail_cache",
        "danger": False,
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
"""
    },
    {
        "id": "clear_wu_cache",
        "danger": False,
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
"""
    },
    {
        "id": "flush_dns",
        "danger": True,
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
"""
    },
    {
        "id": "clear_browser_cache",
        "danger": False,
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
"""
    },
    {
        "id": "clear_event_logs",
        "danger": False,
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
"""
    },
    {
        "id": "empty_recycle_bin",
        "danger": True,
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
"""
    },
    {
        "id": "disk_cleanup",
        "danger": True,
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
"""
    },

    # ─── 💾 DISK ─────────────────────────────────────────────────────────────
    {
        "id": "disk_space_report",
        "danger": False,
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
"""
    },
    {
        "id": "defrag_drives",
        "danger": False,
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
"""
    },
    {
        "id": "disk_health_scan",
        "danger": False,
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
"""
    },
    {
        "id": "large_files_report",
        "danger": False,
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
"""
    },

    # ─── ⚡ PERFORMANCE ───────────────────────────────────────────────────────
    {
        "id": "high_perf_power",
        "danger": True,
        "label": "Set High Performance Power Plan",
        "category": "Performance",
        "description": "Activates the built-in High Performance power scheme",
        "command": r"""
$guid = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
$result = powercfg -setactive $guid 2>&1
$active  = powercfg -getactivescheme 2>&1
Write-Output "  Power plan set to: High Performance"
Write-Output "  Active: $active"
"""
    },
    {
        "id": "visual_effects_perf",
        "danger": False,
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
"""
    },
    {
        "id": "optimize_ram",
        "danger": False,
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
"""
    },
    {
        "id": "tune_sysmain",
        "danger": False,
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
"""
    },
    {
        "id": "restart_search",
        "danger": False,
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
"""
    },
    {
        "id": "startup_report",
        "danger": False,
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
"""
    },
    {
        "id": "pagefile_report",
        "danger": False,
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
"""
    },
    {
        "id": "non_essential_services",
        "danger": False,
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
"""
    },

    # ─── 🔧 WINDOWS HEALTH ───────────────────────────────────────────────────
    {
        "id": "system_info",
        "danger": False,
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
"""
    },
    {
        "id": "top_processes",
        "danger": False,
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
"""
    },
    {
        "id": "run_sfc",
        "danger": True,
        "label": "Run SFC /scannow (System File Check)",
        "category": "Windows Health",
        "description": "Scans & repairs corrupted Windows system files (5-15 min)",
        "command": r"""
Write-Output "  Starting SFC scan — this may take several minutes..."
$result = sfc /scannow 2>&1
$result | foreach { Write-Output "  $_" }
Write-Output "  SFC scan complete"
"""
    },
    {
        "id": "run_dism",
        "danger": True,
        "label": "Run DISM Health Check & Scan",
        "category": "Windows Health",
        "description": "Checks and scans the Windows component store for corruption",
        "command": r"""
Write-Output "  Running DISM CheckHealth..."
DISM /Online /Cleanup-Image /CheckHealth 2>&1 | foreach { Write-Output "  $_" }
Write-Output ""
Write-Output "  Running DISM ScanHealth..."
DISM /Online /Cleanup-Image /ScanHealth 2>&1 | foreach { Write-Output "  $_" }
"""
    },
    {
        "id": "wu_history",
        "danger": False,
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
"""
    },
    {
        "id": "recent_errors",
        "danger": False,
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
"""
    },
    {
        "id": "installed_software",
        "danger": False,
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
"""
    },

    # ─── 🌐 NETWORK ──────────────────────────────────────────────────────────
    {
        "id": "net_ip_config",
        "danger": False,
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
"""
    },
    {
        "id": "net_connectivity",
        "danger": False,
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
"""
    },
    {
        "id": "net_adapter_stats",
        "danger": False,
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
"""
    },
    {
        "id": "reset_network",
        "danger": True,
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
"""
    },
    {
        "id": "dns_test",
        "danger": False,
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
"""
    },
    {
        "id": "firewall_status",
        "danger": False,
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
"""
    },
    {
        "id": "active_connections",
        "danger": False,
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
"""
    },

    # ─── 🔁 POWER RECYCLE ───────────────────────────────────────────────────
    # Design goal (per spec): reproduce what a full physical power cycle fixes
    # -- a hung driver, a stuck storage controller, a wedged network driver, a
    # misbehaving USB device, a firmware quirk, a device that won't wake --
    # WITHOUT actually power-cycling the machine. Read-only diagnostics come
    # first, then narrow/targeted fixes, then progressively more disruptive
    # ones, ending in the bundle that is the closest software-only equivalent
    # to a real power recycle (network + USB cycle + restart).
    {
        "id": "pr_collect_evidence",
        "danger": False,
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
"""
    },
    {
        "id": "pr_diagnose_driver_hang",
        "danger": False,
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
"""
    },
    {
        "id": "pr_list_storage_devices",
        "danger": False,
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
"""
    },
    {
        "id": "pr_list_usb_devices",
        "danger": False,
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
"""
    },
    {
        "id": "pr_cycle_device_by_id",
        "danger": True,
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
"""
    },
    {
        "id": "pr_restart_all_adapters",
        "danger": True,
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
"""
    },
    {
        "id": "pr_restart_named_adapter",
        "danger": True,
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
"""
    },
    {
        "id": "pr_disable_enable_adapter",
        "danger": True,
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
"""
    },
    {
        "id": "pr_cycle_usb_hubs",
        "danger": True,
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
"""
    },
    {
        "id": "pr_firmware_info",
        "danger": False,
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
"""
    },
    {
        "id": "pr_force_restart",
        "danger": True,
        "label": "Force Restart Now (Unsaved Work Will Be Lost)",
        "category": "Power Recycle",
        "description": "Restart-Computer -Force -- the firmware-bug workaround and the last resort before a real power cycle",
        "command": r"""
Write-Output "  Forcing an immediate restart -- any unsaved work on the target WILL be lost."
Write-Output "  The connection will drop now; this is expected."
Restart-Computer -Force
"""
    },
    {
        "id": "pr_wake_armed_devices",
        "danger": False,
        "label": "List Devices Armed to Wake the System",
        "category": "Power Recycle",
        "description": "powercfg /devicequery wake_armed (+ wake_programmable) -- diagnoses devices not waking correctly from sleep",
        "command": r"""
Write-Output "  === DEVICES CURRENTLY ARMED TO WAKE THIS SYSTEM ==="
powercfg /devicequery wake_armed | ForEach-Object { Write-Output "  $_" }
Write-Output ""
Write-Output "  === DEVICES THAT CAN BE PROGRAMMED TO WAKE THIS SYSTEM ==="
powercfg /devicequery wake_programmable | ForEach-Object { Write-Output "  $_" }
"""
    },
    {
        "id": "pr_disable_hibernation",
        "danger": True,
        "label": "Disable Hibernation",
        "category": "Power Recycle",
        "description": "powercfg /h off -- removes hiberfil.sys and Fast Startup/S4 hybrid-sleep behavior",
        "command": r"""
Write-Output "  Disabling hibernation (also removes hiberfil.sys and Fast Startup/hybrid-sleep behavior)..."
powercfg /h off
Write-Output "  Verifying available sleep states..."
powercfg /a | ForEach-Object { Write-Output "  $_" }
"""
    },
    {
        "id": "pr_force_signout_restart",
        "danger": True,
        "label": "Force Sign-out & Restart (shutdown /g)",
        "category": "Power Recycle",
        "description": "shutdown /g /f /t 0 -- restarts and reopens registered apps, distinct from a plain restart",
        "command": r"""
Write-Output "  Signing out and restarting now (shutdown /g) -- Windows will try to reopen registered apps on next login."
Write-Output "  Any unsaved work WILL be lost. The connection will drop now; this is expected."
shutdown /g /f /t 0
"""
    },
    {
        "id": "pr_full_soft_recycle",
        "danger": True,
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
    shutdown /g /f /t 0
} else {
    Write-Output "  [3/3] Auto-Restart is OFF -- network + USB cycle complete, restart skipped."
    Write-Output "  Run 'Force Restart Now' or 'Force Sign-out & Restart' (Power Recycle) manually when ready."
}
"""
    },

    # ─── 🛠️ REMOTE TOOLS ────────────────────────────────────────────────────
    {
        "id": "rt_set_static_ip",
        "danger": True,
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
"""
    },
    {
        "id": "rt_set_dhcp",
        "danger": True,
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
"""
    },
    {
        "id": 'rt_rename_pc_domain',
        "label": 'Rename Computer (Domain-Joined)',
        "category": 'Remote Tools',
        "description": 'Renames a domain-joined PC passing YOUR credential explicitly (-DomainCredential, then WMI Rename) -- no CredSSP needed; restart optional',
        "params": [
            {'key': 'NEW_NAME', 'kind': 'computername', 'label': 'New Computer Name', 'required': True},
            {'key': 'AUTO_RESTART', 'kind': 'bool', 'label': 'Automatically restart when done', 'required': True, 'default': 'true', 'help': "Unchecked: rename now, restart later yourself (name won't take effect until then)"},
        ],
        "command": r"""
$newName = "{{NEW_NAME}}"
$autoRestart = {{AUTO_RESTART}}

function Get-RenameReturnText([int]$c) {
    switch ($c) {
        5    { 'Access denied -- the account cannot rename this computer object in Active Directory' }
        53   { 'Network path not found -- the target cannot reach a domain controller' }
        87   { 'Invalid parameter -- the new name is not acceptable' }
        1219 { 'Conflicting credentials -- the target already has a connection to the DC under another account' }
        1326 { 'Logon failure -- bad user name or password for the domain' }
        1355 { 'The domain could not be contacted (DNS / DC unreachable from the target)' }
        2224 { 'A computer account with the new name already exists in the domain' }
        default { "see https://learn.microsoft.com/windows/win32/cimwin32prov/rename-method-in-class-win32-computersystem (code $c)" }
    }
}

$cs = Get-CimInstance Win32_ComputerSystem
Write-Output "  Current name : $env:COMPUTERNAME"
Write-Output "  New name     : $newName"
if ($env:COMPUTERNAME -ieq $newName) { Write-Output "  The new name is identical to the current name -- nothing to do."; return }
if (-not $cs.PartOfDomain) {
    Write-Output "  This target is NOT domain-joined (workgroup: $($cs.Workgroup))."
    Write-Output "  Use 'Rename Computer (Workgroup/Local)' instead."
    return
}
Write-Output "  Domain       : $($cs.Domain)"
Write-Output "  Credential   : $__u  (passed explicitly to the domain -- not relying on this WinRM logon)"
$done = $false

# Attempt 1 -- Rename-Computer with an explicit domain credential
try {
    Rename-Computer -NewName $newName -DomainCredential $__cred -Force -ErrorAction Stop
    $done = $true
    Write-Output "  [1/2] Rename-Computer -DomainCredential : SUCCESS"
} catch {
    Write-Output "  [1/2] Rename-Computer -DomainCredential failed: $($_.Exception.Message)"
}

# Attempt 2 -- Win32_ComputerSystem.Rename with the credential as method arguments
if (-not $done) {
    try {
        $r = Invoke-CimMethod -InputObject $cs -MethodName Rename -Arguments @{ Name = $newName; Password = $__p; UserName = $__u } -ErrorAction Stop
        if ($r.ReturnValue -eq 0) {
            $done = $true
            Write-Output "  [2/2] Win32_ComputerSystem.Rename : SUCCESS"
        } else {
            Write-Output "  [2/2] Win32_ComputerSystem.Rename failed, code $($r.ReturnValue): $(Get-RenameReturnText $r.ReturnValue)"
        }
    } catch {
        Write-Output "  [2/2] Win32_ComputerSystem.Rename failed: $($_.Exception.Message)"
    }
}

if (-not $done) {
    Write-Output ""
    Write-Output "  RENAME DID NOT COMPLETE. What to check, in order of likelihood:"
    Write-Output "   1. The account '$__u' must be allowed to rename the COMPUTER OBJECT in AD (Domain Admin, or"
    Write-Output "      delegated rights: Write dNSHostName / sAMAccountName / servicePrincipalName on that computer)."
    Write-Output "   2. The target must be able to reach a domain controller (DNS + ports 88/389/445 from the target)."
    Write-Output "   3. No other computer object named '$newName' may already exist in the domain."
    Write-Output "   4. The username must be a DOMAIN account (DOMAIN\user or user@domain) -- a local account cannot rename a domain-joined PC."

    return
}
if ($autoRestart) {
    Write-Output "  Rename submitted -- the target restarts in 8 seconds."
    shutdown.exe /r /t 8 /c "PC Admin Tool: computer renamed to $newName" | Out-Null
} else {
    Write-Output "  Rename submitted -- Auto-Restart is OFF. The new name will NOT take effect until"
    Write-Output "  this computer restarts -- run 'Force Restart Now' (Power Recycle) when ready."
}
""",
        "danger": True,
        "needs_cred": True,
    },
    {
        "id": 'rt_rename_pc_workgroup',
        "label": 'Rename Computer (Workgroup/Local)',
        "category": 'Remote Tools',
        "description": "Rename-Computer for NON-domain targets; refuses cleanly on a domain-joined PC instead of failing with 'Access is denied' -- restart optional",
        "params": [
            {'key': 'NEW_NAME', 'kind': 'computername', 'label': 'New Computer Name', 'required': True},
            {'key': 'AUTO_RESTART', 'kind': 'bool', 'label': 'Automatically restart when done', 'required': True, 'default': 'true', 'help': "Unchecked: rename now, restart later yourself (name won't take effect until then)"},
        ],
        "command": r"""
$newName = "{{NEW_NAME}}"
$autoRestart = {{AUTO_RESTART}}
$cs = Get-CimInstance Win32_ComputerSystem
Write-Output "  Current name: $env:COMPUTERNAME"
Write-Output "  Renaming to : $newName  (workgroup/local)"
if ($env:COMPUTERNAME -ieq $newName) { Write-Output "  The new name is identical to the current name -- nothing to do."; return }
if ($cs.PartOfDomain) {
    Write-Output "  REFUSED: this target is joined to the domain '$($cs.Domain)'."
    Write-Output "  A domain-joined PC cannot be renamed without a domain credential -- that is exactly why this"
    Write-Output "  option ended in 'Access is denied'. Use 'Rename Computer (Domain-Joined)' instead."
    return
}
try {
    Rename-Computer -NewName $newName -Force -ErrorAction Stop
    if ($autoRestart) {
        Write-Output "  Rename submitted -- the target restarts in 8 seconds."
        shutdown.exe /r /t 8 /c "PC Admin Tool: computer renamed to $newName" | Out-Null
    } else {
        Write-Output "  Rename submitted -- Auto-Restart is OFF. The new name will NOT take effect until"
        Write-Output "  this computer restarts -- run 'Force Restart Now' (Power Recycle) when ready."
    }
} catch {
    Write-Output "  Rename FAILED: $($_.Exception.Message)"
    Write-Output "  A local rename needs a local ADMINISTRATOR account (use the Basic/NTLM transport with .\Administrator)."
}
""",
        "danger": True,
    },
    {
        "id": 'rt_rename_pc_wmic_legacy',
        "label": 'Rename Computer via WMIC / WMI (Legacy -- Manual Restart Required)',
        "category": 'Remote Tools',
        "description": 'wmic computersystem ... call rename on old targets; where WMIC is removed (Win11 24H2+) it automatically uses the WMI/CIM Rename method instead. Never auto-restarts',
        "params": [
            {'key': 'NEW_NAME', 'kind': 'computername', 'label': 'New Computer Name', 'required': True},
        ],
        "command": r"""
$newName = "{{NEW_NAME}}"

function Get-RenameReturnText([int]$c) {
    switch ($c) {
        5    { 'Access denied -- the account cannot rename this computer object in Active Directory' }
        53   { 'Network path not found -- the target cannot reach a domain controller' }
        87   { 'Invalid parameter -- the new name is not acceptable' }
        1219 { 'Conflicting credentials -- the target already has a connection to the DC under another account' }
        1326 { 'Logon failure -- bad user name or password for the domain' }
        1355 { 'The domain could not be contacted (DNS / DC unreachable from the target)' }
        2224 { 'A computer account with the new name already exists in the domain' }
        default { "see https://learn.microsoft.com/windows/win32/cimwin32prov/rename-method-in-class-win32-computersystem (code $c)" }
    }
}

$cs = Get-CimInstance Win32_ComputerSystem
Write-Output "  Current name: $env:COMPUTERNAME"
Write-Output "  New name    : $newName   (domain-joined: $($cs.PartOfDomain))"
if ($env:COMPUTERNAME -ieq $newName) { Write-Output "  The new name is identical to the current name -- nothing to do."; return }
$wmic = Get-Command wmic.exe -ErrorAction SilentlyContinue
if ($wmic -and -not $cs.PartOfDomain) {
    Write-Output "  wmic.exe is present -- using it."
    $result = wmic computersystem where "name='$env:COMPUTERNAME'" call rename name="$newName" 2>&1
    $result | ForEach-Object { Write-Output "  $_" }
    Write-Output "  Rename submitted via WMIC -- this does NOT auto-restart. Run 'Force Restart Now' (Power Recycle) when ready."
    return
}
if (-not $wmic) { Write-Output "  wmic.exe is not on this target (removed on Windows 11 24H2+ / recent Server) -- using the WMI/CIM Rename method instead." }
else            { Write-Output "  Target is domain-joined: WMIC cannot pass a credential -- using the WMI/CIM Rename method with your credential." }
try {
    if ($cs.PartOfDomain) { $args2 = @{ Name = $newName; Password = $__p; UserName = $__u } } else { $args2 = @{ Name = $newName } }
    $r = Invoke-CimMethod -InputObject $cs -MethodName Rename -Arguments $args2 -ErrorAction Stop
    if ($r.ReturnValue -eq 0) {
        Write-Output "  Rename submitted via WMI/CIM -- this does NOT auto-restart. Run 'Force Restart Now' (Power Recycle) when ready."
    } else {
        Write-Output "  Rename FAILED, code $($r.ReturnValue): $(Get-RenameReturnText $r.ReturnValue)"
    }
} catch {
    Write-Output "  Rename FAILED: $($_.Exception.Message)"
}
""",
        "danger": True,
        "needs_cred": True,
    },
    {
        "id": "rt_vss_view",
        "danger": False,
        "label": "VSS Shadow Copy Storage Report",
        "category": "Remote Tools",
        "description": "vssadmin list shadowstorage + list shadows -- size/usage per volume and every shadow copy instance",
        "command": r"""
Write-Output "  === VSS SHADOW STORAGE (size/usage per volume) ==="
vssadmin list shadowstorage 2>&1 | ForEach-Object { Write-Output "  $_" }
Write-Output ""
Write-Output "  === VSS SHADOW COPIES (instances) ==="
vssadmin list shadows 2>&1 | ForEach-Object { Write-Output "  $_" }
"""
    },
    {
        "id": "rt_vss_delete_all",
        "danger": True,
        "label": "Delete ALL VSS Shadow Copies (Every Volume)",
        "category": "Remote Tools",
        "description": "vssadmin delete shadows /all /quiet -- IRREVERSIBLE, removes every restore point on every volume",
        "command": r"""
Write-Output "  Deleting ALL VSS shadow copies on ALL volumes -- IRREVERSIBLE, removes every System Restore /"
Write-Output "  previous-versions recovery point on this machine."
vssadmin delete shadows /all /quiet 2>&1 | ForEach-Object { Write-Output "  $_" }
Write-Output "  Done."
"""
    },
    {
        "id": "rt_vss_delete_volume_all",
        "danger": True,
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
"""
    },
    {
        "id": "rt_vss_delete_oldest",
        "danger": True,
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
"""
    },
    {
        "id": "rt_run_scheduled_task_query",
        "danger": False,
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
"""
    },
    {
        "id": "rt_open_computer_management",
        "danger": False,
        "label": "Open Computer Management (Connected to Target)",
        "category": "Remote Tools",
        "description": "Launches mmc.exe compmgmt.msc /computer:\\\\<target> locally on the machine hosting this service (same as the desktop editions do on your own PC)",
        "command": r"""
# Handled specially by the host application -- never actually sent to the remote target.
# Desktop editions (PowerShell / Python GUI) launch locally:
#   mmc.exe compmgmt.msc /computer:\\<target>
# The Web edition returns that command as text instead of executing anything,
# since a server cannot open a window on your screen.
Write-Output "  (informational placeholder -- see description)"
"""
    },
    {
        "id": "rt_restart_service",
        "danger": True,
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
"""
    },
    {
        "id": "rt_list_all_services",
        "danger": False,
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
"""
    },
    {
        "id": "rt_map_network_drive",
        "danger": True,
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
"""
    },
    {
        "id": "rt_unmap_network_drive",
        "danger": True,
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
"""
    },
    {
        "id": "rt_list_mapped_drives",
        "danger": False,
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
"""
    },
    # ═══ v3.7 additions: VSS size ops, DISM/WMI tuning, Admin Consoles ═══
    {
        "id": 'rt_vss_size_report',
        "label": 'VSS Storage Size Report (Used / Allocated / Max vs Volume Size)',
        "category": 'Remote Tools',
        "description": "Per volume: shadow storage Used, Allocated and Max (as GB and % of the volume), where it is stored, and the volume's free space",
        "command": r"""
function Fmt($b) { if ($null -eq $b) { return 'n/a' }; if ($b -ge 1TB) { '{0:N2} TB' -f ($b/1TB) } elseif ($b -ge 1GB) { '{0:N2} GB' -f ($b/1GB) } else { '{0:N0} MB' -f ($b/1MB) } }
$st = @(Get-CimInstance Win32_ShadowStorage -ErrorAction SilentlyContinue)
Write-Output "  === VSS STORAGE SIZE vs VOLUME SIZE ==="
if ($st.Count -eq 0) {
    Write-Output "  No shadow-copy storage is configured on any volume (System Protection is off everywhere)."
    Write-Output "  Use 'Set VSS Max Storage Size' to create it."
    return
}
$vols = @{}
Get-CimInstance Win32_Volume -ErrorAction SilentlyContinue | ForEach-Object { $vols[$_.DeviceID] = $_ }
foreach ($s in $st) {
    $v  = $vols[$s.Volume.DeviceID]
    $dv = $vols[$s.DiffVolume.DeviceID]
    $name = if ($v -and $v.DriveLetter) { $v.DriveLetter } else { $s.Volume.DeviceID }
    $on   = if ($dv -and $dv.DriveLetter) { $dv.DriveLetter } else { $s.DiffVolume.DeviceID }
    $unb  = ($s.MaxSpace -lt 0) -or ($s.MaxSpace -gt 9e18)
    Write-Output ""
    Write-Output "  Volume $name   (capacity $(Fmt $v.Capacity), free $(Fmt $v.FreeSpace))"
    Write-Output "    Stored on     : $on"
    Write-Output "    Used          : $(Fmt $s.UsedSpace)"
    Write-Output "    Allocated     : $(Fmt $s.AllocatedSpace)"
    if ($unb) { Write-Output "    Maximum       : UNBOUNDED  (can grow until the volume is full)" }
    else {
        $pct = if ($v -and $v.Capacity) { [math]::Round(100.0 * $s.MaxSpace / $v.Capacity, 1) } else { 'n/a' }
        Write-Output "    Maximum       : $(Fmt $s.MaxSpace)  ($pct % of the volume)"
    }
}
$cnt = @(Get-CimInstance Win32_ShadowCopy -ErrorAction SilentlyContinue).Count
Write-Output ""
Write-Output "  Shadow copies currently stored: $cnt"
""",
        "danger": False,
    },
    {
        "id": 'rt_vss_set_maxsize',
        "label": 'Set VSS Max Storage Size (Resize / Create Shadow Storage)',
        "category": 'Remote Tools',
        "description": 'vssadmin resize/add shadowstorage /maxsize=... -- limit how much disk shadow copies may use (e.g. 10GB, 20%, UNBOUNDED). Shrinking deletes the OLDEST copies',
        "params": [
            {'key': 'VOLUME', 'kind': 'drive', 'label': 'Volume to protect (drive letter)', 'required': True, 'default': 'C'},
            {'key': 'MAX_SIZE', 'kind': 'vsssize', 'label': 'Max size (e.g. 10GB, 20%, 500MB, UNBOUNDED)', 'required': True, 'default': '10GB', 'help': 'Minimum 320MB. A percentage is of the volume capacity.'},
            {'key': 'STORAGE_VOLUME', 'kind': 'drive', 'label': 'Store shadow data on (blank = same volume)', 'required': False},
        ],
        "command": r"""
$vol  = ("{{VOLUME}}".TrimEnd(':')).ToUpper() + ':'
$size = "{{MAX_SIZE}}"
$on   = "{{STORAGE_VOLUME}}"
if ($on) { $on = ($on.TrimEnd(':')).ToUpper() + ':' } else { $on = $vol }
Write-Output "  Volume: $vol    Storage on: $on    New max size: $size"
$v = Get-CimInstance Win32_Volume -Filter "DriveLetter='$vol'" -ErrorAction SilentlyContinue
if (-not $v) { Write-Output "  Volume $vol was not found on this target."; return }
$exists = @(Get-CimInstance Win32_ShadowStorage -ErrorAction SilentlyContinue | Where-Object { $_.Volume.DeviceID -eq $v.DeviceID }).Count -gt 0
if ($exists) {
    Write-Output "  Shadow storage already exists for $vol -- resizing."
    vssadmin resize shadowstorage /for=$vol /on=$on /maxsize=$size 2>&1 | ForEach-Object { Write-Output "  $_" }
} else {
    Write-Output "  No shadow storage for $vol yet -- creating it."
    vssadmin add shadowstorage /for=$vol /on=$on /maxsize=$size 2>&1 | ForEach-Object { Write-Output "  $_" }
}
Write-Output ""
Write-Output "  === RESULT ==="
vssadmin list shadowstorage /for=$vol 2>&1 | ForEach-Object { Write-Output "  $_" }
""",
        "danger": True,
    },
    {
        "id": 'rt_vss_create_snapshot',
        "label": 'Create a VSS Shadow Copy Now (One Volume)',
        "category": 'Remote Tools',
        "description": 'Creates a restore point / shadow copy of one volume immediately (works on client and server Windows via WMI)',
        "params": [
            {'key': 'VOLUME', 'kind': 'drive', 'label': 'Volume (drive letter)', 'required': True, 'default': 'C'},
        ],
        "command": r"""
$vol = ("{{VOLUME}}".TrimEnd(':')).ToUpper() + ':'
Write-Output "  Creating a shadow copy of $vol ..."
try {
    $r = Invoke-CimMethod -ClassName Win32_ShadowCopy -MethodName Create -Arguments @{ Volume = "$vol\"; Context = 'ClientAccessible' } -ErrorAction Stop
    if ($r.ReturnValue -eq 0) { Write-Output "  Created. Shadow ID: $($r.ShadowID)" }
    else { Write-Output "  Failed, WMI return code $($r.ReturnValue) (1=access denied, 2=invalid arg, 4=unsupported volume, 5=insufficient storage, 6=max copies reached, 9=not enough free space)." }
} catch { Write-Output "  Failed: $($_.Exception.Message)" }
""",
        "danger": False,
    },
    {
        "id": 'perf_dism_analyze_store',
        "label": 'DISM: Analyze Component Store (Reclaimable Space)',
        "category": 'Performance',
        "description": 'Dism /Online /Cleanup-Image /AnalyzeComponentStore -- read-only; says whether a cleanup is worthwhile and how much WinSxS can be reclaimed',
        "command": r"""
function Run-Dism([string[]]$a) {
    Write-Output "  > Dism.exe $($a -join ' ')"
    $o = & Dism.exe @a 2>&1 | Out-String
    foreach ($ln in ($o -split "[\r\n]+")) {
        $t = $ln.Trim()
        if ($t -and $t -notmatch '^\[[= ]*[\d\.]+%[= ]*\]$') { Write-Output "    $t" }
    }
    Write-Output "    (exit code $LASTEXITCODE)"
}

Write-Output "  === COMPONENT STORE ANALYSIS (read-only) ==="
Run-Dism @('/Online','/Cleanup-Image','/AnalyzeComponentStore')
""",
        "danger": False,
        "detached": True,
        "wait_sec": 1800,
    },
    {
        "id": 'perf_dism_component_cleanup',
        "label": 'DISM: Component Store Cleanup (StartComponentCleanup)',
        "category": 'Performance',
        "description": 'Dism /Online /Cleanup-Image /StartComponentCleanup -- removes superseded component versions from WinSxS. Safe; updates stay uninstallable. Can take many minutes',
        "command": r"""
function Run-Dism([string[]]$a) {
    Write-Output "  > Dism.exe $($a -join ' ')"
    $o = & Dism.exe @a 2>&1 | Out-String
    foreach ($ln in ($o -split "[\r\n]+")) {
        $t = $ln.Trim()
        if ($t -and $t -notmatch '^\[[= ]*[\d\.]+%[= ]*\]$') { Write-Output "    $t" }
    }
    Write-Output "    (exit code $LASTEXITCODE)"
}

$drv = Get-PSDrive C -ErrorAction SilentlyContinue
if ($drv) { $before = $drv.Free }
Write-Output "  === COMPONENT STORE CLEANUP ==="
Run-Dism @('/Online','/Cleanup-Image','/StartComponentCleanup')
$drv = Get-PSDrive C -ErrorAction SilentlyContinue
if ($drv -and $before) { Write-Output ("  C: free space change: {0:N0} MB" -f (($drv.Free - $before)/1MB)) }
""",
        "danger": False,
        "detached": True,
        "wait_sec": 3600,
    },
    {
        "id": 'perf_dism_resetbase',
        "label": 'DISM: Deep Cleanup (StartComponentCleanup /ResetBase)',
        "category": 'Performance',
        "description": 'Dism ... /StartComponentCleanup /ResetBase -- reclaims the most WinSxS space BUT already-installed updates can no longer be uninstalled',
        "command": r"""
function Run-Dism([string[]]$a) {
    Write-Output "  > Dism.exe $($a -join ' ')"
    $o = & Dism.exe @a 2>&1 | Out-String
    foreach ($ln in ($o -split "[\r\n]+")) {
        $t = $ln.Trim()
        if ($t -and $t -notmatch '^\[[= ]*[\d\.]+%[= ]*\]$') { Write-Output "    $t" }
    }
    Write-Output "    (exit code $LASTEXITCODE)"
}

Write-Output "  === DEEP COMPONENT CLEANUP (/ResetBase) -- installed updates become permanent ==="
Run-Dism @('/Online','/Cleanup-Image','/StartComponentCleanup','/ResetBase')
""",
        "danger": True,
        "detached": True,
        "wait_sec": 3600,
    },
    {
        "id": 'perf_dism_health_scan',
        "label": 'DISM: Image Health Check + Scan (CheckHealth, ScanHealth)',
        "category": 'Performance',
        "description": "Dism /CheckHealth then /ScanHealth -- detects Windows image corruption without changing anything (RestoreHealth is 'Run DISM' under Windows Health)",
        "command": r"""
function Run-Dism([string[]]$a) {
    Write-Output "  > Dism.exe $($a -join ' ')"
    $o = & Dism.exe @a 2>&1 | Out-String
    foreach ($ln in ($o -split "[\r\n]+")) {
        $t = $ln.Trim()
        if ($t -and $t -notmatch '^\[[= ]*[\d\.]+%[= ]*\]$') { Write-Output "    $t" }
    }
    Write-Output "    (exit code $LASTEXITCODE)"
}

Write-Output "  === IMAGE HEALTH (read-only) ==="
Run-Dism @('/Online','/Cleanup-Image','/CheckHealth')
Run-Dism @('/Online','/Cleanup-Image','/ScanHealth')
""",
        "danger": False,
        "detached": True,
        "wait_sec": 3600,
    },
    {
        "id": 'perf_wmi_repo_check',
        "label": 'WMI: Verify Repository + CIM Performance Snapshot (WMIC replacement)',
        "category": 'Performance',
        "description": 'winmgmt /verifyrepository plus a CIM snapshot of CPU, memory, page file, disks and top memory users. WMIC is removed on new Windows, so this uses CIM',
        "command": r"""
Write-Output "  === WMI REPOSITORY ==="
$v = (winmgmt /verifyrepository 2>&1 | Out-String).Trim()
Write-Output "  $v"
Write-Output ""
Write-Output "  === CIM SNAPSHOT (what WMIC used to show) ==="
$os  = Get-CimInstance Win32_OperatingSystem
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
Write-Output ("  OS            : {0}  build {1}" -f $os.Caption, $os.BuildNumber)
Write-Output ("  Uptime        : {0:N1} days" -f ((Get-Date) - $os.LastBootUpTime).TotalDays)
Write-Output ("  CPU           : {0}  ({1} cores / {2} logical)  load {3}%" -f $cpu.Name.Trim(), $cpu.NumberOfCores, $cpu.NumberOfLogicalProcessors, $cpu.LoadPercentage)
Write-Output ("  Memory        : {0:N1} GB free of {1:N1} GB" -f ($os.FreePhysicalMemory/1MB), ($os.TotalVisibleMemorySize/1MB))
foreach ($p in (Get-CimInstance Win32_PageFileUsage)) { Write-Output ("  Page file     : {0}  {1} MB used of {2} MB (peak {3})" -f $p.Name, $p.CurrentUsage, $p.AllocatedBaseSize, $p.PeakUsage) }
Write-Output ("  Auto page file: {0}" -f (Get-CimInstance Win32_ComputerSystem).AutomaticManagedPagefile)
foreach ($d in (Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3")) { Write-Output ("  Disk {0}        : {1:N1} GB free of {2:N1} GB" -f $d.DeviceID, ($d.FreeSpace/1GB), ($d.Size/1GB)) }
Write-Output "  Top 8 processes by working set:"
Get-CimInstance Win32_Process | Sort-Object WorkingSetSize -Descending | Select-Object -First 8 | ForEach-Object { Write-Output ("    {0,-28} {1,8:N0} MB   PID {2}" -f $_.Name, ($_.WorkingSetSize/1MB), $_.ProcessId) }
if (Get-Command wmic.exe -ErrorAction SilentlyContinue) { Write-Output ""; Write-Output "  (wmic.exe is present on this target; CIM above is the supported replacement.)" }
else { Write-Output ""; Write-Output "  (wmic.exe is not installed on this target -- expected on current Windows; CIM covers everything above.)" }
""",
        "danger": False,
    },
    {
        "id": 'perf_wmi_repo_repair',
        "label": 'WMI: Salvage / Repair Repository',
        "category": 'Performance',
        "description": 'winmgmt /salvagerepository (then /resetrepository only if still inconsistent and you re-run with it). Fixes slow or broken WMI/CIM queries. Restarts the WMI service',
        "command": r"""
Write-Output "  Verifying WMI repository..."
$v = (winmgmt /verifyrepository 2>&1 | Out-String).Trim()
Write-Output "  $v"
if ($v -match 'consistent' -and $v -notmatch 'not consistent|inconsistent') {
    Write-Output "  Repository is consistent -- nothing to repair."
    return
}
Write-Output "  Repository is NOT consistent -- salvaging..."
$s = (winmgmt /salvagerepository 2>&1 | Out-String).Trim()
Write-Output "  $s"
Start-Sleep -Seconds 3
$v2 = (winmgmt /verifyrepository 2>&1 | Out-String).Trim()
Write-Output "  After salvage: $v2"
""",
        "danger": True,
    },
    {
        "id": 'perf_rebuild_perf_counters',
        "label": 'Rebuild Performance Counters (lodctr /R) + Resync WMI Perf',
        "category": 'Performance',
        "description": 'lodctr /R, winmgmt /resyncperf, wmiadap /f -- fixes missing or corrupt Task Manager / PerfMon counters',
        "command": r"""
Write-Output "  Rebuilding performance counter registry (lodctr /R)..."
lodctr /R 2>&1 | ForEach-Object { Write-Output "  $_" }
Write-Output "  Re-syncing WMI performance classes..."
winmgmt /resyncperf 2>&1 | ForEach-Object { Write-Output "  $_" }
wmiadap.exe /f 2>&1 | ForEach-Object { Write-Output "  $_" }
Write-Output "  Done. Counters are re-registered; a restart makes it fully clean."
""",
        "danger": True,
    },
    {
        "id": 'perf_trim_ssd',
        "label": 'Retrim SSD Volumes (Optimize-Volume -ReTrim)',
        "category": 'Performance',
        "description": 'Sends TRIM for every fixed NTFS volume on SSD media so the drive can reclaim free blocks. HDDs are skipped',
        "command": r"""
$any = $false
foreach ($v in (Get-Volume | Where-Object { $_.DriveLetter -and $_.DriveType -eq 'Fixed' -and $_.FileSystem -eq 'NTFS' })) {
    $media = $null
    try { $media = (Get-Partition -DriveLetter $v.DriveLetter -ErrorAction Stop | Get-Disk -ErrorAction Stop | Get-PhysicalDisk -ErrorAction Stop).MediaType } catch {}
    if ($media -eq 'SSD') {
        $any = $true
        Write-Output "  $($v.DriveLetter): SSD -- retrim..."
        try { Optimize-Volume -DriveLetter $v.DriveLetter -ReTrim -ErrorAction Stop; Write-Output "  $($v.DriveLetter): retrim complete" }
        catch { Write-Output "  $($v.DriveLetter): failed -- $($_.Exception.Message)" }
    } else { Write-Output "  $($v.DriveLetter): media type '$media' -- skipped (not SSD)" }
}
if (-not $any) { Write-Output "  No SSD volumes found -- nothing to trim." }
""",
        "danger": False,
        "detached": True,
        "wait_sec": 1800,
    },
    {
        "id": 'perf_pagefile_system_managed',
        "label": 'Page File: Switch to System-Managed Size',
        "category": 'Performance',
        "description": 'Sets AutomaticManagedPagefile = True so Windows sizes the page file itself (fixes a too-small / fixed page file). Takes effect after a restart',
        "command": r"""
$cs = Get-CimInstance Win32_ComputerSystem
Write-Output "  Automatic page-file management is currently: $($cs.AutomaticManagedPagefile)"
if ($cs.AutomaticManagedPagefile) { Write-Output "  Already system-managed -- nothing to change."; return }
try {
    Set-CimInstance -InputObject $cs -Property @{ AutomaticManagedPagefile = $true } -ErrorAction Stop
    Write-Output "  Switched to system-managed. Restart the target for it to take effect."
} catch { Write-Output "  Failed: $($_.Exception.Message)" }
""",
        "danger": True,
    },
    {
        "id": 'rc_computer_mgmt',
        "label": 'Open Computer Management on Target',
        "category": 'Admin Consoles',
        "description": "Opens on the TARGET's screen (not yours) using the admin credentials you entered -- compmgmt.msc -- users, services, disks, event viewer in one console",
        "command": r"""
$exe   = 'mmc.exe'
$argl  = 'compmgmt.msc'
$label = 'Computer Management'

$cs = Get-CimInstance Win32_ComputerSystem -ErrorAction SilentlyContinue
$consoleUser = $cs.UserName
if (-not $consoleUser) {
    Write-Output "  Nobody is signed in at the target's physical console (a Remote Desktop-only session does not count)."
    Write-Output "  There is no screen to open $label on -- sign in at the target, then run this again."
    return
}
Write-Output "  Console session user : $consoleUser"

$full = $exe
$gc = Get-Command $exe -ErrorAction SilentlyContinue
if ($gc -and $gc.Source) { $full = $gc.Source }
elseif (-not [IO.Path]::IsPathRooted($exe)) { $full = Join-Path $env:SystemRoot ('System32\' + $exe) }
$cmdText = if ($argl) { "$full $argl" } else { $full }
Write-Output "  Launching            : $cmdText"

if (-not ('PCAConsole' -as [type])) {
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class PCAConsole {
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct STARTUPINFO { public int cb; public string lpReserved; public string lpDesktop; public string lpTitle;
        public int dwX; public int dwY; public int dwXSize; public int dwYSize; public int dwXCountChars; public int dwYCountChars;
        public int dwFillAttribute; public int dwFlags; public short wShowWindow; public short cbReserved2;
        public IntPtr lpReserved2; public IntPtr hStdInput; public IntPtr hStdOutput; public IntPtr hStdError; }
    [StructLayout(LayoutKind.Sequential)]
    struct PROCESS_INFORMATION { public IntPtr hProcess; public IntPtr hThread; public int dwProcessId; public int dwThreadId; }
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct PROFILEINFO { public int dwSize; public int dwFlags; public string lpUserName; public string lpProfilePath;
        public string lpDefaultPath; public string lpServerName; public string lpPolicyPath; public IntPtr hProfile; }
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LogonUser(string u, string d, string p, int type, int prov, out IntPtr tok);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool DuplicateTokenEx(IntPtr h, uint acc, IntPtr attr, int lvl, int type, out IntPtr nt);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool GetTokenInformation(IntPtr t, int cls, IntPtr info, int len, out int ret);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool SetTokenInformation(IntPtr t, int cls, IntPtr info, int len);
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool CreateProcessAsUser(IntPtr tok, string app, string cmd, IntPtr pa, IntPtr ta, bool inh,
        uint flags, IntPtr env, string cwd, ref STARTUPINFO si, out PROCESS_INFORMATION pi);
    [DllImport("userenv.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LoadUserProfile(IntPtr tok, ref PROFILEINFO pi);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool CreateEnvironmentBlock(out IntPtr env, IntPtr tok, bool inh);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool DestroyEnvironmentBlock(IntPtr env);
    [DllImport("kernel32.dll")]
    static extern uint WTSGetActiveConsoleSessionId();
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern bool CloseHandle(IntPtr h);

    public static string Launch(string account, string password, string app, string args) {
        string domain = null, user = account;
        int i = account.IndexOf('\\');
        if (i > 0) { domain = account.Substring(0, i); user = account.Substring(i + 1); }
        else if (account.IndexOf('@') < 0) { domain = "."; }
        IntPtr tok = IntPtr.Zero, prim = IntPtr.Zero, env = IntPtr.Zero;
        try {
            if (!LogonUser(user, domain, password, 2, 0, out tok))
                return "LogonUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            IntPtr src = tok;
            IntPtr buf = Marshal.AllocHGlobal(IntPtr.Size);
            int ret;
            if (GetTokenInformation(tok, 19, buf, IntPtr.Size, out ret)) {
                IntPtr linked = Marshal.ReadIntPtr(buf);
                if (linked != IntPtr.Zero) src = linked;
            }
            Marshal.FreeHGlobal(buf);
            if (!DuplicateTokenEx(src, 0x02000000, IntPtr.Zero, 2, 1, out prim))
                return "DuplicateTokenEx failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            uint sess = WTSGetActiveConsoleSessionId();
            if (sess == 0xFFFFFFFF) return "no active console session";
            IntPtr p = Marshal.AllocHGlobal(4);
            Marshal.WriteInt32(p, (int)sess);
            bool okSess = SetTokenInformation(prim, 12, p, 4);
            int errSess = Marshal.GetLastWin32Error();
            Marshal.FreeHGlobal(p);
            if (!okSess) return "SetTokenInformation(session) failed (Win32 error " + errSess + ")";
            PROFILEINFO pf = new PROFILEINFO();
            pf.dwSize = Marshal.SizeOf(typeof(PROFILEINFO));
            pf.lpUserName = user;
            LoadUserProfile(prim, ref pf);
            if (!CreateEnvironmentBlock(out env, prim, false)) env = IntPtr.Zero;
            STARTUPINFO si = new STARTUPINFO();
            si.cb = Marshal.SizeOf(typeof(STARTUPINFO));
            si.lpDesktop = "winsta0\\default";
            PROCESS_INFORMATION pi;
            string cmd = "\"" + app + "\"" + (string.IsNullOrEmpty(args) ? "" : " " + args);
            string cwd = Environment.GetEnvironmentVariable("SystemRoot") + "\\System32";
            if (!CreateProcessAsUser(prim, null, cmd, IntPtr.Zero, IntPtr.Zero, false, 0x410, env, cwd, ref si, out pi))
                return "CreateProcessAsUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            CloseHandle(pi.hProcess); CloseHandle(pi.hThread);
            return "OK pid=" + pi.dwProcessId + " console-session=" + sess;
        } finally {
            if (env != IntPtr.Zero) DestroyEnvironmentBlock(env);
            if (prim != IntPtr.Zero) CloseHandle(prim);
            if (tok != IntPtr.Zero) CloseHandle(tok);
        }
    }
}
'@ -ErrorAction Stop
}

$res = 'not attempted'
try { $res = [PCAConsole]::Launch($__u, $__p, $full, $argl) } catch { $res = "exception: $($_.Exception.Message)" }
if ($res -like 'OK*') {
    Start-Sleep -Seconds 2
    $pidv = [int](($res -split 'pid=')[1] -split ' ')[0]
    if (Get-Process -Id $pidv -ErrorAction SilentlyContinue) { Write-Output "  OPENED on the target's screen as $__u  ($res)" }
    else { Write-Output "  Started as $__u ($res); the program has already handed off to another process or closed -- check the target's screen." }
    return
}
Write-Output "  Launch as the supplied admin account did not work: $res"
Write-Output "  Falling back to the account signed in at the console ($consoleUser)..."
try {
    $tn = 'PCAdminTool_UI_' + [guid]::NewGuid().ToString('N').Substring(0,8)
    if ($argl) { $a = New-ScheduledTaskAction -Execute $full -Argument $argl } else { $a = New-ScheduledTaskAction -Execute $full }
    $p = New-ScheduledTaskPrincipal -UserId $consoleUser -LogonType Interactive -RunLevel Highest
    Register-ScheduledTask -TaskName $tn -Action $a -Principal $p -Force | Out-Null
    Start-ScheduledTask -TaskName $tn
    Start-Sleep -Seconds 3
    Unregister-ScheduledTask -TaskName $tn -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "  OPENED on the target's screen as $consoleUser (fallback). It is only elevated if that account is a local administrator."
} catch { Write-Output "  Fallback failed too: $($_.Exception.Message)" }
""",
        "danger": False,
        "needs_cred": True,
        "detached": True,
        "wait_sec": 90,
    },
    {
        "id": 'rc_device_mgr',
        "label": 'Open Device Manager on Target',
        "category": 'Admin Consoles',
        "description": "Opens on the TARGET's screen (not yours) using the admin credentials you entered -- devmgmt.msc -- drivers and hardware",
        "command": r"""
$exe   = 'mmc.exe'
$argl  = 'devmgmt.msc'
$label = 'Device Manager'

$cs = Get-CimInstance Win32_ComputerSystem -ErrorAction SilentlyContinue
$consoleUser = $cs.UserName
if (-not $consoleUser) {
    Write-Output "  Nobody is signed in at the target's physical console (a Remote Desktop-only session does not count)."
    Write-Output "  There is no screen to open $label on -- sign in at the target, then run this again."
    return
}
Write-Output "  Console session user : $consoleUser"

$full = $exe
$gc = Get-Command $exe -ErrorAction SilentlyContinue
if ($gc -and $gc.Source) { $full = $gc.Source }
elseif (-not [IO.Path]::IsPathRooted($exe)) { $full = Join-Path $env:SystemRoot ('System32\' + $exe) }
$cmdText = if ($argl) { "$full $argl" } else { $full }
Write-Output "  Launching            : $cmdText"

if (-not ('PCAConsole' -as [type])) {
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class PCAConsole {
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct STARTUPINFO { public int cb; public string lpReserved; public string lpDesktop; public string lpTitle;
        public int dwX; public int dwY; public int dwXSize; public int dwYSize; public int dwXCountChars; public int dwYCountChars;
        public int dwFillAttribute; public int dwFlags; public short wShowWindow; public short cbReserved2;
        public IntPtr lpReserved2; public IntPtr hStdInput; public IntPtr hStdOutput; public IntPtr hStdError; }
    [StructLayout(LayoutKind.Sequential)]
    struct PROCESS_INFORMATION { public IntPtr hProcess; public IntPtr hThread; public int dwProcessId; public int dwThreadId; }
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct PROFILEINFO { public int dwSize; public int dwFlags; public string lpUserName; public string lpProfilePath;
        public string lpDefaultPath; public string lpServerName; public string lpPolicyPath; public IntPtr hProfile; }
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LogonUser(string u, string d, string p, int type, int prov, out IntPtr tok);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool DuplicateTokenEx(IntPtr h, uint acc, IntPtr attr, int lvl, int type, out IntPtr nt);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool GetTokenInformation(IntPtr t, int cls, IntPtr info, int len, out int ret);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool SetTokenInformation(IntPtr t, int cls, IntPtr info, int len);
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool CreateProcessAsUser(IntPtr tok, string app, string cmd, IntPtr pa, IntPtr ta, bool inh,
        uint flags, IntPtr env, string cwd, ref STARTUPINFO si, out PROCESS_INFORMATION pi);
    [DllImport("userenv.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LoadUserProfile(IntPtr tok, ref PROFILEINFO pi);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool CreateEnvironmentBlock(out IntPtr env, IntPtr tok, bool inh);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool DestroyEnvironmentBlock(IntPtr env);
    [DllImport("kernel32.dll")]
    static extern uint WTSGetActiveConsoleSessionId();
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern bool CloseHandle(IntPtr h);

    public static string Launch(string account, string password, string app, string args) {
        string domain = null, user = account;
        int i = account.IndexOf('\\');
        if (i > 0) { domain = account.Substring(0, i); user = account.Substring(i + 1); }
        else if (account.IndexOf('@') < 0) { domain = "."; }
        IntPtr tok = IntPtr.Zero, prim = IntPtr.Zero, env = IntPtr.Zero;
        try {
            if (!LogonUser(user, domain, password, 2, 0, out tok))
                return "LogonUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            IntPtr src = tok;
            IntPtr buf = Marshal.AllocHGlobal(IntPtr.Size);
            int ret;
            if (GetTokenInformation(tok, 19, buf, IntPtr.Size, out ret)) {
                IntPtr linked = Marshal.ReadIntPtr(buf);
                if (linked != IntPtr.Zero) src = linked;
            }
            Marshal.FreeHGlobal(buf);
            if (!DuplicateTokenEx(src, 0x02000000, IntPtr.Zero, 2, 1, out prim))
                return "DuplicateTokenEx failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            uint sess = WTSGetActiveConsoleSessionId();
            if (sess == 0xFFFFFFFF) return "no active console session";
            IntPtr p = Marshal.AllocHGlobal(4);
            Marshal.WriteInt32(p, (int)sess);
            bool okSess = SetTokenInformation(prim, 12, p, 4);
            int errSess = Marshal.GetLastWin32Error();
            Marshal.FreeHGlobal(p);
            if (!okSess) return "SetTokenInformation(session) failed (Win32 error " + errSess + ")";
            PROFILEINFO pf = new PROFILEINFO();
            pf.dwSize = Marshal.SizeOf(typeof(PROFILEINFO));
            pf.lpUserName = user;
            LoadUserProfile(prim, ref pf);
            if (!CreateEnvironmentBlock(out env, prim, false)) env = IntPtr.Zero;
            STARTUPINFO si = new STARTUPINFO();
            si.cb = Marshal.SizeOf(typeof(STARTUPINFO));
            si.lpDesktop = "winsta0\\default";
            PROCESS_INFORMATION pi;
            string cmd = "\"" + app + "\"" + (string.IsNullOrEmpty(args) ? "" : " " + args);
            string cwd = Environment.GetEnvironmentVariable("SystemRoot") + "\\System32";
            if (!CreateProcessAsUser(prim, null, cmd, IntPtr.Zero, IntPtr.Zero, false, 0x410, env, cwd, ref si, out pi))
                return "CreateProcessAsUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            CloseHandle(pi.hProcess); CloseHandle(pi.hThread);
            return "OK pid=" + pi.dwProcessId + " console-session=" + sess;
        } finally {
            if (env != IntPtr.Zero) DestroyEnvironmentBlock(env);
            if (prim != IntPtr.Zero) CloseHandle(prim);
            if (tok != IntPtr.Zero) CloseHandle(tok);
        }
    }
}
'@ -ErrorAction Stop
}

$res = 'not attempted'
try { $res = [PCAConsole]::Launch($__u, $__p, $full, $argl) } catch { $res = "exception: $($_.Exception.Message)" }
if ($res -like 'OK*') {
    Start-Sleep -Seconds 2
    $pidv = [int](($res -split 'pid=')[1] -split ' ')[0]
    if (Get-Process -Id $pidv -ErrorAction SilentlyContinue) { Write-Output "  OPENED on the target's screen as $__u  ($res)" }
    else { Write-Output "  Started as $__u ($res); the program has already handed off to another process or closed -- check the target's screen." }
    return
}
Write-Output "  Launch as the supplied admin account did not work: $res"
Write-Output "  Falling back to the account signed in at the console ($consoleUser)..."
try {
    $tn = 'PCAdminTool_UI_' + [guid]::NewGuid().ToString('N').Substring(0,8)
    if ($argl) { $a = New-ScheduledTaskAction -Execute $full -Argument $argl } else { $a = New-ScheduledTaskAction -Execute $full }
    $p = New-ScheduledTaskPrincipal -UserId $consoleUser -LogonType Interactive -RunLevel Highest
    Register-ScheduledTask -TaskName $tn -Action $a -Principal $p -Force | Out-Null
    Start-ScheduledTask -TaskName $tn
    Start-Sleep -Seconds 3
    Unregister-ScheduledTask -TaskName $tn -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "  OPENED on the target's screen as $consoleUser (fallback). It is only elevated if that account is a local administrator."
} catch { Write-Output "  Fallback failed too: $($_.Exception.Message)" }
""",
        "danger": False,
        "needs_cred": True,
        "detached": True,
        "wait_sec": 90,
    },
    {
        "id": 'rc_disk_mgmt',
        "label": 'Open Disk Management on Target',
        "category": 'Admin Consoles',
        "description": "Opens on the TARGET's screen (not yours) using the admin credentials you entered -- diskmgmt.msc -- partitions, volumes, drive letters",
        "command": r"""
$exe   = 'mmc.exe'
$argl  = 'diskmgmt.msc'
$label = 'Disk Management'

$cs = Get-CimInstance Win32_ComputerSystem -ErrorAction SilentlyContinue
$consoleUser = $cs.UserName
if (-not $consoleUser) {
    Write-Output "  Nobody is signed in at the target's physical console (a Remote Desktop-only session does not count)."
    Write-Output "  There is no screen to open $label on -- sign in at the target, then run this again."
    return
}
Write-Output "  Console session user : $consoleUser"

$full = $exe
$gc = Get-Command $exe -ErrorAction SilentlyContinue
if ($gc -and $gc.Source) { $full = $gc.Source }
elseif (-not [IO.Path]::IsPathRooted($exe)) { $full = Join-Path $env:SystemRoot ('System32\' + $exe) }
$cmdText = if ($argl) { "$full $argl" } else { $full }
Write-Output "  Launching            : $cmdText"

if (-not ('PCAConsole' -as [type])) {
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class PCAConsole {
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct STARTUPINFO { public int cb; public string lpReserved; public string lpDesktop; public string lpTitle;
        public int dwX; public int dwY; public int dwXSize; public int dwYSize; public int dwXCountChars; public int dwYCountChars;
        public int dwFillAttribute; public int dwFlags; public short wShowWindow; public short cbReserved2;
        public IntPtr lpReserved2; public IntPtr hStdInput; public IntPtr hStdOutput; public IntPtr hStdError; }
    [StructLayout(LayoutKind.Sequential)]
    struct PROCESS_INFORMATION { public IntPtr hProcess; public IntPtr hThread; public int dwProcessId; public int dwThreadId; }
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct PROFILEINFO { public int dwSize; public int dwFlags; public string lpUserName; public string lpProfilePath;
        public string lpDefaultPath; public string lpServerName; public string lpPolicyPath; public IntPtr hProfile; }
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LogonUser(string u, string d, string p, int type, int prov, out IntPtr tok);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool DuplicateTokenEx(IntPtr h, uint acc, IntPtr attr, int lvl, int type, out IntPtr nt);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool GetTokenInformation(IntPtr t, int cls, IntPtr info, int len, out int ret);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool SetTokenInformation(IntPtr t, int cls, IntPtr info, int len);
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool CreateProcessAsUser(IntPtr tok, string app, string cmd, IntPtr pa, IntPtr ta, bool inh,
        uint flags, IntPtr env, string cwd, ref STARTUPINFO si, out PROCESS_INFORMATION pi);
    [DllImport("userenv.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LoadUserProfile(IntPtr tok, ref PROFILEINFO pi);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool CreateEnvironmentBlock(out IntPtr env, IntPtr tok, bool inh);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool DestroyEnvironmentBlock(IntPtr env);
    [DllImport("kernel32.dll")]
    static extern uint WTSGetActiveConsoleSessionId();
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern bool CloseHandle(IntPtr h);

    public static string Launch(string account, string password, string app, string args) {
        string domain = null, user = account;
        int i = account.IndexOf('\\');
        if (i > 0) { domain = account.Substring(0, i); user = account.Substring(i + 1); }
        else if (account.IndexOf('@') < 0) { domain = "."; }
        IntPtr tok = IntPtr.Zero, prim = IntPtr.Zero, env = IntPtr.Zero;
        try {
            if (!LogonUser(user, domain, password, 2, 0, out tok))
                return "LogonUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            IntPtr src = tok;
            IntPtr buf = Marshal.AllocHGlobal(IntPtr.Size);
            int ret;
            if (GetTokenInformation(tok, 19, buf, IntPtr.Size, out ret)) {
                IntPtr linked = Marshal.ReadIntPtr(buf);
                if (linked != IntPtr.Zero) src = linked;
            }
            Marshal.FreeHGlobal(buf);
            if (!DuplicateTokenEx(src, 0x02000000, IntPtr.Zero, 2, 1, out prim))
                return "DuplicateTokenEx failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            uint sess = WTSGetActiveConsoleSessionId();
            if (sess == 0xFFFFFFFF) return "no active console session";
            IntPtr p = Marshal.AllocHGlobal(4);
            Marshal.WriteInt32(p, (int)sess);
            bool okSess = SetTokenInformation(prim, 12, p, 4);
            int errSess = Marshal.GetLastWin32Error();
            Marshal.FreeHGlobal(p);
            if (!okSess) return "SetTokenInformation(session) failed (Win32 error " + errSess + ")";
            PROFILEINFO pf = new PROFILEINFO();
            pf.dwSize = Marshal.SizeOf(typeof(PROFILEINFO));
            pf.lpUserName = user;
            LoadUserProfile(prim, ref pf);
            if (!CreateEnvironmentBlock(out env, prim, false)) env = IntPtr.Zero;
            STARTUPINFO si = new STARTUPINFO();
            si.cb = Marshal.SizeOf(typeof(STARTUPINFO));
            si.lpDesktop = "winsta0\\default";
            PROCESS_INFORMATION pi;
            string cmd = "\"" + app + "\"" + (string.IsNullOrEmpty(args) ? "" : " " + args);
            string cwd = Environment.GetEnvironmentVariable("SystemRoot") + "\\System32";
            if (!CreateProcessAsUser(prim, null, cmd, IntPtr.Zero, IntPtr.Zero, false, 0x410, env, cwd, ref si, out pi))
                return "CreateProcessAsUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            CloseHandle(pi.hProcess); CloseHandle(pi.hThread);
            return "OK pid=" + pi.dwProcessId + " console-session=" + sess;
        } finally {
            if (env != IntPtr.Zero) DestroyEnvironmentBlock(env);
            if (prim != IntPtr.Zero) CloseHandle(prim);
            if (tok != IntPtr.Zero) CloseHandle(tok);
        }
    }
}
'@ -ErrorAction Stop
}

$res = 'not attempted'
try { $res = [PCAConsole]::Launch($__u, $__p, $full, $argl) } catch { $res = "exception: $($_.Exception.Message)" }
if ($res -like 'OK*') {
    Start-Sleep -Seconds 2
    $pidv = [int](($res -split 'pid=')[1] -split ' ')[0]
    if (Get-Process -Id $pidv -ErrorAction SilentlyContinue) { Write-Output "  OPENED on the target's screen as $__u  ($res)" }
    else { Write-Output "  Started as $__u ($res); the program has already handed off to another process or closed -- check the target's screen." }
    return
}
Write-Output "  Launch as the supplied admin account did not work: $res"
Write-Output "  Falling back to the account signed in at the console ($consoleUser)..."
try {
    $tn = 'PCAdminTool_UI_' + [guid]::NewGuid().ToString('N').Substring(0,8)
    if ($argl) { $a = New-ScheduledTaskAction -Execute $full -Argument $argl } else { $a = New-ScheduledTaskAction -Execute $full }
    $p = New-ScheduledTaskPrincipal -UserId $consoleUser -LogonType Interactive -RunLevel Highest
    Register-ScheduledTask -TaskName $tn -Action $a -Principal $p -Force | Out-Null
    Start-ScheduledTask -TaskName $tn
    Start-Sleep -Seconds 3
    Unregister-ScheduledTask -TaskName $tn -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "  OPENED on the target's screen as $consoleUser (fallback). It is only elevated if that account is a local administrator."
} catch { Write-Output "  Fallback failed too: $($_.Exception.Message)" }
""",
        "danger": False,
        "needs_cred": True,
        "detached": True,
        "wait_sec": 90,
    },
    {
        "id": 'rc_defrag_gui',
        "label": 'Open Defragment and Optimize Drives (dfrgui) on Target',
        "category": 'Admin Consoles',
        "description": "Opens on the TARGET's screen (not yours) using the admin credentials you entered -- dfrgui.exe -- analyze / optimize / retrim drives with the GUI",
        "command": r"""
$exe   = 'dfrgui.exe'
$argl  = ''
$label = 'Defragment and Optimize Drives (dfrgui)'

$cs = Get-CimInstance Win32_ComputerSystem -ErrorAction SilentlyContinue
$consoleUser = $cs.UserName
if (-not $consoleUser) {
    Write-Output "  Nobody is signed in at the target's physical console (a Remote Desktop-only session does not count)."
    Write-Output "  There is no screen to open $label on -- sign in at the target, then run this again."
    return
}
Write-Output "  Console session user : $consoleUser"

$full = $exe
$gc = Get-Command $exe -ErrorAction SilentlyContinue
if ($gc -and $gc.Source) { $full = $gc.Source }
elseif (-not [IO.Path]::IsPathRooted($exe)) { $full = Join-Path $env:SystemRoot ('System32\' + $exe) }
$cmdText = if ($argl) { "$full $argl" } else { $full }
Write-Output "  Launching            : $cmdText"

if (-not ('PCAConsole' -as [type])) {
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class PCAConsole {
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct STARTUPINFO { public int cb; public string lpReserved; public string lpDesktop; public string lpTitle;
        public int dwX; public int dwY; public int dwXSize; public int dwYSize; public int dwXCountChars; public int dwYCountChars;
        public int dwFillAttribute; public int dwFlags; public short wShowWindow; public short cbReserved2;
        public IntPtr lpReserved2; public IntPtr hStdInput; public IntPtr hStdOutput; public IntPtr hStdError; }
    [StructLayout(LayoutKind.Sequential)]
    struct PROCESS_INFORMATION { public IntPtr hProcess; public IntPtr hThread; public int dwProcessId; public int dwThreadId; }
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct PROFILEINFO { public int dwSize; public int dwFlags; public string lpUserName; public string lpProfilePath;
        public string lpDefaultPath; public string lpServerName; public string lpPolicyPath; public IntPtr hProfile; }
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LogonUser(string u, string d, string p, int type, int prov, out IntPtr tok);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool DuplicateTokenEx(IntPtr h, uint acc, IntPtr attr, int lvl, int type, out IntPtr nt);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool GetTokenInformation(IntPtr t, int cls, IntPtr info, int len, out int ret);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool SetTokenInformation(IntPtr t, int cls, IntPtr info, int len);
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool CreateProcessAsUser(IntPtr tok, string app, string cmd, IntPtr pa, IntPtr ta, bool inh,
        uint flags, IntPtr env, string cwd, ref STARTUPINFO si, out PROCESS_INFORMATION pi);
    [DllImport("userenv.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LoadUserProfile(IntPtr tok, ref PROFILEINFO pi);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool CreateEnvironmentBlock(out IntPtr env, IntPtr tok, bool inh);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool DestroyEnvironmentBlock(IntPtr env);
    [DllImport("kernel32.dll")]
    static extern uint WTSGetActiveConsoleSessionId();
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern bool CloseHandle(IntPtr h);

    public static string Launch(string account, string password, string app, string args) {
        string domain = null, user = account;
        int i = account.IndexOf('\\');
        if (i > 0) { domain = account.Substring(0, i); user = account.Substring(i + 1); }
        else if (account.IndexOf('@') < 0) { domain = "."; }
        IntPtr tok = IntPtr.Zero, prim = IntPtr.Zero, env = IntPtr.Zero;
        try {
            if (!LogonUser(user, domain, password, 2, 0, out tok))
                return "LogonUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            IntPtr src = tok;
            IntPtr buf = Marshal.AllocHGlobal(IntPtr.Size);
            int ret;
            if (GetTokenInformation(tok, 19, buf, IntPtr.Size, out ret)) {
                IntPtr linked = Marshal.ReadIntPtr(buf);
                if (linked != IntPtr.Zero) src = linked;
            }
            Marshal.FreeHGlobal(buf);
            if (!DuplicateTokenEx(src, 0x02000000, IntPtr.Zero, 2, 1, out prim))
                return "DuplicateTokenEx failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            uint sess = WTSGetActiveConsoleSessionId();
            if (sess == 0xFFFFFFFF) return "no active console session";
            IntPtr p = Marshal.AllocHGlobal(4);
            Marshal.WriteInt32(p, (int)sess);
            bool okSess = SetTokenInformation(prim, 12, p, 4);
            int errSess = Marshal.GetLastWin32Error();
            Marshal.FreeHGlobal(p);
            if (!okSess) return "SetTokenInformation(session) failed (Win32 error " + errSess + ")";
            PROFILEINFO pf = new PROFILEINFO();
            pf.dwSize = Marshal.SizeOf(typeof(PROFILEINFO));
            pf.lpUserName = user;
            LoadUserProfile(prim, ref pf);
            if (!CreateEnvironmentBlock(out env, prim, false)) env = IntPtr.Zero;
            STARTUPINFO si = new STARTUPINFO();
            si.cb = Marshal.SizeOf(typeof(STARTUPINFO));
            si.lpDesktop = "winsta0\\default";
            PROCESS_INFORMATION pi;
            string cmd = "\"" + app + "\"" + (string.IsNullOrEmpty(args) ? "" : " " + args);
            string cwd = Environment.GetEnvironmentVariable("SystemRoot") + "\\System32";
            if (!CreateProcessAsUser(prim, null, cmd, IntPtr.Zero, IntPtr.Zero, false, 0x410, env, cwd, ref si, out pi))
                return "CreateProcessAsUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            CloseHandle(pi.hProcess); CloseHandle(pi.hThread);
            return "OK pid=" + pi.dwProcessId + " console-session=" + sess;
        } finally {
            if (env != IntPtr.Zero) DestroyEnvironmentBlock(env);
            if (prim != IntPtr.Zero) CloseHandle(prim);
            if (tok != IntPtr.Zero) CloseHandle(tok);
        }
    }
}
'@ -ErrorAction Stop
}

$res = 'not attempted'
try { $res = [PCAConsole]::Launch($__u, $__p, $full, $argl) } catch { $res = "exception: $($_.Exception.Message)" }
if ($res -like 'OK*') {
    Start-Sleep -Seconds 2
    $pidv = [int](($res -split 'pid=')[1] -split ' ')[0]
    if (Get-Process -Id $pidv -ErrorAction SilentlyContinue) { Write-Output "  OPENED on the target's screen as $__u  ($res)" }
    else { Write-Output "  Started as $__u ($res); the program has already handed off to another process or closed -- check the target's screen." }
    return
}
Write-Output "  Launch as the supplied admin account did not work: $res"
Write-Output "  Falling back to the account signed in at the console ($consoleUser)..."
try {
    $tn = 'PCAdminTool_UI_' + [guid]::NewGuid().ToString('N').Substring(0,8)
    if ($argl) { $a = New-ScheduledTaskAction -Execute $full -Argument $argl } else { $a = New-ScheduledTaskAction -Execute $full }
    $p = New-ScheduledTaskPrincipal -UserId $consoleUser -LogonType Interactive -RunLevel Highest
    Register-ScheduledTask -TaskName $tn -Action $a -Principal $p -Force | Out-Null
    Start-ScheduledTask -TaskName $tn
    Start-Sleep -Seconds 3
    Unregister-ScheduledTask -TaskName $tn -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "  OPENED on the target's screen as $consoleUser (fallback). It is only elevated if that account is a local administrator."
} catch { Write-Output "  Fallback failed too: $($_.Exception.Message)" }
""",
        "danger": False,
        "needs_cred": True,
        "detached": True,
        "wait_sec": 90,
    },
    {
        "id": 'rc_disk_cleanup',
        "label": 'Open Disk Cleanup (cleanmgr) on Target',
        "category": 'Admin Consoles',
        "description": "Opens on the TARGET's screen (not yours) using the admin credentials you entered -- cleanmgr.exe -- the classic Disk Cleanup window",
        "command": r"""
$exe   = 'cleanmgr.exe'
$argl  = ''
$label = 'Disk Cleanup (cleanmgr)'

$cs = Get-CimInstance Win32_ComputerSystem -ErrorAction SilentlyContinue
$consoleUser = $cs.UserName
if (-not $consoleUser) {
    Write-Output "  Nobody is signed in at the target's physical console (a Remote Desktop-only session does not count)."
    Write-Output "  There is no screen to open $label on -- sign in at the target, then run this again."
    return
}
Write-Output "  Console session user : $consoleUser"

$full = $exe
$gc = Get-Command $exe -ErrorAction SilentlyContinue
if ($gc -and $gc.Source) { $full = $gc.Source }
elseif (-not [IO.Path]::IsPathRooted($exe)) { $full = Join-Path $env:SystemRoot ('System32\' + $exe) }
$cmdText = if ($argl) { "$full $argl" } else { $full }
Write-Output "  Launching            : $cmdText"

if (-not ('PCAConsole' -as [type])) {
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class PCAConsole {
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct STARTUPINFO { public int cb; public string lpReserved; public string lpDesktop; public string lpTitle;
        public int dwX; public int dwY; public int dwXSize; public int dwYSize; public int dwXCountChars; public int dwYCountChars;
        public int dwFillAttribute; public int dwFlags; public short wShowWindow; public short cbReserved2;
        public IntPtr lpReserved2; public IntPtr hStdInput; public IntPtr hStdOutput; public IntPtr hStdError; }
    [StructLayout(LayoutKind.Sequential)]
    struct PROCESS_INFORMATION { public IntPtr hProcess; public IntPtr hThread; public int dwProcessId; public int dwThreadId; }
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct PROFILEINFO { public int dwSize; public int dwFlags; public string lpUserName; public string lpProfilePath;
        public string lpDefaultPath; public string lpServerName; public string lpPolicyPath; public IntPtr hProfile; }
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LogonUser(string u, string d, string p, int type, int prov, out IntPtr tok);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool DuplicateTokenEx(IntPtr h, uint acc, IntPtr attr, int lvl, int type, out IntPtr nt);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool GetTokenInformation(IntPtr t, int cls, IntPtr info, int len, out int ret);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool SetTokenInformation(IntPtr t, int cls, IntPtr info, int len);
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool CreateProcessAsUser(IntPtr tok, string app, string cmd, IntPtr pa, IntPtr ta, bool inh,
        uint flags, IntPtr env, string cwd, ref STARTUPINFO si, out PROCESS_INFORMATION pi);
    [DllImport("userenv.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LoadUserProfile(IntPtr tok, ref PROFILEINFO pi);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool CreateEnvironmentBlock(out IntPtr env, IntPtr tok, bool inh);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool DestroyEnvironmentBlock(IntPtr env);
    [DllImport("kernel32.dll")]
    static extern uint WTSGetActiveConsoleSessionId();
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern bool CloseHandle(IntPtr h);

    public static string Launch(string account, string password, string app, string args) {
        string domain = null, user = account;
        int i = account.IndexOf('\\');
        if (i > 0) { domain = account.Substring(0, i); user = account.Substring(i + 1); }
        else if (account.IndexOf('@') < 0) { domain = "."; }
        IntPtr tok = IntPtr.Zero, prim = IntPtr.Zero, env = IntPtr.Zero;
        try {
            if (!LogonUser(user, domain, password, 2, 0, out tok))
                return "LogonUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            IntPtr src = tok;
            IntPtr buf = Marshal.AllocHGlobal(IntPtr.Size);
            int ret;
            if (GetTokenInformation(tok, 19, buf, IntPtr.Size, out ret)) {
                IntPtr linked = Marshal.ReadIntPtr(buf);
                if (linked != IntPtr.Zero) src = linked;
            }
            Marshal.FreeHGlobal(buf);
            if (!DuplicateTokenEx(src, 0x02000000, IntPtr.Zero, 2, 1, out prim))
                return "DuplicateTokenEx failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            uint sess = WTSGetActiveConsoleSessionId();
            if (sess == 0xFFFFFFFF) return "no active console session";
            IntPtr p = Marshal.AllocHGlobal(4);
            Marshal.WriteInt32(p, (int)sess);
            bool okSess = SetTokenInformation(prim, 12, p, 4);
            int errSess = Marshal.GetLastWin32Error();
            Marshal.FreeHGlobal(p);
            if (!okSess) return "SetTokenInformation(session) failed (Win32 error " + errSess + ")";
            PROFILEINFO pf = new PROFILEINFO();
            pf.dwSize = Marshal.SizeOf(typeof(PROFILEINFO));
            pf.lpUserName = user;
            LoadUserProfile(prim, ref pf);
            if (!CreateEnvironmentBlock(out env, prim, false)) env = IntPtr.Zero;
            STARTUPINFO si = new STARTUPINFO();
            si.cb = Marshal.SizeOf(typeof(STARTUPINFO));
            si.lpDesktop = "winsta0\\default";
            PROCESS_INFORMATION pi;
            string cmd = "\"" + app + "\"" + (string.IsNullOrEmpty(args) ? "" : " " + args);
            string cwd = Environment.GetEnvironmentVariable("SystemRoot") + "\\System32";
            if (!CreateProcessAsUser(prim, null, cmd, IntPtr.Zero, IntPtr.Zero, false, 0x410, env, cwd, ref si, out pi))
                return "CreateProcessAsUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            CloseHandle(pi.hProcess); CloseHandle(pi.hThread);
            return "OK pid=" + pi.dwProcessId + " console-session=" + sess;
        } finally {
            if (env != IntPtr.Zero) DestroyEnvironmentBlock(env);
            if (prim != IntPtr.Zero) CloseHandle(prim);
            if (tok != IntPtr.Zero) CloseHandle(tok);
        }
    }
}
'@ -ErrorAction Stop
}

$res = 'not attempted'
try { $res = [PCAConsole]::Launch($__u, $__p, $full, $argl) } catch { $res = "exception: $($_.Exception.Message)" }
if ($res -like 'OK*') {
    Start-Sleep -Seconds 2
    $pidv = [int](($res -split 'pid=')[1] -split ' ')[0]
    if (Get-Process -Id $pidv -ErrorAction SilentlyContinue) { Write-Output "  OPENED on the target's screen as $__u  ($res)" }
    else { Write-Output "  Started as $__u ($res); the program has already handed off to another process or closed -- check the target's screen." }
    return
}
Write-Output "  Launch as the supplied admin account did not work: $res"
Write-Output "  Falling back to the account signed in at the console ($consoleUser)..."
try {
    $tn = 'PCAdminTool_UI_' + [guid]::NewGuid().ToString('N').Substring(0,8)
    if ($argl) { $a = New-ScheduledTaskAction -Execute $full -Argument $argl } else { $a = New-ScheduledTaskAction -Execute $full }
    $p = New-ScheduledTaskPrincipal -UserId $consoleUser -LogonType Interactive -RunLevel Highest
    Register-ScheduledTask -TaskName $tn -Action $a -Principal $p -Force | Out-Null
    Start-ScheduledTask -TaskName $tn
    Start-Sleep -Seconds 3
    Unregister-ScheduledTask -TaskName $tn -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "  OPENED on the target's screen as $consoleUser (fallback). It is only elevated if that account is a local administrator."
} catch { Write-Output "  Fallback failed too: $($_.Exception.Message)" }
""",
        "danger": False,
        "needs_cred": True,
        "detached": True,
        "wait_sec": 90,
    },
    {
        "id": 'rc_services',
        "label": 'Open Services Console on Target',
        "category": 'Admin Consoles',
        "description": "Opens on the TARGET's screen (not yours) using the admin credentials you entered -- services.msc",
        "command": r"""
$exe   = 'mmc.exe'
$argl  = 'services.msc'
$label = 'Services Console'

$cs = Get-CimInstance Win32_ComputerSystem -ErrorAction SilentlyContinue
$consoleUser = $cs.UserName
if (-not $consoleUser) {
    Write-Output "  Nobody is signed in at the target's physical console (a Remote Desktop-only session does not count)."
    Write-Output "  There is no screen to open $label on -- sign in at the target, then run this again."
    return
}
Write-Output "  Console session user : $consoleUser"

$full = $exe
$gc = Get-Command $exe -ErrorAction SilentlyContinue
if ($gc -and $gc.Source) { $full = $gc.Source }
elseif (-not [IO.Path]::IsPathRooted($exe)) { $full = Join-Path $env:SystemRoot ('System32\' + $exe) }
$cmdText = if ($argl) { "$full $argl" } else { $full }
Write-Output "  Launching            : $cmdText"

if (-not ('PCAConsole' -as [type])) {
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class PCAConsole {
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct STARTUPINFO { public int cb; public string lpReserved; public string lpDesktop; public string lpTitle;
        public int dwX; public int dwY; public int dwXSize; public int dwYSize; public int dwXCountChars; public int dwYCountChars;
        public int dwFillAttribute; public int dwFlags; public short wShowWindow; public short cbReserved2;
        public IntPtr lpReserved2; public IntPtr hStdInput; public IntPtr hStdOutput; public IntPtr hStdError; }
    [StructLayout(LayoutKind.Sequential)]
    struct PROCESS_INFORMATION { public IntPtr hProcess; public IntPtr hThread; public int dwProcessId; public int dwThreadId; }
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct PROFILEINFO { public int dwSize; public int dwFlags; public string lpUserName; public string lpProfilePath;
        public string lpDefaultPath; public string lpServerName; public string lpPolicyPath; public IntPtr hProfile; }
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LogonUser(string u, string d, string p, int type, int prov, out IntPtr tok);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool DuplicateTokenEx(IntPtr h, uint acc, IntPtr attr, int lvl, int type, out IntPtr nt);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool GetTokenInformation(IntPtr t, int cls, IntPtr info, int len, out int ret);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool SetTokenInformation(IntPtr t, int cls, IntPtr info, int len);
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool CreateProcessAsUser(IntPtr tok, string app, string cmd, IntPtr pa, IntPtr ta, bool inh,
        uint flags, IntPtr env, string cwd, ref STARTUPINFO si, out PROCESS_INFORMATION pi);
    [DllImport("userenv.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LoadUserProfile(IntPtr tok, ref PROFILEINFO pi);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool CreateEnvironmentBlock(out IntPtr env, IntPtr tok, bool inh);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool DestroyEnvironmentBlock(IntPtr env);
    [DllImport("kernel32.dll")]
    static extern uint WTSGetActiveConsoleSessionId();
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern bool CloseHandle(IntPtr h);

    public static string Launch(string account, string password, string app, string args) {
        string domain = null, user = account;
        int i = account.IndexOf('\\');
        if (i > 0) { domain = account.Substring(0, i); user = account.Substring(i + 1); }
        else if (account.IndexOf('@') < 0) { domain = "."; }
        IntPtr tok = IntPtr.Zero, prim = IntPtr.Zero, env = IntPtr.Zero;
        try {
            if (!LogonUser(user, domain, password, 2, 0, out tok))
                return "LogonUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            IntPtr src = tok;
            IntPtr buf = Marshal.AllocHGlobal(IntPtr.Size);
            int ret;
            if (GetTokenInformation(tok, 19, buf, IntPtr.Size, out ret)) {
                IntPtr linked = Marshal.ReadIntPtr(buf);
                if (linked != IntPtr.Zero) src = linked;
            }
            Marshal.FreeHGlobal(buf);
            if (!DuplicateTokenEx(src, 0x02000000, IntPtr.Zero, 2, 1, out prim))
                return "DuplicateTokenEx failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            uint sess = WTSGetActiveConsoleSessionId();
            if (sess == 0xFFFFFFFF) return "no active console session";
            IntPtr p = Marshal.AllocHGlobal(4);
            Marshal.WriteInt32(p, (int)sess);
            bool okSess = SetTokenInformation(prim, 12, p, 4);
            int errSess = Marshal.GetLastWin32Error();
            Marshal.FreeHGlobal(p);
            if (!okSess) return "SetTokenInformation(session) failed (Win32 error " + errSess + ")";
            PROFILEINFO pf = new PROFILEINFO();
            pf.dwSize = Marshal.SizeOf(typeof(PROFILEINFO));
            pf.lpUserName = user;
            LoadUserProfile(prim, ref pf);
            if (!CreateEnvironmentBlock(out env, prim, false)) env = IntPtr.Zero;
            STARTUPINFO si = new STARTUPINFO();
            si.cb = Marshal.SizeOf(typeof(STARTUPINFO));
            si.lpDesktop = "winsta0\\default";
            PROCESS_INFORMATION pi;
            string cmd = "\"" + app + "\"" + (string.IsNullOrEmpty(args) ? "" : " " + args);
            string cwd = Environment.GetEnvironmentVariable("SystemRoot") + "\\System32";
            if (!CreateProcessAsUser(prim, null, cmd, IntPtr.Zero, IntPtr.Zero, false, 0x410, env, cwd, ref si, out pi))
                return "CreateProcessAsUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            CloseHandle(pi.hProcess); CloseHandle(pi.hThread);
            return "OK pid=" + pi.dwProcessId + " console-session=" + sess;
        } finally {
            if (env != IntPtr.Zero) DestroyEnvironmentBlock(env);
            if (prim != IntPtr.Zero) CloseHandle(prim);
            if (tok != IntPtr.Zero) CloseHandle(tok);
        }
    }
}
'@ -ErrorAction Stop
}

$res = 'not attempted'
try { $res = [PCAConsole]::Launch($__u, $__p, $full, $argl) } catch { $res = "exception: $($_.Exception.Message)" }
if ($res -like 'OK*') {
    Start-Sleep -Seconds 2
    $pidv = [int](($res -split 'pid=')[1] -split ' ')[0]
    if (Get-Process -Id $pidv -ErrorAction SilentlyContinue) { Write-Output "  OPENED on the target's screen as $__u  ($res)" }
    else { Write-Output "  Started as $__u ($res); the program has already handed off to another process or closed -- check the target's screen." }
    return
}
Write-Output "  Launch as the supplied admin account did not work: $res"
Write-Output "  Falling back to the account signed in at the console ($consoleUser)..."
try {
    $tn = 'PCAdminTool_UI_' + [guid]::NewGuid().ToString('N').Substring(0,8)
    if ($argl) { $a = New-ScheduledTaskAction -Execute $full -Argument $argl } else { $a = New-ScheduledTaskAction -Execute $full }
    $p = New-ScheduledTaskPrincipal -UserId $consoleUser -LogonType Interactive -RunLevel Highest
    Register-ScheduledTask -TaskName $tn -Action $a -Principal $p -Force | Out-Null
    Start-ScheduledTask -TaskName $tn
    Start-Sleep -Seconds 3
    Unregister-ScheduledTask -TaskName $tn -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "  OPENED on the target's screen as $consoleUser (fallback). It is only elevated if that account is a local administrator."
} catch { Write-Output "  Fallback failed too: $($_.Exception.Message)" }
""",
        "danger": False,
        "needs_cred": True,
        "detached": True,
        "wait_sec": 90,
    },
    {
        "id": 'rc_event_viewer',
        "label": 'Open Event Viewer on Target',
        "category": 'Admin Consoles',
        "description": "Opens on the TARGET's screen (not yours) using the admin credentials you entered -- eventvwr.msc",
        "command": r"""
$exe   = 'mmc.exe'
$argl  = 'eventvwr.msc'
$label = 'Event Viewer'

$cs = Get-CimInstance Win32_ComputerSystem -ErrorAction SilentlyContinue
$consoleUser = $cs.UserName
if (-not $consoleUser) {
    Write-Output "  Nobody is signed in at the target's physical console (a Remote Desktop-only session does not count)."
    Write-Output "  There is no screen to open $label on -- sign in at the target, then run this again."
    return
}
Write-Output "  Console session user : $consoleUser"

$full = $exe
$gc = Get-Command $exe -ErrorAction SilentlyContinue
if ($gc -and $gc.Source) { $full = $gc.Source }
elseif (-not [IO.Path]::IsPathRooted($exe)) { $full = Join-Path $env:SystemRoot ('System32\' + $exe) }
$cmdText = if ($argl) { "$full $argl" } else { $full }
Write-Output "  Launching            : $cmdText"

if (-not ('PCAConsole' -as [type])) {
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class PCAConsole {
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct STARTUPINFO { public int cb; public string lpReserved; public string lpDesktop; public string lpTitle;
        public int dwX; public int dwY; public int dwXSize; public int dwYSize; public int dwXCountChars; public int dwYCountChars;
        public int dwFillAttribute; public int dwFlags; public short wShowWindow; public short cbReserved2;
        public IntPtr lpReserved2; public IntPtr hStdInput; public IntPtr hStdOutput; public IntPtr hStdError; }
    [StructLayout(LayoutKind.Sequential)]
    struct PROCESS_INFORMATION { public IntPtr hProcess; public IntPtr hThread; public int dwProcessId; public int dwThreadId; }
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct PROFILEINFO { public int dwSize; public int dwFlags; public string lpUserName; public string lpProfilePath;
        public string lpDefaultPath; public string lpServerName; public string lpPolicyPath; public IntPtr hProfile; }
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LogonUser(string u, string d, string p, int type, int prov, out IntPtr tok);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool DuplicateTokenEx(IntPtr h, uint acc, IntPtr attr, int lvl, int type, out IntPtr nt);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool GetTokenInformation(IntPtr t, int cls, IntPtr info, int len, out int ret);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool SetTokenInformation(IntPtr t, int cls, IntPtr info, int len);
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool CreateProcessAsUser(IntPtr tok, string app, string cmd, IntPtr pa, IntPtr ta, bool inh,
        uint flags, IntPtr env, string cwd, ref STARTUPINFO si, out PROCESS_INFORMATION pi);
    [DllImport("userenv.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LoadUserProfile(IntPtr tok, ref PROFILEINFO pi);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool CreateEnvironmentBlock(out IntPtr env, IntPtr tok, bool inh);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool DestroyEnvironmentBlock(IntPtr env);
    [DllImport("kernel32.dll")]
    static extern uint WTSGetActiveConsoleSessionId();
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern bool CloseHandle(IntPtr h);

    public static string Launch(string account, string password, string app, string args) {
        string domain = null, user = account;
        int i = account.IndexOf('\\');
        if (i > 0) { domain = account.Substring(0, i); user = account.Substring(i + 1); }
        else if (account.IndexOf('@') < 0) { domain = "."; }
        IntPtr tok = IntPtr.Zero, prim = IntPtr.Zero, env = IntPtr.Zero;
        try {
            if (!LogonUser(user, domain, password, 2, 0, out tok))
                return "LogonUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            IntPtr src = tok;
            IntPtr buf = Marshal.AllocHGlobal(IntPtr.Size);
            int ret;
            if (GetTokenInformation(tok, 19, buf, IntPtr.Size, out ret)) {
                IntPtr linked = Marshal.ReadIntPtr(buf);
                if (linked != IntPtr.Zero) src = linked;
            }
            Marshal.FreeHGlobal(buf);
            if (!DuplicateTokenEx(src, 0x02000000, IntPtr.Zero, 2, 1, out prim))
                return "DuplicateTokenEx failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            uint sess = WTSGetActiveConsoleSessionId();
            if (sess == 0xFFFFFFFF) return "no active console session";
            IntPtr p = Marshal.AllocHGlobal(4);
            Marshal.WriteInt32(p, (int)sess);
            bool okSess = SetTokenInformation(prim, 12, p, 4);
            int errSess = Marshal.GetLastWin32Error();
            Marshal.FreeHGlobal(p);
            if (!okSess) return "SetTokenInformation(session) failed (Win32 error " + errSess + ")";
            PROFILEINFO pf = new PROFILEINFO();
            pf.dwSize = Marshal.SizeOf(typeof(PROFILEINFO));
            pf.lpUserName = user;
            LoadUserProfile(prim, ref pf);
            if (!CreateEnvironmentBlock(out env, prim, false)) env = IntPtr.Zero;
            STARTUPINFO si = new STARTUPINFO();
            si.cb = Marshal.SizeOf(typeof(STARTUPINFO));
            si.lpDesktop = "winsta0\\default";
            PROCESS_INFORMATION pi;
            string cmd = "\"" + app + "\"" + (string.IsNullOrEmpty(args) ? "" : " " + args);
            string cwd = Environment.GetEnvironmentVariable("SystemRoot") + "\\System32";
            if (!CreateProcessAsUser(prim, null, cmd, IntPtr.Zero, IntPtr.Zero, false, 0x410, env, cwd, ref si, out pi))
                return "CreateProcessAsUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            CloseHandle(pi.hProcess); CloseHandle(pi.hThread);
            return "OK pid=" + pi.dwProcessId + " console-session=" + sess;
        } finally {
            if (env != IntPtr.Zero) DestroyEnvironmentBlock(env);
            if (prim != IntPtr.Zero) CloseHandle(prim);
            if (tok != IntPtr.Zero) CloseHandle(tok);
        }
    }
}
'@ -ErrorAction Stop
}

$res = 'not attempted'
try { $res = [PCAConsole]::Launch($__u, $__p, $full, $argl) } catch { $res = "exception: $($_.Exception.Message)" }
if ($res -like 'OK*') {
    Start-Sleep -Seconds 2
    $pidv = [int](($res -split 'pid=')[1] -split ' ')[0]
    if (Get-Process -Id $pidv -ErrorAction SilentlyContinue) { Write-Output "  OPENED on the target's screen as $__u  ($res)" }
    else { Write-Output "  Started as $__u ($res); the program has already handed off to another process or closed -- check the target's screen." }
    return
}
Write-Output "  Launch as the supplied admin account did not work: $res"
Write-Output "  Falling back to the account signed in at the console ($consoleUser)..."
try {
    $tn = 'PCAdminTool_UI_' + [guid]::NewGuid().ToString('N').Substring(0,8)
    if ($argl) { $a = New-ScheduledTaskAction -Execute $full -Argument $argl } else { $a = New-ScheduledTaskAction -Execute $full }
    $p = New-ScheduledTaskPrincipal -UserId $consoleUser -LogonType Interactive -RunLevel Highest
    Register-ScheduledTask -TaskName $tn -Action $a -Principal $p -Force | Out-Null
    Start-ScheduledTask -TaskName $tn
    Start-Sleep -Seconds 3
    Unregister-ScheduledTask -TaskName $tn -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "  OPENED on the target's screen as $consoleUser (fallback). It is only elevated if that account is a local administrator."
} catch { Write-Output "  Fallback failed too: $($_.Exception.Message)" }
""",
        "danger": False,
        "needs_cred": True,
        "detached": True,
        "wait_sec": 90,
    },
    {
        "id": 'rc_task_scheduler',
        "label": 'Open Task Scheduler on Target',
        "category": 'Admin Consoles',
        "description": "Opens on the TARGET's screen (not yours) using the admin credentials you entered -- taskschd.msc",
        "command": r"""
$exe   = 'mmc.exe'
$argl  = 'taskschd.msc'
$label = 'Task Scheduler'

$cs = Get-CimInstance Win32_ComputerSystem -ErrorAction SilentlyContinue
$consoleUser = $cs.UserName
if (-not $consoleUser) {
    Write-Output "  Nobody is signed in at the target's physical console (a Remote Desktop-only session does not count)."
    Write-Output "  There is no screen to open $label on -- sign in at the target, then run this again."
    return
}
Write-Output "  Console session user : $consoleUser"

$full = $exe
$gc = Get-Command $exe -ErrorAction SilentlyContinue
if ($gc -and $gc.Source) { $full = $gc.Source }
elseif (-not [IO.Path]::IsPathRooted($exe)) { $full = Join-Path $env:SystemRoot ('System32\' + $exe) }
$cmdText = if ($argl) { "$full $argl" } else { $full }
Write-Output "  Launching            : $cmdText"

if (-not ('PCAConsole' -as [type])) {
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class PCAConsole {
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct STARTUPINFO { public int cb; public string lpReserved; public string lpDesktop; public string lpTitle;
        public int dwX; public int dwY; public int dwXSize; public int dwYSize; public int dwXCountChars; public int dwYCountChars;
        public int dwFillAttribute; public int dwFlags; public short wShowWindow; public short cbReserved2;
        public IntPtr lpReserved2; public IntPtr hStdInput; public IntPtr hStdOutput; public IntPtr hStdError; }
    [StructLayout(LayoutKind.Sequential)]
    struct PROCESS_INFORMATION { public IntPtr hProcess; public IntPtr hThread; public int dwProcessId; public int dwThreadId; }
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct PROFILEINFO { public int dwSize; public int dwFlags; public string lpUserName; public string lpProfilePath;
        public string lpDefaultPath; public string lpServerName; public string lpPolicyPath; public IntPtr hProfile; }
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LogonUser(string u, string d, string p, int type, int prov, out IntPtr tok);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool DuplicateTokenEx(IntPtr h, uint acc, IntPtr attr, int lvl, int type, out IntPtr nt);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool GetTokenInformation(IntPtr t, int cls, IntPtr info, int len, out int ret);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool SetTokenInformation(IntPtr t, int cls, IntPtr info, int len);
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool CreateProcessAsUser(IntPtr tok, string app, string cmd, IntPtr pa, IntPtr ta, bool inh,
        uint flags, IntPtr env, string cwd, ref STARTUPINFO si, out PROCESS_INFORMATION pi);
    [DllImport("userenv.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LoadUserProfile(IntPtr tok, ref PROFILEINFO pi);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool CreateEnvironmentBlock(out IntPtr env, IntPtr tok, bool inh);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool DestroyEnvironmentBlock(IntPtr env);
    [DllImport("kernel32.dll")]
    static extern uint WTSGetActiveConsoleSessionId();
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern bool CloseHandle(IntPtr h);

    public static string Launch(string account, string password, string app, string args) {
        string domain = null, user = account;
        int i = account.IndexOf('\\');
        if (i > 0) { domain = account.Substring(0, i); user = account.Substring(i + 1); }
        else if (account.IndexOf('@') < 0) { domain = "."; }
        IntPtr tok = IntPtr.Zero, prim = IntPtr.Zero, env = IntPtr.Zero;
        try {
            if (!LogonUser(user, domain, password, 2, 0, out tok))
                return "LogonUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            IntPtr src = tok;
            IntPtr buf = Marshal.AllocHGlobal(IntPtr.Size);
            int ret;
            if (GetTokenInformation(tok, 19, buf, IntPtr.Size, out ret)) {
                IntPtr linked = Marshal.ReadIntPtr(buf);
                if (linked != IntPtr.Zero) src = linked;
            }
            Marshal.FreeHGlobal(buf);
            if (!DuplicateTokenEx(src, 0x02000000, IntPtr.Zero, 2, 1, out prim))
                return "DuplicateTokenEx failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            uint sess = WTSGetActiveConsoleSessionId();
            if (sess == 0xFFFFFFFF) return "no active console session";
            IntPtr p = Marshal.AllocHGlobal(4);
            Marshal.WriteInt32(p, (int)sess);
            bool okSess = SetTokenInformation(prim, 12, p, 4);
            int errSess = Marshal.GetLastWin32Error();
            Marshal.FreeHGlobal(p);
            if (!okSess) return "SetTokenInformation(session) failed (Win32 error " + errSess + ")";
            PROFILEINFO pf = new PROFILEINFO();
            pf.dwSize = Marshal.SizeOf(typeof(PROFILEINFO));
            pf.lpUserName = user;
            LoadUserProfile(prim, ref pf);
            if (!CreateEnvironmentBlock(out env, prim, false)) env = IntPtr.Zero;
            STARTUPINFO si = new STARTUPINFO();
            si.cb = Marshal.SizeOf(typeof(STARTUPINFO));
            si.lpDesktop = "winsta0\\default";
            PROCESS_INFORMATION pi;
            string cmd = "\"" + app + "\"" + (string.IsNullOrEmpty(args) ? "" : " " + args);
            string cwd = Environment.GetEnvironmentVariable("SystemRoot") + "\\System32";
            if (!CreateProcessAsUser(prim, null, cmd, IntPtr.Zero, IntPtr.Zero, false, 0x410, env, cwd, ref si, out pi))
                return "CreateProcessAsUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            CloseHandle(pi.hProcess); CloseHandle(pi.hThread);
            return "OK pid=" + pi.dwProcessId + " console-session=" + sess;
        } finally {
            if (env != IntPtr.Zero) DestroyEnvironmentBlock(env);
            if (prim != IntPtr.Zero) CloseHandle(prim);
            if (tok != IntPtr.Zero) CloseHandle(tok);
        }
    }
}
'@ -ErrorAction Stop
}

$res = 'not attempted'
try { $res = [PCAConsole]::Launch($__u, $__p, $full, $argl) } catch { $res = "exception: $($_.Exception.Message)" }
if ($res -like 'OK*') {
    Start-Sleep -Seconds 2
    $pidv = [int](($res -split 'pid=')[1] -split ' ')[0]
    if (Get-Process -Id $pidv -ErrorAction SilentlyContinue) { Write-Output "  OPENED on the target's screen as $__u  ($res)" }
    else { Write-Output "  Started as $__u ($res); the program has already handed off to another process or closed -- check the target's screen." }
    return
}
Write-Output "  Launch as the supplied admin account did not work: $res"
Write-Output "  Falling back to the account signed in at the console ($consoleUser)..."
try {
    $tn = 'PCAdminTool_UI_' + [guid]::NewGuid().ToString('N').Substring(0,8)
    if ($argl) { $a = New-ScheduledTaskAction -Execute $full -Argument $argl } else { $a = New-ScheduledTaskAction -Execute $full }
    $p = New-ScheduledTaskPrincipal -UserId $consoleUser -LogonType Interactive -RunLevel Highest
    Register-ScheduledTask -TaskName $tn -Action $a -Principal $p -Force | Out-Null
    Start-ScheduledTask -TaskName $tn
    Start-Sleep -Seconds 3
    Unregister-ScheduledTask -TaskName $tn -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "  OPENED on the target's screen as $consoleUser (fallback). It is only elevated if that account is a local administrator."
} catch { Write-Output "  Fallback failed too: $($_.Exception.Message)" }
""",
        "danger": False,
        "needs_cred": True,
        "detached": True,
        "wait_sec": 90,
    },
    {
        "id": 'rc_local_users',
        "label": 'Open Local Users and Groups on Target',
        "category": 'Admin Consoles',
        "description": "Opens on the TARGET's screen (not yours) using the admin credentials you entered -- lusrmgr.msc (not on Home editions)",
        "command": r"""
$exe   = 'mmc.exe'
$argl  = 'lusrmgr.msc'
$label = 'Local Users and Groups'

$cs = Get-CimInstance Win32_ComputerSystem -ErrorAction SilentlyContinue
$consoleUser = $cs.UserName
if (-not $consoleUser) {
    Write-Output "  Nobody is signed in at the target's physical console (a Remote Desktop-only session does not count)."
    Write-Output "  There is no screen to open $label on -- sign in at the target, then run this again."
    return
}
Write-Output "  Console session user : $consoleUser"

$full = $exe
$gc = Get-Command $exe -ErrorAction SilentlyContinue
if ($gc -and $gc.Source) { $full = $gc.Source }
elseif (-not [IO.Path]::IsPathRooted($exe)) { $full = Join-Path $env:SystemRoot ('System32\' + $exe) }
$cmdText = if ($argl) { "$full $argl" } else { $full }
Write-Output "  Launching            : $cmdText"

if (-not ('PCAConsole' -as [type])) {
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class PCAConsole {
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct STARTUPINFO { public int cb; public string lpReserved; public string lpDesktop; public string lpTitle;
        public int dwX; public int dwY; public int dwXSize; public int dwYSize; public int dwXCountChars; public int dwYCountChars;
        public int dwFillAttribute; public int dwFlags; public short wShowWindow; public short cbReserved2;
        public IntPtr lpReserved2; public IntPtr hStdInput; public IntPtr hStdOutput; public IntPtr hStdError; }
    [StructLayout(LayoutKind.Sequential)]
    struct PROCESS_INFORMATION { public IntPtr hProcess; public IntPtr hThread; public int dwProcessId; public int dwThreadId; }
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct PROFILEINFO { public int dwSize; public int dwFlags; public string lpUserName; public string lpProfilePath;
        public string lpDefaultPath; public string lpServerName; public string lpPolicyPath; public IntPtr hProfile; }
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LogonUser(string u, string d, string p, int type, int prov, out IntPtr tok);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool DuplicateTokenEx(IntPtr h, uint acc, IntPtr attr, int lvl, int type, out IntPtr nt);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool GetTokenInformation(IntPtr t, int cls, IntPtr info, int len, out int ret);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool SetTokenInformation(IntPtr t, int cls, IntPtr info, int len);
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool CreateProcessAsUser(IntPtr tok, string app, string cmd, IntPtr pa, IntPtr ta, bool inh,
        uint flags, IntPtr env, string cwd, ref STARTUPINFO si, out PROCESS_INFORMATION pi);
    [DllImport("userenv.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LoadUserProfile(IntPtr tok, ref PROFILEINFO pi);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool CreateEnvironmentBlock(out IntPtr env, IntPtr tok, bool inh);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool DestroyEnvironmentBlock(IntPtr env);
    [DllImport("kernel32.dll")]
    static extern uint WTSGetActiveConsoleSessionId();
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern bool CloseHandle(IntPtr h);

    public static string Launch(string account, string password, string app, string args) {
        string domain = null, user = account;
        int i = account.IndexOf('\\');
        if (i > 0) { domain = account.Substring(0, i); user = account.Substring(i + 1); }
        else if (account.IndexOf('@') < 0) { domain = "."; }
        IntPtr tok = IntPtr.Zero, prim = IntPtr.Zero, env = IntPtr.Zero;
        try {
            if (!LogonUser(user, domain, password, 2, 0, out tok))
                return "LogonUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            IntPtr src = tok;
            IntPtr buf = Marshal.AllocHGlobal(IntPtr.Size);
            int ret;
            if (GetTokenInformation(tok, 19, buf, IntPtr.Size, out ret)) {
                IntPtr linked = Marshal.ReadIntPtr(buf);
                if (linked != IntPtr.Zero) src = linked;
            }
            Marshal.FreeHGlobal(buf);
            if (!DuplicateTokenEx(src, 0x02000000, IntPtr.Zero, 2, 1, out prim))
                return "DuplicateTokenEx failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            uint sess = WTSGetActiveConsoleSessionId();
            if (sess == 0xFFFFFFFF) return "no active console session";
            IntPtr p = Marshal.AllocHGlobal(4);
            Marshal.WriteInt32(p, (int)sess);
            bool okSess = SetTokenInformation(prim, 12, p, 4);
            int errSess = Marshal.GetLastWin32Error();
            Marshal.FreeHGlobal(p);
            if (!okSess) return "SetTokenInformation(session) failed (Win32 error " + errSess + ")";
            PROFILEINFO pf = new PROFILEINFO();
            pf.dwSize = Marshal.SizeOf(typeof(PROFILEINFO));
            pf.lpUserName = user;
            LoadUserProfile(prim, ref pf);
            if (!CreateEnvironmentBlock(out env, prim, false)) env = IntPtr.Zero;
            STARTUPINFO si = new STARTUPINFO();
            si.cb = Marshal.SizeOf(typeof(STARTUPINFO));
            si.lpDesktop = "winsta0\\default";
            PROCESS_INFORMATION pi;
            string cmd = "\"" + app + "\"" + (string.IsNullOrEmpty(args) ? "" : " " + args);
            string cwd = Environment.GetEnvironmentVariable("SystemRoot") + "\\System32";
            if (!CreateProcessAsUser(prim, null, cmd, IntPtr.Zero, IntPtr.Zero, false, 0x410, env, cwd, ref si, out pi))
                return "CreateProcessAsUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            CloseHandle(pi.hProcess); CloseHandle(pi.hThread);
            return "OK pid=" + pi.dwProcessId + " console-session=" + sess;
        } finally {
            if (env != IntPtr.Zero) DestroyEnvironmentBlock(env);
            if (prim != IntPtr.Zero) CloseHandle(prim);
            if (tok != IntPtr.Zero) CloseHandle(tok);
        }
    }
}
'@ -ErrorAction Stop
}

$res = 'not attempted'
try { $res = [PCAConsole]::Launch($__u, $__p, $full, $argl) } catch { $res = "exception: $($_.Exception.Message)" }
if ($res -like 'OK*') {
    Start-Sleep -Seconds 2
    $pidv = [int](($res -split 'pid=')[1] -split ' ')[0]
    if (Get-Process -Id $pidv -ErrorAction SilentlyContinue) { Write-Output "  OPENED on the target's screen as $__u  ($res)" }
    else { Write-Output "  Started as $__u ($res); the program has already handed off to another process or closed -- check the target's screen." }
    return
}
Write-Output "  Launch as the supplied admin account did not work: $res"
Write-Output "  Falling back to the account signed in at the console ($consoleUser)..."
try {
    $tn = 'PCAdminTool_UI_' + [guid]::NewGuid().ToString('N').Substring(0,8)
    if ($argl) { $a = New-ScheduledTaskAction -Execute $full -Argument $argl } else { $a = New-ScheduledTaskAction -Execute $full }
    $p = New-ScheduledTaskPrincipal -UserId $consoleUser -LogonType Interactive -RunLevel Highest
    Register-ScheduledTask -TaskName $tn -Action $a -Principal $p -Force | Out-Null
    Start-ScheduledTask -TaskName $tn
    Start-Sleep -Seconds 3
    Unregister-ScheduledTask -TaskName $tn -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "  OPENED on the target's screen as $consoleUser (fallback). It is only elevated if that account is a local administrator."
} catch { Write-Output "  Fallback failed too: $($_.Exception.Message)" }
""",
        "danger": False,
        "needs_cred": True,
        "detached": True,
        "wait_sec": 90,
    },
    {
        "id": 'rc_shared_folders',
        "label": 'Open Shared Folders on Target',
        "category": 'Admin Consoles',
        "description": "Opens on the TARGET's screen (not yours) using the admin credentials you entered -- fsmgmt.msc -- shares, sessions, open files",
        "command": r"""
$exe   = 'mmc.exe'
$argl  = 'fsmgmt.msc'
$label = 'Shared Folders'

$cs = Get-CimInstance Win32_ComputerSystem -ErrorAction SilentlyContinue
$consoleUser = $cs.UserName
if (-not $consoleUser) {
    Write-Output "  Nobody is signed in at the target's physical console (a Remote Desktop-only session does not count)."
    Write-Output "  There is no screen to open $label on -- sign in at the target, then run this again."
    return
}
Write-Output "  Console session user : $consoleUser"

$full = $exe
$gc = Get-Command $exe -ErrorAction SilentlyContinue
if ($gc -and $gc.Source) { $full = $gc.Source }
elseif (-not [IO.Path]::IsPathRooted($exe)) { $full = Join-Path $env:SystemRoot ('System32\' + $exe) }
$cmdText = if ($argl) { "$full $argl" } else { $full }
Write-Output "  Launching            : $cmdText"

if (-not ('PCAConsole' -as [type])) {
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class PCAConsole {
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct STARTUPINFO { public int cb; public string lpReserved; public string lpDesktop; public string lpTitle;
        public int dwX; public int dwY; public int dwXSize; public int dwYSize; public int dwXCountChars; public int dwYCountChars;
        public int dwFillAttribute; public int dwFlags; public short wShowWindow; public short cbReserved2;
        public IntPtr lpReserved2; public IntPtr hStdInput; public IntPtr hStdOutput; public IntPtr hStdError; }
    [StructLayout(LayoutKind.Sequential)]
    struct PROCESS_INFORMATION { public IntPtr hProcess; public IntPtr hThread; public int dwProcessId; public int dwThreadId; }
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct PROFILEINFO { public int dwSize; public int dwFlags; public string lpUserName; public string lpProfilePath;
        public string lpDefaultPath; public string lpServerName; public string lpPolicyPath; public IntPtr hProfile; }
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LogonUser(string u, string d, string p, int type, int prov, out IntPtr tok);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool DuplicateTokenEx(IntPtr h, uint acc, IntPtr attr, int lvl, int type, out IntPtr nt);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool GetTokenInformation(IntPtr t, int cls, IntPtr info, int len, out int ret);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool SetTokenInformation(IntPtr t, int cls, IntPtr info, int len);
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool CreateProcessAsUser(IntPtr tok, string app, string cmd, IntPtr pa, IntPtr ta, bool inh,
        uint flags, IntPtr env, string cwd, ref STARTUPINFO si, out PROCESS_INFORMATION pi);
    [DllImport("userenv.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LoadUserProfile(IntPtr tok, ref PROFILEINFO pi);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool CreateEnvironmentBlock(out IntPtr env, IntPtr tok, bool inh);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool DestroyEnvironmentBlock(IntPtr env);
    [DllImport("kernel32.dll")]
    static extern uint WTSGetActiveConsoleSessionId();
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern bool CloseHandle(IntPtr h);

    public static string Launch(string account, string password, string app, string args) {
        string domain = null, user = account;
        int i = account.IndexOf('\\');
        if (i > 0) { domain = account.Substring(0, i); user = account.Substring(i + 1); }
        else if (account.IndexOf('@') < 0) { domain = "."; }
        IntPtr tok = IntPtr.Zero, prim = IntPtr.Zero, env = IntPtr.Zero;
        try {
            if (!LogonUser(user, domain, password, 2, 0, out tok))
                return "LogonUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            IntPtr src = tok;
            IntPtr buf = Marshal.AllocHGlobal(IntPtr.Size);
            int ret;
            if (GetTokenInformation(tok, 19, buf, IntPtr.Size, out ret)) {
                IntPtr linked = Marshal.ReadIntPtr(buf);
                if (linked != IntPtr.Zero) src = linked;
            }
            Marshal.FreeHGlobal(buf);
            if (!DuplicateTokenEx(src, 0x02000000, IntPtr.Zero, 2, 1, out prim))
                return "DuplicateTokenEx failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            uint sess = WTSGetActiveConsoleSessionId();
            if (sess == 0xFFFFFFFF) return "no active console session";
            IntPtr p = Marshal.AllocHGlobal(4);
            Marshal.WriteInt32(p, (int)sess);
            bool okSess = SetTokenInformation(prim, 12, p, 4);
            int errSess = Marshal.GetLastWin32Error();
            Marshal.FreeHGlobal(p);
            if (!okSess) return "SetTokenInformation(session) failed (Win32 error " + errSess + ")";
            PROFILEINFO pf = new PROFILEINFO();
            pf.dwSize = Marshal.SizeOf(typeof(PROFILEINFO));
            pf.lpUserName = user;
            LoadUserProfile(prim, ref pf);
            if (!CreateEnvironmentBlock(out env, prim, false)) env = IntPtr.Zero;
            STARTUPINFO si = new STARTUPINFO();
            si.cb = Marshal.SizeOf(typeof(STARTUPINFO));
            si.lpDesktop = "winsta0\\default";
            PROCESS_INFORMATION pi;
            string cmd = "\"" + app + "\"" + (string.IsNullOrEmpty(args) ? "" : " " + args);
            string cwd = Environment.GetEnvironmentVariable("SystemRoot") + "\\System32";
            if (!CreateProcessAsUser(prim, null, cmd, IntPtr.Zero, IntPtr.Zero, false, 0x410, env, cwd, ref si, out pi))
                return "CreateProcessAsUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            CloseHandle(pi.hProcess); CloseHandle(pi.hThread);
            return "OK pid=" + pi.dwProcessId + " console-session=" + sess;
        } finally {
            if (env != IntPtr.Zero) DestroyEnvironmentBlock(env);
            if (prim != IntPtr.Zero) CloseHandle(prim);
            if (tok != IntPtr.Zero) CloseHandle(tok);
        }
    }
}
'@ -ErrorAction Stop
}

$res = 'not attempted'
try { $res = [PCAConsole]::Launch($__u, $__p, $full, $argl) } catch { $res = "exception: $($_.Exception.Message)" }
if ($res -like 'OK*') {
    Start-Sleep -Seconds 2
    $pidv = [int](($res -split 'pid=')[1] -split ' ')[0]
    if (Get-Process -Id $pidv -ErrorAction SilentlyContinue) { Write-Output "  OPENED on the target's screen as $__u  ($res)" }
    else { Write-Output "  Started as $__u ($res); the program has already handed off to another process or closed -- check the target's screen." }
    return
}
Write-Output "  Launch as the supplied admin account did not work: $res"
Write-Output "  Falling back to the account signed in at the console ($consoleUser)..."
try {
    $tn = 'PCAdminTool_UI_' + [guid]::NewGuid().ToString('N').Substring(0,8)
    if ($argl) { $a = New-ScheduledTaskAction -Execute $full -Argument $argl } else { $a = New-ScheduledTaskAction -Execute $full }
    $p = New-ScheduledTaskPrincipal -UserId $consoleUser -LogonType Interactive -RunLevel Highest
    Register-ScheduledTask -TaskName $tn -Action $a -Principal $p -Force | Out-Null
    Start-ScheduledTask -TaskName $tn
    Start-Sleep -Seconds 3
    Unregister-ScheduledTask -TaskName $tn -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "  OPENED on the target's screen as $consoleUser (fallback). It is only elevated if that account is a local administrator."
} catch { Write-Output "  Fallback failed too: $($_.Exception.Message)" }
""",
        "danger": False,
        "needs_cred": True,
        "detached": True,
        "wait_sec": 90,
    },
    {
        "id": 'rc_firewall_adv',
        "label": 'Open Windows Defender Firewall with Advanced Security on Target',
        "category": 'Admin Consoles',
        "description": "Opens on the TARGET's screen (not yours) using the admin credentials you entered -- wf.msc -- inbound/outbound rules",
        "command": r"""
$exe   = 'mmc.exe'
$argl  = 'wf.msc'
$label = 'Windows Defender Firewall with Advanced Security'

$cs = Get-CimInstance Win32_ComputerSystem -ErrorAction SilentlyContinue
$consoleUser = $cs.UserName
if (-not $consoleUser) {
    Write-Output "  Nobody is signed in at the target's physical console (a Remote Desktop-only session does not count)."
    Write-Output "  There is no screen to open $label on -- sign in at the target, then run this again."
    return
}
Write-Output "  Console session user : $consoleUser"

$full = $exe
$gc = Get-Command $exe -ErrorAction SilentlyContinue
if ($gc -and $gc.Source) { $full = $gc.Source }
elseif (-not [IO.Path]::IsPathRooted($exe)) { $full = Join-Path $env:SystemRoot ('System32\' + $exe) }
$cmdText = if ($argl) { "$full $argl" } else { $full }
Write-Output "  Launching            : $cmdText"

if (-not ('PCAConsole' -as [type])) {
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class PCAConsole {
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct STARTUPINFO { public int cb; public string lpReserved; public string lpDesktop; public string lpTitle;
        public int dwX; public int dwY; public int dwXSize; public int dwYSize; public int dwXCountChars; public int dwYCountChars;
        public int dwFillAttribute; public int dwFlags; public short wShowWindow; public short cbReserved2;
        public IntPtr lpReserved2; public IntPtr hStdInput; public IntPtr hStdOutput; public IntPtr hStdError; }
    [StructLayout(LayoutKind.Sequential)]
    struct PROCESS_INFORMATION { public IntPtr hProcess; public IntPtr hThread; public int dwProcessId; public int dwThreadId; }
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct PROFILEINFO { public int dwSize; public int dwFlags; public string lpUserName; public string lpProfilePath;
        public string lpDefaultPath; public string lpServerName; public string lpPolicyPath; public IntPtr hProfile; }
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LogonUser(string u, string d, string p, int type, int prov, out IntPtr tok);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool DuplicateTokenEx(IntPtr h, uint acc, IntPtr attr, int lvl, int type, out IntPtr nt);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool GetTokenInformation(IntPtr t, int cls, IntPtr info, int len, out int ret);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool SetTokenInformation(IntPtr t, int cls, IntPtr info, int len);
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool CreateProcessAsUser(IntPtr tok, string app, string cmd, IntPtr pa, IntPtr ta, bool inh,
        uint flags, IntPtr env, string cwd, ref STARTUPINFO si, out PROCESS_INFORMATION pi);
    [DllImport("userenv.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LoadUserProfile(IntPtr tok, ref PROFILEINFO pi);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool CreateEnvironmentBlock(out IntPtr env, IntPtr tok, bool inh);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool DestroyEnvironmentBlock(IntPtr env);
    [DllImport("kernel32.dll")]
    static extern uint WTSGetActiveConsoleSessionId();
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern bool CloseHandle(IntPtr h);

    public static string Launch(string account, string password, string app, string args) {
        string domain = null, user = account;
        int i = account.IndexOf('\\');
        if (i > 0) { domain = account.Substring(0, i); user = account.Substring(i + 1); }
        else if (account.IndexOf('@') < 0) { domain = "."; }
        IntPtr tok = IntPtr.Zero, prim = IntPtr.Zero, env = IntPtr.Zero;
        try {
            if (!LogonUser(user, domain, password, 2, 0, out tok))
                return "LogonUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            IntPtr src = tok;
            IntPtr buf = Marshal.AllocHGlobal(IntPtr.Size);
            int ret;
            if (GetTokenInformation(tok, 19, buf, IntPtr.Size, out ret)) {
                IntPtr linked = Marshal.ReadIntPtr(buf);
                if (linked != IntPtr.Zero) src = linked;
            }
            Marshal.FreeHGlobal(buf);
            if (!DuplicateTokenEx(src, 0x02000000, IntPtr.Zero, 2, 1, out prim))
                return "DuplicateTokenEx failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            uint sess = WTSGetActiveConsoleSessionId();
            if (sess == 0xFFFFFFFF) return "no active console session";
            IntPtr p = Marshal.AllocHGlobal(4);
            Marshal.WriteInt32(p, (int)sess);
            bool okSess = SetTokenInformation(prim, 12, p, 4);
            int errSess = Marshal.GetLastWin32Error();
            Marshal.FreeHGlobal(p);
            if (!okSess) return "SetTokenInformation(session) failed (Win32 error " + errSess + ")";
            PROFILEINFO pf = new PROFILEINFO();
            pf.dwSize = Marshal.SizeOf(typeof(PROFILEINFO));
            pf.lpUserName = user;
            LoadUserProfile(prim, ref pf);
            if (!CreateEnvironmentBlock(out env, prim, false)) env = IntPtr.Zero;
            STARTUPINFO si = new STARTUPINFO();
            si.cb = Marshal.SizeOf(typeof(STARTUPINFO));
            si.lpDesktop = "winsta0\\default";
            PROCESS_INFORMATION pi;
            string cmd = "\"" + app + "\"" + (string.IsNullOrEmpty(args) ? "" : " " + args);
            string cwd = Environment.GetEnvironmentVariable("SystemRoot") + "\\System32";
            if (!CreateProcessAsUser(prim, null, cmd, IntPtr.Zero, IntPtr.Zero, false, 0x410, env, cwd, ref si, out pi))
                return "CreateProcessAsUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            CloseHandle(pi.hProcess); CloseHandle(pi.hThread);
            return "OK pid=" + pi.dwProcessId + " console-session=" + sess;
        } finally {
            if (env != IntPtr.Zero) DestroyEnvironmentBlock(env);
            if (prim != IntPtr.Zero) CloseHandle(prim);
            if (tok != IntPtr.Zero) CloseHandle(tok);
        }
    }
}
'@ -ErrorAction Stop
}

$res = 'not attempted'
try { $res = [PCAConsole]::Launch($__u, $__p, $full, $argl) } catch { $res = "exception: $($_.Exception.Message)" }
if ($res -like 'OK*') {
    Start-Sleep -Seconds 2
    $pidv = [int](($res -split 'pid=')[1] -split ' ')[0]
    if (Get-Process -Id $pidv -ErrorAction SilentlyContinue) { Write-Output "  OPENED on the target's screen as $__u  ($res)" }
    else { Write-Output "  Started as $__u ($res); the program has already handed off to another process or closed -- check the target's screen." }
    return
}
Write-Output "  Launch as the supplied admin account did not work: $res"
Write-Output "  Falling back to the account signed in at the console ($consoleUser)..."
try {
    $tn = 'PCAdminTool_UI_' + [guid]::NewGuid().ToString('N').Substring(0,8)
    if ($argl) { $a = New-ScheduledTaskAction -Execute $full -Argument $argl } else { $a = New-ScheduledTaskAction -Execute $full }
    $p = New-ScheduledTaskPrincipal -UserId $consoleUser -LogonType Interactive -RunLevel Highest
    Register-ScheduledTask -TaskName $tn -Action $a -Principal $p -Force | Out-Null
    Start-ScheduledTask -TaskName $tn
    Start-Sleep -Seconds 3
    Unregister-ScheduledTask -TaskName $tn -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "  OPENED on the target's screen as $consoleUser (fallback). It is only elevated if that account is a local administrator."
} catch { Write-Output "  Fallback failed too: $($_.Exception.Message)" }
""",
        "danger": False,
        "needs_cred": True,
        "detached": True,
        "wait_sec": 90,
    },
    {
        "id": 'rc_net_connections',
        "label": 'Open Network Connections (Network Adapters) on Target',
        "category": 'Admin Consoles',
        "description": "Opens on the TARGET's screen (not yours) using the admin credentials you entered -- ncpa.cpl -- adapter properties, IPv4 settings",
        "command": r"""
$exe   = 'control.exe'
$argl  = 'ncpa.cpl'
$label = 'Network Connections (Network Adapters)'

$cs = Get-CimInstance Win32_ComputerSystem -ErrorAction SilentlyContinue
$consoleUser = $cs.UserName
if (-not $consoleUser) {
    Write-Output "  Nobody is signed in at the target's physical console (a Remote Desktop-only session does not count)."
    Write-Output "  There is no screen to open $label on -- sign in at the target, then run this again."
    return
}
Write-Output "  Console session user : $consoleUser"

$full = $exe
$gc = Get-Command $exe -ErrorAction SilentlyContinue
if ($gc -and $gc.Source) { $full = $gc.Source }
elseif (-not [IO.Path]::IsPathRooted($exe)) { $full = Join-Path $env:SystemRoot ('System32\' + $exe) }
$cmdText = if ($argl) { "$full $argl" } else { $full }
Write-Output "  Launching            : $cmdText"

if (-not ('PCAConsole' -as [type])) {
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class PCAConsole {
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct STARTUPINFO { public int cb; public string lpReserved; public string lpDesktop; public string lpTitle;
        public int dwX; public int dwY; public int dwXSize; public int dwYSize; public int dwXCountChars; public int dwYCountChars;
        public int dwFillAttribute; public int dwFlags; public short wShowWindow; public short cbReserved2;
        public IntPtr lpReserved2; public IntPtr hStdInput; public IntPtr hStdOutput; public IntPtr hStdError; }
    [StructLayout(LayoutKind.Sequential)]
    struct PROCESS_INFORMATION { public IntPtr hProcess; public IntPtr hThread; public int dwProcessId; public int dwThreadId; }
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct PROFILEINFO { public int dwSize; public int dwFlags; public string lpUserName; public string lpProfilePath;
        public string lpDefaultPath; public string lpServerName; public string lpPolicyPath; public IntPtr hProfile; }
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LogonUser(string u, string d, string p, int type, int prov, out IntPtr tok);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool DuplicateTokenEx(IntPtr h, uint acc, IntPtr attr, int lvl, int type, out IntPtr nt);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool GetTokenInformation(IntPtr t, int cls, IntPtr info, int len, out int ret);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool SetTokenInformation(IntPtr t, int cls, IntPtr info, int len);
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool CreateProcessAsUser(IntPtr tok, string app, string cmd, IntPtr pa, IntPtr ta, bool inh,
        uint flags, IntPtr env, string cwd, ref STARTUPINFO si, out PROCESS_INFORMATION pi);
    [DllImport("userenv.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LoadUserProfile(IntPtr tok, ref PROFILEINFO pi);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool CreateEnvironmentBlock(out IntPtr env, IntPtr tok, bool inh);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool DestroyEnvironmentBlock(IntPtr env);
    [DllImport("kernel32.dll")]
    static extern uint WTSGetActiveConsoleSessionId();
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern bool CloseHandle(IntPtr h);

    public static string Launch(string account, string password, string app, string args) {
        string domain = null, user = account;
        int i = account.IndexOf('\\');
        if (i > 0) { domain = account.Substring(0, i); user = account.Substring(i + 1); }
        else if (account.IndexOf('@') < 0) { domain = "."; }
        IntPtr tok = IntPtr.Zero, prim = IntPtr.Zero, env = IntPtr.Zero;
        try {
            if (!LogonUser(user, domain, password, 2, 0, out tok))
                return "LogonUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            IntPtr src = tok;
            IntPtr buf = Marshal.AllocHGlobal(IntPtr.Size);
            int ret;
            if (GetTokenInformation(tok, 19, buf, IntPtr.Size, out ret)) {
                IntPtr linked = Marshal.ReadIntPtr(buf);
                if (linked != IntPtr.Zero) src = linked;
            }
            Marshal.FreeHGlobal(buf);
            if (!DuplicateTokenEx(src, 0x02000000, IntPtr.Zero, 2, 1, out prim))
                return "DuplicateTokenEx failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            uint sess = WTSGetActiveConsoleSessionId();
            if (sess == 0xFFFFFFFF) return "no active console session";
            IntPtr p = Marshal.AllocHGlobal(4);
            Marshal.WriteInt32(p, (int)sess);
            bool okSess = SetTokenInformation(prim, 12, p, 4);
            int errSess = Marshal.GetLastWin32Error();
            Marshal.FreeHGlobal(p);
            if (!okSess) return "SetTokenInformation(session) failed (Win32 error " + errSess + ")";
            PROFILEINFO pf = new PROFILEINFO();
            pf.dwSize = Marshal.SizeOf(typeof(PROFILEINFO));
            pf.lpUserName = user;
            LoadUserProfile(prim, ref pf);
            if (!CreateEnvironmentBlock(out env, prim, false)) env = IntPtr.Zero;
            STARTUPINFO si = new STARTUPINFO();
            si.cb = Marshal.SizeOf(typeof(STARTUPINFO));
            si.lpDesktop = "winsta0\\default";
            PROCESS_INFORMATION pi;
            string cmd = "\"" + app + "\"" + (string.IsNullOrEmpty(args) ? "" : " " + args);
            string cwd = Environment.GetEnvironmentVariable("SystemRoot") + "\\System32";
            if (!CreateProcessAsUser(prim, null, cmd, IntPtr.Zero, IntPtr.Zero, false, 0x410, env, cwd, ref si, out pi))
                return "CreateProcessAsUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            CloseHandle(pi.hProcess); CloseHandle(pi.hThread);
            return "OK pid=" + pi.dwProcessId + " console-session=" + sess;
        } finally {
            if (env != IntPtr.Zero) DestroyEnvironmentBlock(env);
            if (prim != IntPtr.Zero) CloseHandle(prim);
            if (tok != IntPtr.Zero) CloseHandle(tok);
        }
    }
}
'@ -ErrorAction Stop
}

$res = 'not attempted'
try { $res = [PCAConsole]::Launch($__u, $__p, $full, $argl) } catch { $res = "exception: $($_.Exception.Message)" }
if ($res -like 'OK*') {
    Start-Sleep -Seconds 2
    $pidv = [int](($res -split 'pid=')[1] -split ' ')[0]
    if (Get-Process -Id $pidv -ErrorAction SilentlyContinue) { Write-Output "  OPENED on the target's screen as $__u  ($res)" }
    else { Write-Output "  Started as $__u ($res); the program has already handed off to another process or closed -- check the target's screen." }
    return
}
Write-Output "  Launch as the supplied admin account did not work: $res"
Write-Output "  Falling back to the account signed in at the console ($consoleUser)..."
try {
    $tn = 'PCAdminTool_UI_' + [guid]::NewGuid().ToString('N').Substring(0,8)
    if ($argl) { $a = New-ScheduledTaskAction -Execute $full -Argument $argl } else { $a = New-ScheduledTaskAction -Execute $full }
    $p = New-ScheduledTaskPrincipal -UserId $consoleUser -LogonType Interactive -RunLevel Highest
    Register-ScheduledTask -TaskName $tn -Action $a -Principal $p -Force | Out-Null
    Start-ScheduledTask -TaskName $tn
    Start-Sleep -Seconds 3
    Unregister-ScheduledTask -TaskName $tn -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "  OPENED on the target's screen as $consoleUser (fallback). It is only elevated if that account is a local administrator."
} catch { Write-Output "  Fallback failed too: $($_.Exception.Message)" }
""",
        "danger": False,
        "needs_cred": True,
        "detached": True,
        "wait_sec": 90,
    },
    {
        "id": 'rc_task_manager',
        "label": 'Open Task Manager on Target',
        "category": 'Admin Consoles',
        "description": "Opens on the TARGET's screen (not yours) using the admin credentials you entered -- taskmgr.exe",
        "command": r"""
$exe   = 'taskmgr.exe'
$argl  = ''
$label = 'Task Manager'

$cs = Get-CimInstance Win32_ComputerSystem -ErrorAction SilentlyContinue
$consoleUser = $cs.UserName
if (-not $consoleUser) {
    Write-Output "  Nobody is signed in at the target's physical console (a Remote Desktop-only session does not count)."
    Write-Output "  There is no screen to open $label on -- sign in at the target, then run this again."
    return
}
Write-Output "  Console session user : $consoleUser"

$full = $exe
$gc = Get-Command $exe -ErrorAction SilentlyContinue
if ($gc -and $gc.Source) { $full = $gc.Source }
elseif (-not [IO.Path]::IsPathRooted($exe)) { $full = Join-Path $env:SystemRoot ('System32\' + $exe) }
$cmdText = if ($argl) { "$full $argl" } else { $full }
Write-Output "  Launching            : $cmdText"

if (-not ('PCAConsole' -as [type])) {
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class PCAConsole {
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct STARTUPINFO { public int cb; public string lpReserved; public string lpDesktop; public string lpTitle;
        public int dwX; public int dwY; public int dwXSize; public int dwYSize; public int dwXCountChars; public int dwYCountChars;
        public int dwFillAttribute; public int dwFlags; public short wShowWindow; public short cbReserved2;
        public IntPtr lpReserved2; public IntPtr hStdInput; public IntPtr hStdOutput; public IntPtr hStdError; }
    [StructLayout(LayoutKind.Sequential)]
    struct PROCESS_INFORMATION { public IntPtr hProcess; public IntPtr hThread; public int dwProcessId; public int dwThreadId; }
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct PROFILEINFO { public int dwSize; public int dwFlags; public string lpUserName; public string lpProfilePath;
        public string lpDefaultPath; public string lpServerName; public string lpPolicyPath; public IntPtr hProfile; }
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LogonUser(string u, string d, string p, int type, int prov, out IntPtr tok);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool DuplicateTokenEx(IntPtr h, uint acc, IntPtr attr, int lvl, int type, out IntPtr nt);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool GetTokenInformation(IntPtr t, int cls, IntPtr info, int len, out int ret);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool SetTokenInformation(IntPtr t, int cls, IntPtr info, int len);
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool CreateProcessAsUser(IntPtr tok, string app, string cmd, IntPtr pa, IntPtr ta, bool inh,
        uint flags, IntPtr env, string cwd, ref STARTUPINFO si, out PROCESS_INFORMATION pi);
    [DllImport("userenv.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LoadUserProfile(IntPtr tok, ref PROFILEINFO pi);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool CreateEnvironmentBlock(out IntPtr env, IntPtr tok, bool inh);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool DestroyEnvironmentBlock(IntPtr env);
    [DllImport("kernel32.dll")]
    static extern uint WTSGetActiveConsoleSessionId();
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern bool CloseHandle(IntPtr h);

    public static string Launch(string account, string password, string app, string args) {
        string domain = null, user = account;
        int i = account.IndexOf('\\');
        if (i > 0) { domain = account.Substring(0, i); user = account.Substring(i + 1); }
        else if (account.IndexOf('@') < 0) { domain = "."; }
        IntPtr tok = IntPtr.Zero, prim = IntPtr.Zero, env = IntPtr.Zero;
        try {
            if (!LogonUser(user, domain, password, 2, 0, out tok))
                return "LogonUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            IntPtr src = tok;
            IntPtr buf = Marshal.AllocHGlobal(IntPtr.Size);
            int ret;
            if (GetTokenInformation(tok, 19, buf, IntPtr.Size, out ret)) {
                IntPtr linked = Marshal.ReadIntPtr(buf);
                if (linked != IntPtr.Zero) src = linked;
            }
            Marshal.FreeHGlobal(buf);
            if (!DuplicateTokenEx(src, 0x02000000, IntPtr.Zero, 2, 1, out prim))
                return "DuplicateTokenEx failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            uint sess = WTSGetActiveConsoleSessionId();
            if (sess == 0xFFFFFFFF) return "no active console session";
            IntPtr p = Marshal.AllocHGlobal(4);
            Marshal.WriteInt32(p, (int)sess);
            bool okSess = SetTokenInformation(prim, 12, p, 4);
            int errSess = Marshal.GetLastWin32Error();
            Marshal.FreeHGlobal(p);
            if (!okSess) return "SetTokenInformation(session) failed (Win32 error " + errSess + ")";
            PROFILEINFO pf = new PROFILEINFO();
            pf.dwSize = Marshal.SizeOf(typeof(PROFILEINFO));
            pf.lpUserName = user;
            LoadUserProfile(prim, ref pf);
            if (!CreateEnvironmentBlock(out env, prim, false)) env = IntPtr.Zero;
            STARTUPINFO si = new STARTUPINFO();
            si.cb = Marshal.SizeOf(typeof(STARTUPINFO));
            si.lpDesktop = "winsta0\\default";
            PROCESS_INFORMATION pi;
            string cmd = "\"" + app + "\"" + (string.IsNullOrEmpty(args) ? "" : " " + args);
            string cwd = Environment.GetEnvironmentVariable("SystemRoot") + "\\System32";
            if (!CreateProcessAsUser(prim, null, cmd, IntPtr.Zero, IntPtr.Zero, false, 0x410, env, cwd, ref si, out pi))
                return "CreateProcessAsUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            CloseHandle(pi.hProcess); CloseHandle(pi.hThread);
            return "OK pid=" + pi.dwProcessId + " console-session=" + sess;
        } finally {
            if (env != IntPtr.Zero) DestroyEnvironmentBlock(env);
            if (prim != IntPtr.Zero) CloseHandle(prim);
            if (tok != IntPtr.Zero) CloseHandle(tok);
        }
    }
}
'@ -ErrorAction Stop
}

$res = 'not attempted'
try { $res = [PCAConsole]::Launch($__u, $__p, $full, $argl) } catch { $res = "exception: $($_.Exception.Message)" }
if ($res -like 'OK*') {
    Start-Sleep -Seconds 2
    $pidv = [int](($res -split 'pid=')[1] -split ' ')[0]
    if (Get-Process -Id $pidv -ErrorAction SilentlyContinue) { Write-Output "  OPENED on the target's screen as $__u  ($res)" }
    else { Write-Output "  Started as $__u ($res); the program has already handed off to another process or closed -- check the target's screen." }
    return
}
Write-Output "  Launch as the supplied admin account did not work: $res"
Write-Output "  Falling back to the account signed in at the console ($consoleUser)..."
try {
    $tn = 'PCAdminTool_UI_' + [guid]::NewGuid().ToString('N').Substring(0,8)
    if ($argl) { $a = New-ScheduledTaskAction -Execute $full -Argument $argl } else { $a = New-ScheduledTaskAction -Execute $full }
    $p = New-ScheduledTaskPrincipal -UserId $consoleUser -LogonType Interactive -RunLevel Highest
    Register-ScheduledTask -TaskName $tn -Action $a -Principal $p -Force | Out-Null
    Start-ScheduledTask -TaskName $tn
    Start-Sleep -Seconds 3
    Unregister-ScheduledTask -TaskName $tn -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "  OPENED on the target's screen as $consoleUser (fallback). It is only elevated if that account is a local administrator."
} catch { Write-Output "  Fallback failed too: $($_.Exception.Message)" }
""",
        "danger": False,
        "needs_cred": True,
        "detached": True,
        "wait_sec": 90,
    },
    {
        "id": 'rc_resource_monitor',
        "label": 'Open Resource Monitor on Target',
        "category": 'Admin Consoles',
        "description": "Opens on the TARGET's screen (not yours) using the admin credentials you entered -- resmon.exe -- CPU / memory / disk / network per process",
        "command": r"""
$exe   = 'resmon.exe'
$argl  = ''
$label = 'Resource Monitor'

$cs = Get-CimInstance Win32_ComputerSystem -ErrorAction SilentlyContinue
$consoleUser = $cs.UserName
if (-not $consoleUser) {
    Write-Output "  Nobody is signed in at the target's physical console (a Remote Desktop-only session does not count)."
    Write-Output "  There is no screen to open $label on -- sign in at the target, then run this again."
    return
}
Write-Output "  Console session user : $consoleUser"

$full = $exe
$gc = Get-Command $exe -ErrorAction SilentlyContinue
if ($gc -and $gc.Source) { $full = $gc.Source }
elseif (-not [IO.Path]::IsPathRooted($exe)) { $full = Join-Path $env:SystemRoot ('System32\' + $exe) }
$cmdText = if ($argl) { "$full $argl" } else { $full }
Write-Output "  Launching            : $cmdText"

if (-not ('PCAConsole' -as [type])) {
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class PCAConsole {
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct STARTUPINFO { public int cb; public string lpReserved; public string lpDesktop; public string lpTitle;
        public int dwX; public int dwY; public int dwXSize; public int dwYSize; public int dwXCountChars; public int dwYCountChars;
        public int dwFillAttribute; public int dwFlags; public short wShowWindow; public short cbReserved2;
        public IntPtr lpReserved2; public IntPtr hStdInput; public IntPtr hStdOutput; public IntPtr hStdError; }
    [StructLayout(LayoutKind.Sequential)]
    struct PROCESS_INFORMATION { public IntPtr hProcess; public IntPtr hThread; public int dwProcessId; public int dwThreadId; }
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct PROFILEINFO { public int dwSize; public int dwFlags; public string lpUserName; public string lpProfilePath;
        public string lpDefaultPath; public string lpServerName; public string lpPolicyPath; public IntPtr hProfile; }
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LogonUser(string u, string d, string p, int type, int prov, out IntPtr tok);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool DuplicateTokenEx(IntPtr h, uint acc, IntPtr attr, int lvl, int type, out IntPtr nt);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool GetTokenInformation(IntPtr t, int cls, IntPtr info, int len, out int ret);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool SetTokenInformation(IntPtr t, int cls, IntPtr info, int len);
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool CreateProcessAsUser(IntPtr tok, string app, string cmd, IntPtr pa, IntPtr ta, bool inh,
        uint flags, IntPtr env, string cwd, ref STARTUPINFO si, out PROCESS_INFORMATION pi);
    [DllImport("userenv.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LoadUserProfile(IntPtr tok, ref PROFILEINFO pi);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool CreateEnvironmentBlock(out IntPtr env, IntPtr tok, bool inh);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool DestroyEnvironmentBlock(IntPtr env);
    [DllImport("kernel32.dll")]
    static extern uint WTSGetActiveConsoleSessionId();
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern bool CloseHandle(IntPtr h);

    public static string Launch(string account, string password, string app, string args) {
        string domain = null, user = account;
        int i = account.IndexOf('\\');
        if (i > 0) { domain = account.Substring(0, i); user = account.Substring(i + 1); }
        else if (account.IndexOf('@') < 0) { domain = "."; }
        IntPtr tok = IntPtr.Zero, prim = IntPtr.Zero, env = IntPtr.Zero;
        try {
            if (!LogonUser(user, domain, password, 2, 0, out tok))
                return "LogonUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            IntPtr src = tok;
            IntPtr buf = Marshal.AllocHGlobal(IntPtr.Size);
            int ret;
            if (GetTokenInformation(tok, 19, buf, IntPtr.Size, out ret)) {
                IntPtr linked = Marshal.ReadIntPtr(buf);
                if (linked != IntPtr.Zero) src = linked;
            }
            Marshal.FreeHGlobal(buf);
            if (!DuplicateTokenEx(src, 0x02000000, IntPtr.Zero, 2, 1, out prim))
                return "DuplicateTokenEx failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            uint sess = WTSGetActiveConsoleSessionId();
            if (sess == 0xFFFFFFFF) return "no active console session";
            IntPtr p = Marshal.AllocHGlobal(4);
            Marshal.WriteInt32(p, (int)sess);
            bool okSess = SetTokenInformation(prim, 12, p, 4);
            int errSess = Marshal.GetLastWin32Error();
            Marshal.FreeHGlobal(p);
            if (!okSess) return "SetTokenInformation(session) failed (Win32 error " + errSess + ")";
            PROFILEINFO pf = new PROFILEINFO();
            pf.dwSize = Marshal.SizeOf(typeof(PROFILEINFO));
            pf.lpUserName = user;
            LoadUserProfile(prim, ref pf);
            if (!CreateEnvironmentBlock(out env, prim, false)) env = IntPtr.Zero;
            STARTUPINFO si = new STARTUPINFO();
            si.cb = Marshal.SizeOf(typeof(STARTUPINFO));
            si.lpDesktop = "winsta0\\default";
            PROCESS_INFORMATION pi;
            string cmd = "\"" + app + "\"" + (string.IsNullOrEmpty(args) ? "" : " " + args);
            string cwd = Environment.GetEnvironmentVariable("SystemRoot") + "\\System32";
            if (!CreateProcessAsUser(prim, null, cmd, IntPtr.Zero, IntPtr.Zero, false, 0x410, env, cwd, ref si, out pi))
                return "CreateProcessAsUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            CloseHandle(pi.hProcess); CloseHandle(pi.hThread);
            return "OK pid=" + pi.dwProcessId + " console-session=" + sess;
        } finally {
            if (env != IntPtr.Zero) DestroyEnvironmentBlock(env);
            if (prim != IntPtr.Zero) CloseHandle(prim);
            if (tok != IntPtr.Zero) CloseHandle(tok);
        }
    }
}
'@ -ErrorAction Stop
}

$res = 'not attempted'
try { $res = [PCAConsole]::Launch($__u, $__p, $full, $argl) } catch { $res = "exception: $($_.Exception.Message)" }
if ($res -like 'OK*') {
    Start-Sleep -Seconds 2
    $pidv = [int](($res -split 'pid=')[1] -split ' ')[0]
    if (Get-Process -Id $pidv -ErrorAction SilentlyContinue) { Write-Output "  OPENED on the target's screen as $__u  ($res)" }
    else { Write-Output "  Started as $__u ($res); the program has already handed off to another process or closed -- check the target's screen." }
    return
}
Write-Output "  Launch as the supplied admin account did not work: $res"
Write-Output "  Falling back to the account signed in at the console ($consoleUser)..."
try {
    $tn = 'PCAdminTool_UI_' + [guid]::NewGuid().ToString('N').Substring(0,8)
    if ($argl) { $a = New-ScheduledTaskAction -Execute $full -Argument $argl } else { $a = New-ScheduledTaskAction -Execute $full }
    $p = New-ScheduledTaskPrincipal -UserId $consoleUser -LogonType Interactive -RunLevel Highest
    Register-ScheduledTask -TaskName $tn -Action $a -Principal $p -Force | Out-Null
    Start-ScheduledTask -TaskName $tn
    Start-Sleep -Seconds 3
    Unregister-ScheduledTask -TaskName $tn -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "  OPENED on the target's screen as $consoleUser (fallback). It is only elevated if that account is a local administrator."
} catch { Write-Output "  Fallback failed too: $($_.Exception.Message)" }
""",
        "danger": False,
        "needs_cred": True,
        "detached": True,
        "wait_sec": 90,
    },
    {
        "id": 'rc_perfmon',
        "label": 'Open Performance Monitor on Target',
        "category": 'Admin Consoles',
        "description": "Opens on the TARGET's screen (not yours) using the admin credentials you entered -- perfmon.msc",
        "command": r"""
$exe   = 'mmc.exe'
$argl  = 'perfmon.msc'
$label = 'Performance Monitor'

$cs = Get-CimInstance Win32_ComputerSystem -ErrorAction SilentlyContinue
$consoleUser = $cs.UserName
if (-not $consoleUser) {
    Write-Output "  Nobody is signed in at the target's physical console (a Remote Desktop-only session does not count)."
    Write-Output "  There is no screen to open $label on -- sign in at the target, then run this again."
    return
}
Write-Output "  Console session user : $consoleUser"

$full = $exe
$gc = Get-Command $exe -ErrorAction SilentlyContinue
if ($gc -and $gc.Source) { $full = $gc.Source }
elseif (-not [IO.Path]::IsPathRooted($exe)) { $full = Join-Path $env:SystemRoot ('System32\' + $exe) }
$cmdText = if ($argl) { "$full $argl" } else { $full }
Write-Output "  Launching            : $cmdText"

if (-not ('PCAConsole' -as [type])) {
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class PCAConsole {
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct STARTUPINFO { public int cb; public string lpReserved; public string lpDesktop; public string lpTitle;
        public int dwX; public int dwY; public int dwXSize; public int dwYSize; public int dwXCountChars; public int dwYCountChars;
        public int dwFillAttribute; public int dwFlags; public short wShowWindow; public short cbReserved2;
        public IntPtr lpReserved2; public IntPtr hStdInput; public IntPtr hStdOutput; public IntPtr hStdError; }
    [StructLayout(LayoutKind.Sequential)]
    struct PROCESS_INFORMATION { public IntPtr hProcess; public IntPtr hThread; public int dwProcessId; public int dwThreadId; }
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct PROFILEINFO { public int dwSize; public int dwFlags; public string lpUserName; public string lpProfilePath;
        public string lpDefaultPath; public string lpServerName; public string lpPolicyPath; public IntPtr hProfile; }
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LogonUser(string u, string d, string p, int type, int prov, out IntPtr tok);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool DuplicateTokenEx(IntPtr h, uint acc, IntPtr attr, int lvl, int type, out IntPtr nt);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool GetTokenInformation(IntPtr t, int cls, IntPtr info, int len, out int ret);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool SetTokenInformation(IntPtr t, int cls, IntPtr info, int len);
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool CreateProcessAsUser(IntPtr tok, string app, string cmd, IntPtr pa, IntPtr ta, bool inh,
        uint flags, IntPtr env, string cwd, ref STARTUPINFO si, out PROCESS_INFORMATION pi);
    [DllImport("userenv.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LoadUserProfile(IntPtr tok, ref PROFILEINFO pi);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool CreateEnvironmentBlock(out IntPtr env, IntPtr tok, bool inh);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool DestroyEnvironmentBlock(IntPtr env);
    [DllImport("kernel32.dll")]
    static extern uint WTSGetActiveConsoleSessionId();
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern bool CloseHandle(IntPtr h);

    public static string Launch(string account, string password, string app, string args) {
        string domain = null, user = account;
        int i = account.IndexOf('\\');
        if (i > 0) { domain = account.Substring(0, i); user = account.Substring(i + 1); }
        else if (account.IndexOf('@') < 0) { domain = "."; }
        IntPtr tok = IntPtr.Zero, prim = IntPtr.Zero, env = IntPtr.Zero;
        try {
            if (!LogonUser(user, domain, password, 2, 0, out tok))
                return "LogonUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            IntPtr src = tok;
            IntPtr buf = Marshal.AllocHGlobal(IntPtr.Size);
            int ret;
            if (GetTokenInformation(tok, 19, buf, IntPtr.Size, out ret)) {
                IntPtr linked = Marshal.ReadIntPtr(buf);
                if (linked != IntPtr.Zero) src = linked;
            }
            Marshal.FreeHGlobal(buf);
            if (!DuplicateTokenEx(src, 0x02000000, IntPtr.Zero, 2, 1, out prim))
                return "DuplicateTokenEx failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            uint sess = WTSGetActiveConsoleSessionId();
            if (sess == 0xFFFFFFFF) return "no active console session";
            IntPtr p = Marshal.AllocHGlobal(4);
            Marshal.WriteInt32(p, (int)sess);
            bool okSess = SetTokenInformation(prim, 12, p, 4);
            int errSess = Marshal.GetLastWin32Error();
            Marshal.FreeHGlobal(p);
            if (!okSess) return "SetTokenInformation(session) failed (Win32 error " + errSess + ")";
            PROFILEINFO pf = new PROFILEINFO();
            pf.dwSize = Marshal.SizeOf(typeof(PROFILEINFO));
            pf.lpUserName = user;
            LoadUserProfile(prim, ref pf);
            if (!CreateEnvironmentBlock(out env, prim, false)) env = IntPtr.Zero;
            STARTUPINFO si = new STARTUPINFO();
            si.cb = Marshal.SizeOf(typeof(STARTUPINFO));
            si.lpDesktop = "winsta0\\default";
            PROCESS_INFORMATION pi;
            string cmd = "\"" + app + "\"" + (string.IsNullOrEmpty(args) ? "" : " " + args);
            string cwd = Environment.GetEnvironmentVariable("SystemRoot") + "\\System32";
            if (!CreateProcessAsUser(prim, null, cmd, IntPtr.Zero, IntPtr.Zero, false, 0x410, env, cwd, ref si, out pi))
                return "CreateProcessAsUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            CloseHandle(pi.hProcess); CloseHandle(pi.hThread);
            return "OK pid=" + pi.dwProcessId + " console-session=" + sess;
        } finally {
            if (env != IntPtr.Zero) DestroyEnvironmentBlock(env);
            if (prim != IntPtr.Zero) CloseHandle(prim);
            if (tok != IntPtr.Zero) CloseHandle(tok);
        }
    }
}
'@ -ErrorAction Stop
}

$res = 'not attempted'
try { $res = [PCAConsole]::Launch($__u, $__p, $full, $argl) } catch { $res = "exception: $($_.Exception.Message)" }
if ($res -like 'OK*') {
    Start-Sleep -Seconds 2
    $pidv = [int](($res -split 'pid=')[1] -split ' ')[0]
    if (Get-Process -Id $pidv -ErrorAction SilentlyContinue) { Write-Output "  OPENED on the target's screen as $__u  ($res)" }
    else { Write-Output "  Started as $__u ($res); the program has already handed off to another process or closed -- check the target's screen." }
    return
}
Write-Output "  Launch as the supplied admin account did not work: $res"
Write-Output "  Falling back to the account signed in at the console ($consoleUser)..."
try {
    $tn = 'PCAdminTool_UI_' + [guid]::NewGuid().ToString('N').Substring(0,8)
    if ($argl) { $a = New-ScheduledTaskAction -Execute $full -Argument $argl } else { $a = New-ScheduledTaskAction -Execute $full }
    $p = New-ScheduledTaskPrincipal -UserId $consoleUser -LogonType Interactive -RunLevel Highest
    Register-ScheduledTask -TaskName $tn -Action $a -Principal $p -Force | Out-Null
    Start-ScheduledTask -TaskName $tn
    Start-Sleep -Seconds 3
    Unregister-ScheduledTask -TaskName $tn -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "  OPENED on the target's screen as $consoleUser (fallback). It is only elevated if that account is a local administrator."
} catch { Write-Output "  Fallback failed too: $($_.Exception.Message)" }
""",
        "danger": False,
        "needs_cred": True,
        "detached": True,
        "wait_sec": 90,
    },
    {
        "id": 'rc_sys_properties',
        "label": 'Open System Properties (Advanced / Computer Name) on Target',
        "category": 'Admin Consoles',
        "description": "Opens on the TARGET's screen (not yours) using the admin credentials you entered -- sysdm.cpl",
        "command": r"""
$exe   = 'control.exe'
$argl  = 'sysdm.cpl'
$label = 'System Properties (Advanced / Computer Name)'

$cs = Get-CimInstance Win32_ComputerSystem -ErrorAction SilentlyContinue
$consoleUser = $cs.UserName
if (-not $consoleUser) {
    Write-Output "  Nobody is signed in at the target's physical console (a Remote Desktop-only session does not count)."
    Write-Output "  There is no screen to open $label on -- sign in at the target, then run this again."
    return
}
Write-Output "  Console session user : $consoleUser"

$full = $exe
$gc = Get-Command $exe -ErrorAction SilentlyContinue
if ($gc -and $gc.Source) { $full = $gc.Source }
elseif (-not [IO.Path]::IsPathRooted($exe)) { $full = Join-Path $env:SystemRoot ('System32\' + $exe) }
$cmdText = if ($argl) { "$full $argl" } else { $full }
Write-Output "  Launching            : $cmdText"

if (-not ('PCAConsole' -as [type])) {
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class PCAConsole {
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct STARTUPINFO { public int cb; public string lpReserved; public string lpDesktop; public string lpTitle;
        public int dwX; public int dwY; public int dwXSize; public int dwYSize; public int dwXCountChars; public int dwYCountChars;
        public int dwFillAttribute; public int dwFlags; public short wShowWindow; public short cbReserved2;
        public IntPtr lpReserved2; public IntPtr hStdInput; public IntPtr hStdOutput; public IntPtr hStdError; }
    [StructLayout(LayoutKind.Sequential)]
    struct PROCESS_INFORMATION { public IntPtr hProcess; public IntPtr hThread; public int dwProcessId; public int dwThreadId; }
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct PROFILEINFO { public int dwSize; public int dwFlags; public string lpUserName; public string lpProfilePath;
        public string lpDefaultPath; public string lpServerName; public string lpPolicyPath; public IntPtr hProfile; }
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LogonUser(string u, string d, string p, int type, int prov, out IntPtr tok);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool DuplicateTokenEx(IntPtr h, uint acc, IntPtr attr, int lvl, int type, out IntPtr nt);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool GetTokenInformation(IntPtr t, int cls, IntPtr info, int len, out int ret);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool SetTokenInformation(IntPtr t, int cls, IntPtr info, int len);
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool CreateProcessAsUser(IntPtr tok, string app, string cmd, IntPtr pa, IntPtr ta, bool inh,
        uint flags, IntPtr env, string cwd, ref STARTUPINFO si, out PROCESS_INFORMATION pi);
    [DllImport("userenv.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LoadUserProfile(IntPtr tok, ref PROFILEINFO pi);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool CreateEnvironmentBlock(out IntPtr env, IntPtr tok, bool inh);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool DestroyEnvironmentBlock(IntPtr env);
    [DllImport("kernel32.dll")]
    static extern uint WTSGetActiveConsoleSessionId();
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern bool CloseHandle(IntPtr h);

    public static string Launch(string account, string password, string app, string args) {
        string domain = null, user = account;
        int i = account.IndexOf('\\');
        if (i > 0) { domain = account.Substring(0, i); user = account.Substring(i + 1); }
        else if (account.IndexOf('@') < 0) { domain = "."; }
        IntPtr tok = IntPtr.Zero, prim = IntPtr.Zero, env = IntPtr.Zero;
        try {
            if (!LogonUser(user, domain, password, 2, 0, out tok))
                return "LogonUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            IntPtr src = tok;
            IntPtr buf = Marshal.AllocHGlobal(IntPtr.Size);
            int ret;
            if (GetTokenInformation(tok, 19, buf, IntPtr.Size, out ret)) {
                IntPtr linked = Marshal.ReadIntPtr(buf);
                if (linked != IntPtr.Zero) src = linked;
            }
            Marshal.FreeHGlobal(buf);
            if (!DuplicateTokenEx(src, 0x02000000, IntPtr.Zero, 2, 1, out prim))
                return "DuplicateTokenEx failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            uint sess = WTSGetActiveConsoleSessionId();
            if (sess == 0xFFFFFFFF) return "no active console session";
            IntPtr p = Marshal.AllocHGlobal(4);
            Marshal.WriteInt32(p, (int)sess);
            bool okSess = SetTokenInformation(prim, 12, p, 4);
            int errSess = Marshal.GetLastWin32Error();
            Marshal.FreeHGlobal(p);
            if (!okSess) return "SetTokenInformation(session) failed (Win32 error " + errSess + ")";
            PROFILEINFO pf = new PROFILEINFO();
            pf.dwSize = Marshal.SizeOf(typeof(PROFILEINFO));
            pf.lpUserName = user;
            LoadUserProfile(prim, ref pf);
            if (!CreateEnvironmentBlock(out env, prim, false)) env = IntPtr.Zero;
            STARTUPINFO si = new STARTUPINFO();
            si.cb = Marshal.SizeOf(typeof(STARTUPINFO));
            si.lpDesktop = "winsta0\\default";
            PROCESS_INFORMATION pi;
            string cmd = "\"" + app + "\"" + (string.IsNullOrEmpty(args) ? "" : " " + args);
            string cwd = Environment.GetEnvironmentVariable("SystemRoot") + "\\System32";
            if (!CreateProcessAsUser(prim, null, cmd, IntPtr.Zero, IntPtr.Zero, false, 0x410, env, cwd, ref si, out pi))
                return "CreateProcessAsUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            CloseHandle(pi.hProcess); CloseHandle(pi.hThread);
            return "OK pid=" + pi.dwProcessId + " console-session=" + sess;
        } finally {
            if (env != IntPtr.Zero) DestroyEnvironmentBlock(env);
            if (prim != IntPtr.Zero) CloseHandle(prim);
            if (tok != IntPtr.Zero) CloseHandle(tok);
        }
    }
}
'@ -ErrorAction Stop
}

$res = 'not attempted'
try { $res = [PCAConsole]::Launch($__u, $__p, $full, $argl) } catch { $res = "exception: $($_.Exception.Message)" }
if ($res -like 'OK*') {
    Start-Sleep -Seconds 2
    $pidv = [int](($res -split 'pid=')[1] -split ' ')[0]
    if (Get-Process -Id $pidv -ErrorAction SilentlyContinue) { Write-Output "  OPENED on the target's screen as $__u  ($res)" }
    else { Write-Output "  Started as $__u ($res); the program has already handed off to another process or closed -- check the target's screen." }
    return
}
Write-Output "  Launch as the supplied admin account did not work: $res"
Write-Output "  Falling back to the account signed in at the console ($consoleUser)..."
try {
    $tn = 'PCAdminTool_UI_' + [guid]::NewGuid().ToString('N').Substring(0,8)
    if ($argl) { $a = New-ScheduledTaskAction -Execute $full -Argument $argl } else { $a = New-ScheduledTaskAction -Execute $full }
    $p = New-ScheduledTaskPrincipal -UserId $consoleUser -LogonType Interactive -RunLevel Highest
    Register-ScheduledTask -TaskName $tn -Action $a -Principal $p -Force | Out-Null
    Start-ScheduledTask -TaskName $tn
    Start-Sleep -Seconds 3
    Unregister-ScheduledTask -TaskName $tn -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "  OPENED on the target's screen as $consoleUser (fallback). It is only elevated if that account is a local administrator."
} catch { Write-Output "  Fallback failed too: $($_.Exception.Message)" }
""",
        "danger": False,
        "needs_cred": True,
        "detached": True,
        "wait_sec": 90,
    },
    {
        "id": 'rc_programs',
        "label": 'Open Programs and Features on Target',
        "category": 'Admin Consoles',
        "description": "Opens on the TARGET's screen (not yours) using the admin credentials you entered -- appwiz.cpl -- uninstall programs",
        "command": r"""
$exe   = 'control.exe'
$argl  = 'appwiz.cpl'
$label = 'Programs and Features'

$cs = Get-CimInstance Win32_ComputerSystem -ErrorAction SilentlyContinue
$consoleUser = $cs.UserName
if (-not $consoleUser) {
    Write-Output "  Nobody is signed in at the target's physical console (a Remote Desktop-only session does not count)."
    Write-Output "  There is no screen to open $label on -- sign in at the target, then run this again."
    return
}
Write-Output "  Console session user : $consoleUser"

$full = $exe
$gc = Get-Command $exe -ErrorAction SilentlyContinue
if ($gc -and $gc.Source) { $full = $gc.Source }
elseif (-not [IO.Path]::IsPathRooted($exe)) { $full = Join-Path $env:SystemRoot ('System32\' + $exe) }
$cmdText = if ($argl) { "$full $argl" } else { $full }
Write-Output "  Launching            : $cmdText"

if (-not ('PCAConsole' -as [type])) {
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class PCAConsole {
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct STARTUPINFO { public int cb; public string lpReserved; public string lpDesktop; public string lpTitle;
        public int dwX; public int dwY; public int dwXSize; public int dwYSize; public int dwXCountChars; public int dwYCountChars;
        public int dwFillAttribute; public int dwFlags; public short wShowWindow; public short cbReserved2;
        public IntPtr lpReserved2; public IntPtr hStdInput; public IntPtr hStdOutput; public IntPtr hStdError; }
    [StructLayout(LayoutKind.Sequential)]
    struct PROCESS_INFORMATION { public IntPtr hProcess; public IntPtr hThread; public int dwProcessId; public int dwThreadId; }
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct PROFILEINFO { public int dwSize; public int dwFlags; public string lpUserName; public string lpProfilePath;
        public string lpDefaultPath; public string lpServerName; public string lpPolicyPath; public IntPtr hProfile; }
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LogonUser(string u, string d, string p, int type, int prov, out IntPtr tok);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool DuplicateTokenEx(IntPtr h, uint acc, IntPtr attr, int lvl, int type, out IntPtr nt);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool GetTokenInformation(IntPtr t, int cls, IntPtr info, int len, out int ret);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool SetTokenInformation(IntPtr t, int cls, IntPtr info, int len);
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool CreateProcessAsUser(IntPtr tok, string app, string cmd, IntPtr pa, IntPtr ta, bool inh,
        uint flags, IntPtr env, string cwd, ref STARTUPINFO si, out PROCESS_INFORMATION pi);
    [DllImport("userenv.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LoadUserProfile(IntPtr tok, ref PROFILEINFO pi);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool CreateEnvironmentBlock(out IntPtr env, IntPtr tok, bool inh);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool DestroyEnvironmentBlock(IntPtr env);
    [DllImport("kernel32.dll")]
    static extern uint WTSGetActiveConsoleSessionId();
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern bool CloseHandle(IntPtr h);

    public static string Launch(string account, string password, string app, string args) {
        string domain = null, user = account;
        int i = account.IndexOf('\\');
        if (i > 0) { domain = account.Substring(0, i); user = account.Substring(i + 1); }
        else if (account.IndexOf('@') < 0) { domain = "."; }
        IntPtr tok = IntPtr.Zero, prim = IntPtr.Zero, env = IntPtr.Zero;
        try {
            if (!LogonUser(user, domain, password, 2, 0, out tok))
                return "LogonUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            IntPtr src = tok;
            IntPtr buf = Marshal.AllocHGlobal(IntPtr.Size);
            int ret;
            if (GetTokenInformation(tok, 19, buf, IntPtr.Size, out ret)) {
                IntPtr linked = Marshal.ReadIntPtr(buf);
                if (linked != IntPtr.Zero) src = linked;
            }
            Marshal.FreeHGlobal(buf);
            if (!DuplicateTokenEx(src, 0x02000000, IntPtr.Zero, 2, 1, out prim))
                return "DuplicateTokenEx failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            uint sess = WTSGetActiveConsoleSessionId();
            if (sess == 0xFFFFFFFF) return "no active console session";
            IntPtr p = Marshal.AllocHGlobal(4);
            Marshal.WriteInt32(p, (int)sess);
            bool okSess = SetTokenInformation(prim, 12, p, 4);
            int errSess = Marshal.GetLastWin32Error();
            Marshal.FreeHGlobal(p);
            if (!okSess) return "SetTokenInformation(session) failed (Win32 error " + errSess + ")";
            PROFILEINFO pf = new PROFILEINFO();
            pf.dwSize = Marshal.SizeOf(typeof(PROFILEINFO));
            pf.lpUserName = user;
            LoadUserProfile(prim, ref pf);
            if (!CreateEnvironmentBlock(out env, prim, false)) env = IntPtr.Zero;
            STARTUPINFO si = new STARTUPINFO();
            si.cb = Marshal.SizeOf(typeof(STARTUPINFO));
            si.lpDesktop = "winsta0\\default";
            PROCESS_INFORMATION pi;
            string cmd = "\"" + app + "\"" + (string.IsNullOrEmpty(args) ? "" : " " + args);
            string cwd = Environment.GetEnvironmentVariable("SystemRoot") + "\\System32";
            if (!CreateProcessAsUser(prim, null, cmd, IntPtr.Zero, IntPtr.Zero, false, 0x410, env, cwd, ref si, out pi))
                return "CreateProcessAsUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            CloseHandle(pi.hProcess); CloseHandle(pi.hThread);
            return "OK pid=" + pi.dwProcessId + " console-session=" + sess;
        } finally {
            if (env != IntPtr.Zero) DestroyEnvironmentBlock(env);
            if (prim != IntPtr.Zero) CloseHandle(prim);
            if (tok != IntPtr.Zero) CloseHandle(tok);
        }
    }
}
'@ -ErrorAction Stop
}

$res = 'not attempted'
try { $res = [PCAConsole]::Launch($__u, $__p, $full, $argl) } catch { $res = "exception: $($_.Exception.Message)" }
if ($res -like 'OK*') {
    Start-Sleep -Seconds 2
    $pidv = [int](($res -split 'pid=')[1] -split ' ')[0]
    if (Get-Process -Id $pidv -ErrorAction SilentlyContinue) { Write-Output "  OPENED on the target's screen as $__u  ($res)" }
    else { Write-Output "  Started as $__u ($res); the program has already handed off to another process or closed -- check the target's screen." }
    return
}
Write-Output "  Launch as the supplied admin account did not work: $res"
Write-Output "  Falling back to the account signed in at the console ($consoleUser)..."
try {
    $tn = 'PCAdminTool_UI_' + [guid]::NewGuid().ToString('N').Substring(0,8)
    if ($argl) { $a = New-ScheduledTaskAction -Execute $full -Argument $argl } else { $a = New-ScheduledTaskAction -Execute $full }
    $p = New-ScheduledTaskPrincipal -UserId $consoleUser -LogonType Interactive -RunLevel Highest
    Register-ScheduledTask -TaskName $tn -Action $a -Principal $p -Force | Out-Null
    Start-ScheduledTask -TaskName $tn
    Start-Sleep -Seconds 3
    Unregister-ScheduledTask -TaskName $tn -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "  OPENED on the target's screen as $consoleUser (fallback). It is only elevated if that account is a local administrator."
} catch { Write-Output "  Fallback failed too: $($_.Exception.Message)" }
""",
        "danger": False,
        "needs_cred": True,
        "detached": True,
        "wait_sec": 90,
    },
    {
        "id": 'rc_power_options',
        "label": 'Open Power Options on Target',
        "category": 'Admin Consoles',
        "description": "Opens on the TARGET's screen (not yours) using the admin credentials you entered -- powercfg.cpl",
        "command": r"""
$exe   = 'control.exe'
$argl  = 'powercfg.cpl'
$label = 'Power Options'

$cs = Get-CimInstance Win32_ComputerSystem -ErrorAction SilentlyContinue
$consoleUser = $cs.UserName
if (-not $consoleUser) {
    Write-Output "  Nobody is signed in at the target's physical console (a Remote Desktop-only session does not count)."
    Write-Output "  There is no screen to open $label on -- sign in at the target, then run this again."
    return
}
Write-Output "  Console session user : $consoleUser"

$full = $exe
$gc = Get-Command $exe -ErrorAction SilentlyContinue
if ($gc -and $gc.Source) { $full = $gc.Source }
elseif (-not [IO.Path]::IsPathRooted($exe)) { $full = Join-Path $env:SystemRoot ('System32\' + $exe) }
$cmdText = if ($argl) { "$full $argl" } else { $full }
Write-Output "  Launching            : $cmdText"

if (-not ('PCAConsole' -as [type])) {
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class PCAConsole {
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct STARTUPINFO { public int cb; public string lpReserved; public string lpDesktop; public string lpTitle;
        public int dwX; public int dwY; public int dwXSize; public int dwYSize; public int dwXCountChars; public int dwYCountChars;
        public int dwFillAttribute; public int dwFlags; public short wShowWindow; public short cbReserved2;
        public IntPtr lpReserved2; public IntPtr hStdInput; public IntPtr hStdOutput; public IntPtr hStdError; }
    [StructLayout(LayoutKind.Sequential)]
    struct PROCESS_INFORMATION { public IntPtr hProcess; public IntPtr hThread; public int dwProcessId; public int dwThreadId; }
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct PROFILEINFO { public int dwSize; public int dwFlags; public string lpUserName; public string lpProfilePath;
        public string lpDefaultPath; public string lpServerName; public string lpPolicyPath; public IntPtr hProfile; }
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LogonUser(string u, string d, string p, int type, int prov, out IntPtr tok);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool DuplicateTokenEx(IntPtr h, uint acc, IntPtr attr, int lvl, int type, out IntPtr nt);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool GetTokenInformation(IntPtr t, int cls, IntPtr info, int len, out int ret);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool SetTokenInformation(IntPtr t, int cls, IntPtr info, int len);
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool CreateProcessAsUser(IntPtr tok, string app, string cmd, IntPtr pa, IntPtr ta, bool inh,
        uint flags, IntPtr env, string cwd, ref STARTUPINFO si, out PROCESS_INFORMATION pi);
    [DllImport("userenv.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LoadUserProfile(IntPtr tok, ref PROFILEINFO pi);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool CreateEnvironmentBlock(out IntPtr env, IntPtr tok, bool inh);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool DestroyEnvironmentBlock(IntPtr env);
    [DllImport("kernel32.dll")]
    static extern uint WTSGetActiveConsoleSessionId();
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern bool CloseHandle(IntPtr h);

    public static string Launch(string account, string password, string app, string args) {
        string domain = null, user = account;
        int i = account.IndexOf('\\');
        if (i > 0) { domain = account.Substring(0, i); user = account.Substring(i + 1); }
        else if (account.IndexOf('@') < 0) { domain = "."; }
        IntPtr tok = IntPtr.Zero, prim = IntPtr.Zero, env = IntPtr.Zero;
        try {
            if (!LogonUser(user, domain, password, 2, 0, out tok))
                return "LogonUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            IntPtr src = tok;
            IntPtr buf = Marshal.AllocHGlobal(IntPtr.Size);
            int ret;
            if (GetTokenInformation(tok, 19, buf, IntPtr.Size, out ret)) {
                IntPtr linked = Marshal.ReadIntPtr(buf);
                if (linked != IntPtr.Zero) src = linked;
            }
            Marshal.FreeHGlobal(buf);
            if (!DuplicateTokenEx(src, 0x02000000, IntPtr.Zero, 2, 1, out prim))
                return "DuplicateTokenEx failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            uint sess = WTSGetActiveConsoleSessionId();
            if (sess == 0xFFFFFFFF) return "no active console session";
            IntPtr p = Marshal.AllocHGlobal(4);
            Marshal.WriteInt32(p, (int)sess);
            bool okSess = SetTokenInformation(prim, 12, p, 4);
            int errSess = Marshal.GetLastWin32Error();
            Marshal.FreeHGlobal(p);
            if (!okSess) return "SetTokenInformation(session) failed (Win32 error " + errSess + ")";
            PROFILEINFO pf = new PROFILEINFO();
            pf.dwSize = Marshal.SizeOf(typeof(PROFILEINFO));
            pf.lpUserName = user;
            LoadUserProfile(prim, ref pf);
            if (!CreateEnvironmentBlock(out env, prim, false)) env = IntPtr.Zero;
            STARTUPINFO si = new STARTUPINFO();
            si.cb = Marshal.SizeOf(typeof(STARTUPINFO));
            si.lpDesktop = "winsta0\\default";
            PROCESS_INFORMATION pi;
            string cmd = "\"" + app + "\"" + (string.IsNullOrEmpty(args) ? "" : " " + args);
            string cwd = Environment.GetEnvironmentVariable("SystemRoot") + "\\System32";
            if (!CreateProcessAsUser(prim, null, cmd, IntPtr.Zero, IntPtr.Zero, false, 0x410, env, cwd, ref si, out pi))
                return "CreateProcessAsUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            CloseHandle(pi.hProcess); CloseHandle(pi.hThread);
            return "OK pid=" + pi.dwProcessId + " console-session=" + sess;
        } finally {
            if (env != IntPtr.Zero) DestroyEnvironmentBlock(env);
            if (prim != IntPtr.Zero) CloseHandle(prim);
            if (tok != IntPtr.Zero) CloseHandle(tok);
        }
    }
}
'@ -ErrorAction Stop
}

$res = 'not attempted'
try { $res = [PCAConsole]::Launch($__u, $__p, $full, $argl) } catch { $res = "exception: $($_.Exception.Message)" }
if ($res -like 'OK*') {
    Start-Sleep -Seconds 2
    $pidv = [int](($res -split 'pid=')[1] -split ' ')[0]
    if (Get-Process -Id $pidv -ErrorAction SilentlyContinue) { Write-Output "  OPENED on the target's screen as $__u  ($res)" }
    else { Write-Output "  Started as $__u ($res); the program has already handed off to another process or closed -- check the target's screen." }
    return
}
Write-Output "  Launch as the supplied admin account did not work: $res"
Write-Output "  Falling back to the account signed in at the console ($consoleUser)..."
try {
    $tn = 'PCAdminTool_UI_' + [guid]::NewGuid().ToString('N').Substring(0,8)
    if ($argl) { $a = New-ScheduledTaskAction -Execute $full -Argument $argl } else { $a = New-ScheduledTaskAction -Execute $full }
    $p = New-ScheduledTaskPrincipal -UserId $consoleUser -LogonType Interactive -RunLevel Highest
    Register-ScheduledTask -TaskName $tn -Action $a -Principal $p -Force | Out-Null
    Start-ScheduledTask -TaskName $tn
    Start-Sleep -Seconds 3
    Unregister-ScheduledTask -TaskName $tn -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "  OPENED on the target's screen as $consoleUser (fallback). It is only elevated if that account is a local administrator."
} catch { Write-Output "  Fallback failed too: $($_.Exception.Message)" }
""",
        "danger": False,
        "needs_cred": True,
        "detached": True,
        "wait_sec": 90,
    },
    {
        "id": 'rc_control_panel',
        "label": 'Open Control Panel on Target',
        "category": 'Admin Consoles',
        "description": "Opens on the TARGET's screen (not yours) using the admin credentials you entered -- control.exe",
        "command": r"""
$exe   = 'control.exe'
$argl  = ''
$label = 'Control Panel'

$cs = Get-CimInstance Win32_ComputerSystem -ErrorAction SilentlyContinue
$consoleUser = $cs.UserName
if (-not $consoleUser) {
    Write-Output "  Nobody is signed in at the target's physical console (a Remote Desktop-only session does not count)."
    Write-Output "  There is no screen to open $label on -- sign in at the target, then run this again."
    return
}
Write-Output "  Console session user : $consoleUser"

$full = $exe
$gc = Get-Command $exe -ErrorAction SilentlyContinue
if ($gc -and $gc.Source) { $full = $gc.Source }
elseif (-not [IO.Path]::IsPathRooted($exe)) { $full = Join-Path $env:SystemRoot ('System32\' + $exe) }
$cmdText = if ($argl) { "$full $argl" } else { $full }
Write-Output "  Launching            : $cmdText"

if (-not ('PCAConsole' -as [type])) {
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class PCAConsole {
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct STARTUPINFO { public int cb; public string lpReserved; public string lpDesktop; public string lpTitle;
        public int dwX; public int dwY; public int dwXSize; public int dwYSize; public int dwXCountChars; public int dwYCountChars;
        public int dwFillAttribute; public int dwFlags; public short wShowWindow; public short cbReserved2;
        public IntPtr lpReserved2; public IntPtr hStdInput; public IntPtr hStdOutput; public IntPtr hStdError; }
    [StructLayout(LayoutKind.Sequential)]
    struct PROCESS_INFORMATION { public IntPtr hProcess; public IntPtr hThread; public int dwProcessId; public int dwThreadId; }
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct PROFILEINFO { public int dwSize; public int dwFlags; public string lpUserName; public string lpProfilePath;
        public string lpDefaultPath; public string lpServerName; public string lpPolicyPath; public IntPtr hProfile; }
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LogonUser(string u, string d, string p, int type, int prov, out IntPtr tok);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool DuplicateTokenEx(IntPtr h, uint acc, IntPtr attr, int lvl, int type, out IntPtr nt);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool GetTokenInformation(IntPtr t, int cls, IntPtr info, int len, out int ret);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool SetTokenInformation(IntPtr t, int cls, IntPtr info, int len);
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool CreateProcessAsUser(IntPtr tok, string app, string cmd, IntPtr pa, IntPtr ta, bool inh,
        uint flags, IntPtr env, string cwd, ref STARTUPINFO si, out PROCESS_INFORMATION pi);
    [DllImport("userenv.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LoadUserProfile(IntPtr tok, ref PROFILEINFO pi);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool CreateEnvironmentBlock(out IntPtr env, IntPtr tok, bool inh);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool DestroyEnvironmentBlock(IntPtr env);
    [DllImport("kernel32.dll")]
    static extern uint WTSGetActiveConsoleSessionId();
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern bool CloseHandle(IntPtr h);

    public static string Launch(string account, string password, string app, string args) {
        string domain = null, user = account;
        int i = account.IndexOf('\\');
        if (i > 0) { domain = account.Substring(0, i); user = account.Substring(i + 1); }
        else if (account.IndexOf('@') < 0) { domain = "."; }
        IntPtr tok = IntPtr.Zero, prim = IntPtr.Zero, env = IntPtr.Zero;
        try {
            if (!LogonUser(user, domain, password, 2, 0, out tok))
                return "LogonUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            IntPtr src = tok;
            IntPtr buf = Marshal.AllocHGlobal(IntPtr.Size);
            int ret;
            if (GetTokenInformation(tok, 19, buf, IntPtr.Size, out ret)) {
                IntPtr linked = Marshal.ReadIntPtr(buf);
                if (linked != IntPtr.Zero) src = linked;
            }
            Marshal.FreeHGlobal(buf);
            if (!DuplicateTokenEx(src, 0x02000000, IntPtr.Zero, 2, 1, out prim))
                return "DuplicateTokenEx failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            uint sess = WTSGetActiveConsoleSessionId();
            if (sess == 0xFFFFFFFF) return "no active console session";
            IntPtr p = Marshal.AllocHGlobal(4);
            Marshal.WriteInt32(p, (int)sess);
            bool okSess = SetTokenInformation(prim, 12, p, 4);
            int errSess = Marshal.GetLastWin32Error();
            Marshal.FreeHGlobal(p);
            if (!okSess) return "SetTokenInformation(session) failed (Win32 error " + errSess + ")";
            PROFILEINFO pf = new PROFILEINFO();
            pf.dwSize = Marshal.SizeOf(typeof(PROFILEINFO));
            pf.lpUserName = user;
            LoadUserProfile(prim, ref pf);
            if (!CreateEnvironmentBlock(out env, prim, false)) env = IntPtr.Zero;
            STARTUPINFO si = new STARTUPINFO();
            si.cb = Marshal.SizeOf(typeof(STARTUPINFO));
            si.lpDesktop = "winsta0\\default";
            PROCESS_INFORMATION pi;
            string cmd = "\"" + app + "\"" + (string.IsNullOrEmpty(args) ? "" : " " + args);
            string cwd = Environment.GetEnvironmentVariable("SystemRoot") + "\\System32";
            if (!CreateProcessAsUser(prim, null, cmd, IntPtr.Zero, IntPtr.Zero, false, 0x410, env, cwd, ref si, out pi))
                return "CreateProcessAsUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            CloseHandle(pi.hProcess); CloseHandle(pi.hThread);
            return "OK pid=" + pi.dwProcessId + " console-session=" + sess;
        } finally {
            if (env != IntPtr.Zero) DestroyEnvironmentBlock(env);
            if (prim != IntPtr.Zero) CloseHandle(prim);
            if (tok != IntPtr.Zero) CloseHandle(tok);
        }
    }
}
'@ -ErrorAction Stop
}

$res = 'not attempted'
try { $res = [PCAConsole]::Launch($__u, $__p, $full, $argl) } catch { $res = "exception: $($_.Exception.Message)" }
if ($res -like 'OK*') {
    Start-Sleep -Seconds 2
    $pidv = [int](($res -split 'pid=')[1] -split ' ')[0]
    if (Get-Process -Id $pidv -ErrorAction SilentlyContinue) { Write-Output "  OPENED on the target's screen as $__u  ($res)" }
    else { Write-Output "  Started as $__u ($res); the program has already handed off to another process or closed -- check the target's screen." }
    return
}
Write-Output "  Launch as the supplied admin account did not work: $res"
Write-Output "  Falling back to the account signed in at the console ($consoleUser)..."
try {
    $tn = 'PCAdminTool_UI_' + [guid]::NewGuid().ToString('N').Substring(0,8)
    if ($argl) { $a = New-ScheduledTaskAction -Execute $full -Argument $argl } else { $a = New-ScheduledTaskAction -Execute $full }
    $p = New-ScheduledTaskPrincipal -UserId $consoleUser -LogonType Interactive -RunLevel Highest
    Register-ScheduledTask -TaskName $tn -Action $a -Principal $p -Force | Out-Null
    Start-ScheduledTask -TaskName $tn
    Start-Sleep -Seconds 3
    Unregister-ScheduledTask -TaskName $tn -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "  OPENED on the target's screen as $consoleUser (fallback). It is only elevated if that account is a local administrator."
} catch { Write-Output "  Fallback failed too: $($_.Exception.Message)" }
""",
        "danger": False,
        "needs_cred": True,
        "detached": True,
        "wait_sec": 90,
    },
    {
        "id": 'rc_msconfig',
        "label": 'Open System Configuration (msconfig) on Target',
        "category": 'Admin Consoles',
        "description": "Opens on the TARGET's screen (not yours) using the admin credentials you entered -- msconfig.exe -- boot and startup options",
        "command": r"""
$exe   = 'msconfig.exe'
$argl  = ''
$label = 'System Configuration (msconfig)'

$cs = Get-CimInstance Win32_ComputerSystem -ErrorAction SilentlyContinue
$consoleUser = $cs.UserName
if (-not $consoleUser) {
    Write-Output "  Nobody is signed in at the target's physical console (a Remote Desktop-only session does not count)."
    Write-Output "  There is no screen to open $label on -- sign in at the target, then run this again."
    return
}
Write-Output "  Console session user : $consoleUser"

$full = $exe
$gc = Get-Command $exe -ErrorAction SilentlyContinue
if ($gc -and $gc.Source) { $full = $gc.Source }
elseif (-not [IO.Path]::IsPathRooted($exe)) { $full = Join-Path $env:SystemRoot ('System32\' + $exe) }
$cmdText = if ($argl) { "$full $argl" } else { $full }
Write-Output "  Launching            : $cmdText"

if (-not ('PCAConsole' -as [type])) {
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class PCAConsole {
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct STARTUPINFO { public int cb; public string lpReserved; public string lpDesktop; public string lpTitle;
        public int dwX; public int dwY; public int dwXSize; public int dwYSize; public int dwXCountChars; public int dwYCountChars;
        public int dwFillAttribute; public int dwFlags; public short wShowWindow; public short cbReserved2;
        public IntPtr lpReserved2; public IntPtr hStdInput; public IntPtr hStdOutput; public IntPtr hStdError; }
    [StructLayout(LayoutKind.Sequential)]
    struct PROCESS_INFORMATION { public IntPtr hProcess; public IntPtr hThread; public int dwProcessId; public int dwThreadId; }
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct PROFILEINFO { public int dwSize; public int dwFlags; public string lpUserName; public string lpProfilePath;
        public string lpDefaultPath; public string lpServerName; public string lpPolicyPath; public IntPtr hProfile; }
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LogonUser(string u, string d, string p, int type, int prov, out IntPtr tok);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool DuplicateTokenEx(IntPtr h, uint acc, IntPtr attr, int lvl, int type, out IntPtr nt);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool GetTokenInformation(IntPtr t, int cls, IntPtr info, int len, out int ret);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool SetTokenInformation(IntPtr t, int cls, IntPtr info, int len);
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool CreateProcessAsUser(IntPtr tok, string app, string cmd, IntPtr pa, IntPtr ta, bool inh,
        uint flags, IntPtr env, string cwd, ref STARTUPINFO si, out PROCESS_INFORMATION pi);
    [DllImport("userenv.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LoadUserProfile(IntPtr tok, ref PROFILEINFO pi);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool CreateEnvironmentBlock(out IntPtr env, IntPtr tok, bool inh);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool DestroyEnvironmentBlock(IntPtr env);
    [DllImport("kernel32.dll")]
    static extern uint WTSGetActiveConsoleSessionId();
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern bool CloseHandle(IntPtr h);

    public static string Launch(string account, string password, string app, string args) {
        string domain = null, user = account;
        int i = account.IndexOf('\\');
        if (i > 0) { domain = account.Substring(0, i); user = account.Substring(i + 1); }
        else if (account.IndexOf('@') < 0) { domain = "."; }
        IntPtr tok = IntPtr.Zero, prim = IntPtr.Zero, env = IntPtr.Zero;
        try {
            if (!LogonUser(user, domain, password, 2, 0, out tok))
                return "LogonUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            IntPtr src = tok;
            IntPtr buf = Marshal.AllocHGlobal(IntPtr.Size);
            int ret;
            if (GetTokenInformation(tok, 19, buf, IntPtr.Size, out ret)) {
                IntPtr linked = Marshal.ReadIntPtr(buf);
                if (linked != IntPtr.Zero) src = linked;
            }
            Marshal.FreeHGlobal(buf);
            if (!DuplicateTokenEx(src, 0x02000000, IntPtr.Zero, 2, 1, out prim))
                return "DuplicateTokenEx failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            uint sess = WTSGetActiveConsoleSessionId();
            if (sess == 0xFFFFFFFF) return "no active console session";
            IntPtr p = Marshal.AllocHGlobal(4);
            Marshal.WriteInt32(p, (int)sess);
            bool okSess = SetTokenInformation(prim, 12, p, 4);
            int errSess = Marshal.GetLastWin32Error();
            Marshal.FreeHGlobal(p);
            if (!okSess) return "SetTokenInformation(session) failed (Win32 error " + errSess + ")";
            PROFILEINFO pf = new PROFILEINFO();
            pf.dwSize = Marshal.SizeOf(typeof(PROFILEINFO));
            pf.lpUserName = user;
            LoadUserProfile(prim, ref pf);
            if (!CreateEnvironmentBlock(out env, prim, false)) env = IntPtr.Zero;
            STARTUPINFO si = new STARTUPINFO();
            si.cb = Marshal.SizeOf(typeof(STARTUPINFO));
            si.lpDesktop = "winsta0\\default";
            PROCESS_INFORMATION pi;
            string cmd = "\"" + app + "\"" + (string.IsNullOrEmpty(args) ? "" : " " + args);
            string cwd = Environment.GetEnvironmentVariable("SystemRoot") + "\\System32";
            if (!CreateProcessAsUser(prim, null, cmd, IntPtr.Zero, IntPtr.Zero, false, 0x410, env, cwd, ref si, out pi))
                return "CreateProcessAsUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            CloseHandle(pi.hProcess); CloseHandle(pi.hThread);
            return "OK pid=" + pi.dwProcessId + " console-session=" + sess;
        } finally {
            if (env != IntPtr.Zero) DestroyEnvironmentBlock(env);
            if (prim != IntPtr.Zero) CloseHandle(prim);
            if (tok != IntPtr.Zero) CloseHandle(tok);
        }
    }
}
'@ -ErrorAction Stop
}

$res = 'not attempted'
try { $res = [PCAConsole]::Launch($__u, $__p, $full, $argl) } catch { $res = "exception: $($_.Exception.Message)" }
if ($res -like 'OK*') {
    Start-Sleep -Seconds 2
    $pidv = [int](($res -split 'pid=')[1] -split ' ')[0]
    if (Get-Process -Id $pidv -ErrorAction SilentlyContinue) { Write-Output "  OPENED on the target's screen as $__u  ($res)" }
    else { Write-Output "  Started as $__u ($res); the program has already handed off to another process or closed -- check the target's screen." }
    return
}
Write-Output "  Launch as the supplied admin account did not work: $res"
Write-Output "  Falling back to the account signed in at the console ($consoleUser)..."
try {
    $tn = 'PCAdminTool_UI_' + [guid]::NewGuid().ToString('N').Substring(0,8)
    if ($argl) { $a = New-ScheduledTaskAction -Execute $full -Argument $argl } else { $a = New-ScheduledTaskAction -Execute $full }
    $p = New-ScheduledTaskPrincipal -UserId $consoleUser -LogonType Interactive -RunLevel Highest
    Register-ScheduledTask -TaskName $tn -Action $a -Principal $p -Force | Out-Null
    Start-ScheduledTask -TaskName $tn
    Start-Sleep -Seconds 3
    Unregister-ScheduledTask -TaskName $tn -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "  OPENED on the target's screen as $consoleUser (fallback). It is only elevated if that account is a local administrator."
} catch { Write-Output "  Fallback failed too: $($_.Exception.Message)" }
""",
        "danger": False,
        "needs_cred": True,
        "detached": True,
        "wait_sec": 90,
    },
    {
        "id": 'rc_cert_mgr',
        "label": 'Open Certificates (Local Computer) on Target',
        "category": 'Admin Consoles',
        "description": "Opens on the TARGET's screen (not yours) using the admin credentials you entered -- certlm.msc",
        "command": r"""
$exe   = 'mmc.exe'
$argl  = 'certlm.msc'
$label = 'Certificates (Local Computer)'

$cs = Get-CimInstance Win32_ComputerSystem -ErrorAction SilentlyContinue
$consoleUser = $cs.UserName
if (-not $consoleUser) {
    Write-Output "  Nobody is signed in at the target's physical console (a Remote Desktop-only session does not count)."
    Write-Output "  There is no screen to open $label on -- sign in at the target, then run this again."
    return
}
Write-Output "  Console session user : $consoleUser"

$full = $exe
$gc = Get-Command $exe -ErrorAction SilentlyContinue
if ($gc -and $gc.Source) { $full = $gc.Source }
elseif (-not [IO.Path]::IsPathRooted($exe)) { $full = Join-Path $env:SystemRoot ('System32\' + $exe) }
$cmdText = if ($argl) { "$full $argl" } else { $full }
Write-Output "  Launching            : $cmdText"

if (-not ('PCAConsole' -as [type])) {
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class PCAConsole {
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct STARTUPINFO { public int cb; public string lpReserved; public string lpDesktop; public string lpTitle;
        public int dwX; public int dwY; public int dwXSize; public int dwYSize; public int dwXCountChars; public int dwYCountChars;
        public int dwFillAttribute; public int dwFlags; public short wShowWindow; public short cbReserved2;
        public IntPtr lpReserved2; public IntPtr hStdInput; public IntPtr hStdOutput; public IntPtr hStdError; }
    [StructLayout(LayoutKind.Sequential)]
    struct PROCESS_INFORMATION { public IntPtr hProcess; public IntPtr hThread; public int dwProcessId; public int dwThreadId; }
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct PROFILEINFO { public int dwSize; public int dwFlags; public string lpUserName; public string lpProfilePath;
        public string lpDefaultPath; public string lpServerName; public string lpPolicyPath; public IntPtr hProfile; }
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LogonUser(string u, string d, string p, int type, int prov, out IntPtr tok);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool DuplicateTokenEx(IntPtr h, uint acc, IntPtr attr, int lvl, int type, out IntPtr nt);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool GetTokenInformation(IntPtr t, int cls, IntPtr info, int len, out int ret);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool SetTokenInformation(IntPtr t, int cls, IntPtr info, int len);
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool CreateProcessAsUser(IntPtr tok, string app, string cmd, IntPtr pa, IntPtr ta, bool inh,
        uint flags, IntPtr env, string cwd, ref STARTUPINFO si, out PROCESS_INFORMATION pi);
    [DllImport("userenv.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LoadUserProfile(IntPtr tok, ref PROFILEINFO pi);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool CreateEnvironmentBlock(out IntPtr env, IntPtr tok, bool inh);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool DestroyEnvironmentBlock(IntPtr env);
    [DllImport("kernel32.dll")]
    static extern uint WTSGetActiveConsoleSessionId();
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern bool CloseHandle(IntPtr h);

    public static string Launch(string account, string password, string app, string args) {
        string domain = null, user = account;
        int i = account.IndexOf('\\');
        if (i > 0) { domain = account.Substring(0, i); user = account.Substring(i + 1); }
        else if (account.IndexOf('@') < 0) { domain = "."; }
        IntPtr tok = IntPtr.Zero, prim = IntPtr.Zero, env = IntPtr.Zero;
        try {
            if (!LogonUser(user, domain, password, 2, 0, out tok))
                return "LogonUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            IntPtr src = tok;
            IntPtr buf = Marshal.AllocHGlobal(IntPtr.Size);
            int ret;
            if (GetTokenInformation(tok, 19, buf, IntPtr.Size, out ret)) {
                IntPtr linked = Marshal.ReadIntPtr(buf);
                if (linked != IntPtr.Zero) src = linked;
            }
            Marshal.FreeHGlobal(buf);
            if (!DuplicateTokenEx(src, 0x02000000, IntPtr.Zero, 2, 1, out prim))
                return "DuplicateTokenEx failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            uint sess = WTSGetActiveConsoleSessionId();
            if (sess == 0xFFFFFFFF) return "no active console session";
            IntPtr p = Marshal.AllocHGlobal(4);
            Marshal.WriteInt32(p, (int)sess);
            bool okSess = SetTokenInformation(prim, 12, p, 4);
            int errSess = Marshal.GetLastWin32Error();
            Marshal.FreeHGlobal(p);
            if (!okSess) return "SetTokenInformation(session) failed (Win32 error " + errSess + ")";
            PROFILEINFO pf = new PROFILEINFO();
            pf.dwSize = Marshal.SizeOf(typeof(PROFILEINFO));
            pf.lpUserName = user;
            LoadUserProfile(prim, ref pf);
            if (!CreateEnvironmentBlock(out env, prim, false)) env = IntPtr.Zero;
            STARTUPINFO si = new STARTUPINFO();
            si.cb = Marshal.SizeOf(typeof(STARTUPINFO));
            si.lpDesktop = "winsta0\\default";
            PROCESS_INFORMATION pi;
            string cmd = "\"" + app + "\"" + (string.IsNullOrEmpty(args) ? "" : " " + args);
            string cwd = Environment.GetEnvironmentVariable("SystemRoot") + "\\System32";
            if (!CreateProcessAsUser(prim, null, cmd, IntPtr.Zero, IntPtr.Zero, false, 0x410, env, cwd, ref si, out pi))
                return "CreateProcessAsUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            CloseHandle(pi.hProcess); CloseHandle(pi.hThread);
            return "OK pid=" + pi.dwProcessId + " console-session=" + sess;
        } finally {
            if (env != IntPtr.Zero) DestroyEnvironmentBlock(env);
            if (prim != IntPtr.Zero) CloseHandle(prim);
            if (tok != IntPtr.Zero) CloseHandle(tok);
        }
    }
}
'@ -ErrorAction Stop
}

$res = 'not attempted'
try { $res = [PCAConsole]::Launch($__u, $__p, $full, $argl) } catch { $res = "exception: $($_.Exception.Message)" }
if ($res -like 'OK*') {
    Start-Sleep -Seconds 2
    $pidv = [int](($res -split 'pid=')[1] -split ' ')[0]
    if (Get-Process -Id $pidv -ErrorAction SilentlyContinue) { Write-Output "  OPENED on the target's screen as $__u  ($res)" }
    else { Write-Output "  Started as $__u ($res); the program has already handed off to another process or closed -- check the target's screen." }
    return
}
Write-Output "  Launch as the supplied admin account did not work: $res"
Write-Output "  Falling back to the account signed in at the console ($consoleUser)..."
try {
    $tn = 'PCAdminTool_UI_' + [guid]::NewGuid().ToString('N').Substring(0,8)
    if ($argl) { $a = New-ScheduledTaskAction -Execute $full -Argument $argl } else { $a = New-ScheduledTaskAction -Execute $full }
    $p = New-ScheduledTaskPrincipal -UserId $consoleUser -LogonType Interactive -RunLevel Highest
    Register-ScheduledTask -TaskName $tn -Action $a -Principal $p -Force | Out-Null
    Start-ScheduledTask -TaskName $tn
    Start-Sleep -Seconds 3
    Unregister-ScheduledTask -TaskName $tn -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "  OPENED on the target's screen as $consoleUser (fallback). It is only elevated if that account is a local administrator."
} catch { Write-Output "  Fallback failed too: $($_.Exception.Message)" }
""",
        "danger": False,
        "needs_cred": True,
        "detached": True,
        "wait_sec": 90,
    },
    {
        "id": 'rc_gpedit',
        "label": 'Open Local Group Policy Editor on Target',
        "category": 'Admin Consoles',
        "description": "Opens on the TARGET's screen (not yours) using the admin credentials you entered -- gpedit.msc (not on Home editions)",
        "command": r"""
$exe   = 'mmc.exe'
$argl  = 'gpedit.msc'
$label = 'Local Group Policy Editor'

$cs = Get-CimInstance Win32_ComputerSystem -ErrorAction SilentlyContinue
$consoleUser = $cs.UserName
if (-not $consoleUser) {
    Write-Output "  Nobody is signed in at the target's physical console (a Remote Desktop-only session does not count)."
    Write-Output "  There is no screen to open $label on -- sign in at the target, then run this again."
    return
}
Write-Output "  Console session user : $consoleUser"

$full = $exe
$gc = Get-Command $exe -ErrorAction SilentlyContinue
if ($gc -and $gc.Source) { $full = $gc.Source }
elseif (-not [IO.Path]::IsPathRooted($exe)) { $full = Join-Path $env:SystemRoot ('System32\' + $exe) }
$cmdText = if ($argl) { "$full $argl" } else { $full }
Write-Output "  Launching            : $cmdText"

if (-not ('PCAConsole' -as [type])) {
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class PCAConsole {
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct STARTUPINFO { public int cb; public string lpReserved; public string lpDesktop; public string lpTitle;
        public int dwX; public int dwY; public int dwXSize; public int dwYSize; public int dwXCountChars; public int dwYCountChars;
        public int dwFillAttribute; public int dwFlags; public short wShowWindow; public short cbReserved2;
        public IntPtr lpReserved2; public IntPtr hStdInput; public IntPtr hStdOutput; public IntPtr hStdError; }
    [StructLayout(LayoutKind.Sequential)]
    struct PROCESS_INFORMATION { public IntPtr hProcess; public IntPtr hThread; public int dwProcessId; public int dwThreadId; }
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct PROFILEINFO { public int dwSize; public int dwFlags; public string lpUserName; public string lpProfilePath;
        public string lpDefaultPath; public string lpServerName; public string lpPolicyPath; public IntPtr hProfile; }
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LogonUser(string u, string d, string p, int type, int prov, out IntPtr tok);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool DuplicateTokenEx(IntPtr h, uint acc, IntPtr attr, int lvl, int type, out IntPtr nt);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool GetTokenInformation(IntPtr t, int cls, IntPtr info, int len, out int ret);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool SetTokenInformation(IntPtr t, int cls, IntPtr info, int len);
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool CreateProcessAsUser(IntPtr tok, string app, string cmd, IntPtr pa, IntPtr ta, bool inh,
        uint flags, IntPtr env, string cwd, ref STARTUPINFO si, out PROCESS_INFORMATION pi);
    [DllImport("userenv.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LoadUserProfile(IntPtr tok, ref PROFILEINFO pi);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool CreateEnvironmentBlock(out IntPtr env, IntPtr tok, bool inh);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool DestroyEnvironmentBlock(IntPtr env);
    [DllImport("kernel32.dll")]
    static extern uint WTSGetActiveConsoleSessionId();
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern bool CloseHandle(IntPtr h);

    public static string Launch(string account, string password, string app, string args) {
        string domain = null, user = account;
        int i = account.IndexOf('\\');
        if (i > 0) { domain = account.Substring(0, i); user = account.Substring(i + 1); }
        else if (account.IndexOf('@') < 0) { domain = "."; }
        IntPtr tok = IntPtr.Zero, prim = IntPtr.Zero, env = IntPtr.Zero;
        try {
            if (!LogonUser(user, domain, password, 2, 0, out tok))
                return "LogonUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            IntPtr src = tok;
            IntPtr buf = Marshal.AllocHGlobal(IntPtr.Size);
            int ret;
            if (GetTokenInformation(tok, 19, buf, IntPtr.Size, out ret)) {
                IntPtr linked = Marshal.ReadIntPtr(buf);
                if (linked != IntPtr.Zero) src = linked;
            }
            Marshal.FreeHGlobal(buf);
            if (!DuplicateTokenEx(src, 0x02000000, IntPtr.Zero, 2, 1, out prim))
                return "DuplicateTokenEx failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            uint sess = WTSGetActiveConsoleSessionId();
            if (sess == 0xFFFFFFFF) return "no active console session";
            IntPtr p = Marshal.AllocHGlobal(4);
            Marshal.WriteInt32(p, (int)sess);
            bool okSess = SetTokenInformation(prim, 12, p, 4);
            int errSess = Marshal.GetLastWin32Error();
            Marshal.FreeHGlobal(p);
            if (!okSess) return "SetTokenInformation(session) failed (Win32 error " + errSess + ")";
            PROFILEINFO pf = new PROFILEINFO();
            pf.dwSize = Marshal.SizeOf(typeof(PROFILEINFO));
            pf.lpUserName = user;
            LoadUserProfile(prim, ref pf);
            if (!CreateEnvironmentBlock(out env, prim, false)) env = IntPtr.Zero;
            STARTUPINFO si = new STARTUPINFO();
            si.cb = Marshal.SizeOf(typeof(STARTUPINFO));
            si.lpDesktop = "winsta0\\default";
            PROCESS_INFORMATION pi;
            string cmd = "\"" + app + "\"" + (string.IsNullOrEmpty(args) ? "" : " " + args);
            string cwd = Environment.GetEnvironmentVariable("SystemRoot") + "\\System32";
            if (!CreateProcessAsUser(prim, null, cmd, IntPtr.Zero, IntPtr.Zero, false, 0x410, env, cwd, ref si, out pi))
                return "CreateProcessAsUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            CloseHandle(pi.hProcess); CloseHandle(pi.hThread);
            return "OK pid=" + pi.dwProcessId + " console-session=" + sess;
        } finally {
            if (env != IntPtr.Zero) DestroyEnvironmentBlock(env);
            if (prim != IntPtr.Zero) CloseHandle(prim);
            if (tok != IntPtr.Zero) CloseHandle(tok);
        }
    }
}
'@ -ErrorAction Stop
}

$res = 'not attempted'
try { $res = [PCAConsole]::Launch($__u, $__p, $full, $argl) } catch { $res = "exception: $($_.Exception.Message)" }
if ($res -like 'OK*') {
    Start-Sleep -Seconds 2
    $pidv = [int](($res -split 'pid=')[1] -split ' ')[0]
    if (Get-Process -Id $pidv -ErrorAction SilentlyContinue) { Write-Output "  OPENED on the target's screen as $__u  ($res)" }
    else { Write-Output "  Started as $__u ($res); the program has already handed off to another process or closed -- check the target's screen." }
    return
}
Write-Output "  Launch as the supplied admin account did not work: $res"
Write-Output "  Falling back to the account signed in at the console ($consoleUser)..."
try {
    $tn = 'PCAdminTool_UI_' + [guid]::NewGuid().ToString('N').Substring(0,8)
    if ($argl) { $a = New-ScheduledTaskAction -Execute $full -Argument $argl } else { $a = New-ScheduledTaskAction -Execute $full }
    $p = New-ScheduledTaskPrincipal -UserId $consoleUser -LogonType Interactive -RunLevel Highest
    Register-ScheduledTask -TaskName $tn -Action $a -Principal $p -Force | Out-Null
    Start-ScheduledTask -TaskName $tn
    Start-Sleep -Seconds 3
    Unregister-ScheduledTask -TaskName $tn -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "  OPENED on the target's screen as $consoleUser (fallback). It is only elevated if that account is a local administrator."
} catch { Write-Output "  Fallback failed too: $($_.Exception.Message)" }
""",
        "danger": False,
        "needs_cred": True,
        "detached": True,
        "wait_sec": 90,
    },
    {
        "id": 'rc_win_update',
        "label": 'Open Windows Update Settings on Target',
        "category": 'Admin Consoles',
        "description": "Opens on the TARGET's screen (not yours) using the admin credentials you entered -- ms-settings:windowsupdate",
        "command": r"""
$exe   = 'explorer.exe'
$argl  = 'ms-settings:windowsupdate'
$label = 'Windows Update Settings'

$cs = Get-CimInstance Win32_ComputerSystem -ErrorAction SilentlyContinue
$consoleUser = $cs.UserName
if (-not $consoleUser) {
    Write-Output "  Nobody is signed in at the target's physical console (a Remote Desktop-only session does not count)."
    Write-Output "  There is no screen to open $label on -- sign in at the target, then run this again."
    return
}
Write-Output "  Console session user : $consoleUser"

$full = $exe
$gc = Get-Command $exe -ErrorAction SilentlyContinue
if ($gc -and $gc.Source) { $full = $gc.Source }
elseif (-not [IO.Path]::IsPathRooted($exe)) { $full = Join-Path $env:SystemRoot ('System32\' + $exe) }
$cmdText = if ($argl) { "$full $argl" } else { $full }
Write-Output "  Launching            : $cmdText"

if (-not ('PCAConsole' -as [type])) {
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class PCAConsole {
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct STARTUPINFO { public int cb; public string lpReserved; public string lpDesktop; public string lpTitle;
        public int dwX; public int dwY; public int dwXSize; public int dwYSize; public int dwXCountChars; public int dwYCountChars;
        public int dwFillAttribute; public int dwFlags; public short wShowWindow; public short cbReserved2;
        public IntPtr lpReserved2; public IntPtr hStdInput; public IntPtr hStdOutput; public IntPtr hStdError; }
    [StructLayout(LayoutKind.Sequential)]
    struct PROCESS_INFORMATION { public IntPtr hProcess; public IntPtr hThread; public int dwProcessId; public int dwThreadId; }
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct PROFILEINFO { public int dwSize; public int dwFlags; public string lpUserName; public string lpProfilePath;
        public string lpDefaultPath; public string lpServerName; public string lpPolicyPath; public IntPtr hProfile; }
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LogonUser(string u, string d, string p, int type, int prov, out IntPtr tok);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool DuplicateTokenEx(IntPtr h, uint acc, IntPtr attr, int lvl, int type, out IntPtr nt);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool GetTokenInformation(IntPtr t, int cls, IntPtr info, int len, out int ret);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool SetTokenInformation(IntPtr t, int cls, IntPtr info, int len);
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool CreateProcessAsUser(IntPtr tok, string app, string cmd, IntPtr pa, IntPtr ta, bool inh,
        uint flags, IntPtr env, string cwd, ref STARTUPINFO si, out PROCESS_INFORMATION pi);
    [DllImport("userenv.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LoadUserProfile(IntPtr tok, ref PROFILEINFO pi);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool CreateEnvironmentBlock(out IntPtr env, IntPtr tok, bool inh);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool DestroyEnvironmentBlock(IntPtr env);
    [DllImport("kernel32.dll")]
    static extern uint WTSGetActiveConsoleSessionId();
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern bool CloseHandle(IntPtr h);

    public static string Launch(string account, string password, string app, string args) {
        string domain = null, user = account;
        int i = account.IndexOf('\\');
        if (i > 0) { domain = account.Substring(0, i); user = account.Substring(i + 1); }
        else if (account.IndexOf('@') < 0) { domain = "."; }
        IntPtr tok = IntPtr.Zero, prim = IntPtr.Zero, env = IntPtr.Zero;
        try {
            if (!LogonUser(user, domain, password, 2, 0, out tok))
                return "LogonUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            IntPtr src = tok;
            IntPtr buf = Marshal.AllocHGlobal(IntPtr.Size);
            int ret;
            if (GetTokenInformation(tok, 19, buf, IntPtr.Size, out ret)) {
                IntPtr linked = Marshal.ReadIntPtr(buf);
                if (linked != IntPtr.Zero) src = linked;
            }
            Marshal.FreeHGlobal(buf);
            if (!DuplicateTokenEx(src, 0x02000000, IntPtr.Zero, 2, 1, out prim))
                return "DuplicateTokenEx failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            uint sess = WTSGetActiveConsoleSessionId();
            if (sess == 0xFFFFFFFF) return "no active console session";
            IntPtr p = Marshal.AllocHGlobal(4);
            Marshal.WriteInt32(p, (int)sess);
            bool okSess = SetTokenInformation(prim, 12, p, 4);
            int errSess = Marshal.GetLastWin32Error();
            Marshal.FreeHGlobal(p);
            if (!okSess) return "SetTokenInformation(session) failed (Win32 error " + errSess + ")";
            PROFILEINFO pf = new PROFILEINFO();
            pf.dwSize = Marshal.SizeOf(typeof(PROFILEINFO));
            pf.lpUserName = user;
            LoadUserProfile(prim, ref pf);
            if (!CreateEnvironmentBlock(out env, prim, false)) env = IntPtr.Zero;
            STARTUPINFO si = new STARTUPINFO();
            si.cb = Marshal.SizeOf(typeof(STARTUPINFO));
            si.lpDesktop = "winsta0\\default";
            PROCESS_INFORMATION pi;
            string cmd = "\"" + app + "\"" + (string.IsNullOrEmpty(args) ? "" : " " + args);
            string cwd = Environment.GetEnvironmentVariable("SystemRoot") + "\\System32";
            if (!CreateProcessAsUser(prim, null, cmd, IntPtr.Zero, IntPtr.Zero, false, 0x410, env, cwd, ref si, out pi))
                return "CreateProcessAsUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            CloseHandle(pi.hProcess); CloseHandle(pi.hThread);
            return "OK pid=" + pi.dwProcessId + " console-session=" + sess;
        } finally {
            if (env != IntPtr.Zero) DestroyEnvironmentBlock(env);
            if (prim != IntPtr.Zero) CloseHandle(prim);
            if (tok != IntPtr.Zero) CloseHandle(tok);
        }
    }
}
'@ -ErrorAction Stop
}

$res = 'not attempted'
try { $res = [PCAConsole]::Launch($__u, $__p, $full, $argl) } catch { $res = "exception: $($_.Exception.Message)" }
if ($res -like 'OK*') {
    Start-Sleep -Seconds 2
    $pidv = [int](($res -split 'pid=')[1] -split ' ')[0]
    if (Get-Process -Id $pidv -ErrorAction SilentlyContinue) { Write-Output "  OPENED on the target's screen as $__u  ($res)" }
    else { Write-Output "  Started as $__u ($res); the program has already handed off to another process or closed -- check the target's screen." }
    return
}
Write-Output "  Launch as the supplied admin account did not work: $res"
Write-Output "  Falling back to the account signed in at the console ($consoleUser)..."
try {
    $tn = 'PCAdminTool_UI_' + [guid]::NewGuid().ToString('N').Substring(0,8)
    if ($argl) { $a = New-ScheduledTaskAction -Execute $full -Argument $argl } else { $a = New-ScheduledTaskAction -Execute $full }
    $p = New-ScheduledTaskPrincipal -UserId $consoleUser -LogonType Interactive -RunLevel Highest
    Register-ScheduledTask -TaskName $tn -Action $a -Principal $p -Force | Out-Null
    Start-ScheduledTask -TaskName $tn
    Start-Sleep -Seconds 3
    Unregister-ScheduledTask -TaskName $tn -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "  OPENED on the target's screen as $consoleUser (fallback). It is only elevated if that account is a local administrator."
} catch { Write-Output "  Fallback failed too: $($_.Exception.Message)" }
""",
        "danger": False,
        "needs_cred": True,
        "detached": True,
        "wait_sec": 90,
    },
    {
        "id": 'rc_powershell',
        "label": 'Open PowerShell Window (Elevated) on Target',
        "category": 'Admin Consoles',
        "description": "Opens on the TARGET's screen (not yours) using the admin credentials you entered -- powershell.exe -NoExit -- an interactive admin shell on the target's screen",
        "command": r"""
$exe   = 'powershell.exe'
$argl  = '-NoExit'
$label = 'PowerShell Window (Elevated)'

$cs = Get-CimInstance Win32_ComputerSystem -ErrorAction SilentlyContinue
$consoleUser = $cs.UserName
if (-not $consoleUser) {
    Write-Output "  Nobody is signed in at the target's physical console (a Remote Desktop-only session does not count)."
    Write-Output "  There is no screen to open $label on -- sign in at the target, then run this again."
    return
}
Write-Output "  Console session user : $consoleUser"

$full = $exe
$gc = Get-Command $exe -ErrorAction SilentlyContinue
if ($gc -and $gc.Source) { $full = $gc.Source }
elseif (-not [IO.Path]::IsPathRooted($exe)) { $full = Join-Path $env:SystemRoot ('System32\' + $exe) }
$cmdText = if ($argl) { "$full $argl" } else { $full }
Write-Output "  Launching            : $cmdText"

if (-not ('PCAConsole' -as [type])) {
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class PCAConsole {
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct STARTUPINFO { public int cb; public string lpReserved; public string lpDesktop; public string lpTitle;
        public int dwX; public int dwY; public int dwXSize; public int dwYSize; public int dwXCountChars; public int dwYCountChars;
        public int dwFillAttribute; public int dwFlags; public short wShowWindow; public short cbReserved2;
        public IntPtr lpReserved2; public IntPtr hStdInput; public IntPtr hStdOutput; public IntPtr hStdError; }
    [StructLayout(LayoutKind.Sequential)]
    struct PROCESS_INFORMATION { public IntPtr hProcess; public IntPtr hThread; public int dwProcessId; public int dwThreadId; }
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct PROFILEINFO { public int dwSize; public int dwFlags; public string lpUserName; public string lpProfilePath;
        public string lpDefaultPath; public string lpServerName; public string lpPolicyPath; public IntPtr hProfile; }
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LogonUser(string u, string d, string p, int type, int prov, out IntPtr tok);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool DuplicateTokenEx(IntPtr h, uint acc, IntPtr attr, int lvl, int type, out IntPtr nt);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool GetTokenInformation(IntPtr t, int cls, IntPtr info, int len, out int ret);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool SetTokenInformation(IntPtr t, int cls, IntPtr info, int len);
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool CreateProcessAsUser(IntPtr tok, string app, string cmd, IntPtr pa, IntPtr ta, bool inh,
        uint flags, IntPtr env, string cwd, ref STARTUPINFO si, out PROCESS_INFORMATION pi);
    [DllImport("userenv.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LoadUserProfile(IntPtr tok, ref PROFILEINFO pi);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool CreateEnvironmentBlock(out IntPtr env, IntPtr tok, bool inh);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool DestroyEnvironmentBlock(IntPtr env);
    [DllImport("kernel32.dll")]
    static extern uint WTSGetActiveConsoleSessionId();
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern bool CloseHandle(IntPtr h);

    public static string Launch(string account, string password, string app, string args) {
        string domain = null, user = account;
        int i = account.IndexOf('\\');
        if (i > 0) { domain = account.Substring(0, i); user = account.Substring(i + 1); }
        else if (account.IndexOf('@') < 0) { domain = "."; }
        IntPtr tok = IntPtr.Zero, prim = IntPtr.Zero, env = IntPtr.Zero;
        try {
            if (!LogonUser(user, domain, password, 2, 0, out tok))
                return "LogonUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            IntPtr src = tok;
            IntPtr buf = Marshal.AllocHGlobal(IntPtr.Size);
            int ret;
            if (GetTokenInformation(tok, 19, buf, IntPtr.Size, out ret)) {
                IntPtr linked = Marshal.ReadIntPtr(buf);
                if (linked != IntPtr.Zero) src = linked;
            }
            Marshal.FreeHGlobal(buf);
            if (!DuplicateTokenEx(src, 0x02000000, IntPtr.Zero, 2, 1, out prim))
                return "DuplicateTokenEx failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            uint sess = WTSGetActiveConsoleSessionId();
            if (sess == 0xFFFFFFFF) return "no active console session";
            IntPtr p = Marshal.AllocHGlobal(4);
            Marshal.WriteInt32(p, (int)sess);
            bool okSess = SetTokenInformation(prim, 12, p, 4);
            int errSess = Marshal.GetLastWin32Error();
            Marshal.FreeHGlobal(p);
            if (!okSess) return "SetTokenInformation(session) failed (Win32 error " + errSess + ")";
            PROFILEINFO pf = new PROFILEINFO();
            pf.dwSize = Marshal.SizeOf(typeof(PROFILEINFO));
            pf.lpUserName = user;
            LoadUserProfile(prim, ref pf);
            if (!CreateEnvironmentBlock(out env, prim, false)) env = IntPtr.Zero;
            STARTUPINFO si = new STARTUPINFO();
            si.cb = Marshal.SizeOf(typeof(STARTUPINFO));
            si.lpDesktop = "winsta0\\default";
            PROCESS_INFORMATION pi;
            string cmd = "\"" + app + "\"" + (string.IsNullOrEmpty(args) ? "" : " " + args);
            string cwd = Environment.GetEnvironmentVariable("SystemRoot") + "\\System32";
            if (!CreateProcessAsUser(prim, null, cmd, IntPtr.Zero, IntPtr.Zero, false, 0x410, env, cwd, ref si, out pi))
                return "CreateProcessAsUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            CloseHandle(pi.hProcess); CloseHandle(pi.hThread);
            return "OK pid=" + pi.dwProcessId + " console-session=" + sess;
        } finally {
            if (env != IntPtr.Zero) DestroyEnvironmentBlock(env);
            if (prim != IntPtr.Zero) CloseHandle(prim);
            if (tok != IntPtr.Zero) CloseHandle(tok);
        }
    }
}
'@ -ErrorAction Stop
}

$res = 'not attempted'
try { $res = [PCAConsole]::Launch($__u, $__p, $full, $argl) } catch { $res = "exception: $($_.Exception.Message)" }
if ($res -like 'OK*') {
    Start-Sleep -Seconds 2
    $pidv = [int](($res -split 'pid=')[1] -split ' ')[0]
    if (Get-Process -Id $pidv -ErrorAction SilentlyContinue) { Write-Output "  OPENED on the target's screen as $__u  ($res)" }
    else { Write-Output "  Started as $__u ($res); the program has already handed off to another process or closed -- check the target's screen." }
    return
}
Write-Output "  Launch as the supplied admin account did not work: $res"
Write-Output "  Falling back to the account signed in at the console ($consoleUser)..."
try {
    $tn = 'PCAdminTool_UI_' + [guid]::NewGuid().ToString('N').Substring(0,8)
    if ($argl) { $a = New-ScheduledTaskAction -Execute $full -Argument $argl } else { $a = New-ScheduledTaskAction -Execute $full }
    $p = New-ScheduledTaskPrincipal -UserId $consoleUser -LogonType Interactive -RunLevel Highest
    Register-ScheduledTask -TaskName $tn -Action $a -Principal $p -Force | Out-Null
    Start-ScheduledTask -TaskName $tn
    Start-Sleep -Seconds 3
    Unregister-ScheduledTask -TaskName $tn -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "  OPENED on the target's screen as $consoleUser (fallback). It is only elevated if that account is a local administrator."
} catch { Write-Output "  Fallback failed too: $($_.Exception.Message)" }
""",
        "danger": True,
        "needs_cred": True,
        "detached": True,
        "wait_sec": 90,
    },
    {
        "id": 'rc_cmd',
        "label": 'Open Command Prompt (Elevated) on Target',
        "category": 'Admin Consoles',
        "description": "Opens on the TARGET's screen (not yours) using the admin credentials you entered -- cmd.exe -- an interactive admin shell on the target's screen",
        "command": r"""
$exe   = 'cmd.exe'
$argl  = ''
$label = 'Command Prompt (Elevated)'

$cs = Get-CimInstance Win32_ComputerSystem -ErrorAction SilentlyContinue
$consoleUser = $cs.UserName
if (-not $consoleUser) {
    Write-Output "  Nobody is signed in at the target's physical console (a Remote Desktop-only session does not count)."
    Write-Output "  There is no screen to open $label on -- sign in at the target, then run this again."
    return
}
Write-Output "  Console session user : $consoleUser"

$full = $exe
$gc = Get-Command $exe -ErrorAction SilentlyContinue
if ($gc -and $gc.Source) { $full = $gc.Source }
elseif (-not [IO.Path]::IsPathRooted($exe)) { $full = Join-Path $env:SystemRoot ('System32\' + $exe) }
$cmdText = if ($argl) { "$full $argl" } else { $full }
Write-Output "  Launching            : $cmdText"

if (-not ('PCAConsole' -as [type])) {
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class PCAConsole {
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct STARTUPINFO { public int cb; public string lpReserved; public string lpDesktop; public string lpTitle;
        public int dwX; public int dwY; public int dwXSize; public int dwYSize; public int dwXCountChars; public int dwYCountChars;
        public int dwFillAttribute; public int dwFlags; public short wShowWindow; public short cbReserved2;
        public IntPtr lpReserved2; public IntPtr hStdInput; public IntPtr hStdOutput; public IntPtr hStdError; }
    [StructLayout(LayoutKind.Sequential)]
    struct PROCESS_INFORMATION { public IntPtr hProcess; public IntPtr hThread; public int dwProcessId; public int dwThreadId; }
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct PROFILEINFO { public int dwSize; public int dwFlags; public string lpUserName; public string lpProfilePath;
        public string lpDefaultPath; public string lpServerName; public string lpPolicyPath; public IntPtr hProfile; }
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LogonUser(string u, string d, string p, int type, int prov, out IntPtr tok);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool DuplicateTokenEx(IntPtr h, uint acc, IntPtr attr, int lvl, int type, out IntPtr nt);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool GetTokenInformation(IntPtr t, int cls, IntPtr info, int len, out int ret);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool SetTokenInformation(IntPtr t, int cls, IntPtr info, int len);
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool CreateProcessAsUser(IntPtr tok, string app, string cmd, IntPtr pa, IntPtr ta, bool inh,
        uint flags, IntPtr env, string cwd, ref STARTUPINFO si, out PROCESS_INFORMATION pi);
    [DllImport("userenv.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LoadUserProfile(IntPtr tok, ref PROFILEINFO pi);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool CreateEnvironmentBlock(out IntPtr env, IntPtr tok, bool inh);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool DestroyEnvironmentBlock(IntPtr env);
    [DllImport("kernel32.dll")]
    static extern uint WTSGetActiveConsoleSessionId();
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern bool CloseHandle(IntPtr h);

    public static string Launch(string account, string password, string app, string args) {
        string domain = null, user = account;
        int i = account.IndexOf('\\');
        if (i > 0) { domain = account.Substring(0, i); user = account.Substring(i + 1); }
        else if (account.IndexOf('@') < 0) { domain = "."; }
        IntPtr tok = IntPtr.Zero, prim = IntPtr.Zero, env = IntPtr.Zero;
        try {
            if (!LogonUser(user, domain, password, 2, 0, out tok))
                return "LogonUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            IntPtr src = tok;
            IntPtr buf = Marshal.AllocHGlobal(IntPtr.Size);
            int ret;
            if (GetTokenInformation(tok, 19, buf, IntPtr.Size, out ret)) {
                IntPtr linked = Marshal.ReadIntPtr(buf);
                if (linked != IntPtr.Zero) src = linked;
            }
            Marshal.FreeHGlobal(buf);
            if (!DuplicateTokenEx(src, 0x02000000, IntPtr.Zero, 2, 1, out prim))
                return "DuplicateTokenEx failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            uint sess = WTSGetActiveConsoleSessionId();
            if (sess == 0xFFFFFFFF) return "no active console session";
            IntPtr p = Marshal.AllocHGlobal(4);
            Marshal.WriteInt32(p, (int)sess);
            bool okSess = SetTokenInformation(prim, 12, p, 4);
            int errSess = Marshal.GetLastWin32Error();
            Marshal.FreeHGlobal(p);
            if (!okSess) return "SetTokenInformation(session) failed (Win32 error " + errSess + ")";
            PROFILEINFO pf = new PROFILEINFO();
            pf.dwSize = Marshal.SizeOf(typeof(PROFILEINFO));
            pf.lpUserName = user;
            LoadUserProfile(prim, ref pf);
            if (!CreateEnvironmentBlock(out env, prim, false)) env = IntPtr.Zero;
            STARTUPINFO si = new STARTUPINFO();
            si.cb = Marshal.SizeOf(typeof(STARTUPINFO));
            si.lpDesktop = "winsta0\\default";
            PROCESS_INFORMATION pi;
            string cmd = "\"" + app + "\"" + (string.IsNullOrEmpty(args) ? "" : " " + args);
            string cwd = Environment.GetEnvironmentVariable("SystemRoot") + "\\System32";
            if (!CreateProcessAsUser(prim, null, cmd, IntPtr.Zero, IntPtr.Zero, false, 0x410, env, cwd, ref si, out pi))
                return "CreateProcessAsUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            CloseHandle(pi.hProcess); CloseHandle(pi.hThread);
            return "OK pid=" + pi.dwProcessId + " console-session=" + sess;
        } finally {
            if (env != IntPtr.Zero) DestroyEnvironmentBlock(env);
            if (prim != IntPtr.Zero) CloseHandle(prim);
            if (tok != IntPtr.Zero) CloseHandle(tok);
        }
    }
}
'@ -ErrorAction Stop
}

$res = 'not attempted'
try { $res = [PCAConsole]::Launch($__u, $__p, $full, $argl) } catch { $res = "exception: $($_.Exception.Message)" }
if ($res -like 'OK*') {
    Start-Sleep -Seconds 2
    $pidv = [int](($res -split 'pid=')[1] -split ' ')[0]
    if (Get-Process -Id $pidv -ErrorAction SilentlyContinue) { Write-Output "  OPENED on the target's screen as $__u  ($res)" }
    else { Write-Output "  Started as $__u ($res); the program has already handed off to another process or closed -- check the target's screen." }
    return
}
Write-Output "  Launch as the supplied admin account did not work: $res"
Write-Output "  Falling back to the account signed in at the console ($consoleUser)..."
try {
    $tn = 'PCAdminTool_UI_' + [guid]::NewGuid().ToString('N').Substring(0,8)
    if ($argl) { $a = New-ScheduledTaskAction -Execute $full -Argument $argl } else { $a = New-ScheduledTaskAction -Execute $full }
    $p = New-ScheduledTaskPrincipal -UserId $consoleUser -LogonType Interactive -RunLevel Highest
    Register-ScheduledTask -TaskName $tn -Action $a -Principal $p -Force | Out-Null
    Start-ScheduledTask -TaskName $tn
    Start-Sleep -Seconds 3
    Unregister-ScheduledTask -TaskName $tn -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "  OPENED on the target's screen as $consoleUser (fallback). It is only elevated if that account is a local administrator."
} catch { Write-Output "  Fallback failed too: $($_.Exception.Message)" }
""",
        "danger": True,
        "needs_cred": True,
        "detached": True,
        "wait_sec": 90,
    },
    {
        "id": 'rc_regedit',
        "label": 'Open Registry Editor on Target',
        "category": 'Admin Consoles',
        "description": "Opens on the TARGET's screen (not yours) using the admin credentials you entered -- regedit.exe -- edits the target's registry",
        "command": r"""
$exe   = 'regedit.exe'
$argl  = ''
$label = 'Registry Editor'

$cs = Get-CimInstance Win32_ComputerSystem -ErrorAction SilentlyContinue
$consoleUser = $cs.UserName
if (-not $consoleUser) {
    Write-Output "  Nobody is signed in at the target's physical console (a Remote Desktop-only session does not count)."
    Write-Output "  There is no screen to open $label on -- sign in at the target, then run this again."
    return
}
Write-Output "  Console session user : $consoleUser"

$full = $exe
$gc = Get-Command $exe -ErrorAction SilentlyContinue
if ($gc -and $gc.Source) { $full = $gc.Source }
elseif (-not [IO.Path]::IsPathRooted($exe)) { $full = Join-Path $env:SystemRoot ('System32\' + $exe) }
$cmdText = if ($argl) { "$full $argl" } else { $full }
Write-Output "  Launching            : $cmdText"

if (-not ('PCAConsole' -as [type])) {
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class PCAConsole {
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct STARTUPINFO { public int cb; public string lpReserved; public string lpDesktop; public string lpTitle;
        public int dwX; public int dwY; public int dwXSize; public int dwYSize; public int dwXCountChars; public int dwYCountChars;
        public int dwFillAttribute; public int dwFlags; public short wShowWindow; public short cbReserved2;
        public IntPtr lpReserved2; public IntPtr hStdInput; public IntPtr hStdOutput; public IntPtr hStdError; }
    [StructLayout(LayoutKind.Sequential)]
    struct PROCESS_INFORMATION { public IntPtr hProcess; public IntPtr hThread; public int dwProcessId; public int dwThreadId; }
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    struct PROFILEINFO { public int dwSize; public int dwFlags; public string lpUserName; public string lpProfilePath;
        public string lpDefaultPath; public string lpServerName; public string lpPolicyPath; public IntPtr hProfile; }
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LogonUser(string u, string d, string p, int type, int prov, out IntPtr tok);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool DuplicateTokenEx(IntPtr h, uint acc, IntPtr attr, int lvl, int type, out IntPtr nt);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool GetTokenInformation(IntPtr t, int cls, IntPtr info, int len, out int ret);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool SetTokenInformation(IntPtr t, int cls, IntPtr info, int len);
    [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool CreateProcessAsUser(IntPtr tok, string app, string cmd, IntPtr pa, IntPtr ta, bool inh,
        uint flags, IntPtr env, string cwd, ref STARTUPINFO si, out PROCESS_INFORMATION pi);
    [DllImport("userenv.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    static extern bool LoadUserProfile(IntPtr tok, ref PROFILEINFO pi);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool CreateEnvironmentBlock(out IntPtr env, IntPtr tok, bool inh);
    [DllImport("userenv.dll", SetLastError=true)]
    static extern bool DestroyEnvironmentBlock(IntPtr env);
    [DllImport("kernel32.dll")]
    static extern uint WTSGetActiveConsoleSessionId();
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern bool CloseHandle(IntPtr h);

    public static string Launch(string account, string password, string app, string args) {
        string domain = null, user = account;
        int i = account.IndexOf('\\');
        if (i > 0) { domain = account.Substring(0, i); user = account.Substring(i + 1); }
        else if (account.IndexOf('@') < 0) { domain = "."; }
        IntPtr tok = IntPtr.Zero, prim = IntPtr.Zero, env = IntPtr.Zero;
        try {
            if (!LogonUser(user, domain, password, 2, 0, out tok))
                return "LogonUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            IntPtr src = tok;
            IntPtr buf = Marshal.AllocHGlobal(IntPtr.Size);
            int ret;
            if (GetTokenInformation(tok, 19, buf, IntPtr.Size, out ret)) {
                IntPtr linked = Marshal.ReadIntPtr(buf);
                if (linked != IntPtr.Zero) src = linked;
            }
            Marshal.FreeHGlobal(buf);
            if (!DuplicateTokenEx(src, 0x02000000, IntPtr.Zero, 2, 1, out prim))
                return "DuplicateTokenEx failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            uint sess = WTSGetActiveConsoleSessionId();
            if (sess == 0xFFFFFFFF) return "no active console session";
            IntPtr p = Marshal.AllocHGlobal(4);
            Marshal.WriteInt32(p, (int)sess);
            bool okSess = SetTokenInformation(prim, 12, p, 4);
            int errSess = Marshal.GetLastWin32Error();
            Marshal.FreeHGlobal(p);
            if (!okSess) return "SetTokenInformation(session) failed (Win32 error " + errSess + ")";
            PROFILEINFO pf = new PROFILEINFO();
            pf.dwSize = Marshal.SizeOf(typeof(PROFILEINFO));
            pf.lpUserName = user;
            LoadUserProfile(prim, ref pf);
            if (!CreateEnvironmentBlock(out env, prim, false)) env = IntPtr.Zero;
            STARTUPINFO si = new STARTUPINFO();
            si.cb = Marshal.SizeOf(typeof(STARTUPINFO));
            si.lpDesktop = "winsta0\\default";
            PROCESS_INFORMATION pi;
            string cmd = "\"" + app + "\"" + (string.IsNullOrEmpty(args) ? "" : " " + args);
            string cwd = Environment.GetEnvironmentVariable("SystemRoot") + "\\System32";
            if (!CreateProcessAsUser(prim, null, cmd, IntPtr.Zero, IntPtr.Zero, false, 0x410, env, cwd, ref si, out pi))
                return "CreateProcessAsUser failed (Win32 error " + Marshal.GetLastWin32Error() + ")";
            CloseHandle(pi.hProcess); CloseHandle(pi.hThread);
            return "OK pid=" + pi.dwProcessId + " console-session=" + sess;
        } finally {
            if (env != IntPtr.Zero) DestroyEnvironmentBlock(env);
            if (prim != IntPtr.Zero) CloseHandle(prim);
            if (tok != IntPtr.Zero) CloseHandle(tok);
        }
    }
}
'@ -ErrorAction Stop
}

$res = 'not attempted'
try { $res = [PCAConsole]::Launch($__u, $__p, $full, $argl) } catch { $res = "exception: $($_.Exception.Message)" }
if ($res -like 'OK*') {
    Start-Sleep -Seconds 2
    $pidv = [int](($res -split 'pid=')[1] -split ' ')[0]
    if (Get-Process -Id $pidv -ErrorAction SilentlyContinue) { Write-Output "  OPENED on the target's screen as $__u  ($res)" }
    else { Write-Output "  Started as $__u ($res); the program has already handed off to another process or closed -- check the target's screen." }
    return
}
Write-Output "  Launch as the supplied admin account did not work: $res"
Write-Output "  Falling back to the account signed in at the console ($consoleUser)..."
try {
    $tn = 'PCAdminTool_UI_' + [guid]::NewGuid().ToString('N').Substring(0,8)
    if ($argl) { $a = New-ScheduledTaskAction -Execute $full -Argument $argl } else { $a = New-ScheduledTaskAction -Execute $full }
    $p = New-ScheduledTaskPrincipal -UserId $consoleUser -LogonType Interactive -RunLevel Highest
    Register-ScheduledTask -TaskName $tn -Action $a -Principal $p -Force | Out-Null
    Start-ScheduledTask -TaskName $tn
    Start-Sleep -Seconds 3
    Unregister-ScheduledTask -TaskName $tn -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "  OPENED on the target's screen as $consoleUser (fallback). It is only elevated if that account is a local administrator."
} catch { Write-Output "  Fallback failed too: $($_.Exception.Message)" }
""",
        "danger": True,
        "needs_cred": True,
        "detached": True,
        "wait_sec": 90,
    },
]

# v3.7 -- flags consumed by the resilient execution engine (see the
# "v3.7 RESILIENT EXECUTION ENGINE" block). Operations that bounce the
# target's network run as a detached job and are polled until it answers.
_NET_DISRUPTIVE_IDS = {'flush_dns',
 'pr_disable_enable_adapter',
 'pr_restart_all_adapters',
 'pr_restart_named_adapter',
 'reset_network',
 'rt_set_dhcp',
 'rt_set_static_ip'}
for _op in OPERATIONS:
    if _op["id"] in _NET_DISRUPTIVE_IDS:
        _op["net_disruptive"] = True
        _op["detached"] = True
        _op.setdefault("wait_sec", 300)
assert _NET_DISRUPTIVE_IDS <= {o["id"] for o in OPERATIONS}, "net-disruptive id missing"

# ── Build safe metadata list (no commands) for the browser ───────────────────
# "danger" and "params" are plain descriptive metadata (no secrets) -- safe to expose.
# The actual "command" text never leaves this list.
OPS_META = [
    {"id": o["id"], "label": o["label"], "category": o["category"],
     "description": o["description"], "danger": o.get("danger", False),
     "params": o.get("params", [])}
    for o in OPERATIONS
]
OPS_MAP = {o["id"]: o for o in OPERATIONS}
assert len(OPERATIONS) == 105, f"Expected 105 operations, got {len(OPERATIONS)}"
assert len({o['id'] for o in OPERATIONS}) == 105, "Duplicate operation id detected"
CATEGORIES = list(dict.fromkeys(o["category"] for o in OPERATIONS))
DANGER_IDS = {o["id"] for o in OPERATIONS if o.get("danger")}


# ══════════════════════════════════════════════════════════════════════════════
#  PARAMETERIZED OPERATIONS -- validation + {{TOKEN}} substitution
#  v3.2: 16 of the 67 operations need a runtime value (an IP, an adapter name,
#  a device Instance ID, ...) instead of running a fixed script. Each such
#  operation's "command" text contains one or more "{{KEY}}" placeholders.
#  Every value is validated against an allow-list regex for its declared
#  "kind" BEFORE it is substituted in -- this is the injection defence: a
#  value that doesn't match the pattern is rejected outright rather than
#  escaped, so quotes/backticks/semicolons/pipes can never reach the script.
# ══════════════════════════════════════════════════════════════════════════════
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


def _validate_vsssize(raw):
    # v3.7 -- vssadmin /maxsize value: 10GB, 500MB, 2TB, 20% or UNBOUNDED.
    v = raw.strip().replace(" ", "").upper()
    m = re.match(r"^(UNBOUNDED|(\d{1,3})%|(\d{1,7})(MB|GB|TB))$", v)
    if not m:
        return None, f"'{raw}' is not a valid size (use e.g. 10GB, 500MB, 20% or UNBOUNDED)"
    if m.group(2) is not None and not (1 <= int(m.group(2)) <= 100):
        return None, f"'{raw}': a percentage must be 1-100"
    if m.group(3) is not None:
        n = int(m.group(3))
        if n < 1 or (m.group(4) == "MB" and n < 320):
            return None, f"'{raw}': the minimum VSS size is 320MB"
    return v, None


def _validate_bool(raw):
    # Checkbox param. Returns the literal PowerShell token so the command
    # body can write "$autoRestart = {{AUTO_RESTART}}" and get real $true/
    # $false, not a quoted string -- no separate substitution-time special
    # case needed elsewhere, the validator itself IS the transform (same
    # pattern as _validate_subnetmask converting CIDR to a dotted mask).
    v = raw.strip().lower()
    if v in ("true", "1", "yes", "on"):
        return "$true", None
    if v in ("false", "0", "no", "off", ""):
        return "$false", None
    return None, f"'{raw}' is not a valid true/false value"


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
    """
    op:     one operation dict from OPERATIONS (has "command"; may have "params")
    values: dict of {KEY: raw_string_from_caller}
    Returns (final_command_text, error_message_or_None). Every "{{KEY}}" token
    in op["command"] is replaced with its validated value, or with an empty
    string for an optional param the caller left blank (the command body
    itself is responsible for branching on an empty value where relevant --
    see rt_vss_delete_oldest / rt_set_static_ip's DNS1/DNS2 for the pattern).
    """
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


# ══════════════════════════════════════════════════════════════════════════════
#  WINRM HELPERS
# ══════════════════════════════════════════════════════════════════════════════
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
        # v3.7: short-lived polling sessions used while a target's network is
        # changing -- must fail fast instead of hanging for minutes.
        kwargs.update(connection_timeout=8, read_timeout=25, operation_timeout=15)
    if transport == "basic":
        kwargs["encryption"] = "never"
    return Client(hostname, **kwargs)


# ══════════════════════════════════════════════════════════════════════════════
#  v3.7  RESILIENT EXECUTION ENGINE  (kept byte-identical in app.py and
#  PCAdminTool.pyw -- edit both together)
#
#  WHY THIS EXISTS
#  Before v3.7 every operation ran INSIDE the live WinRM connection. Any
#  operation that bounces the target's network (set static IP, set DHCP,
#  flush/re-register DNS, reset TCP/IP, restart adapters) killed the very
#  connection that was carrying its own output. The client then sat waiting
#  for a reply that could never arrive (up to 170 s), "reconnected" to a stale
#  address, and -- worst -- blindly RE-RAN the sensitive operation. The only
#  way out was restarting this application.
#
#  WHAT IT DOES NOW
#  Operations flagged "net_disruptive" (and long-running ones flagged
#  "detached") are dispatched as a ONE-SHOT SCHEDULED TASK running as SYSTEM
#  on the target. The dispatch call returns in about a second, long before the
#  network changes. The task writes its output to a file on the target
#  (C:\ProgramData\PCAdminTool, ACL-restricted to SYSTEM + Administrators).
#  This side then POLLS with short-lived, brand-new sessions -- tolerating
#  drops -- on every address the target might now have (for Set Static IP that
#  is the NEW address first), reads the result when the target is back, and
#  prints it. If the address changed, every following task in the run keeps
#  using the new one. Nothing is ever re-run automatically.
# ══════════════════════════════════════════════════════════════════════════════
import base64
import uuid

JOB_DIR = r"C:\ProgramData\PCAdminTool"

_JOB_PREAMBLE = (
    "$ErrorActionPreference = 'Continue'\n"
    "$ProgressPreference = 'SilentlyContinue'\n"
    "$WarningPreference = 'SilentlyContinue'\n"
)

_WRAPPER_TMPL = r"""
$ErrorActionPreference = 'Continue'
$out  = '__OUT__'
$done = '__DONE__'
try {
    Start-Sleep -Seconds 2
    $txt = [IO.File]::ReadAllText('__INNER__')
    Remove-Item -LiteralPath '__INNER__' -Force -ErrorAction SilentlyContinue
    $sb = [scriptblock]::Create($txt)
    & $sb 2>&1 | ForEach-Object { "$_" } | Out-File -FilePath $out -Encoding utf8 -Append
    Set-Content -LiteralPath $done -Value 'OK' -Encoding ASCII
} catch {
    ('ERROR: ' + $_.Exception.Message) | Out-File -FilePath $out -Encoding utf8 -Append
    Set-Content -LiteralPath $done -Value 'FAIL' -Encoding ASCII
} finally {
    Unregister-ScheduledTask -TaskName '__TASK__' -Confirm:$false -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath '__WRAP__' -Force -ErrorAction SilentlyContinue
}
"""

_LAUNCH_TMPL = r"""
$ErrorActionPreference = 'Stop'
try {
    $d = '__DIR__'
    if (-not (Test-Path -LiteralPath $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
    & icacls.exe $d /inheritance:r /grant:r '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' | Out-Null
    $enc = New-Object System.Text.UTF8Encoding($true)
    [IO.File]::WriteAllText('__INNER__', [Text.Encoding]::Unicode.GetString([Convert]::FromBase64String('__B64INNER__')), $enc)
    [IO.File]::WriteAllText('__WRAP__',  [Text.Encoding]::Unicode.GetString([Convert]::FromBase64String('__B64WRAP__')),  $enc)
    $a = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "__WRAP__"'
    $p = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
    $s = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2)
    Register-ScheduledTask -TaskName '__TASK__' -Action $a -Principal $p -Settings $s -Force | Out-Null
    Start-ScheduledTask -TaskName '__TASK__'
    Write-Output 'JOB_STARTED'
} catch {
    Write-Output ('JOB_LAUNCH_FAILED: ' + $_.Exception.Message)
}
"""

_POLL_TMPL = r"""
$o  = '__OUT__'
$dn = '__DONE__'
if (Test-Path -LiteralPath $dn) {
    $st = (Get-Content -LiteralPath $dn -Raw).Trim()
    Write-Output ('__PCA_DONE__:' + $st)
    if (Test-Path -LiteralPath $o) { Get-Content -LiteralPath $o -Encoding UTF8 }
    Remove-Item -LiteralPath $o,$dn -Force -ErrorAction SilentlyContinue
} else {
    Write-Output '__PCA_PENDING__'
}
"""


def _ps_quote(value):
    """Single-quoted PowerShell literal (only ' needs escaping)."""
    return "'" + str(value).replace("'", "''") + "'"


def inject_credentials(script, username, password):
    """
    Prepend $__u / $__p / $__cred to a script for operations flagged
    "needs_cred". Needed because a WinRM session is a *network* logon: it
    carries no credentials of its own to a domain controller (the classic
    double-hop), so anything that must authenticate onward -- a domain
    computer rename, launching a window as the admin account -- has to be
    handed the credential explicitly. Sent only inside the encrypted PSRP
    channel; the script text is never written to the log.
    """
    prelude = (
        "$__u = " + _ps_quote(username) + "\n"
        "$__p = " + _ps_quote(password) + "\n"
        "$__cred = New-Object System.Management.Automation.PSCredential("
        "$__u, (ConvertTo-SecureString $__p -AsPlainText -Force))\n"
    )
    return prelude + script


def _detached_scripts(job_id, script):
    d = JOB_DIR
    paths = {
        "inner": f"{d}\\job_{job_id}.inner.ps1",
        "wrap":  f"{d}\\job_{job_id}.wrap.ps1",
        "out":   f"{d}\\job_{job_id}.out",
        "done":  f"{d}\\job_{job_id}.done",
        "task":  f"PCAdminTool_{job_id}",
    }
    wrapper = (_WRAPPER_TMPL
               .replace("__OUT__", paths["out"]).replace("__DONE__", paths["done"])
               .replace("__INNER__", paths["inner"]).replace("__WRAP__", paths["wrap"])
               .replace("__TASK__", paths["task"]))
    inner = _JOB_PREAMBLE + script
    b64 = lambda t: base64.b64encode(t.encode("utf-16-le")).decode("ascii")
    launch = (_LAUNCH_TMPL
              .replace("__DIR__", d)
              .replace("__INNER__", paths["inner"]).replace("__WRAP__", paths["wrap"])
              .replace("__TASK__", paths["task"])
              .replace("__B64INNER__", b64(inner)).replace("__B64WRAP__", b64(wrapper)))
    poll = (_POLL_TMPL.replace("__OUT__", paths["out"]).replace("__DONE__", paths["done"]))
    return launch, poll


def _close_client(client):
    try:
        client.wsman.close()
    except Exception:
        pass


def run_detached_gen(host, username, password, transport, script, stop_flag,
                     alt_hosts=(), max_wait=300, poll_every=3):
    """
    Generator. Yields ("info"|"ok"|"warn"|"err", text) progress lines and,
    exactly once at the end, ("result", (stdout, stderr, success, host_in_use)).

    host_in_use is the address that answered last -- the caller must keep using
    it for every following task (it differs from `host` after Set Static IP).
    """
    job_id = uuid.uuid4().hex[:10]
    launch, poll = _detached_scripts(job_id, script)

    try:
        sess = make_session(host, username, password, transport)
        out, err, ok = run_remote_ps(sess, launch)
        _close_client(sess)
    except Exception as e:                       # noqa: BLE001
        yield ("result", ("", f"Could not reach the target to start the job: {e}", False, host))
        return
    if not ok or "JOB_STARTED" not in out:
        reason = (err or out or "no reply").strip()
        yield ("result", ("", f"Could not start the detached job on the target: {reason[:500]}", False, host))
        return

    yield ("info", "Running as a detached SYSTEM job on the target -- it keeps running even if "
                   "the network drops. Waiting for the result...")

    candidates = []
    for h in list(alt_hosts) + [host]:
        if h and h not in candidates:
            candidates.append(h)
    if len(candidates) > 1:
        yield ("info", "Will look for the target at: " + ", ".join(candidates))

    t0 = time.time()
    last_note = t0
    dropped = False
    announced_back = False
    current = host

    while True:
        elapsed = time.time() - t0
        if stop_flag.is_set():
            yield ("warn", f"Stop requested -- the job (id {job_id}) keeps running on the target; "
                           f"its result file stays in {JOB_DIR}.")
            yield ("result", ("", "", False, current))
            return
        if elapsed > max_wait:
            yield ("result", ("", f"TARGET_NOT_REACHED: no result within {int(max_wait)}s. The change may "
                                  f"still have been applied -- check the target directly (job id {job_id}, "
                                  f"files in {JOB_DIR}). Tried: {', '.join(candidates)}", False, current))
            return
        time.sleep(poll_every)

        reached = False
        for h in candidates:
            if stop_flag.is_set():
                break
            try:
                ps = make_session(h, username, password, transport, fast=True)
                o, e, ok2 = run_remote_ps(ps, poll)
                _close_client(ps)
            except Exception as ex:              # noqa: BLE001
                o, e, ok2 = "", str(ex), False
            if not ok2:
                continue
            reached = True
            if h != current:
                current = h
                if h != host:
                    yield ("ok", f"Target answered on its NEW address {h} -- using it from now on.")
            if dropped and not announced_back:
                announced_back = True
                yield ("ok", f"Target is reachable again ({h}).")
            if "__PCA_DONE__:" in o:
                lines = o.splitlines()
                status = "FAIL"
                body = []
                for ln in lines:
                    if ln.startswith("__PCA_DONE__:"):
                        status = ln.split(":", 1)[1].strip()
                    else:
                        body.append(ln.lstrip("\ufeff"))
                yield ("result", ("\n".join(body), "", status == "OK", current))
                return
            break

        if not reached:
            dropped = True      # only a round where NO address answered counts as a drop

        now = time.time()
        if now - last_note >= 15:
            last_note = now
            if reached:
                yield ("info", f"Still running on the target... ({int(now - t0)}s)")
            else:
                yield ("warn", f"Target not answering yet (network change in progress?) ... ({int(now - t0)}s)")


def run_remote_ps(session, script, label=""):
    """
    Execute a PowerShell script on the remote host over real PSRP
    (Fix #18).

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


# ══════════════════════════════════════════════════════════════════════════════
#  FLASK ROUTES
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/")
def index():
    return render_template("index.html",
                           ops=json.dumps(OPS_META),
                           cats=json.dumps(CATEGORIES),
                           copyright=COPYRIGHT)


@app.route("/api/test", methods=["POST"])
def test_connection():
    data      = request.json or {}
    hostname  = data.get("hostname",  "").strip()
    username  = data.get("username",  "").strip()
    password  = data.get("password",  "")
    transport = data.get("transport", "ntlm")

    if not hostname: return jsonify({"status": "error",   "msg": "Hostname is required"})
    if not username: return jsonify({"status": "error",   "msg": "Username is required"})
    if not password: return jsonify({"status": "warning", "msg": "Password is empty — connection may fail"})

    # DNS resolve
    try:
        ip = socket.gethostbyname(hostname)
    except socket.gaierror:
        return jsonify({"status": "error",
                        "msg": f"Cannot resolve '{hostname}'. Check hostname or DNS."})

    # WinRM auth test
    try:
        session = make_session(hostname, username, password, transport)
        stdout, stderr, ok = run_remote_ps(session, 'Write-Output "PING_OK_$env:COMPUTERNAME"')
        if ok and "PING_OK_" in stdout:
            remote_name = stdout.strip().replace("PING_OK_", "")
            return jsonify({"status": "success",
                            "msg": f"Connected to {hostname} ({ip}) as '{username}'. "
                                   f"Remote computer: {remote_name}. WinRM OK."})
        else:
            return jsonify({"status": "error",
                            "msg": f"WinRM connected but test command failed.\n"
                                   f"STDOUT: {stdout[:200]}\nSTDERR: {stderr[:200]}"})
    except AuthenticationError:
        return jsonify({"status": "cred_error",
                        "msg": f"Authentication failed for '{username}' on {hostname}.\n"
                               f"Try: DOMAIN\\username  or  username@domain.local"})
    except Exception as e:
        err = str(e)
        if "5985" in err or "refused" in err.lower() or "timed out" in err.lower():
            return jsonify({"status": "winrm_error",
                            "msg": f"Cannot reach WinRM on {hostname}:5985.\n"
                                   f"Run on target (Admin): Enable-PSRemoting -Force"})
        return jsonify({"status": "error", "msg": f"Connection error: {err}"})


@app.route("/api/run", methods=["POST"])
def run_tasks():
    data       = request.json or {}
    hostname   = data.get("hostname",  "").strip()
    username   = data.get("username",  "").strip()
    password   = data.get("password",  "")
    transport  = data.get("transport", "ntlm")
    task_ids   = set(data.get("tasks", []))
    param_vals = data.get("params", {})            # {op_id: {KEY: value}}
    confirmed_danger = bool(data.get("confirmed_danger", False))

    selected = [op for op in OPERATIONS if op["id"] in task_ids]

    # ── Server-side danger gate ───────────────────────────────────────────
    # index.html already shows a browser confirm() for any DANGER_IDS
    # selection, but that is a UX nicety, not a security boundary -- nothing
    # stops a script from POSTing straight to /api/run. This is the one
    # place in the whole tool that exposes an HTTP API to anything on the
    # subnet, so it is the one place that needs its own server-side check:
    # a dangerous op cannot run without confirmed_danger=true in the body.
    dangerous = [op for op in selected if op.get("danger")]
    if dangerous and not confirmed_danger:
        names = ", ".join(o["label"] for o in dangerous)

        def deny():
            yield f"data: {json.dumps({'type': 'error', 'text': f'  Refused: {len(dangerous)} sensitive operation(s) require confirmed_danger=true: {names}'})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'success': False})}\n\n"
        return Response(stream_with_context(deny()), mimetype="text/event-stream")

    # ── Validate + substitute every {{KEY}} parameter up front ────────────
    # Fails fast, before a WinRM session is even opened, if any parameter is
    # missing or doesn't match its allow-listed pattern.
    final_commands = {}
    param_errors = []
    for op in selected:
        if op.get("params"):
            cmd, err = validate_and_substitute(op, param_vals.get(op["id"], {}))
            if err:
                param_errors.append(f"{op['label']}: {err}")
            else:
                final_commands[op["id"]] = cmd
    if param_errors:
        def deny2():
            yield f"data: {json.dumps({'type': 'error', 'text': '  Refused: invalid parameter value(s):'})}\n\n"
            for e in param_errors:
                yield f"data: {json.dumps({'type': 'error', 'text': f'    - {e}'})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'success': False})}\n\n"
        return Response(stream_with_context(deny2()), mimetype="text/event-stream")

    _stop_flag.clear()

    now       = datetime.datetime.now()
    ts        = now.strftime("%Y%m%d_%H%M%S")
    safe_host = re.sub(r"[^\w\-.]", "_", hostname)
    log_path  = LOG_DIR / f"AdminTool_{safe_host}_{ts}.log"

    def generate():
        def ev(data_dict):
            return f"data: {json.dumps(data_dict)}\n\n"

        log_lines = []

        def lf(text):
            log_lines.append(text)

        header_txt = [
            "=" * 60,
            f"  PC ADMIN & PERFORMANCE TOOL  v3.7  -- Web-Service Edition",
            f"  {COPYRIGHT.splitlines()[0]}",
            "=" * 60,
            f"  Target   : {hostname}",
            f"  Username : {username}",
            f"  Transport: {transport}",
            f"  Date/Time: {now.strftime('%Y-%m-%d %H:%M:%S')}",
            f"  Tasks    : {len(selected)} selected",
            f"  Log File : {log_path.name}",
            "=" * 60,
            "",
        ]
        for line in header_txt:
            lf(line)
            yield ev({"type": "header" if "=" in line or "TOOL" in line else
                               "info" if "Target" in line or "Username" in line or
                                         "Date" in line or "Tasks" in line or "Log" in line else
                               "dim", "text": line})

        # Create WinRM session
        try:
            session = make_session(hostname, username, password, transport)
            # Quick test
            _, stderr_test, ok_test = run_remote_ps(session, 'Write-Output "SESSION_OK"')
            if not ok_test:
                msg = f"  ✗ Cannot establish session: {stderr_test}"
                yield ev({"type": "error", "text": msg})
                lf(msg)
                yield ev({"type": "done", "success": False, "log": log_path.name})
                with open(log_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(log_lines))
                return
            yield ev({"type": "success", "text": "  ✓ WinRM session established"})
            lf("  Session established")
        except AuthenticationError:
            msg = "  ✗ AUTHENTICATION FAILED — check username/password and domain format"
            yield ev({"type": "error", "text": msg})
            lf(msg)
            yield ev({"type": "done", "success": False})
            return
        except Exception as e:
            msg = f"  ✗ Cannot connect: {e}\n  Ensure WinRM is enabled: Enable-PSRemoting -Force"
            yield ev({"type": "error", "text": msg})
            lf(msg)
            yield ev({"type": "done", "success": False})
            return

        yield ev({"type": "blank"})

        cur_host = hostname   # v3.7: follows the target if its address changes
        total = len(selected)
        for idx, task in enumerate(selected):
            if _stop_flag.is_set():
                yield ev({"type": "warning", "text": "\n  ⚠ STOPPED by user request"})
                lf("  STOPPED")
                break

            pct = int((idx / total) * 100)
            yield ev({"type": "progress", "value": pct})
            yield ev({"type": "task_start",
                      "text": f"▶ [{idx+1}/{total}]  {task['label']}",
                      "idx": idx, "total": total,
                      "label": task["label"]})
            yield ev({"type": "dim",  "text": f"    Category : {task['category']}"})
            yield ev({"type": "dim",  "text": f"    Purpose  : {task['description']}"})
            yield ev({"type": "dim",  "text": f"    {'─'*50}"})

            lf(f"\n▶ [{idx+1}/{total}]  {task['label']}")
            lf(f"    {task['description']}")
            lf(f"    {'─'*50}")

            # rt_open_computer_management: a Flask server cannot open a window
            # on a REMOTE browser's screen -- that is a hard OS-level limit,
            # not a design choice. What it CAN do, exactly like the desktop
            # editions already do "on your own PC", is launch MMC locally on
            # the machine actually running this Python process. For the
            # common case -- someone running the Web edition on their own
            # Windows PC and browsing to localhost -- that IS their own PC,
            # so this now behaves identically to the desktop editions. If
            # this service is hosted on a different machine than the one
            # browsing to it, the window opens there instead; said plainly
            # below rather than silently launching somewhere unexpected.
            if task["id"] == "rt_open_computer_management":
                if platform.system() == "Windows":
                    try:
                        subprocess.Popen(["mmc.exe", "compmgmt.msc", f"/computer:\\\\{hostname}"])
                        msg = (f"  Launched: mmc.exe compmgmt.msc /computer:\\\\{hostname}\n"
                               f"  This opened on the machine HOSTING this web service. If you are\n"
                               f"  browsing from that same PC (e.g. localhost), it's on your screen now.\n"
                               f"  If you're browsing from a DIFFERENT computer than the one hosting\n"
                               f"  this service, it opened there instead -- run the command above\n"
                               f"  yourself on your own PC to get a window on your own screen.")
                    except Exception as e:
                        msg = (f"  Could not launch it automatically ({e}).\n"
                               f"  Run this yourself on the machine hosting this service:\n"
                               f"    mmc.exe compmgmt.msc /computer:\\\\{hostname}")
                else:
                    msg = (f"  This service is hosted on {platform.system()}, which cannot run\n"
                           f"  mmc.exe (Windows-only) -- nothing was launched.\n"
                           f"  Run this yourself, on a Windows PC:\n"
                           f"    mmc.exe compmgmt.msc /computer:\\\\{hostname}")
                for line in msg.splitlines():
                    yield ev({"type": "info", "text": f"    {line}"})
                    lf(f"    {line}")
                continue

            t_start = time.time()
            cmd_text = final_commands.get(task["id"], task["command"])
            if task.get("needs_cred"):
                cmd_text = inject_credentials(cmd_text, username, password)

            if task.get("detached") or task.get("net_disruptive"):
                # v3.7: detached job + poll-and-reconnect (see the engine block)
                alt_hosts = []
                if task["id"] == "rt_set_static_ip":
                    new_ip = (param_vals.get(task["id"], {}).get("IP") or "").strip()
                    if new_ip and new_ip != cur_host:
                        alt_hosts.append(new_ip)
                stdout, stderr, success, used_host = "", "", False, cur_host
                for kind, payload in run_detached_gen(
                        cur_host, username, password, transport, cmd_text, _stop_flag,
                        alt_hosts=alt_hosts, max_wait=task.get("wait_sec", 300)):
                    if kind == "result":
                        stdout, stderr, success, used_host = payload
                        break
                    tag_ = {"info": "info", "ok": "success", "warn": "warning", "err": "error"}.get(kind, "info")
                    yield ev({"type": tag_, "text": f"    {payload}"})
                    lf(f"    {payload}")
                if used_host and used_host != cur_host:
                    msg = f"    Target address is now {used_host} (was {cur_host}) -- using it for the remaining tasks"
                    yield ev({"type": "success", "text": msg})
                    lf(msg)
                    cur_host = used_host
                    try:
                        session = make_session(cur_host, username, password, transport)
                    except Exception:
                        pass
            else:
                stdout, stderr, success = run_remote_ps(session, cmd_text, task["label"])

                # Dropped/timed-out session: reconnect. Only a NON-sensitive task is
                # retried -- re-running a sensitive one (rename, restart, delete...)
                # after an unknown outcome could do it twice.
                if not success and stderr.startswith(("TRANSPORT_ERR", "TIMEOUT_ERR")):
                    yield ev({"type": "warning", "text": "    Connection lost -- reconnecting..."})
                    lf("    Connection lost -- reconnecting...")
                    try:
                        session = make_session(cur_host, username, password, transport)
                        _, _, reconn_ok = run_remote_ps(session, 'Write-Output "RECONNECTED"')
                        if reconn_ok and task.get("danger"):
                            m1 = ("    Session reconnected. This task is sensitive, so it was NOT re-run "
                                  "automatically -- its outcome is unknown: check the target, then re-run if needed.")
                            yield ev({"type": "warning", "text": m1})
                            lf(m1)
                        elif reconn_ok:
                            yield ev({"type": "success", "text": "    Session reconnected -- retrying task"})
                            lf("    Session reconnected -- retrying task")
                            stdout, stderr, success = run_remote_ps(session, cmd_text, task["label"])
                        else:
                            yield ev({"type": "error", "text": "    Reconnect failed"})
                            lf("    Reconnect failed")
                    except Exception as e:
                        yield ev({"type": "error", "text": f"    Reconnect failed: {e}"})
                        lf(f"    Reconnect failed: {e}")

            elapsed = round(time.time() - t_start, 1)

            # Output lines with colour hints
            if stdout.strip():
                for line in stdout.splitlines():
                    line = line.rstrip()
                    if not line:
                        continue
                    lo = line.lower()
                    tag = ("success" if any(k in lo for k in ["freed","cleared","complete","restarted","ok","pass","removed","deleted","✓"]) else
                           "warning" if any(k in lo for k in ["⚠","warn","skip","not found","empty","already","none","cannot"]) else
                           "error"   if any(k in lo for k in ["error","fail","denied","exception"]) else
                           "output")
                    yield ev({"type": tag, "text": f"    {line}"})
                    lf(f"    {line}")
            else:
                # No stdout at all. If stderr has a specific reason, let
                # that speak for itself below rather than burying it under
                # four generic guesses that usually aren't the real cause.
                if not stderr.strip():
                    yield ev({"type": "warning",
                              "text": "    ⚠ No output received. Possible reasons:"})
                    yield ev({"type": "dim",
                              "text": "      • Insufficient permissions on remote host"})
                    yield ev({"type": "dim",
                              "text": "      • Path C:\\Users not accessible under current credentials"})
                    yield ev({"type": "dim",
                              "text": "      • PowerShell Execution Policy restriction on target"})
                    yield ev({"type": "dim",
                              "text": "      • Operation completed with nothing to process (already clean)"})
                lf("    (no output)")

            if stderr.strip():
                for line in stderr.splitlines():
                    if not line.strip():
                        continue
                    # Translate common error codes to friendly messages
                    if "CRED_ERR" in line:
                        line = "⚠ Authentication failed — re-check credentials"
                    elif "TRANSPORT_ERR" in line:
                        line = "⚠ WinRM transport error — connection may have dropped"
                    elif "TIMEOUT_ERR" in line:
                        line = "⚠ Task timed out (>170s) — operation may still be running"
                    elif "AccessDenied" in line or "Access is denied" in line:
                        line = "⚠ Access denied — target requires elevated/admin permissions"
                    yield ev({"type": "error", "text": f"    ✗ {line}"})
                    lf(f"    ✗ {line}")

            status = "✓ Completed" if success else "⚠ Completed with errors"
            yield ev({"type": "success" if success else "warning",
                      "text": f"    {status} in {elapsed}s"})
            yield ev({"type": "blank"})
            lf(f"    {status} in {elapsed}s\n")

        yield ev({"type": "progress", "value": 100})

        stopped = _stop_flag.is_set()
        footer_txt = [
            "",
            "=" * 60,
            f"  {'STOPPED BY USER' if stopped else 'ALL TASKS COMPLETED ✓'}",
            f"  Finished : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"  Log saved: {log_path.name}",
            f"  {COPYRIGHT.splitlines()[0]}",
            "=" * 60,
        ]
        for line in footer_txt:
            lf(line)
            yield ev({"type": "warning" if stopped and "STOPPED" in line else
                               "success" if "COMPLETED" in line else
                               "dim" if "Log" in line or "©" in line else
                               "header",
                      "text": line})

        yield ev({"type": "done", "success": not stopped, "log": log_path.name})

        # Write log file
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("\n".join(log_lines))

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache",
                 "X-Accel-Buffering": "no",
                 "Connection": "keep-alive"},
    )


@app.route("/api/stop", methods=["POST"])
def stop():
    _stop_flag.set()
    return jsonify({"status": "stopping"})


@app.route("/api/logs")
def list_logs():
    try:
        logs = sorted(LOG_DIR.glob("*.log"),
                      key=lambda p: p.stat().st_mtime, reverse=True)
        return jsonify([{"name": l.name,
                         "size": l.stat().st_size,
                         "modified": datetime.datetime.fromtimestamp(
                             l.stat().st_mtime).strftime("%Y-%m-%d %H:%M")}
                        for l in logs[:30]])
    except Exception:
        return jsonify([])


def _lan_ip():
    """Best-effort detection of this host's LAN IP for the startup banner."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


if __name__ == "__main__":
    lan_ip = _lan_ip()
    print("=" * 60)
    print("  PC Admin & Performance Tool  v3.7  -- Web-Service Edition")
    print(f"  {COPYRIGHT.splitlines()[0]}")
    print("=" * 60)
    print(f"  Local   : http://localhost:{SERVICE_PORT}")
    print(f"  Network : http://{lan_ip}:{SERVICE_PORT}   (reachable from any")
    print("            host on the same allowed subnet)")
    print(f"  Logs    : {LOG_DIR}")
    print("=" * 60)
    # v3.3: app.run() used to be called bare. Tested (not assumed) what this
    # Flask/Werkzeug version actually does on a startup bind failure (e.g.
    # this same port already held by this tool's own Windows Service, if it
    # was separately installed via install_service.bat): Werkzeug prints its
    # own short diagnostic to stderr and raises SystemExit(1) itself -- it
    # does NOT let a raw OSError reach this code, and does NOT print a Python
    # traceback (a first, discarded version of this fix caught OSError here,
    # which would never have actually fired -- verified with a same-process
    # reproduction before shipping this version, not left as a guess). A
    # normal Ctrl+C, also tested the same way, is swallowed inside app.run()
    # itself, which then simply returns -- no exception reaches here at all.
    # Combined with run_console_testmode.bat having NO pause after this line,
    # whichever of those two things happened, the window closed before
    # anyone could read the reason -- reported as "opens and closes
    # immediately, no response on localhost". Fixed at both levels: this
    # adds a plain-English, tool-specific explanation on top of Werkzeug's
    # own message, AND every launcher .bat now guarantees the window stays
    # open regardless (defense in depth -- either fix alone would have been
    # enough; both together mean a future mistake in one place doesn't bring
    # back the original symptom).
    try:
        app.run(host="0.0.0.0", port=SERVICE_PORT, debug=False, threaded=True)
    except SystemExit as e:
        if e.code not in (None, 0):
            print("=" * 60)
            print(f"  COULD NOT START -- port {SERVICE_PORT} is not available.")
            print("=" * 60)
            print("  Most likely cause: the Windows Service version of this same")
            print("  tool (installed earlier via install_service.bat) is ALREADY")
            print("  RUNNING in the background on this same port. You do not need")
            print("  to run this test-mode window at the same time as the service")
            print("  -- either open the URL above directly (the service is already")
            print("  serving it), or stop the service first with:")
            print("      net stop PCAdminTool")
            print("  and then run this file again.")
            print()
            print("  If that's not it, something else on this machine is using")
            print(f"  port {SERVICE_PORT} -- find out what with:")
            print(f"      netstat -ano | findstr :{SERVICE_PORT}")
        raise
    else:
        print()
        print("  Stopped.")
