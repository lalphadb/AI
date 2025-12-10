#!/bin/bash
cd "$(dirname "$0")"
pip install requests --quiet 2>/dev/null
python3 cli.py
