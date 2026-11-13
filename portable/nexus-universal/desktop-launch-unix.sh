#!/bin/sh
# Manually launch: sh desktop-launch-unix.sh --server https://host:8765
set -eu
cd "$(dirname "$0")"
exec python3 desktop_client.py "$@"
