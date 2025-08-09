#!/usr/bin/env bash
set -Eeuo pipefail

# Přepni do adresáře skriptu
cd "$(dirname "${BASH_SOURCE[0]}")"

# 1) Preferuj připravené prostředí ./jarvis_env, jinak použij ./\.venv
VENV_DIR=""
if [ -x jarvis_env/bin/python ]; then
  VENV_DIR="jarvis_env"
elif [ -d .venv ]; then
  VENV_DIR=".venv"
else
  # Nemáme žádné prostředí – vytvoř lehké .venv
  PY_SYS="python3"
  if command -v python3.10 >/dev/null 2>&1; then
    PY_SYS="python3.10"
  fi
  "$PY_SYS" -m venv .venv
  VENV_DIR=".venv"
fi

# Aktivuj vybrané prostředí
# shellcheck disable=SC1091
source "$VENV_DIR"/bin/activate

# 2) Instalace balíčků: proveď jen pokud jde o čerstvé .venv a není nastaveno JARVIS_SKIP_PIP=1
if [ "${VENV_DIR}" = ".venv" ] && [ "${JARVIS_SKIP_PIP:-0}" != "1" ]; then
  python -m pip -q install -U pip wheel >/dev/null || true
  if [ -f requirements.txt ]; then
    # Pozor: tohle může trvat dlouho (torch atd.)
    python -m pip -q install -r requirements.txt || true
  fi
fi

# 3) Spuštění – preferuj main.py, s bezpečným fallbackem
PYBIN="python"
if [ -f main.py ]; then
  # Zkus main.py; pokud spadne, fallback na simple_jarvis.py (pokud existuje)
  set +e
  "$PYBIN" main.py "$@"
  code=$?
  set -e
  if [ $code -ne 0 ] && [ -f simple_jarvis.py ]; then
    echo "main.py selhal (exit $code) – zkouším simple_jarvis.py" >&2
    exec "$PYBIN" simple_jarvis.py "$@"
  else
    exit $code
  fi
elif [ -f simple_jarvis.py ]; then
  exec "$PYBIN" simple_jarvis.py "$@"
elif [ -f src/core/jarvis.py ]; then
  exec "$PYBIN" src/core/jarvis.py "$@"
elif [ -f src/main.py ]; then
  exec "$PYBIN" src/main.py "$@"
else
  echo "Nenalezen Python entrypoint (myjarvis modul, main.py ani simple_jarvis.py)." >&2
  exit 1
fi
