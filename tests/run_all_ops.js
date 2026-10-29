// Runs every operation through the demo engine (no browser needed) and checks it behaves.
global.window = global; window.fetch = undefined;
const path = '../docs/demo/';
for (const f of ['ops-data.js', 'demo-engine.js', 'demo-sims-1.js', 'demo-sims-2.js']) require(path + f);
const D = window.DemoEngine; D.speed = 0;
const OPS = window.DEMO_OPS;
async function run(body) {
  const r = await window.fetch('/api/run', { method: 'POST', body: JSON.stringify(Object.assign({ hostname: 'DEMO-PC01', username: 'CORP\\admin1', password: 'x', transport: 'ntlm', confirmed_danger: true }, body)) });
  const reader = r.body.getReader(), dec = new TextDecoder(); let buf = '', evs = [];
  for (;;) { const { done, value } = await reader.read(); if (done) break; buf += dec.decode(value, { stream: true }); const parts = buf.split('\n\n'); buf = parts.pop(); for (const p of parts) if (p.startsWith('data: ')) evs.push(JSON.parse(p.slice(6))); }
  return evs;
}
const SAMPLE = { ADAPTER: 'Ethernet', IP: '192.168.10.201', MASK: '255.255.255.0', GATEWAY: '192.168.10.1', DNS1: '192.168.10.5', DNS2: '8.8.8.8', ROLLBACK: 'true', NEW_NAME: 'DEMO-PC02', AUTO_RESTART: 'false', VOLUME: 'C', MAX_SIZE: '10GB', STORAGE_VOLUME: '', TASK_NAME: '\\Microsoft\\Windows\\Defrag\\ScheduledDefrag', SERVICE_NAME: 'Spooler', SHARE_PATH: '\\\\fileserver\\shared', DRIVE_LETTER: 'S', USER_ACCOUNT: 'CORP\\jsmith', APPLY_NOW: 'true', REPLACE_EXISTING: 'true', DEVICE_ID: 'USB\\VID_0000&PID_0002\\5&2A3B&0&3', IP1: '', IP2: '' };
(async () => {
  let bad = 0; const verdicts = {}; const noSim = [];
  for (const op of OPS) {
    if (op.monitor) continue;
    if (!window.DemoSims[op.id]) { noSim.push(op.id); continue; }
    const params = {}; if (op.params.length) { params[op.id] = {}; op.params.forEach(p => { params[op.id][p.key] = SAMPLE[p.key] !== undefined ? SAMPLE[p.key] : (p.default || ''); }); }
    let evs; try { evs = await run({ tasks: [op.id], params }); } catch (e) { console.log('CRASH', op.id, e.message); bad++; continue; }
    const out = evs.filter(e => ['output', 'success', 'warning', 'error'].includes(e.type) && /^ {4}/.test(e.text || '') && !/Category|Purpose|─{5}/.test(e.text));
    const last = evs.filter(e => /RESULT|Completed/.test(e.text || '')).pop();
    const done = evs.find(e => e.type === 'done');
    const errEv = evs.find(e => e.text && /Demo engine error|undefined|NaN|\[object/.test(e.text));
    if (!done || out.length < 2 || errEv) { console.log('PROBLEM', op.id, 'lines:', out.length, 'done:', !!done, errEv ? errEv.text : ''); bad++; }
    const v = last ? (last.text.includes('✗') ? 'FAILED' : last.text.includes('⚠') ? 'WARNING' : 'OK') : '??'; verdicts[v] = (verdicts[v] || 0) + 1;
  }
  console.log('ops without simulator:', noSim.length ? noSim.join(',') : 'none');
  console.log('verdicts:', JSON.stringify(verdicts), '| problems:', bad);
  process.exit(bad ? 1 : 0);
})();
