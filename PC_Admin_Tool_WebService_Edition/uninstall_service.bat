@echo off
:: ============================================================
::  PC Admin and Performance Tool -- uninstall the Windows Service  (v3.8)
::
::  v3.6: rewritten with NO parenthesized blocks, and the firewall
::  cleanup now also covers port 3030.
:: ============================================================
setlocal enableextensions
cd /d "%~dp0"

net session >nul 2>&1
if %errorlevel%==0 goto :is_admin
echo Requesting Administrator privileges...
powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
exit /b

:is_admin
echo Stopping service ^(if running^)...
net stop PCAdminTool >nul 2>nul

echo Removing service...
python pcadmintool_service.py remove

echo.
echo Removing firewall rules ^(every port this tool has ever used^)...
for %%P in (3030 3031 3032 3033 3034 3035 3036 3037 3038 3030) do netsh advfirewall firewall delete rule name="PC Admin Tool %%P" >nul 2>nul

echo Done. The service has been removed from services.msc.
pause
