import sys
sys.path.insert(0, "/tmp/claude-0/-home-claude/553766bb-8ae3-5461-bdb9-0d251a8a8a22/scratchpad")
from rename_ops import DOMAIN, WORKGROUP, LEGACY
p = "app.py"
s = open(p, encoding="utf-8").read()
a = s.index('    {\n        "id": "rt_rename_pc_domain"')
b = s.index('    {\n        "id": "rt_vss_view"')
def op(id_, label, desc, params, body, extra=""):
    ps = ",\n".join(params)
    return ('    {\n        "id": "%s",\n        "danger": True,\n        "needs_cred": True,\n        "label": "%s",\n'
            '        "category": "Remote Tools",\n        "description": "%s",\n        "params": [\n%s\n        ],\n'
            '        "command": r"""\n%s"""\n    },\n') % (id_, label, desc, ps, body.lstrip("\n"))
NAME = '            {"key": "NEW_NAME", "kind": "computername", "label": "New Computer Name", "required": True}'
AR = ('            {"key": "AUTO_RESTART", "kind": "bool", "label": "Automatically restart when done",\n'
      '             "required": True, "default": "true",\n'
      '             "help": "Unchecked: rename now, restart later yourself (name won\'t take effect until then)"}')
new = (op("rt_rename_pc_domain", "Rename Computer (Domain-Joined)",
          "Renames a domain member using the username/password you connected with as an explicit domain credential (no CredSSP needed); restart optional",
          [NAME, AR], DOMAIN)
     + op("rt_rename_pc_workgroup", "Rename Computer (Workgroup/Local)",
          "Local rename for NON-domain targets (refuses on a domain member and says so); restart optional",
          [NAME, AR], WORKGROUP)
     + op("rt_rename_pc_wmic_legacy", "Rename Computer via WMIC (Legacy -- Manual Restart Required)",
          "WMIC where present; automatically uses the same WMI rename method via CIM when WMIC is removed (Win11 24H2+) or the target is domain-joined",
          [NAME], LEGACY))
s = s[:a] + new + s[b:]
open(p, "w", encoding="utf-8").write(s)
print("patched")
