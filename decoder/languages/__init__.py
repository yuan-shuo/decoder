"""
Language parsers: Extract symbols and call relationships from source code.

This module provides the parsing layer that converts source files into
structured data (symbols and edges) for storage.

Components:
    - LanguageParser: Protocol defining the parser interface
    - PythonParser: AST-based parser for Python files
    - ParseResult: Container for extracted symbols, edges, and imports

The parser extracts:
    - Symbols: Functions, classes, methods, variables
    - Edges: Call relationships with context (conditional, loop, try/except)
    - Imports: Module imports for cross-file resolution
    - TypedVars: Type annotations for method resolution

Adding a new language:
    1. Create a new parser class implementing LanguageParser protocol
    2. Implement parse() to return ParseResult
    3. Implement supports() to check file extensions
"""

from decoder.languages.base import LanguageParser
from decoder.languages.models import ParsedEdge, ParsedSymbol, ParseResult
from decoder.languages.python import PythonParser

__all__ = [
    "LanguageParser",
    "ParsedEdge",
    "ParsedSymbol",
    "ParseResult",
    "PythonParser",
]
