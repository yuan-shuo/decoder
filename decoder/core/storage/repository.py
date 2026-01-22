"""Repository that coordinates all storage operations."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from decoder.core.storage.edges import EdgeStorage
from decoder.core.storage.files import FileStorage
from decoder.core.storage.symbols import SymbolStorage

_SCHEMA = """
CREATE TABLE IF NOT EXISTS symbols (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    qualified_name TEXT NOT NULL,
    file TEXT NOT NULL,
    line INTEGER NOT NULL,
    end_line INTEGER,
    type TEXT NOT NULL,
    parent_id INTEGER,
    FOREIGN KEY (parent_id) REFERENCES symbols(id)
);

CREATE TABLE IF NOT EXISTS edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    caller_id INTEGER NOT NULL,
    callee_id INTEGER NOT NULL,
    call_line INTEGER NOT NULL,
    call_type TEXT DEFAULT 'call',
    is_conditional INTEGER DEFAULT 0,
    condition TEXT,
    is_loop INTEGER DEFAULT 0,
    is_try_block INTEGER DEFAULT 0,
    is_except_handler INTEGER DEFAULT 0,
    FOREIGN KEY (caller_id) REFERENCES symbols(id),
    FOREIGN KEY (callee_id) REFERENCES symbols(id)
);

CREATE TABLE IF NOT EXISTS files (
    path TEXT PRIMARY KEY,
    hash TEXT NOT NULL,
    indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_edges_caller ON edges(caller_id);
CREATE INDEX IF NOT EXISTS idx_edges_callee ON edges(callee_id);
CREATE INDEX IF NOT EXISTS idx_symbols_file ON symbols(file);
CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(name);
CREATE INDEX IF NOT EXISTS idx_symbols_qualified ON symbols(qualified_name);
"""


class SymbolRepository:
    """Facade that coordinates symbols, edges, and files storage."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None

        self.symbols = SymbolStorage(self._get_connection)
        self.edges = EdgeStorage(self._get_connection)
        self.files = FileStorage(self._get_connection)

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create a database connection."""
        if self._conn is None:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(self._db_path)
            self._conn.row_factory = sqlite3.Row
            self._conn.executescript(_SCHEMA)
        return self._conn

    def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> SymbolRepository:
        return self

    def __exit__(self, exc_type: type | None, exc_val: Exception | None, exc_tb: object) -> None:
        self.close()

    def delete_file(self, file: Path) -> None:
        """Delete a file and all its symbols/edges."""
        self.edges.delete_for_file(file)
        self.symbols.delete_in_file(file)
        self.files.delete(file)

    def get_stats(self) -> dict[str, int | datetime | None]:
        """Get index statistics."""
        conn = self._get_connection()

        file_count = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        symbol_count = conn.execute("SELECT COUNT(*) FROM symbols").fetchone()[0]
        edge_count = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]

        last_indexed_row = conn.execute("SELECT MAX(indexed_at) FROM files").fetchone()[0]
        last_indexed = datetime.fromisoformat(last_indexed_row) if last_indexed_row else None

        return {
            "files": file_count,
            "symbols": symbol_count,
            "edges": edge_count,
            "last_indexed": last_indexed,
        }

    def clear(self) -> None:
        """Clear all data from the database."""
        self.edges.clear()
        self.symbols.clear()
        self.files.clear()


def get_default_db_path(project_root: Path) -> Path:
    """Get the default database path for a project."""
    return project_root / ".decoder" / "index.db"
