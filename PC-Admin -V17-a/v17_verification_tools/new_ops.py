# New (v3.7) remote-PowerShell operations shared by all editions.
# Each: id, label, category, description, danger, params(list of dicts), command(str), long(bool)
DRIVE_PARAM = {"key": "VOLUME", "kind": "drive", "label": "Drive letter", "required": True, "default": "C"}

NEW_OPS = [
 dict(id="rt_vss_resize_storage", danger=True, category="Remote Tools",
  label="Resize VSS Shadow Storage (Max Size)",
  description="vssadmin resize shadowstorage /for= /on= /maxsize= -- set the storage cap for shadow copies on a volume (shrinking may delete the oldest copies)",
  params=[dict(key="VOLUME", kind="drive", label="Volume", required=True, default="C"),
          dict(key="MAXSIZE", kind="vsssize", label="Max size (e.g. 10%, 20GB, 51200MB, UNBOUNDED)", required=True, default="10%",
               help="10% | 20GB | 51200MB | UNBOUNDED  (minimum 1MB)")],
  command=r'''
$vol = "{{VOLUME}}"
$size = "{{MAXSIZE}}"
Write-Output "  === BEFORE (volume $vol) ==="
vssadmin list shadowstorage /for=$vol 2>&1 | ForEach-Object { Write-Output "  $_" }
Write-Output ""
Write-Output "  Setting maximum shadow storage on $vol to $size ..."
$out = vssadmin resize shadowstorage /for=$vol /on=$vol /maxsize=$size 2>&1
$out | ForEach-Object { Write-Output "  $_" }
if ($LASTEXITCODE -ne 0) {
    Write-Output "  RESIZE FAILED (exit $LASTEXITCODE). Typical causes: no shadow storage association exists yet for this volume"
    Write-Output "  (create a shadow copy first), the size is below 1MB, or the volume letter is wrong."
}
Write-Output ""
Write-Output "  === AFTER ==="
vssadmin list shadowstorage /for=$vol 2>&1 | ForEach-Object { Write-Output "  $_" }
'''),
 dict(id="run_dism_restorehealth", danger=True, category="Windows Health", long=True,
  label="DISM RestoreHealth (Repair Component Store)",
  description="DISM /Online /Cleanup-Image /RestoreHealth -- repairs a corrupt component store from Windows Update; can take 10-30 min (runs detached, tool waits)",
  params=[],
  command=r'''
Write-Output "  Running DISM RestoreHealth (needs the target to reach Windows Update or a repair source)..."
DISM /Online /Cleanup-Image /RestoreHealth 2>&1 | ForEach-Object { if ($_ -and "$_".Trim()) { Write-Output "  $_" } }
Write-Output "  DISM exit code: $LASTEXITCODE  (0 = success, 3010 = success but reboot needed)"
Write-Output "  Tip: run 'Run System File Checker (SFC)' afterwards."
'''),
 dict(id="dism_component_cleanup", danger=True, category="Windows Health", long=True,
  label="DISM Component Store Cleanup (WinSxS)",
  description="DISM /AnalyzeComponentStore then /StartComponentCleanup -- reclaims space from superseded updates (optionally /ResetBase)",
  params=[dict(key="RESET_BASE", kind="bool", label="Also /ResetBase (permanent: installed updates can no longer be uninstalled)",
               required=True, default="false",
               help="Leave unchecked unless you need the extra space; ResetBase cannot be undone")],
  command=r'''
$resetBase = {{RESET_BASE}}
Write-Output "  === ANALYZE COMPONENT STORE ==="
DISM /Online /Cleanup-Image /AnalyzeComponentStore 2>&1 | ForEach-Object { if ($_ -and "$_".Trim()) { Write-Output "  $_" } }
Write-Output ""
if ($resetBase) {
    Write-Output "  === START COMPONENT CLEANUP /ResetBase ==="
    DISM /Online /Cleanup-Image /StartComponentCleanup /ResetBase 2>&1 | ForEach-Object { if ($_ -and "$_".Trim()) { Write-Output "  $_" } }
} else {
    Write-Output "  === START COMPONENT CLEANUP ==="
    DISM /Online /Cleanup-Image /StartComponentCleanup 2>&1 | ForEach-Object { if ($_ -and "$_".Trim()) { Write-Output "  $_" } }
}
Write-Output "  DISM exit code: $LASTEXITCODE"
'''),
 dict(id="perf_hardware_report_cim", danger=False, category="Performance",
  label="Hardware Inventory via CIM (WMIC Replacement)",
  description="CPU, RAM modules, disks, BIOS, GPU, board -- what 'wmic cpu/memorychip/diskdrive/bios get' used to show (WMIC is removed on Win11 24H2+)",
  params=[],
  command=r'''
Write-Output "  === CPU ==="
Get-CimInstance Win32_Processor | ForEach-Object { Write-Output "  $($_.Name.Trim())  cores=$($_.NumberOfCores) threads=$($_.NumberOfLogicalProcessors) maxMHz=$($_.MaxClockSpeed) load=$($_.LoadPercentage)%" }
Write-Output "  === MEMORY MODULES ==="
Get-CimInstance Win32_PhysicalMemory | ForEach-Object { Write-Output "  $($_.DeviceLocator): $([math]::Round($_.Capacity/1GB,1)) GB  $($_.Speed) MHz  $($_.Manufacturer)" }
$os = Get-CimInstance Win32_OperatingSystem
Write-Output "  RAM free now: $([math]::Round($os.FreePhysicalMemory/1MB,2)) GB of $([math]::Round($os.TotalVisibleMemorySize/1MB,2)) GB"
Write-Output "  === DISKS ==="
Get-CimInstance Win32_DiskDrive | ForEach-Object { Write-Output "  $($_.Model)  $([math]::Round($_.Size/1GB,0)) GB  status=$($_.Status)  iface=$($_.InterfaceType)" }
Write-Output "  === BIOS / BOARD ==="
$b = Get-CimInstance Win32_BIOS; Write-Output "  BIOS: $($b.Manufacturer) $($b.SMBIOSBIOSVersion)  serial=$($b.SerialNumber)"
$bb = Get-CimInstance Win32_BaseBoard; Write-Output "  Board: $($bb.Manufacturer) $($bb.Product)"
Write-Output "  === GPU ==="
Get-CimInstance Win32_VideoController | ForEach-Object { Write-Output "  $($_.Name)  driver=$($_.DriverVersion)" }
'''),
 dict(id="perf_trim_ssd", danger=False, category="Performance",
  label="Retrim an SSD Volume (Optimize-Volume -ReTrim)",
  description="Optimize-Volume -ReTrim -- tells the SSD which blocks are free (skips safely on HDDs)",
  params=[dict(key="VOLUME", kind="drive", label="Drive letter", required=True, default="C")],
  command=r'''
$vol = "{{VOLUME}}".TrimEnd(':')
$v = Get-Volume -DriveLetter $vol -ErrorAction SilentlyContinue
if (-not $v) { Write-Output "  Volume $vol`: not found."; return }
$part = Get-Partition -DriveLetter $vol -ErrorAction SilentlyContinue
$disk = if ($part) { Get-PhysicalDisk -ErrorAction SilentlyContinue | Where-Object { $_.DeviceId -eq $part.DiskNumber } } else { $null }
Write-Output "  Volume $vol`: media type = $(if ($disk) { $disk.MediaType } else { 'unknown' })"
if ($disk -and $disk.MediaType -eq 'HDD') { Write-Output "  This is a spinning disk -- ReTrim does not apply. Use 'Defragment' instead. Nothing done."; return }
Optimize-Volume -DriveLetter $vol -ReTrim -ErrorAction SilentlyContinue -Verbose 4>&1 | ForEach-Object { Write-Output "  $_" }
Write-Output "  Retrim finished."
'''),
 dict(id="perf_wmi_verify_repository", danger=False, category="Performance",
  label="Verify WMI Repository Health (winmgmt)",
  description="winmgmt /verifyrepository -- a corrupt WMI repository makes CIM/WMI-based operations and monitoring slow or failing (read-only check)",
  params=[],
  command=r'''
Write-Output "  Verifying the WMI repository (read-only)..."
$r = winmgmt /verifyrepository 2>&1
$r | ForEach-Object { Write-Output "  $_" }
if (($r | Out-String) -match 'inconsistent') { Write-Output "  Repository is INCONSISTENT -- consider 'winmgmt /salvagerepository' on the target (Admin), then a restart." }
'''),
 dict(id="perf_rebuild_perf_counters", danger=True, category="Performance",
  label="Rebuild Performance Counters (lodctr /R)",
  description="lodctr /R -- rebuilds a corrupt performance-counter registry (fixes empty/blank Task Manager, perfmon and monitoring-agent counters)",
  params=[],
  command=r'''
Write-Output "  Rebuilding performance counters (lodctr /R)..."
$r = lodctr /R 2>&1
$r | ForEach-Object { Write-Output "  $_" }
Write-Output "  Re-syncing with WMI performance adapter..."
winmgmt /resyncperf 2>&1 | ForEach-Object { Write-Output "  $_" }
Write-Output "  Done. Monitoring tools may need a restart to pick the counters up."
'''),
 dict(id="chkdsk_online_scan", danger=False, category="Disk", long=True,
  label="CHKDSK Online Scan (Read-Only)",
  description="chkdsk X: /scan -- online, read-only scan of a volume for file-system errors (no dismount, no repair; runs detached, tool waits)",
  params=[dict(key="VOLUME", kind="drive", label="Drive letter", required=True, default="C")],
  command=r'''
$vol = "{{VOLUME}}"
Write-Output "  Online read-only scan of $vol (this can take several minutes)..."
chkdsk $vol /scan 2>&1 | ForEach-Object { if ($_ -and "$_".Trim()) { Write-Output "  $_" } }
Write-Output "  chkdsk exit code: $LASTEXITCODE  (0 = no errors, 1 = errors found/fixed, 2/3 = cleanup needed)"
'''),
]

