import importlib.util, sys, types, re, json, subprocess
from importlib.machinery import SourceFileLoader
R="/home/claude/v17/"
spec=importlib.util.spec_from_file_location("w",R+"PC_Admin_Tool_WebService_Edition/app.py"); w=importlib.util.module_from_spec(spec); spec.loader.exec_module(w)
tk=types.ModuleType("tkinter")
for n in ("Frame","Tk","Canvas","Label","Button","Entry","Text","Scrollbar","Checkbutton","StringVar","BooleanVar","Toplevel"):
    setattr(tk,n,type(n,(),{"__init__":lambda s,*a,**k:None}))
tk.ttk=types.ModuleType("ttk");tk.messagebox=types.ModuleType("mb");tk.filedialog=types.ModuleType("fd")
sys.modules.update({"tkinter":tk,"tkinter.ttk":tk.ttk,"tkinter.messagebox":tk.messagebox,"tkinter.filedialog":tk.filedialog})
tk.ttk.Frame=tk.ttk.Combobox=tk.ttk.Progressbar=tk.ttk.Style=tk.ttk.Scrollbar=object
sp=importlib.util.spec_from_loader("g",SourceFileLoader("g",R+"PC_Admin_Tool_PythonGUI_Edition/PCAdminTool.pyw")); g=importlib.util.module_from_spec(sp); sp.loader.exec_module(g)
W={o["id"]:o for o in w.OPERATIONS}; G={o["id"]:o for o in g.OPERATIONS}
bad=0
print("ids equal Web/Tk:",set(W)==set(G))
for i,o in W.items():
    x=G[i]
    for k in ("label","category","description","command","danger"):
        if o[k]!=x[k]: bad+=1; print("DIFF",i,k)
    if o.get("params",[])!=x.get("params",[]): bad+=1; print("DIFF params",i)
    for fl in ("long","needs_cred"):
        if bool(o.get(fl))!=bool(x.get(fl)): bad+=1; print("DIFF flag",i,fl)
print("web/tk diffs:",bad)
out=subprocess.run(["/home/claude/pwsh/pwsh","-NoProfile","-Command",r'''
$t=$null;$e=$null
$ast=[System.Management.Automation.Language.Parser]::ParseFile("/home/claude/v17/PC_Admin_Tool_PowerShell_Edition/PCAdminTool.ps1",[ref]$t,[ref]$e)
$a=$ast.FindAll({param($n) $n -is [System.Management.Automation.Language.AssignmentStatementAst] -and $n.Left.Extent.Text -eq '$Ops'},$true)|Select-Object -First 1
. ([scriptblock]::Create($a.Extent.Text))
$Ops|ForEach-Object{[pscustomobject]@{id=$_.Id;cat=$_.Cat;d=[bool]$_.D;l=$_.L;ds=$_.Ds;cmd=$_.Cmd.ToString();nc=[bool]$_.NC;lg=[bool]$_.LG;prm=@($_.Prm|ForEach-Object{@{key=$_.Key;kind=$_.Kind}})}}|ConvertTo-Json -Depth 5 -Compress
'''],capture_output=True,text=True)
ps=json.loads(out.stdout)
print("PS ops:",len(ps))
PSID={p["id"]:p for p in ps}
shared=[i for i in W if i in PSID]
print("shared ids:",len(shared),"| Web ids spelled differently in PS (original ops):",len(set(W)-set(PSID)))
cd=0
for i in shared:
    p=PSID[i]
    if p["cat"]!=W[i]["category"] or p["d"]!=W[i]["danger"] or p["nc"]!=bool(W[i].get("needs_cred")) or p["lg"]!=bool(W[i].get("long")):
        print("META DIFF",i); cd+=1
    pk=[x["key"] for x in p["prm"] if x["key"]]
    if pk!=[x["key"] for x in W[i].get("params",[])]:
        print("PARAM DIFF",i); cd+=1
print("ps meta/param diffs:",cd)
norm=lambda s:re.sub(r"\s+","",re.sub(r"\$ProgressPreference\s*=\s*\"SilentlyContinue\"","",s))
NEW=["rt_vss_resize_storage","run_dism_restorehealth","dism_component_cleanup","perf_hardware_report_cim","perf_trim_ssd","perf_wmi_verify_repository","perf_rebuild_perf_counters","chkdsk_online_scan","rt_rename_pc_domain","rt_rename_pc_workgroup","rt_rename_pc_wmic_legacy"]+[c[0] for c in []]
for i in NEW:
    print("BODY",i,"equal" if norm(PSID[i]["cmd"])==norm(W[i]["command"]) else "DIFF")
print("danger count PS:",sum(p["d"] for p in ps),"Web:",sum(o["danger"] for o in w.OPERATIONS))
print("PS-only ids:",sorted(set(PSID)-set(W))[:50])
