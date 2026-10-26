#!/usr/bin/env python3
"""
================================================================================
  PC Admin & Performance Troubleshooting Tool  v3.8  — Web-Service Edition
  © 2024-2026 Abdullah | All Rights Reserved
  Contact : abuabdullah.be@outlook.com
  Unauthorized copying, modification or redistribution is strictly prohibited.

  Runs as a standalone network service on PORT 3030 -- reachable from any
  host on the same allowed subnet at http://<this-machine-IP>:3030
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

  v3.8 (port 3038 -> 3030):
    CHG  FINAL v3.8 DESIGN (supersedes the "detached" approach for network tasks):
         Set Static IP / Set DHCP / Flush DNS / Reset TCP-IP / adapter restarts run
         INLINE again exactly like v3.6 (the method that worked). A dropped
         connection is reported as expected, the change is NOT repeated, the tool
         reconnects (also on the NEW IP) and prints the target's current IP/gateway/
         DNS. DISM / CHKDSK keep the detached engine.
    NEW  Category "Network Push": Push: Set Static IP / Set DHCP / Flush DNS /
         Reset TCP-IP (command is sent, the tool does not wait for the result:
         "<action> cmd pushed to the target machine") and "Ping Host" (continuous
         until Stop; shows which IP/name answers; needs no WinRM login).
         90 operations in total.
    FIX  "Set Static IP / Set DHCP / Flush DNS / Reset TCP/IP / adapter restart"
         stopped at once with
             PCAT_LAUNCH_FAIL:2
             Could not start the detached task on the target
         Root cause: the v3.7 detached-run engine started the background task
         with ONE method only -- Invoke-CimMethod Win32_Process.Create. Return
         code 2 is Windows "Access denied": on many targets that WMI call is
         refused when it is made from inside a WinRM session (network-logon
         token, security software, WMI/DCOM permissions), so the task never
         started and no report could be produced. Nothing else was tried.
         The launcher now tries FIVE methods in order and stops at the first
         that works; every one of them creates a process OUTSIDE the WinRM
         shell, so it still survives the network drop:
           1. one-shot Scheduled Task running as SYSTEM (Register-/Start-
              ScheduledTask) -- the most reliable from a remote session
           2. Win32_Process.Create via CIM          (the v3.7 method)
           3. Win32_Process.Create via WMI (Invoke-WmiMethod)
           4. schtasks.exe one-shot task as SYSTEM   (older Windows)
           5. hidden Start-Process                    (last resort)
         The log now says which method started the task ("Started on the target
         via: ..."). If ALL fail, the raw "PCAT_LAUNCH_FAIL:2" line is replaced
         by a readable report: one line per method with its decoded reason
         (return code 2 = Access denied, 3 = Insufficient privilege, ...), the
         account the target saw and whether it is an administrator, and the
         specific fix (non-admin / remote UAC -> LocalAccountTokenFilterPolicy;
         admin -> check Task Scheduler + WMI services, EDR, batch-logon policy).
         The scheduled task and the temporary files are removed after the task
         reports (cleanup also deletes the task). A launched marker now wins over
         the "ok" flag of the launch call, so a harmless stream warning cannot
         discard a task that did start. The task body runs as SYSTEM for methods
         1 and 4 (netsh / ipconfig / DISM / chkdsk are unaffected by this).

  v3.7 (port 3037 -> 3038):
    FIX  PC RENAME failed on every domain-joined target with "Access is denied"
         (all three variants). Root cause: Rename-Computer on a domain member
         must authenticate to a domain controller itself, but a WinRM/NTLM
         session only carries a network logon that cannot be forwarded to the
         DC (the double hop). The payload now rebuilds the username/password
         you connected with as a real PSCredential INSIDE the remote session
         and calls Rename-Computer -DomainCredential; if that fails it tries
         the WMI Win32_ComputerSystem.Rename method with the same credential
         and prints the decoded reason (2224 = name already exists in AD,
         1326 = logon failure, 5 = no rights, ...). The password travels only
         inside the encrypted PSRP channel as base64, is removed from the
         remote variable immediately and is never printed, logged or placed
         on a command line (verified by tests that search every output, log
         and script for it). Restart now uses "shutdown /r /t 15" so the
         reply returns before the target goes down (Rename-Computer -Restart
         killed the session mid-reply).
         - Domain-Joined: refuses with a clear message on a workgroup target.
         - Workgroup/Local: refuses on a domain member instead of silently
           desynchronising its AD computer account; explains the remote-UAC
           (LocalAccountTokenFilterPolicy) cause for local-account failures.
         - WMIC/Legacy: uses wmic.exe only on workgroup targets that still
           have it; otherwise automatically uses the same WMI method through
           CIM (no password on a wmic command line, works on Win11 24H2+).
    FIX  The app became unusable after network-changing tasks (flush DNS, set
         static IP, set DHCP, reset TCP/IP, restart/disable adapters) until
         restarted. Root cause: the target's network dropped under the open
         WinRM call; pypsrp then waited on the dead socket (read timeout 180 s
         retried 5 times) and the session was never recovered. Those tasks now
         run DETACHED on the target (Win32_Process.Create, outside the WinRM
         shell, so it survives), write their output to a file, and the tool
         polls with short timeouts and reconnects with back-off (8 attempts
         x 4 s, repeated until the wait limit, 300 s) and returns the REAL
         output. For Set Static IP the tool also tries the NEW address, and
         later tasks continue on whichever address answered.
    NEW  The same detached engine runs very long tasks, so they no longer die
         at the 170 s operation timeout: DISM RestoreHealth, DISM component
         cleanup and CHKDSK online scan (wait limit 60 min).
    NEW  Reboot-class tasks (Force Restart, Force Sign-out & Restart, Full
         Soft-Recycle with auto-restart on, rename with auto-restart on) now
         treat the connection closing as the EXPECTED result, and the tasks
         that follow in the same run are skipped with a clear message instead
         of failing one by one. Their shutdown is now issued with a 3-second
         delay (/t 3) so the reply is delivered first.
    NEW  VSS: "Resize VSS Shadow Storage (Max Size)" -- vssadmin resize
         shadowstorage /maxsize= with a validated size (10%, 20GB, 51200MB,
         UNBOUNDED), report before and after. New param kind: vsssize.
    NEW  DISM: RestoreHealth; Component Store Cleanup (Analyze + StartComponentCleanup,
         optional /ResetBase checkbox).
    NEW  Performance (WMIC replacements, WMIC is gone on Win11 24H2+): Hardware
         Inventory via CIM, Retrim SSD (Optimize-Volume -ReTrim, skips HDD),
         Verify WMI Repository (winmgmt /verifyrepository), Rebuild Performance
         Counters (lodctr /R). Disk: CHKDSK Online Scan (read-only).
    NEW  Category "Admin Consoles" (11 launchers, 18 more operations in total
         than v3.6 -> 85): Computer Management (moved here), Disk Management,
         Device Manager (read-only on Win8+/2012+ -- Microsoft removed remote
         device changes), Services, Event Viewer, Shared Folders, C$ admin
         share, Firewall with Advanced Security (guided: wf.msc has no remote
         switch), Remote PowerShell window (Enter-PSSession), Remote Command
         Prompt (winrs), Remote Desktop with the credential pre-loaded (the
         only way to use GUI-only tools: Device Manager with changes, Disk
         Cleanup, Defrag GUI, Network Connections). They open on the machine
         HOSTING this service -- a web server cannot open a window on a remote
         browser. Authentication: "net use" to the target's IPC$ share for MMC/Explorer,
         cmdkey TERMSRV/host for RDP, environment hand-over for PowerShell,
         prompt for winrs. Hostnames are validated (no argument injection).

  Port bumps alongside every versioned release are a standing project
  convention (see the reference doc) -- update any saved bookmarks, firewall
  rules, and the systemd/service files that reference the old port.
================================================================================
"""
from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from pypsrp.client import Client
from pypsrp.exceptions import AuthenticationError, WinRMTransportError, WSManFaultError
import requests.exceptions
import json, datetime, socket, re, os, time, threading, subprocess, platform, base64, secrets
from pathlib import Path

