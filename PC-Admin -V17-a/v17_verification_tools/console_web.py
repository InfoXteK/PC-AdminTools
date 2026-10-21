CONSOLE = r'''
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
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _ps_quote(s):
    return "'" + s.replace("'", "''") + "'"


def _net_use_ipc(host, username, password):
    """Authenticate this PC to the target (IPC$) so MMC/Explorer inherit it. Returns a status line."""
    try:
        r = subprocess.run(["net", "use", f"\\\\{host}\\IPC$", f"/user:{username}", password,
                            "/persistent:no"],
                           capture_output=True, text=True, timeout=45)
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
                               capture_output=True, text=True, timeout=20)
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

'''
