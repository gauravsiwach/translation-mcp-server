#!/usr/bin/env bash
set -e

if [ -z "$PYTHON" ]; then
  PYTHON=python3
fi

$PYTHON -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "Bootstrap complete. Activate the virtualenv with: source .venv/bin/activate" 
