# Shared definition of the three rename operations (Web edition text).
HINTS = r'''
$hint = {
    param($c)
    switch ([string]$c) {
        '5'    { 'Access denied: the account you connected with is not allowed to rename this computer object in AD (needs Domain Admin or delegated "rename computer" rights), or is not a local admin on the target.' }
        '53'   { 'Network path not found: the target cannot reach a domain controller (check DNS / VPN / firewall on the target).' }
        '87'   { 'Invalid parameter: the new name is not accepted (NetBIOS rules: max 15 chars, letters/digits/hyphen).' }
        '1326' { 'Logon failure: the username/password you connected with was rejected by the domain controller.' }
        '1355' { 'The domain, or a domain controller for it, could not be contacted from the target (DNS).' }
        '1909' { 'That account is locked out.' }
        '2224' { 'A computer account with the NEW name already exists in AD -- pick a different name or delete the stale account first.' }
        '2691' { 'The computer is already joined to that name/domain.' }
        default { "Win32 code $c." }
    }
}
'''

RESTART_TAIL = r'''
if ($done) {
    if ($autoRestart) {
        shutdown.exe /r /t 15 /c "PC Admin Tool: computer rename to $newName" | Out-Null
        Write-Output "  Rename submitted -- target restarts in 15 seconds (the session will drop; that is expected)."
    } else {
        Write-Output "  Rename submitted -- Auto-Restart is OFF. The new name will NOT take effect until"
        Write-Output "  this computer restarts -- run 'Force Restart Now' (Power Recycle) when ready."
    }
}
'''

DOMAIN = HINTS + r'''
$newName = "{{NEW_NAME}}"
$autoRestart = {{AUTO_RESTART}}
$cs = Get-CimInstance Win32_ComputerSystem
Write-Output "  Current name : $($cs.Name)"
Write-Output "  Renaming to  : $newName"
Write-Output "  Membership   : $(if ($cs.PartOfDomain) { 'DOMAIN ' + $cs.Domain } else { 'WORKGROUP ' + $cs.Domain })"
if (-not $cs.PartOfDomain) {
    Write-Output "  This target is NOT domain-joined -- use 'Rename Computer (Workgroup/Local)' instead. Nothing was changed."
    return
}
if ($cs.Name -ieq $newName) { Write-Output "  Computer is already named $newName -- nothing to do."; return }
Write-Output "  Using the username/password you connected with as an explicit DOMAIN credential"
Write-Output "  (built on the target, so no CredSSP / double-hop is needed)."
$done = $false
try {
    Rename-Computer -NewName $newName -DomainCredential $__cred -Force -ErrorAction Stop
    $done = $true
    Write-Output "  Method 1 (Rename-Computer -DomainCredential) succeeded."
} catch {
    Write-Output "  Method 1 failed: $($_.Exception.Message)"
}
if (-not $done) {
    try {
        $r = Invoke-CimMethod -InputObject (Get-CimInstance Win32_ComputerSystem) -MethodName Rename -Arguments @{ Name = $newName; UserName = $__cred.UserName; Password = $__cred.GetNetworkCredential().Password } -ErrorAction Stop
        if ($r.ReturnValue -eq 0) { $done = $true; Write-Output "  Method 2 (WMI Win32_ComputerSystem.Rename) succeeded." }
        else { Write-Output "  Method 2 failed, code $($r.ReturnValue): $(& $hint $r.ReturnValue)" }
    } catch {
        Write-Output "  Method 2 failed: $($_.Exception.Message)"
    }
}
if (-not $done) {
    Write-Output "  Rename FAILED -- nothing was changed."
    Write-Output "  Check: (1) the account is Domain Admin / has rename rights on the computer object,"
    Write-Output "         (2) the target can resolve + reach a domain controller,"
    Write-Output "         (3) no AD computer account with the new name already exists."
    try { Write-Output "  Secure channel to domain: $(Test-ComputerSecureChannel)" } catch { Write-Output "  Secure channel test could not run: $($_.Exception.Message)" }
}
''' + RESTART_TAIL

