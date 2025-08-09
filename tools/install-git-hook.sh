#!/usr/bin/env bash
set -euo pipefail

HOOK_DIR=".git/hooks"
HOOK_FILE="$HOOK_DIR/pre-commit"

if [[ ! -d ".git" ]]; then
  echo "Git repo nenalezeno. Inicializuji..."
  git init
fi

mkdir -p "$HOOK_DIR"
cat > "$HOOK_FILE" <<'EOF'
#!/usr/bin/env bash
echo "Pre-commit: lint + test"
bash tools/checks.sh || exit 1
EOF
chmod +x "$HOOK_FILE"
echo "Pre-commit hook nainstalován."