# Local-launch consoles (handled by the host application, never sent to the target).
# id, label, description, kind
CONSOLE_OPS = [
 ("rt_open_computer_management", "Open Computer Management (Connected to Target)",
  "mmc compmgmt.msc /computer:\\\\<target> -- Disk Management, Device Manager (read-only), Event Viewer, Services, Shared Folders, Task Scheduler in one console"),
 ("ac_open_disk_management", "Open Disk Management (Connected to Target)",
  "mmc diskmgmt.msc /computer:\\\\<target> -- partitions, volumes, drive letters, extend/shrink"),
 ("ac_open_device_manager", "Open Device Manager (Connected to Target, Read-Only on Win8+)",
  "mmc devmgmt.msc /computer:\\\\<target> -- Windows 8 / Server 2012 and later only let you VIEW remote devices; use Remote Desktop to change drivers"),
 ("ac_open_services", "Open Services Console (Connected to Target)",
  "mmc services.msc /computer:\\\\<target> -- start/stop/configure services on the target"),
 ("ac_open_event_viewer", "Open Event Viewer (Connected to Target)",
  "mmc eventvwr.msc /computer:<target> -- browse the target's Windows logs"),
 ("ac_open_shared_folders", "Open Shared Folders Console (Connected to Target)",
  "mmc fsmgmt.msc /computer:\\\\<target> -- shares, open sessions, open files"),
 ("ac_open_admin_share", "Open C$ Admin Share in File Explorer",
  "explorer \\\\<target>\\C$ -- browse the target's system drive using the supplied admin credentials"),
 ("ac_open_firewall", "Open Windows Firewall with Advanced Security (Guided)",
  "wf.msc has no remote switch -- opens the console and tells you the 3 clicks to connect it to the target"),
 ("ac_open_remote_shell", "Open Remote PowerShell Window on Target (Enter-PSSession)",
  "New PowerShell window already connected to the target -- run any admin command (cleanmgr /sagerun, defrag, netsh, ...) there"),
 ("ac_open_remote_cmd", "Open Remote Command Prompt on Target (winrs)",
  "New cmd window running on the target through WinRM (winrs) -- asks for the password in that window"),
 ("ac_open_rdp", "Open Remote Desktop to Target (Credentials Pre-Loaded)",
  "mstsc /v:<target> with the supplied credentials stored -- the only way to use GUI-only tools remotely: Device Manager (full), Disk Cleanup, Defrag, Firewall, Network Connections"),
]
