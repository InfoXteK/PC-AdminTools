"""Rebuild the live demo from the real tool. Run from the repository root:

    pip install flask "pypsrp[credssp]"        # app.py is imported to read the operation list
    python tools/build_demo.py                  # uses PC_Admin_Tool_WebService_Edition/
    python tools/build_demo.py path/to/WebServiceEdition   # or point at another folder

It regenerates docs/demo/ops-data.js (operations, parameters, real PowerShell scripts) and
docs/demo/index.html (the real web UI + demo layer). The simulators (docs/demo/demo-sims-*.js)
are hand-written: after adding a NEW operation to the tool, add a simulator for its id there
(an operation without one just prints "No simulator for this operation yet.")."""
import os, subprocess, sys
here = os.path.dirname(os.path.abspath(__file__)); root = os.path.dirname(here)
web = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, "PC_Admin_Tool_WebService_Edition")
app, tpl = os.path.join(web, "app.py"), os.path.join(web, "templates", "index.html")
for p in (app, tpl):
    if not os.path.exists(p):
        sys.exit(f"not found: {p}\nPass the Web-Service edition folder as the first argument.")
py = sys.executable
subprocess.check_call([py, os.path.join(here, "build_data.py"), app, os.path.join(root, "docs", "demo", "ops-data.js")])
subprocess.check_call([py, os.path.join(here, "build_demo_page.py"), tpl, os.path.join(root, "docs", "demo", "index.html")])
print("Demo rebuilt. Commit docs/ and push.")
