import sys, re
S="/tmp/claude-0/-home-claude/553766bb-8ae3-5461-bdb9-0d251a8a8a22/scratchpad"
sys.path.insert(0,S)
from engine_web import ENGINE
from console_web import CONSOLE
from new_ops import NEW_OPS, CONSOLE_OPS
from rename_ops import DOMAIN, WORKGROUP, LEGACY
p="PCAdminTool.pyw"
s=open(p,encoding="utf-8").read()
def must(c,m):
    if not c: raise SystemExit("ANCHOR FAIL: "+m)
# imports
must("import subprocess\nfrom pathlib import Path\n" in s,"imp")
s=s.replace("import subprocess\nfrom pathlib import Path\n","import subprocess\nimport platform\nimport base64\nimport secrets\nfrom pathlib import Path\n",1)

def render(o):
    d=['    {\n        "id": %r,\n        "label": %r,\n        "category": %r,\n        "description": %r,\n'%(o["id"],o["label"],o["category"],o["description"])]
    if o.get("long"): d.append('        "long": True,\n')
    if o.get("needs_cred"): d.append('        "needs_cred": True,\n')
    if o.get("params"):
        d.append('        "params": [\n'+",\n".join("            "+repr(x) for x in o["params"])+'\n        ],\n')
    assert '"""' not in o["command"]
    d.append('        "command": r"""%s""",\n        "danger": %r,\n    },\n'%(o["command"],o["danger"]))
    return "".join(d)
NAME=dict(key="NEW_NAME",kind="computername",label="New Computer Name",required=True)
AR=dict(key="AUTO_RESTART",kind="bool",label="Automatically restart when done",required=True,default="true",help="Unchecked: rename now, restart later yourself (name won't take effect until then)")
ren=[dict(id="rt_rename_pc_domain",danger=True,needs_cred=True,category="Remote Tools",label="Rename Computer (Domain-Joined)",
   description="Renames a domain member using the username/password you connected with as an explicit domain credential (no CredSSP needed); restart optional",params=[NAME,AR],command=DOMAIN.lstrip("\n")),
 dict(id="rt_rename_pc_workgroup",danger=True,needs_cred=True,category="Remote Tools",label="Rename Computer (Workgroup/Local)",
   description="Local rename for NON-domain targets (refuses on a domain member and says so); restart optional",params=[NAME,AR],command=WORKGROUP.lstrip("\n")),
 dict(id="rt_rename_pc_wmic_legacy",danger=True,needs_cred=True,category="Remote Tools",label="Rename Computer via WMIC (Legacy -- Manual Restart Required)",
   description="WMIC where present; automatically uses the same WMI rename method via CIM when WMIC is removed (Win11 24H2+) or the target is domain-joined",params=[NAME],command=LEGACY.lstrip("\n"))]
a=s.index('    {\n        "id": "rt_rename_pc_domain"')
b=s.index('    {\n        "id": "rt_vss_view"')
s=s[:a]+"".join(render(o) for o in ren)+s[b:]
# remove old CM op
a=s.index('    {\n        "id": "rt_open_computer_management"')
b=s.index('    {\n        "id": "rt_restart_service"')
s=s[:a]+s[b:]
# reboot ops
must("Restart-Computer -Force\n" in s,"rc")
s=s.replace("Restart-Computer -Force\n","shutdown.exe /r /f /t 3\n",1)
must(s.count("shutdown /g /f /t 0")>=2,"sd")
s=s.replace("shutdown /g /f /t 0","shutdown /g /f /t 3")
# new ops
txt="\n    # ─── v3.7 additions ──────────────────────────────────────────────────────\n"+"".join(render(o) for o in NEW_OPS)
txt+="\n    # ─── ADMIN CONSOLES (v3.7) ───────────────────────────────────────────────\n"
for cid,label,desc in CONSOLE_OPS:
    txt+=render(dict(id=cid,danger=False,label=label,category="Admin Consoles",description=desc,
      command="\n# Handled by the host application (launch_console) -- never sent to the target.\nWrite-Output \"  (local console launcher)\"\n"))
