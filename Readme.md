# PC Admin & Performance Tool — Complete Setup & User Guide

**For:** `Multi-edition_PC_cleanup_tool-v17.zip` (PowerShell Edition v3.7 · Web-Service Edition v3.7 · Python GUI Edition v3.7)

**Who this is for:** written for someone who has never used PowerShell, never run a Python script, and doesn't know what a "port" or a "firewall rule" is. Every term is explained the first time it's used. If you already know this material, skip straight to whichever Part covers the edition you're installing.

**What's new since your last copy of this guide (v3.7):**
1. **Renaming a PC now works on domain-joined computers** (it failed with "Access is denied" before). See "Renaming a computer, step by step" in Part 4.
2. **Network tasks no longer freeze the tool.** Flush DNS, Set Static IP, Set DHCP, Reset TCP/IP and adapter restarts used to cut the connection and leave the tool stuck until you closed it. They now run in the background on the target and the tool reconnects by itself and shows the real result. See "What happens when a task changes the network".
3. **New tasks:** change the shadow-copy (VSS) size limit, DISM repair and cleanup, CHKDSK scan, a hardware report that works without WMIC, SSD retrim, WMI check, performance-counter rebuild.
4. **New tab "Admin Consoles"** — opens Computer Management, Disk Management, Services, Event Viewer, Device Manager, Firewall, a remote PowerShell window, a remote command prompt, Remote Desktop and the C$ share, all pre-connected to the target with the user name and password you typed. See "Admin Consoles, step by step".
5. **The Web edition now uses port 3038** (was 3037). Re-run `install_service.bat` (as Administrator) and use `:3038` in bookmarks.

---

## Before you start (read this first — 3 minutes)

### What this tool actually does
It's a control panel for fixing and managing OTHER Windows computers on your network from your own desk — restarting a stuck service, cleaning up disk space, fixing a network problem, renaming a computer, mapping a shared drive for someone, and so on — without physically walking over to that computer.

Two computers are involved in everything this tool does:
- **The admin computer** — the one YOU sit at, where you install and run this tool.
- **The target computer** — the OTHER computer you're fixing or managing, somewhere else on the network.

### The one thing every target computer needs, before anything else works
This tool talks to target computers using a built-in Windows feature called **WinRM** (Windows Remote Management). It's already part of Windows — nothing to download — but it's turned **off** by default. You must turn it on, once, on every computer you want to manage.

**How to turn it on** (you need to do this ON the target computer itself, or via someone who has physical/remote-desktop access to it — this one-time step can't be done from the admin computer, that's exactly the chicken-and-egg problem WinRM being off creates):

1. On the target computer, click Start, type `PowerShell`, right-click "Windows PowerShell", choose **"Run as administrator"**.
2. A blue or black window opens. Type this exactly and press Enter:
   ```
   Enable-PSRemoting -Force
   ```
3. It will print several lines and finish with no red error text. That's it — WinRM is now on.
4. If this computer is on a **Domain** (a workplace network managed by IT), that's usually all you need.
   If it's a **Workgroup/home** computer talking to another workgroup computer, also run this one extra line so Windows trusts the connection:
   ```
   Set-Item WSMan:\localhost\Client\TrustedHosts -Value "*" -Force
   ```
   (This tells the computer "allow WinRM connections from anywhere on my network" — fine for a home/lab network, not something you'd do on a computer exposed to the internet.)

You only do this once per target computer. Do it now, on at least one test computer, before going further — every part of this guide assumes it's already done.

### Key terms used throughout this guide
| Term | What it means |
|---|---|
| **Target** | The computer you're fixing/managing (not the one you're sitting at) |
| **WinRM** | The built-in Windows feature this tool uses to talk to a target (see above) |
| **Credentials** | A username and password with admin rights ON THE TARGET |
| **Elevated / Run as Administrator** | Running a program with full admin permissions — Windows will show a pop-up asking you to confirm this |
| **Firewall rule** | A permission that tells Windows "allow this specific kind of network traffic through" |
| **Port** | A number a running program listens on for connections, like a numbered mail slot. This tool's Web edition uses port **3038** |
| **Service** | A program Windows runs in the background permanently, even if nobody is logged in — it starts automatically when the computer boots |
| **UNC path** | A shared-folder address written as `\\servername\sharename` — the format every "map a network drive" field in this tool expects, see Part 4 |
| **Mapped drive** | A shortcut, shown as a lettered drive (like `Z:`) in File Explorer, that actually points at a shared folder on another computer |

---

## Which edition should I use?

There are three complete, independent copies of this tool in the zip file. Pick **one**.

