import sys, re
S="/tmp/claude-0/-home-claude/553766bb-8ae3-5461-bdb9-0d251a8a8a22/scratchpad"
sys.path.insert(0,S)
from new_ops import NEW_OPS, CONSOLE_OPS
from rename_ops import DOMAIN, WORKGROUP, LEGACY
from ps_runner import *
p="PCAdminTool.ps1"
s=open(p,encoding="utf-8-sig",newline="").read().replace("\r\n","\n")
def must(c,m):
    if not c: raise SystemExit("ANCHOR FAIL: "+m)
def q(x): return "'"+x.replace("'","''")+"'"
def prm(x):
    t='@{Key="%s";Kind="%s";Label=%s'%(x["key"],x["kind"],q(x["label"]))
    t+=';Req=$true' if x.get("required",True) else ';Req=$false'
    if x.get("default"): t+=';Def=%s'%q(x["default"])
    if x.get("help"): t+=';Help=%s'%q(x["help"])
    return t+"}"
def render(o):
    flags=';D=$true' if o["danger"] else ';D=$false'
    if o.get("needs_cred"): flags+=';NC=$true'
    if o.get("long"): flags+=';LG=$true'
    t=' @{Id="%s";Cat="%s"%s;L=%s;Ds=%s\n'%(o["id"],o["category"],flags,q(o["label"]),q(o["description"]))
    if o.get("params"):
        t+="   Prm=@(\n"+",\n".join("     "+prm(x) for x in o["params"])+"\n   )\n"
    body="\n".join(("   "+l if l.strip() else l) for l in o["command"].strip("\n").split("\n"))
    t+="   Cmd={\n   $ProgressPreference=\"SilentlyContinue\"\n"+body+"\n   } }\n"
    return t
NAME=dict(key="NEW_NAME",kind="computername",label="New Computer Name",required=True)
AR=dict(key="AUTO_RESTART",kind="bool",label="Automatically restart when done",required=True,default="true",help="Unchecked: rename now, restart later yourself")
ren=[dict(id="rt_rename_pc_domain",danger=True,needs_cred=True,category="Remote Tools",label="Rename Computer (Domain-Joined)",
   description="Renames a domain member using the username/password you connected with as an explicit domain credential (no CredSSP needed); restart optional",params=[NAME,AR],command=DOMAIN),
 dict(id="rt_rename_pc_workgroup",danger=True,needs_cred=True,category="Remote Tools",label="Rename Computer (Workgroup/Local)",
   description="Local rename for NON-domain targets (refuses on a domain member and says so); restart optional",params=[NAME,AR],command=WORKGROUP),
 dict(id="rt_rename_pc_wmic_legacy",danger=True,needs_cred=True,category="Remote Tools",label="Rename Computer via WMIC (Legacy -- Manual Restart Required)",
   description="WMIC where present; automatically uses the same WMI rename method via CIM when WMIC is removed (Win11 24H2+) or the target is domain-joined",params=[NAME],command=LEGACY)]
# the rename bodies read $__cred -> provided as param by the runner
a=s.index(' @{Id="rt_rename_pc_domain"'); b=s.index(' @{Id="rt_vss_view"')
s=s[:a]+"".join(render(o) for o in ren)+s[b:]
a=s.index(' @{Id="rt_open_computer_management"'); b=s.index(' @{Id="rt_restart_service"')
s=s[:a]+s[b:]
must("  Restart-Computer -Force\n" in s,"rc"); s=s.replace("  Restart-Computer -Force\n","  shutdown.exe /r /f /t 3\n",1)
must(s.count("shutdown /g /f /t 0")>=2,"sd"); s=s.replace("shutdown /g /f /t 0","shutdown /g /f /t 3")
# new ops: end of $Ops
i0=s.index("$Ops=@(")
end=s.index("\n)\n",i0)
add="\n"+"".join(render(o) for o in NEW_OPS)
for cid,label,desc in CONSOLE_OPS:
    add+=render(dict(id=cid,danger=False,label=label,category="Admin Consoles",description=desc,
        command="\n# Handled by the host application (Open-AdminConsole) -- never sent to the target.\nWrite-Output \"  (local console launcher)\"\n"))
