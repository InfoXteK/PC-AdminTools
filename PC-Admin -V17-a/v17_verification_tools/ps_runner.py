RUNNER_PRE = r'''
        $NETOPS=@("flush_dns","net_reset","rt_set_static_ip","rt_set_dhcp","pr_restart_all_adapters","pr_restart_named_adapter","pr_disable_enable_adapter")
        $REBOOTOPS=@("pr_force_restart","pr_force_signout_restart","pr_full_soft_recycle","rt_rename_pc_domain","rt_rename_pc_workgroup")
        $REBOOTMARK='restarts in 15 seconds|Restarting the computer now|Forcing an immediate restart|Signing out and restarting now'
        $CONNRX='timed out|timeout|cannot connect|RPC server|WinRM client|interrupted|broken|connection.*(closed|lost)|network connection|terminated unexpectedly|disconnected|transport'
        $CONSOLEOPS=@("rt_open_computer_management","ac_open_disk_management","ac_open_device_manager","ac_open_services","ac_open_event_viewer","ac_open_shared_folders","ac_open_admin_share","ac_open_firewall","ac_open_remote_shell","ac_open_remote_cmd","ac_open_rdp")
        $fastOpts=New-PSSessionOption -OperationTimeout 20000 -OpenTimeout 10000 -NoMachineProfile
$WRAPHEAD=@'
$ErrorActionPreference = 'Continue'
$ProgressPreference = 'SilentlyContinue'
$WarningPreference = 'SilentlyContinue'
$__base = $PSCommandPath -replace '\.ps1$',''
$__o = $__base + '.out.txt'
$__d = $__base + '.done.txt'
try {
  & {
'@
$WRAPTAIL=@'

  } *>&1 | ForEach-Object { "$_" } | Out-File -FilePath $__o -Encoding utf8
} catch { ("ERROR: " + $_.Exception.Message) | Out-File -FilePath $__o -Append -Encoding utf8 }
'done' | Out-File -FilePath $__d -Encoding ascii
'@
$LAUNCHTPL=@'
$dir = Join-Path $env:windir 'Temp'
$ps1 = Join-Path $dir 'pcat_@@TOK@@.ps1'
[IO.File]::WriteAllBytes($ps1, [Convert]::FromBase64String('@@B64@@'))
$cl = 'powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + $ps1 + '"'
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cl }
if ($r.ReturnValue -eq 0) { Write-Output ('PCAT_LAUNCHED:' + $r.ProcessId) } else { Write-Output ('PCAT_LAUNCH_FAIL:' + $r.ReturnValue) }
'@
$POLLTPL=@'
$b = Join-Path (Join-Path $env:windir 'Temp') 'pcat_@@TOK@@'
if (Test-Path ($b + '.done.txt')) {
  if (Test-Path ($b + '.out.txt')) { Get-Content ($b + '.out.txt') -Raw -Encoding UTF8 }
  Write-Output 'PCAT_DONE'
} else { Write-Output 'PCAT_PENDING' }
'@
$CLEANTPL=@'
$b = Join-Path (Join-Path $env:windir 'Temp') 'pcat_@@TOK@@'
Remove-Item ($b + '.*') -Force -ErrorAction SilentlyContinue
'@
'''

