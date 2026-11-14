#!/bin/sh
set -eu
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1; then
  echo "NEXUS TV: Python 3.10+ not found" >&2
  exit 2
fi
if ! python3 -c 'import sys;sys.exit(0 if sys.version_info >= (3,10) else 1)' >/dev/null 2>&1; then
  echo "NEXUS TV: Python 3.10+ required" >&2
  exit 2
fi
exec python3 tv_station.py
