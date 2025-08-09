# Security Guidelines

This project is a lightweight Twitch chat watcher + optional EA Desktop automation. Follow these best practices:

## Secrets
- Do NOT commit real access tokens, refresh tokens, client secrets, or .env files.
- Use environment variables or a local `.env` (ignored) for local development.
- If you accidentally expose a token, revoke/regenerate it immediately.

## Token Scope
- Prefer minimal scopes: for read‑only watching, `chat:read` is sufficient.
- Only request `chat:edit` if you plan to send messages downstream.

## Automation Disclaimer
- Enabling AUTO_REDEEM may conflict with Twitch or EA terms depending on usage. You assume all risk.
- Keep automation disabled by default when distributing.

## Reporting
No formal security policy or bounty. If you discover a sensitive issue (e.g. credential leakage in code), open a PRIVATE report (do not file a public issue) or contact the maintainer directly.

## Dependency Updates
- Optional deps: `psutil`, `pywin32`, `pywinauto`. Keep them updated to receive security patches.
- Periodically run `pip list --outdated` inside the virtual environment.

## Logging
- Avoid writing raw codes or tokens to shared logs. If you add logging, scrub secrets.

## Clipboard & Window Focus Risks
- Clipboard copy could overwrite sensitive data the user expects to keep. Warn users.
- Window focus keystroke automation can send characters to the wrong window. Close unrelated sensitive windows first.

---
Use responsibly.
