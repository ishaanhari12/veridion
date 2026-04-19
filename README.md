# Veridion — Fintech Fraud Detection Platform

> Full-stack fintech platform simulating real-world payment infrastructure
> with real-time ML fraud detection, enterprise-grade security, and AWS deployment.

[![CI](https://github.com/yourusername/veridion/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/veridion/actions)
[![Security: Bandit](https://img.shields.io/badge/security-bandit%20scanned-brightgreen)](docs/security.md)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-green)](https://fastapi.tiangolo.com)

---

## Live Demo
**Coming in Phase 6 — AWS deployment**

---

## Quick Start

```bash
# 1. Copy and configure environment
cp backend/.env.example backend/.env
# Generate secret key and paste into .env as SECRET_KEY:
python -c "import secrets; print(secrets.token_hex(32))"

# 2. Start the full stack (API + PostgreSQL + Fraud service)
docker compose up --build

# 3. Run database migrations (second terminal)
docker exec veridion_api alembic revision --autogenerate -m "initial"
docker exec veridion_api alembic upgrade head

# 4. Run the test suite
docker exec veridion_api pytest tests/ -v

# 5. Open interactive API docs
open http://localhost:8000/docs
```

---

## What It Does

Veridion simulates a production-grade fintech payment platform with:

- **Secure wallet system** — deposit, withdraw, peer-to-peer transfers
- **ACID-compliant transactions** — atomic debit/credit, no double-spending
- **Real-time fraud detection** — every transfer scored 0–1 before money moves
- **Auto-blocking** — transfers above risk threshold blocked automatically
- **Full audit trail** — every action logged with user, IP, and timestamp
- **Admin dashboard** — React frontend with fraud analytics (Phase 5)
- **Cloud-native** — deployed on AWS with Terraform IaC (Phase 6)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI, SQLAlchemy, Alembic |
| Auth | JWT (PyJWT), bcrypt, RBAC (3 roles) |
| Database | PostgreSQL (primary), DynamoDB (Phase 6) |
| ML | Scikit-learn, XGBoost, MLflow (Phase 4) |
| Frontend | React 18, Tailwind CSS, Recharts (Phase 5) |
| Infrastructure | AWS (EC2, RDS, Lambda, API Gateway, S3), Terraform |
| DevOps | Docker, GitHub Actions CI/CD |
| Security | OWASP ZAP, Bandit, slowapi, Pydantic v2 |

---

## Project Structure

```
veridion/
├── backend/              # FastAPI application
│   ├── app/
│   │   ├── api/v1/       # Route handlers with rate limiting
│   │   ├── core/         # Config, JWT, RBAC, security
│   │   ├── db/           # Database session
│   │   ├── models/       # SQLAlchemy ORM models
│   │   ├── schemas/      # Pydantic request/response schemas
│   │   └── services/     # Business logic layer
│   └── tests/            # 55+ tests across auth, transactions, security
├── ml/                   # Fraud detection service
│   └── src/              # FastAPI inference endpoint
├── docs/                 # Architecture diagrams, security audit
├── infrastructure/       # Terraform AWS config (Phase 6)
└── .github/workflows/    # CI/CD pipelines
```

---

## API Endpoints

### Authentication
| Method | Endpoint | Description | Rate Limit |
|---|---|---|---|
| POST | /api/v1/auth/register | Register new user | 10/min |
| POST | /api/v1/auth/login | Login, get JWT tokens | 10/min |
| POST | /api/v1/auth/refresh | Refresh access token | 20/min |
| GET | /api/v1/auth/me | Get current user profile | 60/min |
| GET | /api/v1/auth/me/wallet | Get wallet balance | 60/min |

### Transactions
| Method | Endpoint | Description | Rate Limit |
|---|---|---|---|
| POST | /api/v1/transactions/deposit | Add funds to wallet | 30/min |
| POST | /api/v1/transactions/withdraw | Withdraw funds | 30/min |
| POST | /api/v1/transactions/transfer | Transfer to another user | 20/min |
| GET | /api/v1/transactions/history | Paginated history | 60/min |
| PATCH | /api/v1/transactions/{id}/status | Admin: update status | 60/min |

---

## Security

See [docs/security.md](docs/security.md) for full details.

- Bandit static analysis — zero high-severity findings
- OWASP ZAP dynamic scan — clean report (coming Phase 3 completion)
- bcrypt password hashing
- JWT with refresh token rotation
- Rate limiting on all endpoints
- Security headers on every response
- Input validation via Pydantic v2
- Full audit logging for compliance

---

## ML Model Performance

*Coming in Phase 4 — Isolation Forest + XGBoost ensemble*

| Metric | Score |
|---|---|
| Precision | — |
| Recall | — |
| F1 Score | — |
| AUC-ROC | — |

---

## Key Technical Decisions

**Why FastAPI over Flask?**
Async support, automatic OpenAPI docs, and Pydantic v2 validation built in.
Closer to what production fintech teams use.

**Why ACID-compliant atomic transactions?**
In financial systems, partial writes are catastrophic. Every transfer wraps
the debit and credit in a single database transaction that rolls back on
any failure. No money is ever lost or duplicated.

**Why an ensemble ML model?**
Isolation Forest catches statistical anomalies without labels.
XGBoost provides calibrated fraud probabilities on labelled data.
Combining both reduces false positives significantly.

**Why Terraform?**
Every AWS resource is reproducible, reviewable, and deployable in one command.
No clicking through consoles — infrastructure is code.

**Why fail-open on fraud service outage?**
A fraud service crash should never take down the payment system.
If the ML service is unreachable, transactions are flagged for manual
review rather than blocked entirely.
