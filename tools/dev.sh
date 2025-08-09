#!/usr/bin/env bash
set -euo pipefail

cmd=${1:-help}

case "$cmd" in
  setup)
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    pip install pre-commit
    pre-commit install || true
    ;;
  lint)
    pre-commit run --all-files --show-diff-on-failure
    ;;
  test)
    pytest -q
    ;;
  release)
    ver=${2:-}
    if [[ -z "$ver" ]]; then
      echo "Usage: $0 release vX.Y.Z" && exit 1
    fi
    git tag "$ver"
    git push origin "$ver"
    ;;
  help|*)
    echo "Usage: $0 [setup|lint|test|release vX.Y.Z]"
    ;;
esac
