"""Symbol storage operations."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path

from decoder.core.exceptions import SymbolNotFoundError
from decoder.core.models import Symbol, SymbolType


class SymbolStorage:
    """Storage operations for symbols."""

    def __init__(self, get_connection: Callable[[], sqlite3.Connection]) -> None:
        self._get_connection = get_connection

    def insert(
        self,
        name: str,
        qualified_name: str,
        file: Path,
        line: int,
        symbol_type: SymbolType,
        end_line: int | None = None,
        parent_id: int | None = None,
    ) -> int:
        """Insert a symbol and return its ID."""
        conn = self._get_connection()
        cursor = conn.execute(
            """
            INSERT INTO symbols (name, qualified_name, file, line, end_line, type, parent_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (name, qualified_name, str(file), line, end_line, symbol_type.value, parent_id),
        )
        conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    def get_by_id(self, symbol_id: int) -> Symbol:
        """Get a symbol by its ID."""
        conn = self._get_connection()
        cursor = conn.execute("SELECT * FROM symbols WHERE id = ?", (symbol_id,))
        row = cursor.fetchone()
        if row is None:
            raise SymbolNotFoundError(f"Symbol with id {symbol_id} not found")
        return Symbol.from_row(row)

    def get_by_qualified_name(self, qualified_name: str) -> Symbol:
        """Get a symbol by its qualified name."""
        conn = self._get_connection()
        cursor = conn.execute("SELECT * FROM symbols WHERE qualified_name = ?", (qualified_name,))
        row = cursor.fetchone()
        if row is None:
            raise SymbolNotFoundError(f"Symbol '{qualified_name}' not found")
        return Symbol.from_row(row)

    def find(self, query: str, symbol_type: SymbolType | None = None) -> list[Symbol]:
        """Search for symbols by name (fuzzy match)."""
        conn = self._get_connection()
        if symbol_type is not None:
            cursor = conn.execute(
                "SELECT * FROM symbols WHERE name LIKE ? AND type = ? ORDER BY name",
                (f"%{query}%", symbol_type.value),
            )
        else:
            cursor = conn.execute(
                "SELECT * FROM symbols WHERE name LIKE ? ORDER BY name",
                (f"%{query}%",),
            )
        return [Symbol.from_row(row) for row in cursor.fetchall()]

    def get_in_file(self, file: Path) -> list[Symbol]:
        """Get all symbols in a file."""
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT * FROM symbols WHERE file = ? ORDER BY line",
            (str(file),),
        )
        return [Symbol.from_row(row) for row in cursor.fetchall()]

    def get_at_line(self, file: Path, line: int) -> Symbol:
        """Get the symbol at a specific line (or the nearest enclosing one)."""
        conn = self._get_connection()
        cursor = conn.execute(
            """
            SELECT * FROM symbols
            WHERE file = ? AND line <= ? AND (end_line IS NULL OR end_line >= ?)
            ORDER BY line DESC
            LIMIT 1
            """,
            (str(file), line, line),
        )
        row = cursor.fetchone()
        if row is None:
            raise SymbolNotFoundError(f"No symbol at {file}:{line}")
        return Symbol.from_row(row)

    def delete_in_file(self, file: Path) -> int:
        """Delete all symbols in a file. Returns count deleted."""
        conn = self._get_connection()
        cursor = conn.execute("DELETE FROM symbols WHERE file = ?", (str(file),))
        conn.commit()
        return cursor.rowcount

    def clear(self) -> None:
        """Delete all symbols."""
        conn = self._get_connection()
        conn.execute("DELETE FROM symbols")
        conn.commit()
