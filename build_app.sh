#!/usr/bin/env bash
# Build a macOS .app bundle using a shell wrapper approach.
# This creates a minimal .app that launches the Python package via the venv.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="CredClaude"
APP_DIR="$SCRIPT_DIR/dist/$APP_NAME.app"
CONTENTS="$APP_DIR/Contents"
MACOS="$CONTENTS/MacOS"
RESOURCES="$CONTENTS/Resources"
ICON_SOURCE_DIR="$SCRIPT_DIR/assets/icons/macos"
RUNTIME_ICON_NAME="AppIconRuntime.png"

# Full-bleed rounded-square art still reads oversized at a mild inset.
# Finder / Applications / Launchpad come from the bundle icon, while Dock and
# the settings miniwindow use the runtime PNG set in app.py. Keep those
# surfaces independently tunable without affecting the dedicated menu bar icon.
TARGET_ALPHA_BOUNDS_RATIO="0.82"
DOCK_ICON_BOUNDS_RATIO="0.72"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required tool: $1" >&2
    exit 1
  fi
}

copy_icon_variant() {
  local source_size="$1"
  local dest_name="$2"
  local work_dir="$3"
  local source_path="$work_dir/claude_monitor_icon_${source_size}.png"

  if [ ! -f "$source_path" ]; then
    echo "Missing icon source: $source_path" >&2
    exit 1
  fi

  cp "$source_path" "$ICONSET/$dest_name"
}

normalize_icon_set() {
  local work_dir="$1"
  local ratio="$2"

  cp "$ICON_SOURCE_DIR"/claude_monitor_icon_*.png "$work_dir"/
  for size in 16 32 64 128 256 512 1024; do
    local target_size
    target_size="$(python3 - "$size" "$ratio" <<'PY'
import sys

size = int(sys.argv[1])
ratio = float(sys.argv[2])
print(max(1, int(round(size * ratio))))
PY
)"
    sips -z "$target_size" "$target_size" \
      "$work_dir/claude_monitor_icon_${size}.png" \
      --out "$work_dir/claude_monitor_icon_${size}.scaled.png" >/dev/null
    sips -p "$size" "$size" \
      "$work_dir/claude_monitor_icon_${size}.scaled.png" \
      --out "$work_dir/claude_monitor_icon_${size}.png" >/dev/null
    rm -f "$work_dir/claude_monitor_icon_${size}.scaled.png"
  done
}

# Read version from package (single source of truth)
if [ -d "$SCRIPT_DIR/venv" ]; then
  VERSION=$("$SCRIPT_DIR/venv/bin/python" -c "import credclaude; print(credclaude.__version__)" 2>/dev/null || echo "1.0.0")
else
  VERSION="1.0.0"
fi

echo "→ Building $APP_NAME.app (v$VERSION)..."

# Preflight checks
for tool in python3 sips iconutil cc plutil; do
  require_cmd "$tool"
done

if [ ! -d "$ICON_SOURCE_DIR" ]; then
  echo "Missing icon source directory: $ICON_SOURCE_DIR" >&2
  exit 1
fi

for size in 16 32 64 128 256 512 1024; do
  if [ ! -f "$ICON_SOURCE_DIR/claude_monitor_icon_${size}.png" ]; then
    echo "Missing icon source: $ICON_SOURCE_DIR/claude_monitor_icon_${size}.png" >&2
    exit 1
  fi
done

# Clean previous builds so the output remains deterministic.
mkdir -p "$SCRIPT_DIR/dist"
find "$SCRIPT_DIR/dist" -maxdepth 1 -type d -name "${APP_NAME}*.app" -exec rm -rf {} +

# Create .app structure
mkdir -p "$MACOS" "$RESOURCES"

WORK_DIR="$(mktemp -d "$SCRIPT_DIR/dist/.icon-work.XXXXXX")"
BUNDLE_WORK_DIR="$WORK_DIR/bundle"
DOCK_WORK_DIR="$WORK_DIR/dock"
mkdir -p "$BUNDLE_WORK_DIR" "$DOCK_WORK_DIR"
trap 'rm -rf "$WORK_DIR"' EXIT

echo "   Normalizing bundle icon footprint to ${TARGET_ALPHA_BOUNDS_RATIO} for Finder/Applications/Launchpad."
normalize_icon_set "$BUNDLE_WORK_DIR" "$TARGET_ALPHA_BOUNDS_RATIO"
echo "   Normalizing runtime icon footprint to ${DOCK_ICON_BOUNDS_RATIO} for Dock/settings."
normalize_icon_set "$DOCK_WORK_DIR" "$DOCK_ICON_BOUNDS_RATIO"

