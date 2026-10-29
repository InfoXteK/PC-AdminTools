/* =============================================================================
   PC Admin & Performance Tool -- LIVE DEMO ENGINE
   -----------------------------------------------------------------------------
   The real tool is a Flask service (app.py) that talks WinRM to a Windows PC.
   GitHub Pages can only host static files, so this file is a faithful, in-browser
   STAND-IN for that server. The page you see is the real web UI; this script
   answers its four API calls (/api/test, /api/run, /api/stop, /api/logs) with
   SIMULATED data. NOTHING is ever sent to any real computer.

   What is faithful to the real tool:  the UI, the 113 operations + their parameters,
   the real PowerShell scripts (shown via "</> script"), parameter validation,
   the danger gate, the message formats, the RESULT / PUSHED protocol, the
   Ping Monitor, stop handling, log lines and the run footer.
   What is simulated:  the target PC itself (a fictional "DEMO-PC01" whose state
   really changes when you push an IP, restart, etc.) and every number/report.
   ============================================================================= */
(function () {
  'use strict';
  const D = window.DemoEngine = {};
  const OPS = window.DEMO_OPS, META = window.DEMO_META;
  const COPYRIGHT = '© 2024-2026 Abdullah | PC Admin & Performance Tool ' + META.version + ' | All Rights Reserved';

  // ── speed control (1 = normal, 0.35 = fast, 0 = instant) ─────────────────────
  D.speed = 1;
  const scaled = ms => Math.round(ms * (Number.isFinite(D.speed) && D.speed >= 0 ? D.speed : 1));
  const sleep = ms => new Promise(r => setTimeout(r, scaled(ms)));
  D.sleep = sleep;

  // ── small seeded random so numbers look stable-ish but vary per run ─────────
  function mulberry(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
  let rng = mulberry(Date.now() & 0xffffffff);
  D.rnd = () => rng();
  D.ri = (a, b) => Math.floor(a + rng() * (b - a + 1));
  D.rf = (a, b, d = 1) => (a + rng() * (b - a)).toFixed(d);
  D.pick = arr => arr[Math.floor(rng() * arr.length)];
  const hash = s => { let h = 2166136261; for (const c of s) { h ^= c.charCodeAt(0); h = Math.imul(h, 16777619); } return h >>> 0; };
  const pad = (s, n) => String(s).padEnd(n);
  const lpad = (s, n) => String(s).padStart(n);
  D.pad = pad; D.lpad = lpad;
  const hex = n => { let s = ''; for (let i = 0; i < n; i++) s += '0123456789abcdef'[Math.floor(rng() * 16)]; return s; };
  D.hex = hex;
  const isIPv4 = s => /^(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}$/.test(s);
  const ip2n = ip => ip.split('.').reduce((a, o) => a * 256 + (+o), 0);
  D.isIPv4 = isIPv4; D.ip2n = ip2n;
  const maskToPrefix = m => /^\d+$/.test(m) ? +m : m.split('.').reduce((a, o) => a + (+o).toString(2).replace(/0/g, '').length, 0);
  const prefixToMask = p => [0, 1, 2, 3].map(i => { const n = Math.min(8, Math.max(0, p - i * 8)); return 256 - Math.pow(2, 8 - n); }).join('.');
  D.maskToPrefix = maskToPrefix; D.prefixToMask = prefixToMask;
  const two = n => String(n).padStart(2, '0');
  const stamp = d => d.getFullYear() + '-' + two(d.getMonth() + 1) + '-' + two(d.getDate()) + ' ' + two(d.getHours()) + ':' + two(d.getMinutes()) + ':' + two(d.getSeconds());
  const stamp2 = d => d.getFullYear() + two(d.getMonth() + 1) + two(d.getDate()) + '_' + two(d.getHours()) + two(d.getMinutes()) + two(d.getSeconds());
  D.clock = d => two(d.getHours()) + ':' + two(d.getMinutes()) + ':' + two(d.getSeconds());
  D.stamp = stamp;

  // ── the simulated target PC ───────────────────────────────────────────────────
  const T = D.T = {};
  D.resetTarget = function (hostname) {
    const isIp = isIPv4(hostname);
    const name = isIp ? 'DEMO-PC01' : hostname.split('.')[0].toUpperCase().slice(0, 15);
    const ip = isIp ? hostname : '192.168.10.' + (50 + hash(hostname) % 150);
    const parts = ip.split('.');
    Object.assign(T, {
      key: hostname, host: hostname, name, domain: 'corp.example.local', ip, nameIp: ip,
      mask: '255.255.255.0', prefix: 24, gw: parts[0] + '.' + parts[1] + '.' + parts[2] + '.1',
      dns: [parts[0] + '.' + parts[1] + '.' + parts[2] + '.5', '8.8.8.8'], dhcp: false,
      adapter: 'Ethernet', mac: '00-15-5D-' + hex(2).toUpperCase() + '-' + hex(2).toUpperCase() + '-' + hex(2).toUpperCase(),
      consoleUser: 'CORP\\jsmith', bootTime: Date.now() - (3 * 86400 + 5 * 3600 + 17 * 60) * 1000,
      outages: [], rebootUntil: 0, unreachable: new Set(), dnsCache: 183, hibernation: true, powerPlan: 'Balanced',
      ramTotal: 16, ramFree: 4.1, tmp: { user: 2874, win: 311, pf: 1034, thumb: 142, wu: 1388, browser: 1905, recycle: 642 },
      timers: [], vssMax: '10%', vssCopies: 3,
    });
  };
  D.resetTarget('DEMO-PC01');
  D.ensure = h => { if (T.key !== h) { D.clearTimers(); D.resetTarget(h); } };
  const nowMs = () => Date.now();
  T.at = ms => nowMs() + scaled(ms);
  D.outage = (startMs, durMs) => { T.outages.push([T.at(startMs), T.at(startMs + durMs)]); };
  D.isDown = () => { const n = nowMs(); return n < T.rebootUntil || T.outages.some(w => n >= w[0] && n < w[1]); };
  D.pingMs = function (addr) {
    if (!addr || D.isDown()) return null;
    if (addr === T.ip) return T.unreachable.has(T.ip) ? null : +(0.4 + rng() * 1.6).toFixed(1);
    if (addr === T.host || addr.toUpperCase() === T.name) return D.pingMs(T.nameIp);
    return null;
  };
  D.resolve = name => (name === T.host || name.toUpperCase() === T.name) ? T.nameIp : (isIPv4(name) ? name : null);
  D.setTimer = (ms, fn) => { const id = setTimeout(fn, scaled(ms)); T.timers.push(id); return id; };
  D.clearTimers = () => { T.timers.forEach(clearTimeout); T.timers = []; };
  // an IP change that lands on the target: short outage, then the new address answers; the DNS name catches up a few s later
  D.applyAddress = function (o) {
    const old = T.ip;
    D.outage(o.afterMs, 3500);
    D.setTimer(o.afterMs, () => {
      T.ip = o.ip; T.mask = o.mask; T.prefix = maskToPrefix(o.mask); T.gw = o.gw;
      if (o.dns) T.dns = o.dns; T.dhcp = !!o.dhcp;
      const sameNet = old.split('.').slice(0, 2).join('.') === o.ip.split('.').slice(0, 2).join('.');
      T.unreachable = sameNet ? new Set() : new Set([o.ip]);   // a wrong network is not routable from the admin tool
    });
    D.setTimer(o.afterMs + 9000, () => { T.nameIp = o.ip; });  // DNS re-registration lags behind
  };

  // ── ports of the real client/server validators ────────────────────────────────
  const KIND = {
    ipv4: /^(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(\.(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])){3}$/,
    subnetmask: /^([0-9]|[12][0-9]|3[0-2])$|^(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(\.(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])){3}$/,
    computername: /^[A-Za-z0-9]([A-Za-z0-9-]{0,13}[A-Za-z0-9])?$/,
    adaptername: /^[A-Za-z0-9 ()./#_-]{1,64}$/,
    servicename: /^[A-Za-z0-9 _.$#+()-]{1,256}$/,
    taskname: /^[A-Za-z0-9 _.\\-]{1,200}$/,
    deviceid: /^[A-Za-z0-9\\&_{}-]{1,300}$/,
    drive: /^[A-Za-z]:?$/,
    uncpath: /^\\\\[A-Za-z0-9][A-Za-z0-9._-]{0,200}(?:\\(?!\.+(?:\\|$))[A-Za-z0-9 _.$#@&+(),~-]{1,80}){1,30}$/,
    mapdrive: /^[D-Zd-z]:?$/,
    vsssize: /^(?:UNBOUNDED|\d{1,3}%|\d{1,7}(?:MB|GB|TB))$/i,
    useraccount: /^(?:(?:\.|[A-Za-z0-9][A-Za-z0-9._-]{0,62})\\)?[A-Za-z0-9_.-][A-Za-z0-9 _.-]{0,63}$|^[A-Za-z0-9._-]{1,64}@[A-Za-z0-9][A-Za-z0-9.-]{0,252}$/,
  };
  function validateParams(op, values) {
    const out = {}; let err = null;
    for (const p of op.params || []) {
      let raw = ((values || {})[p.key] || '').trim();
      if (!raw) {
        if (p.default) raw = p.default;
        else if (p.required !== false) { err = 'Missing required value: ' + p.label; break; }
        else { out[p.key] = ''; continue; }
      }
      if (p.kind === 'bool') { out[p.key] = ['false', '0', 'no', 'off'].includes(raw.toLowerCase()) ? false : true; continue; }
      if (p.kind === 'vsssize') raw = raw.replace(/\s+/g, '');
      if (p.kind === 'subnetmask' && /^\d+$/.test(raw) && +raw >= 0 && +raw <= 32) raw = D.prefixToMask(+raw);
      if (p.kind === 'uncpath') raw = raw.replace(/\\+$/, '');
      if (KIND[p.kind] && !KIND[p.kind].test(raw)) { err = p.label + ': invalid value "' + raw + '"'; break; }
      out[p.key] = raw;
    }
    return [out, err];
  }

  // ── port of the real output colouring (classify_line) ─────────────────────────
  function classify(line) {
    const s = line.trim(), lo = s.toLowerCase();
    if (/^(✗|\[FAIL\]|\[TIMEOUT\])/.test(s)) return 'err';
    if (/^(⚠|\[WARN\]|WARN:)/.test(s)) return 'warn';
    if (/^(✓|\[OK\])/.test(s)) return 'ok';
    if (s.startsWith('ERROR:')) return 'err';
    if (['error', 'fail', 'denied', 'exception', 'critical'].some(k => lo.includes(k))) return 'err';
    if (['warn', 'skip', 'not found', 'empty', 'already', 'cannot', 'no reply'].some(k => lo.includes(k))) return 'warn';
    if (/\b(ok|pass|passed)\b/.test(lo) || ['freed', 'cleared', 'complete', 'restarted', 'removed', 'deleted', '✓'].some(k => lo.includes(k))) return 'ok';
    return 'out';
  }
  const TAG = { ok: 'success', warn: 'warning', err: 'error', out: 'output', info: 'info', dim: 'dim' };

  // ── run state ────────────────────────────────────────────────────────────────
  const STOP = { v: false };
  D.logs = [];            // [{name,size,modified,text}]
  D.last = null;
  const jobId = () => hex(10);

  async function* monitorGen(host, watch) {
    const extra = [];
    for (let ip of watch) { ip = (ip || '').trim(); if (ip && ip !== host && !extra.includes(ip)) extra.push(ip); }
    const targets = [host, ...extra];
    const stats = {}; targets.forEach(t => stats[t] = [0, 0]);
    let prevUp = null, prevRes = null;
    yield ['info', 'Ping Monitor started: ' + host + (extra.length ? ' + ' + extra.join(', ') : '') + '  -- keeps running until you press Stop'];
    while (!STOP.v) {
      const t0 = nowMs();
      const resIp = D.resolve(host);
      const ms = {}; targets.forEach(t => { ms[t] = D.pingMs(t); });
      const up = targets.filter(t => ms[t] !== null);
      targets.forEach(t => { stats[t][0]++; if (ms[t] !== null) stats[t][1]++; });
      const answering = [];
      up.forEach(t => { const ip = (t === host ? resIp : t) || t; if (!answering.includes(ip)) answering.push(ip); });
      const parts = targets.map(t => (t === host ? host + ' [' + (resIp || 'cannot resolve') + ']' : t) + ' ' + (ms[t] !== null ? 'reply ' + ms[t] + 'ms' : 'NO REPLY'));
      let winrm = '';
      if (answering.length) winrm = '  | WinRM 5985 ' + (T.unreachable.has(answering[0]) ? 'closed' : 'open');
      let line = D.clock(new Date()) + '  ' + parts.join('  |  ') + winrm;
      if (answering.length) line += '  >> answering IP: ' + answering.join(', ');
      yield [up.includes(host) ? 'ok' : (up.length ? 'warn' : 'err'), line];
      const nowUp = new Set(up);
      if (prevUp !== null) {
        for (const t of targets) {
          if (nowUp.has(t) && !prevUp.has(t)) yield ['ok', '   ▲ ' + t + ' is now ANSWERING'];
          else if (prevUp.has(t) && !nowUp.has(t)) yield ['warn', '   ▼ ' + t + ' stopped answering'];
        }
        if (!nowUp.size && prevUp.size) yield ['err', '   ✗ NOTHING answers right now (host name and watched IPs)'];
      }
      if (prevRes !== null && resIp !== prevRes) yield ['info', '   host name now resolves to ' + (resIp || 'nothing') + ' (was ' + (prevRes || 'nothing') + ')'];
      prevUp = nowUp; prevRes = resIp;
      const wait = Math.max(0, 1000 - (nowMs() - t0));
      // ~1 s cadence (never faster than 300 ms), but wake immediately on Stop
      const end = nowMs() + Math.max(scaled(wait), 300);
      while (nowMs() < end && !STOP.v) await new Promise(r => setTimeout(r, 40));
    }
    for (const t of targets) {
      const [sent, recv] = stats[t];
      const pct = sent ? 100 * (sent - recv) / sent : 0;
      yield ['info', 'Summary ' + t + ': sent ' + sent + ', replied ' + recv + ', lost ' + (sent - recv) + ' (' + pct.toFixed(0) + '% loss)'];
    }
  }

  // ── the run orchestrator -- mirrors app.py's generate() ───────────────────────
  async function* runGen(body) {
    const hostname = (body.hostname || '').trim(), username = (body.username || '').trim();
    const transport = body.transport || 'ntlm';
    const ids = new Set(body.tasks || []);
    const selected = OPS.filter(o => ids.has(o.id));
    const dangerous = selected.filter(o => o.danger);
    if (dangerous.length && !body.confirmed_danger) {
      yield { type: 'error', text: '  Refused: ' + dangerous.length + ' sensitive operation(s) require confirmed_danger=true: ' + dangerous.map(o => o.label).join(', ') };
      yield { type: 'done', success: false }; return;
    }
    const P = {}, perr = [];
    for (const op of selected) {
      if (op.params && op.params.length) {
        const [vals, err] = validateParams(op, (body.params || {})[op.id]);
        if (err) perr.push(op.label + ': ' + err); else P[op.id] = vals;
      }
    }
    if (perr.length) {
      yield { type: 'error', text: '  Refused: invalid parameter value(s):' };
      for (const e of perr) yield { type: 'error', text: '    - ' + e };
      yield { type: 'done', success: false }; return;
    }
    STOP.v = false;
    if (T.key !== hostname) { D.clearTimers(); D.resetTarget(hostname); }
    const now = new Date();
    const logName = 'AdminTool_' + hostname.replace(/[^\w\-.]/g, '_') + '_' + stamp2(now) + '.log';
    const logLines = [];
    const emit = (type, text) => { logLines.push(text); return { type, text }; };
    const hdr = ['='.repeat(60), '  PC ADMIN & PERFORMANCE TOOL  ' + META.version + '  -- Web-Service Edition', '  ' + COPYRIGHT, '='.repeat(60),
      '  Target   : ' + hostname, '  Username : ' + username, '  Transport: ' + transport, '  Date/Time: ' + stamp(now),
      '  Tasks    : ' + selected.length + ' selected', '  Log File : ' + logName, '='.repeat(60), ''];
    for (const line of hdr) {
      const t = (line.includes('=') || line.includes('TOOL')) ? 'header' : (/Target|Username|Date|Tasks|Log/.test(line) ? 'info' : 'dim');
      yield emit(t, line); await sleep(25);
    }
    const finish = async function* (stopped, counts) {
      const head = stopped ? 'STOPPED BY USER' : ((counts.WARNING || counts.FAILED) ? 'TASKS COMPLETED WITH ISSUES' : 'ALL TASKS COMPLETED ✓');
      const foot = ['='.repeat(60), '  ' + head, '  Result   : ' + counts.SUCCESS + ' succeeded, ' + counts.WARNING + ' warning, ' + counts.FAILED + ' failed',
        '  Finished : ' + stamp(new Date()), '  Log saved: ' + logName, '  ' + COPYRIGHT, '='.repeat(60)];
      for (const line of foot) {
        yield emit((stopped && line.includes('STOPPED')) || line.includes('WITH ISSUES') ? 'warning' : (line.includes('COMPLETED') ? 'success' : 'header'), line);
      }
      const text = logLines.join('\n');
      D.logs.unshift({ name: logName, size: text.length, modified: stamp(new Date()), text });
      D.last = { name: logName, text };
      yield { type: 'done', success: !stopped && counts.FAILED === 0, log: logName };
    };

    // Ping Monitor: runs inside the tool, no WinRM session
    const mon = selected.filter(o => o.monitor);
    if (mon.length) {
      if (selected.length > 1) {
        yield emit('error', '  ✗ Ping Monitor keeps running until you press Stop, so it must be run on its own. Untick the other tasks.');
        yield { type: 'done', success: false, log: logName }; return;
      }
      const pv = P[mon[0].id] || {};
      yield { type: 'task_start', text: '▶ [1/1]  ' + mon[0].label, idx: 0, total: 1, label: mon[0].label };
      logLines.push('\n▶ [1/1]  ' + mon[0].label);
      yield emit('dim', '    Purpose  : ' + mon[0].description);
      for await (const [k, text] of monitorGen(hostname, [pv.IP1, pv.IP2])) yield emit(TAG[k] || 'info', '    ' + text);
      const foot = ['', '='.repeat(60), '  PING MONITOR STOPPED', '  Finished : ' + stamp(new Date()), '  Log saved: ' + logName, '  ' + COPYRIGHT, '='.repeat(60)];
      for (const line of foot) yield emit(line.includes('=') || line.includes('MONITOR') ? 'header' : 'dim', line);
      const text = logLines.join('\n');
      D.logs.unshift({ name: logName, size: text.length, modified: stamp(new Date()), text }); D.last = { name: logName, text };
      yield { type: 'done', success: true, log: logName }; return;
    }

    // WinRM session
    if (/unreachable/i.test(hostname) || /nxdomain|\.invalid$/i.test(hostname)) {
      yield emit('error', '  ✗ Cannot open a WinRM session to ' + hostname + ' (demo: this host name is rigged to fail).');
      yield { type: 'done', success: false, log: logName }; return;
    }
    await sleep(350);
    yield emit('success', '  ✓ WinRM session established'); await sleep(200);

    const counts = { SUCCESS: 0, WARNING: 0, FAILED: 0 };
    let stopped = false;
    for (let i = 0; i < selected.length; i++) {
      const op = selected[i];
      if (STOP.v) { stopped = true; break; }
      yield { type: 'progress', value: Math.round(100 * i / selected.length) };
      yield { type: 'task_start', text: '▶ [' + (i + 1) + '/' + selected.length + ']  ' + op.label, idx: i, total: selected.length, label: op.label };
      logLines.push('\n▶ [' + (i + 1) + '/' + selected.length + ']  ' + op.label);
      yield emit('dim', '    Category : ' + op.category);
      yield emit('dim', '    Purpose  : ' + op.description);
      yield emit('dim', '    ' + '─'.repeat(50));
      await sleep(250);

      const ctx = { T, D, op, p: P[op.id] || {}, hostname, username, stop: STOP, jobId: jobId() };
      const sim = (window.DemoSims || {})[op.id];
      let level = null, msg = '', nominal = D.ri(18, 60) / 10, ok = true;
      const isDetached = !!(op.detached || op.net_disruptive);
      if (isDetached && !op.push) {
        yield emit('info', '    Job ' + ctx.jobId + ' started on the target (' + (op.category === 'Admin Consoles' ? 'SYSTEM scheduled task' : 'SYSTEM scheduled task') + ') -- waiting for the result (hard limit 255s).');
        await sleep(450);
      }
      const gen = sim ? sim(ctx) : (async function* () { yield 'No simulator for this operation yet.'; })();
      for await (const item of gen) {
        if (STOP.v && !op.monitor && ctx.interruptible) break;
        if (typeof item === 'string') {
          const lines = item.split('\n');
          for (const ln of lines) { yield emit(TAG[classify(ln)], '    ' + ln); await sleep(D.ri(40, 110)); }
        } else if (Array.isArray(item)) {
          yield emit(TAG[item[0]] || 'output', '    ' + item[1]); await sleep(D.ri(40, 110));
        } else if (item && item.res) { level = item.res[0]; msg = item.res[1]; }
        else if (item && item.sleep) { await sleep(item.sleep); }
        else if (item && item.nominal) { nominal = item.nominal; }
        else if (item && item.fail) { ok = false; }
      }
      // verdict -- identical rules to task_verdict() in the real engine
      let verdict;
      if (level === 'FAILED') verdict = 'FAILED';
      else if (level === 'WARNING') verdict = 'WARNING';
      else if (level === 'SUCCESS') verdict = ok ? 'SUCCESS' : 'WARNING';
      else verdict = ok ? 'SUCCESS' : (isDetached ? 'FAILED' : 'WARNING');
      counts[verdict]++;
      let status;
      if (level) {
        const sym = { SUCCESS: op.push ? '✓ PUSHED' : '✓ SUCCESS', WARNING: '⚠ WARNING', FAILED: '✗ FAILED' }[verdict];
        status = 'RESULT: ' + sym + ' — ' + (msg || 'finished');
      } else if (verdict === 'FAILED') status = 'RESULT: ✗ FAILED';
      else status = ok ? '✓ Completed' : '⚠ Completed with errors';
      yield emit({ SUCCESS: 'success', WARNING: 'warning', FAILED: 'error' }[verdict], '    ' + status + '  (' + nominal.toFixed(1) + 's)');
      yield emit('blank', '');
      yield { type: 'progress', value: Math.round(100 * (i + 1) / selected.length) };
      if (STOP.v) { stopped = true; break; }
    }
    yield* finish(stopped, counts);
  }

  // ── fetch shim: answers the page's four API calls ─────────────────────────────
  const enc = new TextEncoder();
  const json = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { 'Content-Type': 'application/json' } });
  const realFetch = window.fetch ? window.fetch.bind(window) : null;
  window.fetch = async function (url, opts = {}) {
    const u = String(url);
    if (!u.startsWith('/api/') && !u.includes('/api/')) return realFetch ? realFetch(url, opts) : Promise.reject(new Error('offline'));
    const path = u.slice(u.indexOf('/api/'));
    let body = {}; try { body = opts.body ? JSON.parse(opts.body) : {}; } catch (e) { }
    if (path === '/api/test') {
      await sleep(700);
      const h = (body.hostname || '').trim(), usr = (body.username || '').trim();
      if (!h) return json({ status: 'error', msg: 'Hostname is required' });
      if (!usr) return json({ status: 'error', msg: 'Username is required' });
      if (!body.password) return json({ status: 'warning', msg: 'Password is empty — connection may fail' });
      if (/nxdomain|\.invalid$/i.test(h)) return json({ status: 'error', msg: "Cannot resolve '" + h + "'. Check hostname or DNS." });
      if (/unreachable/i.test(h)) return json({ status: 'winrm_error', msg: 'Cannot reach WinRM on ' + h + ':5985.\nRun on target (Admin): Enable-PSRemoting -Force' });
      if ((body.password || '') === 'wrong') return json({ status: 'cred_error', msg: "Authentication failed for '" + usr + "' on " + h + ".\nTry: DOMAIN\\username  or  username@domain.local" });
      if (T.key !== h) { D.clearTimers(); D.resetTarget(h); }
      return json({ status: 'success', msg: 'Connected to ' + h + ' (' + T.ip + ") as '" + usr + "'. Remote computer: " + T.name + '. WinRM OK.' });
    }
    if (path === '/api/stop') { STOP.v = true; return json({ status: 'stopping' }); }
    if (path === '/api/logs') return json(D.logs.map(l => ({ name: l.name, size: l.size, modified: l.modified })));
    if (path === '/api/run') {
      const gen = runGen(body);
      const stream = new ReadableStream({
        async start(controller) {
          try { for await (const ev of gen) controller.enqueue(enc.encode('data: ' + JSON.stringify(ev) + '\n\n')); }
          catch (e) { controller.enqueue(enc.encode('data: ' + JSON.stringify({ type: 'error', text: '  Demo engine error: ' + e.message }) + '\n\n')); }
          controller.close();
        }
      });
      return new Response(stream, { headers: { 'Content-Type': 'text/event-stream' } });
    }
    return json({ error: 'not found' }, 404);
  };
  D.stop = () => { STOP.v = true; };
  D.classify = classify;
  D.COPYRIGHT = COPYRIGHT;
})();
