"""MCP server implementation for Decoder."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from decoder.core.graph import load_from_repository
from decoder.core.graph.traversal import get_callee_tree, get_caller_tree
from decoder.core.storage import SymbolRepository, get_default_db_path

server = Server("decoder")


def _get_repo() -> SymbolRepository:
    """Get repository for current directory."""
    db_path = get_default_db_path(Path.cwd())
    if not db_path.exists():
        raise FileNotFoundError(
            f"No decoder index found. Run 'decoder index .' first.\nExpected: {db_path}"
        )
    return SymbolRepository(db_path)


def _symbol_to_dict(symbol: Any) -> dict[str, Any]:
    """Convert a Symbol to a JSON-serializable dict."""
    return {
        "name": symbol.name,
        "qualified_name": symbol.qualified_name,
        "type": symbol.type.value,
        "file": str(symbol.file),
        "line": symbol.line,
        "end_line": symbol.end_line,
    }


def _tree_to_dict(node: Any, depth: int = 0) -> dict[str, Any]:
    """Convert a TreeNode to a JSON-serializable dict."""
    return {
        "name": node.symbol.name,
        "qualified_name": node.symbol.qualified_name,
        "type": node.symbol.type.value,
        "file": str(node.symbol.file),
        "line": node.symbol.line,
        "depth": depth,
        "is_conditional": node.is_conditional,
        "condition": node.condition,
        "is_loop": node.is_loop,
        "is_try_block": node.is_try_block,
        "children": [_tree_to_dict(c, depth + 1) for c in node.children],
    }


@server.list_tools()  # type: ignore[no-untyped-call, untyped-decorator]
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="decoder_callers",
            description=(
                "Find all functions/methods that call a given symbol. "
                "Returns callers with file locations and call context (conditional, loop, etc)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the function/method to find callers for",
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="decoder_callees",
            description=(
                "Find all functions/methods that a given symbol calls. "
                "Returns callees with line numbers and call context."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the function/method to find callees for",
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="decoder_trace",
            description=(
                "Trace the full call tree for a symbol - both callers (what calls it) "
                "and callees (what it calls). Returns a tree structure showing the "
                "complete call trace."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the function/method to trace",
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum depth to trace (default: 5)",
                        "default": 5,
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="decoder_find",
            description=(
                "Search for symbols (functions, classes, methods) by name. "
                "Supports partial matching."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (partial name match)",
                    },
                    "type": {
                        "type": "string",
                        "enum": ["function", "class", "method"],
                        "description": "Filter by symbol type (optional)",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="decoder_stats",
            description="Get statistics about the indexed codebase.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


@server.call_tool()  # type: ignore[untyped-decorator]
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    try:
        if name == "decoder_callers":
            result = _handle_callers(arguments["name"])
        elif name == "decoder_callees":
            result = _handle_callees(arguments["name"])
        elif name == "decoder_trace":
            result = _handle_trace(
                arguments["name"],
                arguments.get("max_depth", 5),
            )
        elif name == "decoder_find":
            result = _handle_find(
                arguments["query"],
                arguments.get("type"),
            )
        elif name == "decoder_stats":
            result = _handle_stats()
        else:
            result = {"error": f"Unknown tool: {name}"}

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except FileNotFoundError as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


def _handle_callers(name: str) -> dict[str, Any]:
    """Handle decoder_callers tool."""
    with _get_repo() as repo:
        symbols = repo.symbols.find(name)

        if not symbols:
            return {"error": f"No symbol found matching '{name}'", "results": []}

        results = []
        for symbol in symbols:
            caller_list = repo.edges.get_callers(symbol.id)
            results.append(
                {
                    "symbol": _symbol_to_dict(symbol),
                    "callers": [
                        {
                            **_symbol_to_dict(caller),
                            "call_line": edge.call_line,
                            "is_conditional": edge.is_conditional,
                            "condition": edge.condition,
                            "is_loop": edge.is_loop,
                            "is_try_block": edge.is_try_block,
                        }
                        for caller, edge in caller_list
                    ],
                }
            )

        return {"results": results}


def _handle_callees(name: str) -> dict[str, Any]:
    """Handle decoder_callees tool."""
    with _get_repo() as repo:
        symbols = repo.symbols.find(name)

        if not symbols:
            return {"error": f"No symbol found matching '{name}'", "results": []}

        results = []
        for symbol in symbols:
            callee_list = repo.edges.get_callees(symbol.id)
            results.append(
                {
                    "symbol": _symbol_to_dict(symbol),
                    "callees": [
                        {
                            **_symbol_to_dict(callee),
                            "call_line": edge.call_line,
                            "is_conditional": edge.is_conditional,
                            "condition": edge.condition,
                            "is_loop": edge.is_loop,
                            "is_try_block": edge.is_try_block,
                        }
                        for callee, edge in callee_list
                    ],
                }
            )

        return {"results": results}


def _handle_trace(name: str, max_depth: int) -> dict[str, Any]:
    """Handle decoder_trace tool."""
    with _get_repo() as repo:
        symbols = repo.symbols.find(name)

        if not symbols:
            return {"error": f"No symbol found matching '{name}'"}

        start_symbol = max(
            symbols,
            key=lambda s: (len(repo.edges.get_callees(s.id)) + len(repo.edges.get_callers(s.id))),
        )

        graph = load_from_repository(repo)
        callee_tree = get_callee_tree(graph, start_symbol.id, max_depth)
        caller_tree = get_caller_tree(graph, start_symbol.id, max_depth)

        return {
            "symbol": _symbol_to_dict(start_symbol),
            "callers": _tree_to_dict(caller_tree) if caller_tree else None,
            "callees": _tree_to_dict(callee_tree) if callee_tree else None,
        }


def _handle_find(query: str, symbol_type: str | None) -> dict[str, Any]:
    """Handle decoder_find tool."""
    from decoder.core.models import SymbolType

    with _get_repo() as repo:
        type_filter = SymbolType(symbol_type) if symbol_type else None
        symbols = repo.symbols.find(query, type_filter)

        return {
            "results": [_symbol_to_dict(s) for s in symbols],
        }


def _handle_stats() -> dict[str, Any]:
    """Handle decoder_stats tool."""
    with _get_repo() as repo:
        stats = repo.get_stats()
        return {
            "files": stats["files"],
            "symbols": stats["symbols"],
            "edges": stats["edges"],
            "last_indexed": str(stats["last_indexed"]) if stats["last_indexed"] else None,
        }


async def serve() -> None:
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())
