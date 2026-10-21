PC Admin & Performance Tool -- Web-Service Edition  (v3.7)
================================================================
Runs as a standalone network service on PORT 3038. Once started on a
host, anyone on the same allowed subnet can open it from a browser at:

    http://<hosting-machine-IP>:3038

All logs and session files are written LOCALLY on the hosting machine
(the "logs" folder next to app.py) -- not on the client's browser/PC.

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
  - FIX: ROOT CAUSE of launcher windows closing with no visible error,
    found this version after three versions of guessing at symptoms.
    cmd.exe treats an unescaped closing parenthesis ")" inside a
    parenthesized ( ... ) block as the END of that block -- the rest of
    the line then becomes a syntax error, and cmd.exe finds that error
    while PARSING the block, before it even runs, so it happens even
    when the block's own condition is false. That aborts the ENTIRE
    batch file immediately, which is why a double-clicked window just
    vanished with nothing useful printed. check_port.bat -- called by
    BOTH install_service.bat and run_console_testmode.bat since v3.3 --
    had exactly this defect in its reserved-port check, which is why
    the installer in particular tended to die right after its "Removing
    any previous version..." cleanup step: that's the line immediately
    before the port check runs. run_console_testmode.bat's own
    dependency-error handling had a second, independent instance of the
    same defect. Every launcher in every edition of this tool is now
    rewritten with NO parenthesized blocks at all (each uses goto/labels
    instead), so this entire class of failure cannot recur here, and two
    launchers that were saved with Unix (LF-only) line endings -- which
    cmd.exe can mishandle for goto/label lookup -- are now saved CRLF.
  - FIX: the installer's closing summary printed a stray "^" character
    in "PC Admin ^& Performance Tool" instead of a plain ampersand.
  - NEW: both launchers now also print which python.exe will actually
    run (a "Using: ..." line right after the version check) -- useful
    since more than one python.exe on PATH (a real install plus the
    Microsoft Store placeholder) is a normal, common setup, and it was
    not obvious which one a script would actually use.
  - FIX: "Network Adapter Speed and Traffic Stats" threw a conversion
    error on every real adapter instead of showing a speed. The cause:
    Windows' LinkSpeed property is TEXT ("1 Gbps"), not a number, and
    the code tried to do arithmetic on it directly. It now reads the
    adapter's numeric Speed property (bits per second) instead, and
    falls back to printing LinkSpeed as-is if that numeric value isn't
    available. Same fix applied to all three editions.
  - PowerShell edition only -- brought up to match this edition and the
    Python-GUI edition exactly, where it had quietly been doing less:
    installed-software and startup reports now also include per-user
    (not just machine-wide) entries and Startup-folder shortcuts;
    "Auto-Tune SysMain" now actually re-enables SysMain on an HDD-only
    PC if it had been left off; "Optimize Visual Effects" now also
    turns off the minimize/maximize window animation; the full system
    report now includes CPU clock speed and shows uptime down to the
    second; the network-adapter report now includes the adapter's full
    description and packet counts; the non-essential-services report no
    longer misses one SystemRoot-style path Windows can report services
    from; and "Set High Performance Power Plan" now confirms the plan
    that is ACTUALLY active afterwards instead of assuming success.
  - PORT CHANGED AGAIN: 3036 -> 3037, per the standing convention.

WHAT'S NEW IN v3.5
  - FIX: v3.4's own WindowsApps-stub detection was itself broken. It
    scanned the ENTIRE "where python" output for the word "WindowsApps"
    ANYWHERE in it, rather than checking only the one entry Windows
    actually runs. On any machine with a real Python installed AND the
    Store's placeholder stub also present further down PATH -- a normal,
    common setup, and exactly what caused this report -- that produced a
    false positive and stopped both launchers even though "python"
    worked completely fine. Replaced with a direct test (python
    --version, the same call the rest of each script already makes)
    instead of inspecting path text at all.
  - FIX: "Open Computer Management (Connected to Target)" now actually
    launches mmc.exe locally on the machine hosting this service,
    connected to the target -- matching the PowerShell and Python-GUI
    desktop editions, which already did this correctly. It previously
    only printed the equivalent command as text for you to run yourself.
    A server can never open a window on a remote browser's own screen --
    that's a hard limit of how the web works, not something any fix can
    change -- but if you're running this edition on your own PC and
    browsing to localhost (the common case), the hosting machine IS your
    PC, so the window now appears exactly like the desktop editions'
    does. If the host isn't Windows, or the launch itself fails, it
    still tells you the manual command to run yourself, and why.
  - PORT CHANGED AGAIN: 3035 -> 3037, per the standing convention -- the
    port was not the cause of either fix above.

