#!/usr/bin/env bash
set -e
cd -- "$(dirname -- "$0")"
if [ -x .venv/bin/python ]; then
  exec .venv/bin/python frontend.py
else
  exec python3 frontend.py
fi