WORKGROUP = HINTS + r'''
$newName = "{{NEW_NAME}}"
$autoRestart = {{AUTO_RESTART}}
$cs = Get-CimInstance Win32_ComputerSystem
Write-Output "  Current name : $($cs.Name)"
Write-Output "  Renaming to  : $newName"
Write-Output "  Membership   : $(if ($cs.PartOfDomain) { 'DOMAIN ' + $cs.Domain } else { 'WORKGROUP ' + $cs.Domain })"
if ($cs.PartOfDomain) {
    Write-Output "  This target IS joined to domain $($cs.Domain). A local-only rename would leave its AD computer"
    Write-Output "  account out of sync and can break domain logon -- use 'Rename Computer (Domain-Joined)'. Nothing was changed."
    return
}
if ($cs.Name -ieq $newName) { Write-Output "  Computer is already named $newName -- nothing to do."; return }
$done = $false
try {
    Rename-Computer -NewName $newName -Force -ErrorAction Stop
    $done = $true
    Write-Output "  Method 1 (Rename-Computer) succeeded."
} catch {
    Write-Output "  Method 1 failed: $($_.Exception.Message)"
}
if (-not $done) {
    try {
        $r = Invoke-CimMethod -InputObject (Get-CimInstance Win32_ComputerSystem) -MethodName Rename -Arguments @{ Name = $newName } -ErrorAction Stop
        if ($r.ReturnValue -eq 0) { $done = $true; Write-Output "  Method 2 (WMI Win32_ComputerSystem.Rename) succeeded." }
        else { Write-Output "  Method 2 failed, code $($r.ReturnValue): $(& $hint $r.ReturnValue)" }
    } catch {
        Write-Output "  Method 2 failed: $($_.Exception.Message)"
    }
}
if (-not $done) {
    Write-Output "  Rename FAILED -- nothing was changed."
    Write-Output "  If you connected with a LOCAL (non-domain) admin account that is not the built-in Administrator,"
    Write-Output "  Windows remote UAC filtering blocks this. Fix on the target (Admin PowerShell):"
    Write-Output "    reg add HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System /v LocalAccountTokenFilterPolicy /t REG_DWORD /d 1 /f"
}
''' + RESTART_TAIL

LEGACY = HINTS + r'''
$newName = "{{NEW_NAME}}"
$cs = Get-CimInstance Win32_ComputerSystem
Write-Output "  Current name : $($cs.Name)"
Write-Output "  Renaming to  : $newName"
Write-Output "  Membership   : $(if ($cs.PartOfDomain) { 'DOMAIN ' + $cs.Domain } else { 'WORKGROUP ' + $cs.Domain })"
if ($cs.Name -ieq $newName) { Write-Output "  Computer is already named $newName -- nothing to do."; return }
$wmic = Get-Command wmic.exe -ErrorAction SilentlyContinue
$done = $false
if ($wmic -and -not $cs.PartOfDomain) {
    Write-Output "  wmic.exe found -- using it (workgroup target)."
    $result = wmic computersystem where "name='$env:COMPUTERNAME'" call rename name="$newName" 2>&1
    $result | ForEach-Object { Write-Output "  $_" }
    if (($result | Out-String) -match 'ReturnValue = 0') { $done = $true }
} else {
    if (-not $wmic) { Write-Output "  wmic.exe is not present on this target (removed in Windows 11 24H2+) -- using the same WMI method through CIM instead." }
    else { Write-Output "  Domain-joined target: using the WMI rename method via CIM with your credentials (avoids putting a password on a wmic command line)." }
    try {
        if ($cs.PartOfDomain) { $args2 = @{ Name = $newName; UserName = $__cred.UserName; Password = $__cred.GetNetworkCredential().Password } }
        else { $args2 = @{ Name = $newName } }
        $r = Invoke-CimMethod -InputObject (Get-CimInstance Win32_ComputerSystem) -MethodName Rename -Arguments $args2 -ErrorAction Stop
        if ($r.ReturnValue -eq 0) { $done = $true; Write-Output "  WMI Win32_ComputerSystem.Rename succeeded." }
        else { Write-Output "  WMI rename failed, code $($r.ReturnValue): $(& $hint $r.ReturnValue)" }
    } catch {
        Write-Output "  WMI rename failed: $($_.Exception.Message)"
    }
}
if ($done) { Write-Output "  Rename submitted -- this does NOT auto-restart. Run 'Force Restart Now' (Power Recycle) when ready." }
else { Write-Output "  Rename FAILED -- nothing was changed." }
'''
