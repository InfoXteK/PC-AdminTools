/* Simulated output for the Cleanup / Disk / Performance / Windows Health operations.
   Formats follow the real PowerShell scripts' Write-Output lines (see "</> script" in the demo).
   Every number here is invented -- the demo never touches a real computer. */
(function () {
  'use strict';
  const D = window.DemoEngine, S = window.DemoSims = window.DemoSims || {};
  const { pad, lpad, ri, rf, pick } = D;
  const f1 = n => (+n).toFixed(1), f2 = n => (+n).toFixed(2);
  const num = n => Number(n).toLocaleString('en-US');
  const mbOf = c => (c.T.mb = c.T.mb || { user: 431.5, win: 96.2, pf: 12.4, thumb: 48.7, wu: 1342.8, browser: 786.3, recycle: 2150.6, evt: 38 });
  const spent = (c, key, lo = 0.1, hi = 2.5) => { const M = mbOf(c); const v = M[key]; M[key] = +(lo + D.rnd() * (hi - lo)).toFixed(1); return v; };
  const users = ['Administrator', 'jsmith', 'mjones', 'svc_backup'];

  // ── CLEANUP ────────────────────────────────────────────────────────────────
  S.clear_user_temp = async function* (c) {
    yield '  Running as : ' + c.username + '\n  Computer   : ' + c.T.name;
    yield '  Found ' + (users.length + 1) + ' user profile folder(s) under C:\\Users';
    const total = spent(c, 'user'); let left = total, denied = 0;
    const share = [0.04, 0.7, 0.2, 0.06];
    for (let i = 0; i < users.length; i++) {
      const v = i === 3 ? left : +(total * share[i]).toFixed(1); left -= v;
      if (users[i] === 'jsmith' && total > 5) { denied++; yield '  [' + users[i] + '] Freed ' + f1(v) + ' MB  (' + ri(2, 9) + ' file(s) skipped -- in use / access denied)'; }
      else yield '  [' + users[i] + '] Freed ' + f1(Math.max(v, 0)) + ' MB  (' + ri(12, 900) + ' items)';
      yield { sleep: 120 };
    }
    yield '  [Public] No temp folder (profile never fully loaded)';
    yield '  ------------------------------------------------';
    yield '  Profiles processed: ' + users.length + '   |   TOTAL FREED: ' + f1(total) + ' MB';
    if (denied) yield '  NOTE: ' + denied + ' profile(s) had files in use and were partially skipped (normal for the logged-in user\'s active session)';
  };
  S.clear_windows_temp = async function* (c) {
    const v = spent(c, 'win');
    yield '  Target folder : C:\\Windows\\Temp';
    yield '  Items found   : ' + num(ri(120, 900)); yield { sleep: 300 };
    yield '  Freed ' + f1(v) + ' MB  (' + ri(0, 6) + ' item(s) skipped -- in use)';
  };
  S.clear_prefetch = async function* (c) {
    const n = c.T.tmp.pf; c.T.tmp.pf = ri(0, 12);
    yield '  Prefetch folder : C:\\Windows\\Prefetch'; yield '  Files found     : ' + num(n); yield { sleep: 250 };
    yield '  Removed ' + num(n) + ' file(s) -- Windows rebuilds this cache on next boot (first launches may be slightly slower)';
  };
  S.clear_thumbnail_cache = async function* (c) {
    const v = spent(c, 'thumb');
    for (const u of users.slice(0, 3)) { yield '  [' + u + '] thumbcache_*.db cleared'; yield { sleep: 90 }; }
    yield '  Freed ' + f1(v) + ' MB';
  };
  S.clear_wu_cache = async function* (c) {
    const v = spent(c, 'wu');
    yield '  Stopping Windows Update service (wuauserv)...'; yield { sleep: 300 };
    yield '  Stopped.';
    yield '  Clearing C:\\Windows\\SoftwareDistribution\\Download ...'; yield { sleep: 400 };
    yield '  Freed ' + f1(v) + ' MB';
    yield '  Starting Windows Update service...'; yield '  Service restarted -- status: Running';
  };
  S.clear_browser_cache = async function* (c) {
    const v = spent(c, 'browser'); let l = v;
    const rows = [['Chrome', 0.52], ['Edge', 0.38], ['Firefox', 0.1]];
    for (const [b, sh] of rows) {
      const x = b === 'Firefox' ? l : +(v * sh).toFixed(1); l -= x;
      yield '  ' + pad(b, 8) + ' cache cleared for ' + users.length + ' profile(s)  --  ' + f1(Math.max(x, 0)) + ' MB'; yield { sleep: 150 };
    }
    yield '  TOTAL FREED: ' + f1(v) + ' MB   (sign-ins and bookmarks are untouched)';
  };
  S.clear_event_logs = async function* (c) {
    const logs = ['Application', 'Security', 'Setup', 'System', 'Windows PowerShell', 'Microsoft-Windows-WinRM/Operational'];
    let tot = 0;
    for (const l of logs) { const n = ri(80, 6000); tot += n; yield '  Cleared: ' + pad(l, 38) + num(n) + ' events'; yield { sleep: 90 }; }
    yield '  ' + logs.length + ' logs cleared (' + num(tot) + ' events removed)';
  };
  S.empty_recycle_bin = async function* (c) {
    const v = spent(c, 'recycle', 0, 0);
    yield '  Scanning recycle bins on all fixed drives...'; yield { sleep: 300 };
    yield '  C:\\$Recycle.Bin   ' + f1(v * 0.8) + ' MB'; yield '  D:\\$Recycle.Bin   ' + f1(v * 0.2) + ' MB';
    yield '  Recycle Bin emptied -- freed ' + f1(v) + ' MB';
  };
  S.disk_cleanup = async function* (c) {
    yield '  Registering cleanmgr categories (sagerun:99)...';
    yield '  Running: cleanmgr /sagerun:99'; yield { sleep: 500 };
    for (const p of ['Temporary Files', 'Downloaded Program Files', 'Recycle Bin', 'Windows Update Cleanup', 'Thumbnails']) { yield '  Cleaning: ' + p; yield { sleep: 260 }; }
    yield '  Disk Cleanup completed -- ' + f1(ri(300, 3200) / 1.0) + ' MB reclaimed';
  };
  S.flush_dns = async function* (c) {
    const before = c.T.dnsCache; c.T.dnsCache = ri(0, 4);
    yield '  === FLUSH DNS RESOLVER CACHE ===';
    yield '  Entries before : ' + before; yield { sleep: 350 };
    yield '    Windows IP Configuration'; yield '    Successfully flushed the DNS Resolver Cache.';
    yield '  DNS re-registration requested';
    yield '  Entries after  : ' + c.T.dnsCache;
    yield '  Gateway ' + c.T.gw + ' : reachable';
    yield { res: ['SUCCESS', 'DNS cache flushed (' + before + ' -> ' + c.T.dnsCache + ' entries) and DNS re-registration requested'] };
  };

  // ── DISK ───────────────────────────────────────────────────────────────────
  S.disk_space_report = async function* (c) {
    yield '  Drive   FS         Total     Used      Free      Used%   Health';
    yield '  ──────────────────────────────────────────────────────────────────';
    const rows = [['C', 'NTFS', 475.7, 312.4], ['D', 'NTFS', 931.5, 851.3], ['E', 'exFAT', 238.4, 61.0]];
    for (const [d, fs, t, u] of rows) {
      const pct = 100 * u / t, warn = pct > 90 ? '  ⚠ LOW SPACE' : pct > 80 ? '  ⚠ getting full' : '';
      yield '  ' + d + ':      ' + pad(fs, 10) + ' ' + f1(t) + ' GB    ' + f1(u) + ' GB    ' + f1(t - u) + ' GB   ' + f1(pct) + '%' + warn + '   Healthy'; yield { sleep: 140 };
    }
  };
  S.defrag_drives = async function* (c) {
    for (const [d, kind] of [['C', 'SSD'], ['D', 'HDD'], ['E', 'SSD']]) {
      yield '  Optimizing ' + d + ': (' + kind + ') -> ' + (kind === 'SSD' ? 'ReTrim' : 'Defrag'); yield { sleep: 700 };
      yield '  ' + d + ': done -- fragmentation ' + (kind === 'SSD' ? 'n/a (SSD)' : f1(D.rf(0.2, 3.9) ) + '% -> 0.0%');
    }
    yield '  3 volume(s) optimized';
  };
  S.disk_health_scan = async function* (c) {
    yield '  Physical disks:';
    yield '  ' + pad('Model', 28) + pad('Media', 8) + pad('Size', 10) + pad('Health', 10) + 'Status'; yield '  ' + '─'.repeat(66);
    yield '  ' + pad('Samsung SSD 980 PRO 512GB', 28) + pad('SSD', 8) + pad('476 GB', 10) + pad('Healthy', 10) + 'OK';
    yield '  ' + pad('WDC WD10EZEX-08WN4A0', 28) + pad('HDD', 8) + pad('932 GB', 10) + pad('Healthy', 10) + 'OK';
    yield '  Quick file-system scan (Repair-Volume -Scan) ...'; yield { sleep: 700 };
    yield '  C: no errors found'; yield '  D: no errors found';
    yield '  SMART predict-failure: none';
  };
  S.large_files_report = async function* (c) {
    yield '  Scanning C:\\ for the 20 largest files (this can take a while on a real PC)...'; yield { sleep: 600 };
    const files = [['C:\\hiberfil.sys', 12.7], ['C:\\pagefile.sys', 8.0], ['C:\\Users\\jsmith\\Videos\\team-offsite-2025.mp4', 6.4], ['C:\\Users\\jsmith\\Downloads\\Win11_23H2_English_x64.iso', 5.9],
      ['C:\\Users\\mjones\\AppData\\Local\\Temp\\vmware-export.vmdk', 4.8], ['C:\\ProgramData\\Package Cache\\VS2022\\vs_setup.cab', 3.1], ['C:\\Users\\jsmith\\Documents\\Backups\\laptop-2024.pst', 2.9],
      ['C:\\Windows\\MEMORY.DMP', 2.4], ['C:\\Users\\jsmith\\OneDrive\\Archive\\scans-2023.zip', 2.2], ['C:\\Program Files\\Adobe\\Adobe Premiere Pro\\media-cache.db', 1.9]];
    yield '  ' + pad('Size', 10) + 'Path'; yield '  ' + '─'.repeat(78);
    for (let i = 0; i < 20; i++) { const f = files[i] || ['C:\\Users\\jsmith\\AppData\\Local\\Microsoft\\Edge\\User Data\\Cache\\data_' + i, +(1.8 - i * 0.07).toFixed(2)]; yield '  ' + pad(f2(f[1]) + ' GB', 10) + f[0]; yield { sleep: 35 }; }
  };

  // ── PERFORMANCE ────────────────────────────────────────────────────────────
  S.high_perf_power = async function* (c) {
    yield '  Current plan : ' + c.T.powerPlan; yield '  Activating High Performance (powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c)...'; yield { sleep: 400 };
    c.T.powerPlan = 'High performance';
    yield '  Power Scheme GUID: 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c  (High performance)'; yield '  Verified: active plan is now High performance';
  };
  S.visual_effects_perf = async function* (c) {
    for (const k of ['VisualFXSetting = 2 (Adjust for best performance)', 'MinAnimate = 0 (minimize/maximize animation off)', 'TaskbarAnimations = 0', 'ListviewAlphaSelect = 0', 'DragFullWindows = 0']) { yield '  Set ' + k; yield { sleep: 120 }; }
    yield '  Visual effects optimized for performance -- applies at each user\'s next sign-in';
  };
  S.optimize_ram = async function* (c) {
    const tot = c.T.ramTotal, usedB = +(tot - c.T.ramFree).toFixed(2), rec = +D.rf(0.4, 1.6, 2);
    yield '  RAM BEFORE — Total: ' + f2(tot) + ' GB | Used: ' + f2(usedB) + ' GB | Free: ' + f2(c.T.ramFree) + ' GB'; yield { sleep: 600 };
    c.T.ramFree = +(c.T.ramFree + rec).toFixed(2);
    yield '  RAM AFTER  — Total: ' + f2(tot) + ' GB | Used: ' + f2(tot - c.T.ramFree) + ' GB | Free: ' + f2(c.T.ramFree) + ' GB'; yield '  Recovered : ' + f2(rec) + ' GB';
  };
  S.tune_sysmain = async function* (c) {
    yield '  Detecting system drive type...'; yield '  C: = SSD (Samsung SSD 980 PRO)'; yield '  SSD detected -> SysMain (Superfetch) is not needed'; yield { sleep: 300 };
    yield '  SysMain stopped and set to Disabled'; yield '  (On an HDD-only PC this step would re-enable SysMain instead)';
  };
  S.restart_search = async function* (c) {
    yield '  Stopping Windows Search (WSearch)...'; yield { sleep: 300 }; yield '  Deleting index database  C:\\ProgramData\\Microsoft\\Search\\Data\\Applications\\Windows\\Windows.edb'; yield { sleep: 300 };
    yield '  Starting Windows Search...'; yield '  Search indexer restarted -- rebuilding in the background (search may be incomplete for a while)';
  };
  S.startup_report = async function* (c) {
    yield '  === STARTUP PROGRAMS ===';
    const rows = [['OneDrive', 'HKCU\\...\\Run', 'jsmith'], ['Microsoft Teams', 'HKCU\\...\\Run', 'jsmith'], ['SecurityHealth', 'HKLM\\...\\Run', 'All Users'], ['RtkAudUService', 'HKLM\\...\\Run', 'All Users'],
      ['Zoom', 'HKCU\\...\\Run', 'mjones'], ['AdobeAAMUpdater', 'HKLM\\...\\Run', 'All Users'], ['Slack', 'Startup folder', 'mjones']];
    for (const r of rows) { yield '  ' + pad(r[0], 22) + pad(r[1], 18) + r[2]; yield { sleep: 60 }; }
    yield '  === AUTO-START SERVICES (non-Microsoft) ==='; yield '  ' + pad('Zoom Updater', 30) + 'Running'; yield '  ' + pad('Adobe Update Service', 30) + 'Running'; yield '  ' + pad('Dropbox Update', 30) + 'Stopped';
    yield '  ' + rows.length + ' startup item(s), 3 non-Microsoft auto-start service(s)';
  };
  S.pagefile_report = async function* (c) {
    yield '  Automatically managed : True'; yield '  ' + pad('Location', 16) + pad('Allocated', 12) + pad('CurrentUsage', 14) + 'PeakUsage';
    yield '  ' + pad('C:\\pagefile.sys', 16) + pad('2560 MB', 12) + pad('612 MB', 14) + '1450 MB';
    yield '  Physical RAM  : ' + f2(c.T.ramTotal) + ' GB'; yield '  Recommendation: system-managed is fine for this RAM size';
  };
  S.non_essential_services = async function* (c) {
    yield '  Running services that are usually not needed on a desktop:';
    for (const [n, d] of [['Spooler', 'Print Spooler'], ['Fax', 'Fax'], ['RemoteRegistry', 'Remote Registry'], ['WMPNetworkSvc', 'Windows Media Player Network Sharing'], ['XblGameSave', 'Xbox Live Game Save'], ['DiagTrack', 'Connected User Experiences and Telemetry']]) { yield '  ' + pad(n, 18) + d; yield { sleep: 70 }; }
    yield '  Report only -- nothing was stopped';
  };
  S.perf_dism_analyze_store = async function* (c) {
    yield '  Running: DISM /Online /Cleanup-Image /AnalyzeComponentStore'; yield { sleep: 900 };
    yield '  Component Store (WinSxS) information:'; yield '  Windows Explorer Reported Size of Component Store : 8.91 GB'; yield '  Actual Size of Component Store                   : 8.34 GB';
    yield '  Shared with Windows                              : 5.87 GB'; yield '  Backups and Disabled Features                    : 2.15 GB'; yield '  Cache and Temporary Data                         : 0.32 GB';
    yield '  Date of Last Cleanup                             : 2026-09-12 07:41:10'; yield '  Number of Reclaimable Packages                   : 4'; yield '  Component Store Cleanup Recommended               : Yes';
  };
  S.perf_dism_component_cleanup = async function* (c) {
    yield '  Running: DISM /Online /Cleanup-Image /StartComponentCleanup'; for (const p of [10, 38, 71, 100]) { yield '  [' + '='.repeat(p / 5) + ' '.repeat(20 - p / 5) + '] ' + p + '.0%'; yield { sleep: 450 }; }
    yield '  The operation completed successfully. Reclaimed approx 1.2 GB.';
  };
  S.perf_dism_resetbase = async function* (c) {
    yield '  WARNING: /ResetBase makes ALL superseded updates permanent -- installed updates can no longer be uninstalled.';
    yield '  Running: DISM /Online /Cleanup-Image /StartComponentCleanup /ResetBase'; for (const p of [8, 29, 54, 82, 100]) { yield '  [' + '='.repeat(p / 5) + ' '.repeat(20 - p / 5) + '] ' + p + '.0%'; yield { sleep: 500 }; }
    yield '  The operation completed successfully. Reclaimed approx 2.9 GB.';
  };
  S.perf_dism_health_scan = async function* (c) {
    for (const s of ['CheckHealth', 'ScanHealth']) { yield '  Running: DISM /Online /Cleanup-Image /' + s; yield { sleep: 700 }; yield '  ' + (s === 'CheckHealth' ? 'No component store corruption detected.' : 'No component store corruption detected. (scan 100.0%)'); }
    yield '  Image health: Healthy -- the operation completed successfully.';
  };
  S.perf_wmi_repo_check = async function* (c) {
    yield '  Running: winmgmt /verifyrepository'; yield { sleep: 600 }; yield '  WMI repository is consistent';
    yield '  CIM snapshot:'; yield '  Win32_OperatingSystem query : ' + ri(12, 40) + ' ms'; yield '  Win32_Processor query       : ' + ri(8, 30) + ' ms'; yield '  Win32_LogicalDisk query     : ' + ri(10, 45) + ' ms';
  };
  S.perf_wmi_repo_repair = async function* (c) {
    yield '  Stopping winmgmt...'; yield { sleep: 300 }; yield '  Running: winmgmt /salvagerepository'; yield { sleep: 800 }; yield '  WMI repository has been salvaged'; yield '  Restarting winmgmt...'; yield '  Repair completed -- repository consistent';
  };
  S.perf_rebuild_perf_counters = async function* (c) {
    yield '  Running: lodctr /R'; yield { sleep: 700 }; yield '  Info: Successfully rebuilt performance counter setting from system backup store';
    yield '  Running: winmgmt /resyncperf'; yield { sleep: 300 }; yield '  Performance counters rebuilt and WMI resynchronised';
  };
  S.perf_trim_ssd = async function* (c) {
    yield '  Running: Optimize-Volume -DriveLetter C -ReTrim -Verbose'; yield { sleep: 700 }; yield '  VERBOSE: Invoking retrim on Windows (C:)...'; yield '  VERBOSE: Retrim: 100% complete.'; yield '  ReTrim completed on 1 SSD volume(s) (HDD volumes are skipped)';
  };
  S.perf_pagefile_system_managed = async function* (c) {
    yield '  Setting AutomaticManagedPagefile = True ...'; yield { sleep: 300 }; yield '  Page file is now system-managed -- takes effect after the next restart';
  };

  // ── WINDOWS HEALTH ─────────────────────────────────────────────────────────
  S.system_info = async function* (c) {
    const up = Date.now() - c.T.bootTime, d = Math.floor(up / 864e5), h = Math.floor(up % 864e5 / 36e5), m = Math.floor(up % 36e5 / 6e4), s = Math.floor(up % 6e4 / 1e3);
    yield '  Hostname     : ' + c.T.name; yield '  Manufacturer : Dell Inc. Latitude 7440'; yield '  OS           : Microsoft Windows 11 Pro 64-bit'; yield '  OS Build     : 10.0.22631 (Build 22631)';
    yield '  CPU          : 13th Gen Intel(R) Core(TM) i7-1365U'; yield '  CPU Cores    : 10 Physical / 12 Logical'; yield '  CPU Speed    : 1800 MHz'; yield '  RAM Total    : ' + f2(c.T.ramTotal) + ' GB';
    yield '  BIOS         : Dell Inc. v1.12.1'; yield '  Last Boot    : ' + D.stamp(new Date(c.T.bootTime)); yield '  Uptime       : ' + d + 'd ' + h + 'h ' + m + 'm ' + s + 's';
    yield '  Domain       : ' + c.T.domain; yield '  Logged Users : ' + c.T.consoleUser;
  };
  S.top_processes = async function* (c) {
    const P = [['chrome', 14.2, 1210], ['Teams', 9.8, 842], ['MsMpEng', 6.1, 318], ['OUTLOOK', 3.4, 402], ['explorer', 2.2, 221], ['Code', 1.9, 598], ['svchost', 1.2, 96], ['dwm', 0.9, 188], ['SearchIndexer', 0.7, 71], ['OneDrive', 0.5, 142]];
    yield '  === TOP 10 BY CPU ==='; yield '  ' + pad('Process', 18) + pad('CPU %', 9) + pad('RAM (MB)', 10) + 'PID';
    for (const r of P) { yield '  ' + pad(r[0], 18) + pad(f1(r[1] + D.rnd() * 2), 9) + pad(r[2] + ri(-30, 30), 10) + ri(1200, 19000); yield { sleep: 50 }; }
    yield '  === TOP 10 BY RAM ==='; yield '  ' + pad('Process', 18) + pad('RAM (MB)', 10) + 'PID';
    for (const r of [...P].sort((a, b) => b[2] - a[2])) { yield '  ' + pad(r[0], 18) + pad(r[2] + ri(-30, 30), 10) + ri(1200, 19000); yield { sleep: 40 }; }
  };
  S.run_sfc = async function* (c) {
    yield '  Running: sfc /scannow'; yield '  Beginning system scan.  This process will take some time.'; yield '  Beginning verification phase of system scan.';
    yield { nominal: 412.6 };
    for (const p of [8, 23, 41, 58, 77, 94, 100]) { yield '  Verification ' + p + '% complete.'; yield { sleep: 420 }; }
    yield '  Windows Resource Protection did not find any integrity violations.';
  };
  S.run_dism = async function* (c) {
    yield '  Running: DISM /Online /Cleanup-Image /CheckHealth'; yield { sleep: 500 }; yield '  No component store corruption detected.';
    yield '  Running: DISM /Online /Cleanup-Image /ScanHealth'; for (const p of [20, 55, 100]) { yield '  [' + '='.repeat(p / 5) + ' '.repeat(20 - p / 5) + '] ' + p + '.0%'; yield { sleep: 450 }; }
    yield '  No component store corruption detected.'; yield '  The operation completed successfully.';
  };
  S.wu_history = async function* (c) {
    yield '  ' + pad('Date', 12) + pad('Result', 12) + 'Title'; yield '  ' + '─'.repeat(88);
    const rows = [['2026-10-14', 'Succeeded', '2026-10 Cumulative Update for Windows 11 23H2 (KB5044285)'], ['2026-10-14', 'Succeeded', 'Windows Malicious Software Removal Tool x64 (KB890830)'], ['2026-09-10', 'Succeeded', '2026-09 Cumulative Update for Windows 11 23H2 (KB5043145)'],
      ['2026-09-10', 'Failed', '.NET Framework 4.8.1 Security Update (KB5042881)'], ['2026-08-13', 'Succeeded', '2026-08 Cumulative Update for Windows 11 23H2 (KB5041585)'], ['2026-07-09', 'Succeeded', 'Dell Inc. - Firmware - 1.12.1'], ['2026-07-09', 'Succeeded', 'Intel - System - 31.0.101.5186']];
    for (const r of rows) { yield '  ' + pad(r[0], 12) + pad(r[1], 12) + r[2]; yield { sleep: 60 }; }
  };
  S.recent_errors = async function* (c) {
    yield '  Errors / critical events in the last 24 hours:';
    const rows = [['System', 7023, 'Service Control Manager', 'The Print Spooler service terminated with the following error'], ['Application', 1000, 'Application Error', 'Faulting application name: OUTLOOK.EXE, version 16.0.17928'], ['System', 10016, 'DistributedCOM', 'The application-specific permission settings do not grant Local Activation permission'], ['System', 36874, 'Schannel', 'An TLS 1.2 connection request was received from a remote client application, but none of the cipher suites supported by the client application are supported by the server']];
    for (const r of rows) { yield '  ' + D.clock(new Date(Date.now() - ri(1, 22) * 3600e3)) + '  [' + pad(r[0], 11) + '] ID ' + pad(r[1], 6) + pad(r[2], 26) + r[3].slice(0, 70); yield { sleep: 80 }; }
    yield '  ' + rows.length + ' distinct error(s) -- 2 of them repeated';
  };
  S.installed_software = async function* (c) {
    const sw = [['Google Chrome', '130.0.6723.70'], ['Microsoft 365 Apps', '16.0.17928'], ['Microsoft Teams', '24295.605'], ['7-Zip', '24.08'], ['Notepad++', '8.7.1'], ['Zoom Workplace', '6.2.5'], ['Adobe Acrobat', '24.003'], ['Visual Studio Code', '1.94.2'], ['VLC media player', '3.0.21'], ['Dell Command | Update', '5.4.0'], ['Mozilla Firefox', '131.0.2'], ['PuTTY', '0.81']];
    yield '  ' + pad('Name', 34) + pad('Version', 16) + 'Scope'; yield '  ' + '─'.repeat(60);
    for (const [n, v] of sw) { yield '  ' + pad(n, 34) + pad(v, 16) + (D.rnd() > 0.7 ? 'jsmith (per-user)' : 'All users'); yield { sleep: 45 }; }
    yield '  Total: ' + (sw.length + ri(40, 90)) + ' installed program(s) (first ' + sw.length + ' shown in this demo)';
  };
})();
