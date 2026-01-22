"""
Core module: data models, exceptions, and storage.

This module provides the foundational types and persistence layer:

Models (models.py):
    - Symbol: A function, class, method, or variable in the codebase
    - Edge: A call relationship between two symbols
    - SymbolType/EdgeType: Enums for categorization

Exceptions (exceptions.py):
    - DecoderError: Base exception for all decoder errors
    - ParseError: Source file could not be parsed
    - SymbolNotFoundError: Requested symbol doesn't exist

Storage (storage/):
    - SymbolRepository: Facade for all database operations
    - Uses SQLite for persistence in .decoder/index.db
"""

from decoder.core.exceptions import (
    DecoderError,
    ParseError,
    SymbolNotFoundError,
)
from decoder.core.models import Edge, EdgeType, FileRecord, IndexStats, Symbol, SymbolType
from decoder.core.storage import (
    SymbolRepository,
    compute_file_hash,
    get_default_db_path,
)

__all__ = [
    # Models
    "Symbol",
    "Edge",
    "FileRecord",
    "IndexStats",
    "SymbolType",
    "EdgeType",
    # Exceptions
    "DecoderError",
    "SymbolNotFoundError",
    "ParseError",
    # Storage
    "SymbolRepository",
    "compute_file_hash",
    "get_default_db_path",
]
