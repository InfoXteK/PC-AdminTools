PC Admin & Performance Tool -- PowerShell GUI Edition  (v3.8)
================================================================

WHAT'S NEW IN v3.8
  - REVERTED TO THE v3.6 METHOD for the network tasks (Set Static IP, Set DHCP,
    Flush DNS, Reset TCP/IP, adapter restarts): they run inline again, exactly
    as in v3.6, which worked on your network. If the connection drops because the
    network changed, the tool says so (that is expected), does NOT repeat the
    change, reconnects (also on the NEW IP for Set Static IP) and prints the
    target's current IP / gateway / DNS -- so the status shows without
    refreshing anything. Only DISM and CHKDSK still use the detached engine.
  - NEW CATEGORY "Network Push" (5 tasks, always run last):
      Push: Set Static IP (no wait)   IP + mask + gateway + DNS1 + DNS2 are sent in ONE pass
      Push: Set DHCP (no wait)
      Push: Flush DNS (no wait)
      Push: Reset TCP/IP & Winsock (no wait)
      Ping Host (continuous until Stop)
    A push task sends the command and returns after a few seconds with
    "Static IP set cmd pushed to the target machine" (or DHCP / Flush DNS /
    Reset TCP/IP) -- it does not wait for the result. Remaining tasks that
    need the old connection are skipped after a push that changes the network.
    Ping Host needs no WinRM login: it pings the target, the IP its name
    currently resolves to, and up to two extra IPs you type (e.g. the new
    static IP) in parallel every ~2 seconds until you press STOP, prints
    every CHANGE and which IP is LIVE.
  - Operations: 90 in total (was 85).
  - FIX: network tasks (Set Static IP, Set DHCP, Flush DNS, Reset TCP/IP, adapter
    restarts) stopped with "PCAT_LAUNCH_FAIL:2". The background task is now
    started with up to 5 methods (SYSTEM scheduled task, CIM, WMI, schtasks.exe,
    hidden Start-Process); the log says which one worked, and if all fail you
    get a readable report with the exact fix. Same change as the Web edition.

WHAT'S NEW IN v3.7
  - FIX: PC RENAME failed with "Access is denied" on every domain-joined
    target (all three variants). Cause: Rename-Computer on a domain member
    must log on to a domain controller itself; a WinRM/NTLM session only
    carries a network logon, which cannot be passed on to the DC (the
    "double hop"). The operation now rebuilds the username/password you
    connected with as a real credential INSIDE the remote session and calls
    Rename-Computer -DomainCredential, then falls back to the WMI rename
    method with the same credential, and prints the decoded reason when
    both fail (2224 = a computer account with the new name already exists
    in AD, 1326 = logon failure, 5 = no rights, ...). The password is never
    printed, logged or put on a command line.
      * Domain-Joined variant: refuses politely on a workgroup PC.
      * Workgroup/Local variant: refuses on a domain member (a local-only
        rename would break its AD account) and explains the remote-UAC fix
        for local accounts.
      * WMIC/Legacy variant: uses wmic.exe only where it exists and the PC is
        in a workgroup; otherwise the same WMI method through CIM, so it
        also works on Windows 11 24H2+ where WMIC is gone.
      * Restart is now "shutdown /r /t 15" so the reply arrives first.
  - FIX: after Flush DNS / Set Static IP / Set DHCP / Reset TCP-IP / adapter
    restart the tool hung and had to be restarted. Those tasks now run
    DETACHED on the target, the tool reconnects automatically (waits up to
    5 minutes, also tries the NEW IP for Set Static IP) and then shows the
    real output. Very long tasks (DISM RestoreHealth, DISM cleanup, CHKDSK)
    use the same engine, so they no longer die at 170 seconds.
  - NEW: restarting tasks (Force Restart, Force Sign-out & Restart, Full
    Soft-Recycle, rename with auto-restart) treat the dropped connection as
    SUCCESS and skip the remaining tasks with a clear message.
  - NEW operations (85 in total, was 67):
      Remote Tools : Resize VSS Shadow Storage (max size: 10%, 20GB,
                     51200MB, UNBOUNDED)
      Windows Health: DISM RestoreHealth; DISM Component Store Cleanup
                     (optional /ResetBase)
      Performance  : Hardware Inventory via CIM (WMIC replacement), Retrim
                     SSD, Verify WMI Repository, Rebuild Performance Counters
      Disk         : CHKDSK Online Scan (read-only)
      Admin Consoles (new category, 11 launchers): Computer Management,
                     Disk Management, Device Manager (read-only on Win 8 /
                     Server 2012 and later - a Windows limit), Services,
                     Event Viewer, Shared Folders, C$ admin share, Windows
                     Firewall (guided), Remote PowerShell window, Remote
                     Command Prompt (winrs), Remote Desktop with the
                     credential pre-loaded (the way to use GUI-only tools).
                     They open on THIS PC, connected to the target.

