#Requires -Version 5.0
# ============================================================
#  PC Admin & Performance Tool  v3.6 -- PowerShell GUI Edition
#  (c) 2024-2026 Abdullah | All Rights Reserved
#  Contact: abuabdullah.be@outlook.com
# ============================================================
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
try { [System.Windows.Forms.Application]::EnableVisualStyles() } catch {}
try { [System.Windows.Forms.Application]::SetCompatibleTextRenderingDefault($false) } catch {}

$COPY  = "(c) 2024-2026 Abdullah  |  All Rights Reserved  |  abuabdullah.be@outlook.com"
$COPYL = "(c) 2024-2026 Abdullah  |  PC Admin & Performance Tool v3.6  |  All Rights Reserved  |  abuabdullah.be@outlook.com"
$VER   = "v3.6  PowerShell GUI Edition"
$DIR   = if ($MyInvocation.MyCommand.Path) { Split-Path $MyInvocation.MyCommand.Path } else { $PWD.Path }
$LOGD  = Join-Path $DIR "PC_Admin_Logs"
if (-not (Test-Path $LOGD)) { New-Item -ItemType Directory -Path $LOGD | Out-Null }

function HC([string]$h) { [System.Drawing.ColorTranslator]::FromHtml($h) }
$BG=HC "#111827"; $PNL=HC "#1a2438"; $CARD=HC "#1f2e47"; $CRD2=HC "#263654"
$BDR=HC "#2e4368"; $BDR2=HC "#3a5580"; $ACC=HC "#1d4ed8"
$CYAN=HC "#22d3ee"; $GRN=HC "#22c55e"; $RED=HC "#ef4444"; $YEL=HC "#f59e0b"
$TXT=HC "#d1dff0"; $TXTB=HC "#eef2ff"; $TXDD=HC "#5c7a9a"; $LOGBG=HC "#090f1a"
$HDRB=HC "#08111e"; $DIM=HC "#2d4a68"; $OUT2=HC "#8ab0cc"

$DANGER=@("flush_dns","net_reset","run_sfc","dism_check","high_perf","empty_recycle","disk_cleanup_util",
  "pr_cycle_device_by_id","pr_restart_all_adapters","pr_restart_named_adapter","pr_disable_enable_adapter",
  "pr_cycle_usb_hubs","pr_force_restart","pr_disable_hibernation","pr_force_signout_restart","pr_full_soft_recycle",
  "rt_set_static_ip","rt_set_dhcp","rt_rename_pc_domain","rt_rename_pc_workgroup","rt_rename_pc_wmic_legacy",
  "rt_vss_delete_all","rt_vss_delete_volume_all","rt_vss_delete_oldest","rt_restart_service",
  "rt_map_network_drive","rt_unmap_network_drive")
$TMAP=[ordered]@{
    "Windows Domain (NTLM) -- Recommended"="Negotiate"
    "Workgroup / Local Account (Basic)"="Basic"
    "Active Directory (Kerberos)"="Kerberos"
    "Admin Double-Hop (CredSSP)"="Credssp"
}
$CbMap=@{}; $Script:LogFile=$null; $Script:BgPS=$null; $Script:BgRS=$null
$SH=[hashtable]::Synchronized(@{
    Q=[System.Collections.Concurrent.ConcurrentQueue[hashtable]]::new()
    Stop=$false; Done=$false; Pv=0; Pm=1; Stat=""; Task=""
})

function GF([string]$n="Segoe UI",[int]$s=9,[switch]$B) {
    $style = [System.Drawing.FontStyle]::Regular
    if ($B) { $style = [System.Drawing.FontStyle]::Bold }
    New-Object System.Drawing.Font($n,$s,$style)
}
function MF {
    foreach($f in @("Cascadia Mono","Consolas","Courier New")){
        if(([System.Drawing.FontFamily]::Families|Select-Object -Expand Name) -contains $f){
            return New-Object System.Drawing.Font($f,9)
        }
    }
    return New-Object System.Drawing.Font("Courier New",9)
}

