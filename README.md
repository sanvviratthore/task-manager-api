# Finance Dashboard API

A secure, role-based finance dashboard backend built with FastAPI, PostgreSQL, JWT authentication, and RBAC.

**Live Demo:** https://task-manager-api-ubfp.onrender.com  
**Swagger UI:** https://task-manager-api-ubfp.onrender.com/docs

---

## Overview

This project was originally built as a task management API with JWT auth, RBAC, and rate limiting. It was extended into a full finance dashboard backend — covering financial records management, dashboard analytics, and multi-role access control — for a backend engineering assignment.

| Assignment Requirement | Status | Notes |
|---|---|---|
| User management (create, update, deactivate) | ✅ | `/api/v1/users/` endpoints |
| Role-based access control (Viewer / Analyst / Admin) | ✅ | `require_role()` guard in `auth.py` |
| Financial records CRUD | ✅ | `/api/v1/finance/` endpoints |
| Dashboard summary APIs | ✅ | `/api/v1/dashboard/` endpoints |
| Input validation | ✅ | Pydantic v2 schemas with custom validators |
| Optimistic locking | ✅ | `version` field on `FinancialRecord` prevents lost updates |
| Pagination | ✅ | `page` + `limit` query params on record listing |
| Rate limiting | ✅ | Sliding-window per-IP limiter |
| JWT authentication | ✅ | Short-lived access tokens + revocable refresh tokens |
| PostgreSQL persistence | ✅ | Deployed on Render with persistent Postgres |

---

## Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| Framework | FastAPI | Auto Swagger docs, async-ready, Pydantic built-in |
| Database | PostgreSQL + SQLAlchemy | Persistent, production-grade, swappable via `DATABASE_URL` |
| Auth | python-jose (JWT) + passlib (bcrypt) | Industry-standard JWT, secure password hashing |
| Rate Limiting | Custom in-memory sliding window | No Redis dependency; swappable for production |
| Validation | Pydantic v2 | Schema-level sanitization on every request |

---

## Setup

```bash
# 1. Clone
git clone https://github.com/sanvviratthore/task-manager-api
cd task-manager-api

# 2. Virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r backend/requirements.txt

# 4. Configure environment
cp .env.example .env
# Generate a strong secret key:
# python -c "import secrets; print(secrets.token_hex(32))"

# 5. Run
cd backend
uvicorn main:app --reload --port 8000
```

- **Frontend:** http://localhost:8000
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

> Uses SQLite locally by default. Set `DATABASE_URL` to a PostgreSQL connection string for production.

---

## API Reference

### Auth

| Method | Endpoint | Rate Limited | Description |
|---|---|---|---|
| POST | `/api/v1/auth/register` | 3/5min | Create account (first user gets admin) |
| POST | `/api/v1/auth/login` | 5/60s | Login, receive access + refresh tokens |
| POST | `/api/v1/auth/refresh` | — | Refresh access token |
| POST | `/api/v1/auth/logout` | — | Revoke current session |
| POST | `/api/v1/auth/logout-all` | — | Revoke all sessions (all devices) |
| GET | `/api/v1/auth/sessions` | — | List active sessions |
| POST | `/api/v1/auth/password-reset` | 3/5min | Request password reset (rate-limited) |

### Users

| Method | Endpoint | Role | Description |
|---|---|---|---|
| GET | `/api/v1/users/me` | Any | Get own profile |
| PATCH | `/api/v1/users/me` | Any | Update own profile |
| GET | `/api/v1/users/` | Admin | List all users |
| GET | `/api/v1/users/{id}` | Admin | Get user by ID |
| PATCH | `/api/v1/users/{id}/role` | Admin | Change user role |
| DELETE | `/api/v1/users/{id}` | Admin | Deactivate user |

### Financial Records

| Method | Endpoint | Role | Description |
|---|---|---|---|
| POST | `/api/v1/finance/` | Admin | Create a record |
| GET | `/api/v1/finance/` | Any | List records (filterable, paginated) |
| GET | `/api/v1/finance/{id}` | Any | Get a single record |
| PATCH | `/api/v1/finance/{id}` | Admin | Update record (optimistic locking) |
| DELETE | `/api/v1/finance/{id}` | Admin | Delete record |

**Filters for `GET /api/v1/finance/`:**

| Param | Type | Example |
|---|---|---|
| `type` | `income` or `expense` | `?type=expense` |
| `category` | string (partial match) | `?category=rent` |
| `date_from` | YYYY-MM-DD | `?date_from=2024-01-01` |
| `date_to` | YYYY-MM-DD | `?date_to=2024-03-31` |
| `page` | int (default 1) | `?page=2` |
| `limit` | int 1–100 (default 20) | `?limit=50` |

### Dashboard

| Method | Endpoint | Role | Description |
|---|---|---|---|
| GET | `/api/v1/dashboard/summary` | Any | Full summary — totals, trends, categories, recent |
| GET | `/api/v1/dashboard/totals` | Any | Total income, expenses, net balance |
| GET | `/api/v1/dashboard/category-breakdown` | Any | Per-category totals |
| GET | `/api/v1/dashboard/monthly-trends` | Any | Monthly income vs expense trends |
| GET | `/api/v1/dashboard/recent` | Any | Last 10 records |

