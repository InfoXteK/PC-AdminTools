# Publish the live demo on GitHub Pages — step by step

The demo is plain static files in the **`docs/`** folder. No build step, no server.

## 1. Add the files to your repository
Your repo: https://github.com/MohamedAbdullahKhan/PC-AdminTools

**Easiest (web upload):**
1. Open the repo → **Add file → Upload files**.
2. Drag in the **`docs`** folder (it contains `index.html`, a `demo` folder and a hidden file `.nojekyll`) and the **`tools`** folder. *(Optional: also `tests`.)*
   - If your browser's upload skips the hidden `.nojekyll` file, create it: **Add file → Create new file**, name it `docs/.nojekyll`, leave it empty, commit.
3. Click **Commit changes** (to the `main` branch).

**Or with git:**
```
git clone https://github.com/MohamedAbdullahKhan/PC-AdminTools.git
cd PC-AdminTools
# copy docs/ tools/ (and tests/) from this package into the repo folder
git add docs tools
git commit -m "Add GitHub Pages live demo"
git push
```

## 2. Turn on Pages
Repo → **Settings → Pages** → under *Build and deployment*:
- **Source:** Deploy from a branch
- **Branch:** `main`   **Folder:** `/docs`  → **Save**

Wait 1–3 minutes. Your site will be at:

- **Landing page:** https://mohamedabdullahkhan.github.io/PC-AdminTools/
- **Live demo:** https://mohamedabdullahkhan.github.io/PC-AdminTools/demo/

(The first deployment can take a few minutes; refresh the Pages settings screen to see the green “Your site is live” banner.)

## 3. Link it from your README
Add near the top of the repo's `README.md`:
```
## Live demo
**Try it in your browser (no install, nothing touches a real PC):**
https://mohamedabdullahkhan.github.io/PC-AdminTools/
```
or a button: `[![Live demo](https://img.shields.io/badge/live-demo-2563eb)](https://mohamedabdullahkhan.github.io/PC-AdminTools/)`

## 4. Keep the demo in sync with the tool
This demo shows **v4.0 (113 operations)**. Make sure the repo's tool files are the v4.0 ones too (bundle v20), otherwise the site describes features the source does not have yet.

When you change the tool:
```
pip install flask "pypsrp[credssp]"
python tools/build_demo.py            # re-reads app.py + templates/index.html
git add docs && git commit -m "Refresh demo" && git push
```
This refreshes the operation list, parameters, the “</> script” texts and the real UI. If you add a **new** operation, add a simulator for its `id` in `docs/demo/demo-sims-1.js` or `-2.js` (otherwise it prints “No simulator for this operation yet.”). If the real `index.html` changes so much that an edit anchor moves, `build_demo_page.py` stops with a clear message instead of publishing a stale page.

## 5. What visitors get
- **Landing page:** what the tool is, how it works, the three editions, features, a searchable list of all 113 operations, guided scenarios, install notes, version history.
- **Live demo:** the real web interface with a simulated target PC (“DEMO-PC01”): Test Connection, all 9 tabs, parameter forms with real validation, the sensitive-operation popup, live streaming output, Stop, logs, **Network Push** and the **continuous Ping Monitor** (the simulated PC really changes IP / goes offline), speed control, downloadable logs, and a **“</> script”** button showing the real PowerShell of every operation.

## 6. Honest limits
- It is a **simulation**: no real computer is contacted and every number is invented. The page says so in a banner.
- The PowerShell GUI and Python (Tkinter) editions are described but not demonstrated (a browser cannot run a desktop window).
- Tested headlessly (jsdom: engine for all 113 operations, scenarios, click-through of the page, landing page). It has **not** been checked in real browsers or on phones — open it once on desktop and mobile after publishing.

## Run the tests (optional)
```
cd tests
npm install
npm test
```
