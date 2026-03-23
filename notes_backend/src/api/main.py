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

app = FastAPI(
    title="NoteMaster API",
    description=(
        "REST API for a notes application with tag management.\n\n"
        "Database: PostgreSQL (tables: notes, tags, note_tags)."
    ),
    version="1.0.0",
    openapi_tags=openapi_tags,
)

allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",") if os.getenv("ALLOWED_ORIGINS") else ["*"]
allowed_methods = os.getenv("ALLOWED_METHODS", "*").split(",") if os.getenv("ALLOWED_METHODS") else ["*"]
allowed_headers = os.getenv("ALLOWED_HEADERS", "*").split(",") if os.getenv("ALLOWED_HEADERS") else ["*"]
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
        "notes": "Backend will build a postgresql:// URL from POSTGRES_* if POSTGRES_URL is not set.",
    }


app.include_router(notes_router)
app.include_router(tags_router)