# ============================================================
# OPERATIONS (67 total)
# ============================================================
$Ops=@(
 @{Id="clear_user_temp";Cat="Cleanup";D=$false;L="Clear All Users Temp Files";Ds="Removes %TEMP% from every user profile (incl. SYSTEM/service accounts)"
   Cmd={
     $ProgressPreference="SilentlyContinue"
     $tot=0;$denied=0;$profCount=0
     $us=Get-ChildItem "C:\Users" -Directory -Force -EA SilentlyContinue
     if(-not $us){Write-Output "  WARNING: Cannot access C:\Users (insufficient rights?)"}
     else{
       Write-Output "  Found $($us.Count) user profile folder(s) under C:\Users"
       foreach($u in $us){
         if($u.Name -in @("Default","Default User","Public","All Users")){continue}
         $profCount++
         $p="$($u.FullName)\AppData\Local\Temp"
         if(Test-Path $p){
           $it=Get-ChildItem $p -Recurse -Force -EA SilentlyContinue -ErrorVariable errs
           $sz=($it|Measure-Object Length -Sum -EA SilentlyContinue).Sum;if(-not $sz){$sz=0}
           $before=$it.Count
           $it|Remove-Item -Recurse -Force -EA SilentlyContinue -ErrorVariable delErrs
           $mb=[math]::Round($sz/1MB,2);$tot+=$mb
           if($delErrs -and $delErrs.Count -gt 0){
             $denied++
             Write-Output "  [$($u.Name)] Freed $mb MB  ($($delErrs.Count) file(s) skipped -- in use / access denied)"
           } else {
             Write-Output "  [$($u.Name)] Freed $mb MB  ($before items)"
           }
         }else{
           Write-Output "  [$($u.Name)] No temp folder (profile never fully loaded)"
         }
       }
     }
     # Also clear SYSTEM and built-in service account temp -- these are real
     # profiles too and are commonly missed by "all users" cleanup tools.
     $svcProfiles=@(
       @{Name="SYSTEM";Path="C:\Windows\System32\config\systemprofile\AppData\Local\Temp"}
       @{Name="LocalService";Path="C:\Windows\ServiceProfiles\LocalService\AppData\Local\Temp"}
       @{Name="NetworkService";Path="C:\Windows\ServiceProfiles\NetworkService\AppData\Local\Temp"}
     )
     foreach($sp in $svcProfiles){
       if(Test-Path $sp.Path){
         $it=Get-ChildItem $sp.Path -Recurse -Force -EA SilentlyContinue
         $sz=($it|Measure-Object Length -Sum -EA SilentlyContinue).Sum;if(-not $sz){$sz=0}
         $it|Remove-Item -Recurse -Force -EA SilentlyContinue -ErrorVariable svcErrs
         $mb=[math]::Round($sz/1MB,2);$tot+=$mb
         $note=if($svcErrs -and $svcErrs.Count -gt 0){" ($($svcErrs.Count) file(s) skipped -- in use)"}else{""}
         Write-Output "  [$($sp.Name)] Freed $mb MB$note"
         $profCount++
       }
     }
     Write-Output "  ------------------------------------------------"
     Write-Output "  Profiles processed: $profCount   |   TOTAL FREED: $tot MB"
     if($denied -gt 0){Write-Output "  NOTE: $denied profile(s) had files in use and were partially skipped (normal for the logged-in user's active session)"}
   }
 }
 @{Id="clear_win_temp";Cat="Cleanup";D=$false;L="Clear Windows System Temp";Ds="Deletes C:\Windows\Temp"
   Cmd={
     $ProgressPreference="SilentlyContinue"
     $p="C:\Windows\Temp"
     if(Test-Path $p){
       $it=Get-ChildItem $p -Recurse -EA SilentlyContinue
       $sz=($it|Measure-Object Length -Sum -EA SilentlyContinue).Sum;if(-not $sz){$sz=0}
       $it|Remove-Item -Recurse -Force -EA SilentlyContinue
       Write-Output "  Deleted $($it.Count) items | Freed: $([math]::Round($sz/1MB,2)) MB"
     }else{
       Write-Output "  Not found: $p"
     }
   }
 }
 @{Id="clear_prefetch";Cat="Cleanup";D=$false;L="Clear Windows Prefetch Files";Ds="Removes .pf files from Prefetch"
   Cmd={
     $ProgressPreference="SilentlyContinue"
     $p="C:\Windows\Prefetch"
     if(Test-Path $p){
       $f=Get-ChildItem $p -Filter "*.pf" -EA SilentlyContinue
       $sz=($f|Measure-Object Length -Sum -EA SilentlyContinue).Sum;if(-not $sz){$sz=0}
       $f|Remove-Item -Force -EA SilentlyContinue
       Write-Output "  Removed $($f.Count) files | Freed: $([math]::Round($sz/1MB,2)) MB"
     }else{
       Write-Output "  Prefetch not found"
     }
   }
 }
 @{Id="clear_thumb";Cat="Cleanup";D=$false;L="Clear Thumbnail Cache (All Users)";Ds="Deletes thumbcache_*.db from all Explorer profiles"
   Cmd={
     $ProgressPreference="SilentlyContinue"
     $tot=0
     Get-ChildItem "C:\Users" -Directory -EA SilentlyContinue|ForEach-Object{
       $p="$($_.FullName)\AppData\Local\Microsoft\Windows\Explorer"
       if(Test-Path $p){
         $f=Get-ChildItem $p -Filter "thumbcache_*.db" -EA SilentlyContinue
         $sz=($f|Measure-Object Length -Sum -EA SilentlyContinue).Sum;if(-not $sz){$sz=0}
         $f|Remove-Item -Force -EA SilentlyContinue
         $mb=[math]::Round($sz/1MB,2);$tot+=$mb
         Write-Output "  [$($_.Name)] $($f.Count) files | $mb MB"
       }
     }
     Write-Output "  Total freed: $tot MB"
   }
 }
 @{Id="clear_wu";Cat="Cleanup";D=$false;L="Clear Windows Update Download Cache";Ds="Stops WU/BITS, clears SoftwareDistribution\Download"
   Cmd={
     $ProgressPreference="SilentlyContinue"
     Stop-Service wuauserv,bits -Force -EA SilentlyContinue;Start-Sleep 2
     $p="C:\Windows\SoftwareDistribution\Download"
     if(Test-Path $p){
       $sz=(Get-ChildItem $p -Recurse -EA SilentlyContinue|Measure-Object Length -Sum).Sum
       if(-not $sz){$sz=0};Remove-Item "$p\*" -Recurse -Force -EA SilentlyContinue
       Write-Output "  Cache cleared | Freed: $([math]::Round($sz/1MB,2)) MB"
     }
     Start-Service wuauserv,bits -EA SilentlyContinue
     Write-Output "  WU and BITS restarted"
   }
 }
 @{Id="flush_dns";Cat="Cleanup";D=$true;L="Flush DNS Resolver Cache";Ds="SAFE: Clears local DNS cache + /registerdns to preserve network"
   Cmd={
     $ProgressPreference="SilentlyContinue"
     Write-Output "  SAFE FLUSH -- local DNS cache only"
     $b=@(Get-DnsClientCache -EA SilentlyContinue).Count
     Write-Output "  Entries before: $b"
     Clear-DnsClientCache -EA SilentlyContinue
     ipconfig /flushdns 2>&1|Out-Null;ipconfig /registerdns 2>&1|Out-Null
     $a=@(Get-DnsClientCache -EA SilentlyContinue).Count
     Write-Output "  Entries after: $a"
     $gw=(Get-NetIPConfiguration -EA SilentlyContinue|Where-Object{$_.IPv4DefaultGateway}|Select-Object -First 1).IPv4DefaultGateway.NextHop
     if($gw){
       $pg=Test-NetConnection $gw -WarningAction SilentlyContinue -EA SilentlyContinue
       $gwStatus="check connectivity"
       if($pg.PingSucceeded){$gwStatus="REACHABLE"}
       Write-Output "  Gateway $gw : $gwStatus"
     }
     Write-Output "  DNS flushed safely -- domain connectivity preserved"
   }
 }
 @{Id="clear_browsers";Cat="Cleanup";D=$false;L="Clear Browser Caches (Chrome/Edge/Firefox)";Ds="Purges browser cache folders for all user profiles"
   Cmd={$ProgressPreference="SilentlyContinue"
   $brs=@{"Chrome"="\AppData\Local\Google\Chrome\User Data\Default\Cache";"Edge"="\AppData\Local\Microsoft\Edge\User Data\Default\Cache"}
   $tot=0
   Get-ChildItem "C:\Users" -Directory -EA SilentlyContinue|ForEach-Object{
     $u=$_;foreach($b in $brs.GetEnumerator()){$p="$($u.FullName)$($b.Value)"
       if(Test-Path $p){$sz=(Get-ChildItem $p -Recurse -EA SilentlyContinue|Measure-Object Length -Sum).Sum
         if(-not $sz){$sz=0};Remove-Item "$p\*" -Recurse -Force -EA SilentlyContinue
         $mb=[math]::Round($sz/1MB,2);$tot+=$mb;Write-Output "  [$($u.Name)] $($b.Key): $mb MB"}}
     $ff="$($u.FullName)\AppData\Local\Mozilla\Firefox\Profiles"
     if(Test-Path $ff){Get-ChildItem $ff -Directory -EA SilentlyContinue|ForEach-Object{
         $c2="$($_.FullName)\cache2";if(Test-Path $c2){
           $sz=(Get-ChildItem $c2 -Recurse -EA SilentlyContinue|Measure-Object Length -Sum).Sum
           if(-not $sz){$sz=0};Remove-Item "$c2\*" -Recurse -Force -EA SilentlyContinue
           $mb=[math]::Round($sz/1MB,2);$tot+=$mb;Write-Output "  [$($u.Name)] Firefox: $mb MB"}}}}
   Write-Output "  TOTAL browser cache freed: $tot MB" } }
 @{Id="clear_evtlogs";Cat="Cleanup";D=$false;L="Clear Windows Event Logs";Ds="Clears App/System/Setup -- skips Security if >100k entries"
   Cmd={$ProgressPreference="SilentlyContinue"
   foreach($log in @("Application","System","Security","Setup")){try{
     $cnt=0;try{$li=Get-WinEvent -ListLog $log -EA SilentlyContinue;if($li){$cnt=$li.RecordCount}}catch{}
     if($log -eq "Security" -and $cnt -gt 100000){
       Write-Output "  SKIPPED: $log ($cnt entries) -- too large, would hang session";continue}
     wevtutil cl "$log" 2>$null;Write-Output "  Cleared: $log ($cnt entries)"}
   catch{Write-Output "  Skipped: $log"}}}}
 @{Id="empty_recycle";Cat="Cleanup";D=$true;L="Empty Recycle Bin (All Drives)";Ds="Permanently empties Recycle Bin -- cannot be undone"
   Cmd={$ProgressPreference="SilentlyContinue"
   try{$sh2=New-Object -ComObject Shell.Application
     $cnt=($sh2.Namespace(0xA).Items()|Measure-Object).Count
     Clear-RecycleBin -Force -EA Stop;Write-Output "  Recycle Bin emptied: $cnt items"}
   catch{Write-Output "  Already empty or error: $_"}}}
 @{Id="disk_cleanup_util";Cat="Cleanup";D=$true;L="Run Disk Cleanup Utility (cleanmgr)";Ds="Runs Windows Disk Cleanup silently with all categories"
   Cmd={$ProgressPreference="SilentlyContinue"
   $base="HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\VolumeCaches";$n=0
   Get-ChildItem $base -EA SilentlyContinue|ForEach-Object{Set-ItemProperty $_.PSPath -Name StateFlags0099 -Value 2 -EA SilentlyContinue;$n++}
   Write-Output "  Configured $n categories"
   Write-Output "  Launching cleanmgr (max wait: 10 minutes)..."
   $p=Start-Process cleanmgr -ArgumentList "/sagerun:99" -WindowStyle Hidden -PassThru -EA SilentlyContinue
   if($p){
     if(-not $p.WaitForExit(600000)){
       Write-Output "  WARNING: cleanmgr did not finish within 10 minutes -- no desktop is"
       Write-Output "  attached in a remote session, so it can wait forever on a UI dialog"
       Write-Output "  nobody can see. Terminating it now."
       try{$p.Kill()}catch{}
       Get-Process cleanmgr -EA SilentlyContinue|Stop-Process -Force -EA SilentlyContinue
       Write-Output "  Disk Cleanup was terminated after timeout -- some categories may be incomplete"
     } else {
       Write-Output "  Disk Cleanup completed (exit code: $($p.ExitCode))"
     }
   } else { Write-Output "  Failed to launch cleanmgr" } } }
 @{Id="disk_report";Cat="Disk";D=$false;L="Disk Space Report (All Drives)";Ds="Shows used/free/health for all fixed drives"
   Cmd={$ProgressPreference="SilentlyContinue"
   $vols=Get-Volume -EA SilentlyContinue|Where-Object{$_.DriveType -eq "Fixed" -and $_.DriveLetter}
   if(-not $vols){Write-Output "  No fixed volumes";return}
   foreach($v in $vols){$t=[math]::Round($v.Size/1GB,2);$f=[math]::Round($v.SizeRemaining/1GB,2);$u=[math]::Round($t-$f,2)
     $pct=if($t -gt 0){"$([math]::Round(($u/$t)*100,0))%"}else{"N/A"}
     $w=if($t -gt 0 -and ($u/$t) -gt 0.9){"CRITICAL"}elseif($t -gt 0 -and ($u/$t) -gt 0.8){"LOW"}else{"OK"}
     Write-Output "  $($v.DriveLetter):  $($v.FileSystem) ${t}GB used=${u}GB free=${f}GB  $pct  [$w]"}}}
 @{Id="defrag_drives";Cat="Disk";D=$false;L="Optimize / Defragment All Fixed Drives";Ds="Defragments HDDs; TRIM on SSDs (auto-detects)"
   Cmd={$ProgressPreference="SilentlyContinue"
   $vols=Get-Volume -EA SilentlyContinue|Where-Object{$_.DriveType -eq "Fixed" -and $_.DriveLetter -and $_.FileSystem -match "NTFS|ReFS"}
   foreach($v in $vols){$dl=$v.DriveLetter;Write-Output "  Optimizing ${dl}: ..."
     Optimize-Volume -DriveLetter $dl -Verbose 4>$null -EA SilentlyContinue;Write-Output "  Drive ${dl}: complete"}}}
 @{Id="disk_health";Cat="Disk";D=$false;L="Scan Disk Health (Quick -- No Reboot)";Ds="Runs Repair-Volume scan on all drives"
   Cmd={$ProgressPreference="SilentlyContinue"
   $vols=Get-Volume -EA SilentlyContinue|Where-Object{$_.DriveType -eq "Fixed" -and $_.DriveLetter}
   foreach($v in $vols){$dl=$v.DriveLetter;Write-Output "  Scanning ${dl}: ..."
     $r=Repair-Volume -DriveLetter $dl -Scan -EA SilentlyContinue
     Write-Output "  Drive ${dl}: Scan=$r  Health=$($v.HealthStatus)"}}}
 @{Id="large_files";Cat="Disk";D=$false;L="Find Top 20 Largest Files on C:";Ds="Files >100 MB on C: sorted by size"
   Cmd={$ProgressPreference="SilentlyContinue";Write-Output "  Scanning C: ..."
   $files=Get-ChildItem "C:\" -Recurse -File -EA SilentlyContinue|Where-Object{$_.Length -gt 100MB}
   $files|Sort-Object Length -Desc|Select-Object -First 20|ForEach-Object{
     Write-Output "  $([math]::Round($_.Length/1GB,3).ToString("F3")) GB   $($_.FullName)"}
   Write-Output "  Total large files: $($files.Count)"}}
 @{Id="high_perf";Cat="Performance";D=$true;L="Set High Performance Power Plan";Ds="Activates High Performance -- increases power on laptops"
   Cmd={$ProgressPreference="SilentlyContinue"
   powercfg -setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c 2>$null
   Write-Output "  High Performance power plan activated"
   $active=powercfg -getactivescheme 2>&1
   Write-Output "  Active: $active"
   Write-Output "  NOTE: On laptops this increases heat and power usage" } }
 @{Id="visual_perf";Cat="Performance";D=$false;L="Optimize Visual Effects for Performance";Ds="Sets Best Performance mode -- disables animations"
   Cmd={$ProgressPreference="SilentlyContinue"
   $vfx="HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects"
   if(-not(Test-Path $vfx)){New-Item $vfx -Force -EA SilentlyContinue|Out-Null}
   Set-ItemProperty $vfx VisualFXSetting 2 -EA SilentlyContinue
   Set-ItemProperty "HKCU:\Control Panel\Desktop" DragFullWindows "0" -EA SilentlyContinue
   Set-ItemProperty "HKCU:\Control Panel\Desktop" MenuShowDelay "0" -EA SilentlyContinue
   $wm="HKCU:\Control Panel\Desktop\WindowMetrics"
   if(Test-Path $wm){Set-ItemProperty $wm MinAnimate "0" -EA SilentlyContinue}
   Write-Output "  Visual effects set to Best Performance -- re-login for full effect" } }
 @{Id="ram_optimize";Cat="Performance";D=$false;L="Optimize RAM / Force GC Collection";Ds="Reports RAM before/after forcing .NET garbage collection"
   Cmd={$ProgressPreference="SilentlyContinue"
   $os=Get-CimInstance Win32_OperatingSystem -EA SilentlyContinue
   if(-not $os){Write-Output "  Cannot query WMI";return}
   $tot=[math]::Round($os.TotalVisibleMemorySize/1MB,2)
   $frB=[math]::Round($os.FreePhysicalMemory/1MB,2)
   Write-Output "  RAM BEFORE: Total=${tot}GB | Used=$([math]::Round($tot-$frB,2))GB | Free=${frB}GB"
   [System.GC]::Collect();[System.GC]::WaitForPendingFinalizers();[System.GC]::Collect()
   $frA=[math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB,2)
   Write-Output "  RAM AFTER : Total=${tot}GB | Used=$([math]::Round($tot-$frA,2))GB | Free=${frA}GB"
   Write-Output "  Recovered : $([math]::Round($frA-$frB,2)) GB" } }
 @{Id="sysmain_tune";Cat="Performance";D=$false;L="Auto-Tune SysMain / Superfetch";Ds="Disables on SSD; keeps active on HDD systems"
   Cmd={$ProgressPreference="SilentlyContinue"
   $svc=Get-Service "SysMain" -EA SilentlyContinue
   $ssds=Get-PhysicalDisk -EA SilentlyContinue|Where-Object{$_.MediaType -eq "SSD"}
   if($ssds){Write-Output "  SSD detected ($($ssds.Count))"
     if($svc -and $svc.Status -eq "Running"){
       Stop-Service SysMain -Force -EA SilentlyContinue
       Set-Service SysMain -StartupType Disabled -EA SilentlyContinue
       Write-Output "  SysMain DISABLED (recommended for SSD)"}
     else{Write-Output "  SysMain already disabled"}}
   else{Write-Output "  HDD system -- keeping SysMain ACTIVE"
     if($svc -and $svc.Status -ne "Running"){
       Start-Service SysMain -EA SilentlyContinue
       Set-Service SysMain -StartupType Automatic -EA SilentlyContinue
       Write-Output "  SysMain re-enabled for HDD performance"}} } }
 @{Id="restart_search";Cat="Performance";D=$false;L="Restart Windows Search Indexer";Ds="Restarts WSearch to free CPU/disk"
   Cmd={$ProgressPreference="SilentlyContinue"
   $svc=Get-Service "WSearch" -EA SilentlyContinue
   if($svc){Stop-Service WSearch -Force -EA SilentlyContinue;Start-Sleep 2
     Start-Service WSearch -EA SilentlyContinue;Write-Output "  Windows Search indexer restarted"}
   else{Write-Output "  WSearch service not found"} } }
 @{Id="startup_report";Cat="Performance";D=$false;L="Startup Programs and Services Report";Ds="Lists all autostart entries from registry"
   Cmd={$ProgressPreference="SilentlyContinue"
   Write-Output "  === STARTUP REGISTRY ENTRIES ==="
   @("HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run","HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run","HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run")|ForEach-Object{
     if(Test-Path $_){$b=$_.Split("\")[-3]
       Get-ItemProperty $_ -EA SilentlyContinue|ForEach-Object{
         $_.PSObject.Properties|Where-Object{$_.Name -notlike "PS*"}|ForEach-Object{
           Write-Output "  [$b] $($_.Name) = $($_.Value)"}}}}
   Write-Output ""
   Write-Output "  === WIN32 STARTUP COMMANDS ==="
   Get-CimInstance Win32_StartupCommand -EA SilentlyContinue|ForEach-Object{
     Write-Output "  [$($_.User)] $($_.Name) -- $($_.Command)"}
   Write-Output ""
   Write-Output "  === NON-MICROSOFT SCHEDULED TASKS ==="
   Get-ScheduledTask -EA SilentlyContinue|Where-Object{$_.State -eq "Ready" -and $_.TaskPath -notlike "\Microsoft\*"}|
     Select-Object -First 20|ForEach-Object{Write-Output "  $($_.TaskPath)$($_.TaskName)"} } }
 @{Id="pagefile_report";Cat="Performance";D=$false;L="Virtual Memory / Page File Report";Ds="Shows page file path, usage and recommendations"
   Cmd={$ProgressPreference="SilentlyContinue"
   $sys=Get-CimInstance Win32_ComputerSystem -EA SilentlyContinue
   if(-not $sys){Write-Output "  Cannot query WMI";return}
   $ramGB=[math]::Round($sys.TotalPhysicalMemory/1GB,2)
   Write-Output "  RAM Installed   : ${ramGB} GB"
   Write-Output "  Auto-Managed PF : $($sys.AutomaticManagedPagefile)"
   Get-CimInstance Win32_PageFileUsage -EA SilentlyContinue|ForEach-Object{
     Write-Output "  File: $($_.Name) | Allocated: $($_.AllocatedBaseSize) MB | Used: $($_.CurrentUsage) MB | Peak: $($_.PeakUsage) MB"}
   Write-Output "  Recommended: $([math]::Round($ramGB*1024*1.5)) - $([math]::Round($ramGB*1024*3)) MB" } }
 @{Id="services_report";Cat="Performance";D=$false;L="Non-Essential Running Services Report";Ds="Lists third-party auto-start services"
   Cmd={$ProgressPreference="SilentlyContinue"
   Write-Output "  === THIRD-PARTY AUTO-START RUNNING SERVICES ==="
   $svcs=Get-WmiObject Win32_Service -EA SilentlyContinue|Where-Object{
     $_.State -eq "Running" -and $_.StartMode -eq "Auto" -and
     $_.PathName -notlike "*system32*" -and $_.PathName -notlike "*SysWOW64*" -and $_.PathName -notlike "*SystemRoot*"}
   if($svcs){foreach($s in $svcs){$mem="N/A"
       try{$pr2=Get-Process -Id $s.ProcessId -EA SilentlyContinue
         if($pr2){$mem="$([math]::Round($pr2.WorkingSet64/1MB,1)) MB"}}catch{}
       Write-Output "  $($s.Name.PadRight(40)) RAM: $mem"}}
   else{Write-Output "  No third-party auto-start services"} } }
 @{Id="sys_info";Cat="Windows Health";D=$false;L="Full System Information Report";Ds="CPU, RAM, OS, uptime, BIOS, domain"
   Cmd={$ProgressPreference="SilentlyContinue"
   $cs=Get-CimInstance Win32_ComputerSystem -EA SilentlyContinue
   $os=Get-CimInstance Win32_OperatingSystem -EA SilentlyContinue
   $cpu=Get-CimInstance Win32_Processor -EA SilentlyContinue|Select-Object -First 1
   $bio=Get-CimInstance Win32_BIOS -EA SilentlyContinue
   if(-not $cs){Write-Output "  Cannot query WMI";return}
   $up=(Get-Date)-$os.LastBootUpTime
   Write-Output "  Hostname     : $($cs.Name)"
   Write-Output "  Manufacturer : $($cs.Manufacturer) $($cs.Model)"
   Write-Output "  OS           : $($os.Caption) $($os.OSArchitecture)"
   Write-Output "  OS Build     : $($os.Version) (Build $($os.BuildNumber))"
   Write-Output "  CPU          : $($cpu.Name)"
   Write-Output "  CPU Cores    : $($cpu.NumberOfCores) / $($cpu.NumberOfLogicalProcessors) logical"
   Write-Output "  CPU Speed    : $($cpu.MaxClockSpeed) MHz"
   Write-Output "  RAM Total    : $([math]::Round($cs.TotalPhysicalMemory/1GB,2)) GB"
   if($bio){Write-Output "  BIOS         : $($bio.Manufacturer) v$($bio.SMBIOSBIOSVersion)"}
   Write-Output "  Last Boot    : $($os.LastBootUpTime.ToString("yyyy-MM-dd HH:mm:ss"))"
   Write-Output "  Uptime       : $($up.Days)d $($up.Hours)h $($up.Minutes)m $($up.Seconds)s"
   Write-Output "  Domain       : $($cs.Domain)"
   Write-Output "  Logged User  : $($cs.UserName)"} }
 @{Id="top_procs";Cat="Windows Health";D=$false;L="Top CPU and RAM Consuming Processes";Ds="Top 10 processes by CPU time and working set"
   Cmd={$ProgressPreference="SilentlyContinue"
   Write-Output "  === TOP 10 BY CPU ==="
   Get-Process -EA SilentlyContinue|Sort-Object CPU -Desc|Select-Object -First 10|ForEach-Object{
     $c2=if($_.CPU){[math]::Round($_.CPU,1)}else{0}
     Write-Output "  $($_.Name.PadRight(32)) $($c2.ToString().PadLeft(8)) s  $([math]::Round($_.WorkingSet64/1MB,1).ToString().PadLeft(8)) MB"}
   Write-Output ""
   Write-Output "  === TOP 10 BY RAM ==="
   Get-Process -EA SilentlyContinue|Sort-Object WorkingSet64 -Desc|Select-Object -First 10|ForEach-Object{
     Write-Output "  $($_.Name.PadRight(32)) $([math]::Round($_.WorkingSet64/1MB,1).ToString().PadLeft(8)) MB  PID:$($_.Id)"} } }
 @{Id="run_sfc";Cat="Windows Health";D=$true;L="Run SFC /scannow (System File Check)";Ds="Scans and repairs corrupted system files (5-15 min)"
   Cmd={$ProgressPreference="SilentlyContinue"
   Write-Output "  Starting SFC scan (5-15 min) ..."
   sfc /scannow 2>&1|ForEach-Object{Write-Output "  $_"}
   Write-Output "  SFC scan complete" } }
 @{Id="dism_check";Cat="Windows Health";D=$true;L="Run DISM Health Check and Scan";Ds="Checks Windows component store (5-20 min)"
   Cmd={$ProgressPreference="SilentlyContinue"
   Write-Output "  Running DISM CheckHealth..."
   DISM /Online /Cleanup-Image /CheckHealth 2>&1|ForEach-Object{Write-Output "  $_"}
   Write-Output "  Running DISM ScanHealth..."
   DISM /Online /Cleanup-Image /ScanHealth 2>&1|ForEach-Object{Write-Output "  $_"} } }
 @{Id="wu_history";Cat="Windows Health";D=$false;L="Windows Update History Report";Ds="Last 20 installed Windows updates with dates"
   Cmd={$ProgressPreference="SilentlyContinue"
   Write-Output "  === LAST 20 WINDOWS UPDATES ==="
   Get-HotFix -EA SilentlyContinue|Sort-Object InstalledOn -Desc|Select-Object -First 20|ForEach-Object{
     $d=if($_.InstalledOn){$_.InstalledOn.ToString("yyyy-MM-dd")}else{"Unknown    "}
     Write-Output "  $d  $($_.HotFixID.PadRight(15)) $($_.Description)"} } }
 @{Id="recent_errors";Cat="Windows Health";D=$false;L="Recent System and App Errors (Last 24h)";Ds="Error/warning events from System and Application logs"
   Cmd={$ProgressPreference="SilentlyContinue";$since=(Get-Date).AddHours(-24)
   Write-Output "  === SYSTEM ERRORS/WARNINGS ==="
   $e=Get-EventLog -LogName System -EntryType Error,Warning -After $since -Newest 15 -EA SilentlyContinue
   if($e){$e|ForEach-Object{Write-Output "  [$($_.TimeGenerated.ToString("HH:mm"))] [$($_.EntryType)] $($_.Source): $($_.Message.Split([char]10)[0].Trim().Substring(0,[math]::Min(100,$_.Message.Length)))"}}
   else{Write-Output "  No System errors in last 24h"}
   Write-Output ""
   Write-Output "  === APP ERRORS ==="
   $a=Get-EventLog -LogName Application -EntryType Error -After $since -Newest 15 -EA SilentlyContinue
   if($a){$a|ForEach-Object{Write-Output "  [$($_.TimeGenerated.ToString("HH:mm"))] $($_.Source): $($_.Message.Split([char]10)[0].Trim().Substring(0,[math]::Min(100,$_.Message.Length)))"}}
   else{Write-Output "  No App errors in last 24h"} } }
 @{Id="installed_sw";Cat="Windows Health";D=$false;L="Installed Software Inventory";Ds="All installed apps with version and install date"
   Cmd={$ProgressPreference="SilentlyContinue"
   $reg=@("HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*","HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*","HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*")
   $apps=$reg|ForEach-Object{Get-ItemProperty $_ -EA SilentlyContinue}|Where-Object{$_.DisplayName}|Sort-Object DisplayName
   Write-Output "  Total: $($apps.Count) applications"
   $apps|ForEach-Object{$v=if($_.DisplayVersion){$_.DisplayVersion}else{"--"}
     $d=if($_.InstallDate){$_.InstallDate}else{"Unknown"}
     Write-Output "  $($_.DisplayName.PadRight(50)) $($v.PadRight(16)) $d"} } }
 @{Id="net_ip";Cat="Network";D=$false;L="Network Adapter and IP Configuration";Ds="IP, gateway, DNS for all active adapters"
   Cmd={$ProgressPreference="SilentlyContinue"
   Write-Output "  === NETWORK ADAPTERS ==="
   $cfgs=Get-NetIPConfiguration -EA SilentlyContinue|Where-Object{$_.IPv4Address}
   if(-not $cfgs){Write-Output "  No active IPv4 adapters";return}
   foreach($c2 in $cfgs){$dns=($c2.DNSServer|Where-Object{$_.AddressFamily -eq 2}|Select-Object -ExpandProperty ServerAddresses) -join ", "
     $mac=(Get-NetAdapter -Name $c2.InterfaceAlias -EA SilentlyContinue).MacAddress
     Write-Output "  Adapter: $($c2.InterfaceAlias)"
     Write-Output "  IPv4   : $($c2.IPv4Address.IPAddress)  GW: $($c2.IPv4DefaultGateway.NextHop)"
     Write-Output "  DNS    : $dns  MAC: $mac"
     Write-Output "  ----------------------------------------------"} } }
 @{Id="net_ping";Cat="Network";D=$false;L="Test Network Connectivity (Ping Suite)";Ds="Pings gateway, DNS servers, Google, Microsoft, WU"
   Cmd={$ProgressPreference="SilentlyContinue"
   $gw=(Get-NetIPConfiguration -EA SilentlyContinue|Where-Object{$_.IPv4DefaultGateway}|Select-Object -First 1).IPv4DefaultGateway.NextHop
   $tgt=[ordered]@{"Default Gateway"=$gw;"Google DNS"="8.8.8.8";"Cloudflare"="1.1.1.1";"Google.com"="google.com";"Microsoft.com"="microsoft.com";"Windows Update"="windowsupdate.microsoft.com"}
   Write-Output "  Target                    Address                  Status    Latency"
   foreach($t in $tgt.GetEnumerator()){if(-not $t.Value){continue}
     $r=Test-NetConnection -ComputerName $t.Value -WarningAction SilentlyContinue -EA SilentlyContinue
     $ok=if($r.PingSucceeded){"PASS"}else{"FAIL"}
     $ms=if($r.PingReplyDetails){"$($r.PingReplyDetails.RoundtripTime) ms"}else{"--"}
     Write-Output "  $($t.Key.PadRight(26)) $($t.Value.PadRight(25)) $ok   $ms"} } }
 @{Id="net_stats";Cat="Network";D=$false;L="Network Adapter Speed and Traffic Stats";Ds="Link speed, status and sent/received counters"
   Cmd={$ProgressPreference="SilentlyContinue"
   $ada=Get-NetAdapter -EA SilentlyContinue|Where-Object{$_.Status -eq "Up"}
   if(-not $ada){Write-Output "  No active adapters";return}
   foreach($a in $ada){$st=$a|Get-NetAdapterStatistics -EA SilentlyContinue
     $sp=if($a.Speed){"$([math]::Round($a.Speed/1e6,0)) Mbps"}elseif($a.LinkSpeed){"$($a.LinkSpeed)"}else{"Unknown"}
     Write-Output "  $($a.Name) -- $($a.InterfaceDescription)  Speed: $sp  MAC: $($a.MacAddress)"
     if($st){Write-Output "  Sent: $([math]::Round($st.SentBytes/1MB,2)) MB ($($st.SentUnicastPackets) pkts)  Recv: $([math]::Round($st.ReceivedBytes/1MB,2)) MB ($($st.ReceivedUnicastPackets) pkts)"}
     Write-Output "  ----------------------------------------------"} } }
 @{Id="net_reset";Cat="Network";D=$true;L="Reset TCP/IP and Winsock Stack";Ds="REBOOT REQUIRED -- resets network stack -- will disconnect"
   Cmd={$ProgressPreference="SilentlyContinue"
   Write-Output "  WARNING: REBOOT REQUIRED -- network WILL be interrupted"
   netsh winsock reset 2>&1|Out-Null;Write-Output "  Winsock reset done"
   netsh int ip reset 2>&1|Out-Null;netsh int ipv6 reset 2>&1|Out-Null;Write-Output "  TCP/IP reset done"
   ipconfig /flushdns 2>&1|Out-Null;ipconfig /registerdns 2>&1|Out-Null
   ipconfig /release 2>&1|Out-Null;Start-Sleep 2;ipconfig /renew 2>&1|Out-Null
   Write-Output "  Network stack reset complete -- REBOOT REQUIRED" } }
 @{Id="dns_latency";Cat="Network";D=$false;L="DNS Resolution and Latency Test";Ds="DNS lookup time for 5 major domains"
   Cmd={$ProgressPreference="SilentlyContinue"
   Write-Output "  Domain                        IP                   Latency"
   foreach($d in @("google.com","microsoft.com","amazon.com","github.com","youtube.com")){
     $t=Measure-Command{$ip=(Resolve-DnsName $d -EA SilentlyContinue|Select-Object -First 1).IPAddress}
     Write-Output "  $($d.PadRight(30)) $($ip.PadRight(21)) $([math]::Round($t.TotalMilliseconds,1)) ms"} } }
 @{Id="firewall_status";Cat="Network";D=$false;L="Firewall and Security Status Report";Ds="Firewall profiles, AV products, listening ports"
   Cmd={$ProgressPreference="SilentlyContinue"
   Write-Output "  === WINDOWS FIREWALL ==="
   Get-NetFirewallProfile -EA SilentlyContinue|ForEach-Object{
     Write-Output "  $($_.Name): Enabled=$($_.Enabled) In=$($_.DefaultInboundAction) Out=$($_.DefaultOutboundAction)"}
   Write-Output ""
   Write-Output "  === ANTIVIRUS ==="
   $av=Get-CimInstance -Namespace root/SecurityCenter2 -ClassName AntiVirusProduct -EA SilentlyContinue
   if($av){$av|ForEach-Object{Write-Output "  $($_.displayName)"}}else{Write-Output "  None in SecurityCenter2"}
   Write-Output ""
   Write-Output "  === TOP LISTENING PORTS ==="
   netstat -an 2>$null|Select-String "LISTENING"|Select-Object -First 15|ForEach-Object{Write-Output "  $_"} } }
 @{Id="active_conn";Cat="Network";D=$false;L="Active Network Connections Report";Ds="Active TCP connections with owning process names"
   Cmd={$ProgressPreference="SilentlyContinue"
   Write-Output "  Process                    Local                      Remote                     State"
   Get-NetTCPConnection -EA SilentlyContinue|
     Where-Object{$_.State -ne "Listen" -and $_.RemoteAddress -ne "0.0.0.0" -and $_.RemoteAddress -ne "::"}|
     Select-Object -First 25|ForEach-Object{
       $proc=(Get-Process -Id $_.OwningProcess -EA SilentlyContinue).Name
       if(-not $proc){$proc="PID:$($_.OwningProcess)"}
       Write-Output "  $($proc.PadRight(27)) $("$($_.LocalAddress):$($_.LocalPort)".PadRight(27)) $("$($_.RemoteAddress):$($_.RemotePort)".PadRight(27)) $($_.State)"} } }
 # ─── POWER RECYCLE ──────────────────────────────────────────────────────
 @{Id="pr_collect_evidence";Cat="Power Recycle";D=$false;L='Collect Evidence (Pre-Recycle Snapshot)';Ds='Top CPU processes, CPU load, disk health, and last 100 System log events -- capture this BEFORE trying a fix'
   Cmd={
   $ProgressPreference="SilentlyContinue"
   Write-Output "  === TOP 20 PROCESSES BY CPU ==="
   Get-Process -EA SilentlyContinue | Sort-Object CPU -Descending | Select-Object -First 20 |
       ForEach-Object { Write-Output ("  {0,-28} PID:{1,-7} CPU:{2,10} WS:{3,8}MB" -f $_.ProcessName, $_.Id, [math]::Round($_.CPU,1), [math]::Round($_.WorkingSet64/1MB,1)) }

   Write-Output ""
   Write-Output "  === CPU LOAD (3 samples, 1s apart) ==="
   try {
       $samples = Get-Counter '\Processor(_Total)\% Processor Time' -SampleInterval 1 -MaxSamples 3 -EA Stop
       $vals = $samples.CounterSamples | ForEach-Object { [math]::Round($_.CookedValue,1) }
       $avg = ($vals | Measure-Object -Average -EA SilentlyContinue).Average
       Write-Output ("  Samples: {0}%   Average: {1}%" -f ($vals -join "%, "), [math]::Round($avg,1))
   } catch { Write-Output "  Get-Counter unavailable: $($_.Exception.Message)" }

   Write-Output ""
   Write-Output "  === PHYSICAL DISK STATUS ==="
   Get-PhysicalDisk -EA SilentlyContinue | ForEach-Object {
       Write-Output ("  {0,-24} Media:{1,-8} Health:{2,-12} Size:{3}GB" -f $_.FriendlyName, $_.MediaType, $_.HealthStatus, [math]::Round($_.Size/1GB,1))
   }

   Write-Output ""
   Write-Output "  === LAST 100 SYSTEM LOG EVENTS (summary) ==="
   $evts = Get-WinEvent -LogName System -MaxEvents 100 -EA SilentlyContinue
   if ($evts) {
       Get-WinEvent -LogName System -MaxEvents 100 -EA SilentlyContinue | Group-Object LevelDisplayName | Sort-Object Count -Descending |
           ForEach-Object { Write-Output ("  {0,-14}: {1}" -f $_.Name, $_.Count) }
       Write-Output "  --- Most recent Warning/Error/Critical entries (up to 15) ---"
       $evts | Where-Object { $_.LevelDisplayName -in @("Error","Warning","Critical") } | Select-Object -First 15 | ForEach-Object {
           $msg = ($_.Message -replace "`r`n"," ")
           if ($msg.Length -gt 110) { $msg = $msg.Substring(0,110) + "..." }
           Write-Output ("  [{0}] {1,-9} {2,-28} {3}" -f $_.TimeCreated.ToString("MM-dd HH:mm:ss"), $_.LevelDisplayName, $_.ProviderName, $msg)
       }
   } else { Write-Output "  Could not read the System event log (insufficient rights?)" }
   } }
 @{Id="pr_diagnose_driver_hang";Cat="Power Recycle";D=$false;L='Diagnose: Possible Driver Hang (Top Processes + Stuck Services)';Ds='Top 10 CPU processes plus any service stuck in a Pending state -- a common symptom of a hung driver'
   Cmd={
   $ProgressPreference="SilentlyContinue"
   Write-Output "  === TOP 10 PROCESSES BY CPU ==="
   Get-Process -EA SilentlyContinue | Sort-Object CPU -Descending | Select-Object -First 10 |
       ForEach-Object { Write-Output ("  {0,-28} PID:{1,-7} CPU:{2,10} WS:{3,8}MB" -f $_.ProcessName, $_.Id, [math]::Round($_.CPU,1), [math]::Round($_.WorkingSet64/1MB,1)) }

   Write-Output ""
   Write-Output "  === SERVICES STUCK IN A PENDING STATE ==="
   $pending = Get-Service -EA SilentlyContinue | Where-Object { $_.Status -match 'Pending' }
   if ($pending) {
       $pending | ForEach-Object { Write-Output ("  {0,-32} {1}" -f $_.Name, $_.Status) }
       Write-Output "  A pending service above may be the 'hanging driver' -- try 'Restart a Specific Service' (Remote Tools)"
       Write-Output "  or find its owning device with a 'List ... Devices' report and use 'Cycle a Device Driver' below."
   } else {
       Write-Output "  No services currently stuck in a pending state."
   }
   } }
 @{Id="pr_list_storage_devices";Cat="Power Recycle";D=$false;L='List Storage Controllers & Disk Drives';Ds='Lists DiskDrive-class and SCSI/Storage-class PnP devices with their Instance IDs'
   Cmd={
   $ProgressPreference="SilentlyContinue"
   Write-Output "  === DISK DRIVE CLASS DEVICES ==="
   Get-PnpDevice -Class DiskDrive -EA SilentlyContinue | ForEach-Object {
       Write-Output ("  [{0}] {1}" -f $_.Status, $_.FriendlyName)
       Write-Output ("      InstanceId: {0}" -f $_.InstanceId)
   }
   Write-Output ""
   Write-Output "  === SCSI / STORAGE CONTROLLER CLASS DEVICES ==="
   Get-PnpDevice -EA SilentlyContinue | Where-Object { $_.Class -match 'SCSI|Storage' } | ForEach-Object {
       Write-Output ("  [{0}] {1}  (Class: {2})" -f $_.Status, $_.FriendlyName, $_.Class)
       Write-Output ("      InstanceId: {0}" -f $_.InstanceId)
   }
   Write-Output ""
   Write-Output "  WARNING: never disable the controller hosting the boot/system volume -- it can crash the target immediately."
   Write-Output "  Copy an InstanceId above into 'Cycle a Device Driver' to disable/re-enable it."
   } }
 @{Id="pr_list_usb_devices";Cat="Power Recycle";D=$false;L='List USB Devices';Ds='Lists USB-class PnP devices with their Instance IDs'
   Cmd={
   $ProgressPreference="SilentlyContinue"
   Write-Output "  === USB CLASS DEVICES ==="
   Get-PnpDevice -Class USB -EA SilentlyContinue | ForEach-Object {
       Write-Output ("  [{0}] {1}" -f $_.Status, $_.FriendlyName)
       Write-Output ("      InstanceId: {0}" -f $_.InstanceId)
   }
   Write-Output ""
   Write-Output "  Copy an InstanceId above into 'Cycle a Device Driver' to disable/re-enable one specific USB device,"
   Write-Output "  or use 'Cycle All USB Hub Devices' to cycle every USB-matching device at once."
   } }
 @{Id="pr_cycle_device_by_id";Cat="Power Recycle";D=$true;L='Cycle a Device Driver (Disable -> Enable by Instance ID)';Ds='Disables then re-enables one PnP device by Instance ID -- get the ID from a ''List ... Devices'' report first'
   Prm=@(
     @{Key="DEVICE_ID";Kind="deviceid";Label='Device Instance ID';Req=$true;Help='Copy exactly from a ''List ... Devices'' report above'}
   )
   Cmd={
   $ProgressPreference="SilentlyContinue"
   $deviceId = "{{DEVICE_ID}}"
   $before = Get-PnpDevice -InstanceId $deviceId -EA SilentlyContinue
   if (-not $before) {
       Write-Output "  No device found with InstanceId: $deviceId"
       Write-Output "  Run one of the 'List ... Devices' reports first and copy the exact InstanceId."
       return
   }
   Write-Output "  BEFORE: $($before.FriendlyName)  [$($before.Status)]"
   Disable-PnpDevice -InstanceId $deviceId -Confirm:$false -EA SilentlyContinue
   Start-Sleep -Seconds 3
   Enable-PnpDevice -InstanceId $deviceId -Confirm:$false -EA SilentlyContinue
   Start-Sleep -Seconds 1
   $after = Get-PnpDevice -InstanceId $deviceId -EA SilentlyContinue
   Write-Output "  AFTER : $($after.FriendlyName)  [$($after.Status)]"
   if ($after.Status -eq "OK") { Write-Output "  Device cycled successfully." }
   else { Write-Output "  Device did not return to OK status -- check Device Manager before assuming it's fixed." }
   } }
 @{Id="pr_restart_all_adapters";Cat="Power Recycle";D=$true;L='Restart All Network Adapters';Ds='Restarts every network adapter -- the tool auto-reconnects if this session was using one of them'
   Cmd={
   $ProgressPreference="SilentlyContinue"
   Write-Output "  === RESTARTING ALL NETWORK ADAPTERS ==="
   Write-Output "  If this session is on the adapter being restarted you may see a short gap -- the tool auto-reconnects."
   Get-NetAdapter -EA SilentlyContinue | ForEach-Object { Write-Output "  Restarting: $($_.Name) [$($_.Status)]" }
   Get-NetAdapter -EA SilentlyContinue | Restart-NetAdapter -Confirm:$false -EA SilentlyContinue
   Start-Sleep -Seconds 3
   Write-Output "  === POST-RESTART STATUS ==="
   Get-NetAdapter -EA SilentlyContinue | ForEach-Object { Write-Output "  $($_.Name): $($_.Status)" }
   } }
 @{Id="pr_restart_named_adapter";Cat="Power Recycle";D=$true;L='Restart Network Adapter by Name';Ds='Restarts one named adapter (Restart-NetAdapter) -- the direct fix for a wedged network driver'
   Prm=@(
     @{Key="ADAPTER";Kind="adaptername";Label='Adapter Name';Req=$true;Def='Ethernet'}
   )
   Cmd={
   $ProgressPreference="SilentlyContinue"
   $adapterName = "{{ADAPTER}}"
   $nic = Get-NetAdapter -Name $adapterName -EA SilentlyContinue
   if (-not $nic) {
       Write-Output "  Adapter '$adapterName' not found. Available adapters:"
       Get-NetAdapter -EA SilentlyContinue | ForEach-Object { Write-Output "    $($_.Name)  [$($_.Status)]" }
       return
   }
   Write-Output "  BEFORE: $($nic.Name) = $($nic.Status)"
   Restart-NetAdapter -Name $adapterName -Confirm:$false -EA SilentlyContinue
   Start-Sleep -Seconds 3
   $nic2 = Get-NetAdapter -Name $adapterName -EA SilentlyContinue
   Write-Output "  AFTER : $($nic2.Name) = $($nic2.Status)"
   } }
 @{Id="pr_disable_enable_adapter";Cat="Power Recycle";D=$true;L='Disable then Enable a Network Adapter';Ds='Full Disable-NetAdapter / Enable-NetAdapter cycle -- more thorough than a restart for a stuck driver'
   Prm=@(
     @{Key="ADAPTER";Kind="adaptername";Label='Adapter Name';Req=$true;Def='Ethernet'}
   )
   Cmd={
   $ProgressPreference="SilentlyContinue"
   $adapterName = "{{ADAPTER}}"
   $nic = Get-NetAdapter -Name $adapterName -EA SilentlyContinue
   if (-not $nic) {
       Write-Output "  Adapter '$adapterName' not found. Available adapters:"
       Get-NetAdapter -EA SilentlyContinue | ForEach-Object { Write-Output "    $($_.Name)  [$($_.Status)]" }
       return
   }
   Write-Output "  BEFORE: $($nic.Name) = $($nic.Status)"
   Disable-NetAdapter -Name $adapterName -Confirm:$false -EA SilentlyContinue
   Start-Sleep -Seconds 3
   Enable-NetAdapter -Name $adapterName -Confirm:$false -EA SilentlyContinue
   Start-Sleep -Seconds 2
   $nic2 = Get-NetAdapter -Name $adapterName -EA SilentlyContinue
   Write-Output "  AFTER : $($nic2.Name) = $($nic2.Status)"
   } }
 @{Id="pr_cycle_usb_hubs";Cat="Power Recycle";D=$true;L='Cycle All USB Hub Devices';Ds='Disables then re-enables every PnP device whose name matches USB -- fixes a USB device causing interrupts'
   Cmd={
   $ProgressPreference="SilentlyContinue"
   Write-Output "  === CYCLING ALL USB-MATCHING PNP DEVICES ==="
   $usbDevices = Get-PnpDevice -EA SilentlyContinue | Where-Object { $_.FriendlyName -match "USB" }
   if (-not $usbDevices) { Write-Output "  No USB-matching PnP devices found."; return }
   $count = 0
   foreach ($dev in $usbDevices) {
       Write-Output "  Cycling: $($dev.FriendlyName)"
       Disable-PnpDevice -InstanceId $dev.InstanceId -Confirm:$false -EA SilentlyContinue
       Start-Sleep -Seconds 2
       Enable-PnpDevice -InstanceId $dev.InstanceId -Confirm:$false -EA SilentlyContinue
       $count++
   }
   Write-Output "  Cycled $count USB device(s)."
   } }
 @{Id="pr_firmware_info";Cat="Power Recycle";D=$false;L='Firmware / BIOS Version Report';Ds='BIOS/firmware version and system model -- read-only, useful when suspecting a firmware bug'
   Cmd={
   $ProgressPreference="SilentlyContinue"
   Write-Output "  === FIRMWARE / BIOS INFO (Get-ComputerInfo can take a few seconds) ==="
   $info = Get-ComputerInfo -EA SilentlyContinue
   if ($info) {
       Write-Output "  BIOS Version      : $($info.BiosVersion -join ', ')"
       Write-Output "  BIOS Manufacturer : $($info.BiosManufacturer)"
       Write-Output "  BIOS Release Date : $($info.BiosReleaseDate)"
       Write-Output "  Firmware Type     : $($info.BiosFirmwareType)"
       Write-Output "  System Model      : $($info.CsManufacturer) $($info.CsModel)"
   } else {
       Write-Output "  Get-ComputerInfo failed -- falling back to Win32_BIOS"
       Get-CimInstance Win32_BIOS -EA SilentlyContinue | ForEach-Object {
           Write-Output "  BIOS Version: $($_.SMBIOSBIOSVersion)  Manufacturer: $($_.Manufacturer)  ReleaseDate: $($_.ReleaseDate)"
       }
   }
   } }
 @{Id="pr_force_restart";Cat="Power Recycle";D=$true;L='Force Restart Now (Unsaved Work Will Be Lost)';Ds='Restart-Computer -Force -- the firmware-bug workaround and the last resort before a real power cycle'
   Cmd={
   $ProgressPreference="SilentlyContinue"
   Write-Output "  Forcing an immediate restart -- any unsaved work on the target WILL be lost."
   Write-Output "  The connection will drop now; this is expected."
   Restart-Computer -Force
   } }
 @{Id="pr_wake_armed_devices";Cat="Power Recycle";D=$false;L='List Devices Armed to Wake the System';Ds='powercfg /devicequery wake_armed (+ wake_programmable) -- diagnoses devices not waking correctly from sleep'
   Cmd={
   $ProgressPreference="SilentlyContinue"
   Write-Output "  === DEVICES CURRENTLY ARMED TO WAKE THIS SYSTEM ==="
   powercfg /devicequery wake_armed | ForEach-Object { Write-Output "  $_" }
   Write-Output ""
   Write-Output "  === DEVICES THAT CAN BE PROGRAMMED TO WAKE THIS SYSTEM ==="
   powercfg /devicequery wake_programmable | ForEach-Object { Write-Output "  $_" }
   } }
 @{Id="pr_disable_hibernation";Cat="Power Recycle";D=$true;L='Disable Hibernation';Ds='powercfg /h off -- removes hiberfil.sys and Fast Startup/S4 hybrid-sleep behavior'
   Cmd={
   $ProgressPreference="SilentlyContinue"
   Write-Output "  Disabling hibernation (also removes hiberfil.sys and Fast Startup/hybrid-sleep behavior)..."
   powercfg /h off
   Write-Output "  Verifying available sleep states..."
   powercfg /a | ForEach-Object { Write-Output "  $_" }
   } }
 @{Id="pr_force_signout_restart";Cat="Power Recycle";D=$true;L='Force Sign-out & Restart (shutdown /g)';Ds='shutdown /g /f /t 0 -- restarts and reopens registered apps, distinct from a plain restart'
   Cmd={
   $ProgressPreference="SilentlyContinue"
   Write-Output "  Signing out and restarting now (shutdown /g) -- Windows will try to reopen registered apps on next login."
   Write-Output "  Any unsaved work WILL be lost. The connection will drop now; this is expected."
   shutdown /g /f /t 0
   } }
 @{Id="pr_full_soft_recycle";Cat="Power Recycle";D=$true;L='Full Soft-Recycle Bundle (Network + USB Cycle, Restart Optional)';Ds='LAST RESORT before a real power cycle: restarts every adapter, cycles every USB device, then restarts Windows unless Auto-Restart is unchecked'
   Prm=@(
     @{Key="AUTO_RESTART";Kind="bool";Label='Automatically restart when done';Req=$true;Def='true';Help='Unchecked: cycle network + USB only, skip the restart'}
   )
   Cmd={
   $ProgressPreference="SilentlyContinue"
   $autoRestart = {{AUTO_RESTART}}
   Write-Output "  === FULL SOFT-RECYCLE: NETWORK + USB CYCLE + RESTART ==="
   Write-Output "  This is the closest software-only equivalent to a physical power recycle."
   Write-Output ""
   Write-Output "  [1/3] Restarting network adapters..."
   Get-NetAdapter -EA SilentlyContinue | Restart-NetAdapter -Confirm:$false -EA SilentlyContinue

   Write-Output "  [2/3] Cycling USB-matching devices..."
   Get-PnpDevice -EA SilentlyContinue | Where-Object { $_.FriendlyName -match "USB" } | ForEach-Object {
       Disable-PnpDevice -InstanceId $_.InstanceId -Confirm:$false -EA SilentlyContinue
       Start-Sleep -Seconds 2
       Enable-PnpDevice -InstanceId $_.InstanceId -Confirm:$false -EA SilentlyContinue
   }

   if ($autoRestart) {
       Write-Output "  [3/3] Restarting the computer now (shutdown /g)..."
       shutdown /g /f /t 0
   } else {
       Write-Output "  [3/3] Auto-Restart is OFF -- network + USB cycle complete, restart skipped."
       Write-Output "  Run 'Force Restart Now' or 'Force Sign-out & Restart' (Power Recycle) manually when ready."
   }
   } }
 # ─── REMOTE TOOLS ───────────────────────────────────────────────────────
 @{Id="rt_set_static_ip";Cat="Remote Tools";D=$true;L='Set Static IP Address';Ds='netsh interface ipv4 set address ... static -- optionally sets primary/secondary DNS too'
   Prm=@(
     @{Key="ADAPTER";Kind="adaptername";Label='Adapter Name';Req=$true;Def='Ethernet'},
     @{Key="IP";Kind="ipv4";Label='IP Address';Req=$true;Help='e.g. 192.168.1.100'},
     @{Key="MASK";Kind="subnetmask";Label='Subnet Mask (or CIDR, e.g. 24)';Req=$true;Def='255.255.255.0'},
     @{Key="GATEWAY";Kind="ipv4";Label='Default Gateway';Req=$true;Help='e.g. 192.168.1.1'},
     @{Key="DNS1";Kind="ipv4";Label='Primary DNS (optional)';Req=$false},
     @{Key="DNS2";Kind="ipv4";Label='Secondary DNS (optional)';Req=$false}
   )
   Cmd={
   $ProgressPreference="SilentlyContinue"
   $adapterName = "{{ADAPTER}}"
   $ip = "{{IP}}"
   $mask = "{{MASK}}"
   $gw = "{{GATEWAY}}"
   $dns1 = "{{DNS1}}"
   $dns2 = "{{DNS2}}"

   $nic = Get-NetAdapter -Name $adapterName -EA SilentlyContinue
   if (-not $nic) {
       Write-Output "  Adapter '$adapterName' not found. Available adapters:"
       Get-NetAdapter -EA SilentlyContinue | ForEach-Object { Write-Output "    $($_.Name)" }
       return
   }

   Write-Output "  Setting static IP on '$adapterName': $ip / $mask, gateway $gw"
   netsh interface ipv4 set address name="$adapterName" static $ip $mask $gw 2>&1 | ForEach-Object { Write-Output "  $_" }

   if ($dns1) {
       Write-Output "  Setting primary DNS: $dns1"
       netsh interface ipv4 set dns name="$adapterName" static $dns1 primary 2>&1 | ForEach-Object { Write-Output "  $_" }
   }
   if ($dns2) {
       Write-Output "  Adding secondary DNS: $dns2"
       netsh interface ipv4 add dns name="$adapterName" $dns2 index=2 2>&1 | ForEach-Object { Write-Output "  $_" }
   }

   Start-Sleep -Seconds 2
   Write-Output "  === RESULTING CONFIGURATION ==="
   Get-NetIPConfiguration -InterfaceAlias $adapterName -EA SilentlyContinue | ForEach-Object {
       Write-Output "  IPv4 Address : $($_.IPv4Address.IPAddress)"
       Write-Output "  Gateway      : $($_.IPv4DefaultGateway.NextHop)"
       Write-Output "  DNS Servers  : $($_.DNSServer.ServerAddresses -join ', ')"
   }
   } }
 @{Id="rt_set_dhcp";Cat="Remote Tools";D=$true;L='Set Adapter to DHCP (Automatic)';Ds='Reverts a static adapter back to DHCP for both address and DNS, then renews the lease'
   Prm=@(
     @{Key="ADAPTER";Kind="adaptername";Label='Adapter Name';Req=$true;Def='Ethernet'}
   )
   Cmd={
   $ProgressPreference="SilentlyContinue"
   $adapterName = "{{ADAPTER}}"
   $nic = Get-NetAdapter -Name $adapterName -EA SilentlyContinue
   if (-not $nic) {
       Write-Output "  Adapter '$adapterName' not found. Available adapters:"
       Get-NetAdapter -EA SilentlyContinue | ForEach-Object { Write-Output "    $($_.Name)" }
       return
   }
   Write-Output "  Switching '$adapterName' to DHCP..."
   netsh interface ipv4 set address name="$adapterName" source=dhcp 2>&1 | ForEach-Object { Write-Output "  $_" }
   netsh interface ipv4 set dnsservers name="$adapterName" source=dhcp 2>&1 | ForEach-Object { Write-Output "  $_" }
   ipconfig /renew "$adapterName" | Out-Null
   Start-Sleep -Seconds 2
   Write-Output "  === RESULTING CONFIGURATION ==="
   Get-NetIPConfiguration -InterfaceAlias $adapterName -EA SilentlyContinue | ForEach-Object {
       Write-Output "  IPv4 Address : $($_.IPv4Address.IPAddress)"
       Write-Output "  Gateway      : $($_.IPv4DefaultGateway.NextHop)"
       Write-Output "  DNS Servers  : $($_.DNSServer.ServerAddresses -join ', ')"
   }
   } }
 @{Id="rt_rename_pc_domain";Cat="Remote Tools";D=$true;L='Rename Computer (Domain-Joined)';Ds='Rename-Computer using this session''s own credentials -- restart is optional; use CredSSP transport if it fails (double-hop)'
   Prm=@(
     @{Key="NEW_NAME";Kind="computername";Label='New Computer Name';Req=$true},
     @{Key="AUTO_RESTART";Kind="bool";Label='Automatically restart when done';Req=$true;Def='true';Help='Unchecked: rename now, restart later yourself'}
   )
   Cmd={
   $ProgressPreference="SilentlyContinue"
   $newName = "{{NEW_NAME}}"
   $autoRestart = {{AUTO_RESTART}}
   Write-Output "  Current name: $env:COMPUTERNAME"
   Write-Output "  Renaming to : $newName  (domain-joined, using this session's own credentials)"
   Write-Output "  NOTE: if this fails with an RPC/access or 'second logon' style error, reconnect with"
   Write-Output "  Auth Transport = 'Admin Double-Hop (CredSSP)' -- domain rename over WinRM is a classic"
   Write-Output "  double-hop scenario that plain NTLM cannot always complete."
   try {
       if ($autoRestart) {
           Rename-Computer -NewName $newName -Force -Restart -EA Stop
           Write-Output "  Rename submitted -- the target is restarting now."
       } else {
           Rename-Computer -NewName $newName -Force -EA Stop
           Write-Output "  Rename submitted -- Auto-Restart is OFF. The new name will NOT take effect until"
           Write-Output "  this computer restarts -- run 'Force Restart Now' (Power Recycle) when ready."
       }
   } catch {
       Write-Output "  Rename FAILED: $($_.Exception.Message)"
       Write-Output "  Most common cause: NTLM double-hop restriction. Retry with CredSSP or Kerberos-with-delegation."
   }
   } }
 @{Id="rt_rename_pc_workgroup";Cat="Remote Tools";D=$true;L='Rename Computer (Workgroup/Local)';Ds='Rename-Computer with no domain credential -- restart is optional; for non-domain-joined targets'
   Prm=@(
     @{Key="NEW_NAME";Kind="computername";Label='New Computer Name';Req=$true},
     @{Key="AUTO_RESTART";Kind="bool";Label='Automatically restart when done';Req=$true;Def='true';Help='Unchecked: rename now, restart later yourself'}
   )
   Cmd={
   $ProgressPreference="SilentlyContinue"
   $newName = "{{NEW_NAME}}"
   $autoRestart = {{AUTO_RESTART}}
   Write-Output "  Current name: $env:COMPUTERNAME"
   Write-Output "  Renaming to : $newName  (workgroup/local -- no domain credential involved)"
   try {
       if ($autoRestart) {
           Rename-Computer -NewName $newName -Force -Restart -EA Stop
           Write-Output "  Rename submitted -- the target is restarting now."
       } else {
           Rename-Computer -NewName $newName -Force -EA Stop
           Write-Output "  Rename submitted -- Auto-Restart is OFF. The new name will NOT take effect until"
           Write-Output "  this computer restarts -- run 'Force Restart Now' (Power Recycle) when ready."
       }
   } catch {
       Write-Output "  Rename FAILED: $($_.Exception.Message)"
   }
   } }
 @{Id="rt_rename_pc_wmic_legacy";Cat="Remote Tools";D=$true;L='Rename Computer via WMIC (Legacy -- Manual Restart Required)';Ds='wmic computersystem ... call rename -- for old targets only; WMIC is removed on Windows 11 24H2+'
   Prm=@(
     @{Key="NEW_NAME";Kind="computername";Label='New Computer Name';Req=$true}
   )
   Cmd={
   $ProgressPreference="SilentlyContinue"
   $newName = "{{NEW_NAME}}"
   Write-Output "  WARNING: WMIC is deprecated and removed by default on Windows 11 24H2+ / recent Server builds."
   Write-Output "  Prefer 'Rename Computer (Domain-Joined)' or 'Rename Computer (Workgroup/Local)' on modern targets."
   $wmicPath = Get-Command wmic.exe -EA SilentlyContinue
   if (-not $wmicPath) {
       Write-Output "  wmic.exe was not found on this target -- it has been removed. Use the Rename-Computer operations instead."
       return
   }
   $result = wmic computersystem where "name='$env:COMPUTERNAME'" call rename name="$newName" 2>&1
   $result | ForEach-Object { Write-Output "  $_" }
   Write-Output "  Rename submitted via WMIC -- this does NOT auto-restart. Run 'Force Restart Now' (Power Recycle) when ready."
   } }
 @{Id="rt_vss_view";Cat="Remote Tools";D=$false;L='VSS Shadow Copy Storage Report';Ds='vssadmin list shadowstorage + list shadows -- size/usage per volume and every shadow copy instance'
   Cmd={
   $ProgressPreference="SilentlyContinue"
   Write-Output "  === VSS SHADOW STORAGE (size/usage per volume) ==="
   vssadmin list shadowstorage 2>&1 | ForEach-Object { Write-Output "  $_" }
   Write-Output ""
   Write-Output "  === VSS SHADOW COPIES (instances) ==="
   vssadmin list shadows 2>&1 | ForEach-Object { Write-Output "  $_" }
   } }
 @{Id="rt_vss_delete_all";Cat="Remote Tools";D=$true;L='Delete ALL VSS Shadow Copies (Every Volume)';Ds='vssadmin delete shadows /all /quiet -- IRREVERSIBLE, removes every restore point on every volume'
   Cmd={
   $ProgressPreference="SilentlyContinue"
   Write-Output "  Deleting ALL VSS shadow copies on ALL volumes -- IRREVERSIBLE, removes every System Restore /"
   Write-Output "  previous-versions recovery point on this machine."
   vssadmin delete shadows /all /quiet 2>&1 | ForEach-Object { Write-Output "  $_" }
   Write-Output "  Done."
   } }
 @{Id="rt_vss_delete_volume_all";Cat="Remote Tools";D=$true;L='Delete ALL VSS Shadow Copies for One Volume';Ds='vssadmin delete shadows /for=<volume> /all /quiet -- IRREVERSIBLE for that volume only'
   Prm=@(
     @{Key="VOLUME";Kind="drive";Label='Volume (drive letter)';Req=$true;Def='C'}
   )
   Cmd={
   $ProgressPreference="SilentlyContinue"
   $vol = "{{VOLUME}}"
   Write-Output "  Deleting ALL VSS shadow copies on volume $vol -- IRREVERSIBLE for that volume."
   vssadmin delete shadows /for=$vol /all /quiet 2>&1 | ForEach-Object { Write-Output "  $_" }
   Write-Output "  Done."
   } }
 @{Id="rt_vss_delete_oldest";Cat="Remote Tools";D=$true;L='Delete Oldest VSS Shadow Copy (One Volume, or Every Volume if Blank)';Ds='vssadmin delete shadows /for=<volume> /oldest /quiet -- loops every fixed volume if left blank'
   Prm=@(
     @{Key="VOLUME";Kind="drive";Label='Volume (blank = every fixed volume''s oldest)';Req=$false}
   )
   Cmd={
   $ProgressPreference="SilentlyContinue"
   $vol = "{{VOLUME}}"
   if ([string]::IsNullOrWhiteSpace($vol)) {
       Write-Output "  No volume specified -- deleting the oldest shadow copy on every fixed volume that has one."
       Get-Volume -EA SilentlyContinue | Where-Object { $_.DriveLetter } | ForEach-Object {
           $d = "$($_.DriveLetter):"
           Write-Output "  --- $d ---"
           vssadmin delete shadows /for=$d /oldest /quiet 2>&1 | ForEach-Object { Write-Output "    $_" }
       }
   } else {
       Write-Output "  Deleting the oldest VSS shadow copy on volume $vol"
       vssadmin delete shadows /for=$vol /oldest /quiet 2>&1 | ForEach-Object { Write-Output "  $_" }
   }
   } }
 @{Id="rt_run_scheduled_task_query";Cat="Remote Tools";D=$false;L='Query Scheduled Task Details';Ds='Full details + last-run info for a named scheduled task, with a fuzzy-match fallback'
   Prm=@(
     @{Key="TASK_NAME";Kind="taskname";Label='Task Name';Req=$true;Help='Exact name, or partial text to search'}
   )
   Cmd={
   $ProgressPreference="SilentlyContinue"
   $tn = "{{TASK_NAME}}"
   $tasks = Get-ScheduledTask -EA SilentlyContinue | Where-Object { $_.TaskName -eq $tn }
   if (-not $tasks) {
       Write-Output "  No exact match for '$tn'. Closest matches:"
       Get-ScheduledTask -EA SilentlyContinue | Where-Object { $_.TaskName -like "*$tn*" } | Select-Object -First 15 |
           ForEach-Object { Write-Output "    $($_.TaskPath)$($_.TaskName)" }
   } else {
       foreach ($t in $tasks) {
           Write-Output "  === $($t.TaskPath)$($t.TaskName) ==="
           $t | Format-List * | Out-String | Write-Output
           Get-ScheduledTaskInfo -TaskName $t.TaskName -TaskPath $t.TaskPath -EA SilentlyContinue | Format-List * | Out-String | Write-Output
       }
   }
   } }
 @{Id="rt_open_computer_management";Cat="Remote Tools";D=$false;L='Open Computer Management (Connected to Target)';Ds='Launches mmc.exe compmgmt.msc /computer:\\<target> locally on the machine running this edition, connected to the target'
   Cmd={
   $ProgressPreference="SilentlyContinue"
   # Handled specially by the host application -- never actually sent to the remote target.
   # Desktop editions (PowerShell / Python GUI) launch locally:
   #   mmc.exe compmgmt.msc /computer:\\<target>
   # The Web edition returns that command as text instead of executing anything,
   # since a server cannot open a window on your screen.
   Write-Output "  (informational placeholder -- see description)"
   } }
 @{Id="rt_restart_service";Cat="Remote Tools";D=$true;L='Restart a Specific Service';Ds='Restart-Service -Force by exact service Name, reporting status before and after'
   Prm=@(
     @{Key="SERVICE_NAME";Kind="servicename";Label='Service Name (not Display Name)';Req=$true;Help='Copy it exactly from ''List All Services'' -- spaces are fine'}
   )
   Cmd={
$svcName = '{{SERVICE_NAME}}'
$svc = Get-Service -Name $svcName -ErrorAction SilentlyContinue
if (-not $svc) {
    Write-Output "  Service '$svcName' not found. Use 'List All Services' to find the exact Name (not DisplayName)."
    $byDisp = @(Get-Service -DisplayName $svcName -ErrorAction SilentlyContinue)
    if ($byDisp.Count -gt 0) {
        Write-Output "  Note: that text is the DISPLAY name of the service whose Name is '$($byDisp[0].Name)' -- run this again with that Name."
    }
    return
}
Write-Output "  BEFORE: $($svc.Name) [$($svc.DisplayName)] = $($svc.Status)  (StartType: $($svc.StartType))"
Restart-Service -Name $svcName -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
$svc2 = Get-Service -Name $svcName -ErrorAction SilentlyContinue
Write-Output "  AFTER : $($svc2.Name) [$($svc2.DisplayName)] = $($svc2.Status)"
if ($svc2.Status -ne "Running" -and $svc.StartType -ne "Disabled") {
    Write-Output "  WARNING: service is not Running after restart -- check its dependencies or the System event log."
}
   } }
 @{Id="rt_list_all_services";Cat="Remote Tools";D=$false;L='List All Services (Name, Status, Start Type)';Ds='Full raw Get-Service inventory -- every service, not just non-essential/third-party ones'
   Cmd={
$svcs = @(Get-Service -ErrorAction SilentlyContinue | Sort-Object Status, Name)
$w = 20
foreach ($s in $svcs) { if ($s.Name.Length -gt $w) { $w = $s.Name.Length } }
Write-Output "  === ALL SERVICES (Name | Status | StartType) ==="
Write-Output ("  {0,-$w} {1,-10} {2}" -f 'Name', 'Status', 'StartType')
foreach ($s in $svcs) {
    Write-Output ("  {0,-$w} {1,-10} {2}" -f $s.Name, $s.Status, $s.StartType)
}
$total = $svcs.Count
$running = @($svcs | Where-Object Status -eq 'Running').Count
Write-Output ""
Write-Output "  Total: $total services -- $running running"
   } }
 @{Id="rt_map_network_drive";Cat="Remote Tools";D=$true;L='Map Network Drive for a User (Shared Folder -> Drive Letter)';Ds='Maps a shared folder to a drive letter for ONE user account on the target -- saved in that user''s profile (reconnects at every sign-in) and connected live too if they are signed in'
   Prm=@(
     @{Key="SHARE_PATH";Kind="uncpath";Label='Shared Folder Path (UNC)';Req=$true;Help='\\fileserver\share   (a subfolder works too: \\fileserver\share\dept)'},
     @{Key="DRIVE_LETTER";Kind="mapdrive";Label='Drive Letter';Req=$true;Def='Z';Help='D to Z -- must not be a local disk on the target'},
     @{Key="USER_ACCOUNT";Kind="useraccount";Label='Map It For This User Account';Req=$true;Help='DOMAIN\jsmith   or   jsmith@corp.local   or   .\localuser'},
     @{Key="APPLY_NOW";Kind="bool";Label='Also connect it right now if that user is signed in';Req=$true;Def='true';Help='Unchecked: only saved -- the drive appears at the user''s next sign-in'},
     @{Key="REPLACE_EXISTING";Kind="bool";Label='Replace an existing mapping on this drive letter';Req=$true;Def='false';Help='Unchecked: stop if that letter already points at a different share'}
   )
   Cmd={
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
function Invoke-Reg([string[]]$RegArgs) {
    # reg.exe wrapper: stderr is merged into text so it can never leak into the error stream
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $o = (& "$env:SystemRoot\System32\reg.exe" @RegArgs 2>&1 | ForEach-Object { "$_" }) -join ' '
        $c = $LASTEXITCODE
    } finally { $ErrorActionPreference = $prev }
    return @{ Code = $c; Out = "$o".Trim() }
}
function Resolve-TargetUser([string]$Account) {
    # DOMAIN\user, user@domain, .\localuser or a bare name -> SID + canonical DOMAIN\user
    $a = $Account.Trim()
    if ($a -match '^\.\\') { $a = "$env:COMPUTERNAME\" + $a.Substring(2) }
    try {
        $sid = (New-Object System.Security.Principal.NTAccount($a)).Translate([System.Security.Principal.SecurityIdentifier])
        $name = $sid.Translate([System.Security.Principal.NTAccount]).Value
    } catch {
        throw "Windows on the target cannot find the account '$Account'. Use DOMAIN\username for a domain user, or .\username for a local user."
    }
    return @{ Sid = $sid.Value; Name = $name }
}
function Get-UserProfilePath([string]$Sid) {
    $k = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList\$Sid"
    if (Test-Path -LiteralPath $k) { return [string](Get-ItemProperty -LiteralPath $k).ProfileImagePath }
    return $null
}
function Open-UserHive([string]$Sid, [string]$ProfilePath) {
    # Already loaded (user signed in / process running as user) -> use it. Otherwise load NTUSER.DAT temporarily.
    if ([Microsoft.Win32.Registry]::Users.GetSubKeyNames() -contains $Sid) { return @{ Name = $Sid; Temp = $false } }
    if (-not $ProfilePath) { throw 'That account has no profile on the target (it has never signed in there), so there is nothing to map into yet.' }
    $dat = Join-Path $ProfilePath 'NTUSER.DAT'
    if (-not [System.IO.File]::Exists($dat)) { throw "NTUSER.DAT was not found at $dat" }
    $tmp = 'PCAdminTmp_' + [guid]::NewGuid().ToString('N').Substring(0, 8)
    $r = Invoke-Reg @('load', "HKU\$tmp", $dat)
    if ($r.Code -ne 0) { throw "Could not load the user's registry hive (the user may be signing in right now): $($r.Out)" }
    return @{ Name = $tmp; Temp = $true }
}
function Close-UserHive($Hive) {
    if (-not $Hive -or -not $Hive.Temp) { return }
    [gc]::Collect(); [gc]::WaitForPendingFinalizers()
    $r = $null
    for ($i = 0; $i -lt 8; $i++) {
        $r = Invoke-Reg @('unload', "HKU\$($Hive.Name)")
        if ($r.Code -eq 0) { return }
        Start-Sleep -Milliseconds 500
        [gc]::Collect()
    }
    Write-Output "  WARNING: the temporary registry hive HKU\$($Hive.Name) could not be unloaded: $($r.Out)"
}
function Get-NetDriveKeys($Hive) {
    # Persistent mapped drives live in HKU\<SID>\Network\<letter>
    $found = @()
    $nk = [Microsoft.Win32.Registry]::Users.OpenSubKey("$($Hive.Name)\Network")
    if ($nk) {
        try {
            foreach ($n in $nk.GetSubKeyNames()) {
                $k = $nk.OpenSubKey($n)
                if ($k) {
                    try {
                        $found += New-Object PSObject -Property @{
                            Letter     = $n.ToUpper()
                            RemotePath = [string]$k.GetValue('RemotePath')
                            UserName   = [string]$k.GetValue('UserName')
                        }
                    } finally { $k.Close() }
                }
            }
        } finally { $nk.Close() }
    }
    return $found
}
function Set-NetDriveKey($Hive, [string]$Letter, [string]$Share) {
    # The exact value set Windows itself writes for a persistent mapping (read back at sign-in)
    $key = [Microsoft.Win32.Registry]::Users.CreateSubKey("$($Hive.Name)\Network\$Letter")
    try {
        $key.SetValue('RemotePath', $Share, [Microsoft.Win32.RegistryValueKind]::String)
        $key.SetValue('UserName', '0', [Microsoft.Win32.RegistryValueKind]::String)
        $key.SetValue('ProviderName', 'Microsoft Windows Network', [Microsoft.Win32.RegistryValueKind]::String)
        $key.SetValue('ProviderType', 131072, [Microsoft.Win32.RegistryValueKind]::DWord)
        $key.SetValue('ConnectionType', 1, [Microsoft.Win32.RegistryValueKind]::DWord)
        $key.SetValue('DeferFlags', 4, [Microsoft.Win32.RegistryValueKind]::DWord)
    } finally { $key.Close() }
}
function Test-UserLoggedOn([string]$Sid) {
    # A user is "signed in at a desktop" if explorer.exe is running under their SID
    try {
        foreach ($p in @(Get-CimInstance -ClassName Win32_Process -Filter "Name='explorer.exe'" -ErrorAction Stop)) {
            $o = Invoke-CimMethod -InputObject $p -MethodName GetOwnerSid -ErrorAction Stop
            if ($o.Sid -eq $Sid) { return $true }
        }
    } catch { }
    return $false
}
function Invoke-AsUser([string]$Account, [string]$CmdArgs, [int]$TimeoutSec) {
    # One-shot scheduled task that runs cmd.exe inside the user's OWN interactive session (limited token),
    # because a drive mapped from this WinRM session would only exist inside this WinRM session.
    $tn  = 'PCAdminTool_Drive_' + [guid]::NewGuid().ToString('N').Substring(0, 10)
    $act = New-ScheduledTaskAction -Execute "$env:SystemRoot\System32\cmd.exe" -Argument $CmdArgs
    $prn = New-ScheduledTaskPrincipal -UserId $Account -LogonType Interactive -RunLevel Limited
    $set = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 2)
    $code = [int64]267011
    try {
        Register-ScheduledTask -TaskName $tn -Action $act -Principal $prn -Settings $set -Force | Out-Null
        Start-ScheduledTask -TaskName $tn
        $limit = (Get-Date).AddSeconds($TimeoutSec)
        do {
            Start-Sleep -Milliseconds 700
            $code = [int64](Get-ScheduledTaskInfo -TaskName $tn).LastTaskResult
        } while ((Get-Date) -lt $limit -and ($code -eq 267009 -or $code -eq 267011))
    } finally {
        Unregister-ScheduledTask -TaskName $tn -Confirm:$false -ErrorAction SilentlyContinue
    }
    return $code
}
function Test-SmbReachable([string]$UncPath) {
    # Network-level check only (DNS + TCP 445). Deliberately NOT Test-Path on the UNC path:
    # from inside a WinRM session that is a double-hop and would fail even when the user has access.
    $srv = ($UncPath.Substring(2) -split '\\')[0]
    $tcp = New-Object System.Net.Sockets.TcpClient
    $ok = $false
    try {
        $iar = $tcp.BeginConnect($srv, 445, $null, $null)
        $ok = ($iar.AsyncWaitHandle.WaitOne(4000, $false) -and $tcp.Connected)
    } catch { $ok = $false } finally { $tcp.Close() }
    return @{ Server = $srv; Ok = [bool]$ok }
}
function Get-ProfileTempLog([string]$ProfilePath, [string]$Name) {
    if ($ProfilePath) { return (Join-Path $ProfilePath "AppData\Local\Temp\$Name") }
    return $null
}
function Read-AndDeleteLog([string]$Path) {
    $t = ''
    if ($Path -and [System.IO.File]::Exists($Path)) {
        $t = ((Get-Content -LiteralPath $Path -ErrorAction SilentlyContinue) -join ' ').Trim()
        Remove-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
    }
    return $t
}

$share    = '{{SHARE_PATH}}'
$letter   = '{{DRIVE_LETTER}}'
$account  = '{{USER_ACCOUNT}}'
$applyNow = {{APPLY_NOW}}
$replace  = {{REPLACE_EXISTING}}
$L = $letter.TrimEnd(':')
$hive = $null

Write-Output "  === MAP NETWORK DRIVE FOR A USER ==="
Write-Output "  Shared folder : $share"
Write-Output "  Drive letter  : $letter"
Write-Output "  For account   : $account"
try {
    $u = Resolve-TargetUser $account
    Write-Output "  Account found : $($u.Name)  [$($u.Sid)]"
    $prof = Get-UserProfilePath $u.Sid

    $local = Get-CimInstance -ClassName Win32_LogicalDisk -Filter "DeviceID='$letter'" -ErrorAction SilentlyContinue
    if ($local -and $local.DriveType -ne 4) {
        Write-Output "  ERROR: $letter is already a local disk on this PC -- choose a different drive letter."
        return
    }

    $reach = Test-SmbReachable $share
    if ($reach.Ok) {
        Write-Output "  Network check : $($reach.Server) answers on TCP 445 from this PC."
    } else {
        Write-Output "  WARNING: $($reach.Server) did not answer on TCP 445 from this PC -- the mapping is still saved, but the drive shows as disconnected until that server is reachable."
    }

    $hive = Open-UserHive $u.Sid $prof
    if ($hive.Temp) {
        Write-Output "  Profile       : user is not signed in -- profile registry loaded temporarily"
    } else {
        Write-Output "  Profile       : profile registry already loaded (user is signed in or has a running process)"
    }

    $old = @(Get-NetDriveKeys $hive) | Where-Object { $_.Letter -eq $L } | Select-Object -First 1
    $write = $true
    if ($old) {
        if ($old.RemotePath -ieq $share) {
            Write-Output "  $letter is already saved for this user with the same share -- registry left as it is."
            $write = $false
        } elseif (-not $replace) {
            Write-Output "  STOPPED: $letter is already saved for this user as $($old.RemotePath). Tick 'Replace an existing mapping' to overwrite it, or use another drive letter."
            return
        } else {
            Write-Output "  Replacing the saved mapping $letter -> $($old.RemotePath)"
        }
    }
    if ($write) {
        Set-NetDriveKey $hive $L $share
        Write-Output "  Saved in the user's profile: $letter -> $share (reconnects at every sign-in)"
    }

    if (-not $applyNow) {
        Write-Output "  Apply-now is OFF -- the drive appears the next time this user signs in."
    } elseif (-not (Test-UserLoggedOn $u.Sid)) {
        Write-Output "  This user is not signed in at a desktop right now -- the drive appears at their next sign-in."
    } else {
        Write-Output "  User is signed in -- connecting the drive inside their own session now..."
        $logName = "pcadmintool_map_$L.log"
        $logFile = Get-ProfileTempLog $prof $logName
        if ($logFile) { Remove-Item -LiteralPath $logFile -Force -ErrorAction SilentlyContinue }
        $cmdArgs = '/c net use ' + $letter + ' /delete /y >nul 2>&1 & net use ' + $letter + ' "' + $share + '" /persistent:yes > "%TEMP%\' + $logName + '" 2>&1'
        try {
            $rc = Invoke-AsUser $u.Name $cmdArgs 30
            $detail = Read-AndDeleteLog $logFile
            if ($rc -eq 0) {
                Write-Output "  Live connection complete: $letter is now available in the user's session. $detail"
            } elseif ($rc -eq 267011 -or $rc -eq 267009) {
                Write-Output "  WARNING: the connect task did not finish within 30 seconds (still running, or it never started)."
            } else {
                Write-Output "  WARNING: the live connection failed (task result $rc): $detail"
                Write-Output "           The saved mapping is still in place and is retried at the next sign-in."
            }
        } catch {
            Write-Output "  WARNING: could not start the live connection: $($_.Exception.Message)"
            Write-Output "           The saved mapping is still in place and appears at the next sign-in."
        }
    }
    Write-Output "  Registry mapping complete for $($u.Name): $letter -> $share"
} catch {
    Write-Output "  ERROR: $($_.Exception.Message)"
} finally {
    Close-UserHive $hive
}
   } }
 @{Id="rt_unmap_network_drive";Cat="Remote Tools";D=$true;L='Remove Mapped Network Drive for a User';Ds='Removes a saved drive mapping from ONE user''s profile on the target (and disconnects it live if that user is signed in)'
   Prm=@(
     @{Key="DRIVE_LETTER";Kind="mapdrive";Label='Drive Letter';Req=$true;Def='Z';Help='D to Z'},
     @{Key="USER_ACCOUNT";Kind="useraccount";Label='Remove It For This User Account';Req=$true;Help='DOMAIN\jsmith   or   jsmith@corp.local   or   .\localuser'},
     @{Key="APPLY_NOW";Kind="bool";Label='Also disconnect it right now if that user is signed in';Req=$true;Def='true';Help='Unchecked: only removed from the profile -- a live connection stays until sign-out'}
   )
   Cmd={
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
function Invoke-Reg([string[]]$RegArgs) {
    # reg.exe wrapper: stderr is merged into text so it can never leak into the error stream
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $o = (& "$env:SystemRoot\System32\reg.exe" @RegArgs 2>&1 | ForEach-Object { "$_" }) -join ' '
        $c = $LASTEXITCODE
    } finally { $ErrorActionPreference = $prev }
    return @{ Code = $c; Out = "$o".Trim() }
}
function Resolve-TargetUser([string]$Account) {
    # DOMAIN\user, user@domain, .\localuser or a bare name -> SID + canonical DOMAIN\user
    $a = $Account.Trim()
    if ($a -match '^\.\\') { $a = "$env:COMPUTERNAME\" + $a.Substring(2) }
    try {
        $sid = (New-Object System.Security.Principal.NTAccount($a)).Translate([System.Security.Principal.SecurityIdentifier])
        $name = $sid.Translate([System.Security.Principal.NTAccount]).Value
    } catch {
        throw "Windows on the target cannot find the account '$Account'. Use DOMAIN\username for a domain user, or .\username for a local user."
    }
    return @{ Sid = $sid.Value; Name = $name }
}
function Get-UserProfilePath([string]$Sid) {
    $k = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList\$Sid"
    if (Test-Path -LiteralPath $k) { return [string](Get-ItemProperty -LiteralPath $k).ProfileImagePath }
    return $null
}
function Open-UserHive([string]$Sid, [string]$ProfilePath) {
    # Already loaded (user signed in / process running as user) -> use it. Otherwise load NTUSER.DAT temporarily.
    if ([Microsoft.Win32.Registry]::Users.GetSubKeyNames() -contains $Sid) { return @{ Name = $Sid; Temp = $false } }
    if (-not $ProfilePath) { throw 'That account has no profile on the target (it has never signed in there), so there is nothing to map into yet.' }
    $dat = Join-Path $ProfilePath 'NTUSER.DAT'
    if (-not [System.IO.File]::Exists($dat)) { throw "NTUSER.DAT was not found at $dat" }
    $tmp = 'PCAdminTmp_' + [guid]::NewGuid().ToString('N').Substring(0, 8)
    $r = Invoke-Reg @('load', "HKU\$tmp", $dat)
    if ($r.Code -ne 0) { throw "Could not load the user's registry hive (the user may be signing in right now): $($r.Out)" }
    return @{ Name = $tmp; Temp = $true }
}
function Close-UserHive($Hive) {
    if (-not $Hive -or -not $Hive.Temp) { return }
    [gc]::Collect(); [gc]::WaitForPendingFinalizers()
    $r = $null
    for ($i = 0; $i -lt 8; $i++) {
        $r = Invoke-Reg @('unload', "HKU\$($Hive.Name)")
        if ($r.Code -eq 0) { return }
        Start-Sleep -Milliseconds 500
        [gc]::Collect()
    }
    Write-Output "  WARNING: the temporary registry hive HKU\$($Hive.Name) could not be unloaded: $($r.Out)"
}
function Get-NetDriveKeys($Hive) {
    # Persistent mapped drives live in HKU\<SID>\Network\<letter>
    $found = @()
    $nk = [Microsoft.Win32.Registry]::Users.OpenSubKey("$($Hive.Name)\Network")
    if ($nk) {
        try {
            foreach ($n in $nk.GetSubKeyNames()) {
                $k = $nk.OpenSubKey($n)
                if ($k) {
                    try {
                        $found += New-Object PSObject -Property @{
                            Letter     = $n.ToUpper()
                            RemotePath = [string]$k.GetValue('RemotePath')
                            UserName   = [string]$k.GetValue('UserName')
                        }
                    } finally { $k.Close() }
                }
            }
        } finally { $nk.Close() }
    }
    return $found
}
function Remove-NetDriveKey($Hive, [string]$Letter) {
    $nk = [Microsoft.Win32.Registry]::Users.OpenSubKey("$($Hive.Name)\Network", $true)
    if ($nk) {
        try { $nk.DeleteSubKeyTree($Letter, $false) } finally { $nk.Close() }
    }
}
function Test-UserLoggedOn([string]$Sid) {
    # A user is "signed in at a desktop" if explorer.exe is running under their SID
    try {
        foreach ($p in @(Get-CimInstance -ClassName Win32_Process -Filter "Name='explorer.exe'" -ErrorAction Stop)) {
            $o = Invoke-CimMethod -InputObject $p -MethodName GetOwnerSid -ErrorAction Stop
            if ($o.Sid -eq $Sid) { return $true }
        }
    } catch { }
    return $false
}
function Invoke-AsUser([string]$Account, [string]$CmdArgs, [int]$TimeoutSec) {
    # One-shot scheduled task that runs cmd.exe inside the user's OWN interactive session (limited token),
    # because a drive mapped from this WinRM session would only exist inside this WinRM session.
    $tn  = 'PCAdminTool_Drive_' + [guid]::NewGuid().ToString('N').Substring(0, 10)
    $act = New-ScheduledTaskAction -Execute "$env:SystemRoot\System32\cmd.exe" -Argument $CmdArgs
    $prn = New-ScheduledTaskPrincipal -UserId $Account -LogonType Interactive -RunLevel Limited
    $set = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 2)
    $code = [int64]267011
    try {
        Register-ScheduledTask -TaskName $tn -Action $act -Principal $prn -Settings $set -Force | Out-Null
        Start-ScheduledTask -TaskName $tn
        $limit = (Get-Date).AddSeconds($TimeoutSec)
        do {
            Start-Sleep -Milliseconds 700
            $code = [int64](Get-ScheduledTaskInfo -TaskName $tn).LastTaskResult
        } while ((Get-Date) -lt $limit -and ($code -eq 267009 -or $code -eq 267011))
    } finally {
        Unregister-ScheduledTask -TaskName $tn -Confirm:$false -ErrorAction SilentlyContinue
    }
    return $code
}
function Get-ProfileTempLog([string]$ProfilePath, [string]$Name) {
    if ($ProfilePath) { return (Join-Path $ProfilePath "AppData\Local\Temp\$Name") }
    return $null
}
function Read-AndDeleteLog([string]$Path) {
    $t = ''
    if ($Path -and [System.IO.File]::Exists($Path)) {
        $t = ((Get-Content -LiteralPath $Path -ErrorAction SilentlyContinue) -join ' ').Trim()
        Remove-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
    }
    return $t
}

$account  = '{{USER_ACCOUNT}}'
$letter   = '{{DRIVE_LETTER}}'
$applyNow = {{APPLY_NOW}}
$L = $letter.TrimEnd(':')
$hive = $null

Write-Output "  === REMOVE MAPPED NETWORK DRIVE FOR A USER ==="
Write-Output "  Drive letter  : $letter"
Write-Output "  For account   : $account"
try {
    $u = Resolve-TargetUser $account
    Write-Output "  Account found : $($u.Name)  [$($u.Sid)]"
    $prof = Get-UserProfilePath $u.Sid
    $hive = Open-UserHive $u.Sid $prof
    if ($hive.Temp) {
        Write-Output "  Profile       : user is not signed in -- profile registry loaded temporarily"
    } else {
        Write-Output "  Profile       : profile registry already loaded (user is signed in or has a running process)"
    }

    $old = @(Get-NetDriveKeys $hive) | Where-Object { $_.Letter -eq $L } | Select-Object -First 1
    if ($old) {
        Remove-NetDriveKey $hive $L
        Write-Output "  Removed the saved mapping $letter -> $($old.RemotePath) from the user's profile."
    } else {
        Write-Output "  No saved mapping for $letter in this user's profile -- nothing to remove from the registry."
    }

    if (-not $applyNow) {
        Write-Output "  Disconnect-now is OFF -- if the drive is connected in the user's session it stays until they sign out."
    } elseif (-not (Test-UserLoggedOn $u.Sid)) {
        Write-Output "  This user is not signed in at a desktop right now -- nothing to disconnect live."
    } else {
        Write-Output "  User is signed in -- disconnecting the drive inside their own session now..."
        $logName = "pcadmintool_unmap_$L.log"
        $logFile = Get-ProfileTempLog $prof $logName
        if ($logFile) { Remove-Item -LiteralPath $logFile -Force -ErrorAction SilentlyContinue }
        $cmdArgs = '/c net use ' + $letter + ' /delete /y > "%TEMP%\' + $logName + '" 2>&1'
        try {
            $rc = Invoke-AsUser $u.Name $cmdArgs 30
            $detail = Read-AndDeleteLog $logFile
            if ($rc -eq 0) {
                Write-Output "  Live disconnect complete: $letter was disconnected in the user's session. $detail"
            } elseif ($rc -eq 267011 -or $rc -eq 267009) {
                Write-Output "  WARNING: the disconnect task did not finish within 30 seconds (still running, or it never started)."
            } else {
                Write-Output "  Note: nothing was disconnected live (task result $rc) -- the drive was probably not connected in that session. $detail"
            }
        } catch {
            Write-Output "  WARNING: could not start the live disconnect: $($_.Exception.Message)"
        }
    }
    Write-Output "  Removal complete for $($u.Name): $letter"
} catch {
    Write-Output "  ERROR: $($_.Exception.Message)"
} finally {
    Close-UserHive $hive
}
   } }
 @{Id="rt_list_mapped_drives";Cat="Remote Tools";D=$false;L='List Mapped Network Drives (Saved Per User)';Ds='Shows the drive mappings saved in a user''s profile on the target -- use it to verify a mapping (blank user = everyone currently signed in)'
   Prm=@(
     @{Key="USER_ACCOUNT";Kind="useraccount";Label='User Account';Req=$false;Help='blank = every signed-in user   |   DOMAIN\jsmith   |   .\localuser'}
   )
   Cmd={
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
function Invoke-Reg([string[]]$RegArgs) {
    # reg.exe wrapper: stderr is merged into text so it can never leak into the error stream
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $o = (& "$env:SystemRoot\System32\reg.exe" @RegArgs 2>&1 | ForEach-Object { "$_" }) -join ' '
        $c = $LASTEXITCODE
    } finally { $ErrorActionPreference = $prev }
    return @{ Code = $c; Out = "$o".Trim() }
}
function Resolve-TargetUser([string]$Account) {
    # DOMAIN\user, user@domain, .\localuser or a bare name -> SID + canonical DOMAIN\user
    $a = $Account.Trim()
    if ($a -match '^\.\\') { $a = "$env:COMPUTERNAME\" + $a.Substring(2) }
    try {
        $sid = (New-Object System.Security.Principal.NTAccount($a)).Translate([System.Security.Principal.SecurityIdentifier])
        $name = $sid.Translate([System.Security.Principal.NTAccount]).Value
    } catch {
        throw "Windows on the target cannot find the account '$Account'. Use DOMAIN\username for a domain user, or .\username for a local user."
    }
    return @{ Sid = $sid.Value; Name = $name }
}
function Get-UserProfilePath([string]$Sid) {
    $k = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList\$Sid"
    if (Test-Path -LiteralPath $k) { return [string](Get-ItemProperty -LiteralPath $k).ProfileImagePath }
    return $null
}
function Open-UserHive([string]$Sid, [string]$ProfilePath) {
    # Already loaded (user signed in / process running as user) -> use it. Otherwise load NTUSER.DAT temporarily.
    if ([Microsoft.Win32.Registry]::Users.GetSubKeyNames() -contains $Sid) { return @{ Name = $Sid; Temp = $false } }
    if (-not $ProfilePath) { throw 'That account has no profile on the target (it has never signed in there), so there is nothing to map into yet.' }
    $dat = Join-Path $ProfilePath 'NTUSER.DAT'
    if (-not [System.IO.File]::Exists($dat)) { throw "NTUSER.DAT was not found at $dat" }
    $tmp = 'PCAdminTmp_' + [guid]::NewGuid().ToString('N').Substring(0, 8)
    $r = Invoke-Reg @('load', "HKU\$tmp", $dat)
    if ($r.Code -ne 0) { throw "Could not load the user's registry hive (the user may be signing in right now): $($r.Out)" }
    return @{ Name = $tmp; Temp = $true }
}
function Close-UserHive($Hive) {
    if (-not $Hive -or -not $Hive.Temp) { return }
    [gc]::Collect(); [gc]::WaitForPendingFinalizers()
    $r = $null
    for ($i = 0; $i -lt 8; $i++) {
        $r = Invoke-Reg @('unload', "HKU\$($Hive.Name)")
        if ($r.Code -eq 0) { return }
        Start-Sleep -Milliseconds 500
        [gc]::Collect()
    }
    Write-Output "  WARNING: the temporary registry hive HKU\$($Hive.Name) could not be unloaded: $($r.Out)"
}
function Get-NetDriveKeys($Hive) {
    # Persistent mapped drives live in HKU\<SID>\Network\<letter>
    $found = @()
    $nk = [Microsoft.Win32.Registry]::Users.OpenSubKey("$($Hive.Name)\Network")
    if ($nk) {
        try {
            foreach ($n in $nk.GetSubKeyNames()) {
                $k = $nk.OpenSubKey($n)
                if ($k) {
                    try {
                        $found += New-Object PSObject -Property @{
                            Letter     = $n.ToUpper()
                            RemotePath = [string]$k.GetValue('RemotePath')
                            UserName   = [string]$k.GetValue('UserName')
                        }
                    } finally { $k.Close() }
                }
            }
        } finally { $nk.Close() }
    }
    return $found
}
function Get-LoadedUserSids {
    # SIDs of every user whose profile registry is currently loaded (signed in, or a process running as that user)
    return @([Microsoft.Win32.Registry]::Users.GetSubKeyNames() | Where-Object { $_ -match '^S-1-5-21-\d+-\d+-\d+-\d+$' })
}
function Get-NameFromSid([string]$Sid) {
    try { return (New-Object System.Security.Principal.SecurityIdentifier($Sid)).Translate([System.Security.Principal.NTAccount]).Value }
    catch { return '(name not resolvable)' }
}
function Test-UserLoggedOn([string]$Sid) {
    # A user is "signed in at a desktop" if explorer.exe is running under their SID
    try {
        foreach ($p in @(Get-CimInstance -ClassName Win32_Process -Filter "Name='explorer.exe'" -ErrorAction Stop)) {
            $o = Invoke-CimMethod -InputObject $p -MethodName GetOwnerSid -ErrorAction Stop
            if ($o.Sid -eq $Sid) { return $true }
        }
    } catch { }
    return $false
}

$account = '{{USER_ACCOUNT}}'

Write-Output "  === MAPPED NETWORK DRIVES (saved in each user's profile) ==="
$targets = @()
try {
    if ([string]::IsNullOrWhiteSpace($account)) {
        Write-Output "  No account given -- listing every user whose profile is currently loaded (signed in)."
        foreach ($s in @(Get-LoadedUserSids)) { $targets += @{ Sid = $s; Name = '' } }
    } else {
        $u = Resolve-TargetUser $account
        $targets += @{ Sid = $u.Sid; Name = $u.Name }
    }
} catch {
    Write-Output "  ERROR: $($_.Exception.Message)"
    return
}

if ($targets.Count -eq 0) {
    Write-Output "  No signed-in user profiles found."
    return
}

foreach ($t in $targets) {
    $hive = $null
    try {
        $name = $t.Name
        if (-not $name) { $name = Get-NameFromSid $t.Sid }
        $prof = Get-UserProfilePath $t.Sid
        $signedIn = Test-UserLoggedOn $t.Sid
        $hive = Open-UserHive $t.Sid $prof
        $hiveTxt = 'loaded'
        if ($hive.Temp) { $hiveTxt = 'read from disk (user not signed in)' }
        Write-Output ""
        Write-Output "  User : $name   [$($t.Sid)]"
        Write-Output "         signed in at a desktop: $signedIn   |   profile registry: $hiveTxt"
        $drives = @(Get-NetDriveKeys $hive) | Sort-Object Letter
        if ($drives.Count -eq 0) {
            Write-Output "         no saved mapped drives"
        } else {
            foreach ($d in $drives) {
                $cred = ''
                if ($d.UserName -and $d.UserName -ne '0') { $cred = "   (connects as $($d.UserName))" }
                Write-Output ("         {0}:  {1}{2}" -f $d.Letter, $d.RemotePath, $cred)
            }
        }
    } catch {
        Write-Output "  ERROR for $($t.Sid): $($_.Exception.Message)"
    } finally {
        Close-UserHive $hive
    }
}
Write-Output ""
Write-Output "  Note: this lists what is SAVED in the profile (reconnected at every sign-in). Whether a drive is connected"
Write-Output "  right now is only visible inside that user's own session -- ask them to open This PC, or check for a red X."
   } }
)

