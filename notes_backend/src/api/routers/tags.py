from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query, status

from src.api.models import Tag, TagCreate, TagListResponse, TagUpdate
from src.db.connection import get_connection
from src.db.repositories import TagsRepository

router = APIRouter(prefix="/tags", tags=["tags"])

_tags = TagsRepository()


@router.post(
    "",
    response_model=Tag,
    status_code=status.HTTP_201_CREATED,
    summary="Create a tag",
    description="Create a new tag with a unique name.",
    operation_id="create_tag",
)
def create_tag(payload: TagCreate) -> Tag:
    conn = get_connection()
    try:
        with conn.transaction():
            return _tags.create(conn, name=payload.name)
    finally:
        conn.close()


@router.get(
    "",
    response_model=TagListResponse,
    summary="List/search tags",
    description="List all tags, optionally filtering by name query.",
    operation_id="list_tags",
)
def list_tags(q: Optional[str] = Query(None, description="Optional search query for tag name.")) -> TagListResponse:
    conn = get_connection()
    try:
        items, total = _tags.list(conn, q=q)
        return TagListResponse(items=items, total=total)
    finally:
        conn.close()


@router.get(
    "/{tag_id}",
    response_model=Tag,
    summary="Get a tag",
    description="Fetch a tag by id.",
    operation_id="get_tag",
)
def get_tag(tag_id: UUID) -> Tag:
    conn = get_connection()
    try:
        return _tags.get(conn, tag_id)
    finally:
        conn.close()


@router.put(
    "/{tag_id}",
    response_model=Tag,
    summary="Update a tag",
    description="Update a tag's name.",
    operation_id="update_tag",
)
def update_tag(tag_id: UUID, payload: TagUpdate) -> Tag:
    conn = get_connection()
    try:
        with conn.transaction():
            return _tags.update(conn, tag_id=tag_id, name=payload.name)
    finally:
        conn.close()


@router.delete(
    "/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a tag",
    description="Delete a tag and remove its assignments from notes.",
    operation_id="delete_tag",
)
def delete_tag(tag_id: UUID) -> None:
    conn = get_connection()
    try:
        with conn.transaction():
            _tags.delete(conn, tag_id)
        return None
    finally:
        conn.close()