| If you... | Use this edition |
|---|---|
| Just want to try it on your own PC, right now, simplest possible setup | **PowerShell Edition** |
| Want several people on your team to use the same tool from their own browsers, without installing anything on their machines | **Web-Service Edition** |
| Prefer a Python-based desktop app instead of PowerShell, or PowerShell is restricted on your PC | **Python GUI Edition** |

All three do exactly the same **85** things to target computers — the only difference is how YOU access the tool. If you're not sure, start with the **PowerShell Edition** (Part 1) — it needs zero installation.

---

# PART 1 — PowerShell GUI Edition

### What you need
- Windows 7 SP1 or later, on the admin computer.
- Nothing to install — PowerShell and the pieces this tool uses ship with Windows already.

### Step 1 — Get the files
Unzip `PC_Admin_Tool_PowerShell_Edition.zip` anywhere convenient, e.g. `C:\PCAdminTool\`.

### Step 2 — Open the tool
Double-click **`Run-AdminTool.bat`**. Approve the "Do you want to allow this app..." (UAC) prompt — this tool needs elevated permissions to open outbound connections to target computers using your credentials.

### Step 3 — The main screen, explained
- **Top section**: type the target's Hostname or IP address, the Username (as `DOMAIN\username` or `username@domain.com` for a domain account, or just `username` for a local account), and the Password.
- **Auth Transport** dropdown: leave it on "Windows Domain (NTLM) — Recommended" unless a specific task tells you to change it (see Step 7 in the Troubleshooting table).
- **Tabs** (Cleanup, Disk, Performance, Windows Health, Network, Power Recycle, Remote Tools, Admin Consoles): each groups related tasks. There are 85 tasks in total across all eight tabs.

### Step 4 — Connect to a target for the first time
Click **Test Connection**. A green message means it worked; a red one means something's wrong — see the Troubleshooting table at the end of this Part.

### Step 5 — Run your first task
1. Click the **Windows Health** tab.
2. Check the box next to **"Full System Information Report"** (a safe, read-only task — good for a first try).
3. Click **PERFORM SELECTED**.
4. Watch the log area — you'll see the tool connect, run the task, and print the computer's info back to you.

### Step 6 — Tasks that ask you to fill something in
Some tasks need a piece of information from you before they can run — for example, "Set Static IP Address" needs to know which IP address to set, and the three new drive-mapping tasks described below need a shared folder path, a drive letter, and a username. You'll know a task needs this because after checking its box and clicking PERFORM SELECTED, a small window titled **"Enter Required Values"** pops up first.

- Fill in every field shown (fields marked "(optional)" can stay blank).
- Some fields are a real checkbox instead of a text box — for example **"Automatically restart when done"** on the rename and full-recycle tasks, or **"Also connect it right now if that user is signed in"** on the new drive-mapping task (see below).
- Click **Run** on that small window to continue, or **Cancel** to back out without running anything.
- If you type something invalid (like letters in an IP address field, or a service name your target doesn't actually have), the tool will tell you exactly which field is wrong and why, before it tries to connect to anything.

**Mapping a network drive for someone (new in this version):** open the **Remote Tools** tab and check **"Map Network Drive for a User"**. In the window that pops up, fill in:
- **Shared Folder Path (UNC)** — the network address of the shared folder, written like `\\fileserver\share` or `\\fileserver\share\department` (two backslashes, then the server's name, then the shared folder's name). Ask whoever set up the shared folder for this exact path if you don't already have it.
- **Drive Letter** — which letter (D through Z) that shared folder should show up as on the target computer, e.g. `Z`. Letters A, B and C can't be used (they're reserved by Windows).
- **Map It For This User Account** — whose Windows sign-in this drive should appear for, written as `DOMAIN\username` (a work/domain account) or `.\username` (a local account on that computer). This is the person who will actually see the `Z:` drive when they open File Explorer — it is **not** necessarily the same account you used to connect to the target in Step 4.
- **Also connect it right now if that user is signed in** — leave this checked (the default) if you want the drive to appear immediately, assuming that person is currently signed in at that computer. Either way, the drive is saved so it reappears automatically every time that person signs in from now on, even if this box is unchecked or they're not signed in right now.
- **Replace an existing mapping on this drive letter** — leave this unchecked (the default) the first time. If that letter is already used for something else for that person, the task will stop and tell you, rather than silently overwriting it. Only check this box if you've confirmed it's safe to overwrite.

To check what's mapped for someone later, or to confirm a mapping worked, use **"List Mapped Network Drives (Saved Per User)"** (leave the username field blank to see everyone currently signed in). To undo a mapping, use **"Remove Mapped Network Drive for a User"** with the same drive letter and username.

### Step 7 — Understanding the danger warning
If any checked task is flagged sensitive, clicking PERFORM SELECTED first shows a pop-up listing every sensitive task by name and asking "Continue?". Read the list. Click **Yes** only if you meant to select all of them. This pop-up cannot be turned off — it's there on purpose. (Mapping and un-mapping a drive are both flagged sensitive, since they change what a specific person sees on their computer; just listing mapped drives is not.)

### Step 8 — Where the log is saved
Every session is also saved to a text file, automatically, at:
```
C:\PCAdminTool\PC_Admin_Logs\AdminTool_<target-name>_<date-time>.log
```
Open this any time in Notepad to review what happened, even after closing the tool.

### Troubleshooting (PowerShell Edition)
| Problem | What it means | What to do |
|---|---|---|
| "Windows protected your PC" | SmartScreen doesn't recognize this script yet | Click "More info" → "Run anyway" |
| Test Connection says "WinRM not reachable" | The target doesn't have WinRM turned on, or a firewall is blocking it | Go back to "Before you start" and run `Enable-PSRemoting -Force` on the TARGET |
| Test Connection says "Auth Failed" | Wrong username/password, or wrong format | Try `DOMAIN\username` instead of just `username`, or double check the password |
| A service name is rejected as invalid, even though you typed it correctly | **Fixed in this version.** Older copies of this tool wrongly rejected any service name containing a space (like "ManageEngine UEMS - Agent") | Update to this version. If it still happens, double-check you copied the exact **Service name** (not the longer, human-friendly "Display name") from Windows Services — use "List All Services" in this tool to see the exact spelling |
| "Fix these before running" mentions a shared-folder path or drive letter | The UNC path, drive letter, or username you typed doesn't match the expected format | UNC path must start with `\\` and have no quotes in it; drive letter must be a single letter D–Z; username must be `DOMAIN\name`, `name@domain.com`, or `.\name` |
| Drive-mapping task says the mapping was saved, but the drive doesn't appear right now | The target user either isn't signed in, or "connect it right now" was unchecked | The drive still appears automatically the next time that person signs in — this is expected, not an error |
| A domain computer rename fails ("Access is denied", RPC or "second logon" error) | In v3.6 and older the tool did not pass a domain login to the rename (the "double hop" problem). **Fixed in v3.7** — the tool now builds the domain login itself | Use v3.7 and the **Domain-Joined** rename with a domain admin account (no CredSSP needed). If it still fails, read the decoded reason in the log — see "Renaming a computer, step by step" |
| The tool won't open at all | Very old Windows, or PowerShell blocked by company policy | Confirm you're on Windows 10/11; ask your IT department if PowerShell script execution is restricted |
| Nothing visibly happens when you double-click `Run-AdminTool.bat` (no window, no error) | This edition deliberately hides its own PowerShell console window so it doesn't sit behind the tool's actual window — which used to also hide any startup crash completely. **Fixed in this version:** any such error is now saved to a file | Look for `PCAdminTool_last_error.log` in the same folder and open it in Notepad |

---

# PART 2 — Python Web-Service Edition

### What you need
- A computer to act as the "host" (can be Windows, or even Linux) — this runs the service permanently.
- Python 3.9 or later on that hosting computer.
- Any modern web browser on every computer that will USE the tool (Chrome, Edge, Firefox) — nothing installed there at all.

### Step 1 — Install Python (skip if already installed)
Download from `https://www.python.org/downloads/`. During install, **tick "Add Python to PATH"** — this is the single most common thing people forget, and without it the next steps won't work.

