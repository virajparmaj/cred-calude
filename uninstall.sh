#!/usr/bin/env bash
# CredClaude — Uninstall Script
# Stops the launchd agent, removes the plist, and removes the .app bundle.

set -euo pipefail

PLIST_NAME="com.veer.credclaude"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME.plist"
APP_NAME="CredClaude"
APP_DEST="$HOME/Applications/$APP_NAME.app"

launch_agent_is_loaded() {
  launchctl print "gui/$UID/$PLIST_NAME" >/dev/null 2>&1 || launchctl list "$PLIST_NAME" >/dev/null 2>&1
}

stop_launch_agent() {
  if launch_agent_is_loaded; then
    echo "→ Stopping launchd agent..."
    launchctl bootout "gui/$UID" "$PLIST_PATH" 2>/dev/null \
      || launchctl bootout "gui/$UID/$PLIST_NAME" 2>/dev/null \
      || launchctl unload "$PLIST_PATH" 2>/dev/null \
      || true
  fi
}

echo "=== Uninstalling CredClaude ==="

# Quit the running app before removing files
if pgrep -x "CredClaude" &>/dev/null; then
  echo "→ Stopping CredClaude..."
  osascript -e 'tell application "CredClaude" to quit' 2>/dev/null || true
  sleep 1
  pkill -x "CredClaude" 2>/dev/null || true
fi

# Stop and unload launchd agent
stop_launch_agent

# Remove plist
if [ -f "$PLIST_PATH" ]; then
  rm "$PLIST_PATH"
  echo "→ Removed login item."
fi

# Remove .app
if [ -d "$APP_DEST" ]; then
  rm -rf "$APP_DEST"
  echo "→ Removed $APP_DEST"
fi

echo ""
echo "✅ Uninstalled."
echo "   App bundle and login item were removed."
echo "   Config, logs, and pricing data remain at ~/.credclaude/."
echo "   Delete that folder manually only if you want a full data reset:"
echo "     rm -rf ~/.credclaude"
