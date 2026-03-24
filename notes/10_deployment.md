# 10 Deployment

## Purpose
Describe how this project is deployed and operated in its current local-app form.

## Status
- [Confirmed from code] Deployment target is local macOS user session via `launchd` + `.app` bundle.
- [Not found in repository] No cloud deployment manifest (Vercel/Netlify/Render/Docker).

## Confirmed from code
- `install.sh` orchestrates the full install:
  1. Stops any running `CredClaude` instance.
  2. Creates/refreshes venv; `pip install -e .`.
  3. Runs `build_app.sh` → produces `dist/CredClaude.app`.
  4. Copies `.app` to `~/Applications/CredClaude.app`.
  5. Writes `~/Library/LaunchAgents/com.veer.credclaude.plist` (`RunAtLoad: true`, `KeepAlive: false`).
  6. `launchctl load` + `open -a CredClaude` to start immediately.
- launchd plist runs `open -a ~/Applications/CredClaude.app` (not the Python script directly).
- App logs written to `~/.credclaude/monitor.log` by `RotatingFileHandler` (not captured by launchd — `open -a` spawns a separate process).
- Config and data at `~/.credclaude/`.

## Important details
- Release sequence today:
  1. Pull/update repo.
  2. Re-run `bash install.sh` — rebuilds `.app` and reloads launchd agent.
  3. Verify in menu bar; check `~/.credclaude/monitor.log` for startup errors.
- **Path coupling**: `.app` launcher script has the source repo path baked in at build time. If repo moves, re-run `install.sh`. Launcher shows an error dialog (not silent failure) if venv is missing.
- **KeepAlive is false** — launchd will not auto-restart the app if it crashes; user must relaunch or re-run `install.sh`.

## Open issues / gaps
- No versioned release artifacts; updates are manual (re-run `install.sh`).
- No healthcheck command to verify launchd agent status post-install (`launchctl list com.veer.credclaude` works but isn't documented).
- No rollback mechanism other than manual uninstall + reinstall from previous commit.
- No signed/notarized bundle; Gatekeeper may prompt on first launch.

## Recommended next steps
- Document `launchctl list com.veer.credclaude` as the healthcheck command.
- Add explicit release/upgrade checklist.
- Consider `KeepAlive: true` if crash-resilience is desired.
- Consider signed packaging if distributing beyond personal use.
