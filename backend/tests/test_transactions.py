"""
Phase 2 Transaction Engine Tests
Covers: deposit, withdraw, transfer, fraud pipeline, history, admin controls.
"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ── Helpers ───────────────────────────────────────────────────────────────────

def register_and_login(email: str, name: str = "Test User") -> str:
    """Register a user and return their access token."""
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


def deposit(token: str, amount: str) -> dict:
    return client.post(
        "/api/v1/transactions/deposit",
        json={"amount": amount},
        headers=auth(token),
    )


# ── Deposit tests ─────────────────────────────────────────────────────────────

def test_deposit_success():
    token = register_and_login("dep1@test.com")
    r = deposit(token, "500.00")
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "completed"
    assert data["transaction_type"] == "deposit"
    assert float(data["amount"]) == 500.0
    assert data["fraud_score"] is None  # deposits not fraud scored


def test_deposit_updates_wallet():
    token = register_and_login("dep2@test.com")
    deposit(token, "300.00")
    deposit(token, "200.00")
    r = client.get("/api/v1/auth/me/wallet", headers=auth(token))
    assert float(r.json()["balance"]) == 500.0


def test_deposit_zero_rejected():
    token = register_and_login("dep3@test.com")
    r = deposit(token, "0")
    assert r.status_code == 422


def test_deposit_negative_rejected():
    token = register_and_login("dep4@test.com")
    r = deposit(token, "-100")
    assert r.status_code == 422


def test_deposit_over_limit_rejected():
    token = register_and_login("dep5@test.com")
    r = deposit(token, "100001")
    assert r.status_code == 422


def test_deposit_requires_auth():
    r = client.post("/api/v1/transactions/deposit", json={"amount": "100"})
    assert r.status_code == 403


# ── Withdrawal tests ──────────────────────────────────────────────────────────

def test_withdraw_success():
    token = register_and_login("wd1@test.com")
    deposit(token, "1000.00")
    r = client.post(
        "/api/v1/transactions/withdraw",
        json={"amount": "400.00"},
        headers=auth(token),
    )
    assert r.status_code == 201
    assert r.json()["status"] == "completed"


def test_withdraw_updates_wallet():
    token = register_and_login("wd2@test.com")
    deposit(token, "1000.00")
    client.post(
        "/api/v1/transactions/withdraw",
        json={"amount": "300.00"},
        headers=auth(token),
    )
    r = client.get("/api/v1/auth/me/wallet", headers=auth(token))
    assert float(r.json()["balance"]) == 700.0


def test_withdraw_insufficient_funds():
    token = register_and_login("wd3@test.com")
    r = client.post(
        "/api/v1/transactions/withdraw",
        json={"amount": "999.00"},
        headers=auth(token),
    )
    assert r.status_code == 422
    assert "Insufficient" in r.json()["detail"]


def test_withdraw_exactly_balance():
    token = register_and_login("wd4@test.com")
    deposit(token, "500.00")
    r = client.post(
        "/api/v1/transactions/withdraw",
        json={"amount": "500.00"},
        headers=auth(token),
    )
    assert r.status_code == 201
    wallet = client.get("/api/v1/auth/me/wallet", headers=auth(token))
    assert float(wallet.json()["balance"]) == 0.0


# ── Transfer tests ────────────────────────────────────────────────────────────

def test_transfer_success():
    sender = register_and_login("send1@test.com", "Sender")
    register_and_login("recv1@test.com", "Receiver")
    deposit(sender, "1000.00")

    r = client.post(
        "/api/v1/transactions/transfer",
        json={
            "receiver_email": "recv1@test.com",
            "amount": "250.00",
            "description": "Test payment",
        },
        headers=auth(sender),
    )
    assert r.status_code == 201
    data = r.json()
    assert data["transaction_type"] == "transfer"
    # Fraud score is 0.0 (placeholder ML model) so status = completed
    assert data["status"] == "completed"
    assert float(data["amount"]) == 250.0


def test_transfer_debits_sender():
    sender = register_and_login("send2@test.com", "Sender")
    register_and_login("recv2@test.com", "Receiver")
    deposit(sender, "1000.00")

    client.post(
        "/api/v1/transactions/transfer",
        json={"receiver_email": "recv2@test.com", "amount": "300.00"},
        headers=auth(sender),
    )
    wallet = client.get("/api/v1/auth/me/wallet", headers=auth(sender))
    assert float(wallet.json()["balance"]) == 700.0


def test_transfer_credits_receiver():
    sender = register_and_login("send3@test.com", "Sender")
    receiver = register_and_login("recv3@test.com", "Receiver")
    deposit(sender, "1000.00")

    client.post(
        "/api/v1/transactions/transfer",
        json={"receiver_email": "recv3@test.com", "amount": "400.00"},
        headers=auth(sender),
    )
    wallet = client.get("/api/v1/auth/me/wallet", headers=auth(receiver))
    assert float(wallet.json()["balance"]) == 400.0


def test_transfer_to_self_rejected():
    token = register_and_login("self1@test.com")
    deposit(token, "500.00")
    r = client.post(
        "/api/v1/transactions/transfer",
        json={"receiver_email": "self1@test.com", "amount": "100.00"},
        headers=auth(token),
    )
    assert r.status_code == 422
    assert "yourself" in r.json()["detail"]


def test_transfer_unknown_receiver():
    sender = register_and_login("send4@test.com")
    deposit(sender, "500.00")
    r = client.post(
        "/api/v1/transactions/transfer",
        json={"receiver_email": "ghost@nowhere.com", "amount": "100.00"},
        headers=auth(sender),
    )
    assert r.status_code == 404


def test_transfer_insufficient_funds():
    sender = register_and_login("send5@test.com")
    register_and_login("recv5@test.com")
    r = client.post(
        "/api/v1/transactions/transfer",
        json={"receiver_email": "recv5@test.com", "amount": "999.00"},
        headers=auth(sender),
    )
    assert r.status_code == 422
    assert "Insufficient" in r.json()["detail"]


def test_transfer_has_fraud_score():
    sender = register_and_login("send6@test.com")
    register_and_login("recv6@test.com")
    deposit(sender, "1000.00")

    r = client.post(
        "/api/v1/transactions/transfer",
        json={"receiver_email": "recv6@test.com", "amount": "100.00"},
        headers=auth(sender),
    )
    assert r.status_code == 201
    # Fraud score exists and is 0.0 from placeholder model
    assert r.json()["fraud_score"] is not None
    assert float(r.json()["fraud_score"]) == 0.0


# ── History tests ─────────────────────────────────────────────────────────────

def test_history_returns_transactions():
    token = register_and_login("hist1@test.com")
    deposit(token, "100.00")
    deposit(token, "200.00")
    deposit(token, "300.00")

    r = client.get("/api/v1/transactions/history", headers=auth(token))
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3
    assert data["page"] == 1


def test_history_newest_first():
    token = register_and_login("hist2@test.com")
    deposit(token, "100.00")
    deposit(token, "999.00")

    r = client.get("/api/v1/transactions/history", headers=auth(token))
    items = r.json()["items"]
    # Most recent deposit (999) should be first
    assert float(items[0]["amount"]) == 999.0


def test_history_pagination():
    token = register_and_login("hist3@test.com")
    for i in range(5):
        deposit(token, "100.00")

    r = client.get(
        "/api/v1/transactions/history?page=1&page_size=2",
        headers=auth(token),
    )
    data = r.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
    assert data["total_pages"] == 3


def test_history_status_filter():
    token = register_and_login("hist4@test.com")
    deposit(token, "100.00")
    deposit(token, "200.00")

    r = client.get(
        "/api/v1/transactions/history?status=completed",
        headers=auth(token),
    )
    data = r.json()
    assert data["total"] == 2
    for item in data["items"]:
        assert item["status"] == "completed"


def test_history_requires_auth():
    r = client.get("/api/v1/transactions/history")
    assert r.status_code == 403


# ── Users only see their own transactions ─────────────────────────────────────

def test_history_isolated_per_user():
    alice = register_and_login("alice@test.com", "Alice")
    bob = register_and_login("bob@test.com", "Bob")

    deposit(alice, "500.00")
    deposit(alice, "500.00")
    deposit(bob, "100.00")

    alice_history = client.get(
        "/api/v1/transactions/history", headers=auth(alice)
    ).json()
    bob_history = client.get(
        "/api/v1/transactions/history", headers=auth(bob)
    ).json()

    assert alice_history["total"] == 2
    assert bob_history["total"] == 1
