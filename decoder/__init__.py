"""
Decoder: Static call graph analysis for Python codebases.

Decoder parses Python source code to build a call graph, enabling you to:
- Trace call chains from any function
- Find all callers/callees of a symbol
- Detect cycles and hot paths

Usage:
    from decoder.core import SymbolRepository, get_default_db_path
    from decoder.core.indexer import Indexer

    db_path = get_default_db_path(Path("."))
    with SymbolRepository(db_path) as repo:
        indexer = Indexer(repo)
        indexer.index_directory(Path("."))
"""

__version__ = "0.1.0"