end=s.index("]\n\nCATEGORIES = list")
s=s[:end]+txt+s[end:]
s=s.replace('assert len(OPERATIONS) == 67, f"Expected 67 operations, got {len(OPERATIONS)}"','assert len(OPERATIONS) == 85, f"Expected 85 operations, got {len(OPERATIONS)}"')
s=s.replace("assert len({o['id'] for o in OPERATIONS}) == 67,","assert len({o['id'] for o in OPERATIONS}) == 85,")
# validator
vs='''_VSSSIZE_RE = re.compile(r"^(UNBOUNDED|\\d{1,3}%|\\d{1,9}(KB|MB|GB|TB|PB|EB))$", re.IGNORECASE)


def _validate_vsssize(raw):
    raw = raw.strip().upper().replace(" ", "")
    if not _VSSSIZE_RE.match(raw):
        return None, f"'{raw}' is not a valid shadow-storage size (use e.g. 10%, 20GB, 51200MB or UNBOUNDED)"
    if raw.endswith("%") and not (1 <= int(raw[:-1]) <= 100):
        return None, "a percentage must be between 1% and 100%"
    return raw, None


'''
k=s.index("PARAM_VALIDATORS = {"); s=s[:k]+vs+s[k:]
s=s.replace('    "bool": _validate_bool,\n}','    "bool": _validate_bool,\n    "vsssize": _validate_vsssize,\n}')
# make_session fast
s=s.replace('def make_session(hostname, username, password, transport="ntlm"):','def make_session(hostname, username, password, transport="ntlm", fast=False):')
old="        connection_timeout=30,\n        read_timeout=180,\n        operation_timeout=170,\n    )\n"
must(old in s,"timeouts")
s=s.replace(old,old+"    if fast:\n        kwargs.update(connection_timeout=10, read_timeout=30, operation_timeout=20)\n",1)
# engine: Tk uses dict events and a module-level stop flag
eng=ENGINE.replace('def _ev(d):\n    return f"data: {json.dumps(d)}\\n\\n"','def _ev(d):\n    return d')
must("def _ev(d):\n    return d" in eng,"_ev swap")
eng="_stop_flag = threading.Event()   # shared with PCAdminApp.stop_flag\n"+eng
m=s.index("# ══════════════════════════════════════════════════════════════════════════\n#  CUSTOM CANVAS CHECKBOX")
s=s[:m]+eng+"\n"+CONSOLE+"\n"+s[m:]
s=s.replace("        self.stop_flag = threading.Event()\n","        self.stop_flag = _stop_flag       # same Event the engine polls\n",1)
# run_tasks: carry params for the worker
s=s.replace('                op2 = dict(op)\n                op2["command"] = cmd\n','                op2 = dict(op)\n                op2["command"] = cmd\n                op2["_params"] = dict(self.param_values.get(op["id"], {}))\n',1)
# worker
a=s.index("            # rt_open_computer_management never goes to the remote target --")
bm="            elapsed = round(time.time() - t0, 1)\n"
b=s.index(bm,a)
new='''            if target_rebooting:
                self.q.put(("log", "warn", "     Skipped: the target is restarting -- run this task again once it is back online."))
                self.q.put(("log", "dim", ""))
                continue

            # v3.7 Admin Consoles: open on THIS PC, connected to the target.
            if op["id"] in CONSOLE_OP_IDS:
                for line in launch_console(op["id"], cur_host, user, pwd, transport):
                    self.q.put(("log", "out", f"     {line}"))
                self.q.put(("log", "dim", ""))
                continue

            t0 = time.time()
            tid = op["id"]
            cmd_text = op["command"]
            if op.get("needs_cred"):
                cmd_text = build_cred_prelude(user, pwd) + cmd_text
            tparams = op.get("_params", {})

            if tid in NETWORK_BLIP_OPS or op.get("long"):
                alt_hosts = []
                if tid == "rt_set_static_ip":
                    new_ip = (tparams.get("IP") or "").strip()
                    if new_ip and new_ip != cur_host:
                        alt_hosts.append(new_ip)
                self.q.put(("log", "dim", "     Network-changing / long task: running detached on the target; the tool reconnects and fetches the result."))
                stdout, stderr, ok, used_host = self._drive(detached_run_gen(
                    session, [cur_host] + alt_hosts, user, pwd, transport, cmd_text,
                    DETACH_LONG_WAIT if op.get("long") else DETACH_BLIP_WAIT))
                if used_host != cur_host:
                    cur_host = used_host
                    self.q.put(("log", "info", f"     Target is now reached at {cur_host}."))
                session = make_session(cur_host, user, pwd, transport)
            else:
                stdout, stderr, ok = run_remote_ps(session, cmd_text)
                if not ok and stderr.startswith(("TRANSPORT_ERR", "TIMEOUT_ERR")):
                    if expects_reboot(tid, tparams):
                        self.q.put(("log", "ok", "     Connection closed because the target is restarting -- this is the expected result."))
                        stdout, stderr, ok = "  Restart requested; the target is going down.", "", True
                        target_rebooting = True
                    else:
                        self.q.put(("log", "warn", "     Connection lost -- reconnecting..."))
                        s2, h2 = self._drive(reconnect_gen([cur_host], user, pwd, transport))
                        if s2 is not None:
                            session = make_session(cur_host, user, pwd, transport)
                            self.q.put(("log", "ok", "     Session reconnected -- retrying task"))
                            stdout, stderr, ok = run_remote_ps(session, cmd_text)
                        else:
                            self.q.put(("log", "err", "     Reconnect failed -- the target did not come back in time"))
            if ok and tid in (REBOOT_OPS | CONDITIONAL_REBOOT_OPS) and any(mk in stdout for mk in REBOOT_MARKERS):
                target_rebooting = True

'''
s=s[:a]+new+s[b:]
# state vars + _drive helper
s=s.replace("        total = len(selected)\n        for idx, op in enumerate(selected, start=1):\n",
            "        total = len(selected)\n        cur_host = host\n        target_rebooting = False\n        for idx, op in enumerate(selected, start=1):\n",1)
must("cur_host = host" in s,"cur_host")
drive='''    _TAGMAP = {"info": "info", "dim": "dim", "warning": "warn", "success": "ok", "error": "err"}

    def _drive(self, gen):
        """Run an engine generator, forwarding its progress events to the log; return its result."""
        try:
            while True:
                e = next(gen)
                if isinstance(e, dict) and e.get("text"):
                    self.q.put(("log", self._TAGMAP.get(e.get("type"), "out"), e["text"]))
        except StopIteration as si:
            return si.value

    def _run_worker(self, host, user, pwd, transport, selected):'''
s=s.replace("    def _run_worker(self, host, user, pwd, transport, selected):",drive,1)
open(p,"w",encoding="utf-8").write(s)
print("ok")