### Step 2 — Get the files
Unzip `PC_Admin_Tool_WebService_Edition.zip` on the hosting computer, e.g. `C:\PCAdminTool\`.

### Step 3 — Try it first in test mode (recommended before installing it permanently)
Double-click **`run_console_testmode.bat`**. A window opens and stays open (don't close it) — this installs dependencies automatically the first time, then starts the tool. You'll see a numbered `[CHECKPOINT ...]` line before and after each step it performs — this is normal and expected; it's there so that if anything ever does go wrong, you can see exactly where. Open a browser on the SAME computer and go to `http://localhost:3037`. If the page loads, it's working. Close the window (or press Ctrl+C, then any key) to stop the test — the window is designed to always tell you what happened and wait for a keypress before closing (see the note on v3.6 in the Troubleshooting table below if one ever does still vanish instantly).

**Don't run this at the same time as the installed service (Step 4 below).** If you already installed this tool as a permanent background service, it's already using this same port — test mode will tell you so plainly and explain what to do, rather than silently failing.

### Step 4 — Install it as a real always-on service (once you're happy with testing)
Double-click **`install_service.bat`** and approve the UAC prompt. This:
- Installs any missing dependencies.
- Removes any older copy of this service and its old firewall rule automatically, so you don't need to manually clean up an old version first. **On your very first-ever install, you'll see a line saying a service could not be found or was not running — that's completely normal** (there's nothing to remove yet); it's informational, not an error, and the install continues normally.
- Registers it as a proper Windows Service (shows up in `services.msc`, starts automatically every time the computer boots, keeps running with no window open).
- Opens the firewall for port **3038**.