# ============================================================
# HELPER FUNCTIONS
# ============================================================
$Script:RtbLog=$null
function LogIt([string]$t,[string]$tag="out") {
    if(-not $Script:RtbLog){return}
    $col=switch($tag){"hdr"{$CYAN}"ok"{$GRN}"warn"{$YEL}"err"{$RED}"dim"{$DIM}"task"{$TXTB}"info"{$TXDD}default{$OUT2}}
    $Script:RtbLog.SelectionStart=$Script:RtbLog.TextLength
    $Script:RtbLog.SelectionLength=0
    $Script:RtbLog.SelectionColor=$col
    $Script:RtbLog.AppendText($t+"`r`n")
    $Script:RtbLog.ScrollToCaret()
    if($Script:LogFile){Add-Content -Path $Script:LogFile -Value $t -Encoding UTF8 -EA SilentlyContinue}
}
function ConnStat([string]$t,[System.Drawing.Color]$c) {
    if($Script:LblConn){$Script:LblConn.Text=" $t";$Script:LblConn.ForeColor=$c}
}
function GetSel { $Ops|Where-Object{$CbMap.ContainsKey($_.Id) -and $CbMap[$_.Id].Checked} }
function UpdCount {
    $n=(GetSel).Count
    $nd=($Ops|Where-Object{$DANGER -contains $_.Id -and $CbMap.ContainsKey($_.Id) -and $CbMap[$_.Id].Checked}).Count
    $cntTxt="$n task(s) selected"
    if($nd){$cntTxt="$n task(s) selected  |  ! $nd sensitive"}
    $Script:LblCnt.Text=$cntTxt
}