WHAT'S NEW IN v3.6
  - PCAdminTool.ps1 itself: 8 operations were quietly less complete than
    the other two editions and are now at parity with them -- see WHAT'S
    NEW at the top of PCAdminTool.ps1's own header for the itemised list
    (installed-software/startup reports now include per-user entries and
    Startup-folder items; SysMain auto-tune now actually re-enables itself
    on HDD-only PCs; visual-effects tuning now also disables the
    minimize/maximize animation; the system report shows CPU speed and
    uptime seconds; the adapter report shows the description and packet
    counts; the services report and the power-plan check are each one
    line more thorough).
  - FIX: "Network Adapter Speed and Traffic Stats" threw a conversion
    error on every real adapter (Windows reports link speed as TEXT,
    e.g. "1 Gbps", not a number, and the code tried to do arithmetic on
    it directly). It now reads the numeric Speed property instead, with
    a text fallback. Same fix applied in all three editions.
  - The launcher fix this version ships is in Run-AdminTool.bat, not in
    PCAdminTool.ps1: cmd.exe treats an unescaped closing parenthesis
    inside a ( ... ) block as the end of that block, which is a syntax
    error found while the block is PARSED -- even if its condition is
    false -- and that aborts the whole batch file. This is the root
    cause (found this version, after three versions of guessing at
    symptoms) of launcher windows closing with no visible error. Every
    launcher in every edition is now rewritten with no parenthesized
    blocks at all. Run-AdminTool.bat itself did not have this specific
    defect, but is rewritten the same way as a precaution, and its error
    report is now saved to PCAdminTool_last_error.log and read back to
    you instead of just naming the log file. See the Web edition's
    README for the full explanation.

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
  PCAdminTool.ps1      The complete tool (WinForms GUI, 90 operations).
  Run-AdminTool.bat     Double-click launcher. Requests Administrator
                         rights automatically, then opens the GUI.
  README.txt            This file.

