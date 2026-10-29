"""Builds docs/demo/index.html from the REAL templates/index.html of the Web-Service edition.
Every edit is asserted to match exactly once -- if you change the real UI and an anchor moves,
this script stops with a clear message instead of silently producing a stale demo.
Usage:  python tools/build_demo_page.py <path-to-templates/index.html> <output-index.html>"""
import sys
src, out = sys.argv[1], sys.argv[2]
t = open(src, encoding="utf-8").read()

def sub(old, new, label):
    global t
    n = t.count(old)
    assert n == 1, f"anchor '{label}' matched {n} times (expected 1) -- the real index.html changed; update tools/build_demo_page.py"
    t = t.replace(old, new)

BAR = '''<div id="demoBar">
  <div class="db-l"><span class="db-badge">LIVE DEMO</span>Simulated target <b>DEMO-PC01</b> &mdash; nothing is sent to any real computer. The interface, the 113 operations and their PowerShell scripts are the real ones.</div>
  <div class="db-r">
    <label for="scen">Try a scenario:</label>
    <select id="scen"><option value="">&mdash; pick one &mdash;</option>
      <option value="health">Health check (4 reports)</option>
      <option value="cleanup">Cleanup run (+ danger popup)</option>
      <option value="pushwatch">Push a static IP, then watch it live</option>
      <option value="typo">The gateway-typo that v16 missed</option>
      <option value="rollback">Auto-rollback safety net</option>
      <option value="validation">Input validation</option>
      <option value="reboot">Forced restart (then ping it)</option>
    </select><button id="scenGo">Load</button>
    <label for="spd">Speed:</label>
    <select id="spd"><option value="1">Normal</option><option value="0.35">Fast</option><option value="0">Instant</option></select>
    <button id="dlLast" title="Download the log of the last run">&#11015; Last log</button>
    <a class="db-link" href="../">About</a>
    <a class="db-link" href="https://github.com/MohamedAbdullahKhan/PC-AdminTools" target="_blank" rel="noopener">GitHub</a>
  </div>
</div>
<div id="scenHint"></div>
<div id="scrModal"><div class="box">
  <div class="mh"><h4 id="scrTitle"></h4><button id="scrCopy">Copy</button><button id="scrClose">Close</button></div>
  <div class="note">This is the real PowerShell the tool sends to the target PC (with your current parameter values filled in). The demo only <b>shows</b> it &mdash; it is never executed.</div>
  <pre id="scrCode"></pre>
</div></div>
'''
sub('<title>PC Admin &amp; Performance Tool -- Web-Service Edition</title>',
    '<title>PC Admin &amp; Performance Tool -- Live Demo</title>\n<meta name="viewport" content="width=device-width, initial-scale=1">\n<link rel="stylesheet" href="demo-ui.css">', 'title')
sub('<body>\n<header>', '<body>\n' + BAR + '<header>', 'body/header')
sub('<span class="cp">{{ copyright }}</span>', '<span class="cp">&copy; 2024-2026 Abdullah | PC Admin &amp; Performance Tool v4.0 &mdash; live demo</span>', 'copyright')
sub('<script>\nconst OPS = {{ ops|safe }};\nconst CATS = {{ cats|safe }};',
    '<script src="ops-data.js"></script>\n<script src="demo-engine.js"></script>\n<script src="demo-sims-1.js"></script>\n<script src="demo-sims-2.js"></script>\n<script>\nconst OPS = window.DEMO_OPS;\nconst CATS = window.DEMO_CATS;', 'ops/cats')
# "</> script" button on every task card
sub('      <div class="cat">${op.category}</div>`;', '      <div class="cat">${op.category}</div>\n      <button class="scr" title="Show the real PowerShell for this operation">&lt;/&gt; script</button>`;', 'card html')
sub("      renderTasks(); updateCount();\n    };\n    if(op.params && op.params.length){",
    "      renderTasks(); updateCount();\n    };\n    row.querySelector('.scr').onclick = (e) => { e.stopPropagation(); showScript(op.id); };\n    if(op.params && op.params.length){", 'script button handler')
# log names become download links
sub("${l.name} &middot; ${l.size} bytes &middot; ${l.modified}</div>`).join('')",
    "<a href=\"#\" onclick=\"return dlLog('${l.name}')\" style=\"color:var(--cyan)\" title=\"download\">${l.name}</a> &middot; ${l.size} bytes &middot; ${l.modified}</div>`).join('')", 'log links')
sub("panel.innerHTML = '<h3>Recent Logs (this host)</h3>'", "panel.innerHTML = '<h3>Recent Logs (this demo session -- click to download)</h3>'", 'logs title')
sub("buildTabs();\nrenderTasks();\n</script>", "buildTabs();\nrenderTasks();\n</script>\n<script src=\"demo-ui.js\"></script>", 'tail')
open(out, "w", encoding="utf-8").write(t)
print("built", out, len(t), "bytes")