# ============================================================
# FORM
# ============================================================
$F=New-Object System.Windows.Forms.Form
$F.Text="PC Admin & Performance Tool  v3.6  --  (c) 2024-2026 Abdullah"
$F.ClientSize=New-Object System.Drawing.Size(1380,860)
$F.MinimumSize=New-Object System.Drawing.Size(1100,680)
$F.BackColor=$BG;$F.StartPosition="CenterScreen"
try{$F.Icon=[System.Drawing.Icon]::ExtractAssociatedIcon([System.Windows.Forms.Application]::ExecutablePath)}catch{}

# HEADER 52px
$PH=New-Object System.Windows.Forms.Panel;$PH.Dock="Top";$PH.Height=52;$PH.BackColor=$HDRB
$lTi=New-Object System.Windows.Forms.Label
$lTi.Text="   PC ADMIN  PERFORMANCE TROUBLESHOOTING TOOL"
$lTi.Font=GF "Segoe UI" 13 -B;$lTi.ForeColor=$TXTB;$lTi.TextAlign="MiddleLeft";$lTi.Dock="Fill"
$PH.Controls.Add($lTi)
$pV=New-Object System.Windows.Forms.Panel;$pV.Width=480;$pV.Dock="Right";$pV.BackColor=$HDRB
$lV1=New-Object System.Windows.Forms.Label;$lV1.Text=$VER
$lV1.Font=GF "Segoe UI" 9 -B;$lV1.ForeColor=$CYAN;$lV1.TextAlign="TopRight"
$lV1.SetBounds(0,8,478,20);$pV.Controls.Add($lV1)
$lV2=New-Object System.Windows.Forms.Label;$lV2.Text="(c) 2024-2026 Abdullah  |  abuabdullah.be@outlook.com"
$lV2.Font=GF "Segoe UI" 8;$lV2.ForeColor=$TXDD;$lV2.TextAlign="TopRight"
$lV2.SetBounds(0,28,478,18);$pV.Controls.Add($lV2)
$PH.Controls.Add($pV)
$F.Controls.Add($PH)