---

## Role Model

| Role | View Records | Dashboard | Create / Update | Delete | Manage Users |
|---|---|---|---|---|---|
| viewer | ✅ | ✅ | ❌ | ❌ | ❌ |
| analyst | ✅ | ✅ | ❌ | ❌ | ❌ |
| admin | ✅ | ✅ | ✅ | ✅ | ✅ |

Access control is enforced at the router layer via FastAPI dependencies — not just the frontend. Unauthorized requests return `403 Forbidden` before any business logic runs.

The first user to register automatically receives the `admin` role.

---

## Data Models

### User

| Field | Type | Notes |
|---|---|---|
| `id` | int | Primary key |
| `email` | string | Unique, validated |
| `username` | string | Unique, alphanumeric + `_` `-` |
| `hashed_password` | string | bcrypt |
| `role` | enum | `viewer`, `analyst`, `admin` |
| `is_active` | bool | Soft-disable via admin |
| `created_at` / `updated_at` | datetime | Auto-managed |
| `created_by` / `updated_by` | int | Audit trail |

### FinancialRecord

| Field | Type | Notes |
|---|---|---|
| `id` | int | Primary key |
| `amount` | float | Must be > 0, max 10,000,000 |
| `type` | enum | `income` or `expense` |
| `category` | string | Max 100 chars |
| `date` | string | YYYY-MM-DD format |
| `notes` | string (optional) | Max 500 chars |
| `user_id` | int | FK → users.id |
| `version` | int | Optimistic locking counter |
| `created_at` / `updated_at` | datetime | Auto-managed |
| `created_by` / `updated_by` | int | Audit trail |

### UserSession

| Field | Type | Notes |
|---|---|---|
| `id` | int | Primary key |
| `token` | string | Refresh token value |
| `user_id` | int | FK → users.id |
| `ip_address` | string | For session visibility |
| `user_agent` | string | Device info |
| `expires_at` | datetime | 7-day TTL |
| `revoked` | bool | Logout flag |

---

## Project Structure

```
task-manager-api/
├── backend/
│   ├── main.py                      # App entry, CORS, router registration
│   ├── database.py                  # SQLAlchemy engine, session, Base
│   ├── auth.py                      # JWT decode, RBAC dependencies
│   ├── models/
│   │   ├── __init__.py              # Re-exports all models
│   │   ├── user.py                  # User, UserSession, RoleEnum, AuditMixin
│   │   └── financial.py             # FinancialRecord, RecordTypeEnum
│   ├── schemas/
│   │   ├── __init__.py              # Re-exports all schemas
│   │   ├── auth.py                  # Register, Login, Token schemas
│   │   ├── user.py                  # UserOut, UserUpdate, RoleUpdate
│   │   └── financial.py             # FinancialRecord + Dashboard schemas
│   ├── routers/
│   │   ├── auth.py                  # /auth/* endpoints
│   │   ├── users.py                 # /users/* endpoints
│   │   ├── finance.py               # /finance/* endpoints
│   │   └── dashboard.py             # /dashboard/* endpoints
│   ├── services/
│   │   ├── interfaces.py            # Abstract base classes
│   │   ├── jwt_auth_service.py      # JWT implementation
│   │   └── rate_limiter_service.py  # In-memory sliding window
│   └── requirements.txt
├── frontend/
│   ├── index.html                   # Login / Register (auto-login + forgot password)
│   └── dashboard.html               # Finance dashboard UI
├── .env.example
└── README.md
```

---

## Assumptions & Tradeoffs

- **Optimistic locking** on `FinancialRecord` via a `version` field — updates require the client to send the current version, preventing lost updates when two users edit simultaneously. Returns `409 Conflict` on mismatch.
- **Viewer and Analyst have identical read permissions** in this implementation. The distinction is preserved in the DB and easy to extend.
- **In-memory rate limiter** resets on server restart and doesn't work across multiple instances. Swap with Redis + `slowapi` for production.
- **Dashboard aggregation** is done in Python for readability. For large datasets, SQL-level aggregates would be more efficient.
- **Service layer abstraction** — `AuthServiceBase` and `RateLimiterBase` interfaces mean swapping JWT for sessions, or in-memory rate limiting for Redis, requires only changing the concrete implementation — no route changes needed.

---

## Security Highlights

- Access tokens expire in 15 minutes; refresh tokens expire in 7 days and are stored in DB so they can be revoked individually or all at once
- bcrypt password hashing with minimum strength enforced at schema level (8+ chars, 1 uppercase, 1 digit)
- Login failures return identical errors whether the user exists or not — prevents user enumeration
- All input validated by Pydantic v2 before reaching route handlers
- Explicit CORS allowlist configured via `ALLOWED_ORIGINS` env var
- Token type (`access` / `refresh`) embedded in payload — prevents using a refresh token as an access token