# Build AppIcon.icns from the tracked macOS icon assets.
ICONSET="$RESOURCES/AppIcon.iconset"
mkdir -p "$ICONSET"
copy_icon_variant 16 "icon_16x16.png" "$BUNDLE_WORK_DIR"
copy_icon_variant 32 "icon_16x16@2x.png" "$BUNDLE_WORK_DIR"
copy_icon_variant 32 "icon_32x32.png" "$BUNDLE_WORK_DIR"
copy_icon_variant 64 "icon_32x32@2x.png" "$BUNDLE_WORK_DIR"
copy_icon_variant 128 "icon_128x128.png" "$BUNDLE_WORK_DIR"
copy_icon_variant 256 "icon_128x128@2x.png" "$BUNDLE_WORK_DIR"
copy_icon_variant 256 "icon_256x256.png" "$BUNDLE_WORK_DIR"
copy_icon_variant 512 "icon_256x256@2x.png" "$BUNDLE_WORK_DIR"
copy_icon_variant 512 "icon_512x512.png" "$BUNDLE_WORK_DIR"
copy_icon_variant 1024 "icon_512x512@2x.png" "$BUNDLE_WORK_DIR"
iconutil -c icns "$ICONSET" -o "$RESOURCES/AppIcon.icns"
cp "$DOCK_WORK_DIR/claude_monitor_icon_512.png" "$RESOURCES/$RUNTIME_ICON_NAME"
rm -rf "$ICONSET"
echo "   Icon bundle resources: $RESOURCES/AppIcon.icns, $RESOURCES/$RUNTIME_ICON_NAME"

# Info.plist
cat > "$CONTENTS/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key>
  <string>$APP_NAME</string>
  <key>CFBundleDisplayName</key>
  <string>$APP_NAME</string>
  <key>CFBundleIdentifier</key>
  <string>com.veer.credclaude</string>
  <key>CFBundleVersion</key>
  <string>$VERSION</string>
  <key>CFBundleShortVersionString</key>
  <string>$VERSION</string>
  <key>CFBundleExecutable</key>
  <string>CredClaude</string>
  <key>LSUIElement</key>
  <true/>
  <key>LSBackgroundOnly</key>
  <false/>
  <key>CFBundleIconFile</key>
  <string>AppIcon</string>
</dict>
</plist>
PLIST
plutil -lint "$CONTENTS/Info.plist" >/dev/null

# Compiled launcher stub — gives macOS the correct process identity
# so Stage Manager / Dock show "CredClaude" instead of "Python".
LAUNCHER_SRC="$MACOS/launcher.c"
cat > "$LAUNCHER_SRC" <<'CSRC'
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <libgen.h>
#include <mach-o/dyld.h>

int main(int argc, char *argv[]) {
    /* Resolve the directory containing this executable */
    char exe[4096];
    uint32_t sz = sizeof(exe);
    if (_NSGetExecutablePath(exe, &sz) != 0) {
        fprintf(stderr, "CredClaude: cannot resolve executable path\n");
        return 1;
    }
    char *real = realpath(exe, NULL);
    if (!real) { perror("realpath"); return 1; }
    char *dir = dirname(real);           /* .../Contents/MacOS */
    char *contents = dirname(dir);       /* .../Contents        */
    char *app_dir = dirname(contents);   /* .../CredClaude.app  */

    /* Walk up from the .app bundle to find the repo root.
       Installed layout: ~/Applications/CredClaude.app  →  repo is at REPO_DIR
       Dev layout:       <repo>/dist/CredClaude.app     →  repo is dirname(dirname(app_dir))
       We use the CREDCLAUDE_REPO env var if set, otherwise assume the
       repo path was baked in at build time (see sed below). */
    const char *repo = getenv("CREDCLAUDE_REPO");
    if (!repo) repo = "@@REPO_DIR@@";

    /* Validate venv */
    char venv_python[4096];
    snprintf(venv_python, sizeof(venv_python), "%s/venv/bin/python", repo);
    if (access(venv_python, X_OK) != 0) {
        /* Show a dialog via osascript */
        system("osascript -e 'display dialog \"CredClaude: venv not found.\\n"
               "The source repo may have moved.\\n"
               "Please re-run install.sh.\" buttons {\"OK\"} "
               "default button \"OK\" with icon stop' 2>/dev/null");
        free(real);
        return 1;
    }

    /* chdir to repo so relative imports work */
    chdir(repo);

    /* exec the Python interpreter — this process becomes Python but
       macOS already registered our binary name as "CredClaude". */
    char *new_argv[] = { "CredClaude", "-m", "credclaude", NULL };
    execv(venv_python, new_argv);

    /* If exec fails */
    perror("execv");
    free(real);
    return 1;
}
CSRC

# Bake in the repo path
sed -i '' "s|@@REPO_DIR@@|$SCRIPT_DIR|g" "$LAUNCHER_SRC"

# Compile the launcher
echo "   Compiling launcher stub..."
cc -O2 -o "$MACOS/CredClaude" "$LAUNCHER_SRC"
rm "$LAUNCHER_SRC"

echo "✅ Built: $APP_DIR"
echo "   Copy to ~/Applications/ to use."
