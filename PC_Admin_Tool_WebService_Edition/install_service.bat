@echo off
:: ============================================================
::  PC Admin and Performance Tool -- Web-Service Edition  (v3.7)
::  Installs and starts a REAL Windows Service (visible in
::  services.msc, auto-starts on boot). Windows / Windows Server.
::  (c) 2024-2026 Abdullah | All Rights Reserved
::
::  Numbered CHECKPOINT lines run through the whole script. If this
::  window ever closes before the final "Press any key" prompt, the
::  LAST checkpoint number printed says exactly where it stopped.
::
::  v3.6: rewritten with NO parenthesized blocks. cmd.exe treats any
::  unescaped closing parenthesis inside a block as the end of that
::  block, which is a syntax error found while the block is PARSED and
::  closes a double-clicked window with no message. The port-check
::  script this file calls had exactly that defect since v3.3, which is
::  why the window closed right after the cleanup step. Every failure
::  path now jumps to a label and ends at the single pause at the bottom.
:: ============================================================
setlocal enableextensions
cd /d "%~dp0"
set PCA_PORT=3038

echo ============================================================
echo   PC Admin and Performance Tool - Web Service Edition v3.7
echo   INSTALLER   ^(bundle v16, port %PCA_PORT%^)
echo ============================================================
echo [CHECKPOINT 1] Script started. Folder: "%CD%"
echo.

echo [CHECKPOINT 2] Checking for Administrator rights...
net session >nul 2>&1
if %errorlevel%==0 goto :is_admin
echo [CHECKPOINT 2 - NOT ELEVATED] Requesting Administrator privileges...
echo   A new elevated window should open now. If a User Account
echo   Control prompt appears, click Yes. If nothing happens, run
echo   this file yourself as Administrator instead
echo   ^(right-click it -^> "Run as administrator"^).
powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
exit /b

:is_admin
echo [CHECKPOINT 2 - OK] running as Administrator.
echo.

echo [CHECKPOINT 3] Looking for Python...
where python
if errorlevel 1 goto :fail_nopython
echo [CHECKPOINT 3 - OK] python was found. The FIRST path listed above is
echo   the one that runs; extra entries below it are normal.
echo.

echo [CHECKPOINT 4] Confirming "python" actually runs...
python --version
if errorlevel 1 goto :fail_pybroken
python -c "import sys; print('  Using: ' + sys.executable)"
echo [CHECKPOINT 4 - OK] python responded correctly, version shown above.
echo.

echo [CHECKPOINT 5] Installing dependencies ^(Flask, pypsrp, pywin32^)...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt
if errorlevel 1 goto :fail_deps
echo [CHECKPOINT 5 - OK] dependencies installed.
echo.

echo [CHECKPOINT 6] Running pywin32's one-time post-install step...
python -m pywin32_postinstall -install
echo [CHECKPOINT 6 - OK] step finished ^(errorlevel %errorlevel%, informational only^).
echo.

echo [CHECKPOINT 7] Removing any previous version of this service, if one exists...
echo   ^(A message saying the service was not found or not running below
echo   is completely normal and expected on a first-ever install.^)
net stop PCAdminTool
python pcadmintool_service.py remove
for %%P in (3030 3031 3032 3033 3034 3035 3036 3037 3038) do netsh advfirewall firewall delete rule name="PC Admin Tool %%P" >nul 2>nul
echo [CHECKPOINT 7 - OK] cleanup step finished.
echo.

echo [CHECKPOINT 8] Checking whether port %PCA_PORT% is already busy...
call "%~dp0check_port.bat" %PCA_PORT%
echo [CHECKPOINT 8 - OK] port check finished ^(see any WARNING above^).
echo.

echo [CHECKPOINT 9] Opening inbound firewall rule for TCP port %PCA_PORT%...
netsh advfirewall firewall add rule name="PC Admin Tool %PCA_PORT%" dir=in action=allow protocol=TCP localport=%PCA_PORT%
echo [CHECKPOINT 9 - OK] firewall rule step finished.
echo.

echo [CHECKPOINT 10] Registering the Windows Service ^(auto-start on boot^)...
python pcadmintool_service.py --startup=auto install
if errorlevel 1 goto :fail_install
echo [CHECKPOINT 10 - OK] service registered.
echo.

echo [CHECKPOINT 11] Starting the service...
net start PCAdminTool
echo [CHECKPOINT 11 - OK] start command finished ^(see above for its result^).

echo.
echo ============================================================
echo   Service installed:  "PC Admin & Performance Tool - Web Service"  ^(v3.7^)
echo   Check it in services.msc -- it will keep running in the
echo   background and restart automatically on reboot.
echo   Web UI ^(from any host on this subnet^): http://%COMPUTERNAME%:%PCA_PORT%
echo   On this machine: http://localhost:%PCA_PORT%
echo ============================================================
goto :end

:fail_nopython
echo.
echo [CHECKPOINT 3 - STOPPED HERE] Windows could not find "python" at all.
echo   Install Python 3.9 or later from https://www.python.org/downloads/
echo   and tick "Add Python to PATH" during setup. Then run this file again.
goto :end

:fail_pybroken
echo.
echo [CHECKPOINT 4 - STOPPED HERE] "python" did not run correctly.
echo   If the only path listed under CHECKPOINT 3 is inside WindowsApps,
echo   that is a placeholder Windows puts there by default -- it does
echo   nothing. Install real Python from https://www.python.org/downloads/
echo   and make sure it comes before anything else named python on your
echo   PATH, then run this file again.
goto :end

:fail_deps
echo.
echo [CHECKPOINT 5 - STOPPED HERE] Dependency install failed. Full error:
echo ============================================================
python -m pip install -r requirements.txt
echo ============================================================
echo   Common causes: no internet access, a company proxy blocking pip,
echo   or a WindowsApps-only Python placeholder instead of a real Python.
echo   Fix the error above and re-run this file.
goto :end

:fail_install
echo.
echo [CHECKPOINT 10 - STOPPED HERE] Service registration failed -- see
echo   the error above for exactly why.
goto :end

:end
echo.
echo ============================================================
echo   If you need help, copy everything shown in this window ^(or a
echo   screenshot of it^) exactly as it appears above this line.
echo ============================================================
pause
