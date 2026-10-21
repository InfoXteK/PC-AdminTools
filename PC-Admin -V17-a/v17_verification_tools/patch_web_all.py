import sys, re
S="/tmp/claude-0/-home-claude/553766bb-8ae3-5461-bdb9-0d251a8a8a22/scratchpad"
sys.path.insert(0,S)
from engine_web import ENGINE
from console_web import CONSOLE
from new_ops import NEW_OPS, CONSOLE_OPS
p="app.py"
s=open(p,encoding="utf-8").read()
def must(cond,msg):
    if not cond: raise SystemExit("ANCHOR FAIL: "+msg)

# 1 imports
must("import json, datetime, socket, re, os, time, threading, subprocess, platform\n" in s,"imports")
s=s.replace("import json, datetime, socket, re, os, time, threading, subprocess, platform\n",
            "import json, datetime, socket, re, os, time, threading, subprocess, platform, base64, secrets\n")

# 2 remove old Computer Management op
a=s.index('    {\n        "id": "rt_open_computer_management"')
b=s.index('    {\n        "id": "rt_restart_service"')
s=s[:a]+s[b:]

# 3 reboot ops: return before the session dies
must("Restart-Computer -Force\n" in s,"restart-computer")
s=s.replace("Restart-Computer -Force\n","shutdown.exe /r /f /t 3\n",1)
n=s.count("shutdown /g /f /t 0")
must(n>=2,"shutdown /g count %d"%n)
s=s.replace("shutdown /g /f /t 0","shutdown /g /f /t 3")

# 4 new ops appended before end of OPERATIONS
def render(o):
    d=[]
    d.append('    {\n        "id": %r,\n        "danger": %r,\n        "label": %r,\n        "category": %r,\n        "description": %r,\n'%(o["id"],o["danger"],o["label"],o["category"],o["description"]))
    if o.get("long"): d.append('        "long": True,\n')
    if o.get("params"):
        d.append('        "params": [\n'+",\n".join("            "+repr(x) for x in o["params"])+'\n        ],\n')
    assert '"""' not in o["command"]
    d.append('        "command": r"""%s"""\n    },\n'%o["command"])
    return "".join(d)
txt="\n    # ─── v3.7 additions ──────────────────────────────────────────────────────\n"
txt+="".join(render(o) for o in NEW_OPS)
txt+="\n    # ─── 🖥️ ADMIN CONSOLES (v3.7) ───────────────────────────────────────────\n"
for cid,label,desc in CONSOLE_OPS:
    txt+=render(dict(id=cid,danger=False,label=label,category="Admin Consoles",description=desc,
        command="\n# Handled by the host application (launch_console) -- never sent to the target.\nWrite-Output \"  (local console launcher)\"\n"))
end=s.index("]\n\n# ── Build safe metadata list")
s=s[:end]+txt+s[end:]

# 5 engine + console before run_remote_ps header banner
anchor="def make_session(hostname, username, password, transport=\"ntlm\"):"
must(anchor in s,"make_session")
s=s.replace(anchor,"def make_session(hostname, username, password, transport=\"ntlm\", fast=False):")
must("        connection_timeout=30,\n        read_timeout=180,\n        operation_timeout=170,\n" in s,"timeouts")
s=s.replace("        connection_timeout=30,\n        read_timeout=180,\n        operation_timeout=170,\n    )\n",
 "        connection_timeout=30,\n        read_timeout=180,\n        operation_timeout=170,\n    )\n    if fast:\n        # Short timeouts for polling/reconnecting while the target's network may be down.\n        kwargs.update(connection_timeout=10, read_timeout=30, operation_timeout=20)\n")
must("if fast:" in s,"fast kw")
m=s.index("def run_remote_ps(session, script, label=\"\"):")
s=s[:m]+ENGINE+"\n"+CONSOLE+"\n"+s[m:]

# 6 vsssize validator
vs='''_VSSSIZE_RE = re.compile(r"^(UNBOUNDED|\\d{1,3}%|\\d{1,9}(KB|MB|GB|TB|PB|EB))$", re.IGNORECASE)


def _validate_vsssize(raw):
    raw = raw.strip().upper().replace(" ", "")
    if not _VSSSIZE_RE.match(raw):
        return None, f"'{raw}' is not a valid shadow-storage size (use e.g. 10%, 20GB, 51200MB or UNBOUNDED)"
    if raw.endswith("%") and not (1 <= int(raw[:-1]) <= 100):
        return None, "a percentage must be between 1% and 100%"
    return raw, None


'''
k=s.index("PARAM_VALIDATORS = {")
s=s[:k]+vs+s[k:]
must('    "bool": _validate_bool,\n}' in s,"validators dict")
s=s.replace('    "bool": _validate_bool,\n}','    "bool": _validate_bool,\n    "vsssize": _validate_vsssize,\n}')

open(p,"w",encoding="utf-8").write(s)
print("part1 ok")