# TABS 40px
$PT=New-Object System.Windows.Forms.Panel;$PT.Dock="Top";$PT.Height=40;$PT.BackColor=$PNL
$lFl=New-Object System.Windows.Forms.Label;$lFl.Text="  FILTER:"
$lFl.Font=GF "Segoe UI" 8 -B;$lFl.ForeColor=$TXDD;$lFl.TextAlign="MiddleLeft"
$lFl.SetBounds(0,0,66,40);$PT.Controls.Add($lFl)
$Script:TabBtns=@{};$tx=68
foreach($td in @(
  @{L="All";K="all";Col=$GRN},@{L="Clear";K="_c";Col=$RED},@{L="Select All";K="_a";Col=$GRN},
  @{L="|";K=""},
  @{L="Cleanup";K="Cleanup";Col=$CYAN},@{L="Disk";K="Disk";Col=$CYAN},
  @{L="Performance";K="Performance";Col=$CYAN},@{L="Windows Health";K="Windows Health";Col=$CYAN},
  @{L="Network";K="Network";Col=$CYAN},@{L="Power Recycle";K="Power Recycle";Col=$YEL},
  @{L="Remote Tools";K="Remote Tools";Col=$CYAN})){
    if($td.K -eq ""){$sep=New-Object System.Windows.Forms.Label;$sep.SetBounds($tx,8,2,24);$sep.BackColor=$BDR2;$PT.Controls.Add($sep);$tx+=8;continue}
    $tb=New-Object System.Windows.Forms.Button;$tb.Text=$td.L;$tb.Tag=$td.K;$tb.AutoSize=$true
    $tb.Left=$tx;$tb.Top=6;$tb.Height=28;$tb.FlatStyle="Flat"
    $tb.FlatAppearance.BorderSize=1;$tb.FlatAppearance.BorderColor=$BDR
    $tb.BackColor=$CARD;$tb.ForeColor=$TXDD;$tb.Font=GF "Segoe UI" 9 -B
    $tb.Cursor=[System.Windows.Forms.Cursors]::Hand;$tb.Padding=New-Object System.Windows.Forms.Padding(8,0,8,0)
    $tb.Add_Click({TabClk $this.Tag});$PT.Controls.Add($tb)
    if($td.K -notin @("_c","_a")){$Script:TabBtns[$td.K]=@{B=$tb;Col=$td.Col}}
    $tx+=$tb.PreferredSize.Width+4
}
$F.Controls.Add($PT)

