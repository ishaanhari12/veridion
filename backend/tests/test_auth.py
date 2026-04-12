from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ── Helpers ───────────────────────────────────────────────────────────────────

def register(email="test@veridion.com", name="Test User", password="Secure123"):
    return client.post("/api/v1/auth/register", json={
        "email": email,
        "full_name": name,
        "password": password,
    })


def login(email="test@veridion.com", password="Secure123"):
    return client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password,
    })


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Health ────────────────────────────────────────────────────────────────────

def test_health_check():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


# ── Register ──────────────────────────────────────────────────────────────────

def test_register_success():
    r = register()
    assert r.status_code == 201
    data = r.json()
    assert data["email"] == "test@veridion.com"
    assert data["role"] == "user"
    assert data["is_active"] is True
    assert "id" in data
    assert "hashed_password" not in data  # never expose this


def test_register_duplicate_email():
    register()
    r = register()  # same email again
    assert r.status_code == 409
    assert "already exists" in r.json()["detail"]


def test_register_weak_password_too_short():
    r = register(password="Ab1")
    assert r.status_code == 422


def test_register_weak_password_no_uppercase():
    r = register(password="secure123")
    assert r.status_code == 422


def test_register_weak_password_no_number():
    r = register(password="SecurePass")
    assert r.status_code == 422


def test_register_empty_name():
    r = register(name="   ")
    assert r.status_code == 422


def test_register_invalid_email():
    r = register(email="not-an-email")
    assert r.status_code == 422


# ── Login ─────────────────────────────────────────────────────────────────────

def test_login_success():
    register()
    r = login()
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password():
    register()
    r = login(password="WrongPass1")
    assert r.status_code == 401


def test_login_nonexistent_email():
    r = login(email="ghost@veridion.com")
    assert r.status_code == 401


# ── Token refresh ─────────────────────────────────────────────────────────────

def test_refresh_token():
    register()
    tokens = login().json()
    r = client.post("/api/v1/auth/refresh", json={
        "refresh_token": tokens["refresh_token"]
    })
    assert r.status_code == 200
    assert "access_token" in r.json()


# ── /me ───────────────────────────────────────────────────────────────────────

def test_me_returns_profile():
    register()
    token = login().json()["access_token"]
    r = client.get("/api/v1/auth/me", headers=auth_header(token))
    assert r.status_code == 200
    assert r.json()["email"] == "test@veridion.com"


def test_me_requires_auth():
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 403


def test_me_invalid_token():
    r = client.get("/api/v1/auth/me", headers=auth_header("garbage.token.here"))
    assert r.status_code == 401


# ── /me/wallet ────────────────────────────────────────────────────────────────

def test_wallet_created_on_register():
    register()
    token = login().json()["access_token"]
    r = client.get("/api/v1/auth/me/wallet", headers=auth_header(token))
    assert r.status_code == 200
    data = r.json()
    assert float(data["balance"]) == 0.0
    assert data["currency"] == "GBP"