app = Flask(__name__)

SERVICE_PORT = 3030

# Logs/files live on the hosting machine (Linux, Windows, or Windows Server),
# in a "logs" folder next to this script -- not tied to a Docker container.
BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

_stop_flag  = threading.Event()
_run_lock   = threading.Lock()

COPYRIGHT = (
    "© 2024-2026 Abdullah | PC Admin & Performance Tool v3.8 | All Rights Reserved\n"
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
shutdown.exe /r /f /t 3
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
        "description": "shutdown /g /f /t 3 -- restarts and reopens registered apps, distinct from a plain restart",
        "command": r"""
Write-Output "  Signing out and restarting now (shutdown /g) -- Windows will try to reopen registered apps on next login."
Write-Output "  Any unsaved work WILL be lost. The connection will drop now; this is expected."
shutdown /g /f /t 3
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
    shutdown /g /f /t 3
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

$prefix = 0
foreach ($o in $mask.Split('.')) { $prefix += ([Convert]::ToString([int]$o, 2).ToCharArray() | Where-Object { $_ -eq '1' }).Count }

function Get-Missing {
    $m = @()
    $a = Get-NetIPAddress -InterfaceAlias $adapterName -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object { $_.IPAddress -eq $ip } | Select-Object -First 1
    if (-not $a) { $m += 'IP address' }
    elseif ($a.PrefixLength -ne $prefix) { $m += 'subnet mask' }
    $c = Get-NetIPConfiguration -InterfaceAlias $adapterName -ErrorAction SilentlyContinue
    if (-not (@($c.IPv4DefaultGateway.NextHop) -contains $gw)) { $m += 'default gateway' }
    $d = @((Get-DnsClientServerAddress -InterfaceAlias $adapterName -AddressFamily IPv4 -ErrorAction SilentlyContinue).ServerAddresses)
    if ($dns1 -and $d[0] -ne $dns1) { $m += 'primary DNS' }
    if ($dns2 -and $d[1] -ne $dns2) { $m += 'secondary DNS' }
    return $m
}

function Set-AllAtOnce {
    # IP + mask + gateway + DNS are pushed back-to-back in ONE pass (no output handling,
    # no waiting between them) so the connection drop cannot leave a half-applied setup.
    $o1 = netsh interface ipv4 set address name="$adapterName" static $ip $mask $gw 2>&1
    $o2 = $null
    $o3 = $null
    if ($dns1) { $o2 = netsh interface ipv4 set dnsservers name="$adapterName" static $dns1 primary validate=no 2>&1 }
    if ($dns2) { $o3 = netsh interface ipv4 add dnsservers name="$adapterName" $dns2 index=2 validate=no 2>&1 }
    foreach ($x in @($o1) + @($o2) + @($o3)) { if ("$x".Trim()) { Write-Output "  $x" } }
}

Write-Output "  Target configuration on '$adapterName': $ip / $mask (/$prefix), gateway $gw, DNS $dns1 $dns2"
$haveCheck = [bool](Get-Command Get-NetIPAddress -ErrorAction SilentlyContinue)
if (-not $haveCheck) {
    Set-AllAtOnce
    Start-Sleep -Seconds 3
} else {
    $missing = @(Get-Missing)
    if ($missing.Count -eq 0) {
        Write-Output "  Already configured exactly like this -- nothing to change."
    } else {
        $attempt = 0
        while ($attempt -lt 3 -and $missing.Count -gt 0) {
            $attempt++
            Write-Output "  Applying IP, mask, gateway and DNS together (attempt $attempt of 3)..."
            Set-AllAtOnce
            $until = (Get-Date).AddSeconds(20)
            do {
                Start-Sleep -Seconds 2
                $missing = @(Get-Missing)
            } while ($missing.Count -gt 0 -and (Get-Date) -lt $until)
            if ($missing.Count -gt 0) { Write-Output "  Not applied yet: $($missing -join ', ')" }
        }
    }
    if ($missing.Count -eq 0) {
        Write-Output "  VERIFIED: IP address, subnet mask, gateway and DNS all match the requested values."
    } else {
        Write-Output "  WARNING: after 3 attempts these are still not applied: $($missing -join ', ')"
    }
}

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
        "command": r"""$adapterName = "{{ADAPTER}}"
$nic = Get-NetAdapter -Name $adapterName -ErrorAction SilentlyContinue
if (-not $nic) {
    Write-Output "  Adapter '$adapterName' not found. Available adapters:"
    Get-NetAdapter -ErrorAction SilentlyContinue | ForEach-Object { Write-Output "    $($_.Name)" }
    return
}
Write-Output "  Switching '$adapterName' to DHCP (address + DNS together)..."
$o1 = netsh interface ipv4 set address name="$adapterName" source=dhcp 2>&1
$o2 = netsh interface ipv4 set dnsservers name="$adapterName" source=dhcp 2>&1
foreach ($x in @($o1) + @($o2)) { if ("$x".Trim()) { Write-Output "  $x" } }
ipconfig /renew "$adapterName" | Out-Null
if (Get-Command Get-NetIPInterface -ErrorAction SilentlyContinue) {
    $until = (Get-Date).AddSeconds(25)
    $ok = $false
    do {
        Start-Sleep -Seconds 2
        $i = Get-NetIPInterface -InterfaceAlias $adapterName -AddressFamily IPv4 -ErrorAction SilentlyContinue
        $a = Get-NetIPAddress -InterfaceAlias $adapterName -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object { $_.IPAddress -notlike '169.254.*' } | Select-Object -First 1
        if ($i -and $i.Dhcp -eq 'Enabled' -and $a) { $ok = $true }
    } while (-not $ok -and (Get-Date) -lt $until)
    if ($ok) { Write-Output "  VERIFIED: DHCP is enabled and a lease was obtained ($($a.IPAddress))." }
    else { Write-Output "  WARNING: DHCP is set, but no lease was obtained within 25 s (no DHCP server reachable yet?)." }
}
Write-Output "  === RESULTING CONFIGURATION ==="
Get-NetIPConfiguration -InterfaceAlias $adapterName -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Output "  IPv4 Address : $($_.IPv4Address.IPAddress)"
    Write-Output "  Gateway      : $($_.IPv4DefaultGateway.NextHop)"
    Write-Output "  DNS Servers  : $($_.DNSServer.ServerAddresses -join ', ')"
}
"""
    },
    {
        "id": "rt_rename_pc_domain",
        "danger": True,
        "needs_cred": True,
        "label": "Rename Computer (Domain-Joined)",
        "category": "Remote Tools",
        "description": "Renames a domain member using the username/password you connected with as an explicit domain credential (no CredSSP needed); restart optional",
        "params": [
            {"key": "NEW_NAME", "kind": "computername", "label": "New Computer Name", "required": True},
            {"key": "AUTO_RESTART", "kind": "bool", "label": "Automatically restart when done",
             "required": True, "default": "true",
             "help": "Unchecked: rename now, restart later yourself (name won't take effect until then)"}
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
"""
    },
    {
        "id": "rt_rename_pc_workgroup",
        "danger": True,
        "needs_cred": True,
        "label": "Rename Computer (Workgroup/Local)",
        "category": "Remote Tools",
        "description": "Local rename for NON-domain targets (refuses on a domain member and says so); restart optional",
        "params": [
            {"key": "NEW_NAME", "kind": "computername", "label": "New Computer Name", "required": True},
            {"key": "AUTO_RESTART", "kind": "bool", "label": "Automatically restart when done",
             "required": True, "default": "true",
             "help": "Unchecked: rename now, restart later yourself (name won't take effect until then)"}
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
"""
    },
    {
        "id": "rt_rename_pc_wmic_legacy",
        "danger": True,
        "needs_cred": True,
        "label": "Rename Computer via WMIC (Legacy -- Manual Restart Required)",
        "category": "Remote Tools",
        "description": "WMIC where present; automatically uses the same WMI rename method via CIM when WMIC is removed (Win11 24H2+) or the target is domain-joined",
        "params": [
            {"key": "NEW_NAME", "kind": "computername", "label": "New Computer Name", "required": True}
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
"""
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

    # ─── v3.7 additions ──────────────────────────────────────────────────────
    {
        "id": 'rt_vss_resize_storage',
        "danger": True,
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
"""
    },
    {
        "id": 'run_dism_restorehealth',
        "danger": True,
        "label": 'DISM RestoreHealth (Repair Component Store)',
        "category": 'Windows Health',
        "description": 'DISM /Online /Cleanup-Image /RestoreHealth -- repairs a corrupt component store from Windows Update; can take 10-30 min (runs detached, tool waits)',
        "long": True,
        "command": r"""
Write-Output "  Running DISM RestoreHealth (needs the target to reach Windows Update or a repair source)..."
DISM /Online /Cleanup-Image /RestoreHealth 2>&1 | ForEach-Object { if ($_ -and "$_".Trim()) { Write-Output "  $_" } }
Write-Output "  DISM exit code: $LASTEXITCODE  (0 = success, 3010 = success but reboot needed)"
Write-Output "  Tip: run 'Run System File Checker (SFC)' afterwards."
"""
    },
    {
        "id": 'dism_component_cleanup',
        "danger": True,
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
"""
    },
    {
        "id": 'perf_hardware_report_cim',
        "danger": False,
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
"""
    },
    {
        "id": 'perf_trim_ssd',
        "danger": False,
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
"""
    },
    {
        "id": 'perf_wmi_verify_repository',
        "danger": False,
        "label": 'Verify WMI Repository Health (winmgmt)',
        "category": 'Performance',
        "description": 'winmgmt /verifyrepository -- a corrupt WMI repository makes CIM/WMI-based operations and monitoring slow or failing (read-only check)',
        "command": r"""
Write-Output "  Verifying the WMI repository (read-only)..."
$r = winmgmt /verifyrepository 2>&1
$r | ForEach-Object { Write-Output "  $_" }
if (($r | Out-String) -match 'inconsistent') { Write-Output "  Repository is INCONSISTENT -- consider 'winmgmt /salvagerepository' on the target (Admin), then a restart." }
"""
    },
    {
        "id": 'perf_rebuild_perf_counters',
        "danger": True,
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
"""
    },
    {
        "id": 'chkdsk_online_scan',
        "danger": False,
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
"""
    },

    # ─── 🖥️ ADMIN CONSOLES (v3.7) ───────────────────────────────────────────
    {
        "id": 'rt_open_computer_management',
        "danger": False,
        "label": 'Open Computer Management (Connected to Target)',
        "category": 'Admin Consoles',
        "description": 'mmc compmgmt.msc /computer:\\\\<target> -- Disk Management, Device Manager (read-only), Event Viewer, Services, Shared Folders, Task Scheduler in one console',
        "command": r"""
# Handled by the host application (launch_console) -- never sent to the target.
Write-Output "  (local console launcher)"
"""
    },
    {
        "id": 'ac_open_disk_management',
        "danger": False,
        "label": 'Open Disk Management (Connected to Target)',
        "category": 'Admin Consoles',
        "description": 'mmc diskmgmt.msc /computer:\\\\<target> -- partitions, volumes, drive letters, extend/shrink',
        "command": r"""
# Handled by the host application (launch_console) -- never sent to the target.
Write-Output "  (local console launcher)"
"""
    },
    {
        "id": 'ac_open_device_manager',
        "danger": False,
        "label": 'Open Device Manager (Connected to Target, Read-Only on Win8+)',
        "category": 'Admin Consoles',
        "description": 'mmc devmgmt.msc /computer:\\\\<target> -- Windows 8 / Server 2012 and later only let you VIEW remote devices; use Remote Desktop to change drivers',
        "command": r"""
# Handled by the host application (launch_console) -- never sent to the target.
Write-Output "  (local console launcher)"
"""
    },
    {
        "id": 'ac_open_services',
        "danger": False,
        "label": 'Open Services Console (Connected to Target)',
        "category": 'Admin Consoles',
        "description": 'mmc services.msc /computer:\\\\<target> -- start/stop/configure services on the target',
        "command": r"""
# Handled by the host application (launch_console) -- never sent to the target.
Write-Output "  (local console launcher)"
"""
    },
    {
        "id": 'ac_open_event_viewer',
        "danger": False,
        "label": 'Open Event Viewer (Connected to Target)',
        "category": 'Admin Consoles',
        "description": "mmc eventvwr.msc /computer:<target> -- browse the target's Windows logs",
        "command": r"""
# Handled by the host application (launch_console) -- never sent to the target.
Write-Output "  (local console launcher)"
"""
    },
    {
        "id": 'ac_open_shared_folders',
        "danger": False,
        "label": 'Open Shared Folders Console (Connected to Target)',
        "category": 'Admin Consoles',
        "description": 'mmc fsmgmt.msc /computer:\\\\<target> -- shares, open sessions, open files',
        "command": r"""
# Handled by the host application (launch_console) -- never sent to the target.
Write-Output "  (local console launcher)"
"""
    },
    {
        "id": 'ac_open_admin_share',
        "danger": False,
        "label": 'Open C$ Admin Share in File Explorer',
        "category": 'Admin Consoles',
        "description": "explorer \\\\<target>\\C$ -- browse the target's system drive using the supplied admin credentials",
        "command": r"""
# Handled by the host application (launch_console) -- never sent to the target.
Write-Output "  (local console launcher)"
"""
    },
    {
        "id": 'ac_open_firewall',
        "danger": False,
        "label": 'Open Windows Firewall with Advanced Security (Guided)',
        "category": 'Admin Consoles',
        "description": 'wf.msc has no remote switch -- opens the console and tells you the 3 clicks to connect it to the target',
        "command": r"""
# Handled by the host application (launch_console) -- never sent to the target.
Write-Output "  (local console launcher)"
"""
    },
    {
        "id": 'ac_open_remote_shell',
        "danger": False,
        "label": 'Open Remote PowerShell Window on Target (Enter-PSSession)',
        "category": 'Admin Consoles',
        "description": 'New PowerShell window already connected to the target -- run any admin command (cleanmgr /sagerun, defrag, netsh, ...) there',
        "command": r"""
# Handled by the host application (launch_console) -- never sent to the target.
Write-Output "  (local console launcher)"
"""
    },
    {
        "id": 'ac_open_remote_cmd',
        "danger": False,
        "label": 'Open Remote Command Prompt on Target (winrs)',
        "category": 'Admin Consoles',
        "description": 'New cmd window running on the target through WinRM (winrs) -- asks for the password in that window',
        "command": r"""
# Handled by the host application (launch_console) -- never sent to the target.
Write-Output "  (local console launcher)"
"""
    },
    {
        "id": 'ac_open_rdp',
        "danger": False,
        "label": 'Open Remote Desktop to Target (Credentials Pre-Loaded)',
        "category": 'Admin Consoles',
        "description": 'mstsc /v:<target> with the supplied credentials stored -- the only way to use GUI-only tools remotely: Device Manager (full), Disk Cleanup, Defrag, Firewall, Network Connections',
        "command": r"""
# Handled by the host application (launch_console) -- never sent to the target.
Write-Output "  (local console launcher)"
"""
    },
]

# ── v3.8 (DC-45): "Network Push" category ────────────────────────────────────
# Same bodies as the proven network tasks, but the tool only PUSHES the command and
# does not wait for the result (push_run). "Ping Host" watches the target until Stop.
def _np_clone(src_id, new_id, label, description, command=None):
    src = next(o for o in OPERATIONS if o["id"] == src_id)
    o = dict(src)
    o.update({"id": new_id, "label": label, "category": "Network Push",
              "description": description, "danger": True})
    o["params"] = [dict(p) for p in src.get("params", [])]
    if command is not None:
        o["command"] = command
    if not o["params"]:
        o.pop("params")
    return o

_NP_STATIC_BODY = r"""
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

$prefix = 0
foreach ($o in $mask.Split('.')) { $prefix += ([Convert]::ToString([int]$o, 2).ToCharArray() | Where-Object { $_ -eq '1' }).Count }

function Get-Missing {
    $m = @()
    $a = Get-NetIPAddress -InterfaceAlias $adapterName -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object { $_.IPAddress -eq $ip } | Select-Object -First 1
    if (-not $a) { $m += 'IP address' }
    elseif ($a.PrefixLength -ne $prefix) { $m += 'subnet mask' }
    $c = Get-NetIPConfiguration -InterfaceAlias $adapterName -ErrorAction SilentlyContinue
    if (-not (@($c.IPv4DefaultGateway.NextHop) -contains $gw)) { $m += 'default gateway' }
    $d = @((Get-DnsClientServerAddress -InterfaceAlias $adapterName -AddressFamily IPv4 -ErrorAction SilentlyContinue).ServerAddresses)
    if ($dns1 -and $d[0] -ne $dns1) { $m += 'primary DNS' }
    if ($dns2 -and $d[1] -ne $dns2) { $m += 'secondary DNS' }
    return $m
}

function Set-AllAtOnce {
    # IP + mask + gateway + DNS are pushed back-to-back in ONE pass (no output handling,
    # no waiting between them) so the connection drop cannot leave a half-applied setup.
    $o1 = netsh interface ipv4 set address name="$adapterName" static $ip $mask $gw 2>&1
    $o2 = $null
    $o3 = $null
    if ($dns1) { $o2 = netsh interface ipv4 set dnsservers name="$adapterName" static $dns1 primary validate=no 2>&1 }
    if ($dns2) { $o3 = netsh interface ipv4 add dnsservers name="$adapterName" $dns2 index=2 validate=no 2>&1 }
    foreach ($x in @($o1) + @($o2) + @($o3)) { if ("$x".Trim()) { Write-Output "  $x" } }
}

Write-Output "  PUSH: $ip / $mask (/$prefix), gateway $gw, DNS $dns1 $dns2 on '$adapterName' -- everything in one pass"
Set-AllAtOnce
if (Get-Command Get-NetIPAddress -ErrorAction SilentlyContinue) {
    # From here on this only checks and repairs, on the target itself -- it keeps running
    # even if the admin PC has already lost the connection.
    $attempt = 1
    while ($true) {
        $until = (Get-Date).AddSeconds(12)
        do {
            Start-Sleep -Seconds 2
            $missing = @(Get-Missing)
        } while ($missing.Count -gt 0 -and (Get-Date) -lt $until)
        if ($missing.Count -eq 0 -or $attempt -ge 3) { break }
        $attempt++
        Write-Output "  Not applied yet: $($missing -join ', ') -- pushing again (attempt $attempt of 3)..."
        Set-AllAtOnce
    }
    if ($missing.Count -eq 0) { Write-Output "  VERIFIED on the target: IP address, subnet mask, gateway and DNS match." }
    else { Write-Output "  WARNING: still not applied after $attempt attempts: $($missing -join ', ')" }
}
Write-Output "  === RESULTING CONFIGURATION ==="
Get-NetIPConfiguration -InterfaceAlias $adapterName -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Output "  IPv4 Address : $($_.IPv4Address.IPAddress)"
    Write-Output "  Gateway      : $($_.IPv4DefaultGateway.NextHop)"
    Write-Output "  DNS Servers  : $($_.DNSServer.ServerAddresses -join ', ')"
}
"""

OPERATIONS += [
    _np_clone("rt_set_static_ip", "np_static_ip", "Push: Set Static IP (no wait)",
              "Sends IP + mask + gateway + DNS1/DNS2 in ONE pass, then returns immediately: 'Static IP set cmd pushed to the target machine'. Use Ping Host to watch the change.",
              _NP_STATIC_BODY),
    _np_clone("rt_set_dhcp", "np_dhcp", "Push: Set DHCP (no wait)",
              "Switches the adapter to DHCP and returns immediately: 'DHCP set cmd pushed to the target machine'. Use Ping Host to watch the new address appear."),
    _np_clone("flush_dns", "np_flush_dns", "Push: Flush DNS (no wait)",
              "Clears the DNS cache + re-registers and returns immediately: 'Flush DNS cmd pushed to the target machine'."),
    _np_clone("reset_network", "np_reset_tcpip", "Push: Reset TCP/IP & Winsock (no wait)",
              "Resets Winsock + TCP/IP and returns immediately: 'Reset TCP/IP cmd pushed to the target machine'. A restart is needed afterwards."),
    {
        "id": "np_ping_host",
        "danger": False,
        "label": "Ping Host (continuous until Stop)",
        "category": "Network Push",
        "description": "Pings the target (and its DNS answer, plus up to two extra IPs) every 2 s until you press STOP; prints every change and which IP is LIVE. Needs no WinRM login. Put it LAST in the run order.",
        "params": [
            {"key": "WATCH_IP1", "kind": "ipv4", "label": "Also watch this IP (optional, e.g. the NEW static IP)", "required": False},
            {"key": "WATCH_IP2", "kind": "ipv4", "label": "Also watch a 2nd IP (optional, e.g. the OLD IP)", "required": False},
        ],
        "command": r"""
# Handled by the host application (ping_monitor_gen) -- never sent to the target.
Write-Output "  (local ping monitor)"
""",
    },
]

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
        # Short timeouts for polling/reconnecting while the target's network may be down.
        kwargs.update(connection_timeout=10, read_timeout=30, operation_timeout=20)
    if transport == "basic":
        kwargs["encryption"] = "never"
    return Client(hostname, **kwargs)



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
    return f"data: {json.dumps(d)}\n\n"


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


# v3.8 (DC-42): the detached launcher used ONE method (Win32_Process.Create) and
# failed with "PCAT_LAUNCH_FAIL:2" (Access denied) on targets where that WMI call
# is refused from inside a WinRM session. It now tries five methods in order and
# reports exactly which ones failed and why. All of them start a process that
# lives OUTSIDE the WinRM shell, so it survives the network drop.
_LAUNCH_TPL = r"""$dir = Join-Path $env:windir 'Temp'
$ps1 = Join-Path $dir 'pcat_@@TOK@@.ps1'
[IO.File]::WriteAllBytes($ps1, [Convert]::FromBase64String('@@B64@@'))
$tn  = 'PCAT_@@TOK@@'
$exe = 'powershell.exe'
$arg = '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + $ps1 + '"'
$cl  = $exe + ' ' + $arg
$ok  = $false
$why = @()
if (-not $ok) {
  try {
    $a = New-ScheduledTaskAction -Execute $exe -Argument $arg
    $p = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
    $s = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 4)
    Register-ScheduledTask -TaskName $tn -Action $a -Principal $p -Settings $s -Force -ErrorAction Stop | Out-Null
    Start-ScheduledTask -TaskName $tn -ErrorAction Stop
    Write-Output ('PCAT_LAUNCHED:schtask:' + $tn); $ok = $true
  } catch {
    $why += ('ScheduledTask(SYSTEM): ' + ($_.Exception.Message -replace '\s+', ' '))
    try { Unregister-ScheduledTask -TaskName $tn -Confirm:$false -ErrorAction SilentlyContinue } catch {}
  }
}
if (-not $ok) {
  try {
    $r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cl } -ErrorAction Stop
    if ($r.ReturnValue -eq 0) { Write-Output ('PCAT_LAUNCHED:cim:' + $r.ProcessId); $ok = $true }
    else {
      $cc = @{ 2 = 'Access denied'; 3 = 'Insufficient privilege'; 8 = 'Unknown failure'; 9 = 'Path not found'; 21 = 'Invalid parameter' }
      $why += ('Win32_Process.Create(CIM): return code ' + $r.ReturnValue + ' (' + $cc[[int]$r.ReturnValue] + ')')
    }
  } catch { $why += ('Win32_Process.Create(CIM): ' + ($_.Exception.Message -replace '\s+', ' ')) }
}
if (-not $ok) {
  try {
    $r = Invoke-WmiMethod -Class Win32_Process -Name Create -ArgumentList $cl -ErrorAction Stop
    if ($r.ReturnValue -eq 0) { Write-Output ('PCAT_LAUNCHED:wmi:' + $r.ProcessId); $ok = $true }
    else { $why += ('Win32_Process.Create(WMI): return code ' + $r.ReturnValue) }
  } catch { $why += ('Win32_Process.Create(WMI): ' + ($_.Exception.Message -replace '\s+', ' ')) }
}
if (-not $ok) {
  try {
    if ($ps1 -match '\s') { $tr = $exe + ' -NoProfile -NonInteractive -ExecutionPolicy Bypass -File \"' + $ps1 + '\"' }
    else { $tr = $exe + ' -NoProfile -NonInteractive -ExecutionPolicy Bypass -File ' + $ps1 }
    $o1 = & schtasks.exe /Create /TN $tn /TR $tr /SC ONCE /ST 00:00 /RU SYSTEM /RL HIGHEST /F 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) { throw ('create failed (' + $LASTEXITCODE + '): ' + $o1) }
    $o2 = & schtasks.exe /Run /TN $tn 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) { throw ('run failed (' + $LASTEXITCODE + '): ' + $o2) }
    Write-Output ('PCAT_LAUNCHED:schtasks:' + $tn); $ok = $true
  } catch {
    $why += ('schtasks.exe: ' + ($_.Exception.Message -replace '\s+', ' '))
    try { & schtasks.exe /Delete /TN $tn /F 2>&1 | Out-Null } catch {}
  }
}
if (-not $ok) {
  try {
    $pr = Start-Process -FilePath $exe -ArgumentList $arg -WindowStyle Hidden -PassThru -ErrorAction Stop
    Write-Output ('PCAT_LAUNCHED:startprocess:' + $pr.Id); $ok = $true
  } catch { $why += ('Start-Process: ' + ($_.Exception.Message -replace '\s+', ' ')) }
}
if (-not $ok) {
  $who = ''; $adm = ''
  try {
    $wi = [Security.Principal.WindowsIdentity]::GetCurrent(); $who = $wi.Name
    $adm = ([Security.Principal.WindowsPrincipal]$wi).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
  } catch {}
  Remove-Item $ps1 -Force -ErrorAction SilentlyContinue
  Write-Output ('PCAT_LAUNCH_FAIL:' + ($why -join ' | ') + ' || account=' + $who + ' admin=' + $adm)
}
"""

_CLEAN_TPL = r"""$b = Join-Path (Join-Path $env:windir 'Temp') 'pcat_@@TOK@@'
try { Unregister-ScheduledTask -TaskName 'PCAT_@@TOK@@' -Confirm:$false -ErrorAction SilentlyContinue } catch {}
try { & schtasks.exe /Delete /TN 'PCAT_@@TOK@@' /F 2>&1 | Out-Null } catch {}
Remove-Item ($b + '.*') -Force -ErrorAction SilentlyContinue
"""

_LAUNCH_METHOD_NAMES = {
    "schtask": "one-shot scheduled task running as SYSTEM",
    "cim": "Win32_Process.Create (CIM)",
    "wmi": "Win32_Process.Create (WMI)",
    "schtasks": "schtasks.exe one-shot task running as SYSTEM",
    "startprocess": "hidden Start-Process (last resort; may end if the WinRM shell is closed)",
}


def _launch_fail_lines(out):
    """Turn the PCAT_LAUNCH_FAIL:... marker into plain-English report lines."""
    detail = out.split("PCAT_LAUNCH_FAIL:", 1)[1].strip() if "PCAT_LAUNCH_FAIL:" in out else out.strip()
    methods, _, acct = detail.partition(" || ")
    lines = ["  Could not start the task on the target -- every launch method failed:"]
    for m in [x.strip() for x in methods.split(" | ") if x.strip()]:
        lines.append("    - " + m)
    admin_false = "admin=False" in acct
    if acct.strip():
        who = re.search(r"account=(.*?)\s+admin=", acct)
        lines.append("  Signed in on the target as: %s  (administrator: %s)" % (
            who.group(1).strip() if who else "?", "NO" if admin_false else "yes"))
    if admin_false:
        lines += ["  Cause: this account is NOT an administrator on the target (or Windows remote UAC is filtering its token).",
                  "  Fix  : use a Domain Admin / local administrator account. For a local admin that is not the built-in",
                  "         'Administrator', run on the target once:",
                  "         reg add HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System /v LocalAccountTokenFilterPolicy /t REG_DWORD /d 1 /f"]
    else:
        lines += ["  The account is an administrator, but Windows refused every way of starting a process outside the WinRM session.",
                  "  Check on the target: the 'Task Scheduler' and 'Windows Management Instrumentation' services are running;",
                  "  security software (EDR/antivirus) is not blocking task/WMI process creation; Group Policy does not",
                  "  deny 'Log on as a batch job' to SYSTEM."]
    return lines


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
    return _LAUNCH_TPL.replace("@@TOK@@", tok).replace("@@B64@@", b64)


def _detach_poll_script(tok):
    return (
        "$b = Join-Path (Join-Path $env:windir 'Temp') 'pcat_" + tok + "'\n"
        "if (Test-Path ($b + '.done.txt')) {\n"
        "  if (Test-Path ($b + '.out.txt')) { Get-Content ($b + '.out.txt') -Raw -Encoding UTF8 }\n"
        "  Write-Output 'PCAT_DONE'\n"
        "} else { Write-Output 'PCAT_PENDING' }\n"
    )


def _detach_cleanup_script(tok):
    return _CLEAN_TPL.replace("@@TOK@@", tok)


# v3.8 (DC-44): reachability probing used while a network task is running.
# After a network change the old address may be gone. Instead of blindly retrying
# WinRM, probe (ICMP ping OR the WinRM TCP ports) the OLD IP and the HOST NAME in
# parallel; if neither answers, probe the NEW IP, then the host name again, and only
# then reconnect and read the real result from the target.
_TCP_PROBE_PORTS = (5985, 5986)


def _is_ipv4(s):
    return bool(re.match(r"^\d{1,3}(\.\d{1,3}){3}$", s or ""))


def _resolve_safely(fn, arg, timeout=3.0):
    """Run a blocking name lookup with a hard time limit; returns None on failure/timeout."""
    box = {}
    def w():
        try:
            box["v"] = fn(arg)
        except Exception:
            box["v"] = None
    t = threading.Thread(target=w, daemon=True)
    t.start(); t.join(timeout)
    return box.get("v")


def _make_ident(host):
    """Old identity captured BEFORE the change: {'ip': ..., 'name': ...}."""
    ip = name = None
    if _is_ipv4(host):
        ip = host
        r = _resolve_safely(socket.gethostbyaddr, host)
        if r and r[0] and r[0].lower() != host:
            name = r[0]
    else:
        name = host
        ip = _resolve_safely(socket.gethostbyname, host)
    return {"ip": ip, "name": name}


def _icmp_ping(host, timeout_s=2):
    if not _HOST_RE.match(host or ""):
        return False
    try:
        if platform.system() == "Windows":
            cmd = ["ping", "-n", "1", "-w", str(int(timeout_s * 1000)), host]
        else:
            cmd = ["ping", "-c", "1", "-W", str(int(timeout_s)), host]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s + 4,
                           creationflags=_NO_WINDOW)
        if r.returncode != 0:
            return False
        # Windows returns 0 even for "Destination host unreachable" -- a real reply has TTL=
        return ("TTL=" in r.stdout.upper()) if platform.system() == "Windows" else True
    except Exception:
        return False


