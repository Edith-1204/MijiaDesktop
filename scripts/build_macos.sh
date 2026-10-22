#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ "$(uname -s)" != Darwin ]]; then
    echo "Build this app on macOS." >&2
    exit 1
fi

PYTHON="${PYTHON:-python3}"
"$PYTHON" -c 'import sys; assert (3, 11) <= sys.version_info < (3, 14), "Python 3.11–3.13 required"'
if [[ ! -d .venv ]]; then
    "$PYTHON" -m venv .venv
fi
.venv/bin/python -m pip install -e '.[packaging]'
.venv/bin/python scripts/build_icons.py
.venv/bin/python -m PyInstaller --noconfirm --clean MijiaDesktop.spec
echo "Built: $PWD/dist/MijiaDesktop.app"
