p="app.py"
s=open(p,encoding="utf-8").read()
def must(c,m):
    if not c: raise SystemExit("ANCHOR FAIL: "+m)

# A. state vars before task loop
a="        total = len(selected)\n        for idx, task in enumerate(selected):\n"
must(a in s,"loop head")
s=s.replace(a,"        total = len(selected)\n        cur_host = hostname          # may change if a task re-addresses the target\n        target_rebooting = False\n        for idx, task in enumerate(selected):\n")

# B. skip-after-reboot + generic console handler (replace old rt_open_computer_management block)
start=s.index("            # rt_open_computer_management: a Flask server cannot open a window")
endmark='                for line in msg.splitlines():\n                    yield ev({"type": "info", "text": f"    {line}"})\n                    lf(f"    {line}")\n                continue\n'
e=s.index(endmark,start)+len(endmark)
new='''            if target_rebooting:
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
'''
s=s[:start]+new+s[e:]

# C. execution + reconnect block
st=s.index("            t_start = time.time()\n            cmd_text = final_commands.get(task[\"id\"], task[\"command\"])")
en_marker='                    yield ev({"type": "error", "text": f"    Reconnect failed: {e}"})\n                    lf(f"    Reconnect failed: {e}")\n'
en=s.index(en_marker,st)+len(en_marker)
newexec='''            t_start = time.time()
            tid = task["id"]
            cmd_text = final_commands.get(tid, task["command"])
            if task.get("needs_cred"):
                cmd_text = build_cred_prelude(username, password) + cmd_text

            if tid in NETWORK_BLIP_OPS or task.get("long"):
                # Network-changing or very long task: run DETACHED on the target and
                # poll, so a network drop / >170 s runtime cannot hang or kill this call.
                alt_hosts = []
                if tid == "rt_set_static_ip":
                    new_ip = (param_vals.get(tid, {}).get("IP") or "").strip()
                    if new_ip and new_ip != cur_host:
                        alt_hosts.append(new_ip)
                note = ("    Network-changing task: running detached on the target; the tool will reconnect and fetch the result."
                        if tid in NETWORK_BLIP_OPS else
                        "    Long-running task: running detached on the target; waiting for it to finish (no timeout at 170 s).")
                yield ev({"type": "dim", "text": note}); lf(note)
                stdout, stderr, success, used_host = yield from detached_run_gen(
                    session, [cur_host] + alt_hosts, username, password, transport,
                    cmd_text, DETACH_LONG_WAIT if task.get("long") else DETACH_BLIP_WAIT, log=lf)
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
'''
s=s[:st]+newexec+s[en:]
open(p,"w",encoding="utf-8").write(s)
print("ok")