Like test mode, this window shows a numbered `[CHECKPOINT ...]` line before and after every step, so if anything doesn't work, you'll be able to see exactly which step it was.

### Step 5 — Use it from any computer on the network
On any OTHER computer on the same network, open a browser and go to:
```
http://<hosting-computer-name-or-IP>:3038
```
(Ask whoever set this up for the exact address if you don't know it.)

### Step 6 — Using the interface
- Fill in Hostname/IP, Username, Password, and Auth Transport at the top, then click **Test Connection**.
- Click category tabs across the top (Cleanup, Disk, Performance, Windows Health, Network, Power Recycle, Remote Tools, Admin Consoles — 85 tasks total) to browse tasks.
- Any task needing extra information shows its input fields directly under its name, in the task list itself (not a separate pop-up) — fill them in before checking the box.
- **Mapping a network drive for someone:** open the Remote Tools tab, find **"Map Network Drive for a User"**, and fill in the Shared Folder Path, Drive Letter, and the user account it's for, directly under that task — the same fields and same meaning as described in Part 1, Step 6 above. The shared-folder-path box is wider than the others so a long path is easy to read and edit.
- Click **RUN SELECTED TASKS**. If anything checked is sensitive, you'll get a confirmation pop-up first, listing exactly which ones.
- The output streams into the log area live, as each task runs.

### Step 7 — Stopping or removing it later
Double-click `uninstall_service.bat` (as Administrator). This stops the service, removes it from `services.msc`, and removes every firewall rule this tool has ever used on this machine (including older ports from previous versions).

### Troubleshooting (Web-Service Edition)
| Problem | What it means | What to do |
|---|---|---|
| `install_service.bat` prints a line saying a service could not be found, was not installed, or was not running, right after "Removing any previous version..." | **This is normal, not an error** — it just means there was nothing to remove yet (a first-ever install) | Nothing — keep watching, the install continues automatically |
| A launcher window says `python` did not run correctly, right after listing paths under CHECKPOINT 2/3 | Python genuinely isn't working from where this script runs. If EVERY path listed is under `...\WindowsApps\...`, that's a Windows-provided placeholder with no real Python behind it | Install real Python from python.org, tick "Add Python to PATH", make sure it comes before any other python entries — if a real path (like `C:\PythonXX\python.exe`) was ALSO listed, this should now pass on its own |
| `run_console_testmode.bat` or `install_service.bat` opens and closes again **instantly, before any checkpoint even appears** | **This was a genuine bug, fixed in v3.6** — an unescaped character in one of the launcher files made Windows abort the whole script before it could print anything. It was not caused by anything on your PC | Update to this version; this specific failure should no longer be possible in any launcher in this package |
| Either window opens, prints one or more `[CHECKPOINT ...]` lines, then closes without reaching the final "Press any key" prompt | Something failed partway through — the checkpoints tell you where | Note the LAST checkpoint number shown — that pinpoints exactly where. If it is right after "Removing any previous version...", see the row above; that exact spot was the v3.6 bug |
| `run_console_testmode.bat` or `install_service.bat` runs normally but `localhost` never responds | You likely already installed this tool as a permanent background service (Step 4), which is already using this same port — you don't need both running at once | Open `http://localhost:3037` directly (the already-running service may already be serving it), or stop the service first with `net stop PCAdminTool`, then try test mode again |
| Browser can't reach `http://<host>:3038` at all | Service isn't running, or firewall is blocking it | Check `services.msc` on the host for "PC Admin & Performance Tool - Web Service"; confirm port 3037 is allowed through the host's firewall |
| A service name is rejected as invalid, even though you typed it correctly | **Fixed in this version.** Older copies wrongly rejected any service name containing a space | Update to this version; use "List All Services" to copy the exact Name if unsure |
| A shared-folder path, drive letter, or username shows a red border / "is not valid" message | Format doesn't match what's expected | UNC path needs `\\server\share` (no quotes); drive letter is one letter D–Z; username is `DOMAIN\name`, `name@domain.com`, or `.\name` |
| Test Connection says "WinRM not reachable" | The TARGET doesn't have WinRM turned on | Go back to "Before you start" and run `Enable-PSRemoting -Force` on the TARGET (not the hosting computer) |
| Upgrading from an older version left the old service or firewall rule behind | An install/uninstall step was skipped | Run this version's `uninstall_service.bat` once, then `install_service.bat` again — it cleans up every port this tool has ever used (3030 through 3037, inclusive) |

---

# PART 3 — Python Native GUI Edition

### What you need
- Python 3.9+ on the admin computer (Tkinter, which this uses for its window, is included automatically with Windows installs of Python).

### Step 1 — Get the files
Unzip `PC_Admin_Tool_PythonGUI_Edition.zip` anywhere convenient.

### Step 2 — Run it
Double-click `install_and_run.bat`. First run installs the one dependency (`pypsrp`) automatically, then opens the tool's window. After that, you can also just double-click `PCAdminTool.pyw` directly.

### Step 3 — Using the interface
Same layout and same 85 tasks as the other two editions — Hostname/IP, Username, Password, Auth Transport, Test Connection, then category tabs. Any task needing input shows its fields directly under its row in the task list (same as the Web edition, not a separate pop-up).

**Mapping a network drive for someone:** identical fields and meaning to Part 1/Part 2 above — Shared Folder Path, Drive Letter, User Account, "connect now," and "replace existing." In this edition, the shared-folder-path field automatically takes up the whole row by itself so a long path is never cramped next to another field.

### Troubleshooting (Python GUI Edition)
| Problem | What it means | What to do |
|---|---|---|
| A service name is rejected as invalid, even though you typed it correctly | **Fixed in this version** — see the note at the top of this guide | Update to this version |
| The app won't launch, mentions `pypsrp` | Dependency didn't install | Open Command Prompt, run `pip install pypsrp`, try again |
| A shared-folder path, drive letter, or username field turns red / shows an error | Format doesn't match what's expected | Same formats as Part 1/2: `\\server\share`, a single letter D–Z, and `DOMAIN\name` / `name@domain.com` / `.\name` |
| The window never appears after double-clicking `install_and_run.bat` | **Fixed in this version** — the launcher now checks for the most common causes before attempting to open the window at all, with a clear on-screen message | If it still doesn't appear, check `PCAdminTool_last_error.log` in the same folder |

---

# PART 4 — Understanding the tool (applies to all three editions)

### The eight categories, in plain terms
- **Cleanup** — deletes temporary junk (temp files, cache, old logs) to free up space.
- **Disk** — reports on and improves drive health/space (not destructive by itself).
- **Performance** — speeds up a sluggish computer (power plan, visual effects, search indexing).
- **Windows Health** — diagnoses and repairs Windows itself (system file checks, update history).
- **Network** — fixes and reports on network connectivity problems.
- **Power Recycle** — does everything a physical power-cycle (unplug and replug) would fix, without an actual power cycle: restarting a stuck driver, network adapter, or USB device in software, escalating up to a full restart only as a last resort.
- **Admin Consoles** — opens Windows' own admin windows (Computer Management, Services, Event Viewer, Firewall, a remote PowerShell, Remote Desktop …) already connected to the target. Explained in full below.
- **Remote Tools** — the "swiss-army knife" category: static IP setup, renaming a computer, shadow-copy (System Restore point) management, scheduled task lookup, service restart/listing, Computer Management, and (new in this version) mapping a network drive for someone.

### Renaming a computer, step by step

**Which of the three rename tasks do I pick?** Look at what the target PC is joined to:
- The PC is on your company network and you log in to it with a company account (it is "joined to a domain") → **Rename Computer (Domain-Joined)**. This is the one most offices need.
- The PC is a standalone/home-style PC (it is in a "workgroup") → **Rename Computer (Workgroup/Local)**.
- Not sure? Just tick the Domain-Joined one: if the PC is *not* on a domain, the tool tells you so and changes nothing. Likewise, the Workgroup one refuses on a domain PC, on purpose, because renaming only the PC and not its company-network account can lock people out.
- **Rename via WMIC (Legacy)** is only for very old PCs. On modern Windows it quietly does the same job another way, so you can use it as a second try.

**Steps**
1. Fill in Hostname/IP, your **domain admin** user name (like `admin@yourcompany.local` or `YOURCOMPANY\admin`) and password. Press **Test Connection**.
2. Tick the rename task. A small form asks for **New Computer Name** (1–15 letters, digits or hyphens, e.g. `PC-CSD`) and has a checkbox **Automatically restart when done**. Leave it ticked if the PC can restart now; untick it to restart later yourself (the new name does **not** take effect until the restart).
3. Press **Run / Perform Selected**, confirm the warning.
4. Read the result lines. Success looks like `Method 1 … succeeded` and `Rename submitted`. If the restart box was ticked, the PC restarts after about 15 seconds — that is normal; any other tasks you ticked are skipped with a message, run them again after the PC is back.

**If it says FAILED** the tool now tells you why in plain words:
| Message | What it means | What to do |
|---|---|---|
| `code 2224 … account with the NEW name already exists` | The company directory already has a computer with that new name | Choose another name, or ask your directory admin to delete the old stale account |
| `code 5` / `Access denied` | The account you typed is not allowed to rename computers in the directory | Use a Domain Admin account |
| `code 1326` / `Logon failure` | Wrong user name or password for the domain | Retype them; use the form `name@yourcompany.local` |
| `code 53` / `1355` | The PC cannot find your domain controller (DNS/VPN problem) | Check the PC's network/DNS, then try again |
| `Secure channel to domain: False` | The PC has lost its trust relationship with the domain | Needs a domain re-join (not something this tool does) |

You no longer need the special "CredSSP" login type for renaming — the tool handles the domain login by itself, and it never shows or saves your password.

### What happens when a task changes the network

Tasks like **Flush DNS, Reset TCP/IP, Set Static IP, Set DHCP, Restart Network Adapter(s)** briefly cut the target's network — including the connection this tool is using to talk to it. Old versions froze here. Now:
1. The tool starts the task **on the target itself** (in the background), so it finishes even if the connection drops.
2. You may see `Connection to the target interrupted (expected for network changes) -- reconnecting...` followed by `Waiting for the target to come back...` lines. **This is normal. Do not close the tool.** It tries again every few seconds for up to 5 minutes.
3. As soon as the target answers, you see `Reconnected` and then the **real result** of the task, and the next tasks carry on.
4. **Set Static IP changes the address of the PC.** If you connected using the old IP, the tool also tries the **new IP** you entered and continues with whichever answers. If you connected by *name*, make sure the name still resolves to the new IP (DNS can take a few minutes to update).
5. If it still cannot reach the PC after 5 minutes it says the change was started and most likely applied, and tells you to reconnect to the new address.

**Restart tasks** (Force Restart, Force Sign-out & Restart, Full Soft-Recycle, rename with restart): the connection closing is the **expected** result, shown as a green line. Everything you ticked after it is skipped with the message "target is restarting"; run those again once the PC is back (about 1–3 minutes).

**Very long tasks** (DISM RestoreHealth, DISM Component Cleanup, CHKDSK scan) run the same background way and can take 10–60 minutes. The log shows `...still running on the target (NNs)` every 30 seconds. Press **Stop** to stop *waiting* (the task itself keeps running on the target).

### Resizing the shadow-copy (VSS / System Restore) storage

Task: **Resize VSS Shadow Storage (Max Size)** in *Remote Tools*. It asks for:
- **Volume** – the drive letter, e.g. `C`.
- **Max size** – how much disk space shadow copies may use. Allowed forms: `10%` (percent of the drive, 1–100), `20GB`, `51200MB`, or `UNBOUNDED` (no limit). **A unit is required** — `20` alone is refused (Windows would read it as 20 bytes).
Examples: small SSD → `5%`; data drive with history you want to keep → `20%`; remove the cap → `UNBOUNDED`.
The task shows the size **before** and **after**. Making the limit smaller than what is already used makes Windows delete the **oldest** restore points — that is why the task carries the "!" warning. If it says no association exists, the drive has no shadow copies yet.

### Admin Consoles, step by step

**What it is:** each task opens one of Windows' own admin windows, already pointed at the target, using the user name and password you entered at the top. It is like walking up to the target and opening the tool locally — without leaving your desk.

**Important — where the window appears:**
- **PowerShell Edition and Python GUI Edition:** the window appears on **your own screen**.
- **Web-Service Edition:** the window appears on the computer that **runs the web service**. If you installed the service on your own PC and use `http://localhost:3038`, that is your screen. If the service runs on a server and you browse from another PC, the window opens *on the server* — use one of the desktop editions for the consoles.

**Steps:** 1) Enter Hostname/IP, user, password, Test Connection. 2) Open the **Admin Consoles** tab. 3) Tick one task (you can tick several; they open one after another). 4) Run. 5) Read the lines under the task — they say what was launched and what to do if the window shows the wrong computer.

