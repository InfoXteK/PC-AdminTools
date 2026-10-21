#!/usr/bin/env python3
"""
================================================================================
  PC Admin & Performance Tool -- Web-Service Edition
  Windows Service wrapper (installs into services.msc as "PCAdminTool")
  (c) 2024-2026 Abdullah | All Rights Reserved
================================================================================
Usage (run from an elevated Command Prompt, in this folder):

    python pcadmintool_service.py install      Install the service
    python pcadmintool_service.py start        Start it
    python pcadmintool_service.py stop         Stop it
    python pcadmintool_service.py remove       Uninstall it
    python pcadmintool_service.py --startup=auto install
                                                Install with auto-start on boot

Once installed, it shows up in services.msc as:
    "PC Admin & Performance Tool - Web Service"
and stays running (and restarts on reboot, if installed with --startup=auto)
without any console window open. Logs and files remain on this host under
the "logs" folder next to app.py.

(install_service.bat in this package runs the two commands above for you.)
"""
import sys
import os
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import win32serviceutil
import win32service
import win32event
import servicemanager

SERVICE_PORT = 3030


class PCAdminToolService(win32serviceutil.ServiceFramework):
    _svc_name_ = "PCAdminTool"
    _svc_display_name_ = "PC Admin & Performance Tool - Web Service"
    _svc_description_ = (
        "Hosts the PC Admin & Performance Tool web UI on port %d, reachable "
        "from any host on the allowed subnet. Logs are written locally to "
        "the 'logs' folder next to app.py." % SERVICE_PORT
    )

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.server = None
        self.running = True

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.running = False
        try:
            if self.server is not None:
                self.server.shutdown()
        except Exception:
            pass
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, f" starting on port {SERVICE_PORT}"),
        )
        try:
            self.main()
        except Exception as e:
            servicemanager.LogErrorMsg(f"PCAdminTool service crashed: {e}")

    def main(self):
        # IMPORTANT: this tool streams live task output to the browser over
        # Server-Sent Events (SSE). Werkzeug's threaded server flushes each
        # chunk immediately, which SSE needs. waitress buffers responses
        # before sending, which makes the web UI look "stuck" after you
        # click Run -- so we deliberately do NOT use waitress here.
        from werkzeug.serving import make_server
        from app import app  # noqa: local import, uses app.py in this folder

        self.server = make_server("0.0.0.0", SERVICE_PORT, app, threaded=True)

        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, f" listening on 0.0.0.0:{SERVICE_PORT}"),
        )
        t = threading.Thread(target=self.server.serve_forever, daemon=True)
        t.start()

        win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(PCAdminToolService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        # v3.4: HandleCommandLine used to be called bare. install_service.bat
        # unconditionally calls "remove" (and net-stops the service) BEFORE
        # every install, as pre-install cleanup -- including the very first
        # install, when there is nothing installed yet to remove. Depending
        # on the pywin32 version, "remove"/"stop" on a service that was
        # never installed can raise an uncaught pywintypes/win32 exception
        # instead of printing a friendly message and returning cleanly. This
        # could never be tested on Linux (pywin32 does not exist there), so
        # it shipped untested; this is the most likely cause of
        # install_service.bat closing right after printing the "Removing
        # any previous version..." line, since that exception's traceback
        # was ALSO being hidden by ">nul 2>nul" in the batch file. Both are
        # fixed together: real errors here (remove/stop specifically) are
        # now caught and reported as an expected, harmless note rather than
        # a crash, and the batch file no longer hides this command's output.
        # A genuine failure of "install" or any other command still exits
        # non-zero as before, so install_service.bat's own error checking
        # on THAT command is unaffected.
        cmd = sys.argv[1].lower() if len(sys.argv) > 1 else ""
        try:
            win32serviceutil.HandleCommandLine(PCAdminToolService)
        except SystemExit:
            raise
        except Exception as e:
            if cmd in ("remove", "stop"):
                print(f"NOTE ({cmd}): {e}")
                print(f"(expected and harmless if the service was not installed or running yet)")
                sys.exit(0)
            print(f"ERROR ({cmd}): {e}")
            sys.exit(1)
