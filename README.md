# Veridion — Fintech Fraud Detection Platform

> Full-stack fintech platform with real-time ML fraud detection, enterprise-grade security, and AWS deployment.

## Quick Start

```bash
# 1. Copy and configure env
cp backend/.env.example backend/.env
# Open backend/.env and set SECRET_KEY (instructions inside)

# 2. Start the full stack
docker compose up --build

# 3. Run database migrations (new terminal, while stack is running)
docker exec veridion_api alembic upgrade head

# 4. Open interactive API docs
open http://localhost:8000/docs
```

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI, SQLAlchemy, Alembic |
| Auth | JWT (PyJWT), bcrypt, RBAC |
| Database | PostgreSQL |
| ML | Scikit-learn, XGBoost, MLflow (Phase 4) |
| Frontend | React, Tailwind (Phase 5) |
| Cloud | AWS + Terraform (Phase 6) |
| DevOps | Docker, GitHub Actions |
