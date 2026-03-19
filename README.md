# Taskr API — Full-Stack REST API with Auth & Rate Limiting

A secure REST API built with FastAPI, JWT authentication, refresh tokens, role-based access control, and rate limiting — plus a minimal frontend.

## Live Demo

> Paste your deployed backend URL here (e.g. https://taskr-api.onrender.com)

**API Docs (Swagger):** `<your-url>/docs`

---

## Tech Stack

| Layer | Choice | Reason |
|-------|--------|--------|
| Framework | FastAPI | Auto Swagger docs, async-ready, Pydantic validation built-in |
| Database | SQLite + SQLAlchemy | Zero setup for local dev; swap `DATABASE_URL` for Postgres in prod |
| Auth | python-jose (JWT) + passlib (bcrypt) | Industry-standard JWT, bcrypt for password hashing |
| Rate Limiting | Custom in-memory sliding window | No Redis dependency for this scope; production note below |
| Validation | Pydantic v2 | Schema-level sanitization on every request |

---

## Setup

### 1. Clone and enter the project

```bash
cd task-manager-api
```

### 2. Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r backend/requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set a strong `SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 5. Run the server

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Visit:
- **Frontend:** http://localhost:8000
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## API Reference

### Auth Endpoints

| Method | Endpoint | Rate Limited | Description |
|--------|----------|-------------|-------------|
| POST | `/api/v1/auth/register` | ✅ 3/5min | Create account |
| POST | `/api/v1/auth/login` | ✅ 5/60s | Login, get tokens |
| POST | `/api/v1/auth/refresh` | — | Refresh access token |
| POST | `/api/v1/auth/logout` | — | Revoke refresh token |
| POST | `/api/v1/auth/password-reset` | ✅ 3/5min | Request password reset |

### User Endpoints

| Method | Endpoint | Role Required | Description |
|--------|----------|--------------|-------------|
| GET | `/api/v1/users/me` | Any | Get own profile |
| PATCH | `/api/v1/users/me` | Any | Update own profile |
| GET | `/api/v1/users/` | Admin | List all users |
| GET | `/api/v1/users/{id}` | Admin | Get user by ID |
| PATCH | `/api/v1/users/{id}/role` | Admin | Update user role |
| DELETE | `/api/v1/users/{id}` | Admin | Deactivate user |

---

## Security Decisions & Tradeoffs

### JWT Strategy
- **Access tokens** expire in 15 minutes (short-lived, stateless)
- **Refresh tokens** expire in 7 days, stored in the database so they can be revoked
- Token type (`access` / `refresh`) is embedded in the payload — prevents using a refresh token as an access token
- Tokens are signed with HS256 using a strong random secret key

### Password Security
- bcrypt hashing via `passlib` with default work factor (12 rounds)
- Password strength enforced at schema level: min 8 chars, 1 uppercase, 1 digit
- Login failures return the same error whether the user exists or not (prevents user enumeration)

### Rate Limiting
- Implemented as a per-IP sliding window counter in memory
- Sensitive endpoints protected: login (5/min), register (3/5min), password-reset (3/5min)
- **Tradeoff:** In-memory store resets on server restart and doesn't work across multiple instances. For production, swap with Redis + `slowapi`.

### CORS
- `ALLOWED_ORIGINS` is explicit and configurable via `.env`
- Never uses `allow_origins=["*"]` — that would allow any domain to call the API with credentials

### Input Validation
- All request bodies validated by Pydantic v2 schemas before reaching route handlers
- Email validated with `pydantic[email]`
- Username sanitized: alphanumeric + `_` and `-` only
- All user-generated content rendered via `textContent` in the frontend (XSS prevention)

### What I'd Add in Production
- Redis for distributed rate limiting
- SMTP email verification on registration
- HTTPS-only cookie storage for refresh tokens (instead of localStorage)
- Argon2 password hashing (stronger than bcrypt)
- Structured logging with request IDs

---

## Deployment (Render)

1. Push to GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your repo
4. Set:
   - **Root Directory:** `backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables from `.env.example` in the Render dashboard
6. Deploy

---

## Project Structure

```
task-manager-api/
├── backend/
│   ├── main.py          # App entry point, CORS, router registration
│   ├── database.py      # SQLAlchemy engine and session
│   ├── models.py        # User and RefreshToken ORM models
│   ├── schemas.py       # Pydantic request/response schemas
│   ├── auth.py          # JWT, password hashing, RBAC dependencies
│   ├── rate_limit.py    # Sliding-window rate limiter
│   ├── routers/
│   │   ├── auth.py      # /auth/* endpoints
│   │   └── users.py     # /users/* endpoints
│   └── requirements.txt
├── frontend/
│   ├── index.html       # Login / Register page
│   └── dashboard.html   # Protected user dashboard
├── .env.example
├── .gitignore
└── README.md
```
