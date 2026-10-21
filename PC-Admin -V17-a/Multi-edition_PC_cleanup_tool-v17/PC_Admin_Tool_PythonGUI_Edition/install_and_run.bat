@echo off
:: ============================================================
::  PC Admin and Performance Tool -- Native Python GUI Edition  (v3.7)
::  Double-click to install dependencies and launch the GUI.
::
::  v3.6: rewritten with NO parenthesized blocks and saved with CRLF
::  line endings. The v3.3 to v3.5 file had an unescaped closing
::  parenthesis inside the dependency-error block, which cmd.exe treats
::  as the end of that block: a syntax error found while PARSING it, so
::  the launcher stopped right after pip ran, on every start. The title
::  line also had an unescaped ampersand, which cmd runs as a second
::  command and reports as an error on every launch.
:: ============================================================
title PC Admin ^& Performance Tool - Native Python GUI Edition
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 goto :fail_nopython

echo Installing/updating dependencies ^(pypsrp^)...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt
if errorlevel 1 goto :fail_deps

:: v3.3: confirm both pieces this GUI needs actually import correctly BEFORE
:: attempting to launch it. The launch line below uses pythonw, which has no
:: console window at all by design -- if the launch itself failed silently
:: for a reason NOT caught here, nothing would ever tell you why, so this
:: check exists to catch the common cases (missing Tkinter, a dependency
:: that failed to install) up front, where a clear message can still reach you.
python -c "import tkinter, pypsrp" 2>nul
if errorlevel 1 goto :fail_import

echo Launching PC Admin ^& Performance Tool...
del /q "%~dp0PCAdminTool_last_error.log" >nul 2>nul
start "" pythonw "PCAdminTool.pyw" 2>"%~dp0PCAdminTool_last_error.log"
echo If the window does not appear within a few seconds, check
echo PCAdminTool_last_error.log in this folder for details.
exit /b 0

:fail_nopython
echo ============================================================
echo   Python was not found on this machine.
echo   Install Python 3.9+ from https://www.python.org/downloads/
echo   and make sure to tick "Add Python to PATH" during setup.
echo ============================================================
pause
exit /b 1

:fail_deps
echo.
echo ============================================================
echo   DEPENDENCY INSTALL FAILED -- showing the full error below.
echo ============================================================
python -m pip install -r requirements.txt
echo ============================================================
echo   Fix the error above ^(often: no internet access, or a
echo   company proxy blocking pip^) and re-run this file.
echo ============================================================
pause
exit /b 1

:fail_import
echo ============================================================
echo   Cannot start -- Tkinter or pypsrp did not import correctly.
echo   Showing the exact error below:
echo ============================================================
python -c "import tkinter, pypsrp"
echo ============================================================
echo   If this mentions Tkinter: reinstall Python from
echo   https://www.python.org/downloads/ using the official
echo   installer ^(Tkinter is included there by default^).
echo   If this mentions pypsrp: re-run this file to retry the
echo   dependency install above.
echo ============================================================
pause
exit /b 1