RUNNER_FUNCS = r'''
        function Add-OutLines($lines){
            $cnt=0
            foreach($line in $lines){$l="$line".TrimEnd();if(-not $l){continue};$cnt++
                $lo=$l.ToLower()
                $tag=if($lo -match "freed|cleared|complete|restarted|maintained|preserved|pass|ok"){"ok"}
                     elseif($lo -match "warn|skip|not found|already|reboot|interrupt|cannot"){"warn"}
                     elseif($lo -match "error|fail|denied|critical"){"err"}
                     else{"out"}
                $h.Q.Enqueue(@{T="    $l";Tag=$tag})}
            if($cnt -eq 0){$h.Q.Enqueue(@{T="    ! No output -- check permissions or nothing to process";Tag="warn"})}
        }
        function Get-NewSession([string]$hn,$o){
            New-PSSession -ComputerName $hn -Credential $cred -Authentication $h.TR -SessionOption $o -EA Stop
        }
        function Reconnect-Normal([string[]]$hosts){
            for($n=1;$n -le 8;$n++){
                if($h.Stop){return $null}
                foreach($hn in $hosts){
                    try{
                        $s=Get-NewSession $hn $opts
                        $t=Invoke-Command -Session $s -ScriptBlock{"RECONNECTED"} -EA Stop
                        if($t -eq "RECONNECTED"){return @{S=$s;H=$hn}}
                    }catch{
                        if("$($_.Exception.Message)" -match "Access is denied|logon failure|user name or password"){return $null}
                    }
                }
                $h.Q.Enqueue(@{T="    Waiting for the target to come back... attempt $n/8";Tag="dim"})
                Start-Sleep -Seconds 4
            }
            return $null
        }
        function Invoke-Detached([string]$body,[string[]]$hosts,[int]$maxWait,$sess0){
            $tok=([guid]::NewGuid().ToString('N')).Substring(0,12)
            $wrapper=$WRAPHEAD+"`n"+$body+$WRAPTAIL
            $b64=[Convert]::ToBase64String(([byte[]](0xEF,0xBB,0xBF))+[Text.Encoding]::UTF8.GetBytes($wrapper))
            $curHost=$hosts[0]
            try{
                $lo=Invoke-Command -Session $sess0 -ScriptBlock ([scriptblock]::Create($LAUNCHTPL.Replace('@@TOK@@',$tok).Replace('@@B64@@',$b64))) -EA Stop
            }catch{return @{Ok=$false;Lines=@("  Could not start the detached task: $($_.Exception.Message)");Host=$curHost}}
            if(("$lo") -notmatch 'PCAT_LAUNCHED'){return @{Ok=$false;Lines=@("  Could not start the detached task on the target: $lo");Host=$curHost}}
            $start=Get-Date;$deadline=$start.AddSeconds($maxWait);$lastNote=$start;$interrupted=$false
            $pollSb=[scriptblock]::Create($POLLTPL.Replace('@@TOK@@',$tok))
            $ps=$null
            while((Get-Date) -lt $deadline){
                if($h.Stop){return @{Ok=$false;Lines=@("  STOPPED: the task keeps running on the target (file pcat_$tok in %windir%\Temp)");Host=$curHost}}
                if(-not $ps -or $ps.State -ne 'Opened'){
                    $ps=$null
                    foreach($hn in $hosts){try{$ps=Get-NewSession $hn $fastOpts;$curHost=$hn;break}catch{$ps=$null}}
                    if(-not $ps){
                        if(-not $interrupted){$interrupted=$true;$h.Q.Enqueue(@{T="    Connection to the target interrupted (expected for network changes) -- reconnecting...";Tag="warn"})}
                        $h.Q.Enqueue(@{T="    Waiting for the target to come back...";Tag="dim"})
                        Start-Sleep -Seconds 4;continue
                    }
                    if($interrupted){$h.Q.Enqueue(@{T="    Reconnected to $curHost.";Tag="ok"});$interrupted=$false}
                }
                try{
                    $o=Invoke-Command -Session $ps -ScriptBlock $pollSb -EA Stop
                    $txt=(($o|ForEach-Object{"$_"}) -join "`n").TrimEnd()
                    if($txt.EndsWith('PCAT_DONE')){
                        $res=$txt.Substring(0,$txt.Length-9)
                        try{Invoke-Command -Session $ps -ScriptBlock ([scriptblock]::Create($CLEANTPL.Replace('@@TOK@@',$tok))) -EA SilentlyContinue|Out-Null}catch{}
                        try{Remove-PSSession $ps -EA SilentlyContinue}catch{}
                        return @{Ok=$true;Lines=($res -split "`r?`n");Host=$curHost}
                    }
                    if(((Get-Date)-$lastNote).TotalSeconds -ge 30){$lastNote=Get-Date;$h.Q.Enqueue(@{T="    ...still running on the target ($([int]((Get-Date)-$start).TotalSeconds)s)";Tag="dim"})}
                    Start-Sleep -Seconds 3
                }catch{
                    if(-not $interrupted){$interrupted=$true;$h.Q.Enqueue(@{T="    Connection to the target interrupted (expected for network changes) -- reconnecting...";Tag="warn"})}
                    try{Remove-PSSession $ps -EA SilentlyContinue}catch{}
                    $ps=$null;Start-Sleep -Seconds 2
                }
            }
            return @{Ok=$false;Lines=@("  The target did not report completion within $maxWait s.","  The change was started on the target and has most likely been applied.","  If you changed the IP address and connected by IP, reconnect to the NEW address.");Host=$curHost}
        }
        function Open-AdminConsole([string]$id,[string]$hn,[string]$un,[string]$pw,[string]$tr){
            $m=New-Object System.Collections.ArrayList
            if($hn -notmatch '^[A-Za-z0-9][A-Za-z0-9._:-]{0,253}$'){return @("Refused: '$hn' is not a plain hostname/IP (letters, digits, . : - _ only).")}
            if($un -match '[\x00-\x1f]'){return @("Refused: the username contains control characters.")}
            $mmcTable=@{
                "rt_open_computer_management"=@("compmgmt.msc",('\\'+$hn));"ac_open_disk_management"=@("diskmgmt.msc",('\\'+$hn))
                "ac_open_device_manager"=@("devmgmt.msc",('\\'+$hn));"ac_open_services"=@("services.msc",('\\'+$hn))
                "ac_open_event_viewer"=@("eventvwr.msc",$hn);"ac_open_shared_folders"=@("fsmgmt.msc",('\\'+$hn))}
            $needIpc=$mmcTable.ContainsKey($id) -or $id -in @("ac_open_admin_share","ac_open_firewall")
            try{
                if($needIpc){
                    $r=& net.exe use ('\\'+$hn+'\IPC$') "/user:$un" $pw /persistent:no 2>&1 | Out-String
                    if($LASTEXITCODE -eq 0){[void]$m.Add("Authenticated to $hn as $un (net use IPC`$).")}
                    else{
                        $r=($r -replace [regex]::Escape($pw),'********').Trim() -replace "\s+"," "
                        if($r -match "1219"){[void]$m.Add("Windows already holds a connection to $hn under a different account (error 1219). Run  net use \\$hn\IPC`$ /delete  then try again. Detail: $r")}
                        else{[void]$m.Add("Authentication to $hn failed: $r")}
                    }
                }
                if($mmcTable.ContainsKey($id)){
                    $snap=$mmcTable[$id][0];$arg="/computer:"+$mmcTable[$id][1]
                    Start-Process -FilePath "mmc.exe" -ArgumentList $snap,$arg -EA Stop
                    [void]$m.Add("Launched: mmc.exe $snap $arg")
                    [void]$m.Add("If the console shows the LOCAL computer instead, right-click its root node > Connect to another computer > $hn.")
                    if($id -eq "ac_open_device_manager"){[void]$m.Add("Windows 8 / Server 2012 and later show remote devices read-only. For driver changes use 'Open Remote Desktop'.")}
                }elseif($id -eq "ac_open_admin_share"){
                    Start-Process -FilePath "explorer.exe" -ArgumentList ('\\'+$hn+'\C$') -EA Stop
                    [void]$m.Add("Launched: explorer \\$hn\C`$")
                }elseif($id -eq "ac_open_firewall"){
                    Start-Process -FilePath "mmc.exe" -ArgumentList "wf.msc" -EA Stop
                    [void]$m.Add("Launched Windows Firewall with Advanced Security (LOCAL view). To manage the TARGET:")
                    [void]$m.Add("  1. Right-click 'Windows Defender Firewall with Advanced Security' (top-left node)")
                    [void]$m.Add("  2. Choose 'Connect to Another Computer...'")
                    [void]$m.Add("  3. Pick 'Another computer', type $hn, OK.")
                    [void]$m.Add("(The target must allow 'Windows Defender Firewall Remote Management' inbound.)")
                }elseif($id -eq "ac_open_remote_shell"){
                    $auth=switch($tr){"Negotiate"{"Negotiate"}"Kerberos"{"Kerberos"}"Basic"{"Basic"}"Credssp"{"CredSSP"}default{"Negotiate"}}
                    $uq=$un.Replace("'","''");$hq=$hn.Replace("'","''")
                    $inner="`$u = '$uq'; `$sp = ConvertTo-SecureString `$env:PCAT_PW -AsPlainText -Force; Remove-Item Env:PCAT_PW; `$cred = New-Object System.Management.Automation.PSCredential(`$u, `$sp); Enter-PSSession -ComputerName '$hq' -Credential `$cred -Authentication $auth"
                    $env:PCAT_PW=$pw
                    try{Start-Process -FilePath "powershell.exe" -ArgumentList ('-NoExit -NoProfile -Command "'+$inner+'"') -EA Stop}finally{Remove-Item Env:PCAT_PW -EA SilentlyContinue}
                    [void]$m.Add("Launched a PowerShell window connected to $hn ($auth).")
                    [void]$m.Add("Inside it, run anything: cleanmgr /sagerun:1, defrag C: /U, netsh advfirewall show allprofiles, Get-NetAdapter ...")
                    [void]$m.Add("If it says the host is not trusted: on THIS PC run (Admin)  Set-Item WSMan:\localhost\Client\TrustedHosts -Value '$hn' -Concatenate -Force")
                }elseif($id -eq "ac_open_remote_cmd"){
                    Start-Process -FilePath "cmd.exe" -ArgumentList ("/k winrs -r:$hn `"-u:$un`" cmd") -EA Stop
                    [void]$m.Add("Launched: winrs -r:$hn -u:$un cmd  (new window).")
                    [void]$m.Add("Type the password in that window when it asks -- winrs will not take it safely any other way.")
                }elseif($id -eq "ac_open_rdp"){
                    $r=& cmdkey.exe "/generic:TERMSRV/$hn" "/user:$un" "/pass:$pw" 2>&1 | Out-String
                    if($LASTEXITCODE -eq 0){[void]$m.Add("Stored the credential for TERMSRV/$hn on this PC.")}
                    else{[void]$m.Add("Could not store the credential: "+(($r -replace [regex]::Escape($pw),'********').Trim()))}
                    Start-Process -FilePath "mstsc.exe" -ArgumentList "/v:$hn" -EA Stop
                    [void]$m.Add("Launched: mstsc /v:$hn")
                    [void]$m.Add("Inside the session you have EVERYTHING: devmgmt.msc, dfrgui, cleanmgr, wf.msc, ncpa.cpl, services.msc ...")
                    [void]$m.Add("When finished, remove the stored credential:  cmdkey /delete:TERMSRV/$hn")
                }
            }catch{[void]$m.Add("Could not launch: $($_.Exception.Message)")}
            return $m
        }
'''