def _tcp_open(host, port, timeout_s=2):
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return True
    except Exception:
        return False


def _alive(host):
    """True if the host answers ICMP ping or accepts a WinRM TCP connection."""
    if _icmp_ping(host):
        return True
    return any(_tcp_open(host, p) for p in _TCP_PROBE_PORTS)


def _probe_parallel(hosts):
    """Probe all hosts at the same time; returns {host: bool}."""
    res = {}
    def w(h):
        res[h] = _alive(h)
    ts = [threading.Thread(target=w, args=(h,), daemon=True) for h in hosts]
    for t in ts:
        t.start()
    for t in ts:
        t.join(20)
    return {h: bool(res.get(h)) for h in hosts}


def smart_reconnect_gen(ident, new_ips, username, password, transport, ev, log=lambda s: None):
    """
    One reconnect round. Order: (1) OLD IP + HOST NAME probed in parallel;
    (2) if neither answers: the NEW IP, then the host name; (3) WinRM reconnect on
    whatever answered. Yields UI events; returns (session, host) or (None, None).
    ev["new_alive"] is set to the new IP once it has answered.
    """
    def note(kind, text):
        msg = "    " + text
        log(msg)
        return _ev({"type": kind, "text": msg})
    cands = []
    for x in (ident.get("ip"), ident.get("name")):
        if x and x not in cands:
            cands.append(x)
    nm = ident.get("name")
    if nm and not _is_ipv4(nm):
        fresh = _resolve_safely(socket.gethostbyname, nm)      # DNS may now point at a new address
        if fresh and fresh not in cands:
            cands.append(fresh)
    if _stop_flag.is_set():
        return None, None
    yield note("dim", "Checking the old address and the host name in parallel: " + ", ".join(cands) + " ...")
    pr = _probe_parallel(cands)
    alive = [h for h in cands if pr.get(h)]
    if alive:
        yield note("dim", "Answering: " + ", ".join(alive))
    elif new_ips:
        yield note("dim", "Neither the old address nor the host name answers -- checking the NEW IP: " + ", ".join(new_ips) + " ...")
        pn = _probe_parallel(new_ips)
        alive = [h for h in new_ips if pn.get(h)]
        if alive:
            ev["new_alive"] = alive[0]
            yield note("success", "The new IP answers: " + ", ".join(alive))
            if nm:
                yield note("dim", "Now checking the host name " + nm + " ...")
                if _probe_parallel([nm]).get(nm):
                    yield note("success", "The host name " + nm + " answers as well.")
                    if nm not in alive:
                        alive.append(nm)
                else:
                    yield note("warning", "The host name " + nm + " does not answer yet (DNS can need a few minutes) -- using the new IP.")
    for h in alive:
        try:
            s = make_session(h, username, password, transport, fast=True)
            out, err, ok = run_remote_ps(s, 'Write-Output "RECONNECT_OK"')
            if ok and "RECONNECT_OK" in out:
                return s, h
            if err.startswith("CRED_ERR"):
                return None, None
        except Exception:
            pass
    if alive:
        yield note("dim", "It answers ping / the WinRM port, but WinRM is not ready yet -- retrying...")
    else:
        yield note("dim", "No answer yet -- waiting for the target to come back...")
    return None, None


