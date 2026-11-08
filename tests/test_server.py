import os
os.environ["DEMO_MFA"] = "0"
os.environ["DEMO_RATE_LIMIT"] = "0"
from fastapi.testclient import TestClient
from server import app

def test_login_success():
    with TestClient(app) as client:
        response = client.post("/login", data={"email":"sarah@example.com","password":"Summer2026!"})
        assert response.status_code == 200
        assert client.get("/account").json()["status"] == "ACCOUNT_ACCESS_GRANTED"

def test_login_failure():
    with TestClient(app) as client:
        response = client.post("/login", data={"email":"sarah@example.com","password":"wrong"})
        assert response.status_code == 401

def test_account_requires_session():
    with TestClient(app) as client:
        assert client.get("/account").status_code == 401
