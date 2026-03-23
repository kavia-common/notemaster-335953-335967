import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers.notes import router as notes_router
from src.api.routers.tags import router as tags_router

openapi_tags = [
    {"name": "meta", "description": "Health and service metadata endpoints."},
    {"name": "notes", "description": "Create, update, delete, list and search notes."},
    {"name": "tags", "description": "Create, update, delete, list and search tags."},
]


def _split_env_csv(name: str, default: list[str]) -> list[str]:
    """
    Split a CSV env var into a list of stripped items, dropping empty entries.

    This avoids common CORS misconfigurations (e.g. trailing commas resulting in empty origins).
    """
    raw = os.getenv(name)
    if raw is None:
        return default
    items = [x.strip() for x in raw.split(",")]
    return [x for x in items if x]


app = FastAPI(
    title="NoteMaster API",
    description=(
        "REST API for a notes application with tag management.\n\n"
        "Database: PostgreSQL (tables: notes, tags, note_tags)."
    ),
    version="1.0.0",
    openapi_tags=openapi_tags,
)

allowed_origins = _split_env_csv("ALLOWED_ORIGINS", ["*"])
allowed_methods = _split_env_csv("ALLOWED_METHODS", ["*"])
allowed_headers = _split_env_csv("ALLOWED_HEADERS", ["*"])
cors_max_age = int(os.getenv("CORS_MAX_AGE", "600"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=allowed_methods,
    allow_headers=allowed_headers,
    max_age=cors_max_age,
)


@app.get("/", tags=["meta"], summary="Health check", operation_id="health_check")
# PUBLIC_INTERFACE
def health_check():
    """Health check endpoint used by orchestration and uptime monitoring."""
    return {"message": "Healthy"}


@app.get("/docs/db", tags=["meta"], summary="Database configuration help", operation_id="db_config_help")
# PUBLIC_INTERFACE
def db_config_help():
    """
    Describe how the API connects to the PostgreSQL database.

    Returns:
        Connection expectations for runtime environment variables.
    """
    return {
        "expects": ["POSTGRES_URL or POSTGRES_USER/POSTGRES_PASSWORD/POSTGRES_DB/POSTGRES_PORT"],
        "example_psql_cmd_source": "notes_database/db_connection.txt (container guidance)",
        "notes": (
            "Backend will build a postgresql:// URL from POSTGRES_* if POSTGRES_URL is not set. "
            "If POSTGRES_URL starts with postgres:// it will be normalized to postgresql://."
        ),
    }


@app.get(
    "/docs/local-preview",
    tags=["meta"],
    summary="Local preview wiring help",
    description="How to point the Next.js frontend to this backend and configure CORS.",
    operation_id="local_preview_help",
)
# PUBLIC_INTERFACE
def local_preview_help():
    """
    Describe the minimal environment variables needed for an end-to-end local preview.

    Returns:
        A small checklist for backend/frontend wiring.
    """
    return {
        "backend": {
            "cors": {
                "ALLOWED_ORIGINS": "Comma-separated list of allowed frontend origins (no spaces).",
                "example": "http://localhost:3000,https://<your-preview-host>:3000",
            },
            "database": {"see": "/docs/db"},
        },
        "frontend": {
            "NEXT_PUBLIC_NOTES_API_BASE_URL": (
                "Base URL to backend (no trailing slash), e.g. http://localhost:3001"
            )
        },
        "notes": "Frontend expects backend endpoints at /notes and /tags.",
    }


app.include_router(notes_router)
app.include_router(tags_router)
