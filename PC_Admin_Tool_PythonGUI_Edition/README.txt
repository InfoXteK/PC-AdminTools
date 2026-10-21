PC Admin & Performance Tool -- Native Python GUI Edition  (v3.7)
================================================================

WHAT'S NEW IN v3.7
  - FIX: network operations no longer leave the tool silent or force an
    application restart. Set Static IP, Set DHCP, Flush DNS, Reset TCP/IP and the
    adapter restarts now run as a detached SYSTEM job ON THE TARGET. The tool
    polls with fresh short sessions, waits through the network drop, follows the
    target to its NEW address after Set Static IP, and prints the result. A
    sensitive operation is never silently re-run after a dropped connection.
  - FIX: Rename Computer. A domain-joined PC could not be renamed by any of the 3
    variants ("Access is denied"): a WinRM/NTLM logon cannot authenticate onward
    to a domain controller. Domain variant now passes your credential explicitly;
    Workgroup variant refuses cleanly on a domain PC; the WMIC variant uses the
    WMI/CIM Rename where wmic.exe has been removed. No CredSSP needed.
  - NEW (Remote Tools): VSS Storage Size Report, Set VSS Max Storage Size,
    Create VSS Shadow Copy Now.
  - NEW (Performance): DISM Analyze / Component Cleanup / Deep Cleanup (ResetBase)
    / Health Scan, WMI verify + CIM snapshot (WMIC replacement), WMI repair,
    Rebuild Performance Counters, SSD Retrim, System-Managed Page File.
  - NEW category "Admin Consoles" (26 operations): Computer Management, Device
    Manager, Disk Management, Defrag GUI, Disk Cleanup, Services, Event Viewer,
    Task Scheduler, Firewall, Network Connections, PowerShell, CMD, Registry...
    They open on the TARGET's own screen using the credentials you entered.
    Needs someone signed in at the target's physical console, and Windows
    8.1 / Server 2012 R2 or newer on the target.
  - Total operations: 105 (was 67) in 8 categories. Web port: 3038 (was 3037).
  - The PowerShell GUI edition is NOT part of this update and stays at v3.6.

WHAT'S NEW IN v3.6
  - No functional change to this edition's own 67 operations, except
    "Network Adapter Speed and Traffic Stats": it threw a conversion
    error on every real adapter (Windows reports link speed as TEXT,
    e.g. "1 Gbps", not a number). It now reads the numeric Speed
    property instead, with a text fallback. Same fix applied in all
    three editions.
  - The actual launcher fix this version ships is this edition's own
    install_and_run.bat: cmd.exe treats an unescaped
    closing parenthesis inside a ( ... ) block as the end of that block,
    which is a syntax error found while the block is PARSED -- even if
    its condition is false -- and that aborts the whole batch file. This
    is the root cause (found this version, after three versions of
    guessing) of launcher windows closing with no visible error. Every
    launcher in every edition is now rewritten with no parenthesized
    blocks, and this file in particular no longer runs the word
    "Performance" as a stray command on every launch (its title line had
    an unescaped "&"). See the Web edition's README for the full
    explanation.

WHAT'S NEW IN v3.5
  - No functional change to this edition's own tool -- it already launches
    Computer Management locally, connected to the target, correctly. The
    actual fixes this version ships are in the Web edition: a false
    positive in v3.4's own Python-detection check, and Computer Management
    there now also launching locally instead of only printing text -- see
    the Web edition's README for the full explanation.

WHAT'S NEW IN v3.4
  - No functional change to this edition's own tool. The actual fix this
    version ships is in the Web edition's pcadmintool_service.py and its
    two launcher scripts (a pywin32 exception-handling gap on service
    removal that could never be tested on Linux, plus much more detailed
    step-by-step diagnostics in both launchers) -- see the Web edition's
    README for the full explanation.

WHAT'S IN THIS FOLDER
  PCAdminTool.pyw      The complete tool (Tkinter GUI, 67 operations).
  requirements.txt     Just pypsrp -- Tkinter ships with Python itself.
  install_and_run.bat  Double-click: installs pypsrp, then opens the GUI.
  README.txt           This file.

