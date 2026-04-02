from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from dotenv import load_dotenv

from database import engine, Base
from routers.auth import router as auth_router
from routers.users import router as users_router
from routers import finance, dashboard

load_dotenv()

# Create all tables on startup
Base.metadata.create_all(bind=engine)

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Taskr API",
    description="""
## Taskr REST API

A secure REST API with JWT authentication, refresh tokens, and role-based access control.

### Auth Flow
1. **Register** → `POST /auth/register`
2. **Login** → `POST /auth/login` → receive `access_token` + `refresh_token`
3. **Use API** → pass `Authorization: Bearer <access_token>` header
4. **Refresh** → `POST /auth/refresh` with `refresh_token` when access token expires
5. **Logout** → `POST /auth/logout` to revoke refresh token

### Roles
- **user** — can access their own profile
- **admin** — can list, update, and deactivate any user
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS — restrictive by default ─────────────────────────────────────────────
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:8000,http://127.0.0.1:8000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # Never use ["*"] in production
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")

app.include_router(finance.router)
app.include_router(dashboard.router)

# ── Serve Frontend ─────────────────────────────────────────────────────────────
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.get("/", include_in_schema=False)
def serve_frontend():
    index = os.path.join(frontend_path, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    return {"message": "Taskr API is running. Visit /docs for the API reference."}

# ── Health Check ───────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}