| Task | What you get | Good to know |
|---|---|---|
| Computer Management | The "Manage this PC" window with Disk Management, Device Manager, Event Viewer, Services, Shared Folders, Task Scheduler | The all-in-one choice |
| Disk Management | Partitions, drive letters, extend/shrink | |
| Device Manager | List of devices on the target | **View only** on Windows 8 / Server 2012 and newer — a Windows limit, not a tool limit. To change drivers use *Remote Desktop* below |
| Services | Start / stop / configure services | |
| Event Viewer | The target's Windows logs | |
| Shared Folders | Shares, who is connected, open files | |
| C$ admin share | File Explorer on the target's C: drive | |
| Firewall (guided) | Windows Firewall with Advanced Security | Windows cannot pre-connect this one: the tool prints 3 clicks — right-click the top-left item → *Connect to Another Computer* → type the target |
| Remote PowerShell window | A blue PowerShell window already logged in on the target | Run any command there. If it complains the host is "not trusted", run the `TrustedHosts` line the tool prints, once, as Administrator on your PC |
| Remote Command Prompt | A black command window running on the target | It asks you to **type the password in that window** (Windows will not let a tool pass it safely) |
| Remote Desktop | The target's full desktop | Use this for everything that has no remote version: Device Manager with changes, **Disk Cleanup**, **Defrag GUI**, **Network Connections**, Firewall. The credential is stored on your PC for it — remove it afterwards with the `cmdkey /delete:…` line the tool prints |