WHAT'S NEW IN v3.4
  - FIX: even after v3.3, both launchers could still close before you
    could read why. Root cause this time: pcadmintool_service.py called
    a pywin32 function with no exception handling. install_service.bat
    always tries to remove any previous copy of the service before
    installing -- including on the very first install ever, when there
    is nothing to remove -- and depending on the pywin32 version, that
    can raise an error instead of returning cleanly. That error's details
    were also being hidden (">nul 2>nul"). This could not be tested
    before shipping, because pywin32 and Windows' own Service Control
    Manager do not exist on Linux -- said plainly rather than glossed
    over. Fixed at the source: removing/stopping a service that isn't
    installed or running now prints one plain line and continues; a
    genuine install failure still stops the script and shows the error,
    exactly as before.
  - NEW: both launchers now print a numbered CHECKPOINT before and after
    every step. (v3.5 above fixes a mistake in one of these checks.)
  - PORT CHANGED AGAIN: 3034 -> 3035, per this project's standing
    per-version convention -- not because 3034 itself was the problem
    this time.

WHAT'S NEW IN v3.3
  - FIX: run_console_testmode.bat could open and close again almost
    instantly, with localhost never responding, and no way to read why.
    Root cause: that file had NO pause anywhere after starting app.py,
    so however app.py ended -- most commonly, port 3034 already held by
    this tool's own Windows Service if that was installed separately via
    install_service.bat -- whatever it printed flashed by and the window
    closed before it could be read. Fixed at both levels: the window now
    ALWAYS pauses before closing and explains what happened, and app.py
    itself now adds a plain-English, tool-specific explanation (naming
    "net stop PCAdminTool" as the fix) on top of the underlying error.
  - FIX: install_service.bat's dependency-install step is now checked for
    failure too (previously silent -- a failed install fell through to a
    confusing, unrelated-looking error later).
  - Checked the other two editions' own launchers for this same class of
    problem rather than assuming only this one had it -- both did, to
    different degrees, and both are fixed too (see their own READMEs).
  - PORT CHANGED AGAIN: 3033 -> 3034 (see UPGRADING below).

WHAT'S NEW IN v3.2
  - FIX: the service-name field rejected any real Windows service Name
    that contains a space -- e.g. "ManageEngine UEMS - Agent" -- and
    showed "looks invalid" even though the value was correct. It now
    accepts spaces and the characters real service Names actually use
    ($ # + ( ) as in "MSSQL$SQLEXPRESS"), while still refusing wildcards,
    quotes, backticks, semicolons and pipes. The value is substituted as
    a single-quoted PowerShell literal so none of those characters can
    expand or execute.
  - NEW: Map / unmap a network drive for a specific user account on the
    target, plus a read-only "List Mapped Network Drives" check -- 3 new
    Remote Tools operations (67 total, up from 64). A drive mapped over
    a remote PowerShell session only exists inside that session, so
    mapping writes the target user's own registry profile (reconnects
    at every sign-in) and, if that user is currently signed in, also
    connects the drive live inside their own desktop session.
  - FIX: a task row with input fields (an IP, a service name, ...) no
    longer squeezes its title/description down to one word per line --
    the input area now wraps onto its own line below the title.
  - FIX: "List All Services" lines up its Name / Status / StartType
    columns even for long service names that used to push them out of
    alignment.
  - PORT CHANGED AGAIN: 3032 -> 3033 (see UPGRADING below).

WHAT'S NEW IN v3.1
  - Three operations that used to restart the target automatically now
    show a real checkbox ("Automatically restart when done") instead of
    always restarting: Full Soft-Recycle Bundle, and both Rename Computer
    operations. Leave it checked for the old behavior. Uncheck it to do
    the real work (the network/USB cycle, or the rename) and leave the
    restart for you to trigger yourself later via Power Recycle -> Force
    Restart Now. Not added to "Force Restart Now" / "Force Sign-out &
    Restart" -- those two ARE the restart, so an "off" switch on them
    would just mean doing nothing.
  - PORT CHANGED AGAIN: 3031 -> 3032 (see UPGRADING below).

