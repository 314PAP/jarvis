#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

if command -v entr >/dev/null 2>&1; then
  printf "Running pytest on file changes (entr)... Ctrl-C to stop\n"
  find . -type f -name "*.py" | entr -c ./jarvis_env/bin/pytest -q
else
  printf "entr not found; falling back to simple loop. Ctrl-C to stop\n"
  while true; do
    ./jarvis_env/bin/pytest -q || true
    sleep 2
  done
fi
