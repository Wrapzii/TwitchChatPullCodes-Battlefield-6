"""Utility to refresh a Twitch access token using a stored refresh token.

Environment variables required:
  TWITCH_CLIENT_ID       Your app's client id
  TWITCH_CLIENT_SECRET   Your app's client secret
  TWITCH_REFRESH_TOKEN   The refresh token previously issued

Optional:
  OUTPUT_JSON=1          Write new tokens to .token.json
  PRINT_EXPORT=1         Print PowerShell export lines for quick copy/paste

Usage (PowerShell):
  $env:TWITCH_CLIENT_ID="your_client_id"
  $env:TWITCH_CLIENT_SECRET="your_client_secret"
  $env:TWITCH_REFRESH_TOKEN="your_refresh_token"
  python refresh_token.py

This script uses only the standard library (urllib + json). It does not
automatically update your running environment; you must export the new access
token yourself (prefixed with oauth: when used for IRC PASS / TWITCH_OAUTH).
"""
from __future__ import annotations
import os, json, sys, urllib.request, urllib.parse, time

TOKEN_URL = "https://id.twitch.tv/oauth2/token"

def err(msg: str):
    print(f"[error] {msg}")
    sys.exit(1)

def refresh():
    client_id = os.getenv("TWITCH_CLIENT_ID") or err("TWITCH_CLIENT_ID missing")
    client_secret = os.getenv("TWITCH_CLIENT_SECRET") or err("TWITCH_CLIENT_SECRET missing")
    refresh_token = os.getenv("TWITCH_REFRESH_TOKEN") or err("TWITCH_REFRESH_TOKEN missing")

    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(TOKEN_URL, data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    print("[info] Refreshing token ...")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode()
    except Exception as e:
        err(f"Request failed: {e}")

    try:
        js = json.loads(raw)
    except json.JSONDecodeError:
        err(f"Non-JSON response: {raw[:200]}")

    access_token = js.get("access_token")
    new_refresh = js.get("refresh_token", refresh_token)
    if not access_token:
        err(f"No access_token in response: {js}")

    print("[ok] Got new access token (length {}), expires_in={}s".format(len(access_token), js.get("expires_in")))

    if os.getenv("OUTPUT_JSON") == "1":
        payload = {
            "access_token": access_token,
            "refresh_token": new_refresh,
            "fetched_at": int(time.time()),
            "expires_in": js.get("expires_in"),
            "client_id": client_id,
        }
        with open(".token.json", "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print("[ok] Wrote .token.json")

    if os.getenv("PRINT_EXPORT") == "1":
        print("\n# PowerShell exports (copy/paste):")
        print(f"$env:TWITCH_OAUTH=\"oauth:{access_token}\"")
        print(f"$env:TWITCH_REFRESH_TOKEN=\"{new_refresh}\"")

    return access_token, new_refresh

if __name__ == "__main__":
    refresh()
