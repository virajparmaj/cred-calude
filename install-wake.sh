#!/usr/bin/env bash
# CredClaude — Tier 2 system-wake installer.
#
# Adds a scoped sudoers entry that lets CredClaude schedule pmset wake
# events without prompting for a password every 5 hours. Run once with
# sudo after the main install.sh.
#
#   sudo bash install-wake.sh
#
# To remove: `sudo rm /etc/sudoers.d/credclaude-wake`

set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "install-wake.sh must run as root. Re-run with: sudo bash $0" >&2
  exit 1
fi

TARGET_USER="${SUDO_USER:-}"
if [ -z "$TARGET_USER" ] || [ "$TARGET_USER" = "root" ]; then
  echo "Could not determine the invoking user. Run this via 'sudo bash $0'." >&2
  exit 1
fi

SUDOERS_FILE="/etc/sudoers.d/credclaude-wake"
TMP_FILE="$(mktemp)"
trap 'rm -f "$TMP_FILE"' EXIT

cat > "$TMP_FILE" <<EOF
# Installed by CredClaude install-wake.sh — allows the keepalive scheduler
# to program Mac sleep-wake events via pmset without a password prompt.
# The commands listed here are intentionally narrow in scope.
$TARGET_USER ALL=(root) NOPASSWD: /usr/bin/pmset schedule wake *
$TARGET_USER ALL=(root) NOPASSWD: /usr/bin/pmset schedule cancel wake *
$TARGET_USER ALL=(root) NOPASSWD: /usr/bin/pmset -g sched
EOF

chmod 0440 "$TMP_FILE"

if ! visudo -cf "$TMP_FILE" >/dev/null; then
  echo "Generated sudoers file failed validation — aborting." >&2
  cat "$TMP_FILE" >&2
  exit 1
fi

install -m 0440 -o root -g wheel "$TMP_FILE" "$SUDOERS_FILE"

echo "✅ Installed $SUDOERS_FILE"
echo "   CredClaude can now wake the Mac from sleep at each reset."
echo "   Open Settings → Monitoring and enable 'Wake Mac from sleep'."
