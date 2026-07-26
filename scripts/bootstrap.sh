#!/usr/bin/env bash
set -euo pipefail
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
