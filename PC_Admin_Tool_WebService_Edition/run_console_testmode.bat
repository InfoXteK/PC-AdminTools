@echo off
:: ============================================================
::  PC Admin and Performance Tool -- Web-Service Edition  (v3.8)
::  CONSOLE / TEST MODE -- runs in the foreground for quick testing.
::  For a real background Windows Service (services.msc, auto-start
::  on boot), use install_service.bat instead.
::
::  Numbered CHECKPOINT lines run through the whole script. If this
::  window ever closes before the final "Press any key" prompt, the
::  LAST checkpoint number printed says exactly where it stopped.
::
::  v3.6: rewritten with NO parenthesized blocks. The v3.4 and v3.5
::  file had an unescaped closing parenthesis inside the dependency
::  error block, so cmd.exe hit a syntax error right after pip ran and
::  the window closed. Every failure path now jumps to a label and ends
::  at the single pause at the bottom, so the window always stays open.
:: ============================================================
setlocal enableextensions
cd /d "%~dp0"
set PCA_PORT=3030

echo ============================================================
echo   PC Admin and Performance Tool - Web Service Edition v3.8
echo   TEST MODE   ^(bundle v16, port %PCA_PORT%^)
echo ============================================================
echo [CHECKPOINT 1] Script started. Folder: "%CD%"
echo.

echo [CHECKPOINT 2] Looking for Python...
where python
if errorlevel 1 goto :fail_nopython
echo [CHECKPOINT 2 - OK] python was found. The FIRST path listed above is
echo   the one that runs; extra entries below it are normal.
echo.

echo [CHECKPOINT 3] Confirming "python" actually runs...
python --version
if errorlevel 1 goto :fail_pybroken
python -c "import sys; print('  Using: ' + sys.executable)"
echo [CHECKPOINT 3 - OK] python responded correctly, version shown above.
echo.

echo [CHECKPOINT 4] Installing/updating pip...
python -m pip install --quiet --upgrade pip
echo [CHECKPOINT 4 - OK] pip step finished ^(errorlevel %errorlevel%, informational only^).
echo.

echo [CHECKPOINT 5] Installing dependencies from requirements.txt ^(Flask, pypsrp^)...
python -m pip install --quiet -r requirements.txt
if errorlevel 1 goto :fail_deps
echo [CHECKPOINT 5 - OK] dependencies installed.
echo.

echo [CHECKPOINT 6] Checking whether port %PCA_PORT% is already busy...
call "%~dp0check_port.bat" %PCA_PORT%
echo [CHECKPOINT 6 - OK] port check finished ^(see any WARNING above^).
echo.

echo [CHECKPOINT 7] Starting app.py now.
echo ============================================================
echo   If this works, you will see Flask/Werkzeug start-up lines
echo   below, and this window will APPEAR TO STOP RESPONDING -- that
echo   is correct, it means the web server is running. Leave it open
echo   and open http://localhost:%PCA_PORT% in a browser. Press CTRL+C in
echo   THIS window to stop the server when you are done.
echo ============================================================
python app.py
set PCA_EXIT=%errorlevel%
echo.
echo [CHECKPOINT 8] app.py has exited. Exit code was: %PCA_EXIT%
if "%PCA_EXIT%"=="0" goto :end
echo.
echo ============================================================
echo   The tool stopped with an error instead of running normally.
echo   Most likely cause: this tool's own Windows Service ^(installed
echo   earlier via install_service.bat^) is ALREADY RUNNING on this
echo   same port in the background. You do not need to run this
echo   test-mode window at the same time as the service -- either
echo   open http://localhost:%PCA_PORT% directly ^(the service is already
echo   serving it^), or stop the service first with:
echo       net stop PCAdminTool
echo   and then run this file again.
echo.
echo   If that is not it, something else on this machine is using
echo   port %PCA_PORT% -- find out what with:
echo       netstat -ano ^| findstr :%PCA_PORT%
echo ============================================================
goto :end

:fail_nopython
echo.
echo [CHECKPOINT 2 - STOPPED HERE] Windows could not find "python" at all.
echo   Install Python 3.9 or later from https://www.python.org/downloads/
echo   and tick "Add Python to PATH" during setup. Then run this file again.
goto :end

:fail_pybroken
echo.
echo [CHECKPOINT 3 - STOPPED HERE] "python" did not run correctly.
echo   If the only path listed under CHECKPOINT 2 is inside WindowsApps,
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
echo   Fix the error above and run this file again.
goto :end

:end
echo.
echo ============================================================
echo   If you need help, copy everything shown in this window ^(or a
echo   screenshot of it^) exactly as it appears above this line.
echo ============================================================
pause
