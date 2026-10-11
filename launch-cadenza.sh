#!/bin/sh
cd "$(dirname "$0")" || exit 1
if ! command -v python3 >/dev/null 2>&1; then
 echo 'Install Python 3.11+ with Tk, then reopen Cadenza. See DEPENDENCIES.txt.'
 if command -v zenity >/dev/null 2>&1; then zenity --error --text='Cadenza needs Python 3.11+ with Tk. See DEPENDENCIES.txt.'; fi
 exit 1
fi
if [ -x .venv/bin/python ]; then exec .venv/bin/python desktop.py; fi
exec python3 desktop.py
