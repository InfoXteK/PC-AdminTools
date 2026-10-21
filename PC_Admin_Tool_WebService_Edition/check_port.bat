@echo off
:: ============================================================
::  PC Admin and Performance Tool -- advisory port check  (v3.7)
::  Usage: check_port.bat PORT
::  Prints a WARNING if the TCP port is already listening, or if
::  Windows has reserved it (Hyper-V / WinNAT excluded port range).
::  ADVISORY ONLY -- always exits 0, never blocks an install.
::
::  v3.6: rewritten with NO parenthesized blocks. The v3.3 to v3.5
::  file had an unescaped closing parenthesis inside a block. cmd.exe
::  reads that as the END of the block, which is a syntax error found
::  when the block is PARSED, even if its condition is false. That
::  aborts the whole batch run, and a double-clicked window closes.
:: ============================================================
setlocal
set "CHK=%~1"
if "%CHK%"=="" exit /b 0

netstat -ano -p tcp | findstr /R /C:":%CHK% .*LISTENING" >nul 2>nul
if errorlevel 1 goto :chk_reserved
echo.
echo *** WARNING: TCP port %CHK% is ALREADY IN USE by another program on this machine. ***
echo     See which one:  netstat -ano ^| findstr :%CHK%
echo     If it is not an old copy of this tool, tell Claude "port %CHK% is taken"
echo     so the next version skips to the following port.
echo.

:chk_reserved
powershell -NoProfile -Command "$p=%CHK%; $hit=$false; foreach($l in (netsh int ipv4 show excludedportrange protocol=tcp)){ if($l -match '^\s*(\d+)\s+(\d+)'){ if($p -ge [int]$Matches[1] -and $p -le [int]$Matches[2]){$hit=$true} } }; if($hit){exit 3}else{exit 0}" >nul 2>nul
if not "%errorlevel%"=="3" goto :chk_done
echo.
echo *** WARNING: Windows has RESERVED TCP port %CHK% ^(Hyper-V / WinNAT excluded port range^). ***
echo     Show the reserved ranges:  netsh int ipv4 show excludedportrange protocol=tcp
echo     Tell Claude "port %CHK% is reserved" so the next version skips to the following port.
echo.

:chk_done
exit /b 0
