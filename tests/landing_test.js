const { JSDOM } = require('jsdom'); const path = require('path'); const fs = require('fs');
const sleep = ms => new Promise(r => setTimeout(r, ms)); let fails = 0; const ok = (c, m) => { console.log((c ? '  PASS ' : '  FAIL ') + m); if (!c) fails++; };
(async () => {
  const file = path.resolve(__dirname, '../docs/index.html');
  const dom = await JSDOM.fromFile(file, { runScripts: 'dangerously', resources: 'usable' }); const w = dom.window, d = w.document;
  for (let i = 0; i < 40 && !d.querySelectorAll('.op').length; i++) await sleep(100);
  ok(d.getElementById('sOps').textContent === '113' && d.getElementById('sCats').textContent === '9', 'stats filled from the real data: 113 ops / 9 categories');
  ok(d.querySelectorAll('#chips .chip').length === 10, 'category chips: All + 9');
  ok(d.querySelectorAll('#exList .op').length === 113, 'explorer lists all 113 operations');
  const q = d.getElementById('q'); q.value = 'vss'; q.oninput({ target: q });
  const n = d.querySelectorAll('#exList .op').length; ok(n >= 6 && n < 20, 'search "vss" -> ' + n + ' operations');
  q.value = ''; q.oninput({ target: q }); [...d.querySelectorAll('#chips .chip')].find(c => /^Network Push/.test(c.textContent)).click();
  ok(d.querySelectorAll('#exList .op').length === 8, 'chip "Network Push" -> 8 operations');
  ok(d.querySelectorAll('#exList .op.d').length === 7, 'sensitive operations are flagged amber (7 in Network Push)');
  // link targets
  const hrefs = [...d.querySelectorAll('a[href]')].map(a => a.getAttribute('href')).filter(h => !/^https?:|^#/.test(h));
  const missing = [...new Set(hrefs)].map(h => h.split('?')[0]).filter(h => !fs.existsSync(path.resolve(path.dirname(file), h)) && !fs.existsSync(path.resolve(path.dirname(file), h, 'index.html')));
  ok(missing.length === 0, 'all relative links resolve (' + [...new Set(hrefs)].length + ' checked)' + (missing.length ? ' missing: ' + missing : ''));
  const anchors = [...d.querySelectorAll('a[href^="#"]')].map(a => a.getAttribute('href').slice(1)); ok(anchors.every(id => d.getElementById(id)), 'all #anchors exist');
  const scen = [...d.querySelectorAll('a[href*="scenario="]')].map(a => a.getAttribute('href').split('scenario=')[1]);
  const ui = fs.readFileSync(path.resolve(__dirname, '../docs/demo/demo-ui.js'), 'utf8'); ok(scen.every(s => new RegExp('\\b' + s + ':\\s*\\{').test(ui)), 'every scenario card maps to a scenario in the demo: ' + scen.join(', '));
  console.log(fails ? '\n' + fails + ' FAILED' : '\nLANDING CHECKS PASSED'); process.exit(fails ? 1 : 0);
})();
