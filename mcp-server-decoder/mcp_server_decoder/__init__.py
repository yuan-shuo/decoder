"""MCP server for Decoder - static call graph analysis for Python."""

from decoder.mcp import serve


def main() -> None:
    """Entry point for mcp-server-decoder."""
    serve()


__all__ = ["main", "serve"]