def detached_run_gen(session, hosts, username, password, transport, body,
                     max_wait, log=lambda s: None):
    """
    Generator. Yields SSE strings; returns (stdout, stderr, success, host_used).
    """
    tok = secrets.token_hex(6)
    cur, cur_host = session, hosts[0]
    new_ips = [x for x in hosts[1:] if x]
    ident = _make_ident(hosts[0])            # old IP + host name, captured BEFORE the change
    ev = {"new_alive": None}
    out, err, ok = run_remote_ps(cur, _detach_launch_script(tok, body))
    if "PCAT_LAUNCHED" not in out:
        if err.startswith(("CRED_ERR", "TRANSPORT_ERR", "TIMEOUT_ERR")):
            return "", err, False, cur_host
        if "PCAT_LAUNCH_FAIL" in out:
            return "\n".join(_launch_fail_lines(out)), "Could not start the task on the target", False, cur_host
        return out, (err or "Could not start the detached task on the target: " + out.strip()), False, cur_host
    _m = re.search(r"PCAT_LAUNCHED:(\w+)", out)
    _meth = _LAUNCH_METHOD_NAMES.get(_m.group(1), _m.group(1)) if _m else "?"
    _msg = "    Started on the target via: " + _meth
    log(_msg); yield _ev({"type": "dim", "text": _msg})
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
        s2, h2 = yield from smart_reconnect_gen(ident, new_ips, username, password, transport, ev, log=log)
        if s2 is not None:
            cur, cur_host = s2, h2
        else:
            time.sleep(RECONNECT_WAIT_SECONDS)
    if ev["new_alive"] and new_ips:
        text = ("  The NEW IP %s answers (ping / WinRM port) and the old address no longer does -- the new address is active.\n"
                "  The change was applied. The detailed result could not be read back over WinRM (it may still be starting up).\n"
                "  Reconnect to the NEW address %s.\n" % (ev["new_alive"], ev["new_alive"]))
        return text, "", True, ev["new_alive"]
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
# ══════════════════════════════════════════════════════════════════════════════
#  v3.8 (DC-45)  NETWORK PUSH + PING MONITOR  (v16 method restored for network ops)
#  * The 7 network-changing tasks run INLINE again, exactly like v16 (one
#    run_remote_ps call, no detached engine) -- that is the method that worked.
#  * "Network Push" category: the command is sent and the tool does NOT wait for
#    the result -> "<action> cmd pushed to the target machine".
#  * "Ping Host" (np_ping_host): pings continuously until Stop and shows which
#    IP / name answers, so an IP change can be watched live.
# ══════════════════════════════════════════════════════════════════════════════
PUSH_OPS = {"np_static_ip", "np_dhcp", "np_flush_dns", "np_reset_tcpip"}
PUSH_DROPS_LINK = {"np_static_ip", "np_dhcp", "np_reset_tcpip"}   # later WinRM tasks would hit a dead link
MONITOR_OPS = {"np_ping_host"}
PUSH_MESSAGES = {
    "np_static_ip":   "Static IP set cmd pushed to the target machine",
    "np_dhcp":        "DHCP set cmd pushed to the target machine",
    "np_flush_dns":   "Flush DNS cmd pushed to the target machine",
    "np_reset_tcpip": "Reset TCP/IP cmd pushed to the target machine",
}
PUSH_GRACE_SECONDS = 8          # how long the command is given to be delivered / answer before we stop waiting
MONITOR_INTERVAL = 2.0          # seconds between ping rounds
MONITOR_HEARTBEAT_ROUNDS = 5    # print an unchanged status every N rounds
MONITOR_MAX_SECONDS = 6 * 3600  # safety cap; Stop ends it sooner
NETWORK_RECONNECT_ATTEMPTS = 10