**If a console opens but shows YOUR computer instead of the target:** right-click the top item in the left pane → **Connect to another computer…** → type the target name. (Some Windows builds ignore the pre-connect switch for certain consoles.) Tell me which one and I will adjust it.

**If it says `error 1219` / "multiple connections":** Windows already has a connection to that target under a different account. Open Command Prompt on your PC and run `net use \\TARGET\IPC$ /delete`, then run the task again.

**Safety notes:** your password is never written to the log or the screen. For the connection step Windows needs it on a command line for a split second *on your own PC* (not on the network). If that matters in your environment, use "Remote PowerShell window" or "Remote Desktop" and type the password yourself where asked.

### How to use Power Recycle without guessing
Start with a read-only "list" or "diagnose" task to find out WHICH device/adapter is causing trouble, then use a "cycle"/"restart"/"disable-then-enable" task targeting that specific one. Only reach for "Full Soft-Recycle Bundle" (which touches every adapter and USB device at once, then optionally restarts) when you don't know which specific thing is wrong, or nothing targeted has worked.

### "Open Computer Management (Connected to Target)," explained
This opens Windows' own Computer Management console — the same window you'd get by right-clicking "This PC" → "Manage" — already connected to the target computer, so you can browse its Disk Management, Device Manager, Event Viewer, Services, and more, directly.

