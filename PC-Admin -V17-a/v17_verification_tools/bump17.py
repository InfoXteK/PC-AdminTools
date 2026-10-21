import re, io
R="/home/claude/v17/"
W=R+"PC_Admin_Tool_WebService_Edition/"; G=R+"PC_Admin_Tool_PythonGUI_Edition/"; P=R+"PC_Admin_Tool_PowerShell_Edition/"
def rb(p): return open(p,"rb").read()
def wb(p,b): open(p,"wb").write(b)
def sub(p,pairs,count_check=True):
    b=rb(p).decode("utf-8")
    for old,new,*cnt in pairs:
        n=b.count(old)
        if n==0: raise SystemExit(f"MISSING in {p}: {old!r}")
        if cnt and cnt[0]!=n: raise SystemExit(f"COUNT {p}: {old!r} expected {cnt[0]} got {n}")
        b=b.replace(old,new)
    wb(p,b.encode("utf-8"))

CL_WEB='''  v3.7 (port 3037 -> 3038):
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
         browser. Authentication: "net use \\\\host\\IPC$" for MMC/Explorer,
         cmdkey TERMSRV/host for RDP, environment hand-over for PowerShell,
         prompt for winrs. Hostnames are validated (no argument injection).
'''
CL_SHORT='''  v3.7: same functional changes as the Web edition's v3.7 entry, ported
  1:1 -- PC rename fixed on domain-joined targets (explicit domain credential
  built inside the remote session, WMI fallback, decoded error codes), detached
  run-and-reconnect for network-changing and very long tasks, reboot-class tasks
  treated as expected, VSS storage resize, DISM RestoreHealth / component
  cleanup, CIM replacements for WMIC, CHKDSK online scan, and the new
  "Admin Consoles" category (85 operations in total). These consoles open on
  THIS PC, connected to the target. See the Web edition's README.
'''
# ---------------- Web
sub(W+"app.py",[
 ("PC Admin & Performance Troubleshooting Tool  v3.6  — Web-Service Edition","PC Admin & Performance Troubleshooting Tool  v3.7  — Web-Service Edition",1),
 ("PORT 3037 -- reachable","PORT 3038 -- reachable",1),("http://<this-machine-IP>:3037","http://<this-machine-IP>:3038",1),
 ("SERVICE_PORT = 3037","SERVICE_PORT = 3038",1),
 ("PC Admin & Performance Tool v3.6 | All Rights Reserved","PC Admin & Performance Tool v3.7 | All Rights Reserved",1),
 ("PC ADMIN & PERFORMANCE TOOL  v3.6  -- Web-Service Edition","PC ADMIN & PERFORMANCE TOOL  v3.7  -- Web-Service Edition",1),
 ("PC Admin & Performance Tool  v3.6  -- Web-Service Edition","PC Admin & Performance Tool  v3.7  -- Web-Service Edition",1),
 ("  Port bumps alongside every versioned release are a standing project\n",CL_WEB+"\n  Port bumps alongside every versioned release are a standing project\n",1),
])
sub(W+"templates/index.html",[
 ("v3.6 &middot; Web-Service Edition &middot; port 3037","v3.7 &middot; Web-Service Edition &middot; port 3038",1),
 ("  useraccount: /^(?:(?:\\.|","  vsssize: /^(UNBOUNDED|\\d{1,3}%|\\d{1,9}(KB|MB|GB|TB|PB|EB))$/i,\n  useraccount: /^(?:(?:\\.|",1),
 ("  useraccount: 'DOMAIN\\\\user, user@domain.com or .\\\\localuser',\n","  useraccount: 'DOMAIN\\\\user, user@domain.com or .\\\\localuser',\n  vsssize: 'a size such as 10%, 20GB, 51200MB or UNBOUNDED (a unit is required)',\n",1),
])
sub(W+"pcadmintool_service.py",[("SERVICE_PORT = 3037","SERVICE_PORT = 3038",1)])
sub(W+"pcadmintool.service.template",[("port 3037","port 3038",1)])
sub(W+"install_and_run.sh",[("3037","3038")])
for f in ["run_console_testmode.bat","install_service.bat","uninstall_service.bat","check_port.bat"]:
    b=rb(W+f).decode("utf-8")
    b=b.replace("set PCA_PORT=3037","set PCA_PORT=3038").replace("3036 3037)","3036 3037 3038)").replace("covers port 3037","covers port 3038")
    b=b.replace("(v3.6)","(v3.7)").replace("Edition v3.6","Edition v3.7").replace("^(v3.6^)","^(v3.7^)")
    wb(W+f,b.encode("utf-8"))
# ---------------- Tk
sub(G+"PCAdminTool.pyw",[
 ("PC Admin & Performance Tool  v3.6  -- Native Python GUI Edition (Tkinter)","PC Admin & Performance Tool  v3.7  -- Native Python GUI Edition (Tkinter)",1),
 ('VER = "v3.6  Native','VER = "v3.7  Native',1),
 ("PC Admin & Performance Tool v3.6 | ","PC Admin & Performance Tool v3.7 | ",2),
 ("  line no longer runs the word Performance as a command. See the README.\n","  line no longer runs the word Performance as a command. See the README.\n\n"+CL_SHORT,1),
])
b=rb(G+"install_and_run.bat").decode("utf-8").replace("(v3.6)","(v3.7)"); wb(G+"install_and_run.bat",b.encode())
# ---------------- PS
b=rb(P+"PCAdminTool.ps1").decode("utf-8-sig")
for old,new in [("PC Admin & Performance Tool  v3.6 -- PowerShell GUI Edition","PC Admin & Performance Tool  v3.7 -- PowerShell GUI Edition"),
                ("Performance Tool v3.6  |","Performance Tool v3.7  |"),('$VER   = "v3.6  PowerShell','$VER   = "v3.7  PowerShell'),
                ("Performance Tool  v3.6  --  (c)","Performance Tool  v3.7  --  (c)"),("TOOL  v3.6 -- PowerShell Edition","TOOL  v3.7 -- PowerShell Edition")]:
    assert old in b,old; b=b.replace(old,new)
marker="#  power scheme afterwards instead of assuming success). The launcher\n#  (Run-AdminTool.bat) is also rewritten -- see the README.\n"
crlf="\r\n" in b
assert marker.replace("\n","\r\n") in b or marker in b
cl_ps="".join("#"+l[1:] if l.startswith("  ") else "#  "+l for l in CL_SHORT.splitlines(True))
if marker.replace("\n","\r\n") in b:
    b=b.replace(marker.replace("\n","\r\n"),marker.replace("\n","\r\n")+cl_ps.replace("\n","\r\n"))
else:
    b=b.replace(marker,marker+cl_ps)
open(P+"PCAdminTool.ps1","wb").write(("﻿"+b).encode("utf-8"))
b=rb(P+"Run-AdminTool.bat").decode().replace("(v3.6)","(v3.7)"); wb(P+"Run-AdminTool.bat",b.encode())
print("bumped")
