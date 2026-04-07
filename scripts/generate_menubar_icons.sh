#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
SOURCE="$REPO_ROOT/assets/icons/macos/claude_monitor_icon_1024.png"

if [[ ! -f "$SOURCE" ]]; then
    echo "Error: source image not found at $SOURCE" >&2
    exit 1
fi

sips -z 22 22 "$SOURCE" --out "$REPO_ROOT/assets/credclaude_menubar.png"
sips -z 44 44 "$SOURCE" --out "$REPO_ROOT/assets/credclaude_menubar@2x.png"

echo "Generated:"
sips -g pixelWidth -g pixelHeight "$REPO_ROOT/assets/credclaude_menubar.png"
sips -g pixelWidth -g pixelHeight "$REPO_ROOT/assets/credclaude_menubar@2x.png"