WHAT'S NEW IN v3.3
  - No functional change to this edition's own tool -- version bumped for
    consistency across all three editions (the actual bug this version
    fixes was in the Web edition's launcher, reported as "opens and
    closes immediately, no response on localhost").
  - FIX (proactive): Run-AdminTool.bat had a worse version of the same
    underlying problem -- it launches PCAdminTool.ps1 with its console
    window deliberately hidden (so you don't see a blank PowerShell
    window sitting behind the actual tool), which meant that if
    PowerShell crashed before the tool's own window ever appeared, there
    was no indication of anything going wrong at all -- not even a
    flash, nothing visibly opened, nothing recorded anywhere. Its output
    is now captured to PCAdminTool_last_error.log in this folder, and the
    launcher checks whether it exited with an error and tells you to
    check that file -- while staying just as quiet as before on normal,
    successful use (closing the tool's window normally still just exits
    cleanly with no extra prompts).

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
  - FIX: "List All Services" lines up its Name / Status / StartType
    columns even for long service names that used to push them out of
    alignment.
  - Sensitive-operation detection re-verified: the per-operation flag
    and the master $DANGER list now agree on all 27 sensitive operations
    (up from 25 -- the 2 new ones are mapping and un-mapping a drive;
    listing mapped drives is read-only and is not flagged).

WHAT'S NEW IN v3.1
  - Three operations that used to restart the target automatically now
    show a real "Automatically restart when done" checkbox in the
    "Enter Required Values" window instead: Full Soft-Recycle Bundle,
    and both Rename Computer operations. Leave it checked for the old
    behavior. Uncheck it to do the real work (the network/USB cycle, or
    the rename) and leave the restart for you to trigger yourself later
    via Power Recycle -> Force Restart Now.
  - Not added to "Force Restart Now" / "Force Sign-out & Restart" --
    those two operations ARE the restart, so an "off" switch on them
    would just mean doing nothing.

WHAT'S NEW IN v3.0
  - Two new tabs, 28 new operations (64 total, up from 36):
      * Power Recycle  -- software-only alternatives to a physical power
        cycle: diagnose/fix a hung driver, storage controller, network
        driver, or USB device; check firmware/BIOS; fix sleep/wake
        devices; a pre-recycle evidence snapshot; and a last-resort
        "full soft recycle" bundle (restart every adapter, cycle every
        USB device, then restart -- the closest thing to pulling the
        plug without actually doing it).
      * Remote Tools    -- static IP/DHCP, computer rename (domain,
        workgroup, and legacy WMIC), VSS shadow-copy view/delete,
        scheduled task lookup, restart one service, a full service
        inventory, and a Computer Management launcher.
  - 12 of the 64 operations now need a value first (an IP, an adapter
    name, a device Instance ID, ...). Checking one of these and clicking
    PERFORM SELECTED opens a small "Enter Required Values" window first --
    fill it in, click Run. Every value is checked against an allow-listed
    pattern before it's used; a bad value is rejected with a clear
    message, never silently guessed or passed through as-is.
  - "Open Computer Management" launches mmc.exe on THIS machine (your
    admin workstation), connected to the target, instead of trying to
    run remotely -- a remote PSRemoting session has no desktop to show
    a window on, so this is the only way to make that feature actually
    usable.
  - Sensitive-operation detection is now double-checked internally
    (both the per-operation flag and the master list agree on all 25
    sensitive operations) so a new dangerous operation can never end up
    running without the confirmation prompt.

REQUIREMENTS
  - Windows 7 SP1 or later (client running the tool)
  - PowerShell 5.0+ (built in to Windows 7 SP1+/8.1/10/11)
  - Zero external modules / zero installs -- uses only
    System.Windows.Forms and System.Drawing (built in to .NET)
  - WinRM enabled on TARGET machines you want to manage:
      Run on each target (as Admin):  Enable-PSRemoting -Force

HOW TO RUN
  1. Copy this whole folder to the admin workstation.
  2. Double-click Run-AdminTool.bat
  3. Approve the UAC prompt (the tool needs to run elevated so it
     can open outbound PSRemoting sessions with your credentials).
  4. In the GUI: enter target Hostname/IP, Username, Password,
     pick the Auth Transport, click Test Connection, select the
     tasks you want (a small window will ask for any required values
     the first time you click Perform), click Perform / Run.

LOGS
  Every session writes a timestamped log to:
    PC_Admin_Logs\AdminTool_<hostname>_<timestamp>.log
  (created next to PCAdminTool.ps1)

NOTES
  - Operations marked with "!" are sensitive (may reboot the
    target, interrupt its network, delete recovery points, or take
    many minutes). The tool shows a confirmation dialog listing them
    before running.
  - Domain computer rename over WinRM can fail with plain NTLM due to
    the classic "double-hop" limitation -- if it fails, reconnect using
    Auth Transport = "Admin Double-Hop (CredSSP)" and retry.
  - Mapping a network drive uses the TARGET user's own Windows identity
    -- there is no separate username/password field for the share.
  - If Run-AdminTool.bat is blocked by SmartScreen ("Windows
    protected your PC"), click "More info" -> "Run anyway" (this
    is expected for unsigned scripts from outside the Store).

(c) 2024-2026 Abdullah | All Rights Reserved | abuabdullah.be@outlook.com