_NETSTATUS_PS = r"""
Get-NetIPConfiguration -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Output ("  {0}: IPv4 {1} | Gateway {2} | DNS {3}" -f $_.InterfaceAlias, ($_.IPv4Address.IPAddress -join ','), ($_.IPv4DefaultGateway.NextHop -join ','), ($_.DNSServer.ServerAddresses -join ','))
}
"""


def push_run(session, script):
    """
    Send a script and do not wait for the full result.
    Returns (stdout, stderr, success, state); state is "done" when the target answered
    within PUSH_GRACE_SECONDS with a real result, or "pushed" when the command was sent
    and we stopped waiting (or the link dropped, which is the expected effect of a
    network change).
    """
    box = {}

    def w():
        box["r"] = run_remote_ps(session, script)
    t = threading.Thread(target=w, daemon=True)
    t.start()
    t.join(PUSH_GRACE_SECONDS)
    if "r" not in box:
        return "", "", True, "pushed"
    out, err, ok = box["r"]
    if not ok and err.startswith(("TRANSPORT_ERR", "TIMEOUT_ERR")):
        return out, "", True, "pushed"
    return out, err, ok, "done"


_PING_TIME_RE = re.compile(r"time\s*[=<]\s*([0-9.]+)\s*ms", re.IGNORECASE)
_PING_TTL_RE = re.compile(r"ttl\s*=\s*(\d+)", re.IGNORECASE)


