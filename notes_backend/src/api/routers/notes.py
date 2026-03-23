from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query, status

from src.api.models import Note, NoteCreate, NoteListResponse, NoteUpdate
from src.db.connection import get_connection
from src.db.repositories import NoteTagsRepository, NotesRepository, TagsRepository

router = APIRouter(prefix="/notes", tags=["notes"])

_notes = NotesRepository()
_tags = TagsRepository()
_note_tags = NoteTagsRepository()


@router.post(
    "",
    response_model=Note,
    status_code=status.HTTP_201_CREATED,
    summary="Create a note",
    description="Create a new note, optionally assigning tags by tag_ids.",
    operation_id="create_note",
)
def create_note(payload: NoteCreate) -> Note:
    conn = get_connection()
    try:
        with conn.transaction():
            note = _notes.create(conn, title=payload.title, content=payload.content)
            for tag_id in payload.tag_ids:
                _tags.ensure_exists(conn, tag_id)
                _note_tags.assign(conn, UUID(note["id"]), tag_id)
            # Reload to include assigned tags
            return _notes.get(conn, UUID(note["id"]))
    finally:
        conn.close()


@router.get(
    "",
    response_model=NoteListResponse,
    summary="List/search notes",
    description="List notes with optional free-text search and optional filtering by tag_id.",
    operation_id="list_notes",
)
def list_notes(
    q: Optional[str] = Query(None, description="Optional search query (matches title/content)."),
    tag_id: Optional[UUID] = Query(None, description="Optional tag UUID to filter notes."),
    limit: int = Query(20, ge=1, le=200, description="Page size."),
    offset: int = Query(0, ge=0, description="Pagination offset."),
) -> NoteListResponse:
    conn = get_connection()
    try:
        items, total = _notes.list(conn, q=q, tag_id=tag_id, limit=limit, offset=offset)
        return NoteListResponse(items=items, total=total, limit=limit, offset=offset)
    finally:
        conn.close()


@router.get(
    "/{note_id}",
    response_model=Note,
    summary="Get a note",
    description="Fetch a note by id, including its assigned tags.",
    operation_id="get_note",
)
def get_note(note_id: UUID) -> Note:
    conn = get_connection()
    try:
        return _notes.get(conn, note_id)
    finally:
        conn.close()


@router.put(
    "/{note_id}",
    response_model=Note,
    summary="Update a note",
    description="Update the title and/or content of a note.",
    operation_id="update_note",
)
def update_note(note_id: UUID, payload: NoteUpdate) -> Note:
    conn = get_connection()
    try:
        with conn.transaction():
            return _notes.update(conn, note_id=note_id, title=payload.title, content=payload.content)
    finally:
        conn.close()


@router.delete(
    "/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a note",
    description="Delete a note and its tag assignments.",
    operation_id="delete_note",
)
def delete_note(note_id: UUID) -> None:
    conn = get_connection()
    try:
        with conn.transaction():
            _notes.delete(conn, note_id)
        return None
    finally:
        conn.close()


@router.post(
    "/{note_id}/tags/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Assign tag to note",
    description="Assign a tag to a note (idempotent).",
    operation_id="assign_tag_to_note",
)
def assign_tag_to_note(note_id: UUID, tag_id: UUID) -> None:
    conn = get_connection()
    try:
        with conn.transaction():
            _note_tags.assign(conn, note_id=note_id, tag_id=tag_id)
        return None
    finally:
        conn.close()


@router.delete(
    "/{note_id}/tags/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove tag from note",
    description="Remove a tag assignment from a note (idempotent).",
    operation_id="remove_tag_from_note",
)
def remove_tag_from_note(note_id: UUID, tag_id: UUID) -> None:
    conn = get_connection()
    try:
        with conn.transaction():
            _note_tags.remove(conn, note_id=note_id, tag_id=tag_id)
        return None
    finally:
        conn.close()
