#!/bin/bash
set -e
DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DIR"
PYTHONPATH="$DIR" "$DIR/.venv/bin/python" scripts/sync.py "$@"
