#!/usr/bin/env bash
set -euo pipefail

# Aktivuj lokální venv pokud existuje
if [[ -f "jarvis_env/bin/activate" ]]; then
  source "jarvis_env/bin/activate"
fi

echo "== Ruff (lint/format) =="
if command -v ruff >/dev/null 2>&1; then
  ruff check --fix . || true
else
  pip install -q ruff
  ruff check --fix . || true
fi

echo "== Pylint (test files + main) =="
if command -v pylint >/dev/null 2>&1; then
  pylint -s n main.py test_*.py verify_implementation.py || true
else
  pip install -q pylint
  pylint -s n main.py test_*.py verify_implementation.py || true
fi

echo "== Pytest =="
if command -v pytest >/dev/null 2>&1; then
  pytest -q || true
else
  pip install -q pytest
  pytest -q || true
fi
