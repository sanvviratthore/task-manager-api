# Finance Dashboard API

A secure, role-based finance dashboard backend built on top of [Taskr API](https://github.com/sanvviratthore/task-manager-api).

**Live Demo:** https://task-manager-api-ubfp.onrender.com  
**Swagger UI:** https://task-manager-api-ubfp.onrender.com/docs

---

## How This Relates to the Assignment

This project was originally built as a general-purpose task management API with JWT auth, RBAC, rate limiting, and SQLite persistence. The finance assignment maps almost perfectly onto that foundation:

| Assignment Requirement | Status | Notes |
|---|---|---|
| User management (create, update, deactivate) | ✅ Already built | `/api/v1/users/` endpoints |
| Role-based access control (Viewer / Analyst / Admin) | ✅ Already built | `require_role()` guard in `auth.py` |
| Financial records CRUD | ✅ Added | `/api/v1/finance/` endpoints |
| Dashboard summary APIs | ✅ Added | `/api/v1/dashboard/` endpoints |
| Input validation | ✅ Already built | Pydantic v2 schemas |
| Soft delete | ✅ Added | `is_deleted` flag on records |
| Pagination | ✅ Added | `page` + `limit` query params |
| Rate limiting | ✅ Already built | Sliding-window, per-IP |
| JWT authentication | ✅ Already built | Access + refresh token strategy |
| SQLite persistence | ✅ Already built | Swappable via `DATABASE_URL` |

---

## Tech Stack

| Layer | Choice |
|---|---|
| Framework | FastAPI |
| Database | SQLite + SQLAlchemy (swap `DATABASE_URL` for Postgres in prod) |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| Rate Limiting | Custom in-memory sliding window |
| Validation | Pydantic v2 |

---

## Setup

```bash
# 1. Clone
git clone https://github.com/sanvviratthore/task-manager-api
cd task-manager-api

# 2. Virtual environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r backend/requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env — set a strong SECRET_KEY:
# python -c "import secrets; print(secrets.token_hex(32))"

# 5. Run
cd backend
uvicorn main:app --reload --port 8000
```

Swagger UI: http://localhost:8000/docs

---

## API Reference

### Auth

| Method | Endpoint | Rate Limited | Description |
|---|---|---|---|
| POST | `/api/v1/auth/register` | 3/5min | Create account |
| POST | `/api/v1/auth/login` | 5/60s | Login, get tokens |
| POST | `/api/v1/auth/refresh` | — | Refresh access token |
| POST | `/api/v1/auth/logout` | — | Revoke refresh token |

### Users

| Method | Endpoint | Role | Description |
|---|---|---|---|
| GET | `/api/v1/users/me` | Any | Own profile |
| PATCH | `/api/v1/users/me` | Any | Update own profile |
| GET | `/api/v1/users/` | Admin | List all users |
| PATCH | `/api/v1/users/{id}/role` | Admin | Change user role |
| DELETE | `/api/v1/users/{id}` | Admin | Deactivate user |

### Financial Records

| Method | Endpoint | Role | Description |
|---|---|---|---|
| POST | `/api/v1/finance/` | Admin | Create record |
| GET | `/api/v1/finance/` | Any | List records (with filters) |
| GET | `/api/v1/finance/{id}` | Any | Get single record |
| PATCH | `/api/v1/finance/{id}` | Admin | Update record |
| DELETE | `/api/v1/finance/{id}` | Admin | Soft-delete record |

**Filter query params for GET /finance/:**

| Param | Type | Example |
|---|---|---|
| `type` | `income` or `expense` | `?type=expense` |
| `category` | string | `?category=rent` |
| `date_from` | YYYY-MM-DD | `?date_from=2024-01-01` |
| `date_to` | YYYY-MM-DD | `?date_to=2024-03-31` |
| `page` | int (default 1) | `?page=2` |
| `limit` | int 1–100 (default 20) | `?limit=50` |

### Dashboard

| Method | Endpoint | Role | Description |
|---|---|---|---|
| GET | `/api/v1/dashboard/summary` | Any | Full summary (all stats combined) |
| GET | `/api/v1/dashboard/totals` | Any | Total income, expenses, net balance |
| GET | `/api/v1/dashboard/category-breakdown` | Any | Totals grouped by category |
| GET | `/api/v1/dashboard/monthly-trends` | Any | Monthly income vs expense trends |
| GET | `/api/v1/dashboard/recent` | Any | Last 10 records by date |

---

## Role Model

| Role | View Records | Dashboard | Create / Update | Delete | Manage Users |
|---|---|---|---|---|---|
| viewer | ✅ | ✅ | ❌ | ❌ | ❌ |
| analyst | ✅ | ✅ | ❌ | ❌ | ❌ |
| admin | ✅ | ✅ | ✅ | ✅ | ✅ |

Access control is enforced at the router level via the `require_role()` dependency in `auth.py`. Viewers and analysts are blocked at the API layer — not just the frontend.

---

## Data Model

### FinancialRecord

| Field | Type | Notes |
|---|---|---|
| `id` | int | Primary key |
| `amount` | float | Must be > 0 |
| `type` | enum | `income` or `expense` |
| `category` | string | Max 100 chars |
| `date` | date | YYYY-MM-DD |
| `notes` | string (optional) | Max 1000 chars |
| `is_deleted` | bool | Soft-delete flag |
| `created_by` | int | FK → users.id |
| `created_at` | datetime | Auto-set |
| `updated_at` | datetime | Auto-updated |

---

## Project Structure

```
task-manager-api/
├── backend/
│   ├── main.py           # App entry point, CORS, router registration
│   ├── database.py       # SQLAlchemy engine and session
│   ├── models.py         # User, RefreshToken, FinancialRecord ORM models
│   ├── schemas.py        # Pydantic request/response schemas
│   ├── auth.py           # JWT, bcrypt, RBAC dependencies
│   ├── rate_limit.py     # Sliding-window rate limiter
│   ├── routers/
│   │   ├── auth.py       # /auth/* endpoints
│   │   ├── users.py      # /users/* endpoints
│   │   ├── finance.py    # /finance/* endpoints  ← NEW
│   │   └── dashboard.py  # /dashboard/* endpoints ← NEW
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   └── dashboard.html
├── .env.example
└── README.md
```

---

## Assumptions & Tradeoffs

- **Soft delete over hard delete** — financial records are never truly removed; `is_deleted = True` hides them from all queries. This is standard for finance systems where audit trails matter.
- **Viewer and Analyst have identical read permissions** in this implementation. The role distinction is preserved in the DB and is easy to differentiate further (e.g., Analyst could get access to trend data while Viewer only sees recent records).
- **In-memory rate limiter** resets on server restart and doesn't scale across multiple processes. Swap with Redis + `slowapi` for production.
- **SQLite** is used for zero-setup local development. The `DATABASE_URL` env var makes it trivial to point at Postgres on Render or Railway.
- **Dashboard aggregation** is done in Python rather than raw SQL for readability. For large datasets, the category breakdown endpoint already uses a SQL `GROUP BY` query; monthly trends would also benefit from a SQL aggregate query at scale.

---

## Security Highlights

- Short-lived JWT access tokens (15 min) + revocable refresh tokens (7 days, stored in DB)
- bcrypt password hashing, minimum strength enforced at schema level
- Login errors are identical whether user exists or not (prevents enumeration)
- All user input validated by Pydantic before reaching route handlers
- Explicit CORS origin allowlist (never `*` in production)
