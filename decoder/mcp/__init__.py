"""
MCP server for Decoder.

Exposes call graph analysis tools to LLMs via the Model Context Protocol.

Tools:
    - decoder_callers: Find what calls a function
    - decoder_callees: Find what a function calls
    - decoder_trace: Trace full call tree
    - decoder_find: Search for symbols
    - decoder_stats: Get index statistics

Usage:
    Install: pip install mcp-server-decoder
    Run: mcp-server-decoder
"""

import asyncio

from decoder.mcp.server import serve as _serve


def serve() -> None:
    """Entry point for the MCP server."""
    asyncio.run(_serve())


__all__ = ["serve"]
