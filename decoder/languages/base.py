"""Protocol for language parsers."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from decoder.languages.models import ParseResult


class LanguageParser(Protocol):
    """Protocol for language parsers."""

    def parse(self, file: Path) -> ParseResult:
        """Parse a file and extract symbols and edges."""
        ...

    def supports(self, file: Path) -> bool:
        """Check if this parser supports the given file."""
        ...
