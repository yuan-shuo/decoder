"""Load CallGraph from SymbolRepository."""

from __future__ import annotations

from typing import TYPE_CHECKING

from decoder.core.graph.base import CallGraph
from decoder.core.models import Edge, EdgeType, Symbol

if TYPE_CHECKING:
    from decoder.core.storage import SymbolRepository


def load_from_repository(repo: SymbolRepository) -> CallGraph:
    """Load full graph from repository. O(V + E)."""
    graph = CallGraph()
    conn = repo._get_connection()

    cursor = conn.execute("SELECT * FROM symbols")
    for row in cursor.fetchall():
        symbol = Symbol.from_row(row)
        graph.add_symbol(symbol)

    cursor = conn.execute("SELECT * FROM edges")
    for row in cursor.fetchall():
        edge = Edge(
            id=row["id"],
            caller_id=row["caller_id"],
            callee_id=row["callee_id"],
            call_line=row["call_line"],
            call_type=EdgeType(row["call_type"]),
            is_conditional=bool(row["is_conditional"]),
            condition=row["condition"],
            is_loop=bool(row["is_loop"]),
            is_try_block=bool(row["is_try_block"]),
            is_except_handler=bool(row["is_except_handler"]),
        )
        graph.add_edge(edge)

    return graph


def load_subgraph(
    repo: SymbolRepository,
    root_id: int,
    direction: str = "callees",
    max_depth: int = 10,
) -> CallGraph:
    """Load only the subgraph reachable from root.

    More memory efficient for large codebases.
    """
    graph = CallGraph()
    conn = repo._get_connection()
    visited: set[int] = set()
    queue: list[tuple[int, int]] = [(root_id, 0)]

    while queue:
        symbol_id, depth = queue.pop(0)
        if symbol_id in visited or depth > max_depth:
            continue
        visited.add(symbol_id)

        cursor = conn.execute("SELECT * FROM symbols WHERE id = ?", (symbol_id,))
        row = cursor.fetchone()
        if row:
            graph.add_symbol(Symbol.from_row(row))

        if direction == "callees":
            edge_cursor = conn.execute("SELECT * FROM edges WHERE caller_id = ?", (symbol_id,))
        else:
            edge_cursor = conn.execute("SELECT * FROM edges WHERE callee_id = ?", (symbol_id,))

        for edge_row in edge_cursor.fetchall():
            edge = Edge(
                id=edge_row["id"],
                caller_id=edge_row["caller_id"],
                callee_id=edge_row["callee_id"],
                call_line=edge_row["call_line"],
                call_type=EdgeType(edge_row["call_type"]),
                is_conditional=bool(edge_row["is_conditional"]),
                condition=edge_row["condition"],
                is_loop=bool(edge_row["is_loop"]),
                is_try_block=bool(edge_row["is_try_block"]),
                is_except_handler=bool(edge_row["is_except_handler"]),
            )
            graph.add_edge(edge)

            next_id = edge.callee_id if direction == "callees" else edge.caller_id
            if next_id not in visited:
                queue.append((next_id, depth + 1))

    return graph
