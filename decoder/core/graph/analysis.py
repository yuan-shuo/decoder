"""Graph analysis: cycles, entry points, hot paths, topological sort."""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from decoder.core.graph.base import CallGraph
    from decoder.core.models import Symbol


def has_cycle(graph: CallGraph) -> bool:
    """Check for cycles using three-color DFS. O(V + E)."""
    white, gray, black = 0, 1, 2
    color: dict[int, int] = {v: white for v in graph.symbols}

    def dfs(node_id: int) -> bool:
        color[node_id] = gray
        for callee_id, _ in graph._out.get(node_id, []):
            if callee_id in color:
                if color[callee_id] == gray:
                    return True
                if color[callee_id] == white and dfs(callee_id):
                    return True
        color[node_id] = black
        return False

    return any(color[nid] == white and dfs(nid) for nid in graph.symbols)


def find_cycles(graph: CallGraph, max_cycles: int = 10) -> list[list[Symbol]]:
    """Find all cycles in the graph."""
    cycles: list[list[Symbol]] = []
    visited: set[int] = set()
    stack: list[int] = []
    stack_set: set[int] = set()

    def dfs(node_id: int) -> None:
        if len(cycles) >= max_cycles:
            return

        visited.add(node_id)
        stack.append(node_id)
        stack_set.add(node_id)

        for callee_id, _ in graph._out.get(node_id, []):
            if callee_id not in visited:
                dfs(callee_id)
            elif callee_id in stack_set:
                idx = stack.index(callee_id)
                cycle = [graph.symbols[n] for n in stack[idx:]]
                cycles.append(cycle)

        stack.pop()
        stack_set.remove(node_id)

    for nid in graph.symbols:
        if nid not in visited:
            dfs(nid)

    return cycles


def get_entry_points(graph: CallGraph) -> list[Symbol]:
    """Get symbols with no callers (in-degree = 0). O(V)."""
    return [graph.symbols[sid] for sid in graph.symbols if not graph._in.get(sid)]


def get_leaf_functions(graph: CallGraph) -> list[Symbol]:
    """Get symbols with no callees (out-degree = 0). O(V)."""
    return [graph.symbols[sid] for sid in graph.symbols if not graph._out.get(sid)]


def get_hot_paths(graph: CallGraph, top_k: int = 10) -> list[Symbol]:
    """Get symbols with highest connectivity. O(V log V)."""
    scored = [
        (sid, len(graph._in.get(sid, [])) + len(graph._out.get(sid, []))) for sid in graph.symbols
    ]
    scored.sort(key=lambda x: -x[1])
    return [graph.symbols[sid] for sid, _ in scored[:top_k]]


def topological_sort(graph: CallGraph) -> list[Symbol] | None:
    """Topological sort using Kahn's algorithm. O(V + E).

    Returns None if graph has cycles.
    """
    in_degree = {sid: len(graph._in.get(sid, [])) for sid in graph.symbols}
    queue: deque[int] = deque(sid for sid, d in in_degree.items() if d == 0)
    result: list[Symbol] = []

    while queue:
        node_id = queue.popleft()
        result.append(graph.symbols[node_id])

        for callee_id, _ in graph._out.get(node_id, []):
            if callee_id in in_degree:
                in_degree[callee_id] -= 1
                if in_degree[callee_id] == 0:
                    queue.append(callee_id)

    return result if len(result) == len(graph.symbols) else None
