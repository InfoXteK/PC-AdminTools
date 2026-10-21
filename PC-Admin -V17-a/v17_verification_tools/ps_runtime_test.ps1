param([string]$File)
$ErrorActionPreference='Continue'
$tok=$null;$err=$null
$ast=[System.Management.Automation.Language.Parser]::ParseFile($File,[ref]$tok,[ref]$err)
$call=$ast.FindAll({param($n) $n -is [System.Management.Automation.Language.InvokeMemberExpressionAst] -and $n.Member.Value -eq 'AddScript' -and $n.Extent.Text -match 'in \$h\.OD'},$true)|Select-Object -First 1
$inner=$call.Arguments[0].ScriptBlock.Extent.Text
$inner=$inner.Substring(1,$inner.Length-2)
$runner=[scriptblock]::Create($inner)

$script:down=0;$script:pend=2;$script:log=@();$script:launched=$null;$script:pwSeen=$false
function Start-Sleep { param($Seconds,$Milliseconds) }
function New-PSSessionOption { @{} }
function Remove-PSSession { param($Session) }
function New-PSSession { param($ComputerName,$Credential,$Authentication,$SessionOption,$ErrorAction)
  if($script:down -gt 0 -and $ComputerName -eq '10.0.0.5'){ $script:down--; throw "The network connection to $ComputerName has been interrupted." }
  [pscustomobject]@{State='Opened';ComputerName=$ComputerName} }
function Invoke-Command { param($Session,$ScriptBlock,$ArgumentList,$ErrorAction)
  $t=$ScriptBlock.ToString(); $script:log+=$t
  if($t -match 'PCAT_LAUNCHED'){ $m=[regex]::Match($t,"FromBase64String\('([^']+)'\)"); $bytes=[Convert]::FromBase64String($m.Groups[1].Value); $script:launched=[Text.Encoding]::UTF8.GetString($bytes); $script:down=3; return 'PCAT_LAUNCHED:99' }
  if($t -match 'PCAT_PENDING'){ if($script:down -gt 0){$script:down--; throw 'The network connection has been interrupted.'}; if($script:pend -gt 0){$script:pend--;return 'PCAT_PENDING'}; return @('  Flushed DNS','  Done','PCAT_DONE') }
  if($t -match 'Remove-Item \(\$b'){ return }
  if($t -match 'RECONNECTED'){ return 'RECONNECTED' }
  if($t -match 'shutdown\.exe /r /f /t 3'){ throw 'The WS-Management service cannot process the request. The network connection to host was closed (broken).' }
  if($t -match 'Rename-Computer'){ if($ArgumentList -and $ArgumentList[0].UserName -eq 'corp\bob'){ $script:pwSeen=($ArgumentList[0].GetNetworkCredential().Password -eq "S3cret'pw") }; return @('  Rename submitted -- target restarts in 15 seconds') }
  return @('  generic ok')
}
function Start-Process { param($FilePath,$ArgumentList,$ErrorAction) $script:log+="START $FilePath $ArgumentList" }
function net.exe { $script:log+="NET $($args -join ' ')"; $global:LASTEXITCODE=0 }
function cmdkey.exe { $script:log+="CMDKEY $($args -join ' ')"; $global:LASTEXITCODE=0 }

# pull op defs from the real file by dot-sourcing only the $Ops array region
$opsStart=$ast.FindAll({param($n) $n -is [System.Management.Automation.Language.AssignmentStatementAst] -and $n.Left.Extent.Text -eq '$Ops'},$true)|Select-Object -First 1
. ([scriptblock]::Create($opsStart.Extent.Text))
"Ops loaded: $($Ops.Count)"
function MkOd($ids,$pv){ foreach($id in $ids){ $o=$Ops|Where-Object{$_.Id -eq $id}; $ct=$o.Cmd.ToString(); if($o.ContainsKey('Prm')){ foreach($p in $o.Prm){ $v=if($pv.ContainsKey($p.Key)){$pv[$p.Key]}else{$p.Def}; $ct=$ct.Replace("{{$($p.Key)}}",$(if($p.Kind -eq 'bool'){if($v -eq 'false'){'$false'}else{'$true'}}else{$v})) } }
  @{Id=$o.Id;L=$o.L;Cat=$o.Cat;Ds=$o.Ds;CT=$ct;D=$o.D;NC=[bool]$o.NC;LG=[bool]$o.LG;PV=$pv} } }
function RunIt($od){
  $sh=[hashtable]::Synchronized(@{Q=[System.Collections.Concurrent.ConcurrentQueue[hashtable]]::new();Stop=$false;Done=$false;Pv=0;Pm=1;Stat="";Task=""})
  $sh.OD=$od;$sh.HN='10.0.0.5';$sh.UN='corp\bob';$sh.PW="S3cret'pw";$sh.TR='Negotiate';$sh.LF='x.log';$sh.CP='c'
  & $runner
  $lines=@();$it=$null;while($sh.Q.TryDequeue([ref]$it)){$lines+=$it.T}
  ,$lines }
$fails=@()
function Check($n,$c){ if($c){"PASS $n"}else{"FAIL $n";$script:fails+=$n} }
$sh=$null
$l=RunIt @(MkOd @('flush_dns') @{})
$txt=$l -join "`n"
Check 'blip: real output returned' ($txt -match 'Flushed DNS')
Check 'blip: interruption announced + reconnected' ($txt -match 'interrupted' -and $txt -match 'Reconnected')
Check 'blip: wrapper uploaded w/ body' ($script:launched -match 'ipconfig' -and $script:launched -match 'done.txt')
$script:down=0;$script:pend=2
$l=RunIt @((MkOd @('pr_force_restart','rt_vss_view') @{}))
$txt=$l -join "`n"
Check 'reboot op: expected result' ($txt -match 'expected result')
Check 'task after reboot skipped' ($txt -match 'Skipped: the target is restarting')
$l=RunIt @((MkOd @('rt_rename_pc_domain','rt_vss_view') @{rt_rename_pc_domain=@{NEW_NAME='PC-X';AUTO_RESTART='true'}}))
$txt=$l -join "`n"
Check 'rename: credential passed via ArgumentList' $script:pwSeen
Check 'rename: reboot flagged -> next skipped' ($txt -match 'Skipped')
Check 'password not in any output line' ($txt -notmatch 'S3cret')
Check 'password not in any remote script text' (($script:log -join "`n") -notmatch 'S3cret')
$script:log=@()
$l=RunIt @((MkOd @('ac_open_rdp','ac_open_remote_shell','ac_open_services') @{}))
$txt=$l -join "`n"
Check 'consoles: no pw in output' ($txt -notmatch 'S3cret')
Check 'consoles: mmc launched' (($script:log -join "`n") -match 'START mmc.exe services.msc /computer:\\\\10.0.0.5')
Check 'consoles: shell uses env not argv' (($script:log -join "`n") -notmatch 'START powershell.exe.*S3cret')
$l=RunIt @((MkOd @('rt_vss_resize_storage') @{rt_vss_resize_storage=@{VOLUME='C';MAXSIZE='10%'}}))
Check 'vss resize op runs' (($l -join "`n") -match 'generic ok')
"FAILS: $($fails -join '; ')"
if($fails.Count){exit 1}
