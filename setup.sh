#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

if [ ! -d jarvis_env ]; then
	python3 -m venv jarvis_env
fi

source jarvis_env/bin/activate
python -m pip -q install -U pip wheel
if [ -f requirements.txt ]; then
	python -m pip install -r requirements.txt
fi
echo "Environment ready in ./jarvis_env"