**Which computer the window opens ON depends on which edition you're using:**
- **PowerShell Edition and Python GUI Edition:** it opens on YOUR OWN computer (the one you're sitting at), connected to the target. This is the only way it can work for these two — a window has to appear somewhere with an actual screen, and that's your desktop.
- **Web-Service Edition:** it opens on whichever computer is HOSTING the web service. If you're running the service on your own PC and browsing to `localhost` (the most common setup), that's the same computer you're sitting at, so it behaves exactly like the other two editions. If someone else is hosting the service on a different machine and you're browsing to it from your own PC, the window opens on THEIR machine, not yours — a web page can never open a window on your own screen, no matter which tool serves it. In that case, the tool tells you the exact command to run yourself instead.

### Mapping a network drive for someone, explained from scratch
If you've never mapped a network drive before: normally, if you sat down at someone's desk, opened File Explorer, right-clicked "This PC," chose "Map network drive," typed in a shared folder's address, and picked a drive letter — that's exactly what this feature does, remotely, without you needing to be at their desk or even for them to be sitting there at the time.

The three pieces of information it needs are the same three things Windows itself would ask you for: the shared folder's address (the UNC path, `\\servername\sharename`), the letter you want it to show up as (like `Z:`), and — the one thing this tool needs that you specify explicitly, since it's acting on someone else's behalf — **whose Windows sign-in** the drive should appear for. That's not necessarily the account you're using to connect to their computer in the top section of the tool; it's whichever person will actually be sitting at that computer seeing the `Z:` drive appear in their own File Explorer.

Once mapped, it stays mapped for that person permanently, reappearing every time they sign in, until someone removes it (with "Remove Mapped Network Drive for a User") or the shared folder itself is deleted/moved.

### The Auto-Restart checkbox, in plain terms
On a few tasks (renaming a computer, the full Power-Recycle bundle), you get to choose: leave the checkbox checked for the simple old behavior (it restarts the target automatically the moment it's done), or uncheck it to have the tool do the actual work but leave the restart for you to trigger later yourself — useful if you're doing this during business hours and don't want to interrupt someone without warning.

### What the "!" warning means
A task marked with "!" (or shown in a highlighted/red style, depending on edition) is flagged sensitive — it could restart the target, interrupt its network connection, delete a restore point, or change what a specific person sees on their computer (like a drive mapping). You'll always get a confirmation prompt listing exactly which sensitive tasks you're about to run before anything happens.

---

# PART 5 — Quick troubleshooting reference (all editions)

| Symptom | Likely cause | Fix |
|---|---|---|
| Rename says `Access is denied` (old versions) or `FAILED` | Domain login could not be completed | Update to v17, use the **Domain-Joined** task with a **domain admin** account — see "Renaming a computer, step by step" |
| The tool shows "reconnecting…" for a while after a network task | Normal — the target's network was cut on purpose and is coming back | Wait up to 5 minutes; do not close the tool |
| After Set Static IP the tool says it could not reach the PC | You connected by the old IP/name | Reconnect using the NEW IP |
| A console window opened on the wrong PC (Web edition) | The Web edition opens consoles on the PC that hosts the service | Use the PowerShell or Python GUI edition, or host the service on your own PC |
| A console shows your own PC, not the target | That Windows console ignored the pre-connect switch | Right-click the top item → *Connect to another computer…* |
| `error 1219` when opening a console | Windows has a different login saved for that target | `net use \\TARGET\IPC$ /delete`, then retry |
| Tasks after a restart task say "Skipped: the target is restarting" | Intended | Run them again when the PC is back |
| A launcher window closes **instantly** — no checkpoint ever printed, nothing readable | You're on an older version with a launcher-script bug (present in v3.3 through v3.5, in three different launcher files) | Update to this version (v3.6) — this specific failure is fixed at the root cause |
| A launcher window prints one or more checkpoints, *then* closes without a final "Press any key" prompt | Something genuinely failed partway through | Note the last checkpoint shown — every launcher's own Troubleshooting table (Parts 1–3) explains what each checkpoint number means |
| Can't connect to a target at all | WinRM not enabled on the TARGET | Run `Enable-PSRemoting -Force` on the target (see "Before you start") |
| Connects, but a specific task fails | Target-side issue (service doesn't exist, path doesn't exist, etc.) | Read the exact error text in the log — it names what went wrong |
| A field is rejected as invalid | The value doesn't match the expected format for that field | Every field's pop-up/tooltip help text shows an example of the expected format |
| A service name specifically is rejected | You're on an older version with the space-in-service-name bug | Update to this version (fixed since v3.2) |
| A mapped drive doesn't show up immediately | The target user wasn't signed in, or "connect now" was unchecked | It will appear automatically at their next sign-in — check with "List Mapped Network Drives" |
| Domain rename fails with a login/RPC error | Fixed in v3.7 (no CredSSP needed any more). Remaining causes: wrong password, no rights, new name already exists in the directory, PC cannot reach a domain controller | Read the decoded reason line in the log and follow the table in "Renaming a computer, step by step" |

---

## Appendix A — Enabling WinRM on a target, copy-paste version

On the **target** computer, in an elevated PowerShell window:
```powershell
Enable-PSRemoting -Force
```
If the target is a Workgroup/home computer (not on a company Domain), also run:
```powershell
Set-Item WSMan:\localhost\Client\TrustedHosts -Value "*" -Force
```

---

## Appendix B — Glossary
- **Target** — the computer being managed.
- **Admin computer** — the computer you're sitting at, running this tool.
- **WinRM** — Windows' built-in remote-management feature; must be turned on with `Enable-PSRemoting -Force`.
- **Credentials** — a username + password with admin rights on the target.
- **Elevated / Run as Administrator** — running with full permissions; Windows asks you to confirm this.
- **Port** — a numbered connection slot a running program listens on (this tool's Web edition: 3038).
- **Service** — a background program that keeps running, starts on boot, with no window to keep open.
- **Double-hop** — a known Windows limitation where credentials used for one remote connection can't automatically be reused for a second one (matters for domain computer rename).
- **VSS / Shadow Copy** — Windows' snapshot system behind "Previous Versions" and System Restore points.
- **UNC path** — a shared folder's network address, written `\\servername\sharename` (used by the network-drive-mapping tasks).
- **Mapped drive** — a shared folder made to appear as a lettered drive (like `Z:`) in File Explorer.
- **Drive letter** — the single letter (D through Z, for this tool's mapping feature) a mapped drive appears as.
