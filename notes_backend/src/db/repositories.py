from __future__ import annotations

from typing import Optional
from uuid import UUID

import psycopg

from src.api.errors import conflict, not_found
from src.db.connection import execute, fetch_all, fetch_one


def _get_note_tags(conn: psycopg.Connection, note_id: UUID) -> list[dict]:
    return fetch_all(
        conn,
        """
        SELECT t.id, t.name, t.created_at
        FROM note_tags nt
        JOIN tags t ON t.id = nt.tag_id
        WHERE nt.note_id = %(note_id)s
        ORDER BY t.name ASC
        """,
        {"note_id": note_id},
    )


def _note_row_to_note(conn: psycopg.Connection, row: dict) -> dict:
    note_id = row["id"]
    return {
        "id": note_id,
        "title": row["title"],
        "content": row["content"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "tags": _get_note_tags(conn, note_id),
    }


class NotesRepository:
    """Data access for notes."""

    def create(self, conn: psycopg.Connection, title: str, content: str) -> dict:
        row = fetch_one(
            conn,
            """
            INSERT INTO notes (title, content)
            VALUES (%(title)s, %(content)s)
            RETURNING id, title, content, created_at, updated_at
            """,
            {"title": title, "content": content},
        )
        assert row is not None
        return _note_row_to_note(conn, row)

    def get(self, conn: psycopg.Connection, note_id: UUID) -> dict:
        row = fetch_one(
            conn,
            """
            SELECT id, title, content, created_at, updated_at
            FROM notes
            WHERE id = %(id)s
            """,
            {"id": note_id},
        )
        if not row:
            raise not_found("Note not found")
        return _note_row_to_note(conn, row)

    def update(self, conn: psycopg.Connection, note_id: UUID, title: Optional[str], content: Optional[str]) -> dict:
        existing = fetch_one(conn, "SELECT id FROM notes WHERE id=%(id)s", {"id": note_id})
        if not existing:
            raise not_found("Note not found")

        row = fetch_one(
            conn,
            """
            UPDATE notes
            SET
              title = COALESCE(%(title)s, title),
              content = COALESCE(%(content)s, content)
            WHERE id = %(id)s
            RETURNING id, title, content, created_at, updated_at
            """,
            {"id": note_id, "title": title, "content": content},
        )
        assert row is not None
        return _note_row_to_note(conn, row)

    def delete(self, conn: psycopg.Connection, note_id: UUID) -> None:
        rc = execute(conn, "DELETE FROM notes WHERE id=%(id)s", {"id": note_id})
        if rc == 0:
            raise not_found("Note not found")

    def list(
        self,
        conn: psycopg.Connection,
        q: Optional[str],
        tag_id: Optional[UUID],
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        where = []
        params: dict = {"limit": limit, "offset": offset}

        if q:
            params["q"] = q
            where.append("(title ILIKE ('%' || %(q)s || '%') OR content ILIKE ('%' || %(q)s || '%'))")

        if tag_id:
            params["tag_id"] = tag_id
            where.append(
                """id IN (
                    SELECT note_id FROM note_tags WHERE tag_id = %(tag_id)s
                )"""
            )

        where_sql = ("WHERE " + " AND ".join(where)) if where else ""

        total_row = fetch_one(conn, f"SELECT count(*)::int AS total FROM notes {where_sql}", params)
        total = int(total_row["total"]) if total_row else 0

        rows = fetch_all(
            conn,
            f"""
            SELECT id, title, content, created_at, updated_at
            FROM notes
            {where_sql}
            ORDER BY updated_at DESC
            LIMIT %(limit)s OFFSET %(offset)s
            """,
            params,
        )

        return ([_note_row_to_note(conn, r) for r in rows], total)


class TagsRepository:
    """Data access for tags."""

    def create(self, conn: psycopg.Connection, name: str) -> dict:
        try:
            row = fetch_one(
                conn,
                """
                INSERT INTO tags (name)
                VALUES (%(name)s)
                RETURNING id, name, created_at
                """,
                {"name": name},
            )
        except psycopg.errors.UniqueViolation:
            raise conflict("Tag name already exists") from None
        assert row is not None
        return row

    def get(self, conn: psycopg.Connection, tag_id: UUID) -> dict:
        row = fetch_one(conn, "SELECT id, name, created_at FROM tags WHERE id=%(id)s", {"id": tag_id})
        if not row:
            raise not_found("Tag not found")
        return row

    def update(self, conn: psycopg.Connection, tag_id: UUID, name: str) -> dict:
        try:
            row = fetch_one(
                conn,
                """
                UPDATE tags
                SET name=%(name)s
                WHERE id=%(id)s
                RETURNING id, name, created_at
                """,
                {"id": tag_id, "name": name},
            )
        except psycopg.errors.UniqueViolation:
            raise conflict("Tag name already exists") from None

        if not row:
            raise not_found("Tag not found")
        return row

    def delete(self, conn: psycopg.Connection, tag_id: UUID) -> None:
        rc = execute(conn, "DELETE FROM tags WHERE id=%(id)s", {"id": tag_id})
        if rc == 0:
            raise not_found("Tag not found")

    def list(self, conn: psycopg.Connection, q: Optional[str]) -> tuple[list[dict], int]:
        params: dict = {}
        where_sql = ""
        if q:
            params["q"] = q
            where_sql = "WHERE name ILIKE ('%' || %(q)s || '%')"

        total_row = fetch_one(conn, f"SELECT count(*)::int AS total FROM tags {where_sql}", params)
        total = int(total_row["total"]) if total_row else 0

        rows = fetch_all(
            conn,
            f"""
            SELECT id, name, created_at
            FROM tags
            {where_sql}
            ORDER BY name ASC
            """,
            params,
        )
        return rows, total

    def ensure_exists(self, conn: psycopg.Connection, tag_id: UUID) -> None:
        row = fetch_one(conn, "SELECT id FROM tags WHERE id=%(id)s", {"id": tag_id})
        if not row:
            raise not_found("Tag not found")


class NoteTagsRepository:
    """Data access for note<->tag assignments."""

    def assign(self, conn: psycopg.Connection, note_id: UUID, tag_id: UUID) -> None:
        # Ensure both exist for better error messages than FK violation.
        note = fetch_one(conn, "SELECT id FROM notes WHERE id=%(id)s", {"id": note_id})
        if not note:
            raise not_found("Note not found")
        tag = fetch_one(conn, "SELECT id FROM tags WHERE id=%(id)s", {"id": tag_id})
        if not tag:
            raise not_found("Tag not found")

        execute(
            conn,
            """
            INSERT INTO note_tags (note_id, tag_id)
            VALUES (%(note_id)s, %(tag_id)s)
            ON CONFLICT DO NOTHING
            """,
            {"note_id": note_id, "tag_id": tag_id},
        )

    def remove(self, conn: psycopg.Connection, note_id: UUID, tag_id: UUID) -> None:
        # Do not require existence; removing a non-existent assignment is idempotent.
        execute(
            conn,
            "DELETE FROM note_tags WHERE note_id=%(note_id)s AND tag_id=%(tag_id)s",
            {"note_id": note_id, "tag_id": tag_id},
        )