# FOOTER 22px
$PF=New-Object System.Windows.Forms.Panel;$PF.Dock="Bottom";$PF.Height=22;$PF.BackColor=HC "#06111e"
$lFo=New-Object System.Windows.Forms.Label;$lFo.Text="  $COPYL"
$lFo.Font=GF "Segoe UI" 8;$lFo.ForeColor=HC "#253d57";$lFo.TextAlign="MiddleLeft";$lFo.Dock="Fill"
$PF.Controls.Add($lFo);$F.Controls.Add($PF)

# ACTION BAR 60px
$PA=New-Object System.Windows.Forms.Panel;$PA.Dock="Bottom";$PA.Height=60;$PA.BackColor=$PNL
$BtnRun=New-Object System.Windows.Forms.Button;$BtnRun.Text="  PERFORM SELECTED  "
$BtnRun.SetBounds(8,9,210,42);$BtnRun.BackColor=HC "#15803d";$BtnRun.ForeColor=[System.Drawing.Color]::White
$BtnRun.FlatStyle="Flat";$BtnRun.FlatAppearance.BorderSize=0;$BtnRun.Font=GF "Segoe UI" 11 -B
$BtnRun.Cursor=[System.Windows.Forms.Cursors]::Hand;$PA.Controls.Add($BtnRun)
$BtnStop=New-Object System.Windows.Forms.Button;$BtnStop.Text="  STOP  "
$BtnStop.SetBounds(226,9,96,42);$BtnStop.BackColor=HC "#991b1b";$BtnStop.ForeColor=[System.Drawing.Color]::White
$BtnStop.FlatStyle="Flat";$BtnStop.FlatAppearance.BorderSize=0;$BtnStop.Font=GF "Segoe UI" 11 -B
$BtnStop.Enabled=$false;$BtnStop.Cursor=[System.Windows.Forms.Cursors]::Hand;$PA.Controls.Add($BtnStop)
$BtnClr=New-Object System.Windows.Forms.Button;$BtnClr.Text="Clear Log"
$BtnClr.SetBounds(330,9,86,42);$BtnClr.BackColor=$CRD2;$BtnClr.ForeColor=$TXDD
$BtnClr.FlatStyle="Flat";$BtnClr.FlatAppearance.BorderSize=0;$BtnClr.Font=GF "Segoe UI" 9
$BtnClr.Cursor=[System.Windows.Forms.Cursors]::Hand;$PA.Controls.Add($BtnClr)
$PrgBar=New-Object System.Windows.Forms.ProgressBar
$PrgBar.SetBounds(424,20,200,20);$PrgBar.Style="Continuous";$PA.Controls.Add($PrgBar)
$Script:LblStat=New-Object System.Windows.Forms.Label
$Script:LblStat.Text="Ready -- select tasks and click PERFORM SELECTED"
$Script:LblStat.SetBounds(632,9,450,42);$Script:LblStat.ForeColor=$TXDD;$Script:LblStat.Font=GF "Segoe UI" 9
$Script:LblStat.TextAlign="MiddleLeft";$Script:LblStat.BackColor=[System.Drawing.Color]::Transparent
$PA.Controls.Add($Script:LblStat)
$Script:LblCnt=New-Object System.Windows.Forms.Label;$Script:LblCnt.Text="0 tasks selected"
$Script:LblCnt.Top=9;$Script:LblCnt.Width=200;$Script:LblCnt.Height=42
$Script:LblCnt.ForeColor=$TXDD;$Script:LblCnt.Font=GF "Segoe UI" 9;$Script:LblCnt.TextAlign="MiddleRight"
$Script:LblCnt.Anchor=[System.Windows.Forms.AnchorStyles]::Top -bor [System.Windows.Forms.AnchorStyles]::Right
$PA.Controls.Add($Script:LblCnt)
$BtnLogs=New-Object System.Windows.Forms.Button;$BtnLogs.Text="Open Logs"
$BtnLogs.Top=9;$BtnLogs.Width=96;$BtnLogs.Height=42
$BtnLogs.BackColor=$CRD2;$BtnLogs.ForeColor=$TXDD;$BtnLogs.FlatStyle="Flat";$BtnLogs.FlatAppearance.BorderSize=0
$BtnLogs.Font=GF "Segoe UI" 9;$BtnLogs.Cursor=[System.Windows.Forms.Cursors]::Hand
$BtnLogs.Anchor=[System.Windows.Forms.AnchorStyles]::Top -bor [System.Windows.Forms.AnchorStyles]::Right
$PA.Controls.Add($BtnLogs)
$F.Controls.Add($PA)

# MAIN FILL
$PM=New-Object System.Windows.Forms.Panel;$PM.Dock="Fill";$PM.BackColor=$BG

# RIGHT: log panel (Dock=Right, 420px)
$PR=New-Object System.Windows.Forms.Panel;$PR.Dock="Right";$PR.Width=420;$PR.BackColor=$BG
$PRL=New-Object System.Windows.Forms.Panel;$PRL.Dock="Top";$PRL.Height=28;$PRL.BackColor=$PNL
$Script:LblDot=New-Object System.Windows.Forms.Label;$Script:LblDot.Text=" o"
$Script:LblDot.SetBounds(4,0,24,28);$Script:LblDot.ForeColor=$TXDD;$Script:LblDot.Font=GF "Segoe UI" 11;$Script:LblDot.TextAlign="MiddleLeft"
$PRL.Controls.Add($Script:LblDot)
$lLT=New-Object System.Windows.Forms.Label;$lLT.Text="LIVE OUTPUT  &  LOG"
$lLT.SetBounds(28,0,200,28);$lLT.ForeColor=$TXDD;$lLT.Font=GF "Segoe UI" 8 -B;$lLT.TextAlign="MiddleLeft"
$PRL.Controls.Add($lLT)
$Script:LblTask=New-Object System.Windows.Forms.Label;$Script:LblTask.Text=""
$Script:LblTask.SetBounds(200,0,210,28);$Script:LblTask.ForeColor=$CYAN;$Script:LblTask.Font=GF "Segoe UI" 8;$Script:LblTask.TextAlign="MiddleRight"
$PRL.Controls.Add($Script:LblTask)
$PR.Controls.Add($PRL)

# RICH TEXT BOX FOR LOGGING
$Script:RtbLog=New-Object System.Windows.Forms.RichTextBox;$Script:RtbLog.Dock="Fill"
$Script:RtbLog.BackColor=$LOGBG;$Script:RtbLog.ForeColor=$OUT2;$Script:RtbLog.Font=MF
$Script:RtbLog.BorderStyle="None";$Script:RtbLog.ReadOnly=$true
$PR.Controls.Add($Script:RtbLog)
$PM.Controls.Add($PR)

# DIVIDER 1px
$PD=New-Object System.Windows.Forms.Panel;$PD.Dock="Right";$PD.Width=1;$PD.BackColor=$BDR2
$PM.Controls.Add($PD)

# LEFT PANEL
$PL=New-Object System.Windows.Forms.Panel;$PL.Dock="Fill";$PL.BackColor=$BG

# -- CREDENTIALS PANEL --
$PC=New-Object System.Windows.Forms.Panel
$PC.Dock="Top";$PC.Height=134;$PC.BackColor=$CARD

# Header bar
$hdrBar=New-Object System.Windows.Forms.Label
$hdrBar.Text="  TARGET MACHINE  &  CREDENTIALS"
$hdrBar.SetBounds(0,0,1400,26)
$hdrBar.BackColor=HC "#0d1b2e";$hdrBar.ForeColor=$CYAN
$hdrBar.Font=GF "Segoe UI" 8 -B;$hdrBar.TextAlign="MiddleLeft"
$PC.Controls.Add($hdrBar)

# Row 1: Hostname / IP + Test Connection + Status  (y=35)
$l1a=New-Object System.Windows.Forms.Label;$l1a.Text="Hostname / IP :"
$l1a.SetBounds(8,35,112,24);$l1a.ForeColor=$TXTB;$l1a.BackColor=[System.Drawing.Color]::Transparent
$l1a.Font=GF "Segoe UI" 9;$l1a.TextAlign="MiddleLeft"
$PC.Controls.Add($l1a)