WHAT'S NEW IN v3.0
  - Two new categories, 28 new operations (64 total, up from 36):
      * Power Recycle  -- software-only alternatives to a physical power
        cycle: diagnose/fix a hung driver, storage controller, network
        driver, or USB device; check firmware/BIOS; fix sleep/wake
        devices; a pre-recycle evidence snapshot; and a last-resort
        "full soft recycle" bundle.
      * Remote Tools    -- static IP/DHCP, computer rename (domain,
        workgroup, and legacy WMIC), VSS shadow-copy view/delete,
        scheduled task lookup, a specific service restart, a full
        service inventory, and a Computer Management launcher.
  - Some operations now take a runtime value (an IP, an adapter name, a
    device ID, ...) entered in the task list before running -- every
    value is validated against an allow-list pattern for its field type
    before it is ever sent anywhere.
  - Every operation now carries a real "danger" flag the SERVER checks
    too, not just the browser -- a sensitive operation cannot run
    without an explicit confirmation, even from a direct API call.
  - PORT CHANGED: 3030 -> 3031.

UPGRADING FROM AN OLDER INSTALL
  The Windows service installer and the firewall rule it creates are
  both named/scoped for the OLD port -- this matters whether you're
  coming from port 3030, 3031, 3032, 3033, 3034 or 3035.
  Before installing this version over an old one:
    1. On the OLD install folder, run uninstall_service.bat (or, on
       Linux, stop the old systemd unit / kill the old process). This
       removes the old firewall rule and the Windows Service
       registration. (v3.2+'s install_service.bat / uninstall_service.bat
       now also do this cleanup step for you automatically -- see step 2.)
    2. Copy THIS folder to the host (a fresh folder is fine, or overwrite
       the old one) and run install_service.bat / install_and_run.sh as
       normal -- it removes any previous copy of the service, opens
       port 3038, and registers the service under the same service
       name, now pointed at the new port.
    3. Update any saved bookmarks / links to use :3038.
  Skipping step 1 just leaves a harmless unused firewall rule open on
  the old port -- it won't conflict with the new one, but you should
  still close it if this machine is internet-facing.

  IMPORTANT -- if you use BOTH install modes, know which one is running:
  install_service.bat installs a REAL background Windows Service that
  keeps running permanently, even after you close every window and
  reboot the machine. If you install the service and LATER also try
  run_console_testmode.bat (or vice versa), the second one to start
  will fail, because the first one is already holding the port -- this
  is expected, not a bug, and as of v3.3 the tool tells you so clearly
  instead of the window just closing. You only need ONE of the two
  running at a time; test mode is for trying the tool out in the
  foreground, the service is for permanent background use.

WHAT'S IN THIS FOLDER
  app.py                        Flask backend, 67 remote PowerShell operations
  templates/index.html          Web UI (dark theme, category tabs, live log)
  pcadmintool_service.py        Windows Service wrapper (pywin32)
  requirements.txt              Flask, pypsrp, pywin32 (Windows only)
  install_service.bat           Windows / Windows Server: installs as a REAL
                                 Windows Service (shows in services.msc);
                                 also removes any previous version + old
                                 firewall rules before installing
  uninstall_service.bat         Windows: stops & removes the service, and
                                 every firewall rule this tool has ever used
  run_console_testmode.bat      Windows: quick foreground test run (not a
                                 service -- window must stay open; always
                                 pauses before closing so you can read any
                                 error, as of v3.3)
  check_port.bat                Windows: advisory-only check for whether the
                                 service port is already in use or reserved
                                 by Windows (used automatically by the two
                                 scripts above; safe to run by hand too)
  install_and_run.sh            Linux installer + launcher
  pcadmintool.service.template  Linux: optional systemd unit (real service)
  README.txt                    This file

WORKS ON
  - The HOSTING machine (runs this tool): Linux, Windows 10/11, or
    Windows Server 2016+, with Python 3.9+.
  - The TARGET machines it manages: must be Windows, with WinRM enabled
    (run once on each target, as Admin: Enable-PSRemoting -Force).
  - Any CLIENT browser on the same subnet, no install needed there --
    just a browser pointed at http://<hosting-IP>:3038

HOW TO RUN -- Windows / Windows Server  (installs as a real Service)
  1. Copy this folder to the machine that will host the service, e.g.
     C:\PCAdminTool\
  2. Double-click install_service.bat and approve the UAC prompt.
     This installs dependencies, removes any previous version of the
     service and its old firewall rules, registers "PC Admin &
     Performance Tool - Web Service" in services.msc with Startup
     Type = Automatic, opens firewall port 3038, and starts it.
  3. Open services.msc to confirm -- you'll see it listed, Status
     "Running", Startup type "Automatic". It will keep running in the
     background (no console window) and restart automatically on reboot.
  4. Share the URL with anyone on the same subnet:
        http://<this-machine-IP-or-name>:3038
  5. To stop/remove it later, run uninstall_service.bat.

  Prefer to just test it first without installing a service? Run
  run_console_testmode.bat instead (foreground only, window must stay
  open) -- but not at the same time as an already-installed service; see
  "IMPORTANT" under UPGRADING above.

