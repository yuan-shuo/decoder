"""Edge storage operations."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path

from decoder.core.models import Edge, EdgeType, Symbol


class EdgeStorage:
    """Storage operations for edges (relationships between symbols)."""

    def __init__(self, get_connection: Callable[[], sqlite3.Connection]) -> None:
        self._get_connection = get_connection

    def insert(
        self,
        caller_id: int,
        callee_id: int,
        call_line: int,
        call_type: EdgeType = EdgeType.CALL,
        is_conditional: bool = False,
        condition: str | None = None,
        is_loop: bool = False,
        is_try_block: bool = False,
        is_except_handler: bool = False,
    ) -> int:
        """Insert an edge and return its ID."""
        conn = self._get_connection()
        cursor = conn.execute(
            """
            INSERT INTO edges (caller_id, callee_id, call_line, call_type,
                              is_conditional, condition, is_loop, is_try_block, is_except_handler)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                caller_id,
                callee_id,
                call_line,
                call_type.value,
                int(is_conditional),
                condition,
                int(is_loop),
                int(is_try_block),
                int(is_except_handler),
            ),
        )
        conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    def get_callees(self, symbol_id: int) -> list[tuple[Symbol, Edge]]:
        """Get all symbols that this symbol calls (downstream)."""
        conn = self._get_connection()
        cursor = conn.execute(
            """
            SELECT s.*, e.id as edge_id, e.caller_id, e.callee_id, e.call_line, e.call_type,
                   e.is_conditional, e.condition, e.is_loop, e.is_try_block, e.is_except_handler
            FROM symbols s
            JOIN edges e ON s.id = e.callee_id
            WHERE e.caller_id = ?
            GROUP BY e.callee_id, e.call_line
            ORDER BY e.call_line
            """,
            (symbol_id,),
        )
        return self._rows_to_symbol_edge_pairs(cursor.fetchall())

    def get_callers(self, symbol_id: int) -> list[tuple[Symbol, Edge]]:
        """Get all symbols that call this symbol (upstream)."""
        conn = self._get_connection()
        cursor = conn.execute(
            """
            SELECT s.*, e.id as edge_id, e.caller_id, e.callee_id, e.call_line, e.call_type,
                   e.is_conditional, e.condition, e.is_loop, e.is_try_block, e.is_except_handler
            FROM symbols s
            JOIN edges e ON s.id = e.caller_id
            WHERE e.callee_id = ?
            GROUP BY e.caller_id, e.call_line
            ORDER BY s.file, e.call_line
            """,
            (symbol_id,),
        )
        return self._rows_to_symbol_edge_pairs(cursor.fetchall())

    def delete_for_file(self, file: Path) -> int:
        """Delete all edges involving symbols in a file."""
        conn = self._get_connection()
        cursor = conn.execute(
            """
            DELETE FROM edges WHERE caller_id IN (SELECT id FROM symbols WHERE file = ?)
            OR callee_id IN (SELECT id FROM symbols WHERE file = ?)
            """,
            (str(file), str(file)),
        )
        conn.commit()
        return cursor.rowcount

    def clear(self) -> None:
        """Delete all edges."""
        conn = self._get_connection()
        conn.execute("DELETE FROM edges")
        conn.commit()

    def _rows_to_symbol_edge_pairs(self, rows: list[sqlite3.Row]) -> list[tuple[Symbol, Edge]]:
        """Convert database rows to (Symbol, Edge) pairs."""
        results = []
        for row in rows:
            symbol = Symbol.from_row(row)
            edge = Edge(
                id=row["edge_id"],
                caller_id=row["caller_id"],
                callee_id=row["callee_id"],
                call_line=row["call_line"],
                call_type=EdgeType(row["call_type"]),
                is_conditional=bool(row["is_conditional"]),
                condition=row["condition"],
                is_loop=bool(row["is_loop"]),
                is_try_block=bool(row["is_try_block"]),
                is_except_handler=bool(row["is_except_handler"]),
            )
            results.append((symbol, edge))
        return results
