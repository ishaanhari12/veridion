# Security Documentation

## Overview

Veridion implements security practices aligned with OWASP Top 10 and
standards encouraged by ISC² for fintech applications.

---

## Authentication & Authorisation

### JWT Authentication
- Every protected endpoint requires a valid JWT access token
- Access tokens expire after 30 minutes
- Refresh tokens expire after 7 days
- Tokens are signed with HS256 using a secret key stored in environment variables — never hardcoded

### Role-Based Access Control (RBAC)
Three roles with escalating permissions:

| Role | Can do |
|---|---|
| `user` | Deposit, withdraw, transfer, view own history |
| `analyst` | All user permissions + review and update flagged transactions |
| `admin` | All analyst permissions + full system access |

### Password Security
- Passwords hashed with bcrypt (cost factor 12)
- Minimum 8 characters, requires uppercase and number
- Hashed password never returned in any API response
- Login error messages are identical whether the email exists or not (prevents user enumeration)

---

## Rate Limiting

All endpoints are rate limited per IP address using slowapi:

| Endpoint | Limit | Reason |
|---|---|---|
| POST /auth/register | 10/minute | Prevent account spam |
| POST /auth/login | 10/minute | Prevent brute force |
| POST /auth/refresh | 20/minute | Prevent token farming |
| POST /transactions/deposit | 30/minute | Normal usage headroom |
| POST /transactions/withdraw | 30/minute | Normal usage headroom |
| POST /transactions/transfer | 20/minute | Lower limit — fraud risk |
| All other endpoints | 60/minute | Global default |

Exceeding a rate limit returns `429 Too Many Requests`.

---

## Security Headers

Every API response includes these headers:

| Header | Value | Protects Against |
|---|---|---|
| X-Content-Type-Options | nosniff | MIME sniffing attacks |
| X-Frame-Options | DENY | Clickjacking |
| Strict-Transport-Security | max-age=31536000 | Forces HTTPS for 1 year |
| Content-Security-Policy | default-src 'self' | XSS, data injection |
| Referrer-Policy | strict-origin-when-cross-origin | Information leakage |
| Permissions-Policy | geolocation=(), microphone=(), camera=() | Browser feature abuse |

---

## Input Validation

All request data is validated through Pydantic v2 before reaching business logic:
- Email addresses validated with email-validator
- Amounts validated as positive decimals within defined limits
- Strings length-checked and type-enforced
- SQL injection protection via SQLAlchemy parameterised queries
- No raw SQL strings anywhere in the codebase

---

## Audit Logging

Every sensitive action is recorded in the `audit_logs` table:
- User registration and login
- Every deposit, withdrawal, and transfer
- Fraud scoring decisions (blocked/flagged/completed)
- Admin status overrides

Each log entry includes: user ID, action, resource, resource ID, IP address, timestamp, and details.

---

## Security Scanning

### Bandit (Static Analysis)
Bandit scans the codebase for common Python security mistakes.
Run in CI on every push. Zero high-severity findings required to pass.

```bash
bandit -r backend/app -ll -ii
```

### OWASP ZAP (Dynamic Analysis)
OWASP ZAP scans the running API for vulnerabilities.
Run manually against the local stack. Results documented below.

---

## Secrets Management

- All secrets stored in environment variables — never in code
- `.env` file is gitignored and never committed
- Production secrets managed via AWS Secrets Manager (Phase 6)
- Secret key generated with `python -c "import secrets; print(secrets.token_hex(32))"`

---

## Data Protection

- Sensitive data encrypted at rest via PostgreSQL (AWS RDS encryption in Phase 6)
- All inter-service communication over HTTPS in production
- Database credentials rotated per environment (dev/staging/prod)