$Script:TxH=New-Object System.Windows.Forms.TextBox
$Script:TxH.SetBounds(124,33,224,28);$Script:TxH.BackColor=HC "#07111f";$Script:TxH.ForeColor=$TXTB
$Script:TxH.BorderStyle="FixedSingle";$Script:TxH.Font=GF "Consolas" 10
$PC.Controls.Add($Script:TxH)

$Script:BtnT=New-Object System.Windows.Forms.Button;$Script:BtnT.Text="  Test Connection  "
$Script:BtnT.SetBounds(356,32,172,30);$Script:BtnT.BackColor=$ACC;$Script:BtnT.ForeColor=$TXTB
$Script:BtnT.FlatStyle="Flat";$Script:BtnT.FlatAppearance.BorderSize=0;$Script:BtnT.Font=GF "Segoe UI" 9 -B
$Script:BtnT.Cursor=[System.Windows.Forms.Cursors]::Hand
$PC.Controls.Add($Script:BtnT)

$Script:LblConn=New-Object System.Windows.Forms.Label;$Script:LblConn.Text="  Not tested"
$Script:LblConn.SetBounds(536,35,430,24);$Script:LblConn.ForeColor=$TXDD
$Script:LblConn.BackColor=[System.Drawing.Color]::Transparent;$Script:LblConn.Font=GF "Segoe UI" 9;$Script:LblConn.TextAlign="MiddleLeft"
$PC.Controls.Add($Script:LblConn)

# Row 2: Username + Password + Show + Auth  (y=71)
$l2a=New-Object System.Windows.Forms.Label;$l2a.Text="Username :"
$l2a.SetBounds(8,71,82,24);$l2a.ForeColor=$TXTB;$l2a.BackColor=[System.Drawing.Color]::Transparent
$l2a.Font=GF "Segoe UI" 9;$l2a.TextAlign="MiddleLeft"
$PC.Controls.Add($l2a)

$Script:TxU=New-Object System.Windows.Forms.TextBox
$Script:TxU.SetBounds(92,69,244,28);$Script:TxU.BackColor=HC "#07111f";$Script:TxU.ForeColor=$TXTB
$Script:TxU.BorderStyle="FixedSingle";$Script:TxU.Font=GF "Consolas" 10
$PC.Controls.Add($Script:TxU)

$l2b=New-Object System.Windows.Forms.Label;$l2b.Text="Password :"
$l2b.SetBounds(346,71,80,24);$l2b.ForeColor=$TXTB;$l2b.BackColor=[System.Drawing.Color]::Transparent
$l2b.Font=GF "Segoe UI" 9;$l2b.TextAlign="MiddleLeft"
$PC.Controls.Add($l2b)

$Script:TxP=New-Object System.Windows.Forms.TextBox
$Script:TxP.SetBounds(428,69,162,28);$Script:TxP.BackColor=HC "#07111f";$Script:TxP.ForeColor=$TXTB
$Script:TxP.BorderStyle="FixedSingle";$Script:TxP.Font=GF "Consolas" 10;$Script:TxP.UseSystemPasswordChar=$true
$PC.Controls.Add($Script:TxP)

$Script:BtnE=New-Object System.Windows.Forms.Button;$Script:BtnE.Text="Show"
$Script:BtnE.SetBounds(598,68,54,30);$Script:BtnE.BackColor=$CRD2;$Script:BtnE.ForeColor=$TXDD
$Script:BtnE.FlatStyle="Flat";$Script:BtnE.FlatAppearance.BorderSize=0;$Script:BtnE.Font=GF "Segoe UI" 8
$Script:BtnE.Cursor=[System.Windows.Forms.Cursors]::Hand
$PC.Controls.Add($Script:BtnE)

$l2c=New-Object System.Windows.Forms.Label;$l2c.Text="Auth :"
$l2c.SetBounds(660,71,44,24);$l2c.ForeColor=$TXTB;$l2c.BackColor=[System.Drawing.Color]::Transparent
$l2c.Font=GF "Segoe UI" 9;$l2c.TextAlign="MiddleLeft"
$PC.Controls.Add($l2c)

$Script:CbA=New-Object System.Windows.Forms.ComboBox
$Script:CbA.SetBounds(706,69,258,28);$Script:CbA.DropDownStyle="DropDownList"
$Script:CbA.BackColor=HC "#07111f";$Script:CbA.ForeColor=$TXT;$Script:CbA.Font=GF "Segoe UI" 9
$TMAP.Keys|ForEach-Object{[void]$Script:CbA.Items.Add($_)};$Script:CbA.SelectedIndex=0
$PC.Controls.Add($Script:CbA)

# Hint row  (y=104)
$hintLbl=New-Object System.Windows.Forms.Label
$hintLbl.Text="  Username: DOMAIN\admin  or  admin@domain.local  |  NTLM=Domain  Basic=Workgroup  Kerberos=AD  CredSSP=Double-hop  |  WinRM: Enable-PSRemoting -Force"
$hintLbl.SetBounds(0,104,1400,24);$hintLbl.ForeColor=$TXDD;$hintLbl.Font=GF "Segoe UI" 8
$hintLbl.BackColor=[System.Drawing.Color]::Transparent;$hintLbl.TextAlign="MiddleLeft"
$PC.Controls.Add($hintLbl)

$PL.Controls.Add($PC)

# Task list header
$PTH=New-Object System.Windows.Forms.Panel;$PTH.Dock="Top";$PTH.Height=22;$PTH.BackColor=$BG
$lTH=New-Object System.Windows.Forms.Label
$lTH.Text=" TROUBLESHOOTING & PERFORMANCE OPTIONS  (67 operations)"
$lTH.Dock="Fill";$lTH.ForeColor=$TXDD;$lTH.Font=GF "Segoe UI" 8 -B;$lTH.TextAlign="MiddleLeft"
$PTH.Controls.Add($lTH);$PL.Controls.Add($PTH)

# Task scroll
$Script:TS=New-Object System.Windows.Forms.Panel;$Script:TS.Dock="Fill";$Script:TS.AutoScroll=$true;$Script:TS.BackColor=$CARD
$PL.Controls.Add($Script:TS)
$PM.Controls.Add($PL)
$F.Controls.Add($PM)

# ============================================================
# BUILD TASK LIST
# ============================================================
function BuildTasks([string]$Flt="all") {
    $Script:TS.SuspendLayout();$Script:TS.Controls.Clear();$CbMap.Clear()
    $Script:TS.AutoScrollPosition = New-Object System.Drawing.Point(0,0)
    $y=2;$curC=""
    foreach($op in $Ops){
        if($Flt -ne "all" -and $op.Cat -ne $Flt){continue}
        if($op.Cat -ne $curC){
            $curC=$op.Cat
            $ph=New-Object System.Windows.Forms.Panel
            $ph.Left=0;$ph.Top=$y;$ph.Width=2000;$ph.Height=26;$ph.BackColor=$PNL
            $lh2=New-Object System.Windows.Forms.Label;$lh2.Text="  [$curC]"
            $lh2.Dock="Fill";$lh2.ForeColor=$CYAN;$lh2.Font=GF "Segoe UI" 9 -B
            $lh2.TextAlign="MiddleLeft";$lh2.BackColor=$PNL
            $ph.Controls.Add($lh2);$Script:TS.Controls.Add($ph);$y+=28
        }
        $isDgr=$DANGER -contains $op.Id
        $pr=New-Object System.Windows.Forms.Panel
        $pr.Left=0;$pr.Top=$y;$pr.Width=2000;$pr.Height=28;$pr.BackColor=$CARD;$pr.Tag=$op.Id
        if($isDgr){$str=New-Object System.Windows.Forms.Panel;$str.Left=0;$str.Top=0;$str.Width=3;$str.Height=28;$str.BackColor=$YEL;$pr.Controls.Add($str)}
        $cb=New-Object System.Windows.Forms.CheckBox
        $cb.Left=8;$cb.Top=5;$cb.Width=20;$cb.Height=20;$cb.FlatStyle="Flat"
        $cb.FlatAppearance.BorderSize=2;$cb.FlatAppearance.BorderColor=[System.Drawing.Color]::White
        $cb.BackColor=$CARD;$cb.Tag=$op.Id;$cb.Add_CheckedChanged({UpdCount});$CbMap[$op.Id]=$cb
        $pr.Controls.Add($cb)
        $nc=if($isDgr){$YEL}else{$TXT};$pfx=if($isDgr){"! "}else{""}
        $ll=New-Object System.Windows.Forms.Label
        $ll.Text="$pfx$($op.L)   --   $($op.Ds)"
        $ll.Left=32;$ll.Top=5;$ll.Width=1900;$ll.Height=20
        $ll.ForeColor=$nc;$ll.Font=GF "Segoe UI" 9;$ll.BackColor=$CARD;$ll.Tag=$op.Id
        $ll.Cursor=[System.Windows.Forms.Cursors]::Hand
        $ll.Add_Click({$CbMap[$this.Tag].Checked=-not $CbMap[$this.Tag].Checked})
        $pr.Controls.Add($ll)
        $pr.Add_MouseEnter({$this.BackColor=$CRD2;foreach($ctrl in $this.Controls){if($ctrl -is [System.Windows.Forms.Label]){$ctrl.BackColor=$CRD2}}})
        $pr.Add_MouseLeave({$this.BackColor=$CARD; foreach($ctrl in $this.Controls){if($ctrl -is [System.Windows.Forms.Label]){$ctrl.BackColor=$CARD}}})
        $pr.Add_Click({$id=$this.Tag;if($CbMap.ContainsKey($id)){$CbMap[$id].Checked=-not $CbMap[$id].Checked}})
        $Script:TS.Controls.Add($pr);$y+=30
    }
    $Script:TS.ResumeLayout($true)
    $Script:TS.AutoScrollPosition = New-Object System.Drawing.Point(0,0)
    $Script:TS.VerticalScroll.Value = 0
}

# ============================================================
# TAB CLICK
# ============================================================
function TabClk([string]$k) {
    if($k -eq "_c"){$CbMap.Values|ForEach-Object{$_.Checked=$false};UpdCount;return}
    if($k -eq "_a"){$CbMap.Values|ForEach-Object{$_.Checked=$true};UpdCount;return}
    $Script:TabBtns.Keys|ForEach-Object{$b=$Script:TabBtns[$_].B
        if($_-eq$k){$b.BackColor=$CRD2;$b.ForeColor=$Script:TabBtns[$_].Col;$b.FlatAppearance.BorderColor=$BDR2}
        else{$b.BackColor=$CARD;$b.ForeColor=$TXDD;$b.FlatAppearance.BorderColor=$BDR}}
    BuildTasks $k
}

# ============================================================
# EVENTS
# ============================================================
$Script:BtnE.Add_Click({
    if($Script:TxP.UseSystemPasswordChar){$Script:TxP.UseSystemPasswordChar=$false;$Script:BtnE.Text="Hide"}
    else{$Script:TxP.UseSystemPasswordChar=$true;$Script:BtnE.Text="Show"}
})
$BtnClr.Add_Click({$Script:RtbLog.Clear();$PrgBar.Value=0;$Script:LblStat.Text="Log cleared"})
$BtnLogs.Add_Click({
    if(Test-Path $LOGD){Start-Process "explorer.exe" $LOGD}
    else{[System.Windows.Forms.MessageBox]::Show("No logs yet.","Logs")}
})
$F.Add_Resize({$w=$PA.Width
    if($w -gt 110){$BtnLogs.Left=$w-104;$Script:LblCnt.Left=[math]::Max(640,$w-312)}
})
$Script:TxH.Add_KeyDown({if($_.KeyCode -eq "Return"){$Script:BtnT.PerformClick()}})
$Script:TxP.Add_KeyDown({if($_.KeyCode -eq "Return"){$Script:BtnT.PerformClick()}})

# TEST CONNECTION
$Script:BtnT.Add_Click({
    $hn=$Script:TxH.Text.Trim();$un=$Script:TxU.Text.Trim()
    $pw=$Script:TxP.Text;$tr=$TMAP[$Script:CbA.SelectedItem]
    if(-not $hn){[System.Windows.Forms.MessageBox]::Show("Enter hostname or IP.","Input");return}
    if(-not $un){[System.Windows.Forms.MessageBox]::Show("Enter username.","Input");return}
    ConnStat "Testing..." $YEL;$Script:BtnT.Enabled=$false
    LogIt ("  "+"-"*44) "dim";LogIt "  Testing : $hn  [$tr]" "info";LogIt "  User    : $un" "info"
    if($Script:TestTimer){try{$Script:TestTimer.Stop()}catch{}}
    $Script:TestJob=[PowerShell]::Create()
    [void]$Script:TestJob.AddScript({param($h,$u,$p,$t,$sh2)
      try{$sec=ConvertTo-SecureString $p -AsPlainText -Force
        $cred=New-Object System.Management.Automation.PSCredential($u,$sec)
        $opts=New-PSSessionOption -OpenTimeout 15000 -OperationTimeout 14000
        $s=New-PSSession -ComputerName $h -Credential $cred -Authentication $t -SessionOption $opts -EA Stop
        $out=Invoke-Command -Session $s -ScriptBlock{"$env:COMPUTERNAME"} -EA Stop
        Remove-PSSession $s -EA SilentlyContinue
        $sh2.CR="ok";$sh2.CM="Connected to $h | Remote: $out | Auth: $t"
      }catch{$e=$_.Exception.Message
        if($e -match "credential|password|auth|logon"){$sh2.CR="cred";$sh2.CM=$e}
        elseif($e -match "5985|refused|connect|network"){$sh2.CR="winrm";$sh2.CM=$e}
        else{$sh2.CR="err";$sh2.CM=$e}}
    }).AddArgument($hn).AddArgument($un).AddArgument($pw).AddArgument($tr).AddArgument($SH)
    $SH.CR="";$SH.CM="";$Script:TestAr=$Script:TestJob.BeginInvoke()
    $Script:TestTimer=New-Object System.Windows.Forms.Timer;$Script:TestTimer.Interval=200
    $Script:TestTimer.Add_Tick({
        if($Script:TestJob.InvocationStateInfo.State -ne "Running"){
            $Script:TestTimer.Stop();$Script:BtnT.Enabled=$true
            switch($SH.CR){
                "ok"   {ConnStat "Connected OK" $GRN;LogIt "  Connected: $($SH.CM)" "ok"}
                "cred" {ConnStat "Auth Failed"  $RED;LogIt "  Auth FAILED: $($SH.CM)" "err";LogIt "  Try: DOMAIN\username  or  user@domain.local" "dim"}
                "winrm"{ConnStat "WinRM Failed" $RED;LogIt "  WinRM not reachable: $($SH.CM)" "err";LogIt "  Run on target: Enable-PSRemoting -Force" "dim"}
                default{ConnStat "Error"        $RED;LogIt "  Error: $($SH.CM)" "err"}}
            LogIt "" "dim";$Script:TestJob.Dispose()}
    });$Script:TestTimer.Start()
})

# STOP
$BtnStop.Add_Click({$SH.Stop=$true;LogIt "  ! STOP requested -- finishing current task..." "warn"})

# ══════════════════════════════════════════════════════════════════════════
#  PARAMETERIZED OPERATIONS -- validation + {{TOKEN}} substitution
#  v3.2: 16 of the 67 operations carry a Prm array (Key/Kind/Label/Req/Def/
#  Help) instead of running a fixed script. Show-ParamForm collects one
#  value per Prm field in a single dialog; Test-ParamValue validates each
#  against an allow-list pattern for its Kind BEFORE it is substituted into
#  a "{{KEY}}" token in the op's Cmd text -- a value that doesn't match is
#  rejected outright, never escaped-and-passed-through. Same rules as the
#  Web/PyGUI editions' PARAM_VALIDATORS, transcribed to PowerShell.
#  v3.1: added a "bool" Kind (a real CheckBox in Show-ParamForm, not a
#  text box) and an Auto-Restart checkbox on the three operations that
#  used to restart unconditionally as a side effect of their real work --
#  pr_full_soft_recycle, rt_rename_pc_domain, rt_rename_pc_workgroup.
#  Default stays checked (unchanged behavior); unchecked, the operation
#  still does its real work but skips the trailing restart. Not added to
#  Force Restart Now / Force Sign-out & Restart -- those two ARE the
#  restart, so an "off" switch would just mean doing nothing.
#  v3.2: added "uncpath" / "mapdrive" / "useraccount" Kinds for the new
#  network-drive-mapping operations, and widened "servicename" to allow
#  spaces and $ # + ( ) -- real service Names such as "ManageEngine UEMS
#  - Agent" or "MSSQL$SQLEXPRESS" were being rejected as invalid before.
#  v3.3: no functional change in this file -- version bumped only for
#  consistency across all three editions. The actual fix this version
#  ships is in the launcher .bat files (see the README).
#  v3.4: no functional change in this file either -- the actual fix this
#  version ships is in the Web edition's pcadmintool_service.py and its
#  two launcher scripts (a pywin32 exception-handling gap that could
#  never be tested on Linux, plus much more detailed diagnostics) --
#  see the Web edition's README for the full explanation.
#  v3.5: no functional change in this file -- the actual fixes this version
#  ships are in the Web edition (a false-positive in v3.4's own WindowsApps
#  detection, and Computer Management now actually launching locally instead
#  of only printing text -- this edition already did the latter correctly)
#  -- see the Web edition's README for the full explanation.
#  v3.6: eight operations were quietly LESS complete here than in the Web and
#  Python-GUI editions and are now at parity: sysmain_tune (re-enables
#  SysMain on an HDD-only PC when it is stopped), installed_sw (now includes
#  per-user installs, HKCU), startup_report (now includes the 32-bit Run key
#  and Win32_StartupCommand, which also covers Startup-folder shortcuts),
#  visual_perf (now also disables MinAnimate), sys_info (now shows CPU Speed
#  and seconds of uptime), net_stats (now shows the adapter description and
#  packet counts, and its link speed no longer throws: LinkSpeed is TEXT such
#  as 1 Gbps, so it now uses the numeric Speed property -- fixed in all three
#  editions), services_report (now also skips services whose path holds
#  SystemRoot, like the other editions), high_perf (now prints the ACTUAL active
#  power scheme afterwards instead of assuming success). The launcher
#  (Run-AdminTool.bat) is also rewritten -- see the README.
# ══════════════════════════════════════════════════════════════════════════
function ConvertTo-DottedMask([int]$n) {
    $bits=("1"*$n).PadRight(32,"0")
    $bytes=for($i=0;$i -lt 32;$i+=8){[Convert]::ToInt32($bits.Substring($i,8),2)}
    ($bytes -join ".")
}

