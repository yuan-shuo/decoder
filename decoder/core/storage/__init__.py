"""
Storage layer: SQLite persistence for the call graph.

This module provides database operations split by concern:

Components:
    - SymbolRepository: Main facade that coordinates all storage
    - SymbolStorage: CRUD operations for symbols table
    - EdgeStorage: CRUD operations for edges table
    - FileStorage: Track indexed files and their hashes

Database Schema:
    symbols: id, name, qualified_name, file, line, end_line, type, parent_id
    edges: id, caller_id, callee_id, call_line, call_type, context flags
    files: path, hash, indexed_at

The database is stored at .decoder/index.db relative to the project root.
"""

from decoder.core.storage.edges import EdgeStorage
from decoder.core.storage.files import FileStorage, compute_file_hash
from decoder.core.storage.repository import SymbolRepository, get_default_db_path
from decoder.core.storage.symbols import SymbolStorage

__all__ = [
    "SymbolRepository",
    "SymbolStorage",
    "EdgeStorage",
    "FileStorage",
    "compute_file_hash",
    "get_default_db_path",
]
