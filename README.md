# Twitch Code Watcher + (Optional EA Desktop Auto-Entry)

Minimal Python script (stdlib only for basic mode) that connects to a Twitch channel via IRC, watches chat for promo-like codes (default pattern: `XXXX-XXXX-XXXX-XXXX`), and notifies you (clipboard + beep). Optional Windows-only automation can attempt to focus EA Desktop and type the code (best-effort; requires extra packages and may violate Terms of Service if misused—use responsibly). The base watcher does NOT auto redeem and automation is disabled by default.

## Features
- Pure standard library (asyncio + sockets over TLS)
- Regex based detection (default covers 4 blocks of 4 A-Z0-9 characters)
- De-duplicates already seen codes during the session
- Optional Windows beep (enabled by default on Windows unless disabled)
- Simple environment variable configuration
- Offline self-test mode (no network) to verify detection
- Python 3.9+ compatible

## Configuration (Environment Variables)
Set the following environment variables (create a `.env` if you use a loader, or set in PowerShell before running):
- `TWITCH_OAUTH`  Your Twitch IRC OAuth token in the form `oauth:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` (generate at https://twitchapps.com/tmi/)
- `TWITCH_NICK`   Your Twitch username (matching the token)
- `TWITCH_CHANNEL` Channel to join (without the leading #)
- `CODE_REGEX` (optional) Override the default pattern. Default: `\b[A-Z0-9]{4}(?:-[A-Z0-9]{4}){3}\b`
- `DISABLE_BEEP` (optional) Set to `1` to disable the beep on Windows.
- `AUTO_REDEEM` (optional) Set `1` to enable EA Desktop best‑effort auto typing.
- `EA_PID` (optional) PID of `EADesktop.exe`. If omitted and `AUTO_REDEEM=1`, the script will try to auto-detect via `psutil`.
- `REDEEM_SEND_ENTER` (optional) Set `1` to send Enter after typing the code.

## Install & Run (PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
# (Base mode needs no deps; for auto-redeem install requirements)
pip install -r requirements.txt  # optional if using AUTO_REDEEM
$env:TWITCH_OAUTH="oauth:your_token_here"
$env:TWITCH_NICK="your_nick"
$env:TWITCH_CHANNEL="channelname"
# Optional automation (disabled by default; uncomment only if you accept ToS risk)
# $env:AUTO_REDEEM="1"; $env:EA_PID="10912"; $env:REDEEM_SEND_ENTER="1"
python main.py
```

### Token notes (access vs refresh vs client id)
The script only needs an ACCESS token for chat (prefixed with `oauth:`). If you were issued an access token and a refresh token:
- Use: `TWITCH_OAUTH="oauth:ACCESS_TOKEN_VALUE"`
- Keep: `TWITCH_REFRESH_TOKEN` only if you want to refresh later (not required just to run watcher).
- `TWITCH_CLIENT_ID` (and secret) are only needed to refresh / obtain tokens, not for everyday watching.

### Optional: Refreshing a token
If you have a refresh token and client secret, you can use the helper:
```
$env:TWITCH_CLIENT_ID="your_client_id"
$env:TWITCH_CLIENT_SECRET="your_client_secret"
$env:TWITCH_REFRESH_TOKEN="your_refresh_token"
$env:PRINT_EXPORT="1"   # (optional) show export lines
$env:OUTPUT_JSON="1"     # (optional) write .token.json
python refresh_token.py
# Then export the new access token (shown) as TWITCH_OAUTH with oauth: prefix
```

## Sample Output
```
[2025-08-08T12:00:01.123Z] Connected to Twitch IRC, joined #example
[2025-08-08T12:05:33.456Z] CODE DETECTED: ENB2-C3KL-3AQ2-6DCV (first time)
```

## Notes / Ethics
- Only observe chat you are legitimately allowed to view.
- Do NOT enable automation if it breaches Twitch or EA terms; you assume all risk.
- Avoid rapid reconnect loops; Twitch can throttle or ban abusive clients.
- Automation is heuristic (window focus + keystrokes) and can misdirect input—close sensitive windows first.
- Clipboard copy overwrites your previous clipboard contents; disable with `DISABLE_CLIPBOARD=1` if unwanted.

## Test Mode (Offline)
Use to confirm regex, clipboard, and beep without connecting:
```powershell
$env:NO_CONNECT="1"; $env:TEST_MESSAGE="ABCD-EF12-3456-7890"; python main.py
```
Unset (or remove) `NO_CONNECT` to run live.

## Security
See `SECURITY.md` for guidance (tokens, automation risk, dependency updates).

## Next Ideas (Optional)
- Write detected codes with timestamps to a CSV file.
- Desktop notification (e.g., Toast on Windows) or sound file instead of simple beep.
- Add small HTTP server to show last code in a local browser.

---
MIT License.
