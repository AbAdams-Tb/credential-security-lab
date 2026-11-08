# Credential Security Lab — FastAPI + Playwright + TOTP MFA

A **localhost-only**, reproducible classroom demonstration of credential reuse, automated browser logins, time-based one-time-password (TOTP) MFA, and simple IP-based rate limiting.

**Safety:** All identities are invented (`example.com`); the browser script has a hard-coded loopback URL and accepts exactly five predefined test accounts. Never point this exercise at a real login service or use real leaked passwords. This is **not** a production authentication implementation.

## Architecture

`combos.txt` (fictional data) → `attack_bot.py` (Playwright/Chromium) → `http://127.0.0.1:8001/login` (FastAPI) → password check → optional MFA → `/account`.

The browser script does **not** try to solve or bypass MFA. It stops at the MFA challenge.

## Prerequisites

- Windows 10/11 with PowerShell and Python 3.12 (or Python 3.10+)
- Chromium installed by Playwright
- A phone authenticator app (Google Authenticator, Microsoft Authenticator, etc.) for the manual MFA portion
- No Docker required. Port **8001** avoids conflicts with services already using port 8000.

## 1. Clone and install

```powershell
git clone https://github.com/YOUR_USERNAME/credential-security-lab.git
cd credential-security-lab
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
```

If Python 3.12 isn't installed, replace `py -3.12` with your installed Python launcher version.

## 2. Choose a scenario and start FastAPI (Terminal 1)

PowerShell environment variables are read **when the server starts**. Stop the server with `Ctrl+C` and restart it after changing scenarios.

**Scenario A — no MFA, no rate limiting**

```powershell
$env:DEMO_MFA="0"
$env:DEMO_RATE_LIMIT="0"
.\.venv\Scripts\python.exe -m uvicorn server:app --host 127.0.0.1 --port 8001
```

Open http://127.0.0.1:8001/login . Try fictional credentials `sarah@example.com` / `Summer2026!`. The page redirects to `/account`, which displays `ACCOUNT_ACCESS_GRANTED`.

**Scenario B — MFA enabled, no rate limiting**

Stop the server (`Ctrl+C`), then:

```powershell
$env:DEMO_MFA="1"
$env:DEMO_RATE_LIMIT="0"
.\.venv\Scripts\python.exe -m uvicorn server:app --host 127.0.0.1 --port 8001
```

The correct password produces HTTP `202 MFA_REQUIRED` and the browser opens `/mfa`, **not** `/account`. To manually complete MFA, see section 4.

**Scenario C — MFA + rate limiting**

Stop the server (`Ctrl+C`), then:

```powershell
$env:DEMO_MFA="1"
$env:DEMO_RATE_LIMIT="1"
.\.venv\Scripts\python.exe -m uvicorn server:app --host 127.0.0.1 --port 8001
```

The first three incorrect login attempts within 60 seconds return `401`; the fourth returns `429`. The bot stops before Sarah. Restarting the server resets the in-memory counter; waiting over 60 seconds also expires the failures.

**Note:** PowerShell environment variables override the old `ENABLE_MFA` / `ENABLE_RATE_LIMIT` booleans from earlier versions of this project. Use the commands above instead of editing source code.

## 3. Run Playwright (Terminal 2)

With Terminal 1 running, open a **separate** PowerShell window in the same project folder:

```powershell
.\.venv\Scripts\python.exe attack_bot.py
```

Chromium opens visibly (`headless=False`). The script enters five invented credential pairs, one at a time, and prints only status results (not passwords).

| Scenario | Expected output |
|---|---|
| A: No protection | 4 × `401`, then Sarah `200` and confirmed account access |
| B: MFA | 4 × `401`, then Sarah `202 MFA_REQUIRED`; no account access |
| C: MFA + rate limit | 3 × `401`, then `429 BLOCKED`; Sarah is not attempted |

The bot uses the exact loopback address `127.0.0.1:8001`. It cannot be configured through command-line arguments to target another site.

## 4. Set up the authenticator app (manual demo)

With the dependencies installed, in the project folder run:

```powershell
.\.venv\Scripts\python.exe setup_mfa.py
```

This creates `mfa_qr.png`. Open that file on your laptop and scan it with your authenticator app. The code changes approximately every 30 seconds. With **Scenario B** running, sign in manually as Sarah and enter the code on `/mfa`. You should reach `/account`.

**Keep the QR code and `.mfa_sarah_secret` private.** Both are ignored by Git. If you want a fresh enrollment, stop the server, delete `.mfa_sarah_secret` and `mfa_qr.png`, run `setup_mfa.py` again, and re-enroll your authenticator. The session signing key `.demo_session_key` is also ignored by Git.

## 5. Test the HTTP endpoints

In another terminal, while the server runs:

```powershell
curl.exe -i http://127.0.0.1:8001/login
curl.exe -i -X POST http://127.0.0.1:8001/login --data-urlencode "email=sarah@example.com" --data-urlencode "password=Summer2026!"
```

The second command returns `200` in Scenario A and `202` in Scenarios B/C (unless rate limiting has already triggered). A raw `curl` request does not automatically navigate to the MFA page; use the browser for that.

Run unit tests (with the server stopped or in another terminal):

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```


## Presentation walkthrough (3–5 minutes)

1. Explain that `combos.txt` contains **fictional** credentials and Playwright automates a real browser.
2. Run Scenario A: Sarah's reused password reaches `/account`.
3. Run Scenario B: the same password produces `202` and requires an authenticator code; optionally complete MFA manually on your phone.
4. Run Scenario C: the fourth failed attempt is blocked with `429`.
5. Explain that MFA protects against password-only compromise and that rate limiting slows repeated attempts. These defenses are complementary.

## Limitations and responsible-use notes

- Passwords are intentionally plaintext **only for a local demo**. Real applications must use password hashing (e.g. Argon2id).
- Rate limiting is an in-memory per-IP example, not distributed or durable; real deployments should use a centralized store, account-based safeguards, and monitoring.
- The session cookie is HTTP-only by Starlette's session middleware but `https_only` is disabled for localhost HTTP. Production requires HTTPS and secure cookies.
- MFA is demonstrated for Sarah's account only. TOTP seeds are stored in local files and must never be published. TOTP is not phishing-resistant; passkeys/WebAuthn offer stronger protection.
- There is no registration, recovery, database, persistent lockout, or production audit trail.
- Only synthetic data, a loopback service, and authorized classroom use are supported.
