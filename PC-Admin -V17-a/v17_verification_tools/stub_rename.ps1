param($Script,$Mode)
$script:mode=$Mode
function Get-CimInstance { param($ClassName) [pscustomobject]@{Name='PC1-CSD';PartOfDomain=($script:mode -notlike 'wg*');Domain='corpdomain.local'} }
function Rename-Computer { param($NewName,$DomainCredential,[switch]$Force,$ErrorAction) if($script:mode -eq 'dom-m1fail'-or $script:mode -eq 'dom-allfail'){ throw 'Access is denied.' }; if($DomainCredential -and $DomainCredential.UserName -ne 'corp\bob'){throw 'wrong cred'} }
function Invoke-CimMethod { param($InputObject,$MethodName,$Arguments,$ErrorAction) if($script:mode -eq 'dom-allfail'){ [pscustomobject]@{ReturnValue=2224} } else { [pscustomobject]@{ReturnValue=0} } }
function Test-ComputerSecureChannel { $true }
function shutdown.exe { Write-Output "SHUTDOWN-CALLED $args" }
function Get-Command { param($n,$ErrorAction) if($script:mode -eq 'wg-wmic'){ 'wmic' } else { $null } }
function wmic { 'ReturnValue = 0' }
. $Script
