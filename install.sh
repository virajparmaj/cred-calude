#!/usr/bin/env bash
# CredClaude — Install Script
# Builds .app bundle, copies to ~/Applications, registers launchd auto-start.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$HOME/.credclaude"
VENV_DIR="$SCRIPT_DIR/venv"
PLIST_NAME="com.veer.credclaude"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME.plist"
APP_NAME="CredClaude"
APP_DEST="$HOME/Applications/$APP_NAME.app"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required tool: $1" >&2
    exit 1
  fi
}

launch_agent_is_loaded() {
  launchctl print "gui/$UID/$PLIST_NAME" >/dev/null 2>&1 || launchctl list "$PLIST_NAME" >/dev/null 2>&1
}

stop_launch_agent() {
  if launch_agent_is_loaded; then
    echo "→ Stopping existing launchd agent..."
    launchctl bootout "gui/$UID" "$PLIST_PATH" 2>/dev/null \
      || launchctl bootout "gui/$UID/$PLIST_NAME" 2>/dev/null \
      || launchctl unload "$PLIST_PATH" 2>/dev/null \
      || true
  fi
}

load_launch_agent() {
  launchctl bootstrap "gui/$UID" "$PLIST_PATH" 2>/dev/null || launchctl load "$PLIST_PATH"
}

echo "=== CredClaude Installer ==="
echo ""

# Preflight checks
for tool in python3 launchctl osascript open ditto xattr; do
  require_cmd "$tool"
done

# 0. Quit any running instance before rebuilding
if pgrep -x "CredClaude" &>/dev/null; then
  echo "→ Stopping running CredClaude instance..."
  osascript -e 'tell application "CredClaude" to quit' 2>/dev/null || true
  sleep 1
  # Force-kill if still running after graceful quit
  pkill -x "CredClaude" 2>/dev/null || true
fi

# 0b. Stop launchd before replacing the bundle
stop_launch_agent

# 0c. Remove previous installed app so Finder cannot reuse the old bundle
if [ -d "$APP_DEST" ]; then
  echo "→ Removing previous app bundle..."
  rm -rf "$APP_DEST"
fi

# 1. Create venv
echo "→ Creating virtual environment..."
python3 -m venv "$VENV_DIR"

# 2. Install deps
echo "→ Installing dependencies..."
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet -e "$SCRIPT_DIR"

# 3. Build .app bundle
echo "→ Building app bundle..."
bash "$SCRIPT_DIR/build_app.sh"

# 4. Copy to ~/Applications
echo "→ Installing to ~/Applications..."
mkdir -p "$HOME/Applications"
ditto "$SCRIPT_DIR/dist/$APP_NAME.app" "$APP_DEST"

# 5. Create app support dir
mkdir -p "$APP_DIR"

# 6. Write launchd plist
echo "→ Registering login item with launchd..."
mkdir -p "$HOME/Library/LaunchAgents"

cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$PLIST_NAME</string>

  <key>ProgramArguments</key>
  <array>
    <string>open</string>
    <string>-a</string>
    <string>$APP_DEST</string>
  </array>

  <key>RunAtLoad</key>
  <true/>

  <key>KeepAlive</key>
  <false/>

  <!-- Note: stdout/stderr not captured here because 'open -a' spawns a
       separate process. App logs are written to ~/.credclaude/monitor.log
       by the Python logging module (RotatingFileHandler). -->
</dict>
</plist>
PLIST

# 7. Load the agent
echo "→ Loading launchd agent..."
load_launch_agent

# 8. Launch the new version explicitly
# (launchctl load with RunAtLoad only fires on a fresh load — open ensures the
# app starts immediately in both fresh-install and update scenarios)
echo "→ Launching CredClaude..."
open "$APP_DEST"

echo ""
echo "✅ Installed! CredClaude is now running in your menu bar."
echo "   It will auto-start on every login."
echo ""
echo "   App:        $APP_DEST"
echo "   Config:     $APP_DIR/config.json"
echo "   Logs:       $APP_DIR/monitor.log"
echo "   Pricing:    $APP_DIR/pricing.json"
echo ""
echo "   First launch / trust:"
echo "   - The installer already placed the app in ~/Applications."
echo "   - If macOS says the app cannot be opened, open Finder → ~/Applications,"
echo "     Control-click CredClaude.app, choose Open, then confirm."
echo "   - If macOS still blocks it, go to System Settings → Privacy & Security"
echo "     and click Open Anyway for CredClaude."
if xattr -p com.apple.quarantine "$APP_DEST" >/dev/null 2>&1 || xattr -p com.apple.quarantine "$SCRIPT_DIR" >/dev/null 2>&1; then
  echo "   - This copy appears to carry a quarantine attribute, so macOS may"
  echo "     require that manual Open step the first time you launch it."
fi
echo ""
echo "   If Finder or Launchpad still shows the old icon after reinstall:"
echo "   - That is usually icon cache lag, not a failed build."
echo "   - Close any Finder windows showing the app, quit and reopen CredClaude,"
echo "     then log out/in if the icon still has not refreshed."
echo "   - If you later move or rename the app bundle, rerun install.sh so the"
echo "     launch agent points back at ~/Applications/CredClaude.app."
echo ""
echo "   To uninstall:  bash $SCRIPT_DIR/uninstall.sh"
