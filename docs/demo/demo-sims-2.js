/* Simulated output for Network / Power Recycle / Remote Tools / Admin Consoles / Network Push.
   The simulated target ("T") really changes: pushing an IP moves it, a forced restart takes it
   offline for ~25 s, a wrong-network address is unreachable, etc. -- watch it with Ping Monitor. */
(function () {
  'use strict';
  const D = window.DemoEngine, S = window.DemoSims = window.DemoSims || {};
  const { pad, lpad, ri, rf, pick } = D;
  const f1 = n => (+n).toFixed(1);
  const net2 = ip => ip.split('.').slice(0, 2).join('.');
  const net3 = ip => ip.split('.').slice(0, 3).join('.');
  const dnsOf = p => [p.DNS1, p.DNS2].filter(Boolean);
  const adapterRows = T => [{ n: T.adapter, s: 'Up', sp: '1 Gbps' }, { n: 'Wi-Fi', s: 'Disconnected', sp: '0 bps' }];
  const findAdapter = (T, name) => adapterRows(T).find(a => a.n.toLowerCase() === String(name).toLowerCase());
  const listAdapters = T => adapterRows(T).map(a => '    ' + a.n + '  [' + a.s + ']').join('\n');
  const prevDesc = T => (T.dhcp ? 'DHCP ' : 'static ') + T.ip + '/' + T.prefix + '  gw ' + T.gw + '  dns ' + T.dns.join(',');

  // ── NETWORK reports ────────────────────────────────────────────────────────
  S.net_ip_config = async function* (c) {
    const T = c.T;
    for (const a of adapterRows(T)) {
      yield '  ── ' + a.n + ' ──────────────────────────────';
      if (a.s === 'Up') {
        yield '  Description  : Intel(R) Ethernet Connection (17) I219-LM'; yield '  Status       : Up   ' + a.sp; yield '  MAC          : ' + T.mac;
        yield '  DHCP         : ' + (T.dhcp ? 'Enabled' : 'Disabled'); yield '  IPv4 Address : ' + T.ip + '/' + T.prefix; yield '  Gateway      : ' + T.gw; yield '  DNS Servers  : ' + T.dns.join(', ');
      } else { yield '  Description  : Intel(R) Wi-Fi 6E AX211 160MHz'; yield '  Status       : Disconnected'; }
      yield { sleep: 150 };
    }
  };
  S.net_connectivity = async function* (c) {
    const T = c.T;
    for (const [lbl, tgt, ms] of [['Gateway', T.gw, 1], ['Primary DNS', T.dns[0], 2], ['Internet (8.8.8.8)', '8.8.8.8', 14], ['Internet (1.1.1.1)', '1.1.1.1', 12]]) {
      yield '  Pinging ' + pad(lbl, 20) + tgt; yield { sleep: 260 };
      yield '    Reply from ' + tgt + ': 4/4 received, avg ' + (ms + ri(0, 4)) + ' ms, 0% loss';
    }
    yield '  Name resolution (www.microsoft.com): OK ' + ri(8, 30) + ' ms';
  };
  S.net_adapter_stats = async function* (c) {
    yield '  ' + pad('Adapter', 12) + pad('Speed', 10) + pad('Sent (MB)', 14) + pad('Received (MB)', 16) + 'Errors';
    yield '  ' + pad(c.T.adapter, 12) + pad('1 Gbps', 10) + pad(num(ri(4000, 90000) / 10), 14) + pad(num(ri(20000, 400000) / 10), 16) + '0';
    yield '  ' + pad('Wi-Fi', 12) + pad('0 bps', 10) + pad('0', 14) + pad('0', 16) + '0';
    function num(n) { return f1(n); }
  };
  S.dns_test = async function* (c) {
    yield '  DNS server under test: ' + c.T.dns[0];
    for (const h of ['www.microsoft.com', 'login.microsoftonline.com', 'dc01.' + c.T.domain, 'fileserver.' + c.T.domain, 'www.github.com']) { yield { sleep: 200 }; yield '  ' + pad(h, 36) + 'OK   ' + ri(6, 45) + ' ms'; }
    yield '  5/5 names resolved -- average ' + ri(12, 28) + ' ms';
  };
  S.firewall_status = async function* (c) {
    for (const p of ['Domain', 'Private', 'Public']) { yield '  ' + pad(p + ' profile', 18) + 'Enabled   Inbound: Block   Outbound: Allow'; yield { sleep: 100 }; }
    yield '  Windows Defender: Real-time protection ON, signatures 2026-10-22 (up to date)'; yield '  Last quick scan : ' + D.stamp(new Date(Date.now() - 86400e3));
  };
  S.active_connections = async function* (c) {
    yield '  ' + pad('Local', 24) + pad('Remote', 24) + pad('State', 14) + 'Process';
    for (const r of [[c.T.ip + ':50321', '142.250.74.14:443', 'Established', 'chrome'], [c.T.ip + ':50344', '52.113.194.132:443', 'Established', 'Teams'], [c.T.ip + ':50377', c.T.gw.replace(/\.1$/, '.20') + ':445', 'Established', 'System'],
      [c.T.ip + ':5985', c.T.gw.replace(/\.1$/, '.77') + ':51812', 'Established', 'svchost'], ['0.0.0.0:3389', '0.0.0.0:0', 'Listen', 'svchost'], ['0.0.0.0:445', '0.0.0.0:0', 'Listen', 'System']]) { yield '  ' + pad(r[0], 24) + pad(r[1], 24) + pad(r[2], 14) + r[3]; yield { sleep: 50 }; }
  };
  S.reset_network = async function* (c) {
    yield '  === RESET TCP/IP AND WINSOCK ===';
    for (const s of ['Winsock catalog', 'TCP/IP (IPv4)', 'TCP/IP (IPv6)', 'DNS cache flush', 'DNS registration', 'Release address', 'Renew address']) { yield { sleep: 260 }; yield '  [OK]      ' + s; }
    D.outage(0, 3000);
    yield '  Network address now: ' + c.T.ip; yield '  NOTE: a REBOOT is required to finish applying the Winsock / TCP-IP reset';
    yield { res: ['SUCCESS', 'Winsock and TCP/IP stack reset, address renewed. REBOOT REQUIRED to finish applying'] };
  };

  // ── adapter restart family (verified versions with RESULT) ─────────────────
  S.pr_restart_all_adapters = async function* (c) {
    yield '  === RESTART ALL NETWORK ADAPTERS ==='; for (const a of adapterRows(c.T)) yield '  Before: ' + a.n + ' = ' + a.s;
    D.outage(0, 5000); yield { sleep: 600 }; yield '  Restarted: ' + c.T.adapter; yield { sleep: 1500 };
    yield '  === AFTER ==='; for (const a of adapterRows(c.T)) yield '  ' + a.n + ' = ' + a.s;
    yield { res: ['SUCCESS', 'All 1 active adapter(s) restarted and are Up again'] };
  };
  const adapterOp = (mode) => async function* (c) {
    const name = c.p.ADAPTER, a = findAdapter(c.T, name);
    yield '  === ' + (mode === 'restart' ? 'RESTART ADAPTER' : 'DISABLE / ENABLE ADAPTER') + " '" + name + "' ===";
    if (!a) { yield "  Adapter '" + name + "' not found. Available adapters:"; yield listAdapters(c.T); yield { res: ['FAILED', "Adapter '" + name + "' does not exist on the target -- nothing was changed"] }; return; }
    yield '  BEFORE: ' + a.n + ' = ' + a.s;
    if (a.n === c.T.adapter) D.outage(0, 5500);
    yield { sleep: 800 }; if (mode !== 'restart') { yield { sleep: 600 }; }
    if (a.s === 'Up') { yield '  AFTER : ' + a.n + ' = Up'; yield { res: ['SUCCESS', "'" + a.n + "' " + (mode === 'restart' ? 'restarted' : 'disabled, re-enabled') + ' and is Up'] }; }
    else { yield '  AFTER : ' + a.n + ' = Disconnected'; yield { res: ['WARNING', "'" + a.n + "' was 'Disconnected' before and is 'Disconnected' now (link/cable?)"] }; }
  };
  S.pr_restart_named_adapter = adapterOp('restart');
  S.pr_disable_enable_adapter = adapterOp('cycle');

  // ── verified Set Static IP / DHCP (rt_*) ───────────────────────────────────
  S.rt_set_static_ip = async function* (c) {
    const T = c.T, p = c.p, dns = dnsOf(p);
    yield '  === SET STATIC IP ==='; yield '  Adapter : ' + p.ADAPTER; yield '  Request : ' + p.IP + ' / ' + p.MASK + '   gateway ' + p.GATEWAY + '   DNS: ' + dns.join(' ');
    yield { sleep: 400 };
    const bad = staticChecks(c);
    if (bad) { if (bad.list) { yield "  Adapter '" + p.ADAPTER + "' not found. Available adapters:"; yield listAdapters(T); } yield { res: ['FAILED', bad.msg + ' -- nothing was changed'] }; return; }
    const prefix = D.maskToPrefix(p.MASK), prev = { ip: T.ip, mask: T.mask, gw: T.gw, dns: T.dns.slice(), dhcp: T.dhcp };
    yield '  Before  : ' + prevDesc(T); yield '  Applying address, mask, gateway and DNS in ONE step...'; yield '  Ok.'; yield { sleep: 700 };
    const sameNet = net2(p.IP) === net2(T.ip);
    if (p.ROLLBACK && !sameNet) {
      D.outage(0, 5000);
      yield '  === VERIFICATION ==='; yield '  IP address   : ' + p.IP + '/' + prefix + '  state Preferred'; yield '  Gateway      : ' + p.GATEWAY; yield '  DNS servers  : ' + (dns.join(', ') || T.dns.join(', '));
      yield '  Waiting up to 90s for the admin tool to reach this PC on the new address...'; yield { sleep: 1800 };
      yield '  The admin tool could NOT reach this PC after the change -- reverting to the previous configuration.'; yield { sleep: 700 };
      yield '  Now     : ' + T.ip + '/' + T.prefix + '  gw ' + T.gw;
      yield { res: ['WARNING', 'REVERTED: ' + p.IP + ' was applied but this PC was not reachable from the admin tool on it (wrong subnet/VLAN/routing?). Previous configuration restored. Untick auto-rollback to keep it anyway'] }; return;
    }
    D.applyAddress({ ip: p.IP, mask: p.MASK, gw: p.GATEWAY, dns: dns.length ? dns : null, afterMs: 900 });
    yield '  === VERIFICATION ==='; yield '  IP address   : ' + p.IP + '/' + prefix + '  state Preferred'; yield '  Gateway      : ' + p.GATEWAY; yield '  DNS servers  : ' + (dns.join(', ') || T.dns.join(', '));
    yield '  Gateway ping : reply from ' + p.GATEWAY;
    if (!sameNet) {   // rollback OFF on a wrong network: the tool can no longer see the PC
      yield { sleep: 1500 }; yield ['warn', 'Old address and hostname are not answering -- the new address is ' + p.IP + ' but it does not answer from here'];
      yield ['warn', 'Target not answering yet (network change in progress?) ... (15s)']; yield ['warn', 'Target not answering yet (network change in progress?) ... (30s)']; yield { sleep: 600 };
      yield ['err', 'TARGET_NOT_REACHED: no result within 255s. The change may still have been applied -- check the target directly (job id ' + c.jobId + ', files in C:\\ProgramData\\PCAdminTool). Tried: ' + p.IP + ', ' + c.hostname];
      yield { fail: true }; return;
    }
    if (p.ROLLBACK) { yield '  Waiting up to 90s for the admin tool to reach this PC on the new address...'; }
    yield { sleep: 1200 }; yield ['info', 'Old address and hostname are not answering -- the new address answers: ' + p.IP];
    yield ['ok', 'Target answered on its NEW address ' + p.IP + ' -- using it from now on.']; yield ['ok', 'Target is reachable again (' + p.IP + ').'];
    if (p.ROLLBACK) yield '  Admin tool reached this PC -- change confirmed.';
    yield { res: ['SUCCESS', 'Static IP ' + p.IP + '/' + prefix + ' gateway ' + p.GATEWAY + " applied and verified on '" + p.ADAPTER + "'"] };
  };
  function staticChecks(c) {
    const T = c.T, p = c.p;
    if (!findAdapter(T, p.ADAPTER)) return { list: true, msg: "Adapter '" + p.ADAPTER + "' does not exist on the target" };
    const pre = D.maskToPrefix(p.MASK), m = D.ip2n(D.prefixToMask(pre));
    if (p.IP === p.GATEWAY) return { msg: 'IP address and gateway are the same (' + p.IP + ')' };
    if ((D.ip2n(p.IP) & m) !== (D.ip2n(p.GATEWAY) & m)) return { msg: 'Gateway ' + p.GATEWAY + ' is not inside the subnet of ' + p.IP + ' / ' + p.MASK };
    if (p.IP !== T.ip && (p.IP === T.gw || p.IP === T.dns[0] || p.IP.endsWith('.1'))) return { msg: p.IP + ' is already in use by another device on the network' };
    return null;
  }
  S.rt_set_dhcp = async function* (c) {
    const T = c.T, p = c.p, a = findAdapter(T, p.ADAPTER);
    yield '  === SWITCH TO DHCP ==='; yield { sleep: 300 };
    if (!a) { yield "  Adapter '" + p.ADAPTER + "' not found. Available adapters:"; yield listAdapters(T); yield { res: ['FAILED', "Adapter '" + p.ADAPTER + "' does not exist on the target -- nothing was changed"] }; return; }
    yield '  Before  : ' + prevDesc(T); yield '  Switching address AND DNS to DHCP in ONE step...'; yield '  Ok.'; yield '  Requesting a lease (max 25s)...'; yield { sleep: 900 };
    if (a.s !== 'Up') {
      yield '  Note: adapter status is \'' + a.s + '\' (cable/link may be down)'; yield '  === VERIFICATION ==='; yield '  No DHCP lease was obtained within 40s (adapter fell back to 169.254.' + ri(1, 254) + '.' + ri(1, 254) + ').';
      if (p.ROLLBACK && !T.dhcp) { yield '  Reverting to the previous static configuration...'; yield { res: ['WARNING', 'REVERTED: DHCP is enabled but no DHCP server answered within 40s. Previous static configuration restored'] }; }
      else yield { res: ['WARNING', "DHCP is enabled on '" + a.n + "' but no lease was obtained within 40s -- check the DHCP server / cable / VLAN"] };
      return;
    }
    const ip = net3(T.ip) + '.' + ri(100, 199);
    D.applyAddress({ ip, mask: T.mask, gw: T.gw, dns: [T.gw.replace(/\.1$/, '.5'), '8.8.8.8'], dhcp: true, afterMs: 800 });
    yield '  === VERIFICATION ==='; yield '  IP address   : ' + ip + '/' + T.prefix; yield '  Gateway      : ' + T.gw; yield '  DNS servers  : ' + T.gw.replace(/\.1$/, '.5') + ', 8.8.8.8';
    yield { sleep: 1500 }; yield ['info', 'Old address and hostname are not answering -- the new address answers: ' + ip]; yield ['ok', 'Target answered on its NEW address ' + ip + ' -- using it from now on.'];
    if (p.ROLLBACK) yield '  Admin tool reached this PC -- change confirmed.';
    yield { res: ['SUCCESS', "DHCP enabled on '" + a.n + "' -- lease " + ip + '/' + T.prefix + ', gateway ' + T.gw] };
  };

  // ── NETWORK PUSH (v16 idea: pre-check, push, do not wait) ──────────────────
  const pushHead = 'Pre-check on the target (nothing is changed yet)...';
  const pushed = (c, msg) => ({ res: ['SUCCESS', msg + ' -- via background process (CIM); not waiting for a reply (job ' + c.jobId + ', log in C:\\ProgramData\\PCAdminTool)'] });
  S.np_set_static_ip = async function* (c) {
    const T = c.T, p = c.p, dns = dnsOf(p);
    yield '  ' + pushHead; yield { sleep: 400 };
    const bad = staticChecks(c);
    if (bad) { if (bad.list) { yield "  Adapter '" + p.ADAPTER + "' not found. Available adapters:"; yield listAdapters(T); } yield { res: ['FAILED', bad.msg + ' -- nothing was pushed'] }; return; }
    yield '  Now     : ' + prevDesc(T); yield '  Pushing : ' + p.IP + ' / ' + p.MASK + '  gw ' + p.GATEWAY + '  dns ' + (dns.join(' ') || '(unchanged)'); yield { sleep: 700 };
    D.applyAddress({ ip: p.IP, mask: p.MASK, gw: p.GATEWAY, dns: dns.length ? dns : null, afterMs: 5000 });
    yield pushed(c, 'Static IP set command pushed to the target machine');
  };
  S.np_set_dhcp = async function* (c) {
    const T = c.T, p = c.p, a = findAdapter(T, p.ADAPTER);
    yield '  ' + pushHead; yield { sleep: 400 };
    if (!a) { yield "  Adapter '" + p.ADAPTER + "' not found. Available adapters:"; yield listAdapters(T); yield { res: ['FAILED', "Adapter '" + p.ADAPTER + "' does not exist on the target -- nothing was pushed"] }; return; }
    yield '  Now     : ' + prevDesc(T); yield '  Pushing : switch address AND DNS to DHCP'; yield { sleep: 600 };
    if (a.s === 'Up') D.applyAddress({ ip: net3(T.ip) + '.' + ri(100, 199), mask: T.mask, gw: T.gw, dns: [T.gw.replace(/\.1$/, '.5'), '8.8.8.8'], dhcp: true, afterMs: 5000 });
    yield pushed(c, 'DHCP command pushed to the target machine');
  };
  S.np_flush_dns = async function* (c) {
    yield '  Pushing : flush the DNS resolver cache and re-register DNS'; yield { sleep: 600 }; c.T.dnsCache = 0; yield pushed(c, 'Flush DNS command pushed to the target machine');
  };
  S.np_reset_network = async function* (c) {
    yield '  Pushing : reset Winsock + TCP/IP (IPv4 and IPv6), flush DNS, release and renew the address'; yield { sleep: 600 };
    D.outage(5000, 9000); yield pushed(c, 'TCP/IP + Winsock reset command pushed to the target machine');
  };
  S.np_restart_all_adapters = async function* (c) {
    yield '  Adapters on the target: ' + adapterRows(c.T).map(a => a.n + '=' + a.s).join(', '); yield '  Pushing : restart every network adapter'; yield { sleep: 500 };
    D.outage(5000, 6000); yield pushed(c, 'Restart-all-adapters command pushed to the target machine');
  };
  const pushAdapter = (what, msg) => async function* (c) {
    const a = findAdapter(c.T, c.p.ADAPTER);
    if (!a) { yield "  Adapter '" + c.p.ADAPTER + "' not found. Available adapters:"; yield listAdapters(c.T); yield { res: ['FAILED', "Adapter '" + c.p.ADAPTER + "' does not exist on the target -- nothing was pushed"] }; return; }
    yield '  Now     : ' + a.n + ' = ' + a.s; yield '  Pushing : ' + what; yield { sleep: 500 };
    if (a.n === c.T.adapter) D.outage(5000, 7000);
    yield pushed(c, msg);
  };
  S.np_restart_named_adapter = pushAdapter('restart this adapter', 'Restart-adapter command pushed to the target machine');
  S.np_disable_enable_adapter = pushAdapter('disable, wait 3 s, enable this adapter', 'Disable/Enable command pushed to the target machine');

  // ── POWER RECYCLE ──────────────────────────────────────────────────────────
  S.pr_collect_evidence = async function* (c) {
    yield '  Snapshot taken ' + D.stamp(new Date()); yield '  Uptime         : 3d 5h 17m'; yield '  Top CPU        : chrome 14.2%, Teams 9.8%, MsMpEng 6.1%'; yield '  Devices with problems: 1';
    yield '  ' + pad('Class', 12) + pad('Status', 10) + 'Name'; yield '  ' + pad('USB', 12) + pad('Error', 10) + 'Unknown USB Device (Device Descriptor Request Failed)';
    yield '  Saved to C:\\ProgramData\\PCAdminTool\\evidence_' + D.stamp(new Date()).replace(/[: -]/g, '') + '.txt';
  };
  S.pr_diagnose_driver_hang = async function* (c) {
    yield '  Processes not responding : 0'; yield '  Highest CPU (sustained)  : chrome 14.2%'; yield '  Kernel handles (top)     : System 41,208'; yield '  Drivers in a pending-I/O state: none';
    yield '  Disk queue length        : 0.3 (normal)'; yield '  Verdict: no sign of a driver hang right now';
  };
  S.pr_list_storage_devices = async function* (c) {
    yield '  Storage controllers:'; yield '    Standard NVM Express Controller       OK'; yield '    Intel(R) 600 Series SATA AHCI Controller   OK'; yield '  Disk drives:';
    yield '    Samsung SSD 980 PRO 512GB   (NVMe)   476 GB   OK'; yield '    WDC WD10EZEX-08WN4A0        (SATA)   932 GB   OK';
  };
  S.pr_list_usb_devices = async function* (c) {
    yield '  ' + pad('Status', 8) + pad('Class', 10) + 'Name  (InstanceId)'; for (const r of [['OK', 'USB', 'USB Root Hub (USB 3.0)', 'USB\\ROOT_HUB30\\4&1A2B3C&0&0'], ['OK', 'HIDClass', 'USB Input Device', 'USB\\VID_046D&PID_C52B\\5&2A3B&0&1'], ['OK', 'Camera', 'Integrated Webcam', 'USB\\VID_0C45&PID_6A10\\5&2A3B&0&6'], ['Error', 'USB', 'Unknown USB Device (Device Descriptor Request Failed)', 'USB\\VID_0000&PID_0002\\5&2A3B&0&3']]) { yield '  ' + pad(r[0], 8) + pad(r[1], 10) + r[2]; yield '            ' + r[3]; yield { sleep: 70 }; }
  };
  S.pr_cycle_device_by_id = async function* (c) {
    yield '  Device : ' + c.p.DEVICE_ID; yield '  Disabling device (Disable-PnpDevice)...'; yield { sleep: 700 }; yield '  Disabled.'; yield '  Enabling device (Enable-PnpDevice)...'; yield { sleep: 700 }; yield '  Enabled -- device status: OK';
  };
  S.pr_cycle_usb_hubs = async function* (c) {
    for (const h of ['USB Root Hub (USB 3.0)', 'Generic USB Hub', 'USB Composite Device']) { yield '  Cycling: ' + h; yield { sleep: 500 }; yield '    Disable -> Enable OK'; }
    yield '  3 hub device(s) cycled -- attached USB devices re-enumerate (keyboard/mouse may blink for a second)';
  };
  S.pr_firmware_info = async function* (c) {
    yield '  BIOS vendor   : Dell Inc.'; yield '  BIOS version  : 1.12.1'; yield '  Release date  : 2025-08-19'; yield '  SMBIOS        : 3.4'; yield '  Secure Boot   : Enabled'; yield '  TPM           : 2.0 present, ready'; yield '  Boot mode     : UEFI';
  };
  S.pr_force_restart = async function* (c) {
    yield '  Sending: shutdown /r /f /t 0 /c "Admin tool: forced restart"'; yield { sleep: 600 }; yield '  Restart command accepted -- the target is going down now';
    c.T.rebootUntil = c.T.at(28000); c.T.bootTime = c.T.at(28000); yield '  (Tip: run the Ping Monitor now and watch it go down and come back)';
  };
  S.pr_wake_armed_devices = async function* (c) {
    yield '  Devices armed to wake the system:'; yield '    Intel(R) Ethernet Connection (17) I219-LM'; yield '    HID-compliant mouse'; yield '    Dell Universal Receiver';
  };
  S.pr_disable_hibernation = async function* (c) {
    yield '  Running: powercfg /hibernate off'; yield { sleep: 500 }; c.T.hibernation = false; yield '  Hibernation disabled -- hiberfil.sys (12.7 GB) removed';
  };
  S.pr_force_signout_restart = async function* (c) {
    yield '  Sending: shutdown /g /f /t 0 (sign out, restart, re-open registered apps)'; yield { sleep: 600 }; yield '  Command accepted -- signing out ' + c.T.consoleUser + ' and restarting';
    c.T.rebootUntil = c.T.at(30000); c.T.bootTime = c.T.at(30000);
  };
  S.pr_full_soft_recycle = async function* (c) {
    yield '  Step 1/3  Restart network adapters...'; yield { sleep: 600 }; yield '  Step 1/3  done';
    yield '  Step 2/3  Cycle USB hubs...'; yield { sleep: 600 }; yield '  Step 2/3  done';
    if (c.p.AUTO_RESTART) { yield '  Step 3/3  Restart scheduled (shutdown /r /t 30)'; c.T.rebootUntil = c.T.at(35000); c.T.bootTime = c.T.at(35000); }
    else yield '  Step 3/3  Restart NOT requested (AUTO_RESTART is off) -- restart manually when convenient';
  };

  // ── REMOTE TOOLS ───────────────────────────────────────────────────────────
  const renameOp = (kind) => async function* (c) {
    const T = c.T, nn = c.p.NEW_NAME;
    yield '  Current name : ' + T.name + '  (domain: ' + T.domain + ')'; yield '  New name     : ' + nn; yield { sleep: 400 };
    if (kind === 'workgroup') {
      yield ['err', '  This PC is domain-joined (' + T.domain + ') -- the Workgroup/Local rename refuses to run here.']; yield '  Use "Rename Computer (Domain-Joined)" instead.'; yield { fail: true }; return;
    }
    if (kind === 'domain') yield '  Using the supplied admin credential for the domain controller (a WinRM logon cannot hop onward by itself)...';
    if (kind === 'wmic') yield '  wmic.exe is not present on this Windows build -- using the WMI/CIM Rename method instead';
    yield { sleep: 800 }; yield '  Rename succeeded -- the new name ' + nn + ' takes effect after a restart';
    if (c.p.AUTO_RESTART) { yield '  Restart scheduled in 30 seconds'; T.name = nn.toUpperCase(); T.rebootUntil = T.at(34000); T.bootTime = T.at(34000); }
    else if (kind !== 'wmic') yield '  Restart NOT requested -- restart the PC to finish';
    else yield '  Manual restart required';
  };
  S.rt_rename_pc_domain = renameOp('domain'); S.rt_rename_pc_workgroup = renameOp('workgroup'); S.rt_rename_pc_wmic_legacy = renameOp('wmic');
  const vss = (c) => (c.T.vss = c.T.vss || { C: 3, D: 2 });
  const vol = v => String(v || '').replace(':', '').toUpperCase();
  S.rt_vss_view = async function* (c) {
    const V = vss(c); yield '  VSS shadow copies:'; for (const k of Object.keys(V)) { yield '  Volume ' + k + ':  ' + V[k] + ' shadow cop' + (V[k] === 1 ? 'y' : 'ies'); for (let i = 0; i < V[k]; i++) yield '     {' + D.hex(8) + '-' + D.hex(4) + '-' + D.hex(4) + '}  created ' + D.stamp(new Date(Date.now() - (i + 1) * 5 * 864e5)); }
  };
  S.rt_vss_delete_all = async function* (c) { const V = vss(c); yield '  Running: vssadmin delete shadows /all /quiet'; yield { sleep: 700 }; for (const k of Object.keys(V)) { yield '  Deleted ' + V[k] + ' shadow cop' + (V[k] === 1 ? 'y' : 'ies') + ' on ' + k + ':'; V[k] = 0; } };
  S.rt_vss_delete_volume_all = async function* (c) { const V = vss(c), v = vol(c.p.VOLUME); if (!(v in V)) V[v] = 0; yield '  Running: vssadmin delete shadows /for=' + v + ': /all /quiet'; yield { sleep: 600 }; yield '  Deleted ' + V[v] + ' shadow copy(ies) on ' + v + ':'; V[v] = 0; };
  S.rt_vss_delete_oldest = async function* (c) {
    const V = vss(c), vols = c.p.VOLUME ? [vol(c.p.VOLUME)] : Object.keys(V);
    for (const v of vols) { if (!V[v]) { yield '  ' + v + ': no shadow copies to delete'; continue; } yield '  Running: vssadmin delete shadows /for=' + v + ': /oldest /quiet'; yield { sleep: 400 }; V[v]--; yield '  Deleted the oldest shadow copy on ' + v + ': (' + V[v] + ' left)'; }
  };
  S.rt_vss_size_report = async function* (c) {
    yield '  ' + pad('Volume', 8) + pad('Used', 10) + pad('Allocated', 12) + pad('Max', 10) + 'Copies'; for (const [v, u, a, m] of [['C:', 18.4, 21.0, 47.6], ['D:', 6.2, 8.0, 93.1]]) { yield '  ' + pad(v, 8) + pad(u + ' GB', 10) + pad(a + ' GB', 12) + pad(m + ' GB', 10) + (vss(c)[v[0]] || 0); yield { sleep: 90 }; }
  };
  S.rt_vss_set_maxsize = async function* (c) {
    const v = vol(c.p.VOLUME); yield '  Running: vssadmin resize shadowstorage /for=' + v + ': /on=' + (c.p.STORAGE_VOLUME ? vol(c.p.STORAGE_VOLUME) : v) + ': /maxsize=' + c.p.MAX_SIZE; yield { sleep: 600 };
    yield '  Successfully resized the shadow copy storage association'; c.T.vssMax = c.p.MAX_SIZE;
  };
  S.rt_vss_create_snapshot = async function* (c) { const V = vss(c), v = vol(c.p.VOLUME); V[v] = (V[v] || 0) + 1; yield '  Creating shadow copy on ' + v + ': ...'; yield { sleep: 900 }; yield '  Shadow copy created: {' + D.hex(8) + '-' + D.hex(4) + '-' + D.hex(4) + '}  (' + V[v] + ' now on ' + v + ':)'; };
  S.rt_run_scheduled_task_query = async function* (c) {
    const n = c.p.TASK_NAME; yield '  Task name   : \\' + n; yield '  State       : Ready'; yield '  Last run    : ' + D.stamp(new Date(Date.now() - 6 * 3600e3)); yield '  Last result : 0 (The operation completed successfully.)'; yield '  Next run    : ' + D.stamp(new Date(Date.now() + 18 * 3600e3)); yield '  Run as      : SYSTEM';
  };
  S.rt_open_computer_management = async function* (c) {
    yield '  This operation launches the Computer Management console on the ADMIN PC (not on the target),'; yield '  pointed at \\\\' + c.T.name + ':  mmc.exe compmgmt.msc /computer:\\\\' + c.T.name;
    yield '  A browser demo cannot start a program on your computer -- in the real tool it opens here.';
  };
  const SVCS = { spooler: 'Print Spooler', wuauserv: 'Windows Update', bits: 'Background Intelligent Transfer Service', w32time: 'Windows Time', dnscache: 'DNS Client', wsearch: 'Windows Search', lanmanserver: 'Server', eventlog: 'Windows Event Log', winrm: 'Windows Remote Management (WS-Management)' };
  S.rt_restart_service = async function* (c) {
    const n = c.p.SERVICE_NAME, d = SVCS[n.toLowerCase()];
    yield '  Service : ' + n; if (!d) { yield ["err", "  Service '" + n + "' not found on the target. (Use \"List All Services\" to see the exact Name.)"]; yield { fail: true }; return; }
    yield '  Display : ' + d; yield '  Status before : Running'; yield '  Stopping...'; yield { sleep: 700 }; yield '  Starting...'; yield { sleep: 600 }; yield '  Status after  : Running'; yield "  Service '" + n + "' restarted";
  };
  S.rt_list_all_services = async function* (c) {
    yield '  ' + pad('Name', 24) + pad('Status', 10) + pad('StartType', 12) + 'DisplayName';
    const rows = [['AudioEndpointBuilder', 'Running', 'Automatic', 'Windows Audio Endpoint Builder'], ['BITS', 'Running', 'Manual', 'Background Intelligent Transfer Service'], ['Dnscache', 'Running', 'Automatic', 'DNS Client'], ['EventLog', 'Running', 'Automatic', 'Windows Event Log'], ['LanmanServer', 'Running', 'Automatic', 'Server'], ['MpsSvc', 'Running', 'Automatic', 'Windows Defender Firewall'], ['Spooler', 'Running', 'Automatic', 'Print Spooler'], ['W32Time', 'Running', 'Manual', 'Windows Time'], ['WSearch', 'Running', 'Automatic', 'Windows Search'], ['wuauserv', 'Running', 'Manual', 'Windows Update'], ['Fax', 'Stopped', 'Manual', 'Fax'], ['RemoteRegistry', 'Stopped', 'Disabled', 'Remote Registry']];
    for (const r of rows) { yield '  ' + pad(r[0], 24) + pad(r[1], 10) + pad(r[2], 12) + r[3]; yield { sleep: 30 }; }
    yield '  Total: 214 services, 98 running (first ' + rows.length + ' shown in this demo)';
  };
  S.rt_map_network_drive = async function* (c) {
    const p = c.p; yield '  User    : ' + p.USER_ACCOUNT; yield '  Share   : ' + p.SHARE_PATH; yield '  Drive   : ' + p.DRIVE_LETTER.toUpperCase().replace(':', '') + ':'; yield { sleep: 500 };
    yield '  Writing persistent mapping into the user\'s profile (HKU\\...\\Network\\' + p.DRIVE_LETTER.toUpperCase().replace(':', '') + ')'; if (p.REPLACE_EXISTING) yield '  Replacing any existing mapping for that letter';
    yield p.APPLY_NOW ? '  Applied now in the user\'s signed-in session -- the drive is visible immediately' : '  Saved -- the drive appears at the user\'s next sign-in';
  };
  S.rt_unmap_network_drive = async function* (c) {
    yield '  User  : ' + c.p.USER_ACCOUNT; yield '  Drive : ' + c.p.DRIVE_LETTER.toUpperCase().replace(':', '') + ':'; yield { sleep: 400 }; yield '  Mapping removed from the profile'; yield c.p.APPLY_NOW ? '  Disconnected now in the signed-in session' : '  Takes effect at next sign-in';
  };
  S.rt_list_mapped_drives = async function* (c) {
    yield '  Saved mapped drives for ' + c.p.USER_ACCOUNT + ':'; yield '  ' + pad('Drive', 7) + 'Path'; yield '  ' + pad('H:', 7) + '\\\\fileserver.' + c.T.domain + '\\home\\' + (c.p.USER_ACCOUNT.split('\\').pop()); yield '  ' + pad('S:', 7) + '\\\\fileserver.' + c.T.domain + '\\shared';
  };

  // ── ADMIN CONSOLES (all run as detached jobs that open a window on the target's screen) ──
  const CONSOLES = { rc_computer_mgmt: ['Computer Management', 'mmc.exe compmgmt.msc'], rc_device_mgr: ['Device Manager', 'mmc.exe devmgmt.msc'], rc_disk_mgmt: ['Disk Management', 'mmc.exe diskmgmt.msc'], rc_defrag_gui: ['Defragment and Optimize Drives', 'dfrgui.exe'], rc_disk_cleanup: ['Disk Cleanup', 'cleanmgr.exe'], rc_services: ['Services', 'mmc.exe services.msc'], rc_event_viewer: ['Event Viewer', 'eventvwr.msc'], rc_task_scheduler: ['Task Scheduler', 'taskschd.msc'], rc_local_users: ['Local Users and Groups', 'mmc.exe lusrmgr.msc'], rc_shared_folders: ['Shared Folders', 'mmc.exe fsmgmt.msc'], rc_firewall_adv: ['Windows Defender Firewall with Advanced Security', 'mmc.exe wf.msc'], rc_net_connections: ['Network Connections', 'control.exe ncpa.cpl'], rc_task_manager: ['Task Manager', 'taskmgr.exe'], rc_resource_monitor: ['Resource Monitor', 'resmon.exe'], rc_perfmon: ['Performance Monitor', 'perfmon.exe'], rc_sys_properties: ['System Properties', 'sysdm.cpl'], rc_programs: ['Programs and Features', 'appwiz.cpl'], rc_power_options: ['Power Options', 'powercfg.cpl'], rc_control_panel: ['Control Panel', 'control.exe'], rc_msconfig: ['System Configuration', 'msconfig.exe'], rc_cert_mgr: ['Certificates (Local Computer)', 'certlm.msc'], rc_gpedit: ['Local Group Policy Editor', 'gpedit.msc'], rc_win_update: ['Windows Update Settings', 'ms-settings:windowsupdate'], rc_powershell: ['PowerShell (Elevated)', 'powershell.exe'], rc_cmd: ['Command Prompt (Elevated)', 'cmd.exe'], rc_regedit: ['Registry Editor', 'regedit.exe'] };
  for (const id of Object.keys(CONSOLES)) {
    S[id] = async function* (c) {
      const [label, cmd] = CONSOLES[id];
      yield '  Console session user : ' + c.T.consoleUser; yield '  Launching            : ' + cmd; yield { sleep: 900 };
      yield '  OPENED on the target\'s screen as ' + c.username + '  (PID ' + ri(2000, 15000) + ')';
      yield ['dim', '  ' + label + ' is now visible to whoever sits at ' + c.T.name + ' (a real remote screen is not shown in this demo).'];
    };
  }
})();
