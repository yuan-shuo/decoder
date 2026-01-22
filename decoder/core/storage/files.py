"""File storage operations."""

from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Callable
from pathlib import Path

from decoder.core.models import FileRecord


class FileStorage:
    """Storage operations for indexed files."""

    def __init__(self, get_connection: Callable[[], sqlite3.Connection]) -> None:
        self._get_connection = get_connection

    def upsert(self, file: Path, content_hash: str) -> None:
        """Insert or update a file record."""
        conn = self._get_connection()
        conn.execute(
            """
            INSERT INTO files (path, hash, indexed_at) VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(path) DO UPDATE SET hash = ?, indexed_at = CURRENT_TIMESTAMP
            """,
            (str(file), content_hash, content_hash),
        )
        conn.commit()

    def get(self, file: Path) -> FileRecord | None:
        """Get a file record, or None if not indexed."""
        conn = self._get_connection()
        cursor = conn.execute("SELECT * FROM files WHERE path = ?", (str(file),))
        row = cursor.fetchone()
        if row is None:
            return None
        return FileRecord.from_row(row)

    def delete(self, file: Path) -> None:
        """Delete a file record."""
        conn = self._get_connection()
        conn.execute("DELETE FROM files WHERE path = ?", (str(file),))
        conn.commit()

    def needs_reindex(self, file: Path) -> bool:
        """Check if a file needs to be re-indexed based on hash."""
        record = self.get(file)
        if record is None:
            return True
        current_hash = compute_file_hash(file)
        return current_hash != record.hash

    def clear(self) -> None:
        """Delete all file records."""
        conn = self._get_connection()
        conn.execute("DELETE FROM files")
        conn.commit()


def compute_file_hash(file: Path) -> str:
    """Compute SHA-256 hash of a file's contents."""
    content = file.read_bytes()
    return hashlib.sha256(content).hexdigest()
