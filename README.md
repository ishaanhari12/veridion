# Veridion — Fintech Fraud Detection Platform

![CI](https://github.com/ishaanhari12/veridion/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)
![React](https://img.shields.io/badge/React-18-61DAFB)
![AWS](https://img.shields.io/badge/AWS-EC2%20%7C%20RDS%20%7C%20S3-orange)
![Terraform](https://img.shields.io/badge/Terraform-1.x-purple)

A production-grade fraud detection platform built to demonstrate full-stack fintech engineering, ML, and cloud deployment skills.

---

## What It Does

Veridion is a real-time payment platform that scores every transaction for fraud using a trained ML ensemble model before money moves.

- Users register, authenticate with JWT, and manage a wallet
- Deposits and transfers are processed atomically (ACID transactions)
- Every transfer is scored by an **Isolation Forest + XGBoost ensemble** trained on 284,807 real credit card transactions
- Transactions are automatically **blocked** (score ≥ 0.85), **flagged** (score ≥ 0.50), or **completed** (score < 0.50)
- A React dashboard shows live balances, fraud scores, and transaction history with colour-coded risk levels

---

## Architecture

```
React Dashboard (Vite + Tailwind)
        │
        ▼
FastAPI Backend (JWT Auth, RBAC, Rate Limiting)
        │                         │
        ▼                         ▼
PostgreSQL (AWS RDS)     Fraud ML Service
                         (Isolation Forest + XGBoost)
                                  │
                                  ▼
                           S3 (Model Storage)
```

All infrastructure provisioned with **Terraform** on AWS (EC2, RDS, S3, VPC).

---

## ML Model Performance

Trained on the [Kaggle Credit Card Fraud dataset](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud) — 284,807 transactions, 492 fraud cases (0.1727% fraud rate).

| Metric | Isolation Forest | XGBoost | Ensemble |
|--------|-----------------|---------|----------|
| AUC-ROC | 0.9416 | 0.9818 | 0.9654 |
| Precision | — | 0.4183 | 0.5305 |
| Recall | — | 0.8878 | 0.8878 |
| F1 Score | — | 0.5686 | 0.6641 |

Ensemble weighting: **30% Isolation Forest + 70% XGBoost**. SMOTE oversampling applied to handle class imbalance.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, SQLAlchemy, Alembic |
| Auth | JWT, bcrypt, RBAC (user / analyst / admin) |
| Database | PostgreSQL 16 |
| ML | scikit-learn, XGBoost, MLflow, imbalanced-learn |
| Frontend | React, Vite, Tailwind CSS |
| Infrastructure | AWS EC2, RDS, S3, VPC, Terraform |
| Security | Rate limiting, Bandit, security headers, Pydantic v2 |
| CI/CD | GitHub Actions |

---

## Project Structure

```
veridion/
├── backend/            # FastAPI application
│   ├── app/
│   │   ├── api/        # Endpoints (auth, transactions)
│   │   ├── core/       # JWT, security, config
│   │   ├── models/     # SQLAlchemy models
│   │   └── services/   # Business logic, fraud client
│   └── tests/          # 60+ tests
├── ml/                 # Fraud detection microservice
│   ├── src/            # FastAPI inference service
│   └── notebooks/      # Training script (Colab)
├── frontend/           # React dashboard
│   └── src/
│       ├── pages/      # Login, Register, Dashboard
│       ├── context/    # Auth context
│       └── services/   # API client
└── infrastructure/     # Terraform (AWS)
```

---

## Running Locally

**Prerequisites:** Docker Desktop, Node.js

```bash
# Clone the repo
git clone https://github.com/ishaanhari12/veridion.git
cd veridion

# Start backend + database + ML service
docker compose up

# Start frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173` for the dashboard.
API docs available at `http://localhost:8000/docs`.

---

## Key Engineering Decisions

**Fail-open fraud design** — if the ML service is unreachable, transactions are flagged for review rather than blocking all payments. A fraud service outage should never take down the payment system.

**ACID transactions** — every transfer debits the sender and credits the receiver in a single database transaction. Any failure rolls back completely — no partial transfers.

**Training-serving feature parity** — `ml/src/features.py` defines the exact feature set used at both training and inference time, preventing training-serving skew.

**Environment-aware rate limiting** — strict limits in production (10/min login), relaxed in development and test (1000/min) so tests are never blocked.

---

## Security

- JWT access and refresh tokens
- bcrypt password hashing (pinned to 4.0.1 for passlib compatibility)
- Role-based access control (user / analyst / admin)
- Rate limiting on all sensitive endpoints via slowapi
- SQL injection protection via Pydantic v2 validation
- Security headers middleware (X-Content-Type-Options, X-Frame-Options, etc.)
- Bandit static analysis in CI pipeline

See [docs/security.md](docs/security.md) for full details.

---

## Tests

```bash
docker compose exec api pytest tests/ -v
```

60+ tests covering auth flows, transaction logic, security headers, RBAC enforcement, injection attempts, and rate limiting.
