#!/bin/bash
cd /root/licitmap
PYTHONPATH=/root/licitmap .venv/bin/python scripts/sync.py "$@"
