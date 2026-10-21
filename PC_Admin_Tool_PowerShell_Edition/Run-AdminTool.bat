@echo off
:: ============================================================
::  PC Admin and Performance Tool -- PowerShell GUI Edition  (v3.6)
::  Self-elevating launcher -- double-click to run
::  (c) 2024-2026 Abdullah | All Rights Reserved
::
::  v3.3: PCAdminTool.ps1 runs with its console window hidden (by
::  design -- otherwise you would see a blank PowerShell window sitting
::  behind the actual tool). That also meant that if PowerShell
::  failed to start the tool at all (a crash before the window ever
::  appears), there was previously no way to know why -- nothing
::  visible, not even a flash, and no file recording what happened.
::  Its output is now captured to a log file, and this launcher
::  checks whether it exited with an error and tells you where to
::  look, instead of just silently doing nothing.
::
::  v3.6: this file is now saved with CRLF line endings, which cmd.exe
::  needs for reliable goto and label lookup (it was LF only), and the
::  closing error report no longer sits inside a parenthesized block.
:: ============================================================
setlocal
cd /d "%~dp0"

:: Check for admin rights; if missing, relaunch elevated
net session >nul 2>&1
if %errorlevel% == 0 goto :run

echo Requesting Administrator privileges...
powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
exit /b

:run
echo ============================================================
echo   PC Admin ^& Performance Tool -- PowerShell GUI Edition
echo   Launching ^(running as Administrator^)...
echo ============================================================
del /q "%~dp0PCAdminTool_last_error.log" >nul 2>nul
powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0PCAdminTool.ps1" >"%~dp0PCAdminTool_last_error.log" 2>&1
set PCA_EXIT=%errorlevel%

if "%PCA_EXIT%"=="0" exit /b 0
echo.
echo ============================================================
echo   The tool closed with an error ^(exit code %PCA_EXIT%^) instead
echo   of opening normally.
echo   Details were saved to:
echo     "%~dp0PCAdminTool_last_error.log"
echo   Open that file in Notepad to see exactly what went wrong.
echo ============================================================
pause
exit /b %PCA_EXIT%
