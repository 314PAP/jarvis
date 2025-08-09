#!/usr/bin/env bash
set -euo pipefail

APP_NAME="Jarvis"
DESKTOP_FILE="$HOME/.config/autostart/jarvis.desktop"
SCRIPT_PATH="$(cd "$(dirname "$0")"/.. && pwd)/jarvis.sh"

mkdir -p "$HOME/.config/autostart"
cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=$APP_NAME
Exec=$SCRIPT_PATH
X-GNOME-Autostart-enabled=true
X-KDE-autostart-after=panel
X-KDE-StartupNotify=false
EOF

echo "Autostart vytvořen: $DESKTOP_FILE"