s=s[:end]+add.rstrip("\n")+s[end:]
# danger list
new_danger=[o["id"] for o in NEW_OPS if o["danger"]]
must('"rt_map_network_drive","rt_unmap_network_drive")' in s,"danger")
s=s.replace('"rt_map_network_drive","rt_unmap_network_drive")','"rt_map_network_drive","rt_unmap_network_drive",\n  '+",".join('"%s"'%x for x in new_danger)+")",1)
# validator
must('        "bool" {\n            $bl=$v.ToLower()' in s,"bool validator")
s=s.replace('        "bool" {\n            $bl=$v.ToLower()','''        "vsssize" {
            $z=($v.ToUpper() -replace ' ','')
            if($z -match '^(UNBOUNDED|\\d{1,3}%|\\d{1,9}(KB|MB|GB|TB|PB|EB))$'){
                if($z.EndsWith('%') -and ([int]$z.TrimEnd('%') -lt 1 -or [int]$z.TrimEnd('%') -gt 100)){return @{Ok=$false;Err="a percentage must be between 1% and 100%"}}
                return @{Ok=$true;Value=$z}}
            return @{Ok=$false;Err="'$v' is not a valid shadow-storage size (use e.g. 10%, 20GB, 51200MB or UNBOUNDED)"} }
        "bool" {
            $bl=$v.ToLower()''',1)
# tab
must('@{L="Remote Tools";K="Remote Tools";Col=$CYAN})){' in s,"tab")
s=s.replace('@{L="Remote Tools";K="Remote Tools";Col=$CYAN})){','@{L="Remote Tools";K="Remote Tools";Col=$CYAN},\n  @{L="Admin Consoles";K="Admin Consoles";Col=$YEL})){',1)
# counts
s=s.replace("# OPERATIONS (67 total)","# OPERATIONS (85 total)").replace("(67 operations)","(85 operations)")
# run click: $vals default + $od extras
must("    $subs=@{}    # Id -> final substituted command text\n" in s,"subs")
s=s.replace("    $subs=@{}    # Id -> final substituted command text\n","    $subs=@{}    # Id -> final substituted command text\n    $vals=@{}\n",1)
old="        @{Id=$_.Id;L=$_.L;Cat=$_.Cat;Ds=$_.Ds;CT=$ctxt;D=$_.D}\n"
must(old in s,"od")
s=s.replace(old,"        @{Id=$_.Id;L=$_.L;Cat=$_.Cat;Ds=$_.Ds;CT=$ctxt;D=$_.D;NC=[bool]$_.NC;LG=[bool]$_.LG;PV=$vals[$_.Id]}\n",1)
# runner
anchor='        $h=$sh;$ProgressPreference="SilentlyContinue";$WarningPreference="SilentlyContinue"\n'
must(anchor in s,"runner head")
s=s.replace(anchor,anchor+RUNNER_PRE.lstrip("\n"),1)
cf='        }catch{$h.Q.Enqueue(@{T="  CONNECT FAILED: $($_.Exception.Message)";Tag="err"});$h.Done=$true;return}\n'
must(cf in s,"connect fail")
s=s.replace(cf,cf+RUNNER_FUNCS.lstrip("\n")+"        $curHost=$h.HN;$rebooting=$false\n",1)
a=s.index('            if($op.Id -eq "rt_open_computer_management"){')
bm='            $el=[math]::Round(((Get-Date)-$t0).TotalSeconds,1)\n'
b=s.index(bm,a)
s=s[:a]+RUNNER_LOOP_CONSOLE+RUNNER_EXEC+s[b:]
s=s.replace("Remove-PSSession $sess -EA SilentlyContinue\n        $h.Q.Enqueue(@{T=\"=\"*55;Tag=\"hdr\"})","try{Remove-PSSession $sess -EA SilentlyContinue}catch{}\n        $h.Q.Enqueue(@{T=\"=\"*55;Tag=\"hdr\"})",1)
open(p,"w",encoding="utf-8",newline="").write("﻿"+s.replace("\n","\r\n"))
print("ok")
