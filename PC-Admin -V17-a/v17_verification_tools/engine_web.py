# Engine source block inserted into app.py before run_remote_ps (Web edition).
ENGINE = r'''
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

'''