def _ping_detail(host, timeout_s=2):
    """One ICMP ping -> (ok, rtt_ms or None, ttl or None)."""
    if not _HOST_RE.match(host or ""):
        return False, None, None
    try:
        if platform.system() == "Windows":
            cmd = ["ping", "-n", "1", "-w", str(int(timeout_s * 1000)), host]
        else:
            cmd = ["ping", "-c", "1", "-W", str(int(timeout_s)), host]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s + 4,
                           creationflags=_NO_WINDOW)
        txt = r.stdout or ""
        ttl_m = _PING_TTL_RE.search(txt)
        if r.returncode != 0 or (platform.system() == "Windows" and not ttl_m):
            return False, None, None
        t_m = _PING_TIME_RE.search(txt)
        return True, (float(t_m.group(1)) if t_m else None), (int(ttl_m.group(1)) if ttl_m else None)
    except Exception:
        return False, None, None


def _probe_detail(host):
    ok, rtt, ttl = _ping_detail(host)
    winrm = any(_tcp_open(host, p, 1.5) for p in _TCP_PROBE_PORTS)
    return {"ping": ok, "rtt": rtt, "ttl": ttl, "winrm": winrm}


def _probe_detail_parallel(hosts):
    """Probe every host at the same time; returns {host: detail-dict}."""
    res = {}

    def w(h):
        res[h] = _probe_detail(h)
    ts = [threading.Thread(target=w, args=(h,), daemon=True) for h in hosts]
    for t in ts:
        t.start()
    for t in ts:
        t.join(15)
    return {h: res.get(h) or {"ping": False, "rtt": None, "ttl": None, "winrm": False} for h in hosts}