function Test-ParamValue([string]$Kind,[string]$Raw) {
    $v=$Raw.Trim()
    switch($Kind){
        "ipv4" {
            if($v -match '^(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(\.(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])){3}$'){return @{Ok=$true;Value=$v}}
            return @{Ok=$false;Err="'$v' is not a valid IPv4 address (expected e.g. 192.168.1.100)"} }
        "subnetmask" {
            if($v -match '^\d{1,2}$' -and [int]$v -ge 0 -and [int]$v -le 32){return @{Ok=$true;Value=(ConvertTo-DottedMask ([int]$v))}}
            if($v -match '^(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(\.(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])){3}$'){return @{Ok=$true;Value=$v}}
            return @{Ok=$false;Err="'$v' is not a valid subnet mask (expected e.g. 255.255.255.0 or CIDR like 24)"} }
        "computername" {
            if($v -match '^[A-Za-z0-9]([A-Za-z0-9-]{0,13}[A-Za-z0-9])?$'){return @{Ok=$true;Value=$v}}
            return @{Ok=$false;Err="'$v' is not a valid computer name (1-15 letters/digits/hyphens, can't start/end with a hyphen)"} }
        "adaptername" {
            if($v -match '^[A-Za-z0-9 ()./#_-]{1,64}$'){return @{Ok=$true;Value=$v}}
            return @{Ok=$false;Err="'$v' contains characters not allowed in an adapter name"} }
        "servicename" {
            if($v -match '^[A-Za-z0-9 _.$#+()-]{1,256}$'){return @{Ok=$true;Value=$v}}
            return @{Ok=$false;Err="'$v' is not a valid service Name (letters, digits, spaces and _ . - `$ # + ( ) only, max 256 characters -- copy the Name exactly from 'List All Services'; it can differ from the Display Name)"} }
        "taskname" {
            if($v -match '^[A-Za-z0-9 _.\\-]{1,200}$'){return @{Ok=$true;Value=$v}}
            return @{Ok=$false;Err="'$v' contains characters not allowed in a task name"} }
        "deviceid" {
            if($v -match '^[A-Za-z0-9\\&_{}-]{1,300}$'){return @{Ok=$true;Value=$v}}
            return @{Ok=$false;Err="'$v' doesn't look like a PNP Instance ID (copy it exactly from a device list report)"} }
        "drive" {
            $d=$v.TrimEnd(":").ToUpper()
            if($d -eq ""){return @{Ok=$true;Value=""}}
            if($d -match '^[A-Za-z]$'){return @{Ok=$true;Value="$d`:"}}
            return @{Ok=$false;Err="'$v' is not a single drive letter (expected e.g. C)"} }
        "uncpath" {
            $u=$v.TrimEnd('\')
            if($u.Length -le 260 -and $u -match '^\\\\[A-Za-z0-9][A-Za-z0-9._-]{0,200}(?:\\(?!\.+(?:\\|$))[A-Za-z0-9 _.$#@&+(),~-]{1,80}){1,30}$'){return @{Ok=$true;Value=$u}}
            return @{Ok=$false;Err="'$v' is not a valid shared-folder path (expected \\server\share or \\server\share\folder -- backslashes, no quotes and none of ; | % ^ = [ ] * ?)"} }
        "mapdrive" {
            if($v -match '^[D-Zd-z]:?$'){return @{Ok=$true;Value=($v.Substring(0,1).ToUpper()+":")}}
            return @{Ok=$false;Err="'$v' is not a usable drive letter (choose D to Z -- A, B and C are reserved)"} }
        "useraccount" {
            if($v -match '^(?:(?:\.|[A-Za-z0-9][A-Za-z0-9._-]{0,62})\\)?[A-Za-z0-9_.-][A-Za-z0-9 _.-]{0,63}$' -or $v -match '^[A-Za-z0-9._-]{1,64}@[A-Za-z0-9][A-Za-z0-9.-]{0,252}$'){return @{Ok=$true;Value=$v}}
            return @{Ok=$false;Err="'$v' is not a valid Windows account (use DOMAIN\username, username@domain.com or .\localuser)"} }
        "bool" {
            $bl=$v.ToLower()
            if($bl -in @("true","1","yes","on")){return @{Ok=$true;Value='$true'}}
            if($bl -in @("false","0","no","off","")){return @{Ok=$true;Value='$false'}}
            return @{Ok=$false;Err="'$v' is not a valid true/false value"} }
        default { return @{Ok=$true;Value=$v} }
    }
}

function Show-ParamForm($OpsWithParams) {
    # $OpsWithParams: array of op hashtables (.Id, .L, .Prm). Returns
    # @{ op_id = @{ KEY = "raw text" } } or $null if the user cancelled.
    $pf=New-Object System.Windows.Forms.Form
    $pf.Text="Enter Required Values"
    $pf.Size=New-Object System.Drawing.Size(560,600)
    $pf.StartPosition="CenterParent";$pf.BackColor=$BG;$pf.ForeColor=$TXT
    $pf.FormBorderStyle="FixedDialog";$pf.MaximizeBox=$false;$pf.MinimizeBox=$false

    $panel=New-Object System.Windows.Forms.Panel
    $panel.Dock="Fill";$panel.AutoScroll=$true;$panel.BackColor=$BG;$panel.Padding=New-Object System.Windows.Forms.Padding(10)
    $pf.Controls.Add($panel)

    $btnPanel=New-Object System.Windows.Forms.Panel
    $btnPanel.Dock="Bottom";$btnPanel.Height=50;$btnPanel.BackColor=$PNL
    $pf.Controls.Add($btnPanel)
    $btnOk=New-Object System.Windows.Forms.Button
    $btnOk.Text="Run";$btnOk.DialogResult="OK";$btnOk.SetBounds(360,10,80,30)
    $btnOk.BackColor=$GRN;$btnOk.ForeColor=[System.Drawing.Color]::White;$btnOk.FlatStyle="Flat"
    $btnPanel.Controls.Add($btnOk)
    $btnCancel=New-Object System.Windows.Forms.Button
    $btnCancel.Text="Cancel";$btnCancel.DialogResult="Cancel";$btnCancel.SetBounds(450,10,80,30)
    $btnCancel.BackColor=$CRD2;$btnCancel.ForeColor=$TXT;$btnCancel.FlatStyle="Flat"
    $btnPanel.Controls.Add($btnCancel)
    $pf.AcceptButton=$btnOk;$pf.CancelButton=$btnCancel

    $y=10;$entries=@{}
    foreach($op in $OpsWithParams){
        $h=New-Object System.Windows.Forms.Label
        $h.Text=$op.L;$h.Font=GF "Segoe UI" 10 -B;$h.ForeColor=$CYAN
        $h.SetBounds(10,$y,500,22);$panel.Controls.Add($h);$y+=26
        foreach($p in $op.Prm){
            if($p.Kind -eq "bool"){
                $cb=New-Object System.Windows.Forms.CheckBox
                $cb.Text=$p.Label;$cb.ForeColor=$TXTB;$cb.Font=GF "Segoe UI" 9 -B
                $cb.SetBounds(20,$y,480,22);$cb.Checked=(-not ($p.Def -eq 'false'))
                $panel.Controls.Add($cb);$y+=24
                if($p.Help){
                    $hl=New-Object System.Windows.Forms.Label
                    $hl.Text=$p.Help;$hl.ForeColor=$TXDD;$hl.Font=GF "Segoe UI" 7
                    $hl.SetBounds(38,$y,480,16);$panel.Controls.Add($hl);$y+=18
                }
                $entries["$($op.Id)|$($p.Key)"]=@{Ctrl=$cb;Kind="bool"}
                continue
            }
            $lbl=New-Object System.Windows.Forms.Label
            $ltxt=$p.Label;if($p.Req -eq $false){$ltxt+=" (optional)"}
            $lbl.Text=$ltxt;$lbl.ForeColor=$TXDD;$lbl.Font=GF "Segoe UI" 8 -B
            $lbl.SetBounds(20,$y,500,16);$panel.Controls.Add($lbl);$y+=18
            $tb=New-Object System.Windows.Forms.TextBox
            $tb.SetBounds(20,$y,480,24);$tb.BackColor=$LOGBG;$tb.ForeColor=$TXTB;$tb.BorderStyle="FixedSingle"
            if($p.Def){$tb.Text=$p.Def}
            $panel.Controls.Add($tb);$y+=28
            if($p.Help){
                $hl=New-Object System.Windows.Forms.Label
                $hl.Text=$p.Help;$hl.ForeColor=$TXDD;$hl.Font=GF "Segoe UI" 7
                $hl.SetBounds(20,$y,480,16);$panel.Controls.Add($hl);$y+=18
            }
            $entries["$($op.Id)|$($p.Key)"]=@{Ctrl=$tb;Kind="text"}
        }
        $y+=10
    }

    $result=$pf.ShowDialog()
    if($result -ne "OK"){return $null}
    $out=@{}
    foreach($op in $OpsWithParams){
        $out[$op.Id]=@{}
        foreach($p in $op.Prm){
            $e=$entries["$($op.Id)|$($p.Key)"]
            $out[$op.Id][$p.Key]=if($e.Kind -eq "bool"){ if($e.Ctrl.Checked){"true"}else{"false"} } else { $e.Ctrl.Text }
        }
    }
    return $out
}

# RUN TASKS
$BtnRun.Add_Click({
    $sel=GetSel
    if($sel.Count -eq 0){[System.Windows.Forms.MessageBox]::Show("Select at least one task.","No Tasks");return}
    $hn=$Script:TxH.Text.Trim();$un=$Script:TxU.Text.Trim();$pw=$Script:TxP.Text;$tr=$TMAP[$Script:CbA.SelectedItem]
    if(-not $hn){[System.Windows.Forms.MessageBox]::Show("Enter hostname or IP.","Input");return}
    if(-not $un){[System.Windows.Forms.MessageBox]::Show("Enter credentials.","Input");return}
    $dsel=$sel|Where-Object{$DANGER -contains $_.Id}
    if($dsel.Count -gt 0){
        $dn=($dsel|ForEach-Object{"  * $($_.L)"}) -join "`n"
        $ans=[System.Windows.Forms.MessageBox]::Show("WARNING: $($dsel.Count) sensitive op(s):`n`n$dn`n`nSome require reboots or may interrupt network.`n`nContinue?","Confirm","YesNo","Warning")
        if($ans -ne "Yes"){return}}

    # ── Collect + validate {{KEY}} parameters for any selected op that needs them ──
    $prmOps=$sel|Where-Object{$_.ContainsKey("Prm")}
    $subs=@{}    # Id -> final substituted command text
    if($prmOps.Count -gt 0){
        $vals=Show-ParamForm $prmOps
        if($null -eq $vals){return}   # user cancelled
        $errs=@()
        foreach($op in $prmOps){
            $ct=$op.Cmd.ToString()
            foreach($p in $op.Prm){
                $raw=[string]$vals[$op.Id][$p.Key]
                if([string]::IsNullOrWhiteSpace($raw)){
                    if($p.Def){$raw=$p.Def}
                    elseif($p.Req -ne $false){$errs+="$($op.L) -> $($p.Label) is required";continue}
                    else{$ct=$ct.Replace("{{$($p.Key)}}","");continue}
                }
                $tv=Test-ParamValue $p.Kind $raw
                if(-not $tv.Ok){$errs+="$($op.L) -> $($p.Label): $($tv.Err)";continue}
                $ct=$ct.Replace("{{$($p.Key)}}",$tv.Value)
            }
            $subs[$op.Id]=$ct
        }
        if($errs.Count -gt 0){
            [System.Windows.Forms.MessageBox]::Show(("Fix these before running:`n`n"+(($errs|ForEach-Object{"  * $_"}) -join "`n")),"Invalid Parameter","OK","Error")
            return
        }
    }

    $ts2=Get-Date -Format "yyyyMMdd_HHmmss";$shn=$hn -replace "[^\w\-\.]","_"
    $Script:LogFile=Join-Path $LOGD "AdminTool_${shn}_${ts2}.log"
    $SH.Stop=$false;$SH.Done=$false;$SH.Pv=0;$SH.Pm=$sel.Count
    $BtnRun.Enabled=$false;$BtnStop.Enabled=$true;try{$PrgBar.Value=0}catch{}
    $Script:LblDot.ForeColor=$GRN;$Script:LblStat.Text="Connecting..."
    $od=$sel|ForEach-Object{
        $ctxt=if($subs.ContainsKey($_.Id)){$subs[$_.Id]}else{$_.Cmd.ToString()}
        @{Id=$_.Id;L=$_.L;Cat=$_.Cat;Ds=$_.Ds;CT=$ctxt;D=$_.D}
    }
    $SH.OD=$od;$SH.HN=$hn;$SH.UN=$un;$SH.PW=$pw;$SH.TR=$tr;$SH.LF=$Script:LogFile;$SH.CP=$COPY
    $hdrs=@("="*55,"  PC ADMIN & PERFORMANCE TOOL  v3.6 -- PowerShell Edition","  $COPYL","="*55,
       "  Target   : $hn","  Username : $un  [$tr]","  Date/Time: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")",
       "  Tasks    : $($sel.Count) selected","  Log File : $(Split-Path $Script:LogFile -Leaf)","="*55,"")
    foreach($hline in $hdrs){
        $htag="dim"
        if($hline -match "^=+$" -or $hline -match "TOOL"){$htag="hdr"}
        elseif($hline -match "^  Target|Username|Date|Tasks|Log"){$htag="info"}
        $SH.Q.Enqueue(@{T=$hline;Tag=$htag})
    }
    $Script:BgRS=[runspacefactory]::CreateRunspace()
    $Script:BgRS.ApartmentState="STA";$Script:BgRS.ThreadOptions="ReuseThread";$Script:BgRS.Open()
    $Script:BgRS.SessionStateProxy.SetVariable("sh",$SH)
    $Script:BgPS=[PowerShell]::Create();$Script:BgPS.Runspace=$Script:BgRS
    [void]$Script:BgPS.AddScript({
        $h=$sh;$ProgressPreference="SilentlyContinue";$WarningPreference="SilentlyContinue"
        try{$sec=ConvertTo-SecureString $h.PW -AsPlainText -Force
          $cred=New-Object System.Management.Automation.PSCredential($h.UN,$sec)
          $opts=New-PSSessionOption -OperationTimeout 170000 -OpenTimeout 30000 -NoMachineProfile
          $sess=New-PSSession -ComputerName $h.HN -Credential $cred -Authentication $h.TR -SessionOption $opts -EA Stop
          $h.Q.Enqueue(@{T="  Session ready -- $($h.HN)";Tag="ok"});$h.Q.Enqueue(@{T="";Tag="dim"})
        }catch{$h.Q.Enqueue(@{T="  CONNECT FAILED: $($_.Exception.Message)";Tag="err"});$h.Done=$true;return}
        $tot=$h.OD.Count;$idx=0
        foreach($op in $h.OD){
            if($h.Stop){$h.Q.Enqueue(@{T="  ! STOPPED by user";Tag="warn"});break}
            $idx++;$h.Pv=$idx;$h.Stat="[$idx/$tot] $($op.L)"
            $h.Task="[$idx/$tot] $($op.L.Substring(0,[math]::Min(42,$op.L.Length)))"
            $tpfx=""
            if($op.D){$tpfx="! "}
            $h.Q.Enqueue(@{T=">> [$idx/$tot]  $tpfx$($op.L)";Tag="task"})
            $h.Q.Enqueue(@{T="    Category: $($op.Cat)  --  $($op.Ds)";Tag="dim"})
            $h.Q.Enqueue(@{T="    "+"-"*48;Tag="dim"})

            if($op.Id -eq "rt_open_computer_management"){
                try{
                    Start-Process -FilePath "mmc.exe" -ArgumentList "compmgmt.msc","/computer:\\$($h.HN)" -EA Stop
                    $h.Q.Enqueue(@{T="    Launched Computer Management locally, connected to \\$($h.HN)";Tag="ok"})
                }catch{$h.Q.Enqueue(@{T="    Could not launch Computer Management: $($_.Exception.Message)";Tag="err"})}
                $h.Q.Enqueue(@{T="";Tag="dim"})
                continue
            }

            $t0=Get-Date
            try{
                $sb=[scriptblock]::Create('$ProgressPreference="SilentlyContinue"'+"`n"+'$WarningPreference="SilentlyContinue"'+"`n"+'$OutputEncoding=[Text.Encoding]::UTF8'+"`n"+$op.CT)
                $out=Invoke-Command -Session $sess -ScriptBlock $sb -EA Stop;$ok=$true
                if($out){foreach($line in $out){$l="$line".TrimEnd();if(-not $l){continue}
                    $lo=$l.ToLower()
                    $tag=if($lo -match "freed|cleared|complete|restarted|maintained|preserved|pass|ok"){"ok"}
                         elseif($lo -match "warn|skip|not found|already|reboot|interrupt|cannot"){"warn"}
                         elseif($lo -match "error|fail|denied|critical"){"err"}
                         else{"out"}
                    $h.Q.Enqueue(@{T="    $l";Tag=$tag})}}
                else{$h.Q.Enqueue(@{T="    ! No output -- check permissions or nothing to process";Tag="warn"})}
            }catch{
                $ok=$false;$em=$_.Exception.Message
                if($em -match "#< CLIXML|<Objs|<T>Completed"){$h.Q.Enqueue(@{T="    (non-critical PowerShell diagnostic output suppressed)";Tag="warn"})}
                elseif($em -match "AccessDenied|Access is denied"){$h.Q.Enqueue(@{T="    Access denied -- use Domain Admin account";Tag="err"})}
                elseif($em -match "timed out|timeout|cannot connect|RPC server|WinRM client"){
                    $h.Q.Enqueue(@{T="    Connection lost -- reconnecting...";Tag="warn"})
                    try{Remove-PSSession $sess -EA SilentlyContinue
                        $sess=New-PSSession -ComputerName $h.HN -Credential $cred -Authentication $h.TR -SessionOption $opts -EA Stop
                        $rt=Invoke-Command -Session $sess -ScriptBlock{"RECONNECTED"} -EA Stop
                        if($rt -eq "RECONNECTED"){$h.Q.Enqueue(@{T="    Session reconnected -- continuing";Tag="ok"})}
                    }catch{$h.Q.Enqueue(@{T="    Reconnect failed: $($_.Exception.Message)";Tag="err"})}}
                else{$h.Q.Enqueue(@{T="    Error: $em";Tag="err"})}
            }
            $el=[math]::Round(((Get-Date)-$t0).TotalSeconds,1)
            $doneTxt="Completed with errors";$doneTag="warn"
            if($ok){$doneTxt="Completed";$doneTag="ok"}
            $h.Q.Enqueue(@{T="    $doneTxt in ${el}s";Tag=$doneTag})
            $h.Q.Enqueue(@{T="";Tag="dim"})
        }
        Remove-PSSession $sess -EA SilentlyContinue
        $h.Q.Enqueue(@{T="="*55;Tag="hdr"})
        $finalTxt="ALL TASKS COMPLETED";$finalTag="ok"
        if($h.Stop){$finalTxt="STOPPED BY USER";$finalTag="warn"}
        $h.Q.Enqueue(@{T="  $finalTxt";Tag=$finalTag})
        $h.Q.Enqueue(@{T="  Finished : $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")";Tag="dim"})
        $h.Q.Enqueue(@{T="  Log: $(Split-Path $h.LF -Leaf)";Tag="dim"})
        $h.Q.Enqueue(@{T="  $($h.CP)";Tag="dim"});$h.Q.Enqueue(@{T="="*55;Tag="hdr"})
        $h.Done=$true
    })
    $Script:BgPS.BeginInvoke()|Out-Null
})

# UI POLL TIMER
$UT=New-Object System.Windows.Forms.Timer;$UT.Interval=80
$UT.Add_Tick({
    $item=$null
    while($SH.Q.TryDequeue([ref]$item)){LogIt $item.T $item.Tag}
    $pm=$SH.Pm;if($pm -lt 1){$pm=1}
    $pct=[math]::Min(100,[int](([math]::Min($SH.Pv,$pm)/$pm)*100))
    try{$PrgBar.Value=$pct}catch{}
    if($SH.Stat){$Script:LblStat.Text=$SH.Stat;$SH.Stat=""}
    if($SH.Task){$Script:LblTask.Text=$SH.Task;$SH.Task=""}
    if($SH.Done){
        $UT.Stop();$SH.Done=$false;try{$PrgBar.Value=100}catch{}
        $BtnRun.Enabled=$true;$BtnStop.Enabled=$false
        $Script:LblDot.ForeColor=$TXDD;$Script:LblTask.Text=""
        $Script:LblStat.Text=if($SH.Stop){"Stopped -- review log"}else{"All tasks completed -- log saved"}
        try{$Script:BgPS.Dispose()}catch{};try{$Script:BgRS.Close();$Script:BgRS.Dispose()}catch{}
        $Script:LogFile=$null}
})
$UT.Start()

# FORM SHOWN
$F.Add_Shown({
    $PH.SendToBack()
    $PT.SendToBack()
    $PF.SendToBack()
    $PA.SendToBack()
    $PM.BringToFront()

    $w=$PA.Width;$BtnLogs.Left=$w-104;$Script:LblCnt.Left=[math]::Max(640,$w-312)
    TabClk "all"
    LogIt "  PC Admin & Performance Tool  v3.6 -- PowerShell GUI Edition" "hdr"
    LogIt "  $COPY" "dim";LogIt ("  "+"-"*50) "dim"
    LogIt "  $($Ops.Count) operations ready across $(@($Ops | ForEach-Object { $_.Cat } | Select-Object -Unique).Count) categories" "info"
    LogIt "  Enter Hostname/IP -- Test Connection -- Select tasks -- Perform" "dim"
    LogIt "" "dim"
})

[System.Windows.Forms.Application]::Run($F)