WHAT'S NEW IN v3.3
  - No functional change to this edition's own tool -- version bumped for
    consistency across all three editions (the actual bug this version
    fixes was in the Web edition's launcher, reported as "opens and
    closes immediately, no response on localhost").
  - FIX (proactive): install_and_run.bat had the same underlying class of
    problem as the Web edition's bug above -- if pythonw failed to launch
    the GUI (a missing dependency, for instance), the launcher gave no
    indication why, since pythonw has no console window at all by design.
    It now checks that Tkinter and pypsrp both import correctly BEFORE
    attempting to launch (catching the most likely failures with a clear,
    visible message), checks the dependency-install step for failure too
    (previously silent), and captures any remaining launch error to
    PCAdminTool_last_error.log in this folder.

WHAT'S NEW IN v3.2
  - FIX: the service-name field rejected any real Windows service Name
    that contains a space -- e.g. "ManageEngine UEMS - Agent" -- and
    showed as invalid even though the value was correct. It now accepts
    spaces and the characters real service Names actually use ($ # + ( )
    as in "MSSQL$SQLEXPRESS"), while still refusing wildcards, quotes,
    backticks, semicolons and pipes.
  - NEW: Map / unmap a network drive for a specific user account on the
    target, plus a read-only "List Mapped Network Drives" check -- 3 new
    Remote Tools operations (67 total, up from 64). A drive mapped over
    a remote PowerShell session only exists inside that session, so
    mapping writes the target user's own registry profile (reconnects
    at every sign-in) and, if that user is currently signed in, also
    connects the drive live inside their own desktop session.
  - FIX: a parameterized task's input fields could be squeezed into a
    half-width column even when a field (like the new shared-folder
    path) needed the full row -- such fields now take the whole row.
  - FIX: "List All Services" lines up its Name / Status / StartType
    columns even for long service names that used to push them out of
    alignment.

WHAT'S NEW IN v3.1
  - Three operations that used to restart the target automatically now
    show a real "Automatically restart when done" checkbox instead:
    Full Soft-Recycle Bundle, and both Rename Computer operations.
    Leave it checked for the old behavior (restarts right away).
    Uncheck it to do the real work (the network/USB cycle, or the
    rename) and leave the restart for you to trigger yourself later
    via Power Recycle -> Force Restart Now.
  - Not added to "Force Restart Now" / "Force Sign-out & Restart" --
    those two operations ARE the restart, so an "off" switch on them
    would just mean doing nothing.

WHAT'S NEW IN v3.0
  - Two new categories, 28 new operations (64 total, up from 36):
      * Power Recycle  -- software-only alternatives to a physical power
        cycle (hung driver, storage controller, network driver, USB
        device, firmware/BIOS check, sleep/wake devices, a pre-recycle
        evidence snapshot, and a last-resort full soft-recycle bundle).
      * Remote Tools    -- static IP/DHCP, computer rename (domain,
        workgroup, legacy WMIC), VSS shadow-copy view/delete, scheduled
        task lookup, restart one service, a full service inventory, and
        a Computer Management launcher.
  - 12 of the 64 operations now show extra input fields right under
    their row (an IP, an adapter name, a device ID, ...) when you look
    at them -- fill these in before checking the box and running.
    Every value is checked against an allow-listed pattern before it's
    used; invalid values are refused with a clear message, nothing is
    silently guessed.
  - "Open Computer Management" is special: it launches mmc.exe on THIS
    machine (your admin workstation), connected to the target, instead
    of trying to run remotely -- a remote session has no desktop to
    show a window on, so this is the only way to make that feature
    actually usable.

REQUIREMENTS
  - Python 3.9+ installed on the admin workstation (from
    https://www.python.org/downloads/ -- tick "Add to PATH" during
    install; Tkinter is included by default on Windows installers).
  - WinRM enabled on TARGET machines you want to manage:
      Run on each target (as Admin):  Enable-PSRemoting -Force

HOW TO RUN
  1. Copy this whole folder to the admin workstation.
  2. Double-click install_and_run.bat
     (installs pypsrp if missing, then launches the GUI with pythonw
     so no console window stays open).
  3. In the GUI: enter target Hostname/IP, Username, Password, pick
     the Auth Transport, click Test Connection, select tasks (fill in
     any input fields shown under a task first), Run.

  Alternatively, once pypsrp is installed, you can just double-click
  PCAdminTool.pyw directly (Windows associates .pyw with pythonw.exe).

LOGS
  Every session writes a timestamped log to:
    PC_Admin_Logs\AdminTool_<hostname>_<timestamp>.log
  (created next to PCAdminTool.pyw)

NOTES
  - Operations marked with "!" are sensitive (may reboot the target,
    interrupt its network, delete recovery points, or take many
    minutes). The tool shows a confirmation dialog listing them before
    running.
  - Domain computer rename over WinRM can fail with plain NTLM due to
    the classic "double-hop" limitation -- if it fails, reconnect using
    Auth Transport = "Admin Double-Hop (CredSSP)" and retry.
  - Mapping a network drive uses the TARGET user's own Windows identity
    -- there is no separate username/password field for the share.
  - Same 67 operations, same categories, and the same PowerShell
    command bodies as the Web-Service Edition (app.py) -- this is a
    desktop-native port of that same operation library, no browser
    or server required. Verified field-for-field and byte-for-byte
    (command text) identical to app.py's operation data (one
    intentional exception: the Computer Management launcher's own
    description/command, which is edition-specific by design -- see
    above).

(c) 2024-2026 Abdullah | All Rights Reserved | abuabdullah.be@outlook.com