def _fmt_detail(host, d):
    if d["ping"]:
        extra = (f" {d['rtt']:g}ms" if d["rtt"] is not None else "") + (f" TTL={d['ttl']}" if d["ttl"] is not None else "")
        s = f"{host}: PING OK{extra}"
    else:
        s = f"{host}: no ping"
    s += ", WinRM port open" if d["winrm"] else ", WinRM port closed"
    return s


def ping_monitor_gen(host, watch_ips, log=lambda s: None):
    """
    Generator: ping `host` (name or IP) plus any extra IPs to watch -- all in parallel,
    every MONITOR_INTERVAL seconds -- until Stop is pressed. When `host` is a name its
    current DNS answer is probed too, so you see WHICH IP the name is live on.
    Prints on every change and every MONITOR_HEARTBEAT_ROUNDS rounds.
    Returns the number of rounds run.
    """
    watch = [w for w in (watch_ips or []) if w]
    yield _ev({"type": "info", "text": f"    Pinging {host}" + (f" + watching {', '.join(watch)}" if watch else "")
               + f" every {MONITOR_INTERVAL:g}s -- press STOP to end."})
    log(f"    Ping monitor started: {host} {watch}")
    last_sig = None
    last_live = None
    rounds = 0
    started = time.time()
    while not _stop_flag.is_set() and (time.time() - started) < MONITOR_MAX_SECONDS:
        rounds += 1
        resolved = None
        if not _is_ipv4(host):
            resolved = _resolve_safely(socket.gethostbyname, host)
        targets = list(dict.fromkeys([host] + ([resolved] if resolved else []) + watch))
        det = _probe_detail_parallel(targets)
        live = [h for h in targets if _is_ipv4(h) and (det[h]["ping"] or det[h]["winrm"])]
        sig = (resolved, tuple((h, det[h]["ping"], det[h]["winrm"]) for h in targets))
        changed = sig != last_sig
        if changed or rounds % MONITOR_HEARTBEAT_ROUNDS == 0:
            stamp = time.strftime("%H:%M:%S")
            parts = []
            if not _is_ipv4(host):
                parts.append(f"{host} resolves to {resolved or 'NOTHING (DNS has no answer)'}")
            parts += [_fmt_detail(h, det[h]) for h in targets]
            any_up = any(det[h]["ping"] or det[h]["winrm"] for h in targets)
            tag = "success" if any_up else "error"
            prefix = "CHANGE " if (changed and last_sig is not None) else ""
            line = f"    [{stamp}] #{rounds} {prefix}" + " | ".join(parts)
            yield _ev({"type": tag, "text": line}); log(line)
            if live != last_live:
                msg = ("    LIVE IP now: " + ", ".join(live)) if live else "    LIVE IP now: none -- the target is not answering"
                yield _ev({"type": "info" if live else "warning", "text": msg}); log(msg)
                last_live = live
            last_sig = sig
        slept = 0.0
        while slept < MONITOR_INTERVAL and not _stop_flag.is_set():
            time.sleep(0.25)
            slept += 0.25
    msg = f"    Ping monitor stopped after {rounds} round(s)."
    yield _ev({"type": "dim", "text": msg}); log(msg)
    return rounds


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
            f"  PC ADMIN & PERFORMANCE TOOL  v3.8  -- Web-Service Edition",
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

        # Create WinRM session (skipped when only local tasks -- Ping Host / consoles -- are selected)
        only_local = all(o["id"] in (MONITOR_OPS | CONSOLE_OP_IDS) for o in selected)
        session = None
        if only_local:
            yield ev({"type": "info", "text": "  No WinRM login needed for the selected task(s)."})
            lf("  No WinRM session needed")
        if not only_local:
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

        total = len(selected)
        cur_host = hostname          # may change if a task re-addresses the target
        target_rebooting = False
        link_dropped = False         # set after a pushed network change
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

            if target_rebooting:
                msg = "    Skipped: the target is restarting -- run this task again once it is back online."
                yield ev({"type": "warning", "text": msg}); lf(msg)
                yield ev({"type": "blank"})
                continue

            # v3.7 Admin Consoles: launched locally on the machine hosting this
            # service (a web server cannot open a window on a remote browser).
            if task["id"] in CONSOLE_OP_IDS:
                for line in launch_console(task["id"], cur_host, username, password, transport):
                    yield ev({"type": "info", "text": f"    {line}"})
                    lf(f"    {line}")
                yield ev({"type": "blank"})
                continue

            # v3.8 Ping Host: runs locally, no WinRM, until Stop.
            if task["id"] in MONITOR_OPS:
                pv = param_vals.get(task["id"], {})
                watch = []
                for k in ("WATCH_IP1", "WATCH_IP2"):
                    c, e = _validate_ipv4((pv.get(k) or "").strip()) if (pv.get(k) or "").strip() else (None, None)
                    if c and not e:
                        watch.append(c)
                yield from ping_monitor_gen(cur_host, watch, log=lf)
                yield ev({"type": "blank"})
                continue

            if link_dropped:
                msg = ("    Skipped: a network change was pushed to the target, so the old connection is gone -- "
                       "use 'Ping Host' to see when it answers, then run this task again.")
                yield ev({"type": "warning", "text": msg}); lf(msg)
                yield ev({"type": "blank"})
                continue

            t_start = time.time()
            tid = task["id"]
            pushed_flag = False
            cmd_text = final_commands.get(tid, task["command"])
            if task.get("needs_cred"):
                cmd_text = build_cred_prelude(username, password) + cmd_text

            if tid in PUSH_OPS:
                # v3.8 Network Push: send the command, do not wait for the result.
                stdout, stderr, success, pstate = push_run(session, cmd_text)
                if success:
                    pushed_flag = True
                    msg = f"    ✓ {PUSH_MESSAGES[tid]}"
                    yield ev({"type": "success", "text": msg}); lf(msg)
                    if pstate == "pushed" and not stdout.strip():
                        stdout = "  The command keeps running on the target; no result is awaited. Use 'Ping Host' to watch it."
                    elif pstate == "done":
                        stdout = stdout.rstrip() + "\n  (the target answered within a few seconds -- result above)"
                    link_dropped = tid in PUSH_DROPS_LINK
            elif task.get("long"):
                # Very long task (DISM / CHKDSK): run DETACHED on the target and poll,
                # so a >170 s runtime cannot hang or kill this call.
                alt_hosts = []
                note = "    Long-running task: running detached on the target; waiting for it to finish (no timeout at 170 s)."
                yield ev({"type": "dim", "text": note}); lf(note)
                stdout, stderr, success, used_host = yield from detached_run_gen(
                    session, [cur_host] + alt_hosts, username, password, transport,
                    cmd_text, DETACH_LONG_WAIT, log=lf)
                if used_host != cur_host:
                    cur_host = used_host
                    msg = f"    Target is now reached at {cur_host}."
                    yield ev({"type": "info", "text": msg}); lf(msg)
                session = make_session(cur_host, username, password, transport)
            else:
                stdout, stderr, success = run_remote_ps(session, cmd_text, task["label"])
                if not success and stderr.startswith(("TRANSPORT_ERR", "TIMEOUT_ERR")):
                    if expects_reboot(tid, param_vals.get(tid, {})):
                        msg = "    Connection closed because the target is restarting -- this is the expected result."
                        yield ev({"type": "success", "text": msg}); lf(msg)
                        stdout, stderr, success = "  Restart requested; the target is going down.", "", True
                        target_rebooting = True
                    elif tid in NETWORK_BLIP_OPS:
                        # v16 method: the connection dropping is the expected effect of a network
                        # change -- do NOT retry the change; reconnect and report what the target has now.
                        msg = "    Connection dropped while the network changed -- this is expected. Checking the target..."
                        yield ev({"type": "warning", "text": msg}); lf(msg)
                        alt = []
                        if tid == "rt_set_static_ip":
                            nip = (param_vals.get(tid, {}).get("IP") or "").strip()
                            if nip and nip != cur_host:
                                alt.append(nip)
                        s2, h2 = yield from reconnect_gen([cur_host] + alt, username, password, transport,
                                                          log=lf, attempts=NETWORK_RECONNECT_ATTEMPTS)
                        if s2 is not None:
                            session, cur_host = s2, h2
                            so, se, sok = run_remote_ps(session, _NETSTATUS_PS)
                            stdout = ("  The command was delivered; the connection dropped as expected.\n"
                                      f"  Target answers again at {cur_host}. Current network status:\n" + so)
                            stderr, success = "", True
                        else:
                            stdout = ("  The command was delivered but the target has not answered yet.\n"
                                      "  Use 'Ping Host' (Network Push) to watch it, then re-check.")
                            stderr, success = "", False
                    else:
                        msg = "    Connection lost -- reconnecting..."
                        yield ev({"type": "warning", "text": msg}); lf(msg)
                        s2, h2 = yield from reconnect_gen([cur_host], username, password, transport, log=lf)
                        if s2 is not None:
                            session = make_session(cur_host, username, password, transport)
                            msg = "    Session reconnected -- retrying task"
                            yield ev({"type": "success", "text": msg}); lf(msg)
                            stdout, stderr, success = run_remote_ps(session, cmd_text, task["label"])
                        else:
                            msg = "    Reconnect failed -- the target did not come back in time"
                            yield ev({"type": "error", "text": msg}); lf(msg)
            if success and tid in (REBOOT_OPS | CONDITIONAL_REBOOT_OPS) and any(m in stdout for m in REBOOT_MARKERS):
                target_rebooting = True

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

            status = ("✓ Pushed" if pushed_flag else "✓ Completed") if success else "⚠ Completed with errors"
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
    print("  PC Admin & Performance Tool  v3.8  -- Web-Service Edition")
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
