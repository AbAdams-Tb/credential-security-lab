"""Local-only educational authentication lab. Never deploy as a real login service."""
import os
import secrets
import time
from pathlib import Path

import pyotp
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware

BASE = Path(__file__).resolve().parent
ENABLE_MFA = os.getenv("DEMO_MFA", "0") == "1"
ENABLE_RATE_LIMIT = os.getenv("DEMO_RATE_LIMIT", "0") == "1"

# Deliberately fictional plaintext credentials for a localhost teaching exercise.
USERS = {
    "alice@example.com": "NewUniquePass_99!",
    "bob@example.com": "SecureLogin_44#",
    "sarah@example.com": "Summer2026!",
}
failures = {}
last_otp_step = {}

def persistent_secret(filename, factory):
    path = BASE / filename
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    secret = factory()
    path.write_text(secret, encoding="utf-8")
    return secret

session_secret = persistent_secret(".demo_session_key", lambda: secrets.token_urlsafe(32))
mfa_secret = persistent_secret(".mfa_sarah_secret", pyotp.random_base32)
app = FastAPI(title="Local Credential Security Lab")
app.add_middleware(SessionMiddleware, secret_key=session_secret, same_site="lax", max_age=1800)

STYLE = """
<style>
body{font:16px system-ui;background:#f3f6fa;min-height:100vh;display:grid;place-items:center;margin:0}
main{background:white;padding:32px;width:min(390px,85vw);border-radius:16px;box-shadow:0 12px 30px #182c4518}
h1{font-size:24px}label{display:block;margin-top:15px}input,button{box-sizing:border-box;width:100%;padding:12px;margin-top:7px;border-radius:8px}
input{border:1px solid #aebaca}button{background:#245eea;color:white;border:0;cursor:pointer;margin-top:20px}
small{color:#526079}#message{color:#b42318}
</style>
"""

LOGIN_HTML = """<!doctype html><html><head><meta charset="utf-8"><title>Demo Login</title>""" + STYLE + """</head>
<body><main><h1>Customer Portal</h1><small>Fictional localhost security lab</small>
<form id="loginForm">
<label>Email<input id="email" name="email" type="email" required autocomplete="username"></label>
<label>Password<input id="password" name="password" type="password" required autocomplete="current-password"></label>
<button id="submitBtn">Sign in</button></form><p id="message"></p></main>
<script>
document.querySelector('#loginForm').addEventListener('submit',async e=>{
e.preventDefault();const msg=document.querySelector('#message');msg.textContent='';
try{const r=await fetch('/login',{method:'POST',body:new FormData(e.target)});
if(r.status===202){location.assign('/mfa');return;}
if(r.status===200){location.assign('/account');return;}
msg.textContent=r.status===429?'Too many attempts (429)':'Invalid credentials (401)';
}catch(err){msg.textContent='Network error';}
});
</script></body></html>"""

MFA_HTML = """<!doctype html><html><head><meta charset="utf-8"><title>MFA</title>""" + STYLE + """</head>
<body><main><h1>Authenticator verification</h1><small>Enter the 6-digit code from your authenticator app</small>
<form id="mfaForm"><label>One-time code<input name="code" inputmode="numeric" pattern="[0-9]{6}" maxlength="6" required autofocus></label>
<button>Verify code</button></form><p id="message"></p></main>
<script>
document.querySelector('#mfaForm').addEventListener('submit',async e=>{
e.preventDefault();const r=await fetch('/mfa',{method:'POST',body:new FormData(e.target)});
if(r.ok){location.assign('/account');return;}
document.querySelector('#message').textContent=r.status===429?'Too many invalid codes':'Incorrect or expired code';
});
</script></body></html>"""

@app.get("/")
def home():
    return {"lab": "Credential Security Lab", "login": "/login"}

@app.get("/login", response_class=HTMLResponse)
def login_page():
    return HTMLResponse(LOGIN_HTML, headers={"Cache-Control":"no-store"})

@app.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...)):
    request.session.clear()
    email = email.strip().lower()
    ip = request.client.host if request.client else "local"
    now = time.time()
    recent = [t for t in failures.get(ip, []) if now-t < 60]
    failures[ip] = recent
    if ENABLE_RATE_LIMIT and len(recent) >= 3:
        print("[RATE LIMITED]", email, flush=True)
        return JSONResponse({"status":"BLOCKED"},status_code=429)
    if USERS.get(email) != password:
        recent.append(now)
        print("[INVALID]", email, flush=True)
        return JSONResponse({"status":"FAILED"},status_code=401)
    if ENABLE_MFA:
        request.session.update(pending=email, started=now, tries=0)
        print("[MFA REQUIRED]", email, flush=True)
        return JSONResponse({"status":"MFA_REQUIRED"},status_code=202)
    request.session["authenticated"] = email
    print("[ACCESS GRANTED]", email, flush=True)
    return {"status":"SUCCESS","account":email}

@app.get("/mfa",response_class=HTMLResponse)
def mfa_page(request: Request):
    if not request.session.get("pending"):
        return HTMLResponse("<p>Sign in first: <a href='/login'>Login</a></p>",status_code=401)
    return HTMLResponse(MFA_HTML,headers={"Cache-Control":"no-store"})

@app.post("/mfa")
def mfa_verify(request: Request, code: str = Form(...)):
    email = request.session.get("pending")
    started = request.session.get("started",0)
    if email != "sarah@example.com" or time.time()-started > 180:
        request.session.clear()
        return JSONResponse({"status":"MFA_SESSION_EXPIRED"},status_code=401)
    tries = request.session.get("tries",0)
    if tries >= 3:
        request.session.clear()
        return JSONResponse({"status":"MFA_BLOCKED"},status_code=429)
    now_step = int(time.time()//30)
    match = None
    if len(code)==6 and code.isascii() and code.isdigit():
        totp=pyotp.TOTP(mfa_secret)
        for step in (now_step-1,now_step,now_step+1):
            if secrets.compare_digest(totp.at(step*30),code):
                match=step
                break
    if match is None or match <= last_otp_step.get(email,-1):
        request.session["tries"]=tries+1
        return JSONResponse({"status":"INVALID_MFA_CODE"},status_code=401)
    last_otp_step[email]=match
    request.session.clear()
    request.session["authenticated"]=email
    return {"status":"SUCCESS","account":email}

@app.get("/account")
def account(request: Request):
    email=request.session.get("authenticated")
    if not email:
        return JSONResponse({"status":"ACCESS_DENIED"},status_code=401)
    return {"status":"ACCOUNT_ACCESS_GRANTED","account":email,"message":"Demo account opened"}

@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return {"status":"LOGGED_OUT"}
