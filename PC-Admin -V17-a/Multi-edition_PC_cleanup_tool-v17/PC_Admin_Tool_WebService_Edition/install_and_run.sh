#!/usr/bin/env bash
# ============================================================
#  PC Admin & Performance Tool -- Web-Service Edition
#  Installs dependencies and starts the service on port 3030
#  (c) 2024-2026 Abdullah | All Rights Reserved
# ============================================================
set -e
cd "$(dirname "$0")"

PY=$(command -v python3 || true)
if [ -z "$PY" ]; then
    echo "python3 was not found. Install Python 3.9+ (e.g. sudo apt install python3 python3-venv python3-pip) and re-run this script."
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    "$PY" -m venv .venv
fi
source .venv/bin/activate

echo "Installing/updating dependencies (Flask, pypsrp)..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

if command -v ss >/dev/null 2>&1 && ss -ltn 2>/dev/null | awk '{print $4}' | grep -qE '[:.]3030$'; then
    echo ""
    echo "*** WARNING: TCP port 3030 is already in use on this machine -- the service cannot start until it is free. ***"
    echo "    Find the owner with:  ss -ltnp | grep 3030   (then tell Claude \"port 3030 is taken\" to skip to the next port)"
fi

echo ""
echo "============================================================"
echo "  Starting PC Admin & Performance Tool service on port 3030"
echo "  Reachable from any host on the same allowed subnet at:"
echo "    http://$(hostname -I 2>/dev/null | awk '{print $1}'):3030"
echo "  Logs are written to: $(pwd)/logs"
echo "  Press CTRL+C to stop, or run with --daemon to background it."
echo "============================================================"

if [ "$1" == "--daemon" ]; then
    nohup python app.py > service.out 2>&1 &
    echo "Started in background (PID $!). Logs: $(pwd)/service.out"
else
    python app.py
fi
