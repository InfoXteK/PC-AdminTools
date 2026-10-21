import sys, types, importlib.util, re, base64, queue, threading
tk = types.ModuleType("tkinter")
for n in ("Frame","Tk","Canvas","Label","Button","Entry","Text","Scrollbar","Checkbutton","StringVar","BooleanVar","Toplevel"):
    setattr(tk, n, type(n, (), {"__init__": lambda self,*a,**k: None}))
tk.ttk = types.ModuleType("ttk"); tk.messagebox = types.ModuleType("mb"); tk.filedialog = types.ModuleType("fd")
sys.modules.update({"tkinter": tk, "tkinter.ttk": tk.ttk, "tkinter.messagebox": tk.messagebox, "tkinter.filedialog": tk.filedialog})
tk.ttk.Frame = tk.ttk.Combobox = tk.ttk.Progressbar = tk.ttk.Style = tk.ttk.Scrollbar = object
from importlib.machinery import SourceFileLoader
spec = importlib.util.spec_from_loader("pyw", SourceFileLoader("pyw", "PCAdminTool.pyw"))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
m.RECONNECT_WAIT_SECONDS = 0; m.DETACH_POLL_SECONDS = 0
fails = []
def check(n, c):
    print(("PASS " if c else "FAIL ") + n)
    if not c: fails.append(n)
check("85 ops", len(m.OPERATIONS) == 85)
state = {"down": 0, "pend": 2, "log": []}
def fms(h, u, p, t="ntlm", fast=False): return {"h": h}
def frun(s, script, *a):
    state["log"].append(script)
    if state["down"] > 0 and s["h"] == "10.0.0.5": state["down"] -= 1; return "", "TRANSPORT_ERR:x", False
    if "PCAT_LAUNCHED" in script and "FromBase64String" in script: state["down"] = 3; return "PCAT_LAUNCHED:1", "", True
    if "RECONNECT_OK" in script: return "RECONNECT_OK", "", True
    if "SESSION_OK" in script: return "SESSION_OK", "", True
    if "PCAT_PENDING" in script:
        if state["pend"] > 0: state["pend"] -= 1; return "PCAT_PENDING", "", True
        return "  net reset ok\nPCAT_DONE", "", True
    if "shutdown.exe /r /f /t 3" in script: return "", "TRANSPORT_ERR:reset", False
    return "  fine", "", True
m.make_session = fms; m.run_remote_ps = frun
app = object.__new__(m.PCAdminApp)
app.q = queue.Queue(); app.stop_flag = m._stop_flag; app.log_file = None
def logs():
    out = []
    while not app.q.empty(): out.append(app.q.get())
    return out
ops = {o["id"]: dict(o) for o in m.OPERATIONS}
app._run_worker("10.0.0.5", "corp\\bob", "S3cret'pw", "ntlm", [ops["reset_network"], ops["pr_force_restart"], ops["rt_vss_view"]])
L = logs(); txt = "\n".join(str(x[2]) for x in L if x[0] == "log")
check("blip result returned", "net reset ok" in txt)
check("reconnect messages", "interrupted" in txt and "Reconnected" in txt)
check("reboot-class handled", "expected result" in txt)
check("task after reboot skipped", "Skipped: the target is restarting" in txt)
check("done emitted", any(x[0] == "done" for x in L))
check("no password anywhere", "S3cret" not in txt and "S3cret" not in "\n".join(state["log"]))
r = dict(ops["rt_rename_pc_domain"]); r["command"], e = m.validate_and_substitute(r, {"NEW_NAME": "PC-X", "AUTO_RESTART": "true"})
check("rename substitutes", e is None and "PC-X" in r["command"] and "{{" not in r["command"])
check("rename needs_cred", ops["rt_rename_pc_domain"].get("needs_cred"))
print("FAILS", fails); sys.exit(1 if fails else 0)
