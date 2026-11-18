"""TaskTracker - multi-tenant REST API (Lab 15.1)."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .db import get_db, init_indexes
from .routes_auth import router as auth_router
from .routes_tasks import router as tasks_router

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("tasktracker")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_indexes()
    except Exception:  # keep the API up so /health can report the problem
        log.exception("Could not create indexes - is MongoDB reachable at %s ?", config.MONGO_URI)
    yield


app = FastAPI(
    title="TaskTracker Multi-Tenant API",
    version="1.0.0",
    description=(
        "Lab 15.1 - document-level tenant isolation (tenant_id on every document), JWT auth, "
        "role-based access control and MongoDB-backed rate limiting.\n\n"
        "**Quick start:** `POST /tenants` -> `POST /auth/login` -> click *Authorize* and paste the token."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(tasks_router)


@app.get("/health", tags=["system"])
def health():
    try:
        get_db().command("ping")
        return {"status": "ok", "database": "up"}
    except Exception as exc:
        return {"status": "degraded", "database": "down", "error": str(exc)[:200]}
