import sys, json, re, time, importlib.util, base64
sys.path.insert(0, "/home/claude/v17/PC_Admin_Tool_WebService_Edition")
spec = importlib.util.spec_from_file_location("appmod", "/home/claude/v17/PC_Admin_Tool_WebService_Edition/app.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
m.RECONNECT_WAIT_SECONDS = 0; m.DETACH_POLL_SECONDS = 0
print("ops:", len(m.OPERATIONS), "ids unique:", len({o['id'] for o in m.OPERATIONS}) == len(m.OPERATIONS))
print("cats:", m.CATEGORIES)
fails = []
def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond: fails.append(name)

# Fake target
class Target:
    def __init__(self): self.down_calls = 0; self.files = {}; self.tok = None; self.script_log = []; self.pending_polls = 2; self.reboot = False
T = Target()
def fake_make_session(h, u, p, t="ntlm", fast=False):
    return {"host": h, "fast": fast}
def fake_run(session, script, label=""):
    T.script_log.append(script)
    if T.down_calls > 0 and session["host"] == "10.0.0.5":
        T.down_calls -= 1
        return "", "TRANSPORT_ERR:connection reset", False
    if "RECONNECT_OK" in script: return "RECONNECT_OK", "", True
    if "SESSION_OK" in script: return "SESSION_OK", "", True
    if "PCAT_LAUNCHED" in script:
        mm = re.search(r"\$tok = '([0-9a-f]+)'", script); T.tok = mm.group(1)
        b64 = re.search(r"FromBase64String\('([^']+)'\)\)\n\$cl", script).group(1)
        body = base64.b64decode(b64)
        assert body[:3] == b"\xef\xbb\xbf"
        T.files["wrapper"] = body.decode("utf-8-sig")
        T.down_calls = 3   # network blip right after launch
        return "PCAT_LAUNCHED:1234", "", True
    if "PCAT_PENDING" in script:
        if T.pending_polls > 0: T.pending_polls -= 1; return "PCAT_PENDING", "", True
        return "  Flushed DNS\n  Done\nPCAT_DONE", "", True
    if "Remove-Item" in script and T.tok in script: T.files["cleaned"] = True; return "", "", True
    if "Rename-Computer" in script: return "  Rename submitted -- target restarts in 15 seconds\n", "", True
    return "  generic output", "", True
m.make_session = fake_make_session; m.run_remote_ps = fake_run

client = m.app.test_client()
def run(tasks, params=None):
    r = client.post("/api/run", json={"hostname": "10.0.0.5", "username": "admin@corp.local", "password": "S3cret!'\"pw",
                                      "transport": "ntlm", "tasks": tasks, "params": params or {}, "confirmed_danger": True})
    evs = [json.loads(l[6:]) for l in r.get_data(as_text=True).split("\n\n") if l.startswith("data: ")]
    return evs
evs = run(["flush_dns"])
txt = "\n".join(e.get("text", "") for e in evs)
check("blip op returns real output after outage", "Flushed DNS" in txt)
check("blip op announced reconnect", "interrupted" in txt and "Reconnected" in txt)
check("wrapper has body+done marker", "ipconfig" in T.files["wrapper"] and "done.txt" in T.files["wrapper"])
check("temp files cleaned", T.files.get("cleaned"))
check("run finished ok", evs[-1]["type"] == "done" and evs[-1]["success"])

# rename + credential prelude: password must never be in any event text or log
T.script_log.clear()
evs = run(["rt_rename_pc_domain", "rt_vss_view"], {"rt_rename_pc_domain": {"NEW_NAME": "PC-CSD", "AUTO_RESTART": "true"}})
txt = "\n".join(e.get("text", "") for e in evs)
check("rename ran", "target restarts in 15 seconds" in txt)
check("task after reboot skipped", "Skipped: the target is restarting" in txt)
check("password absent from output", "S3cret" not in txt)
joined = "\n".join(T.script_log)
check("password absent in plaintext from scripts", "S3cret" not in joined)
check("prelude present", "$__cred" in joined and base64.b64encode("S3cret!'\"pw".encode()).decode() in joined)
import glob
logs = sorted(glob.glob("/home/claude/v17/PC_Admin_Tool_WebService_Edition/logs/*.log"))
check("password absent from log files", all("S3cret" not in open(f, encoding="utf-8").read() for f in logs))

# reboot-op connection loss is success
def fake_run2(session, script, label=""):
    if "SESSION_OK" in script: return "SESSION_OK", "", True
    return "", "TRANSPORT_ERR:reset", False
m.run_remote_ps = fake_run2
evs = run(["pr_force_restart", "rt_vss_view"])
txt = "\n".join(e.get("text", "") for e in evs)
check("reboot op loss treated as expected", "expected result" in txt and "Skipped" in txt)
# soft recycle with auto restart off -> not expected
m.run_remote_ps = fake_run2
m.RECONNECT_ATTEMPTS = 2
evs = run(["pr_full_soft_recycle"], {"pr_full_soft_recycle": {"AUTO_RESTART": "false"}})
txt = "\n".join(e.get("text", "") for e in evs)
check("non-reboot loss reconnect fails clearly", "Reconnect failed" in txt)

# vsssize validator
v = m.PARAM_VALIDATORS["vsssize"]
for good in ["10%", "20gb", "51200 MB", "unbounded", "100%"]:
    check("vsssize ok " + good, v(good)[1] is None)
for bad in ["0%", "101%", "20", "10GBx", "10%;calc", ""]:
    check("vsssize bad " + repr(bad), v(bad)[1] is not None)

# console launcher (Linux: refuses; Windows path mocked)
lines = m.launch_console("ac_open_rdp", "pc1", "u", "pw", "ntlm")
check("console on non-Windows refuses cleanly", any("cannot open Windows consoles" in l for l in lines))
import platform, subprocess
calls = []
class R: returncode = 0; stdout = ""; stderr = ""
m.platform.system = lambda: "Windows"
m.subprocess.run = lambda *a, **k: (calls.append(("run", a[0])), R())[1]
m.subprocess.Popen = lambda *a, **k: calls.append(("popen", a[0], k.get("env", {}).get("PCAT_PW")))
for cid in sorted(m.CONSOLE_OP_IDS):
    out = m.launch_console(cid, "PC1.corp.local", "admin@corp.local", "S3cret'pw", "ntlm")
    check("console %s no password in msg" % cid, "S3cret" not in "\n".join(out))
argv_all = json.dumps([c[1] for c in calls if c[0] == "popen"])
check("no password in any Popen argv", "S3cret" not in argv_all)
check("shell gets pw via env", any(c[0] == "popen" and c[2] == "S3cret'pw" for c in calls))
check("injection host refused", "Refused" in m.launch_console("ac_open_services", "-evil /x", "u", "p", "ntlm")[0])
inner = [c for c in calls if c[0] == "popen" and c[1][0] == "powershell.exe"][0][1][-1]
check("ps inner quoted", "'admin@corp.local'" in inner and "PCAT_PW" in inner)
print("FAILS:", fails)
sys.exit(1 if fails else 0)
