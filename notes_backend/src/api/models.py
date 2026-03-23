from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class Tag(BaseModel):
    """A tag object."""

    id: UUID = Field(..., description="Tag UUID.")
    name: str = Field(..., min_length=1, max_length=64, description="Unique tag name.")
    created_at: datetime = Field(..., description="Timestamp when the tag was created.")


class TagCreate(BaseModel):
    """Payload to create a new tag."""

    name: str = Field(..., min_length=1, max_length=64, description="Unique tag name.")

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        """Normalize tag name for uniqueness and UX consistency."""
        return v.strip()


class TagUpdate(BaseModel):
    """Payload to update an existing tag."""

    name: str = Field(..., min_length=1, max_length=64, description="Unique tag name.")

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        """Normalize tag name for uniqueness and UX consistency."""
        return v.strip()


class NoteBase(BaseModel):
    """Common fields for notes."""

    title: str = Field(..., min_length=1, max_length=200, description="Note title.")
    content: str = Field(..., min_length=1, max_length=50_000, description="Note content (markdown/plain text).")


class NoteCreate(NoteBase):
    """Payload to create a note."""

    tag_ids: list[UUID] = Field(default_factory=list, description="Optional list of tag UUIDs to assign on creation.")


class NoteUpdate(BaseModel):
    """Payload to update a note."""

    title: Optional[str] = Field(None, min_length=1, max_length=200, description="Updated note title.")
    content: Optional[str] = Field(None, min_length=1, max_length=50_000, description="Updated note content.")

    @field_validator("title")
    @classmethod
    def strip_title(cls, v: Optional[str]) -> Optional[str]:
        """Trim title if provided."""
        return v.strip() if isinstance(v, str) else v


class Note(BaseModel):
    """A note object, optionally with tags."""

    id: UUID = Field(..., description="Note UUID.")
    title: str = Field(..., description="Note title.")
    content: str = Field(..., description="Note content.")
    created_at: datetime = Field(..., description="Timestamp when the note was created.")
    updated_at: datetime = Field(..., description="Timestamp when the note was last updated.")
    tags: list[Tag] = Field(default_factory=list, description="Tags assigned to the note.")


class NoteListResponse(BaseModel):
    """List response wrapper for notes."""

    items: list[Note] = Field(..., description="List of notes.")
    total: int = Field(..., ge=0, description="Total number of matching notes.")
    limit: int = Field(..., ge=1, le=200, description="Page size.")
    offset: int = Field(..., ge=0, description="Pagination offset.")


class TagListResponse(BaseModel):
    """List response wrapper for tags."""

    items: list[Tag] = Field(..., description="List of tags.")
    total: int = Field(..., ge=0, description="Total number of matching tags.")
