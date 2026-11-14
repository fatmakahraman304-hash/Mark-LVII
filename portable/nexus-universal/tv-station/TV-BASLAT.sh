#!/bin/sh
set -eu
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1; then
  echo "NEXUS TV: Python 3.10+ not found" >&2
  exit 2
fi
exec python3 tv_station.py