RUNNER_LOOP_CONSOLE = r'''            if($rebooting){
                $h.Q.Enqueue(@{T="    Skipped: the target is restarting -- run this task again once it is back online.";Tag="warn"})
                $h.Q.Enqueue(@{T="";Tag="dim"})
                continue
            }
            if($CONSOLEOPS -contains $op.Id){
                foreach($cl in (Open-AdminConsole $op.Id $curHost $h.UN $h.PW $h.TR)){$h.Q.Enqueue(@{T="    $cl";Tag="out"})}
                $h.Q.Enqueue(@{T="";Tag="dim"})
                continue
            }
'''

RUNNER_EXEC = r'''            $t0=Get-Date
            $ok=$true;$retried=$false;$outText=""
            $preLines='$ProgressPreference="SilentlyContinue"'+"`n"+'$WarningPreference="SilentlyContinue"'+"`n"+'$OutputEncoding=[Text.Encoding]::UTF8'+"`n"
            $expReboot=($op.Id -in @("pr_force_restart","pr_force_signout_restart")) -or ($op.Id -eq "pr_full_soft_recycle" -and "$($op.PV.AUTO_RESTART)".ToLower() -notin @("false","0","no","off"))
            while($true){
                try{
                    if($NETOPS -contains $op.Id -or $op.LG){
                        $alt=@();if($op.Id -eq "rt_set_static_ip"){$nip="$($op.PV.IP)".Trim();if($nip -and $nip -ne $curHost){$alt+=$nip}}
                        if($NETOPS -contains $op.Id){$h.Q.Enqueue(@{T="    Network-changing task: running detached on the target; the tool reconnects and fetches the result.";Tag="dim"})}
                        else{$h.Q.Enqueue(@{T="    Long-running task: running detached on the target; waiting for it to finish (no 170 s limit).";Tag="dim"})}
                        $mw=if($op.LG){3600}else{300}
                        $res=Invoke-Detached ($preLines+$op.CT) (@($curHost)+$alt) $mw $sess
                        $ok=$res.Ok;$outText=($res.Lines -join "`n");Add-OutLines $res.Lines
                        if($res.Host -and $res.Host -ne $curHost){$curHost=$res.Host;$h.Q.Enqueue(@{T="    Target is now reached at $curHost.";Tag="info"})}
                        try{Remove-PSSession $sess -EA SilentlyContinue}catch{}
                        $sess=$null
                        $rc=Reconnect-Normal @($curHost)
                        if($rc){$sess=$rc.S}else{$h.Q.Enqueue(@{T="    Note: could not reopen the main session yet -- it will be retried before the next task.";Tag="warn"})}
                    }else{
                        if(-not $sess -or $sess.State -ne 'Opened'){
                            $h.Q.Enqueue(@{T="    Session not open -- reconnecting...";Tag="warn"})
                            $rc=Reconnect-Normal @($curHost)
                            if($rc){$sess=$rc.S;$h.Q.Enqueue(@{T="    Session reconnected";Tag="ok"})}else{throw "Reconnect failed -- the target did not come back in time"}
                        }
                        if($op.NC){
                            $sb=[scriptblock]::Create('param($__cred)'+"`n"+$preLines+$op.CT)
                            $out=Invoke-Command -Session $sess -ScriptBlock $sb -ArgumentList $cred -EA Stop
                        }else{
                            $sb=[scriptblock]::Create($preLines+$op.CT)
                            $out=Invoke-Command -Session $sess -ScriptBlock $sb -EA Stop
                        }
                        $ok=$true;$outText=(($out|ForEach-Object{"$_"}) -join "`n");Add-OutLines $out
                    }
                    break
                }catch{
                    $ok=$false;$em=$_.Exception.Message
                    if($em -match "#< CLIXML|<Objs|<T>Completed"){$h.Q.Enqueue(@{T="    (non-critical PowerShell diagnostic output suppressed)";Tag="warn"});break}
                    elseif($em -match "AccessDenied|Access is denied"){$h.Q.Enqueue(@{T="    Access denied -- use Domain Admin account";Tag="err"});break}
                    elseif($em -match $CONNRX){
                        if($expReboot){
                            $h.Q.Enqueue(@{T="    Connection closed because the target is restarting -- this is the expected result.";Tag="ok"})
                            $ok=$true;$rebooting=$true;$sess=$null;break
                        }
                        if(-not $retried){
                            $retried=$true
                            $h.Q.Enqueue(@{T="    Connection lost -- reconnecting...";Tag="warn"})
                            try{Remove-PSSession $sess -EA SilentlyContinue}catch{}
                            $rc=Reconnect-Normal @($curHost)
                            if($rc){$sess=$rc.S;$h.Q.Enqueue(@{T="    Session reconnected -- retrying task";Tag="ok"});continue}
                            $h.Q.Enqueue(@{T="    Reconnect failed -- the target did not come back in time";Tag="err"});$sess=$null;break
                        }
                        $h.Q.Enqueue(@{T="    Error: $em";Tag="err"});break
                    }
                    else{$h.Q.Enqueue(@{T="    Error: $em";Tag="err"});break}
                }
            }
            if($ok -and ($REBOOTOPS -contains $op.Id) -and ($outText -match $REBOOTMARK)){$rebooting=$true}
'''
