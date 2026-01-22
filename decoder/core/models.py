"""Data models for Decoder."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path


class SymbolType(Enum):
    """Types of symbols that can be indexed."""

    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    VARIABLE = "variable"


class EdgeType(Enum):
    """Types of relationships between symbols."""

    CALL = "call"
    IMPORT = "import"
    INHERIT = "inherit"
    ATTRIBUTE = "attribute"


@dataclass
class Symbol:
    """A code symbol (function, class, method, or variable)."""

    id: int
    name: str
    qualified_name: str
    file: Path
    line: int
    end_line: int | None
    type: SymbolType
    parent_id: int | None = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Symbol:
        """Create a Symbol from a database row."""
        return cls(
            id=row["id"],
            name=row["name"],
            qualified_name=row["qualified_name"],
            file=Path(row["file"]),
            line=row["line"],
            end_line=row["end_line"],
            type=SymbolType(row["type"]),
            parent_id=row["parent_id"],
        )


@dataclass
class Edge:
    """A relationship between two symbols."""

    id: int
    caller_id: int
    callee_id: int
    call_line: int
    call_type: EdgeType
    # Context fields for smart analysis
    is_conditional: bool = False
    condition: str | None = None
    is_loop: bool = False
    is_try_block: bool = False
    is_except_handler: bool = False

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Edge:
        """Create an Edge from a database row."""
        return cls(
            id=row["id"],
            caller_id=row["caller_id"],
            callee_id=row["callee_id"],
            call_line=row["call_line"],
            call_type=EdgeType(row["call_type"]),
            is_conditional=bool(row["is_conditional"]) if "is_conditional" in row.keys() else False,
            condition=row["condition"] if "condition" in row.keys() else None,
            is_loop=bool(row["is_loop"]) if "is_loop" in row.keys() else False,
            is_try_block=bool(row["is_try_block"]) if "is_try_block" in row.keys() else False,
            is_except_handler=(
                bool(row["is_except_handler"]) if "is_except_handler" in row.keys() else False
            ),
        )


@dataclass
class FileRecord:
    """A record of an indexed file."""

    path: Path
    hash: str
    indexed_at: datetime

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> FileRecord:
        """Create a FileRecord from a database row."""
        return cls(
            path=Path(row["path"]),
            hash=row["hash"],
            indexed_at=datetime.fromisoformat(row["indexed_at"]),
        )


class IndexStats:
    """Statistics from an indexing operation."""

    def __init__(self) -> None:
        self.files: int = 0
        self.symbols: int = 0
        self.edges: int = 0
        self.skipped: int = 0
        self.unchanged: int = 0
        self.errors: list[str] = []

    def __repr__(self) -> str:
        return (
            f"IndexStats(files={self.files}, symbols={self.symbols}, "
            f"edges={self.edges}, skipped={self.skipped}, "
            f"unchanged={self.unchanged}, errors={len(self.errors)})"
        )
