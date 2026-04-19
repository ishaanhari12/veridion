"""
Phase 3 Security Tests
Verifies: security headers, rate limiting behaviour, input validation,
authentication enforcement, and RBAC restrictions.
"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ── Helpers ───────────────────────────────────────────────────────────────────

def register_and_login(email: str, name: str = "Test User") -> str:
    client.post("/api/v1/auth/register", json={
        "email": email,
        "full_name": name,
        "password": "Secure123",
    })
    r = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "Secure123",
    })
    return r.json()["access_token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Security headers ──────────────────────────────────────────────────────────

def test_security_headers_present():
    """Every response must include the core security headers."""
    r = client.get("/health")
    assert r.status_code == 200
    assert "x-content-type-options" in r.headers
    assert "x-frame-options" in r.headers
    assert "strict-transport-security" in r.headers
    assert "referrer-policy" in r.headers


def test_x_content_type_options_value():
    """nosniff prevents MIME type confusion attacks."""
    r = client.get("/health")
    assert r.headers["x-content-type-options"] == "nosniff"


def test_x_frame_options_value():
    """DENY prevents this API being embedded in iframes (clickjacking)."""
    r = client.get("/health")
    assert r.headers["x-frame-options"] == "DENY"


def test_hsts_header_present():
    """HSTS forces HTTPS for 1 year."""
    r = client.get("/health")
    assert "max-age=31536000" in r.headers["strict-transport-security"]


def test_security_headers_on_api_endpoints():
    """Security headers must appear on API endpoints too, not just /health."""
    r = client.get("/api/v1/auth/me")
    assert "x-content-type-options" in r.headers
    assert "x-frame-options" in r.headers


# ── Authentication enforcement ────────────────────────────────────────────────

def test_protected_endpoint_no_token():
    """No token = 403. Not 401 because we use HTTPBearer which returns 403."""
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 403


def test_protected_endpoint_invalid_token():
    """Malformed token = 401."""
    r = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer this.is.fake"},
    )
    assert r.status_code == 401


def test_protected_endpoint_empty_bearer():
    """Empty bearer = rejected."""
    r = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer "},
    )
    assert r.status_code in (401, 403, 422)


def test_deposit_no_token_rejected():
    r = client.post("/api/v1/transactions/deposit", json={"amount": "100"})
    assert r.status_code == 403


def test_transfer_no_token_rejected():
    r = client.post("/api/v1/transactions/transfer", json={
        "receiver_email": "someone@test.com",
        "amount": "100",
    })
    assert r.status_code == 403


def test_history_no_token_rejected():
    r = client.get("/api/v1/transactions/history")
    assert r.status_code == 403


# ── RBAC — role based access control ─────────────────────────────────────────

def test_admin_endpoint_rejected_for_normal_user():
    """Normal users cannot update transaction status — analyst/admin only."""
    token = register_and_login("rbac1@test.com")
    fake_id = "00000000-0000-0000-0000-000000000000"
    r = client.patch(
        f"/api/v1/transactions/{fake_id}/status",
        json={"new_status": "completed"},
        headers=auth(token),
    )
    # 403 = correct RBAC rejection
    assert r.status_code == 403


# ── Input validation ──────────────────────────────────────────────────────────

def test_sql_injection_in_email_rejected():
    """Malformed email with SQL-like characters must be rejected by Pydantic."""
    r = client.post("/api/v1/auth/register", json={
        "email": "not-an-email'; DROP TABLE users; --",
        "full_name": "Hacker",
        "password": "Secure123",
    })
    assert r.status_code == 422


def test_xss_in_full_name_sanitised():
    """XSS content in full_name is stored as plain text, never executed."""
    r = client.post("/api/v1/auth/register", json={
        "email": "xss.security.test@veridion.com",
        "full_name": "<script>alert(1)</script>",
        "password": "Secure123",
    })
    # Registers successfully — the API stores it as plain text, never renders it.
    # A JSON API is not vulnerable to XSS the way an HTML page would be.
    # The script tag is returned as an inert string in the JSON response.
    assert r.status_code == 201
    assert "<script>" in r.json()["full_name"]


def test_extremely_long_input_rejected():
    """Very long inputs should be rejected cleanly, not crash the server."""
    r = client.post("/api/v1/auth/login", json={
        "email": "a" * 1000 + "@test.com",
        "password": "Secure123",
    })
    assert r.status_code == 422


def test_missing_required_fields_rejected():
    """Missing required fields must return 422, not 500."""
    r = client.post("/api/v1/auth/register", json={
        "email": "missing@test.com",
    })
    assert r.status_code == 422


def test_wrong_content_type_handled():
    """Sending form data instead of JSON must not crash the server."""
    r = client.post(
        "/api/v1/auth/login",
        data={"email": "test@test.com", "password": "Secure123"},
    )
    assert r.status_code == 422


def test_negative_deposit_rejected():
    """Negative amounts are a classic financial exploit attempt."""
    token = register_and_login("neg@test.com")
    r = client.post(
        "/api/v1/transactions/deposit",
        json={"amount": "-500"},
        headers=auth(token),
    )
    assert r.status_code == 422


def test_zero_amount_rejected():
    """Zero amount transfers/deposits must be rejected."""
    token = register_and_login("zero@test.com")
    r = client.post(
        "/api/v1/transactions/deposit",
        json={"amount": "0"},
        headers=auth(token),
    )
    assert r.status_code == 422


def test_string_amount_rejected():
    """Non-numeric amounts must be rejected."""
    token = register_and_login("str@test.com")
    r = client.post(
        "/api/v1/transactions/deposit",
        json={"amount": "one hundred"},
        headers=auth(token),
    )
    assert r.status_code == 422


# ── Password security ─────────────────────────────────────────────────────────

def test_password_not_returned_in_response():
    """The hashed password must never appear in any API response."""
    r = client.post("/api/v1/auth/register", json={
        "email": "pwtest@test.com",
        "full_name": "PW Test",
        "password": "Secure123",
    })
    assert r.status_code == 201
    response_text = str(r.json())
    assert "hashed_password" not in response_text
    assert "Secure123" not in response_text


def test_wrong_password_gives_generic_error():
    """
    Login failure must give the same error whether the email exists or not.
    This prevents user enumeration attacks.
    """
    # Register alice
    client.post("/api/v1/auth/register", json={
        "email": "alice2@test.com",
        "full_name": "Alice",
        "password": "Secure123",
    })

    # Wrong password for real user
    r1 = client.post("/api/v1/auth/login", json={
        "email": "alice2@test.com",
        "password": "WrongPass1",
    })

    # Non-existent user
    r2 = client.post("/api/v1/auth/login", json={
        "email": "ghost@nowhere.com",
        "password": "WrongPass1",
    })

    # Both must return 401 with identical error — attacker cannot tell the difference
    assert r1.status_code == 401
    assert r2.status_code == 401
    assert r1.json()["detail"] == r2.json()["detail"]