HOW TO RUN -- Linux
  1. Copy this folder to the host.
  2. chmod +x install_and_run.sh && ./install_and_run.sh
     (or ./install_and_run.sh --daemon to background it)
  3. To install as a real systemd service (auto-start on boot, restart
     on crash, equivalent to the Windows Service above), see
     pcadmintool.service.template.

FIREWALL
  Make sure TCP port 3038 is allowed inbound on the hosting machine so
  other hosts on the subnet can reach it. install_service.bat attempts
  this automatically on Windows via netsh; on Linux, open it with your
  distro's firewall tool, e.g.:
    sudo ufw allow 3038/tcp
    sudo firewall-cmd --add-port=3038/tcp --permanent && sudo firewall-cmd --reload

LOGS & FILES
  Every run writes: logs/AdminTool_<hostname>_<timestamp>.log
  on the HOSTING machine (wherever app.py lives), regardless of which
  browser/client triggered the run.

WHY NOT WAITRESS?
  This tool streams live task output to the browser as it runs (Server-
  Sent Events). Werkzeug's threaded server (what app.py uses via
  app.run(..., threaded=True)) flushes each line immediately, which SSE
  needs. Waitress buffers responses before sending, which makes the web
  UI look "stuck" after clicking Run -- so both the service wrapper and
  the console/Linux launchers deliberately run app.py directly instead.

SECURITY NOTE
  Credentials are submitted from the browser to this service over plain
  HTTP by default and used to open a WinRM session to the target. Only
  run this on a trusted, access-controlled subnet, or put it behind
  HTTPS (a reverse proxy such as nginx/IIS with a TLS certificate) for
  anything beyond an isolated internal network.

  Every parameter value (IP address, computer name, service name, device
  ID, shared-folder path, drive letter, user account, ...) is checked
  against a strict allow-list pattern on the SERVER before it is
  substituted into any script -- a value with quotes, semicolons,
  backticks or pipes is rejected outright rather than escaped. Any
  operation flagged dangerous also requires the request to explicitly
  say so (confirmed_danger=true); this is enforced server-side, not
  just as a browser pop-up, so a script that skips the UI cannot skip
  the warning either.

  Mapping a network drive uses the TARGET user's own Windows identity --
  there is no separate username/password field for the share. Whoever
  can reach this service and has credentials for the target PC can map
  or remove drives for any user profile that exists on it; treat access
  to this tool with the same care as any other remote-admin credential.

TROUBLESHOOTING
  "A launcher window opens and closes immediately, localhost doesn't
  respond" -- both launchers print a numbered CHECKPOINT before and
  after every step, and always pause before closing so you can read what
  happened. If a window still closes before you can read it, re-run it
  and note the LAST checkpoint number printed just before it closes --
  that pinpoints exactly where. Two things worth knowing specifically:
    - If it stops at the "confirming python actually runs" checkpoint:
      this genuinely means Python isn't working from where this script
      is being run. Check the "where python" listing shown just above
      that checkpoint -- if EVERY path listed is under ...\WindowsApps\...
      that's a Windows-provided placeholder with no real Python behind
      it; install Python from https://www.python.org/downloads/. If a
      real path (like C:\PythonXX\python.exe) is ALSO listed, the
      checkpoint should pass on its own -- if it still doesn't, something
      else about that specific Python install is broken.
    - This tool's own Windows Service may already be running in the
      background (you installed it earlier with install_service.bat, or
      a previous test-mode window didn't fully close) and already
      holding the port. Run "net stop PCAdminTool" first, or just open
      the service's URL directly instead of running test mode.
  "A window opened, printed some checkpoints, and closed instantly with
  no error and no final pause" (fixed in v3.6) -- this was a genuine bug
  in check_port.bat / run_console_testmode.bat, not a problem with your
  PC; update to this version. Every launcher now always ends at "Press
  any key to continue" no matter what happens, so this specific failure
  mode (a window closing with nothing to read) should no longer be
  possible in any script in this package -- if it ever is, that is
  itself a bug worth reporting.
  If install_service.bat shows a line saying a service could not be
  found, was not running, or a similar one-line NOTE right after
  "Removing any previous version..." -- that is expected and harmless on
  a first-ever install (there is nothing to remove yet); it is
  informational, not an error, and the script continues normally.

(c) 2024-2026 Abdullah | All Rights Reserved | abuabdullah.be@outlook.com
