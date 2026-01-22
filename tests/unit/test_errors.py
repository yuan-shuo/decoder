"""Tests for error handling paths."""

import tempfile
from pathlib import Path

import pytest

from decoder.core.exceptions import ParseError, SymbolNotFoundError
from decoder.core.indexer import Indexer
from decoder.core.storage import SymbolRepository, get_default_db_path
from decoder.languages.python import PythonParser


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


@pytest.fixture
def repository(temp_dir: Path) -> SymbolRepository:
    """Create a repository for testing."""
    db_path = get_default_db_path(temp_dir)
    return SymbolRepository(db_path)


class TestParserErrors:
    """Tests for parser error handling."""

    def test_parse_syntax_error(self, temp_dir: Path) -> None:
        """Test that syntax errors raise ParseError."""
        bad_code = """
def broken(
    # Missing closing paren and colon
"""
        file_path = temp_dir / "bad_syntax.py"
        file_path.write_text(bad_code)

        parser = PythonParser()
        with pytest.raises(ParseError) as exc_info:
            parser.parse(file_path)

        assert "Syntax error" in str(exc_info.value)

    def test_parse_encoding_error(self, temp_dir: Path) -> None:
        """Test that encoding errors raise ParseError."""
        file_path = temp_dir / "bad_encoding.py"
        # Write invalid UTF-8 bytes
        file_path.write_bytes(b"\xff\xfe invalid utf-8 \x80\x81")

        parser = PythonParser()
        with pytest.raises(ParseError) as exc_info:
            parser.parse(file_path)

        assert "Cannot read" in str(exc_info.value)

    def test_parse_empty_file(self, temp_dir: Path) -> None:
        """Test that empty files parse without error."""
        file_path = temp_dir / "empty.py"
        file_path.write_text("")

        parser = PythonParser()
        result = parser.parse(file_path)

        assert result.symbols == []
        assert result.edges == []


class TestStorageErrors:
    """Tests for storage error handling."""

    def test_symbol_not_found_by_id(self, repository: SymbolRepository) -> None:
        """Test that getting a nonexistent symbol by ID raises SymbolNotFoundError."""
        with pytest.raises(SymbolNotFoundError) as exc_info:
            repository.symbols.get_by_id(999)

        assert "999" in str(exc_info.value)

    def test_symbol_not_found_by_qualified_name(self, repository: SymbolRepository) -> None:
        """Test that getting a nonexistent symbol by name raises SymbolNotFoundError."""
        with pytest.raises(SymbolNotFoundError) as exc_info:
            repository.symbols.get_by_qualified_name("nonexistent.symbol")

        assert "nonexistent.symbol" in str(exc_info.value)

    def test_symbol_not_found_at_line(self, repository: SymbolRepository, temp_dir: Path) -> None:
        """Test that getting a symbol at a line with no symbol raises SymbolNotFoundError."""
        file_path = temp_dir / "test.py"
        file_path.write_text("# just a comment")

        with pytest.raises(SymbolNotFoundError) as exc_info:
            repository.symbols.get_at_line(file_path, 1)

        assert str(file_path) in str(exc_info.value)

    def test_find_returns_empty_list(self, repository: SymbolRepository) -> None:
        """Test that find returns empty list for no matches (not an error)."""
        results = repository.symbols.find("nonexistent")
        assert results == []


class TestIndexerErrors:
    """Tests for indexer error handling."""

    def test_index_file_with_syntax_error(
        self, repository: SymbolRepository, temp_dir: Path
    ) -> None:
        """Test that indexing a file with syntax error raises ParseError."""
        bad_code = "def broken("
        file_path = temp_dir / "bad.py"
        file_path.write_text(bad_code)

        indexer = Indexer(repository)
        with pytest.raises(ParseError):
            indexer.index_file(file_path)

    def test_index_directory_collects_errors(
        self, repository: SymbolRepository, temp_dir: Path
    ) -> None:
        """Test that index_directory collects errors instead of raising."""
        # Create one good file and one bad file
        good_file = temp_dir / "good.py"
        good_file.write_text("def foo(): pass")

        bad_file = temp_dir / "bad.py"
        bad_file.write_text("def broken(")

        indexer = Indexer(repository)
        stats = indexer.index_directory(temp_dir)

        # One file indexed successfully, one had an error
        assert stats.files == 1
        assert len(stats.errors) == 1
        assert "Syntax error" in stats.errors[0]

    def test_index_directory_excludes_patterns(
        self, repository: SymbolRepository, temp_dir: Path
    ) -> None:
        """Test that exclude patterns work."""
        # Create files
        (temp_dir / "include.py").write_text("def included(): pass")
        tests_dir = temp_dir / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_something.py").write_text("def test_excluded(): pass")

        indexer = Indexer(repository)
        stats = indexer.index_directory(temp_dir, exclude_patterns=["tests/*"])

        # Only include.py should be indexed
        assert stats.files == 1
        assert stats.skipped == 1

    def test_index_unchanged_files_skipped(
        self, repository: SymbolRepository, temp_dir: Path
    ) -> None:
        """Test that unchanged files are skipped on re-index."""
        file_path = temp_dir / "test.py"
        file_path.write_text("def foo(): pass")

        indexer = Indexer(repository)

        # First index
        stats1 = indexer.index_directory(temp_dir)
        assert stats1.files == 1
        assert stats1.unchanged == 0

        # Second index (same files)
        stats2 = indexer.index_directory(temp_dir)
        assert stats2.files == 0
        assert stats2.unchanged == 1

    def test_index_force_reindexes(
        self, repository: SymbolRepository, temp_dir: Path
    ) -> None:
        """Test that force=True re-indexes unchanged files."""
        file_path = temp_dir / "test.py"
        file_path.write_text("def foo(): pass")

        indexer = Indexer(repository)

        # First index
        stats1 = indexer.index_directory(temp_dir)
        assert stats1.files == 1

        # Second index with force
        stats2 = indexer.index_directory(temp_dir, force=True)
        assert stats2.files == 1
        assert stats2.unchanged == 0


class TestExceptionHierarchy:
    """Tests for exception class hierarchy."""

    def test_parse_error_is_decoder_error(self) -> None:
        """Test that ParseError inherits from DecoderError."""
        from decoder.core.exceptions import DecoderError

        error = ParseError("test")
        assert isinstance(error, DecoderError)
        assert isinstance(error, Exception)

    def test_symbol_not_found_is_decoder_error(self) -> None:
        """Test that SymbolNotFoundError inherits from DecoderError."""
        from decoder.core.exceptions import DecoderError

        error = SymbolNotFoundError("test")
        assert isinstance(error, DecoderError)
        assert isinstance(error, Exception)
